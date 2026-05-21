"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { WorldAtmosphere, WorldScenery } from "@/components/ui/World";
import {
  applyRoom,
  pickWorldFromDestination,
  worldStyleVars,
} from "@/lib/worldData";
import {
  AlertTriangle,
  Bookmark,
  BookmarkCheck,
  ChevronDown,
  ExternalLink,
  Loader2,
  MapPin,
  Send,
  Trash2,
} from "lucide-react";
import { callConciergeSearch, saveItem } from "@/lib/api";
import type {
  ConciergeSearchResult,
  UnifiedAttractionResult,
  UnifiedAreaComparisonResult,
  UnifiedHotelResult,
  UnifiedResearchSourceResult,
  UnifiedRestaurantResult,
} from "@/lib/api";
import {
  pickCardReason,
  pickCardCategory,
  sanitizeWhyPick,
  splitReason,
  isAddableCanonicalCard,
  shouldShowCollapsedSources,
} from "@/lib/concierge/cardPresentation";
import {
  ACTION,
  parseRefinementAction,
  applyRefinementToMessage,
  buildContextualSearchQuery,
  looksLikeFreshSearch,
  dedupeCardsAgainstCurrentSet,
  hasGooglePriceSignals,
} from "@/lib/concierge/refinementInterpreter";
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

// ─── Types ────────────────────────────────────────────────────────────────────

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
  warnings?: string[];
  isRefinement?: boolean;
  refinementAction?: string;
  refinementComparison?: RefinementComparisonCard[] | null;
}

// ─── Data transforms ──────────────────────────────────────────────────────────

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
    warnings: result.warnings,
  };
}

function isRenderableVerifiedPlace(place: {
  display?: { addability?: string | null; displayName?: string | null; displayCategory?: string | null } | null;
  googleVerification?: { providerPlaceId?: string | null } | null;
}): boolean {
  return isAddableCanonicalCard(place);
}

function getLatestCardMessage(msgs: Message[]): Message | null {
  for (let i = msgs.length - 1; i >= 0; i--) {
    const m = msgs[i];
    if (
      m.role === "assistant" &&
      !m.isRefinement &&
      ((m.restaurants?.length ?? 0) > 0 ||
        (m.attractions?.length ?? 0) > 0 ||
        (m.hotels?.length ?? 0) > 0)
    )
      return m;
  }
  return null;
}

// ─── ConciergeResultCard ──────────────────────────────────────────────────────

type SaveState = "idle" | "saving" | "saved" | "error";

function ConciergeResultCard({
  title,
  category,
  meta,
  reason,
  extraDetail,
  mapLink,
  sourceLink,
  isOperational,
  operationalConfidence,
  onSave,
  saveState = "idle",
}: {
  title: string;
  category: string;
  meta: string[];
  reason?: string;
  extraDetail?: string[];
  mapLink?: string;
  sourceLink?: string;
  isOperational?: boolean;
  operationalConfidence?: TrustConfidence;
  onSave?: () => void;
  saveState?: SaveState;
}) {
  const [expanded, setExpanded] = useState(false);
  const reasonParts = splitReason(reason);
  const hasDetail = (extraDetail?.length ?? 0) > 0;

  return (
    <Card
      tone="dark"
      as="article"
      className="boutique-folio folio-cinema-desk folio-cinema-result-card card-lift flex flex-col"
      style={{ padding: "0", overflow: "hidden" }}
    >
      {/* Folio cover tab — makes each result card feel like a recommendation slip */}
      <div className="folio-cover-tab" aria-hidden="true" />
      {/* Card content — all interior content in a padded container */}
      <div style={{ padding: "var(--ds-space-5)" }}>
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

        {/* Trust strip — only where Google-verified OPERATIONAL */}
        {isOperational && operationalConfidence && (
          <div style={{ marginBottom: "var(--ds-space-3)" }}>
            <TrustStrip confidence={operationalConfidence} />
          </div>
        )}

        {/* Concierge note — backend reason, rendered verbatim */}
        {reasonParts.short && (
          <div
            className="border-l-2 text-ds-text-secondary"
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
                    {extraDetail?.map((line) => (
                      <p key={line}>{line}</p>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* Actions: save + map + source */}
        <div className="flex items-center gap-2 flex-wrap" style={{ marginTop: "var(--ds-space-3)" }}>
          {onSave && (
            <button
              type="button"
              onClick={saveState === "idle" || saveState === "error" ? onSave : undefined}
              disabled={saveState === "saving" || saveState === "saved"}
              aria-label={saveState === "saved" ? `${title} saved` : `Save ${title}`}
              data-testid="concierge-result-save-btn"
              className="inline-flex items-center gap-1.5 rounded-lg transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2 disabled:opacity-60 disabled:cursor-default"
              style={{
                padding: "var(--ds-space-2) var(--ds-space-3)",
                fontSize: "var(--ds-type-body-s-size)",
                background: saveState === "saved"
                  ? "color-mix(in srgb, var(--ds-trust) 15%, transparent)"
                  : "var(--ds-accent-subtle)",
                color: saveState === "saved" ? "var(--ds-trust)" : "var(--ds-accent)",
                border: `1px solid ${saveState === "saved" ? "var(--ds-trust)" : "color-mix(in srgb, var(--ds-accent) 30%, transparent)"}`,
              }}
            >
              {saveState === "saving" ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              ) : saveState === "saved" ? (
                <BookmarkCheck className="h-3.5 w-3.5" aria-hidden="true" />
              ) : (
                <Bookmark className="h-3.5 w-3.5" aria-hidden="true" />
              )}
              {saveState === "saved" ? "Saved" : saveState === "saving" ? "Saving…" : "Save"}
            </button>
          )}
          {mapLink && (
            <a
              href={mapLink}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`View ${title} on Google Maps`}
              className="inline-flex items-center gap-1.5 rounded-lg bg-ds-carbon text-ds-text-tertiary hover:bg-ds-pen-stroke hover:text-ds-text transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
              style={{
                padding: "var(--ds-space-2) var(--ds-space-3)",
                fontSize: "var(--ds-type-body-s-size)",
              }}
            >
              <MapPin className="h-3.5 w-3.5" aria-hidden="true" />
              Map
            </a>
          )}
          {sourceLink && (
            <a
              href={sourceLink}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`View source for ${title}`}
              className="inline-flex items-center gap-1.5 rounded-lg bg-ds-carbon text-ds-text-tertiary hover:bg-ds-pen-stroke hover:text-ds-text transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
              style={{
                padding: "var(--ds-space-2) var(--ds-space-3)",
                fontSize: "var(--ds-type-body-s-size)",
              }}
            >
              <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              Source
            </a>
          )}
          {!onSave && !mapLink && !sourceLink && (
            <span
              className="text-ds-text-tertiary"
              style={{ fontSize: "var(--ds-type-caption-size)" }}
            >
              Research only
            </span>
          )}
        </div>
      </div>
    </Card>
  );
}

// ─── Generic starter prompts — no hardcoded destinations ─────────────────────
// Chips populate the query input only; they never auto-set destination or
// auto-submit. The concierge must not pretend to know the user's city.

const EDITORIAL_PROMPTS = [
  "Cocktail bars with a view",
  "Design-forward boutique hotels",
  "A romantic dinner",
  "Hidden neighbourhood gems",
  "Best neighbourhood to stay",
  "Local breakfast worth the walk",
] as const;

// ─── localStorage transcript persistence ──────────────────────────────────────

const TRANSCRIPT_KEY = "concierge_outside_trip_transcript_v1";

function loadPersistedTranscript(): Message[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(TRANSCRIPT_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed as Message[];
  } catch {
    return [];
  }
}

function saveTranscript(msgs: Message[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(TRANSCRIPT_KEY, JSON.stringify(msgs));
  } catch {
    // storage quota exceeded or unavailable — silently skip
  }
}

// ─── Main ConciergePage ───────────────────────────────────────────────────────

export function ConciergePage() {
  // Lazy initializers run once at mount from localStorage. This prevents the
  // save-effect race where messages=[] is written to storage before the load
  // completes when the component re-mounts with a non-empty persisted transcript.
  const [messages, setMessages] = useState<Message[]>(loadPersistedTranscript);
  const [lastQuery, setLastQuery] = useState<string | null>(() => {
    const persisted = loadPersistedTranscript();
    return [...persisted].reverse().find((m) => m.role === "user")?.text ?? null;
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [destination, setDestination] = useState("");
  const [destinationError, setDestinationError] = useState(false);
  // Save state per card, keyed by a stable identifier (providerPlaceId or title)
  const [cardSaveStates, setCardSaveStates] = useState<Map<string, SaveState>>(new Map());
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Salon world — portal mood is a pure function of the typed destination via
  // pickWorldFromDestination → applyRoom("salon"). No regex, no hardcoded list.
  // If destination is empty, the salon archetype default mood is shown.
  const salonWorld = useMemo(
    () => applyRoom(pickWorldFromDestination(destination || null), "salon"),
    [destination],
  );

  // Persist transcript whenever messages change
  useEffect(() => {
    saveTranscript(messages);
  }, [messages]);

  function clearTranscript() {
    setMessages([]);
    setLastQuery(null);
    setError(null);
    if (typeof window !== "undefined") {
      try { window.localStorage.removeItem(TRANSCRIPT_KEY); } catch { /* ignore */ }
    }
  }

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  // Refinement chips shown after cards are present
  const refinementChips = useMemo(() => {
    const latestCardMsg = getLatestCardMessage(messages);
    if (!latestCardMsg) return null;
    const currentCards = [
      ...(latestCardMsg.restaurants ?? []),
      ...(latestCardMsg.attractions ?? []),
      ...(latestCardMsg.hotels ?? []),
    ].filter(isRenderableVerifiedPlace);
    const cheaperChip = hasGooglePriceSignals(currentCards)
      ? "Find cheaper nearby"
      : "Find more like these";
    return ["Show only casual", "Compare top 2", cheaperChip];
  }, [messages]);

  // Follow-up chips based on last assistant intent
  const followUpChips = useMemo(() => {
    const lastIntent = [...messages]
      .reverse()
      .find((m) => m.role === "assistant")?.intent;
    if (
      lastIntent &&
      [
        "michelin_restaurants",
        "restaurants",
        "hidden_gems",
        "romantic",
        "luxury_value",
      ].includes(lastIntent)
    ) {
      return ["Michelin / tasting menus", "Best value dinner", "Nearby cocktail bars"];
    }
    if (lastIntent === "hotels") {
      return ["Compare areas", "Luxury with value", "Find more options"];
    }
    if (lastIntent && ["attractions", "plan_day"].includes(lastIntent)) {
      return ["Rainy day plan", "Kid-friendly options", "Nearby restaurants"];
    }
    return null;
  }, [messages]);

  const activeChips = refinementChips ?? followUpChips;

  // ── Save a concierge result card to Saved Ideas ─────────────────────────────
  const handleSaveCard = useCallback(async (
    cardKey: string,
    vertical: "restaurant" | "attraction" | "hotel",
    title: string,
    place: unknown
  ) => {
    setCardSaveStates((prev) => new Map(prev).set(cardKey, "saving"));
    try {
      const p = place as Record<string, unknown>;
      const gv = p.googleVerification as Record<string, unknown> | undefined;
      const disp = p.display as Record<string, unknown> | undefined;
      const providerPlaceId = (gv?.providerPlaceId ?? gv?.provider_place_id) as string | undefined;
      if (!providerPlaceId) throw new Error("no providerPlaceId — cannot save without canonical identifier");
      const googleMapsUri = (gv?.googleMapsUri ?? gv?.google_maps_uri) as string | undefined;
      const rating = (p.rating ?? gv?.rating) as number | undefined;
      const address = (p.address ?? p.neighborhood ?? disp?.address) as string | undefined;
      const category = (p.category ?? disp?.displayCategory ?? vertical) as string;
      const cuisine = (p.cuisine ?? disp?.cuisine) as string | undefined;
      const priceLevel = (p.priceLevel ?? p.price_level ?? disp?.priceLevel ?? disp?.price_level) as string | undefined;
      const tags = (p.tags ?? disp?.tags) as string[] | undefined;

      await saveItem({
        vertical,
        displayName: title,
        provider: "google_places",
        providerPlaceId,
        displaySnapshot: {
          name: title,
          destination,
          category,
          cuisine,
          rating,
          priceLevel,
          address,
          googleMapsUri,
          tags,
        },
        searchContext: { destination, query: lastQuery ?? "" },
        provenance: { source: "outside_concierge" },
      });
      setCardSaveStates((prev) => new Map(prev).set(cardKey, "saved"));
    } catch {
      setCardSaveStates((prev) => new Map(prev).set(cardKey, "error"));
    }
  }, [destination, lastQuery]);

  const hasResults = messages.some(
    (m) =>
      m.role === "assistant" &&
      ((m.restaurants?.length ?? 0) > 0 ||
        (m.attractions?.length ?? 0) > 0 ||
        (m.hotels?.length ?? 0) > 0),
  );

  function getCardsWithKind(msg: Message) {
    return [
      ...(msg.restaurants ?? [])
        .filter(isRenderableVerifiedPlace)
        .map((place) => ({ kind: "restaurant" as const, place })),
      ...(msg.attractions ?? [])
        .filter(isRenderableVerifiedPlace)
        .map((place) => ({ kind: "attraction" as const, place })),
      ...(msg.hotels ?? [])
        .filter(isRenderableVerifiedPlace)
        .map((place) => ({ kind: "hotel" as const, place })),
    ];
  }

  async function sendQuery(query: string, destOverride?: string) {
    if (!query.trim() || loading) return;
    const effectiveDest = (destOverride ?? destination).trim();
    if (!effectiveDest) {
      setDestinationError(true);
      return;
    }
    setDestinationError(false);
    const requestId =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    setInput("");
    setLastQuery(query.trim());
    setError(null);
    setMessages((prev) => [...prev, { role: "user", text: query.trim() }]);
    setLoading(true);
    try {
      const result = await callConciergeSearch(null, query.trim(), requestId, effectiveDest);
      setMessages((prev) => [...prev, fromSearchResult(result)]);
    } catch (err) {
      console.error("[concierge-page] search failed", err);
      setError(
        "The concierge is temporarily unavailable. Please try again in a moment.",
      );
    } finally {
      setLoading(false);
      setTimeout(scrollToBottom, 100);
    }
  }

  async function handleUserInput(query: string, destOverride?: string) {
    const q = query.trim();
    if (!q || loading) return;
    const latestCardMsg = getLatestCardMessage(messages);
    if (latestCardMsg && !looksLikeFreshSearch(q)) {
      const handled = await handleRefinement(q, latestCardMsg);
      if (!handled) await sendQuery(q, destOverride);
    } else {
      await sendQuery(q, destOverride);
    }
  }

  async function handleRefinement(
    query: string,
    latestCardMsg: Message,
  ): Promise<boolean> {
    const cardsWithKind = getCardsWithKind(latestCardMsg);
    const action = parseRefinementAction(
      query,
      cardsWithKind.map((c) => c.place),
    ) as {
      type: string;
      modifier?: string;
      dayNumber?: number | null;
      isTemporal?: boolean;
      clarificationText?: string;
    };

    if (action.type === ACTION.CLARIFY_UNSUPPORTED) return false;

    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", text: query }]);

    // ADD_SELECTED_TO_DAY: no trip context on standalone page
    if (action.type === ACTION.ADD_SELECTED_TO_DAY) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "To add a place to your itinerary, open your trip from My Trips and use the AI Concierge there.",
          isRefinement: true,
          refinementAction: ACTION.ADD_SELECTED_TO_DAY,
          restaurants: [],
          attractions: [],
          hotels: [],
          researchSources: [],
          areaComparisons: [],
        },
      ]);
      return true;
    }

    if (action.type === ACTION.SEARCH_MORE_WITH_CONTEXT) {
      const isCheaperQuery =
        /\bcheap(er)?\b|\bbudget\b|\baffordable\b|\blower[- ]price\b/i.test(
          query,
        );
      const currentVisibleCards = cardsWithKind.map((c) => c.place);
      if (isCheaperQuery && !hasGooglePriceSignals(currentVisibleCards)) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            text: "No Google price signals for these places yet. Try \"Find more like these\" to search for additional venues.",
            isRefinement: true,
            refinementAction: ACTION.SEARCH_MORE_WITH_CONTEXT,
            restaurants: [],
            attractions: [],
            hotels: [],
            researchSources: [],
            areaComparisons: [],
          },
        ]);
        return true;
      }
      const contextualQuery = buildContextualSearchQuery(
        lastQuery ?? query,
        query,
        {},
      );
      setLoading(true);
      try {
        const requestId =
          typeof crypto !== "undefined" && "randomUUID" in crypto
            ? crypto.randomUUID()
            : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
        const result = await callConciergeSearch(null, contextualQuery, requestId, destination.trim() || undefined);
        const deduped = dedupeCardsAgainstCurrentSet(
          fromSearchResult(result),
          currentVisibleCards,
        ) as Message & { allDuplicates: boolean };
        if (deduped.allDuplicates) {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              text: "Mostly the same top options. Try specifying a different neighbourhood or vibe.",
              isRefinement: true,
              refinementAction: ACTION.SEARCH_MORE_WITH_CONTEXT,
              restaurants: [],
              attractions: [],
              hotels: [],
              researchSources: [],
              areaComparisons: [],
            },
          ]);
        } else {
          setMessages((prev) => [...prev, deduped]);
        }
      } catch (err) {
        console.error("[concierge-page] refinement search failed", err);
        setError(
          "The concierge is temporarily unavailable. Please try again.",
        );
      } finally {
        setLoading(false);
        setTimeout(scrollToBottom, 100);
      }
      return true;
    }

    // FILTER, REMOVE, RERANK, COMPARE — applied locally
    const synthetic = applyRefinementToMessage(action, latestCardMsg);
    if (!synthetic) {
      const contextualQuery = buildContextualSearchQuery(
        lastQuery ?? query,
        query,
        {},
      );
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: `No matches for "${action.modifier ?? query}" in the current set. Searching for more…`,
          isRefinement: true,
          refinementAction: action.type,
          restaurants: [],
          attractions: [],
          hotels: [],
          researchSources: [],
          areaComparisons: [],
        },
      ]);
      setLoading(true);
      try {
        const requestId =
          typeof crypto !== "undefined" && "randomUUID" in crypto
            ? crypto.randomUUID()
            : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
        const result = await callConciergeSearch(null, contextualQuery, requestId, destination.trim() || undefined);
        setMessages((prev) => [...prev, fromSearchResult(result)]);
      } catch (err) {
        console.error("[concierge-page] refinement fallback failed", err);
        setError("The concierge is temporarily unavailable. Please try again.");
      } finally {
        setLoading(false);
        setTimeout(scrollToBottom, 100);
      }
      return true;
    }

    setMessages((prev) => [...prev, synthetic as Message]);
    setTimeout(scrollToBottom, 100);
    return true;
  }

  // ── Render ───────────────────────────────────────────────────────────────────
  // Portal mode derived from existing state — no new state needed.
  // "open": pre-search (no messages, no lastQuery) — portal fills the stage.
  // "tuned": post-search — portal collapses to a banner above the result canvas.
  const portalMode = (messages.length === 0 && !lastQuery) ? "open" : "tuned";

  return (
    <div
      data-testid="concierge-page"
      className="flex flex-col atelier-transition atelier-salon-page atelier-salon-room atelier-salon-stage-room"
      data-world-location={salonWorld.location}
      data-scenery-tone={salonWorld.visualLayer.contrastTone ?? "dark"}
      style={worldStyleVars(salonWorld)}
    >
      {/* Salon ambient layer — destination-aware when a city is typed.
          WorldAtmosphere sits at z-index:-1 within the atelier-salon-room
          stacking context, behind all in-flow content. */}
      <WorldAtmosphere />

      {/* Workbench — two-column grid on desktop (main panel + briefing rail).
          CSS owns the grid / flex layout; Tailwind mx-auto centers the column. */}
      <div className="atelier-salon-workbench mx-auto">

        {/* ── Main stage panel ──────────────────────────────────────────── */}
        <div
          className="atelier-salon-main-panel atelier-salon-stage-panel"
          data-portal-state={portalMode}
        >

          {/* ── THE PORTAL — emotional centerpiece ────────────────────────
              portal mood is driven by the typed destination via
              pickWorldFromDestination → applyRoom("salon") → worldStyleVars.
              No fake regex, no demo SCENES map. */}
          <section
            className="atelier-salon-portal"
            data-portal-state={portalMode}
            aria-label="Concierge stage"
          >
            {/* Scene layer — WorldScenery reads --world-scenery / --world-scenery-image
                from the salon world CSS vars. Fills the portal frame via CSS override. */}
            <WorldScenery className="atelier-salon-portal-scene" />

            {/* Depth layers — decorative atmosphere, pointer-events: none */}
            <span className="atelier-salon-portal-haze" aria-hidden="true" />
            <span className="atelier-salon-portal-bloom" aria-hidden="true" />
            <span className="atelier-salon-portal-grain" aria-hidden="true" />
            <span className="atelier-salon-portal-vignette" aria-hidden="true" />

            {/* Portal copy — all readable content sits ABOVE the depth layers */}
            <div className="atelier-salon-portal-copy">
              <header
                data-testid="concierge-instrument-header"
                className="atelier-salon-room-header atelier-salon-panel-header atelier-salon-header-landing pb-5 sm:pb-8"
              >
                <p
                  className="uppercase tracking-[0.1em]"
                  style={{
                    fontSize: "var(--ds-type-overline-size)",
                    lineHeight: "var(--ds-type-overline-leading)",
                    fontWeight: "var(--ds-type-overline-weight)",
                    color: "var(--ds-ember-brass)",
                  }}
                >
                  Private Travel Concierge
                </p>
                <h1
                  className="atelier-salon-portal-headline"
                  style={{
                    fontSize: "var(--ds-type-display-s-size)",
                    lineHeight: "var(--ds-type-display-s-leading)",
                    fontWeight: "var(--ds-type-display-s-weight)",
                    letterSpacing: "var(--ds-type-display-s-tracking)",
                    marginTop: "var(--ds-space-2)",
                  }}
                >
                  {lastQuery ? `"${lastQuery}"` : "What can I find for you?"}
                </h1>
                {portalMode === "open" && (
                  <p
                    className="atelier-salon-portal-subline"
                    style={{
                      fontSize: "var(--ds-type-body-size)",
                      lineHeight: "var(--ds-type-body-leading)",
                      maxWidth: "38ch",
                      marginTop: "var(--ds-space-3)",
                    }}
                  >
                    Describe a mood, a neighbourhood, or an occasion.
                    <br />
                    I surface verified places worth your time.
                  </p>
                )}
              </header>

              {/* Editorial mapline — visual rhythm between header and invitations */}
              {portalMode === "open" && (
                <div className="mapline-rule mx-auto" aria-hidden="true" />
              )}

              {/* Pre-search invitations — inside portal copy, never in the canvas */}
              {portalMode === "open" && (
                <div
                  data-testid="concierge-empty-state"
                  className="atelier-salon-invitation"
                >
                  <p
                    className="text-center uppercase tracking-[0.1em]"
                    style={{
                      fontSize: "var(--ds-type-overline-size)",
                      lineHeight: "var(--ds-type-overline-leading)",
                      fontWeight: "var(--ds-type-overline-weight)",
                      marginBottom: "var(--ds-space-5)",
                      color: "color-mix(in srgb, var(--ds-pearl-cream) 70%, transparent)",
                    }}
                  >
                    Starting points — tell me where to search:
                  </p>
                  <div className="atelier-salon-chip-grid">
                    {EDITORIAL_PROMPTS.map((prompt) => (
                      <button
                        key={prompt}
                        type="button"
                        onClick={() => {
                          setInput(prompt);
                          inputRef.current?.focus();
                        }}
                        className="rounded-lg folio-concierge-chip atelier-salon-starter-chip focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2 min-h-[44px]"
                        style={{
                          padding: "var(--ds-space-3) var(--ds-space-4)",
                          fontSize: "var(--ds-type-body-s-size)",
                          lineHeight: "var(--ds-type-body-s-leading)",
                          textAlign: "center",
                        }}
                        data-testid="concierge-prompt-chip"
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </section>

          {/* ── Results canvas — transcript/loading/error only ────────────
              Empty pre-search so the portal fills the panel.
              Becomes the only scrollable region post-search. */}
          <main
            data-testid="concierge-results-canvas"
            aria-label="Concierge results"
            aria-live="polite"
            aria-atomic="false"
            className="atelier-salon-panel-body"
          >
            {/* Messages — transcript: user turns + assistant card groups */}
            <div className="space-y-4">
              {messages.map((msg, idx) => {
                // User turn: quiet query marker — not a chat bubble.
                if (msg.role === "user") {
                  return (
                    <div
                      key={idx}
                      data-testid="concierge-user-query"
                      className="border-l-2 pl-3 my-2 atelier-salon-user-turn"
                    >
                      <p
                        className="italic"
                        style={{
                          fontSize: "var(--ds-type-body-s-size)",
                          lineHeight: "var(--ds-type-body-s-leading)",
                          wordBreak: "break-word",
                          color: "var(--world-ink-mist)",
                        }}
                      >
                        {msg.text}
                      </p>
                    </div>
                  );
                }

                // Refinement text-only note (no cards)
                if (
                  msg.isRefinement &&
                  !(msg.restaurants?.length) &&
                  !(msg.attractions?.length) &&
                  !(msg.hotels?.length)
                ) {
                  return (
                    <p
                      key={idx}
                      style={{
                        fontSize: "var(--ds-type-body-s-size)",
                        lineHeight: "var(--ds-type-body-s-leading)",
                        paddingTop: "var(--ds-space-2)",
                        color: "var(--world-ink-mist)",
                      }}
                    >
                      {msg.text}
                    </p>
                  );
                }

                // Card result message
                const addablePlaces = [
                  ...(msg.restaurants ?? [])
                    .filter(isRenderableVerifiedPlace)
                    .map((place) => ({
                      kind: "restaurant" as const,
                      place,
                      sourceLink:
                        (place as { bookingLink?: string }).bookingLink ??
                        (place as { sourceUrl?: string }).sourceUrl,
                    })),
                  ...(msg.attractions ?? [])
                    .filter(isRenderableVerifiedPlace)
                    .map((place) => ({
                      kind: "attraction" as const,
                      place,
                      sourceLink: (place as { sourceUrl?: string }).sourceUrl,
                    })),
                  ...(msg.hotels ?? [])
                    .filter(isRenderableVerifiedPlace)
                    .map((place) => ({
                      kind: "hotel" as const,
                      place,
                      sourceLink:
                        (place as { bookingUrl?: string }).bookingUrl ??
                        (place as { sourceUrl?: string }).sourceUrl,
                    })),
                ];

                if (addablePlaces.length === 0) return null;

                const allTitles = addablePlaces.map(
                  ({ place }) =>
                    (place as { display?: { displayName?: string } }).display
                      ?.displayName ??
                    (place as { name?: string }).name ??
                    "",
                );

                return (
                  <section key={idx} data-testid="concierge-result-section" aria-label="Place recommendations">
                    <div className="space-y-3">
                      {addablePlaces.map(({ kind, place, sourceLink }) => {
                        const title =
                          (place as { display?: { displayName?: string } }).display
                            ?.displayName ??
                          (place as { name?: string }).name ??
                          "";
                        const category = pickCardCategory(place);
                        const baseReason = pickCardReason(place);
                        const reason = sanitizeWhyPick(baseReason, title, allTitles);
                        const conciergeNote = (
                          place as {
                            supportingDetails?: { conciergeNote?: string };
                          }
                        ).supportingDetails?.conciergeNote;
                        const extraDetail = conciergeNote ? [conciergeNote] : [];
                        const isClosed = hasClosedSignal(
                          place as ClosedSignalSource,
                        );
                        const isOperational =
                          !isClosed &&
                          canShowGoogleVerifiedBadge(
                            place as OperationalBadgeCard,
                          );
                        const rawConfidence = (
                          place as { googleVerification?: { confidence?: string } }
                        ).googleVerification?.confidence?.toLowerCase();
                        const operationalConfidence =
                          isOperational &&
                          (rawConfidence === "high" || rawConfidence === "medium")
                            ? (rawConfidence as TrustConfidence)
                            : undefined;
                        const meta = pickCardMeta(place as DisplayCard);
                        const mapLink =
                          (
                            place as {
                              googleVerification?: { googleMapsUri?: string };
                            }
                          ).googleVerification?.googleMapsUri ??
                          (place as { mapsLink?: string }).mapsLink;

                        // Stable card key: prefer providerPlaceId, fall back to title
                        const placeId = (
                          (place as { googleVerification?: { providerPlaceId?: string } }).googleVerification?.providerPlaceId
                        );
                        const cardKey = placeId ?? title;
                        const isSaveable = isAddableCanonicalCard(place);

                        return (
                          <ConciergeResultCard
                            key={cardKey}
                            title={title}
                            category={category}
                            meta={meta}
                            reason={reason}
                            extraDetail={extraDetail}
                            mapLink={mapLink}
                            sourceLink={sourceLink}
                            isOperational={isOperational}
                            operationalConfidence={operationalConfidence}
                            onSave={isSaveable ? () => handleSaveCard(cardKey, kind, title, place) : undefined}
                            saveState={cardSaveStates.get(cardKey) ?? "idle"}
                          />
                        );
                      })}
                    </div>

                    {/* Collapsed sources — only when verified cards + research sources coexist */}
                    {shouldShowCollapsedSources(msg) && (
                      <details
                        className="rounded-lg"
                        style={{
                          border: "1px solid var(--ds-pen-stroke)",
                          background: "var(--ds-onyx-velvet)",
                          marginTop: "var(--ds-space-3)",
                        }}
                      >
                        <summary
                          className="cursor-pointer text-ds-text-tertiary uppercase tracking-[0.1em]"
                          style={{
                            padding: "var(--ds-space-3) var(--ds-space-4)",
                            fontSize: "var(--ds-type-overline-size)",
                            fontWeight: "var(--ds-type-overline-weight)",
                          }}
                        >
                          Sources (
                          {msg.researchSources?.filter(
                            (s) => s.type === "research_source",
                          ).length ?? 0}
                          )
                        </summary>
                        <ul
                          style={{
                            padding:
                              "0 var(--ds-space-4) var(--ds-space-3) var(--ds-space-4)",
                          }}
                          className="space-y-1"
                        >
                          {msg.researchSources
                            ?.filter((s) => s.type === "research_source")
                            .map((s) => (
                              <li key={`${s.title}-${s.sourceUrl ?? "source"}`}>
                                {s.sourceUrl ? (
                                  <a
                                    href={s.sourceUrl}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-ds-accent hover:text-ds-text transition-colors duration-[120ms] truncate block focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                                    style={{
                                      fontSize: "var(--ds-type-caption-size)",
                                      lineHeight: "var(--ds-type-caption-leading)",
                                    }}
                                  >
                                    {s.title}
                                  </a>
                                ) : (
                                  <span
                                    className="text-ds-text-tertiary"
                                    style={{
                                      fontSize: "var(--ds-type-caption-size)",
                                    }}
                                  >
                                    {s.title}
                                  </span>
                                )}
                              </li>
                            ))}
                        </ul>
                      </details>
                    )}

                    {/* Warnings */}
                    {(msg.warnings?.length ?? 0) > 0 && (
                      <div
                        className="space-y-2"
                        style={{ marginTop: "var(--ds-space-3)" }}
                      >
                        {msg.warnings?.map((warning, i) => (
                          <div
                            key={i}
                            className="flex items-start gap-2 rounded-lg"
                            style={{
                              border: "1px solid var(--ds-caution-amber)",
                              background: "color-mix(in srgb, var(--ds-caution) 10%, transparent)",
                              padding: "var(--ds-space-3) var(--ds-space-4)",
                            }}
                          >
                            <AlertTriangle
                              className="h-3.5 w-3.5 shrink-0 text-ds-caution mt-0.5"
                              aria-hidden="true"
                            />
                            <p
                              className="text-ds-text-secondary"
                              style={{ fontSize: "var(--ds-type-body-s-size)" }}
                            >
                              {warning}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </section>
                );
              })}
            </div>

            {/* Loading state — honest staged text, no fake progress */}
            {loading && (
              <div
                data-testid="concierge-loading-state"
                className="flex items-center gap-3"
                style={{ marginTop: "var(--ds-space-6)" }}
                role="status"
                aria-live="polite"
              >
                <Loader2
                  className="h-4 w-4 animate-spin text-ds-accent shrink-0"
                  aria-hidden="true"
                />
                <p style={{ fontSize: "var(--ds-type-body-s-size)", color: "var(--world-ink-mist)" }}>
                  <span style={{ color: "var(--world-ink)" }}>Searching</span>
                  <span className="mx-2">·</span>
                  <span>Verifying</span>
                  <span className="mx-2">·</span>
                  <span>Composing</span>
                </p>
              </div>
            )}

            {/* Error state — named constraint + retry */}
            {error && !loading && (
              <div
                data-testid="concierge-error-state"
                className="flex items-start gap-3 rounded-lg"
                style={{
                  border: "1px solid var(--ds-warning)",
                  background: "color-mix(in srgb, var(--ds-warning) 10%, transparent)",
                  padding: "var(--ds-space-4)",
                  marginTop: "var(--ds-space-5)",
                }}
                role="alert"
              >
                <AlertTriangle
                  className="h-4 w-4 shrink-0 text-ds-warning"
                  style={{ marginTop: "2px" }}
                  aria-hidden="true"
                />
                <div>
                  <p
                    className="text-ds-warning"
                    style={{
                      fontSize: "var(--ds-type-body-s-size)",
                      lineHeight: "var(--ds-type-body-s-leading)",
                    }}
                  >
                    {error}
                  </p>
                  {lastQuery && (
                    <button
                      type="button"
                      onClick={() => {
                        setError(null);
                        sendQuery(lastQuery);
                      }}
                      className="text-ds-accent hover:text-ds-text transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                      style={{
                        fontSize: "var(--ds-type-body-s-size)",
                        marginTop: "var(--ds-space-2)",
                        display: "block",
                      }}
                    >
                      Try again
                    </button>
                  )}
                </div>
              </div>
            )}

            <div ref={bottomRef} style={{ height: "var(--ds-space-1)" }} />
          </main>

          {/* ── THE DESK — fused to portal/stage base ─────────────────────
              The atelier-salon-composer-surface::before brass hairline joins
              the canvas/portal to the desk without a visible gap. */}
          <div
            data-testid="concierge-instrument-composer"
            className="sticky z-10 concierge-sticky-bottom folio-cinema-composer atelier-salon-composer-surface atelier-salon-desk"
          >
            {/* Refinement / follow-up chips */}
            {activeChips && messages.length > 0 && !loading && (
              <div
                className="flex gap-2 overflow-x-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]"
                style={{
                  padding:
                    "var(--ds-space-3) var(--ds-space-4) 0 var(--ds-space-4)",
                }}
              >
                {activeChips.map((chip) => (
                  <button
                    key={chip}
                    type="button"
                    onClick={() => handleUserInput(chip)}
                    className="shrink-0 rounded-lg bg-ds-carbon text-ds-text-tertiary hover:bg-ds-pen-stroke hover:text-ds-text transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                    style={{
                      padding: "var(--ds-space-2) var(--ds-space-3)",
                      fontSize: "var(--ds-type-body-s-size)",
                      border: "1px solid var(--ds-pen-stroke)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {chip}
                  </button>
                ))}
              </div>
            )}

            {/* Destination field — visible label for instrument clarity */}
            <div
              data-testid="concierge-destination-field"
              style={{
                padding: "var(--ds-space-3) var(--ds-space-4) 0 var(--ds-space-4)",
              }}
            >
              <label
                htmlFor="concierge-destination"
                className="text-ds-text-tertiary uppercase tracking-[0.1em]"
                style={{
                  display: "block",
                  fontSize: "var(--ds-type-overline-size)",
                  fontWeight: "var(--ds-type-overline-weight)",
                  lineHeight: "var(--ds-type-overline-leading)",
                  marginBottom: "var(--ds-space-1)",
                }}
              >
                Where
              </label>
              <div
                className="flex items-center gap-2 rounded-xl bg-ds-carbon transition-colors duration-[120ms] folio-mapline-field"
                style={{
                  border: destinationError
                    ? "1px solid var(--ds-warning)"
                    : "1px solid var(--ds-brass-field-border)",
                  padding: "var(--ds-space-2) var(--ds-space-4)",
                  minHeight: "44px",
                }}
              >
                <MapPin
                  className="h-3.5 w-3.5 shrink-0 text-ds-accent"
                  aria-hidden="true"
                />
                <input
                  id="concierge-destination"
                  type="text"
                  value={destination}
                  onChange={(e) => {
                    setDestination(e.target.value);
                    if (destinationError && e.target.value.trim()) setDestinationError(false);
                  }}
                  placeholder="Tokyo, Paris, Barcelona…"
                  disabled={loading}
                  className="flex-1 bg-transparent text-ds-text placeholder:text-ds-text-tertiary focus-visible:outline-none disabled:opacity-50"
                  style={{
                    fontSize: "var(--ds-type-body-size)",
                    lineHeight: "var(--ds-type-body-leading)",
                  }}
                />
              </div>
              {destinationError && (
                <p
                  className="text-ds-text-secondary"
                  style={{
                    fontSize: "var(--ds-type-caption-size)",
                    lineHeight: "var(--ds-type-caption-leading)",
                    marginTop: "var(--ds-space-2)",
                  }}
                >
                  Add a destination so the concierge knows where to search.
                </p>
              )}
            </div>

            {/* Input row — instrument search entry */}
            <div
              className="flex items-end gap-3"
              style={{
                padding: "var(--ds-space-3) var(--ds-space-4) var(--ds-space-4)",
              }}
            >
              {/* Clear-chat — only shown when transcript has messages */}
              {messages.length > 0 && !loading && (
                <button
                  type="button"
                  onClick={clearTranscript}
                  aria-label="Clear search history"
                  title="Clear search history"
                  data-testid="concierge-clear-chat"
                  className="shrink-0 rounded-xl bg-ds-carbon text-ds-text-tertiary hover:bg-ds-pen-stroke hover:text-ds-text transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                  style={{
                    padding: "var(--ds-space-3)",
                    minWidth: "44px",
                    minHeight: "44px",
                    border: "1px solid var(--ds-pen-stroke)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                </button>
              )}
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  e.target.style.height = "auto";
                  e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void handleUserInput(input.trim());
                  }
                }}
                placeholder="What can I find for you?"
                disabled={loading}
                rows={1}
                aria-label="Concierge query"
                data-testid="concierge-query-input"
                className="flex-1 resize-none rounded-xl bg-ds-carbon text-ds-text placeholder:text-ds-text-tertiary border border-ds-pen-stroke hover:border-ds-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-1 disabled:opacity-50 transition-colors duration-[120ms]"
                style={{
                  padding: "var(--ds-space-3) var(--ds-space-4)",
                  fontSize: "var(--ds-type-body-size)",
                  lineHeight: "var(--ds-type-body-leading)",
                  minHeight: "44px",
                }}
              />
              <button
                type="button"
                onClick={() => void handleUserInput(input.trim())}
                disabled={loading || !input.trim()}
                aria-label="Submit query"
                data-testid="concierge-submit-button"
                className="shrink-0 rounded-xl text-ds-text-inverse disabled:opacity-40 transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2 hover:brightness-110"
                style={{
                  background: "var(--ds-accent)",
                  padding: "var(--ds-space-3)",
                  minWidth: "44px",
                  minHeight: "44px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                ) : (
                  <Send className="h-4 w-4" aria-hidden="true" />
                )}
              </button>
            </div>
          </div>

        </div> {/* end atelier-salon-main-panel / atelier-salon-stage-panel */}

        {/* ── Atelier briefing rail — static capability affordances ──────────
            Desktop only (hidden on mobile via CSS). No live data, no counts.
            Declares concierge capabilities as warm editorial copy. */}
        <aside className="atelier-salon-briefing-rail" aria-label="Concierge capabilities">
          <div className="atelier-salon-briefing-header">
            <p
              className="uppercase tracking-[0.1em]"
              style={{
                fontSize: "var(--ds-type-overline-size)",
                fontWeight: "var(--ds-type-overline-weight)",
                lineHeight: "var(--ds-type-overline-leading)",
                color: "var(--world-ink-mist)",
              }}
            >
              How I can help
            </p>
          </div>
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {[
              "Find verified places",
              "Compare neighbourhoods",
              "Shape a date night",
              "Turn ideas into saved cards",
              "Refine a trip itinerary",
              "Discover hidden gems",
            ].map((item) => (
              <li key={item} className="atelier-salon-briefing-item">
                <span
                  aria-hidden="true"
                  style={{
                    color: "var(--ds-ember-brass)",
                    fontSize: "var(--ds-type-body-s-size)",
                    lineHeight: "1",
                    marginTop: "3px",
                    flexShrink: 0,
                  }}
                >
                  ›
                </span>
                <span
                  style={{
                    fontSize: "var(--ds-type-body-s-size)",
                    lineHeight: "var(--ds-type-body-s-leading)",
                    color: "var(--world-ink)",
                  }}
                >
                  {item}
                </span>
              </li>
            ))}
          </ul>
          <div className="atelier-salon-briefing-footer">
            {[
              "Verified Google-backed cards",
              "Save or add to trip",
              "Maps-ready places",
            ].map((badge) => (
              <p
                key={badge}
                style={{
                  fontSize: "var(--ds-type-caption-size)",
                  lineHeight: "var(--ds-type-caption-leading)",
                  color: "var(--world-ink-mist)",
                }}
              >
                {badge}
              </p>
            ))}
          </div>
        </aside>

      </div> {/* end atelier-salon-workbench */}
    </div>
  );
}
