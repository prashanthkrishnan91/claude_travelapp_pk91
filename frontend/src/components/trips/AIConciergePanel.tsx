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
  fetchConciergeMessages,
  fetchItinerary,
} from "@/lib/api";
import type {
  ConciergeSearchResult,
  UnifiedAttractionResult,
  UnifiedHotelResult,
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
  intent?: string;
  sourceStatus?: string;
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

function sourceLabel(status: string): string | null {
  if (status === "curated_static") return "Curated reference data";
  if (status === "live_search") return "Live search results";
  if (status === "confirmed_michelin") return "Confirmed Michelin data";
  return null;
}

function cardKey(name: string, dayId?: string): string {
  return `${name.trim().toLowerCase()}::${dayId ?? "trip"}`;
}

function normalizeTitle(value: string): string {
  return value.trim().toLowerCase();
}

function splitReason(text?: string): { short: string; detail?: string } {
  const clean = (text ?? "").trim();
  if (!clean) return { short: "Great fit for this trip." };
  const parts = clean.split(/(?<=[.!?])\s+/);
  return {
    short: parts.slice(0, 1).join(" "),
    detail: parts.length > 1 ? parts.slice(1).join(" ") : undefined,
  };
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
  onAdd,
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
  onAdd: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const reasonParts = splitReason(reason);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-slate-900">{title}</p>
          <p className="mt-0.5 text-xs text-slate-500">{category}</p>
          {meta.length > 0 && <p className="mt-0.5 text-xs text-slate-500">{meta.join(" · ")}</p>}
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
        {mapLink && (
          <a href={mapLink} target="_blank" rel="noopener noreferrer" className="rounded-lg bg-slate-100 px-2 py-1.5 text-xs text-slate-700 hover:bg-slate-200">
            <MapPin className="h-3.5 w-3.5" />
          </a>
        )}
        {sourceLink && (
          <a href={sourceLink} target="_blank" rel="noopener noreferrer" className="rounded-lg bg-violet-50 px-2 py-1.5 text-xs text-violet-700 hover:bg-violet-100">
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
    intent: result.intent,
    sourceStatus: result.sourceStatus,
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
  const loadedTripRef = useRef<string | null>(null);

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

    if (historyResult.status === "rejected") {
      console.error("[concierge] failed to load persisted history", historyResult.reason);
      setError("Could not load previous concierge history.");
    }

    if (historyMessages.length === 0) {
      historyMessages.push({
        role: "assistant",
        text: `Tell me what you need for ${destination || "your trip"} and I'll return concise picks with action cards.`,
      });
    }

    const itinerary = itineraryResult.status === "fulfilled" ? itineraryResult.value : [];
    if (itineraryResult.status === "rejected") {
      console.error("[concierge] failed to load itinerary days", itineraryResult.reason);
    }

    setMessages(historyMessages);
    setTripDays(itinerary);
    setItineraryItems(itinerary.flatMap((day) => day.items ?? []));
    setSelectedDayId((prev) => {
      if (prev && itinerary.some((day) => day.id === prev)) return prev;
      return itinerary[0]?.id || "";
    });
    loadedTripRef.current = tripId;
    setLoadingHistory(false);
  }, [destination, tripDaysProp, tripId]);

  useEffect(() => {
    if (!isOpen) return;
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
  }, [tripId]);

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
          <button onClick={onClose} className="rounded p-1 text-white/80 hover:bg-white/20" aria-label="Close">
            <X className="h-4 w-4" />
          </button>
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

          {messages.map((msg, idx) => (
            <div key={idx} className="space-y-2">
              <div className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${msg.role === "user" ? "rounded-br-sm bg-sky-500 text-white" : "rounded-bl-sm bg-slate-100 text-slate-800"}`}>
                  {msg.text}
                </div>
              </div>

              {msg.role === "assistant" && (
                <>
                  {(msg.restaurants?.length || msg.attractions?.length || msg.hotels?.length) ? (
                    <div className="space-y-2">
                      {msg.restaurants?.map((r) => {
                        const key = cardKey(r.name, selectedDayId || undefined);
                        const reason = r.summary;
                        return (
                          <ConciergeCard
                            key={`${r.name}-${key}`}
                            title={r.name}
                            category="Restaurant"
                            meta={[
                              r.cuisine,
                              r.neighborhood || "",
                              r.rating ? `★ ${r.rating}` : "",
                            ].filter(Boolean)}
                            tags={r.tags ?? []}
                            reason={reason}
                            mapLink={r.mapsLink}
                            sourceLink={r.bookingLink}
                            added={addedItems.has(key)}
                            adding={addingItems.has(key)}
                            onAdd={() => addItem(r.name, "restaurant", r, reason)}
                          />
                        );
                      })}

                      {msg.attractions?.map((a) => {
                        const key = cardKey(a.name, selectedDayId || undefined);
                        return (
                          <ConciergeCard
                            key={`${a.name}-${key}`}
                            title={a.name}
                            category={a.category || "Attraction"}
                            meta={[
                              a.neighborhood || a.address || "",
                              a.rating ? `★ ${a.rating}` : "",
                              a.reviewCount ? `${a.reviewCount} reviews` : "",
                            ].filter(Boolean)}
                            tags={a.tags ?? []}
                            reason={a.description}
                            mapLink={a.mapsLink}
                            sourceLink={a.mapsLink}
                            added={addedItems.has(key)}
                            adding={addingItems.has(key)}
                            onAdd={() => addItem(a.name, "attraction", a, a.description)}
                          />
                        );
                      })}

                      {msg.hotels?.map((h) => {
                        const key = cardKey(h.name, selectedDayId || undefined);
                        const reason = h.pricePerNight ? `Around $${Math.round(h.pricePerNight)}/night.` : undefined;
                        return (
                          <ConciergeCard
                            key={`${h.name}-${key}`}
                            title={h.name}
                            category="Hotel"
                            meta={[
                              h.areaLabel || "",
                              h.stars ? `${Math.round(h.stars)}★` : "",
                              h.rating ? `★ ${h.rating}` : "",
                            ].filter(Boolean)}
                            tags={h.tags ?? []}
                            reason={reason}
                            mapLink={h.mapsLink}
                            sourceLink={h.mapsLink}
                            added={addedItems.has(key)}
                            adding={addingItems.has(key)}
                            onAdd={() => addItem(h.name, "hotel", h, reason)}
                          />
                        );
                      })}
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

                  {msg.sourceStatus && sourceLabel(msg.sourceStatus) && (
                    <div className="flex items-center gap-1 text-[10px] text-slate-400">
                      <Info className="h-3 w-3" />
                      <span>{sourceLabel(msg.sourceStatus)}</span>
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
