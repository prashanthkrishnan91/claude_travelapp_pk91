"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  Check,
  ChevronDown,
  ExternalLink,
  Info,
  Loader2,
  MapPin,
  Send,
  Sparkles,
  X,
} from "lucide-react";
import {
  addStructuredConciergeItemToTrip,
  saveToTripIdeas,
  fetchTripIdeas,
  callConciergeSearch,
  clearConciergeCache,
  fetchConciergeMessages,
  fetchItinerary,
} from "@/lib/api";
import type {
  UnifiedAreaComparisonResult,
  ConciergeSearchResult,
  UnifiedAttractionResult,
  UnifiedHotelResult,
  UnifiedResearchSourceResult,
  UnifiedRestaurantResult,
} from "@/lib/api";
import type { ItineraryDay, ItineraryItem } from "@/types";
import { pickCardReason, pickCardCategory, sanitizeWhyPick, shouldShowCollapsedSources, splitReason, normalizeTitle, isAddableCanonicalCard } from "@/lib/concierge/cardPresentation";
import { ACTION, parseRefinementAction, applyRefinementToMessage, buildContextualSearchQuery, selectBestCard, looksLikeFreshSearch, dedupeCardsAgainstCurrentSet, hasGooglePriceSignals, getBaselinePriceLevel } from "@/lib/concierge/refinementInterpreter";
import {
  hasClosedSignal,
  canShowGoogleVerifiedBadge,
  pickCardMeta,
} from "@/lib/concierge/cardHelpers";
import type {
  ClosedSignalSource,
  OperationalBadgeCard,
  DisplayCard,
} from "@/lib/concierge/cardHelpers";
import { Card } from "@/components/ui/Card";
import { TrustStrip } from "@/components/ui/TrustStrip";
import type { TrustConfidence } from "@/components/ui/TrustStrip";

type MessageRole = "user" | "assistant";

interface RefinementComparisonCard {
  name: string;
  category: string;
  rating: string | null;
  price: string | null;
  area: string | null;
  bestFor: string | null;
}

interface Message {
  role: MessageRole;
  text: string;
  restaurants?: UnifiedRestaurantResult[];
  attractions?: UnifiedAttractionResult[];
  hotels?: UnifiedHotelResult[];
  researchSources?: UnifiedResearchSourceResult[];
  areaComparisons?: UnifiedAreaComparisonResult[];
  intent?: string;
  retrievalUsed?: boolean;
  sourceStatus?: string;
  cached?: boolean;
  liveProvider?: string | null;
  sources?: string[];
  warnings?: string[];
  // Conversational refinement fields
  isRefinement?: boolean;
  refinementAction?: string;
  refinementComparison?: RefinementComparisonCard[] | null;
}

interface Props {
  tripId: string;
  destination: string;
  tripDays?: ItineraryDay[];
  isOpen: boolean;
  onClose: () => void;
  onItemAdded?: () => void;
  onIdeaSaved?: () => void;
}

const CONCIERGE_CACHE_VERSION = 5;

interface ConciergeClientCacheEntry {
  version: number;
  tripId: string;
  destination: string;
  messages: Message[];
}

function conciergeCacheKey(tripId: string, destination: string): string {
  return `concierge_cache::${tripId}::${destination.trim().toLowerCase()}`;
}

function readConciergeClientCache(tripId: string, destination: string): Message[] | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(conciergeCacheKey(tripId, destination));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ConciergeClientCacheEntry;
    if (parsed.version !== CONCIERGE_CACHE_VERSION) return null;
    if (parsed.tripId !== tripId) return null;
    if ((parsed.destination || "").trim().toLowerCase() !== destination.trim().toLowerCase()) return null;
    return Array.isArray(parsed.messages) ? parsed.messages : null;
  } catch {
    return null;
  }
}

function writeConciergeClientCache(tripId: string, destination: string, messages: Message[]): void {
  if (typeof window === "undefined") return;
  const payload: ConciergeClientCacheEntry = {
    version: CONCIERGE_CACHE_VERSION,
    tripId,
    destination,
    messages,
  };
  window.localStorage.setItem(conciergeCacheKey(tripId, destination), JSON.stringify(payload));
}

function clearConciergeClientCache(tripId: string, destination: string): void {
  if (typeof window === "undefined") return;
  const specificKey = conciergeCacheKey(tripId, destination);
  const tripPrefix = `concierge_cache::${tripId}::`;
  for (const storage of [window.localStorage, window.sessionStorage]) {
    const keysToDelete: string[] = [];
    for (let i = 0; i < storage.length; i += 1) {
      const key = storage.key(i);
      if (!key) continue;
      if (key === specificKey || key.startsWith(tripPrefix)) {
        keysToDelete.push(key);
      }
    }
    keysToDelete.forEach((key) => storage.removeItem(key));
  }
}

function sourceLabel(status: string, intent?: string, liveProvider?: string | null, cached?: boolean): string | null {
  if (status === "confirmed_michelin") return "Confirmed Michelin data";
  if (status === "curated_static") return intent === "michelin_restaurants"
    ? "Based on curated Michelin reference data"
    : "Based on available app database";
  if (status === "live_search") {
    const provider = liveProvider ? `Live · ${liveProvider}` : "Live search results";
    return cached ? `${provider} (cached)` : provider;
  }
  if (status === "mixed") {
    const provider = liveProvider ? `Live research (${liveProvider}) + fallback sources` : "Live research + fallback sources";
    return cached ? `${provider} (cached)` : provider;
  }
  if (status === "app_database") return "Based on available app database";
  if (status === "sample_data") return "Limited source coverage — verify hours and booking before adding.";
  if (status === "unavailable") return "Limited source coverage — verify names, hours, and booking details.";
  return null;
}

function isLiveSource(source?: string | null): boolean {
  return (source ?? "").toLowerCase().includes("live search");
}

function footerSourceLabel(msg: Message): string | null {
  const venueCards = [...(msg.restaurants ?? []), ...(msg.attractions ?? []), ...(msg.hotels ?? [])];
  const allCards = [...venueCards, ...(msg.researchSources ?? [])];
  const hasLive = allCards.some((card) => isLiveSource(card.source));
  const hasSample = allCards.some((card) => (card.source ?? "").toLowerCase().includes("sample"));
  const hasDbLike = venueCards.some((card) => {
    const source = (card.source ?? "").toLowerCase();
    return source.includes("database") || source === "search" || source.includes("michelin guide");
  });

  if (hasLive && (hasSample || hasDbLike)) {
    const provider = msg.liveProvider ? `Live research (${msg.liveProvider}) + fallback sources` : "Live research + fallback sources";
    return msg.cached ? `${provider} (cached)` : provider;
  }
  if (hasLive) {
    const provider = msg.liveProvider ? `Live · ${msg.liveProvider}` : "Live search results";
    return msg.cached ? `${provider} (cached)` : provider;
  }
  if (hasSample) {
    return "Limited source coverage — verify hours and booking before adding.";
  }
  return sourceLabel(msg.sourceStatus ?? "", msg.intent, msg.liveProvider, msg.cached);
}

function cardKey(name: string, dayId?: string): string {
  return `${name.trim().toLowerCase()}::${dayId ?? "trip"}`;
}

function pickCardDetail(place: { supportingDetails?: { conciergeNote?: string | null } | null }): string[] {
  const note = place.supportingDetails?.conciergeNote;
  return note ? [note] : [];
}

function ConciergeCard({
  title,
  category,
  meta,
  reason,
  extraDetail,
  mapLink,
  sourceLink,
  actionLabel,
  added,
  adding,
  savedIdea,
  savingIdea,
  isOperational,
  operationalConfidence,
  onAdd,
  onSaveIdea,
  canAdd = true,
}: {
  title: string;
  category: string;
  meta: string[];
  reason?: string;
  extraDetail?: string[];
  mapLink?: string;
  sourceLink?: string;
  actionLabel?: string;
  added: boolean;
  adding: boolean;
  savedIdea: boolean;
  savingIdea: boolean;
  isOperational?: boolean;
  operationalConfidence?: TrustConfidence;
  onAdd: () => void;
  onSaveIdea: () => void;
  canAdd?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const reasonParts = splitReason(reason);
  const expandableDetail = extraDetail ?? [];
  const hasDetail = expandableDetail.length > 0;

  return (
    <Card
      tone="dark"
      as="article"
      className="card-lift"
      style={{ padding: "var(--ds-space-4)" }}
    >
      {/* Identity */}
      <div style={{ marginBottom: "var(--ds-space-3)" }}>
        <h3
          className="text-ds-text font-semibold"
          style={{
            fontSize: "var(--ds-type-body-l-size)",
            lineHeight: "var(--ds-type-body-l-leading)",
          }}
        >
          {title}
        </h3>
        <p
          className="text-ds-text-tertiary uppercase tracking-[0.1em]"
          style={{
            fontSize: "var(--ds-type-overline-size)",
            lineHeight: "var(--ds-type-overline-leading)",
            fontWeight: "var(--ds-type-overline-weight)",
            marginTop: "var(--ds-space-1)",
          }}
        >
          {category}
        </p>
        {meta.length > 0 && (
          <p
            className="text-ds-text-secondary"
            style={{
              fontSize: "var(--ds-type-body-s-size)",
              lineHeight: "var(--ds-type-body-s-leading)",
              marginTop: "var(--ds-space-2)",
            }}
          >
            {meta.join(" · ")}
          </p>
        )}
      </div>

      {/* Trust strip — only where Google-verified OPERATIONAL; confidence from actual backend field */}
      {isOperational && operationalConfidence && (
        <div style={{ marginBottom: "var(--ds-space-3)" }} aria-label="Google verified">
          <TrustStrip confidence={operationalConfidence} />
        </div>
      )}

      {/* Concierge note — backend reason rendered verbatim, no paraphrase */}
      {reasonParts.short && (
        <div
          className="border-l-2"
          style={{
            borderColor: "var(--ds-accent-subtle)",
            paddingLeft: "var(--ds-space-3)",
            marginBottom: "var(--ds-space-3)",
          }}
        >
          <p
            className="text-ds-text-tertiary uppercase tracking-[0.1em]"
            style={{
              fontSize: "var(--ds-type-overline-size)",
              lineHeight: "var(--ds-type-overline-leading)",
              fontWeight: "var(--ds-type-overline-weight)",
              marginBottom: "var(--ds-space-1)",
            }}
          >
            Concierge note
          </p>
          <p
            className="text-ds-text-secondary"
            style={{
              fontSize: "var(--ds-type-body-s-size)",
              lineHeight: "var(--ds-type-body-s-leading)",
            }}
          >
            {reasonParts.short}
          </p>
          {hasDetail && (
            <>
              <button
                type="button"
                onClick={() => setExpanded((v) => !v)}
                className="inline-flex items-center gap-0.5 text-ds-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                style={{
                  fontSize: "var(--ds-type-caption-size)",
                  marginTop: "var(--ds-space-1)",
                }}
              >
                {expanded ? "Less" : "More"}
                <ChevronDown
                  className={`h-3 w-3 transition-transform duration-[120ms] ${expanded ? "rotate-180" : ""}`}
                  aria-hidden="true"
                />
              </button>
              {expanded && (
                <div
                  className="text-ds-text-tertiary"
                  style={{
                    marginTop: "var(--ds-space-1)",
                    fontSize: "var(--ds-type-caption-size)",
                    lineHeight: "var(--ds-type-caption-leading)",
                  }}
                >
                  {expandableDetail.map((line) => (
                    <p key={line}>{line}</p>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Actions: trip actions (add-to-day, save) + map/source links */}
      <Card.Actions style={{ marginTop: "var(--ds-space-3)", flexWrap: "wrap" }}>
        {canAdd ? (
          <>
            <button
              type="button"
              onClick={onAdd}
              disabled={adding || added}
              className={`flex-1 rounded-lg text-center transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2 disabled:opacity-50 ${
                added ? "text-ds-trust" : "text-ds-text-inverse hover:brightness-110"
              }`}
              style={{
                background: added ? "rgba(136, 168, 153, 0.15)" : "var(--ds-accent)",
                padding: "var(--ds-space-2) var(--ds-space-3)",
                fontSize: "var(--ds-type-body-s-size)",
                minHeight: "36px",
              }}
            >
              {adding ? (
                <Loader2 className="mx-auto h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              ) : added ? (
                <span className="inline-flex items-center gap-1">
                  <Check className="h-3 w-3" aria-hidden="true" />
                  Added
                </span>
              ) : (
                actionLabel ?? "Add to Day"
              )}
            </button>
            <button
              type="button"
              onClick={onSaveIdea}
              disabled={savingIdea || savedIdea}
              title={savedIdea ? "Saved to trip ideas" : "Save to trip ideas without assigning a day"}
              className="rounded-lg bg-ds-carbon text-ds-text-tertiary hover:bg-ds-pen-stroke hover:text-ds-text transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2 disabled:opacity-50"
              style={{
                padding: "var(--ds-space-2) var(--ds-space-3)",
                fontSize: "var(--ds-type-body-s-size)",
                border: "1px solid var(--ds-pen-stroke)",
                minHeight: "36px",
              }}
            >
              {savingIdea ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              ) : savedIdea ? (
                <span className="inline-flex items-center gap-1">
                  <Check className="h-3 w-3" aria-hidden="true" />
                  Saved
                </span>
              ) : (
                "Save"
              )}
            </button>
          </>
        ) : sourceLink ? (
          <a
            href={sourceLink}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg bg-ds-carbon text-ds-text-tertiary hover:bg-ds-pen-stroke hover:text-ds-text transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
            style={{
              padding: "var(--ds-space-2) var(--ds-space-3)",
              fontSize: "var(--ds-type-body-s-size)",
              border: "1px solid var(--ds-pen-stroke)",
            }}
          >
            <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
            View source
          </a>
        ) : (
          <span
            className="text-ds-text-tertiary"
            style={{ fontSize: "var(--ds-type-caption-size)" }}
          >
            Research only
          </span>
        )}
        {mapLink && (
          <a
            href={mapLink}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`View ${title} on Google Maps`}
            className="inline-flex items-center rounded-lg bg-ds-carbon text-ds-text-tertiary hover:bg-ds-pen-stroke hover:text-ds-text transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
            style={{
              padding: "var(--ds-space-2) var(--ds-space-3)",
              border: "1px solid var(--ds-pen-stroke)",
              minHeight: "36px",
            }}
          >
            <MapPin className="h-3.5 w-3.5" aria-hidden="true" />
          </a>
        )}
        {sourceLink && sourceLink !== mapLink && canAdd && (
          <a
            href={sourceLink}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`View source for ${title}`}
            className="inline-flex items-center rounded-lg bg-ds-carbon text-ds-text-tertiary hover:bg-ds-pen-stroke hover:text-ds-text transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
            style={{
              padding: "var(--ds-space-2) var(--ds-space-3)",
              border: "1px solid var(--ds-pen-stroke)",
              minHeight: "36px",
            }}
          >
            <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
          </a>
        )}
      </Card.Actions>
    </Card>
  );
}

function fromSearchResult(result: ConciergeSearchResult): Message {
  return {
    role: "assistant",
    text: result.response,
    restaurants: result.restaurants,
    attractions: result.attractions,
    hotels: result.hotels,
    researchSources: result.researchSources,
    areaComparisons: result.areaComparisons,
    intent: result.intent,
    retrievalUsed: result.retrievalUsed,
    sourceStatus: result.sourceStatus,
    cached: result.cached,
    liveProvider: result.liveProvider ?? null,
    sources: result.sources,
    warnings: result.warnings,
  };
}

// Canonical addable-card gate (PR #287/#289 frontend enforcement).
// Replaces the previous fallback ladder which accepted any card with
// `type === "verified_place"` or a non-null googleVerification block, even
// when the canonical display contract was missing.  The new gate requires
// the full canonical contract: addability === "addable", display.displayName,
// display.displayCategory, and a Google providerPlaceId.  Cards that fail
// this gate are filtered out rather than rendered from legacy top-level
// fields, so backend contract drift surfaces as missing cards (loud) instead
// of a silently degraded polished card (quiet).
function isRenderableVerifiedPlace(place: {
  display?: { addability?: string | null; displayName?: string | null; displayCategory?: string | null } | null;
  googleVerification?: { providerPlaceId?: string | null } | null;
}): boolean {
  return isAddableCanonicalCard(place);
}

export function AIConciergePanel({ tripId, destination, tripDays: tripDaysProp = [], isOpen, onClose, onItemAdded, onIdeaSaved }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [input, setInput] = useState("");
  const [tripDays, setTripDays] = useState<ItineraryDay[]>([]);
  const [itineraryItems, setItineraryItems] = useState<ItineraryItem[]>([]);
  const [selectedDayId, setSelectedDayId] = useState<string>("");
  const [addingItems, setAddingItems] = useState<Set<string>>(new Set());
  const [addedItems, setAddedItems] = useState<Set<string>>(new Set());
  const [savingIdeaItems, setSavingIdeaItems] = useState<Set<string>>(new Set());
  const [savedIdeaItems, setSavedIdeaItems] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [historyWarning, setHistoryWarning] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const loadedTripRef = useRef<string | null>(null);
  const skipReloadRef = useRef(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-dismiss toast after 4 s
  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(id);
  }, [toast]);

  const quickActions = useMemo(() => {
    const dest = destination || "this destination";
    return [
      `Best restaurants near my hotel in ${dest}`,
      `Best attractions in ${dest}`,
      `Best hotels in ${dest}`,
      `Hidden gems in ${dest}`,
    ];
  }, [destination]);

  const followUpActions = useMemo(() => {
    const lastAssistantIntent = [...messages].reverse().find((msg) => msg.role === "assistant")?.intent;
    if (lastAssistantIntent && ["michelin_restaurants", "restaurants", "hidden_gems", "romantic", "family_friendly", "luxury_value"].includes(lastAssistantIntent)) {
      return ["Michelin / tasting menus", "Best value dinner", "Nearby cocktail bars"];
    }
    if (lastAssistantIntent === "hotels") {
      return ["Compare areas", "Luxury with value", "Points vs cash ideas"];
    }
    if (lastAssistantIntent && ["attractions", "plan_day"].includes(lastAssistantIntent)) {
      return ["Rainy day plan", "Kid-friendly options", "Nearby restaurants"];
    }
    return ["Best restaurants near my hotel", "Attractions for Day 2", "Compare neighborhoods"];
  }, [messages]);

  // Contextual refinement chips shown after a card result is present.
  // "Find cheaper nearby" only appears when the latest card set has usable Google
  // price signals; otherwise "Find more like these" avoids inviting a dead action.
  const refinementChips = useMemo(() => {
    const latestCardMsg = getLatestCardMessage(messages);
    if (!latestCardMsg) return null;
    const currentCards = [
      ...(latestCardMsg.restaurants ?? []),
      ...(latestCardMsg.attractions ?? []),
      ...(latestCardMsg.hotels ?? []),
    ].filter(isRenderableVerifiedPlace);
    const cheaperChip = hasGooglePriceSignals(currentCards) ? "Find cheaper nearby" : "Find more like these";
    return ["Show only casual", "Compare top 2", cheaperChip, "Add best to Day 1"];
  }, [messages]);

  useEffect(() => {
    if (!isOpen) return;
    setTimeout(() => inputRef.current?.focus(), 100);
  }, [isOpen]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const loadState = useCallback(async () => {
    setLoadingHistory(true);
    setError(null);
    setHistoryWarning(null);
    const [historyResult, itineraryResult, ideasResult] = await Promise.allSettled([
      fetchConciergeMessages(tripId),
      tripDaysProp.length > 0 ? Promise.resolve(tripDaysProp) : fetchItinerary(tripId),
      fetchTripIdeas(tripId),
    ]);

    const historyMessages: Message[] = historyResult.status === "fulfilled"
      ? historyResult.value
          .filter((m) => m.role === "assistant" || m.role === "user")
          .map((m) => {
            if (m.role === "assistant" && m.structuredResults) {
              return fromSearchResult(m.structuredResults);
            }
            return { role: m.role as MessageRole, text: m.content };
          })
      : [];

    const cachedMessages = readConciergeClientCache(tripId, destination);
    const initialMessages = cachedMessages && cachedMessages.length > 0 ? cachedMessages : historyMessages;

    if (historyResult.status === "rejected") {
      const detail = historyResult.reason instanceof Error ? historyResult.reason.message : String(historyResult.reason ?? "");
      const lowered = detail.toLowerCase();
      const isExpectedEmptyStateFailure =
        lowered.includes("404")
        || lowered.includes("not found")
        || lowered.includes("relation")
        || lowered.includes("does not exist")
        || lowered.includes("permission denied")
        || lowered.includes("row-level security")
        || lowered.includes("rls");

      console.error("[concierge] failed to load persisted history", historyResult.reason);

      if (!isExpectedEmptyStateFailure) {
        const hadConversation = messages.filter((msg) => msg.role === "user").length > 0;
        if (hadConversation) {
          setHistoryWarning("We couldn’t refresh older chat history right now.");
        }
      }
    }

    if (initialMessages.length === 0) {
      initialMessages.push({
        role: "assistant",
        text: `Tell me what you need for ${destination || "your trip"} and I'll return concise picks with action cards.`,
      });
    }

    const itinerary = itineraryResult.status === "fulfilled" ? itineraryResult.value : [];
    if (itineraryResult.status === "rejected") {
      console.error("[concierge] failed to load itinerary days", itineraryResult.reason);
    }

    const existingIdeas = ideasResult.status === "fulfilled" ? ideasResult.value : [];
    const ideaTitles = new Set(
      existingIdeas
        .filter((it) => (it.details as Record<string, unknown>)?.source_kind === "concierge_idea")
        .map((it) => it.title.trim().toLowerCase()),
    );

    setMessages(initialMessages);
    setTripDays(itinerary);
    setItineraryItems(itinerary.flatMap((day) => day.items ?? []));
    setSavedIdeaItems(ideaTitles);
    setSelectedDayId((prev) => {
      if (prev && itinerary.some((day) => day.id === prev)) return prev;
      return itinerary[0]?.id || "";
    });
    loadedTripRef.current = tripId;
    setLoadingHistory(false);
  }, [destination, messages, tripDaysProp, tripId]);

  useEffect(() => {
    if (messages.length === 0) return;
    writeConciergeClientCache(tripId, destination, messages);
  }, [destination, messages, tripId]);

  useEffect(() => {
    if (!isOpen) return;
    if (skipReloadRef.current) return;
    if (loadedTripRef.current === tripId && messages.length > 0) return;
    void loadState();
  }, [isOpen, tripId, messages.length, loadState]);

  useEffect(() => {
    if (loadedTripRef.current === tripId) return;
    setMessages([]);
    setTripDays([]);
    setItineraryItems([]);
    setSelectedDayId("");
    setAddedItems(new Set());
    setAddingItems(new Set());
    setError(null);
    setHistoryWarning(null);
    clearConciergeClientCache(tripId, destination);
  }, [destination, tripId]);

  async function handleClearChat() {
    skipReloadRef.current = true;
    loadedTripRef.current = tripId;
    setLoading(false);
    setLoadingHistory(false);
    setError(null);
    setHistoryWarning(null);
    setInput("");
    setMessages([]);
    setAddedItems(new Set());
    setAddingItems(new Set());
    clearConciergeClientCache(tripId, destination);

    try {
      await clearConciergeCache(tripId, destination);
      setToast("Concierge chat cleared.");
    } catch (err) {
      console.error("[concierge] clear cache failed", err);
      setError("Could not clear concierge cache.");
    }
  }

  useEffect(() => {
    if (tripDaysProp.length === 0) return;
    setTripDays(tripDaysProp);
    setItineraryItems(tripDaysProp.flatMap((day) => day.items ?? []));
    setSelectedDayId((prev) => {
      if (prev && tripDaysProp.some((day) => day.id === prev)) return prev;
      return tripDaysProp[0]?.id || "";
    });
  }, [tripDaysProp]);

  async function sendQuery(query: string) {
    if (!query || loading) return;
    skipReloadRef.current = false;
    const requestId = typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", text: query }]);
    setLoading(true);
    try {
      const result = await callConciergeSearch(tripId, query, requestId);
      setMessages((prev) => [...prev, fromSearchResult(result)]);
    } catch (err) {
      console.error("[concierge] send failed", err);
      setMessages((prev) => [...prev, { role: "assistant", text: "I hit a temporary issue. Please try again." }]);
      setError("Failed to send message.");
    } finally {
      setLoading(false);
    }
  }

  async function addItem(
    name: string,
    kind: "restaurant" | "attraction" | "hotel",
    item: UnifiedRestaurantResult | UnifiedAttractionResult | UnifiedHotelResult,
    reason?: string,
    targetDayId?: string,
  ): Promise<boolean> {
    const effectiveDayId = targetDayId ?? selectedDayId;
    if (!effectiveDayId) {
      setError("Select a day before adding this item.");
      return false;
    }
    const key = cardKey(name, effectiveDayId || undefined);
    if (addingItems.has(key) || addedItems.has(key)) return true;

    const duplicate = itineraryItems.some((it) => {
      const titleMatch = normalizeTitle(it.title) === normalizeTitle(name);
      if (!titleMatch) return false;
      if (effectiveDayId) return it.dayId === effectiveDayId;
      return it.tripId === tripId;
    });

    if (duplicate) {
      setAddedItems((prev) => new Set(prev).add(key));
      return true;
    }

    setAddingItems((prev) => new Set(prev).add(key));
    setError(null);
    let success = false;
    try {
      const added = await addStructuredConciergeItemToTrip(tripId, item, kind, {
        dayId: effectiveDayId || undefined,
        reason,
      });
      setAddedItems((prev) => new Set(prev).add(key));
      setItineraryItems((prev) => [...prev, added]);
      setTripDays((prev) =>
        prev.map((day) =>
          day.id === effectiveDayId
            ? { ...day, items: [...(day.items ?? []), added] }
            : day
        )
      );
      onItemAdded?.();
      success = true;
    } catch (err) {
      console.error("[concierge] add item failed", err);
      setError("Could not add item to trip.");
    } finally {
      setAddingItems((prev) => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
    }
    return success;
  }

  async function saveIdea(
    name: string,
    kind: "restaurant" | "attraction" | "hotel",
    item: UnifiedRestaurantResult | UnifiedAttractionResult | UnifiedHotelResult,
    reason?: string,
  ) {
    const normalizedName = name.trim().toLowerCase();
    if (savingIdeaItems.has(normalizedName) || savedIdeaItems.has(normalizedName)) return;

    setSavingIdeaItems((prev) => new Set(prev).add(normalizedName));
    setError(null);
    try {
      await saveToTripIdeas(tripId, item, kind, reason);
      setSavedIdeaItems((prev) => new Set(prev).add(normalizedName));
      setToast("Saved to Trip Ideas — close this panel to schedule it.");
      onIdeaSaved?.();
    } catch (err) {
      console.error("[concierge] save idea failed", err);
      setError("Could not save idea to trip.");
    } finally {
      setSavingIdeaItems((prev) => {
        const next = new Set(prev);
        next.delete(normalizedName);
        return next;
      });
    }
  }

  // Returns the most recent assistant message that has verified cards (non-refinement).
  function getLatestCardMessage(msgs: Message[]): Message | null {
    for (let i = msgs.length - 1; i >= 0; i--) {
      const m = msgs[i];
      if (m.role === "assistant" && !m.isRefinement && (
        (m.restaurants?.length ?? 0) > 0 ||
        (m.attractions?.length ?? 0) > 0 ||
        (m.hotels?.length ?? 0) > 0
      )) return m;
    }
    return null;
  }

  // Returns the user query that immediately preceded the latest card message.
  function getOriginalQuery(msgs: Message[], latestCardMsg: Message): string {
    const idx = msgs.indexOf(latestCardMsg);
    for (let i = idx - 1; i >= 0; i--) {
      if (msgs[i].role === "user") return msgs[i].text;
    }
    return destination;
  }

  // Flat array of addable cards with their kind, for passing to the refinement interpreter.
  function getCardsWithKind(msg: Message) {
    return [
      ...(msg.restaurants ?? []).filter(isRenderableVerifiedPlace).map((place) => ({ kind: "restaurant" as const, place })),
      ...(msg.attractions ?? []).filter(isRenderableVerifiedPlace).map((place) => ({ kind: "attraction" as const, place })),
      ...(msg.hotels ?? []).filter(isRenderableVerifiedPlace).map((place) => ({ kind: "hotel" as const, place })),
    ];
  }

  // Main entry point for typed input and refinement chips.
  // Routes to refinement only when a card set exists AND the query is not a
  // fresh destination/category search. Falls back to sendQuery if the action
  // parser returns CLARIFY_UNSUPPORTED (handleRefinement returns false).
  async function handleUserInput(query: string) {
    const q = query.trim();
    if (!q || loading) return;
    const latestCardMsg = getLatestCardMessage(messages);
    if (latestCardMsg && !looksLikeFreshSearch(q)) {
      const handled = await handleRefinement(q, latestCardMsg);
      if (!handled) await sendQuery(q);
    } else {
      await sendQuery(q);
    }
  }

  // Returns false when the query should fall through to sendQuery instead
  // (CLARIFY_UNSUPPORTED — caller handles without double-appending user message).
  async function handleRefinement(query: string, latestCardMsg: Message): Promise<boolean> {
    const cardsWithKind = getCardsWithKind(latestCardMsg);
    const action = parseRefinementAction(query, cardsWithKind.map((c) => c.place)) as {
      type: string;
      modifier?: string;
      dayNumber?: number | null;
      isTemporal?: boolean;
      clarificationText?: string;
    };

    // CLARIFY_UNSUPPORTED: don't intercept — tell caller to use sendQuery.
    if (action.type === ACTION.CLARIFY_UNSUPPORTED) {
      return false;
    }

    // Confirmed refinement action — append user message and process.
    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", text: query }]);

    if (action.type === ACTION.ADD_SELECTED_TO_DAY) {
      const best = selectBestCard(cardsWithKind);
      if (!best) {
        setMessages((prev) => [...prev, {
          role: "assistant",
          text: "No cards available to add.",
          isRefinement: true, refinementAction: ACTION.ADD_SELECTED_TO_DAY,
          restaurants: [], attractions: [], hotels: [],
          researchSources: [], areaComparisons: [],
          retrievalUsed: false, sourceStatus: "none",
        }]);
        return true;
      }
      // Resolve the target day deterministically — never rely on async state.
      const resolvedDayId = action.dayNumber
        ? (tripDays.find((d) => d.dayNumber === action.dayNumber)?.id ?? selectedDayId)
        : selectedDayId;
      if (!resolvedDayId) {
        setMessages((prev) => [...prev, {
          role: "assistant",
          text: `Select a day first, then say "add the best one to Day X".`,
          isRefinement: true, refinementAction: ACTION.ADD_SELECTED_TO_DAY,
          restaurants: [], attractions: [], hotels: [],
          researchSources: [], areaComparisons: [],
          retrievalUsed: false, sourceStatus: "none",
        }]);
        return true;
      }
      const bestReason = pickCardReason(best.place);
      const sanitized = sanitizeWhyPick(bestReason, best.place.name, cardsWithKind.map((c) => c.place.name));
      // Pass resolvedDayId explicitly so addItem does not read from async state.
      const didAdd = await addItem(best.place.name, best.kind, best.place, sanitized, resolvedDayId);
      const dayLabel = action.dayNumber ? `Day ${action.dayNumber}` : "your selected day";
      setMessages((prev) => [...prev, {
        role: "assistant",
        text: didAdd
          ? `Added ${best.place.name} to ${dayLabel}.`
          : `I couldn't add ${best.place.name} to ${dayLabel}. Please try again.`,
        isRefinement: true, refinementAction: ACTION.ADD_SELECTED_TO_DAY,
        restaurants: [], attractions: [], hotels: [],
        researchSources: [], areaComparisons: [],
        retrievalUsed: false, sourceStatus: "none",
      }]);
      return true;
    }

    if (action.type === ACTION.SEARCH_MORE_WITH_CONTEXT) {
      const isCheaperQuery = /\bcheap(er)?\b|\bbudget\b|\baffordable\b|\blower[- ]price\b/i.test(query);
      const currentVisibleCards = getCardsWithKind(latestCardMsg).map((c) => c.place);
      if (isCheaperQuery && !hasGooglePriceSignals(currentVisibleCards)) {
        // No Google price signals for the current set — give honest message.
        setMessages((prev) => [...prev, {
          role: "assistant",
          text: "I don't have Google price signals for these places yet, so I can't honestly rank cheaper options. I can still find more options like these — try \"Find more like these\" to search for additional venues.",
          isRefinement: true,
          refinementAction: ACTION.SEARCH_MORE_WITH_CONTEXT,
          restaurants: [], attractions: [], hotels: [],
          researchSources: [], areaComparisons: [],
          retrievalUsed: false, sourceStatus: "none",
        }]);
        return true;
      }
      // isCheaperQuery with price signals: falls through to value-aware search.
      // The backend detects cheaper/budget/affordable in the contextual query and
      // sorts results by priceLevel ascending as a post-retrieval modifier.

      const originalQuery = getOriginalQuery(messages, latestCardMsg);
      const contextualQuery = buildContextualSearchQuery(originalQuery, query, { destination });
      setLoading(true);
      try {
        const requestId = typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
        const result = await callConciergeSearch(tripId, contextualQuery, requestId);
        // De-dupe against current visible card set before rendering.
        const deduped = dedupeCardsAgainstCurrentSet(fromSearchResult(result), currentVisibleCards) as Message & { allDuplicates: boolean };
        if (deduped.allDuplicates) {
          setMessages((prev) => [...prev, {
            role: "assistant",
            text: "I mostly found the same top options. Try specifying a different area or a vibe like quiet, lively, or late-night to discover different places.",
            isRefinement: true,
            refinementAction: ACTION.SEARCH_MORE_WITH_CONTEXT,
            restaurants: [], attractions: [], hotels: [],
            researchSources: [], areaComparisons: [],
            retrievalUsed: false, sourceStatus: "none",
          }]);
        } else if (isCheaperQuery) {
          const newCards = [
            ...(deduped.restaurants ?? []),
            ...(deduped.attractions ?? []),
            ...(deduped.hotels ?? []),
          ];
          const newHasPriceSignals = hasGooglePriceSignals(newCards);
          if (!newHasPriceSignals) {
            // No price data in returned cards — honest disclosure.
            setMessages((prev) => [...prev, {
              ...deduped,
              text: "I found more verified options, but not enough Google price data to prove they're cheaper. Showing them below — check their price tiers before deciding.",
            }]);
          } else {
            // Price signals present — check if any returned card is actually cheaper
            // than the current visible baseline. Never claim cheaper without proof.
            const baseline = getBaselinePriceLevel(currentVisibleCards);
            const PRICE_ORD = { PRICE_LEVEL_FREE: 0, PRICE_LEVEL_INEXPENSIVE: 1, PRICE_LEVEL_MODERATE: 2, PRICE_LEVEL_EXPENSIVE: 3, PRICE_LEVEL_VERY_EXPENSIVE: 4 } as const;
            type PriceLevelKey = keyof typeof PRICE_ORD;
            let minNewLevel: number | null = null;
            for (const c of newCards) {
              const lvl = (c as { supportingDetails?: { priceLevel?: string } }).supportingDetails?.priceLevel;
              if (lvl && lvl in PRICE_ORD) {
                const ord = PRICE_ORD[lvl as PriceLevelKey];
                minNewLevel = minNewLevel === null ? ord : Math.min(minNewLevel, ord);
              }
            }
            const hasActuallyCheaper = baseline !== null && minNewLevel !== null && minNewLevel < baseline;
            if (!hasActuallyCheaper) {
              setMessages((prev) => [...prev, {
                ...deduped,
                text: "I found more verified options, but Google price data does not prove they're cheaper than the current picks. Showing them below for comparison.",
              }]);
            } else {
              setMessages((prev) => [...prev, deduped]);
            }
          }
        } else {
          setMessages((prev) => [...prev, deduped]);
        }
      } catch (err) {
        console.error("[concierge] refinement search failed", err);
        setMessages((prev) => [...prev, { role: "assistant", text: "I hit a temporary issue. Please try again." }]);
        setError("Failed to send message.");
      } finally {
        setLoading(false);
      }
      return true;
    }

    // FILTER, REMOVE, RERANK, COMPARE — apply locally.
    const synthetic = applyRefinementToMessage(action, latestCardMsg);
    if (!synthetic) {
      // Filter returned no matches → tell user and fall through to contextual search.
      const originalQuery = getOriginalQuery(messages, latestCardMsg);
      const contextualQuery = buildContextualSearchQuery(originalQuery, query, { destination });
      setMessages((prev) => [...prev, {
        role: "assistant",
        text: `No matches for "${action.modifier ?? query}" in the current set. Searching for more options…`,
        isRefinement: true,
        refinementAction: action.type,
        restaurants: [], attractions: [], hotels: [],
        researchSources: [], areaComparisons: [],
        retrievalUsed: false, sourceStatus: "none",
      }]);
      setLoading(true);
      try {
        const requestId = typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
        const result = await callConciergeSearch(tripId, contextualQuery, requestId);
        setMessages((prev) => [...prev, fromSearchResult(result)]);
      } catch (err) {
        console.error("[concierge] refinement fallback search failed", err);
        setMessages((prev) => [...prev, { role: "assistant", text: "I hit a temporary issue. Please try again." }]);
        setError("Failed to send message.");
      } finally {
        setLoading(false);
      }
      return true;
    }

    setMessages((prev) => [...prev, synthetic as Message]);
    return true;
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative flex h-full w-full max-w-md flex-col border-l border-ds-pen-stroke bg-ds-midnight text-ds-text shadow-2xl">
        <div className="flex items-center justify-between border-b border-ds-pen-stroke bg-ds-onyx px-4 py-3">
          <div className="flex items-center gap-2 text-ds-text">
            <Sparkles className="h-4 w-4 text-ds-accent" />
            <span className="text-sm font-semibold">AI Concierge</span>
            {destination && <span className="text-xs text-ds-text-tertiary">· {destination}</span>}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleClearChat}
              className="rounded border border-ds-pen-stroke bg-ds-carbon px-2.5 py-1 text-[11px] font-medium text-ds-text hover:bg-ds-pen-stroke focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
            >
              Clear chat
            </button>
            <button onClick={onClose} className="rounded p-1 text-ds-text-tertiary hover:bg-ds-carbon focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2" aria-label="Close">
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="border-b border-ds-pen-stroke bg-ds-onyx px-4 py-2.5">
          <label className="text-[11px] font-medium uppercase tracking-[0.08em] text-ds-text-tertiary">Target day for Add to Day</label>
          <select
            value={selectedDayId}
            onChange={(e) => setSelectedDayId(e.target.value)}
            className="mt-1 w-full rounded-lg border border-ds-pen-stroke bg-ds-carbon px-2 py-1.5 text-xs text-ds-text"
          >
            {tripDays.length === 0 && <option value="">No days yet</option>}
            {tripDays.map((day) => (
              <option key={day.id} value={day.id}>
                Day {day.dayNumber}{day.date ? ` · ${day.date}` : ""}
              </option>
            ))}
          </select>
        </div>

        <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
          {loadingHistory && (
            <div className="rounded-lg bg-ds-carbon px-3 py-2 text-xs text-ds-text-secondary">Loading previous chat…</div>
          )}

          {loading && messages.length === 0 && (
            <div className="rounded-lg bg-ds-carbon px-3 py-2 text-xs text-ds-text-secondary">Loading concierge…</div>
          )}

          {error && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">{error}</div>
          )}

          {historyWarning && (
            <div className="rounded-lg border border-ds-pen-stroke bg-ds-carbon px-3 py-2 text-xs text-ds-text-secondary">
              {historyWarning}
            </div>
          )}

          {messages.map((msg, idx) => (
            <div key={idx} className="space-y-2">
              <div className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                {msg.role === "assistant" && msg.intent === "compare" ? (
                  <div className="w-full rounded-xl border border-indigo-200 bg-indigo-50 p-3">
                    <div className="mb-1.5 flex items-center gap-1.5">
                      <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-indigo-700">Comparison</span>
                    </div>
                    <p className="text-xs leading-relaxed text-slate-700">{msg.text}</p>
                  </div>
                ) : (
                  <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${msg.role === "user" ? "rounded-br-sm bg-ds-accent/15 text-ds-text ring-1 ring-ds-accent/30" : "rounded-bl-sm bg-ds-carbon text-ds-text"}`}>
                    {msg.text}
                  </div>
                )}
              </div>

              {msg.role === "assistant" && (
                <>
                  {msg.intent === "compare" && (msg.areaComparisons?.length ?? 0) > 0 && (
                    <>
                      <div className="hidden overflow-x-auto rounded-xl border border-slate-200 bg-white md:block">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-slate-50 text-slate-600">
                            <tr>
                              <th className="px-2 py-2 font-semibold">Area</th>
                              <th className="px-2 py-2 font-semibold">Vibe</th>
                              <th className="px-2 py-2 font-semibold">Best for</th>
                              <th className="px-2 py-2 font-semibold">Logistics</th>
                              <th className="px-2 py-2 font-semibold">Value</th>
                            </tr>
                          </thead>
                          <tbody>
                            {msg.areaComparisons?.map((area) => (
                              <tr key={area.area} className="border-t border-slate-100 align-top">
                                <td className="px-2 py-2 font-medium text-slate-900">{area.area}</td>
                                <td className="px-2 py-2 text-slate-700">{area.vibe}</td>
                                <td className="px-2 py-2 text-slate-700">{area.bestFor}</td>
                                <td className="px-2 py-2 text-slate-700">{area.logistics}</td>
                                <td className="px-2 py-2 text-slate-700">{area.valueSignal}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <div className="space-y-2 md:hidden">
                        {msg.areaComparisons?.map((area) => (
                          <div key={area.area} className="rounded-xl border border-slate-200 bg-white p-3 text-xs">
                            <p className="font-semibold text-slate-900">{area.area}</p>
                            <p className="mt-1 text-slate-700">{area.vibe}</p>
                            <p className="mt-1 text-slate-600"><span className="font-medium">Best for:</span> {area.bestFor}</p>
                            <p className="mt-1 text-slate-600"><span className="font-medium">Pros:</span> {area.pros.join(" · ")}</p>
                            <p className="mt-1 text-slate-600"><span className="font-medium">Cons:</span> {area.cons.join(" · ")}</p>
                            <p className="mt-1 text-slate-600"><span className="font-medium">Logistics:</span> {area.logistics}</p>
                            <p className="mt-1 text-slate-600"><span className="font-medium">Value:</span> {area.valueSignal}</p>
                            <p className="mt-1 text-slate-700"><span className="font-medium">Verdict:</span> {area.recommendation}</p>
                          </div>
                        ))}
                      </div>
                    </>
                  )}

                  {msg.refinementAction === ACTION.COMPARE_CURRENT_SET && msg.refinementComparison && msg.refinementComparison.length > 0 && (
                    <div className="rounded-xl border border-slate-600/40 bg-slate-800/30 px-3 py-2.5 text-xs">
                      <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-400">Quick comparison</p>
                      {/* Wide screens: side-by-side table */}
                      <table className="hidden w-full border-collapse sm:table">
                        <thead>
                          <tr>
                            <th className="w-16 pb-1.5 pr-3 text-left text-[10px] font-normal text-slate-500" />
                            {msg.refinementComparison.map((card) => (
                              <th key={card.name} className="pb-1.5 text-left">
                                <span className="font-semibold text-slate-200">{card.name}</span>
                                {card.category && <span className="ml-1 font-normal text-slate-400">· {card.category}</span>}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {msg.refinementComparison.some((c) => c.rating) && (
                            <tr className="border-t border-slate-700/40">
                              <td className="py-1 pr-3 text-slate-500">Rating</td>
                              {msg.refinementComparison.map((card) => (
                                <td key={card.name} className="py-1 text-slate-300">{card.rating ?? "—"}</td>
                              ))}
                            </tr>
                          )}
                          {msg.refinementComparison.some((c) => c.price) && (
                            <tr className="border-t border-slate-700/40">
                              <td className="py-1 pr-3 text-slate-500">Price</td>
                              {msg.refinementComparison.map((card) => (
                                <td key={card.name} className="py-1 text-slate-300">{card.price ?? "—"}</td>
                              ))}
                            </tr>
                          )}
                          {msg.refinementComparison.some((c) => c.area) && (
                            <tr className="border-t border-slate-700/40">
                              <td className="py-1 pr-3 text-slate-500">Area</td>
                              {msg.refinementComparison.map((card) => (
                                <td key={card.name} className="py-1 text-slate-300 leading-snug">{card.area ?? "—"}</td>
                              ))}
                            </tr>
                          )}
                          {msg.refinementComparison.some((c) => c.bestFor) && (
                            <tr className="border-t border-slate-700/40">
                              <td className="py-1 pr-3 text-slate-500">Best for</td>
                              {msg.refinementComparison.map((card) => (
                                <td key={card.name} className="py-1 italic text-slate-300 leading-snug">{card.bestFor ?? "—"}</td>
                              ))}
                            </tr>
                          )}
                        </tbody>
                      </table>
                      {/* Narrow screens: stacked cards — prevents column crush */}
                      <div className="flex flex-col gap-3 sm:hidden">
                        {msg.refinementComparison.map((card) => (
                          <div key={card.name} className="rounded-lg border border-slate-700/40 px-2.5 py-2">
                            <p className="mb-1.5 font-semibold text-slate-200 break-words">{card.name}
                              {card.category && <span className="ml-1 font-normal text-slate-400">· {card.category}</span>}
                            </p>
                            {card.rating && <p className="text-slate-300"><span className="text-slate-500 mr-1">Rating</span>{card.rating}</p>}
                            {card.price && <p className="text-slate-300"><span className="text-slate-500 mr-1">Price</span>{card.price}</p>}
                            {card.area && <p className="text-slate-300 leading-snug break-words"><span className="text-slate-500 mr-1">Area</span>{card.area}</p>}
                            {card.bestFor && <p className="italic text-slate-300 leading-snug break-words"><span className="not-italic text-slate-500 mr-1">Best for</span>{card.bestFor}</p>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {msg.intent !== "compare" && (msg.restaurants?.length || msg.attractions?.length || msg.hotels?.length || msg.researchSources?.length) ? (
                    <div className="space-y-2">
                      {(() => {
                        // isRenderableVerifiedPlace enforces the full canonical
                        // contract (display.addability + displayName + displayCategory
                        // + Google providerPlaceId).  Cards that fail it are dropped
                        // rather than rebuilt from legacy top-level fields.
                        const addablePlaces = [
                          ...(msg.restaurants ?? []).filter((r) => isRenderableVerifiedPlace(r)).map((place) => ({ kind: "restaurant" as const, place, sourceLink: place.bookingLink ?? place.sourceUrl })),
                          ...(msg.attractions ?? []).filter((a) => isRenderableVerifiedPlace(a)).map((place) => ({ kind: "attraction" as const, place, sourceLink: place.sourceUrl })),
                          ...(msg.hotels ?? []).filter((h) => isRenderableVerifiedPlace(h)).map((place) => ({ kind: "hotel" as const, place, sourceLink: place.bookingUrl ?? place.sourceUrl })),
                        ];
                        const allTitles = addablePlaces.map(({ place }) => place.display?.displayName ?? place.name);

                        return addablePlaces.map(({ kind, place, sourceLink }) => {
                          // Canonical display fields are required by isRenderableVerifiedPlace.
                          const title = place.display?.displayName ?? place.name;
                          const displayCategory = pickCardCategory(place);
                          const key = cardKey(title, selectedDayId || undefined);
                          const baseReason = pickCardReason(place);
                          const reason = sanitizeWhyPick(baseReason, title, allTitles);
                          const extraDetail = pickCardDetail(place);
                          const isClosed = hasClosedSignal(place as ClosedSignalSource);
                          const isOperational = !isClosed && canShowGoogleVerifiedBadge(place as OperationalBadgeCard);
                          const rawConfidence = (place as { googleVerification?: { confidence?: string } }).googleVerification?.confidence?.toLowerCase();
                          const operationalConfidence: TrustConfidence | undefined = isOperational && (rawConfidence === "high" || rawConfidence === "medium") ? (rawConfidence as TrustConfidence) : undefined;
                          const meta = pickCardMeta(place as DisplayCard);
                          // Maps URL prefers Google's googleMapsUri (canonical Google
                          // identity) and falls back to the explicit mapsLink that the
                          // backend already derives from providerPlaceId.  No top-level
                          // legacy URL ladders.
                          const mapLink = place.googleVerification?.googleMapsUri ?? place.mapsLink;

                          const normalizedName = title.trim().toLowerCase();
                          return (
                            <ConciergeCard
                              key={`${title}-${key}`}
                              title={title}
                              category={displayCategory}
                              meta={meta}
                              reason={reason}
                              extraDetail={extraDetail}
                              mapLink={mapLink}
                              sourceLink={sourceLink}
                              isOperational={isOperational}
                              operationalConfidence={operationalConfidence}
                              added={addedItems.has(key)}
                              adding={addingItems.has(key)}
                              savedIdea={savedIdeaItems.has(normalizedName)}
                              savingIdea={savingIdeaItems.has(normalizedName)}
                              canAdd={!isClosed}
                              onAdd={() => addItem(place.name, kind, place, reason)}
                              onSaveIdea={() => saveIdea(place.name, kind, place, reason)}
                            />
                          );
                        });
                      })()}

                      {shouldShowCollapsedSources(msg) && (
                        <div className="pt-1">
                          <details className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                            <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                              Sources used ({msg.researchSources?.filter((s) => s.type === "research_source").length ?? 0})
                            </summary>
                            <ul className="mt-2 space-y-1 text-xs text-slate-600">
                              {msg.researchSources?.filter((s) => s.type === "research_source").map((s) => (
                                <li key={`${s.title}-${s.sourceUrl ?? "source"}`} className="truncate">
                                  {s.sourceUrl ? (
                                    <a href={s.sourceUrl} target="_blank" rel="noreferrer" className="underline decoration-slate-300 underline-offset-2 hover:text-slate-800">
                                      {s.title}
                                    </a>
                                  ) : s.title}
                                </li>
                              ))}
                            </ul>
                          </details>
                        </div>
                      )}
                    </div>
                  ) : null}

                  {msg.warnings && msg.warnings.length > 0 && (
                    <div className="space-y-1">
                      {msg.warnings.map((warning, i) => (
                        <div key={i} className="flex items-start gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
                          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 text-amber-500" />
                          <p className="text-xs text-amber-700">{warning}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {msg.retrievalUsed && footerSourceLabel(msg) && (
                    <div className="flex items-center gap-1 text-[10px] text-ds-text-tertiary">
                      <Info className="h-3 w-3" />
                      <span>{footerSourceLabel(msg)}</span>
                    </div>
                  )}
                </>
              )}
            </div>
          ))}

          {messages.length <= 1 && !loadingHistory && (
            <div className="flex flex-wrap gap-2">
              {quickActions.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => handleUserInput(prompt)}
                  className="rounded-full border border-ds-pen-stroke bg-ds-carbon px-3 py-1.5 text-xs font-medium text-ds-text-secondary hover:bg-ds-pen-stroke hover:text-ds-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                >
                  {prompt}
                </button>
              ))}
            </div>
          )}

          {loading && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 rounded-2xl rounded-bl-sm bg-ds-carbon px-3 py-2">
                <Loader2 className="h-3 w-3 animate-spin text-ds-text-tertiary" />
                <span className="text-xs text-ds-text-secondary">Researching options…</span>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        <div className="border-t border-ds-pen-stroke bg-ds-midnight px-4 py-3">
          {toast && (
            <div className="mb-2 rounded-lg border border-ds-pen-stroke bg-ds-carbon px-3 py-2 text-xs text-ds-trust">
              {toast}
            </div>
          )}
          {messages.length > 1 && !loadingHistory && (
            <div className="mb-2 flex gap-1.5 overflow-x-auto pb-0.5 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
              {(refinementChips ?? followUpActions).map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => refinementChips ? handleUserInput(prompt) : sendQuery(prompt)}
                  className="shrink-0 rounded-full border border-ds-pen-stroke bg-ds-carbon px-3 py-1.5 text-[11px] font-medium text-ds-text-secondary hover:bg-ds-pen-stroke hover:text-ds-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                >
                  {prompt}
                </button>
              ))}
            </div>
          )}
          <div className="flex items-center gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleUserInput(input.trim())}
              placeholder="Ask, refine, or compare the results…"
              disabled={loading}
              className="flex-1 rounded-xl border border-ds-pen-stroke bg-ds-onyx px-3 py-2 text-sm text-ds-text placeholder:text-ds-text-tertiary focus:outline-none focus:ring-2 focus:ring-ds-accent/60 disabled:opacity-60"
            />
            <button
              onClick={() => handleUserInput(input.trim())}
              disabled={loading || !input.trim()}
              className="rounded-xl bg-ds-accent px-3 py-2 text-ds-text-inverse transition hover:brightness-110 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2 disabled:opacity-50"
              aria-label="Send"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
