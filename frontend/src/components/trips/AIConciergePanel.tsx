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

type MessageRole = "user" | "assistant";

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
}

interface Props {
  tripId: string;
  destination: string;
  tripDays?: ItineraryDay[];
  isOpen: boolean;
  onClose: () => void;
  onItemAdded?: () => void;
}

const CONCIERGE_CACHE_VERSION = 2;
const CLOSED_SIGNAL_PATTERNS = [
  "permanently closed",
  "closed permanently",
  "closed for good",
  "closed for the final time",
  "has closed",
  "is closed",
  "shut down",
  "no longer open",
  "won't reopen",
  "will not reopen",
];

interface ConciergeClientCacheEntry {
  version: number;
  tripId: string;
  destination: string;
  messages: Message[];
}

type ClosedSignalCard = Partial<{
  name: string | null;
  title: string | null;
  summary: string | null;
  description: string | null;
  reason: string | null;
  source: string | null;
  sourceText: string | null;
  rawText: string | null;
  url: string | null;
  sourceUrl: string | null;
  snippet: string | null;
  raw: unknown;
}>;

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
  if (status === "sample_data") return "Sample bar research data · verify hours and current status before booking.";
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
    return "Sample bar research data · verify hours and current status before booking.";
  }
  return sourceLabel(msg.sourceStatus ?? "", msg.intent, msg.liveProvider, msg.cached);
}

function formatVerifiedAt(iso?: string): string | null {
  if (!iso) return null;
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return null;
  const days = Math.max(0, Math.round((Date.now() - dt.getTime()) / (24 * 60 * 60 * 1000)));
  // Tavily / Brave / Serper sources only show "source checked …" — never a
  // same-day freshness claim, which is reserved for Google Places.
  if (days < 1) return "source checked";
  if (days === 1) return "source checked 1 day ago";
  if (days < 30) return `source checked ${days} days ago`;
  const months = Math.round(days / 30);
  if (months < 12) return `source checked ${months} mo ago`;
  return `source checked ${Math.round(months / 12)} yr ago`;
}

function cardKey(name: string, dayId?: string): string {
  return `${name.trim().toLowerCase()}::${dayId ?? "trip"}`;
}

function normalizeTitle(value: string): string {
  return value.trim().toLowerCase();
}

function splitReason(text?: string): { short: string; detail?: string } {
  const clean = (text ?? "")
    .replace(/#{1,6}\s*/g, " ")
    .replace(/^\s*(?:\d{1,3}[.)]|[-*])\s+/g, "")
    .replace(/\s+/g, " ")
    .trim();
  if (!clean) return { short: "Great fit for this trip." };
  const parts = clean.split(/(?<=[.!?])\s+/);
  return {
    short: parts.slice(0, 1).join(" "),
    detail: parts.length > 1 ? parts.slice(1).join(" ") : undefined,
  };
}

interface OperationalBadgeCard {
  source?: string | null;
  sourceUrl?: string | null;
  verifiedPlace?: boolean | null;
  confidence?: string | null;
  lastVerifiedAt?: string | null;
  googleVerification?: {
    businessStatus?: string | null;
    confidence?: string | null;
    providerPlaceId?: string | null;
  } | null;
}

// Only Google-verified OPERATIONAL venues get the "Google verified" badge.
// Tavily/Serper/Brave alone — even with a source URL — never qualify.
function canShowGoogleVerifiedBadge(card: OperationalBadgeCard): boolean {
  if (hasClosedSignal(card)) return false;
  const gv = card.googleVerification;
  if (!gv) return false;
  if (gv.businessStatus !== "OPERATIONAL") return false;
  const gvConfidence = (gv.confidence ?? "").toLowerCase();
  if (gvConfidence !== "high" && gvConfidence !== "medium") return false;
  if (!gv.providerPlaceId) return false;
  return true;
}

function hasClosedSignal(card: ClosedSignalCard): boolean {
  const textBlob = [
    card.name,
    card.title,
    card.summary,
    card.description,
    card.reason,
    card.source,
    card.sourceText,
    card.rawText,
    card.url,
    card.sourceUrl,
    card.snippet,
    card.raw,
  ]
    .map((value) => String(value ?? "").toLowerCase())
    .join("\n");
  return CLOSED_SIGNAL_PATTERNS.some((signal) => textBlob.includes(signal));
}

function ConciergeCard({
  title,
  category,
  meta,
  tags,
  reason,
  mapLink,
  sourceLink,
  actionLabel,
  added,
  adding,
  isOperational,
  verifiedAt,
  onAdd,
  canAdd = true,
}: {
  title: string;
  category: string;
  meta: string[];
  tags: string[];
  reason?: string;
  mapLink?: string;
  sourceLink?: string;
  actionLabel?: string;
  added: boolean;
  adding: boolean;
  isOperational?: boolean;
  verifiedAt?: string | null;
  onAdd: () => void;
  canAdd?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const reasonParts = splitReason(reason);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <p className="truncate text-sm font-semibold text-slate-900">{title}</p>
            {isOperational && (
              <span
                className="rounded-full bg-emerald-50 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-emerald-700"
                title={verifiedAt ?? "Verified by Google Places"}
              >
                Google verified
              </span>
            )}
          </div>
          <p className="mt-0.5 text-xs text-slate-500">{category}</p>
          {meta.length > 0 && <p className="mt-0.5 text-xs text-slate-500">{meta.join(" · ")}</p>}
          {isOperational && verifiedAt && (
            <p className="mt-0.5 text-[10px] text-slate-400">{verifiedAt}</p>
          )}
        </div>
      </div>

      {tags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {tags.slice(0, 3).map((tag) => (
            <span key={tag} className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600">
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="mt-2 rounded-lg bg-slate-50 px-2 py-1.5 text-xs text-slate-600">
        <span className="font-medium">Why this pick:</span> {reasonParts.short}
        {reasonParts.detail && (
          <>
            <button
              onClick={() => setExpanded((v) => !v)}
              className="ml-1 inline-flex items-center gap-0.5 text-[11px] font-medium text-slate-500 hover:text-slate-700"
            >
              {expanded ? "Less" : "More"}
              <ChevronDown className={`h-3 w-3 transition ${expanded ? "rotate-180" : ""}`} />
            </button>
            {expanded && <p className="mt-1 text-[11px] text-slate-500">{reasonParts.detail}</p>}
          </>
        )}
      </div>

      <div className="mt-2 flex items-center gap-2">
        {canAdd ? (
          <button
            onClick={onAdd}
            disabled={adding || added}
            className={`flex-1 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              added
                ? "bg-emerald-50 text-emerald-700"
                : "bg-sky-50 text-sky-700 hover:bg-sky-100"
            }`}
          >
            {adding ? <Loader2 className="mx-auto h-3.5 w-3.5 animate-spin" /> : added ? <span className="inline-flex items-center gap-1"><Check className="h-3 w-3" /> Added</span> : actionLabel ?? "Add to Trip"}
          </button>
        ) : sourceLink ? (
          <a
            href={sourceLink}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-200"
          >
            <ExternalLink className="h-3 w-3" /> Open source
          </a>
        ) : (
          <span className="flex-1 rounded-lg bg-slate-100 px-3 py-1.5 text-center text-xs font-medium text-slate-500">
            Research only
          </span>
        )}
        {mapLink && (
          <a href={mapLink} target="_blank" rel="noopener noreferrer" title="View on map" aria-label="View on map" className="rounded-lg bg-slate-100 px-2 py-1.5 text-xs text-slate-700 hover:bg-slate-200">
            <MapPin className="h-3.5 w-3.5" />
          </a>
        )}
        {sourceLink && sourceLink !== mapLink && canAdd && (
          <a href={sourceLink} target="_blank" rel="noopener noreferrer" title="View source / book" aria-label="View source or book" className="rounded-lg bg-violet-50 px-2 py-1.5 text-xs text-violet-700 hover:bg-violet-100">
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
      </div>
    </div>
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

export function AIConciergePanel({ tripId, destination, tripDays: tripDaysProp = [], isOpen, onClose, onItemAdded }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [input, setInput] = useState("");
  const [tripDays, setTripDays] = useState<ItineraryDay[]>([]);
  const [itineraryItems, setItineraryItems] = useState<ItineraryItem[]>([]);
  const [selectedDayId, setSelectedDayId] = useState<string>("");
  const [addingItems, setAddingItems] = useState<Set<string>>(new Set());
  const [addedItems, setAddedItems] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [historyWarning, setHistoryWarning] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const loadedTripRef = useRef<string | null>(null);
  const skipReloadRef = useRef(false);

  const inputRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

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
    const [historyResult, itineraryResult] = await Promise.allSettled([
      fetchConciergeMessages(tripId),
      tripDaysProp.length > 0 ? Promise.resolve(tripDaysProp) : fetchItinerary(tripId),
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

    setMessages(initialMessages);
    setTripDays(itinerary);
    setItineraryItems(itinerary.flatMap((day) => day.items ?? []));
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
  ) {
    if (!selectedDayId) {
      setError("Select a day before adding this item.");
      return;
    }
    const key = cardKey(name, selectedDayId || undefined);
    if (addingItems.has(key) || addedItems.has(key)) return;

    const duplicate = itineraryItems.some((it) => {
      const titleMatch = normalizeTitle(it.title) === normalizeTitle(name);
      if (!titleMatch) return false;
      if (selectedDayId) return it.dayId === selectedDayId;
      return it.tripId === tripId;
    });

    if (duplicate) {
      setAddedItems((prev) => new Set(prev).add(key));
      return;
    }

    setAddingItems((prev) => new Set(prev).add(key));
    setError(null);
    try {
      const added = await addStructuredConciergeItemToTrip(tripId, item, kind, {
        dayId: selectedDayId || undefined,
        reason,
      });
      setAddedItems((prev) => new Set(prev).add(key));
      setItineraryItems((prev) => [...prev, added]);
      setTripDays((prev) =>
        prev.map((day) =>
          day.id === selectedDayId
            ? { ...day, items: [...(day.items ?? []), added] }
            : day
        )
      );
      onItemAdded?.();
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
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative flex h-full w-full max-w-md flex-col bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-100 bg-gradient-to-r from-violet-600 to-sky-500 px-4 py-3">
          <div className="flex items-center gap-2 text-white">
            <Sparkles className="h-4 w-4" />
            <span className="text-sm font-semibold">AI Concierge</span>
            {destination && <span className="text-xs text-white/80">· {destination}</span>}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleClearChat}
              className="rounded bg-white/15 px-2.5 py-1 text-[11px] font-medium text-white hover:bg-white/25"
            >
              Clear chat
            </button>
            <button onClick={onClose} className="rounded p-1 text-white/80 hover:bg-white/20" aria-label="Close">
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="border-b border-slate-100 bg-slate-50 px-4 py-2">
          <label className="text-[11px] font-medium text-slate-500">Add items to day</label>
          <select
            value={selectedDayId}
            onChange={(e) => setSelectedDayId(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-700"
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
            <div className="rounded-lg bg-slate-100 px-3 py-2 text-xs text-slate-500">Loading previous chat…</div>
          )}

          {loading && messages.length === 0 && (
            <div className="rounded-lg bg-slate-100 px-3 py-2 text-xs text-slate-500">Loading concierge…</div>
          )}

          {error && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">{error}</div>
          )}

          {historyWarning && (
            <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
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
                  <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${msg.role === "user" ? "rounded-br-sm bg-sky-500 text-white" : "rounded-bl-sm bg-slate-100 text-slate-800"}`}>
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

                  {msg.intent !== "compare" && (msg.restaurants?.length || msg.attractions?.length || msg.hotels?.length || msg.researchSources?.length) ? (
                    <div className="space-y-2">
                      {msg.restaurants?.filter((r) => r.type === "verified_place").map((r) => {
                        const key = cardKey(r.name, selectedDayId || undefined);
                        const reason = r.summary;
                        const isClosed = hasClosedSignal(r);
                        const isOperational = !isClosed && canShowGoogleVerifiedBadge(r);
                        return (
                          <ConciergeCard
                            key={`${r.name}-${key}`}
                            title={r.name}
                            category={r.cuisine || "Restaurant"}
                            meta={[
                              r.neighborhood || "",
                              r.rating ? `★ ${r.rating}` : "",
                            ].filter(Boolean)}
                            tags={r.tags ?? []}
                            reason={reason}
                            mapLink={r.mapsLink}
                            sourceLink={r.bookingLink ?? r.sourceUrl}
                            isOperational={isOperational}
                            verifiedAt={formatVerifiedAt(r.lastVerifiedAt)}
                            added={addedItems.has(key)}
                            adding={addingItems.has(key)}
                            canAdd={!isClosed}
                            onAdd={() => addItem(r.name, "restaurant", r, reason)}
                          />
                        );
                      })}

                      {msg.attractions?.filter((a) => a.type === "verified_place").map((a) => {
                        const key = cardKey(a.name, selectedDayId || undefined);
                        const isClosed = hasClosedSignal(a);
                        const isOperational = !isClosed && canShowGoogleVerifiedBadge(a);
                        return (
                          <ConciergeCard
                            key={`${a.name}-${key}`}
                            title={a.name}
                            category={a.category || "Attraction"}
                            meta={[
                              a.neighborhood || a.address || "",
                              a.rating ? `★ ${a.rating}` : "",
                              a.reviewCount ? `${a.reviewCount.toLocaleString()} reviews` : "",
                            ].filter(Boolean)}
                            tags={a.tags ?? []}
                            reason={a.description}
                            mapLink={a.mapsLink}
                            sourceLink={a.sourceUrl}
                            isOperational={isOperational}
                            verifiedAt={formatVerifiedAt(a.lastVerifiedAt)}
                            added={addedItems.has(key)}
                            adding={addingItems.has(key)}
                            canAdd={!isClosed}
                            onAdd={() => addItem(a.name, "attraction", a, a.description)}
                          />
                        );
                      })}

                      {msg.hotels?.filter((h) => h.type === "verified_place").map((h) => {
                        const key = cardKey(h.name, selectedDayId || undefined);
                        const reason = h.reason ?? (h.pricePerNight ? `~$${Math.round(h.pricePerNight)}/night` : undefined);
                        const isClosed = hasClosedSignal(h);
                        const isOperational = !isClosed && canShowGoogleVerifiedBadge(h);
                        return (
                          <ConciergeCard
                            key={`${h.name}-${key}`}
                            title={h.name}
                            category="Hotel"
                            meta={[
                              h.areaLabel || "",
                              h.stars ? `${Math.round(h.stars)}★` : "",
                              h.rating ? `★ ${h.rating}` : "",
                              h.pricePerNight ? `~$${Math.round(h.pricePerNight)}/night` : "",
                            ].filter(Boolean)}
                            tags={h.tags ?? []}
                            reason={reason}
                            mapLink={h.mapsLink}
                            sourceLink={h.bookingUrl ?? h.sourceUrl}
                            isOperational={isOperational}
                            verifiedAt={formatVerifiedAt(h.lastVerifiedAt)}
                            added={addedItems.has(key)}
                            adding={addingItems.has(key)}
                            canAdd={!isClosed}
                            onAdd={() => addItem(h.name, "hotel", h, reason)}
                          />
                        );
                      })}

                      {(msg.researchSources?.filter((s) => s.type === "research_source").length ?? 0) > 0 && (
                        <div className="pt-1">
                          <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Research sources</p>
                          <div className="space-y-2">
                            {msg.researchSources?.filter((s) => s.type === "research_source").map((s) => (
                              <ConciergeCard
                                key={`${s.title}-${s.sourceUrl ?? "source"}`}
                                title={s.title}
                                category={
                                  s.sourceType === "article_listicle_blog_directory"
                                    ? (s.venuesDiscovered && s.venuesDiscovered > 0
                                        ? `Discovery source · ${s.venuesDiscovered} place${s.venuesDiscovered !== 1 ? "s" : ""} verified`
                                        : "Discovery source")
                                    : "Research source"
                                }
                                meta={[s.neighborhood || ""].filter(Boolean)}
                                tags={[]}
                                reason={s.summary}
                                sourceLink={s.sourceUrl}
                                isOperational={false}
                                verifiedAt={formatVerifiedAt(s.lastVerifiedAt)}
                                added={false}
                                adding={false}
                                canAdd={false}
                                onAdd={() => undefined}
                              />
                            ))}
                          </div>
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
                    <div className="flex items-center gap-1 text-[10px] text-slate-400">
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
                  onClick={() => sendQuery(prompt)}
                  className="rounded-full border border-violet-200 bg-violet-50 px-3 py-1.5 text-xs font-medium text-violet-700 hover:bg-violet-100"
                >
                  {prompt}
                </button>
              ))}
            </div>
          )}

          {loading && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 rounded-2xl rounded-bl-sm bg-slate-100 px-3 py-2">
                <Loader2 className="h-3 w-3 animate-spin text-slate-400" />
                <span className="text-xs text-slate-500">Researching options…</span>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        <div className="border-t border-slate-100 bg-white px-4 py-3">
          {toast && (
            <div className="mb-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
              {toast}
            </div>
          )}
          {messages.length > 1 && !loadingHistory && (
            <div className="mb-2 flex flex-wrap gap-1.5">
              {followUpActions.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => sendQuery(prompt)}
                  className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-medium text-slate-600 hover:bg-slate-100"
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
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendQuery(input.trim())}
              placeholder="Ask for restaurants, hotels, attractions..."
              disabled={loading}
              className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 disabled:opacity-60"
            />
            <button
              onClick={() => sendQuery(input.trim())}
              disabled={loading || !input.trim()}
              className="btn-primary px-3 py-2 disabled:opacity-50"
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
