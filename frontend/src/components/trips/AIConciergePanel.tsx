"use client";

import { useState, useRef, useEffect } from "react";
import { X, Send, Sparkles, Plus, Loader2, UtensilsCrossed, MapPin, Star, ExternalLink, AlertTriangle, Info } from "lucide-react";
import { callConciergeSearch, addConciergeItemToTrip, addMichelinRestaurantToTrip } from "@/lib/api";
import type { ConciergeSuggestion, UnifiedRestaurantResult, UnifiedAttractionResult, UnifiedHotelResult } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  text: string;
  suggestions?: ConciergeSuggestion[];
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
  isOpen: boolean;
  onClose: () => void;
  onItemAdded?: () => void;
}

// ── Michelin badge helpers ────────────────────────────────────────────────────

function michelinStarIcons(status: string): string {
  if (status === "3 Stars") return "⭐⭐⭐";
  if (status === "2 Stars") return "⭐⭐";
  if (status === "1 Star") return "⭐";
  if (status === "Bib Gourmand") return "🍽️";
  return "";
}

function michelinBadgeClass(status: string): string {
  if (status.includes("Star")) return "bg-red-50 text-red-700 border-red-200";
  if (status === "Bib Gourmand") return "bg-orange-50 text-orange-700 border-orange-200";
  return "bg-slate-50 text-slate-600 border-slate-200";
}

function sourceLabel(status: string): string | null {
  if (status === "curated_static") return "Curated reference data";
  if (status === "live_search") return "Live search results";
  if (status === "confirmed_michelin") return "Confirmed Michelin data";
  return null;
}

// ── Restaurant card ───────────────────────────────────────────────────────────

function RestaurantCard({
  restaurant,
  tripId,
  onAdded,
}: {
  restaurant: UnifiedRestaurantResult;
  tripId: string;
  onAdded?: () => void;
}) {
  const [adding, setAdding] = useState(false);
  const [added, setAdded] = useState(false);

  async function handleAdd() {
    if (adding || added) return;
    setAdding(true);
    try {
      await addMichelinRestaurantToTrip(tripId, restaurant);
      setAdded(true);
      onAdded?.();
    } catch {
      // silent fail — user can retry
    } finally {
      setAdding(false);
    }
  }

  return (
    <div className="border border-slate-200 rounded-xl p-3 bg-white shadow-sm">
      {/* Name + Michelin badge */}
      <div className="flex items-start gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <p className="text-sm font-semibold text-slate-800">{restaurant.name}</p>
            {restaurant.michelinStatus && (
              <span
                className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded border text-[10px] font-bold ${michelinBadgeClass(restaurant.michelinStatus)}`}
              >
                {michelinStarIcons(restaurant.michelinStatus)}{" "}
                {restaurant.michelinStatus}
              </span>
            )}
          </div>

          {/* Cuisine · neighborhood · rating */}
          <div className="flex items-center gap-1.5 mt-0.5 text-xs text-slate-500 flex-wrap">
            <span>{restaurant.cuisine}</span>
            {restaurant.neighborhood && (
              <>
                <span className="text-slate-300">·</span>
                <span>{restaurant.neighborhood}</span>
              </>
            )}
            {restaurant.rating != null && (
              <>
                <span className="text-slate-300">·</span>
                <span className="flex items-center gap-0.5 text-amber-600 font-medium">
                  <Star className="w-3 h-3 fill-amber-400 stroke-amber-500" />
                  {restaurant.rating}
                </span>
              </>
            )}
          </div>

          {/* Summary */}
          {restaurant.summary && (
            <p className="text-xs text-slate-500 mt-1 line-clamp-2">{restaurant.summary}</p>
          )}

          {/* Tags */}
          {restaurant.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {restaurant.tags.slice(0, 3).map((tag) => (
                <span
                  key={tag}
                  className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 text-[10px]"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 mt-2">
        <button
          onClick={handleAdd}
          disabled={adding || added}
          className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
            added
              ? "bg-emerald-50 text-emerald-600 cursor-default"
              : "bg-sky-50 text-sky-600 hover:bg-sky-100 active:scale-95"
          }`}
        >
          {adding ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : added ? (
            "✓ Added to Trip"
          ) : (
            <>
              <Plus className="w-3 h-3" />
              Add to Trip
            </>
          )}
        </button>

        {restaurant.mapsLink && (
          <a
            href={restaurant.mapsLink}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-50 text-slate-600 hover:bg-slate-100 transition"
          >
            <MapPin className="w-3 h-3" />
            Map
          </a>
        )}

        {restaurant.bookingLink && (
          <a
            href={restaurant.bookingLink}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-violet-50 text-violet-600 hover:bg-violet-100 transition"
          >
            <ExternalLink className="w-3 h-3" />
            Book
          </a>
        )}
      </div>

      {/* Source + review count */}
      <div className="flex items-center justify-between mt-1.5">
        <span className="text-[10px] text-slate-400">Source: {restaurant.source}</span>
        {restaurant.reviewCount != null && (
          <span className="text-[10px] text-slate-400">
            {restaurant.reviewCount.toLocaleString()} reviews
          </span>
        )}
      </div>
    </div>
  );
}

// ── Attraction card ───────────────────────────────────────────────────────────

function AttractionCard({ attraction }: { attraction: UnifiedAttractionResult }) {
  return (
    <div className="border border-slate-200 rounded-xl p-3 bg-white shadow-sm">
      <div className="flex items-start gap-2">
        <MapPin className="w-4 h-4 text-violet-500 mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <p className="text-sm font-semibold text-slate-800">{attraction.name}</p>
            <span className="px-1.5 py-0.5 rounded bg-violet-50 text-violet-600 border border-violet-200 text-[10px] font-medium">
              {attraction.category}
            </span>
          </div>
          <div className="flex items-center gap-1.5 mt-0.5 text-xs text-slate-500 flex-wrap">
            {attraction.neighborhood && <span>{attraction.neighborhood}</span>}
            {attraction.rating != null && (
              <>
                {attraction.neighborhood && <span className="text-slate-300">·</span>}
                <span className="flex items-center gap-0.5 text-amber-600 font-medium">
                  <Star className="w-3 h-3 fill-amber-400 stroke-amber-500" />
                  {attraction.rating}
                </span>
              </>
            )}
          </div>
          {attraction.description && (
            <p className="text-xs text-slate-500 mt-1 line-clamp-2">{attraction.description}</p>
          )}
          {attraction.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {attraction.tags.slice(0, 3).map((tag) => (
                <span key={tag} className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 text-[10px]">
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
      {attraction.mapsLink && (
        <div className="mt-2">
          <a
            href={attraction.mapsLink}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-50 text-slate-600 hover:bg-slate-100 transition"
          >
            <MapPin className="w-3 h-3" />
            View on Map
          </a>
        </div>
      )}
    </div>
  );
}

// ── Hotel card ────────────────────────────────────────────────────────────────

function HotelCard({ hotel }: { hotel: UnifiedHotelResult }) {
  const stars = hotel.stars ? "★".repeat(Math.round(hotel.stars)) : null;
  return (
    <div className="border border-slate-200 rounded-xl p-3 bg-white shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <p className="text-sm font-semibold text-slate-800">{hotel.name}</p>
            {stars && <span className="text-amber-500 text-xs">{stars}</span>}
          </div>
          <div className="flex items-center gap-1.5 mt-0.5 text-xs text-slate-500 flex-wrap">
            {hotel.areaLabel && <span>{hotel.areaLabel}</span>}
            {hotel.rating != null && (
              <>
                {hotel.areaLabel && <span className="text-slate-300">·</span>}
                <span className="flex items-center gap-0.5 text-amber-600 font-medium">
                  <Star className="w-3 h-3 fill-amber-400 stroke-amber-500" />
                  {hotel.rating}
                </span>
              </>
            )}
          </div>
          {hotel.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {hotel.tags.slice(0, 3).map((tag) => (
                <span key={tag} className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 text-[10px]">
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
        {hotel.pricePerNight != null && (
          <div className="text-right flex-shrink-0">
            <p className="text-sm font-semibold text-slate-800">${Math.round(hotel.pricePerNight)}</p>
            <p className="text-[10px] text-slate-400">/night</p>
          </div>
        )}
      </div>
      {hotel.mapsLink && (
        <div className="mt-2">
          <a
            href={hotel.mapsLink}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-50 text-slate-600 hover:bg-slate-100 transition"
          >
            <MapPin className="w-3 h-3" />
            View on Map
          </a>
        </div>
      )}
    </div>
  );
}

// ── Main panel ────────────────────────────────────────────────────────────────

export function AIConciergePanel({ tripId, destination, isOpen, onClose, onItemAdded }: Props) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      text: `Hi! I'm your AI Concierge for ${destination || "your trip"}. Ask me anything — Michelin restaurants, hidden gems, romantic dinners, what to do…`,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [addingItems, setAddingItems] = useState<Set<string>>(new Set());
  const [addedItems, setAddedItems] = useState<Set<string>>(new Set());
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const dest = destination || "this destination";
  const QUICK_ACTIONS = [
    { label: "⭐ Michelin restaurants", query: `Michelin starred restaurants in ${dest}` },
    { label: "🍽️ Bib Gourmand", query: `Bib Gourmand restaurants in ${dest}` },
    { label: "💑 Romantic dinner", query: `Romantic dinner restaurants in ${dest}` },
    { label: "📍 Best near hotel", query: `Best restaurants near my hotel in ${dest}` },
    { label: "💎 Hidden gems", query: `Hidden gem restaurants in ${dest}` },
  ];

  async function sendQuery(query: string) {
    if (!query || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: query }]);
    setLoading(true);
    try {
      const result = await callConciergeSearch(tripId, query);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: result.response,
          suggestions: result.suggestions,
          restaurants: result.restaurants,
          attractions: result.attractions,
          hotels: result.hotels,
          intent: result.intent,
          sourceStatus: result.sourceStatus,
          warnings: result.warnings,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Sorry, something went wrong. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function handleSend() {
    await sendQuery(input.trim());
  }

  async function handleAddToTrip(suggestion: ConciergeSuggestion) {
    if (addingItems.has(suggestion.name) || addedItems.has(suggestion.name)) return;
    setAddingItems((prev) => new Set(prev).add(suggestion.name));
    try {
      await addConciergeItemToTrip(tripId, suggestion);
      setAddedItems((prev) => new Set(prev).add(suggestion.name));
      onItemAdded?.();
    } catch {
      // silently fail — user can retry
    } finally {
      setAddingItems((prev) => {
        const next = new Set(prev);
        next.delete(suggestion.name);
        return next;
      });
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end" onClick={(e) => e.target === e.currentTarget && onClose()}>
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />

      {/* Panel */}
      <div className="relative flex flex-col w-full max-w-md h-full bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-violet-600 to-sky-500">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-white" />
            <span className="text-sm font-semibold text-white">AI Concierge</span>
            {destination && (
              <span className="text-xs text-white/70">· {destination}</span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-white/20 text-white/80 transition"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {messages.map((msg, i) => (
            <div key={i}>
              <div className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[85%] px-3 py-2 rounded-2xl text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-sky-500 text-white rounded-br-sm"
                      : "bg-slate-100 text-slate-800 rounded-bl-sm"
                  }`}
                >
                  {msg.text}
                </div>
              </div>

              {/* Warnings — shown below AI bubble */}
              {msg.warnings && msg.warnings.length > 0 && (
                <div className="mt-2 space-y-1">
                  {msg.warnings.map((w, wi) => (
                    <div key={wi} className="flex items-start gap-1.5 px-3 py-2 rounded-lg bg-amber-50 border border-amber-200">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-500 mt-0.5 flex-shrink-0" />
                      <p className="text-xs text-amber-700">{w}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Source note */}
              {msg.sourceStatus && sourceLabel(msg.sourceStatus) && (
                <div className="flex items-center gap-1 mt-1.5 px-1">
                  <Info className="w-3 h-3 text-slate-400" />
                  <span className="text-[10px] text-slate-400">{sourceLabel(msg.sourceStatus)}</span>
                </div>
              )}

              {/* Restaurant result cards */}
              {msg.restaurants && msg.restaurants.length > 0 && (
                <div className="mt-3 space-y-2">
                  <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide px-1">
                    {msg.intent === "michelin_restaurants"
                      ? `Michelin Guide Results · ${destination}`
                      : `Restaurant Results · ${destination}`}
                  </p>
                  {msg.restaurants.map((r, ri) => (
                    <RestaurantCard key={ri} restaurant={r} tripId={tripId} onAdded={onItemAdded} />
                  ))}
                </div>
              )}

              {/* Attraction cards */}
              {msg.attractions && msg.attractions.length > 0 && (
                <div className="mt-3 space-y-2">
                  <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide px-1">
                    Top Attractions · {destination}
                  </p>
                  {msg.attractions.map((a, ai) => (
                    <AttractionCard key={ai} attraction={a} />
                  ))}
                </div>
              )}

              {/* Hotel cards */}
              {msg.hotels && msg.hotels.length > 0 && (
                <div className="mt-3 space-y-2">
                  <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide px-1">
                    Hotel Options · {destination}
                  </p>
                  {msg.hotels.map((h, hi) => (
                    <HotelCard key={hi} hotel={h} />
                  ))}
                </div>
              )}

              {/* Fallback suggestion cards (for non-restaurant intents without specific cards) */}
              {msg.suggestions && msg.suggestions.length > 0 &&
                (!msg.restaurants || msg.restaurants.length === 0) &&
                (!msg.attractions || msg.attractions.length === 0) &&
                (!msg.hotels || msg.hotels.length === 0) && (
                <div className="mt-3 space-y-2">
                  {msg.suggestions.map((s, si) => {
                    const added = addedItems.has(s.name);
                    const adding = addingItems.has(s.name);
                    return (
                      <div
                        key={si}
                        className="border border-slate-200 rounded-xl p-3 bg-white shadow-sm"
                      >
                        <div className="flex items-start gap-2">
                          <div className="mt-0.5 flex-shrink-0">
                            {s.type === "restaurant" ? (
                              <UtensilsCrossed className="w-4 h-4 text-amber-500" />
                            ) : (
                              <MapPin className="w-4 h-4 text-violet-500" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-slate-800 truncate">{s.name}</p>
                            <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{s.reason}</p>
                          </div>
                        </div>
                        <button
                          onClick={() => handleAddToTrip(s)}
                          disabled={adding || added}
                          className={`mt-2 w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                            added
                              ? "bg-emerald-50 text-emerald-600 cursor-default"
                              : "bg-sky-50 text-sky-600 hover:bg-sky-100 active:scale-95"
                          }`}
                        >
                          {adding ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : added ? (
                            "✓ Added to Trip"
                          ) : (
                            <>
                              <Plus className="w-3 h-3" />
                              Add to Trip
                            </>
                          )}
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))}

          {/* Quick action buttons — shown only before conversation starts */}
          {messages.length === 1 && !loading && (
            <div className="flex flex-wrap gap-2 mt-1">
              {QUICK_ACTIONS.map((action) => (
                <button
                  key={action.label}
                  onClick={() => sendQuery(action.query)}
                  className="px-3 py-1.5 rounded-full border border-violet-200 bg-violet-50 text-violet-700 text-xs font-medium hover:bg-violet-100 active:scale-95 transition"
                >
                  {action.label}
                </button>
              ))}
            </div>
          )}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-slate-100 rounded-2xl rounded-bl-sm px-3 py-2 flex items-center gap-2">
                <Loader2 className="w-3 h-3 text-slate-400 animate-spin" />
                <span className="text-xs text-slate-500">Retrieving results…</span>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="px-4 py-3 border-t border-slate-100 bg-white">
          <div className="flex items-center gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
              placeholder="Michelin restaurants, romantic dinner, hidden gems…"
              disabled={loading}
              className="flex-1 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 disabled:opacity-60"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading}
              className="btn-primary px-3 py-2 disabled:opacity-50"
              aria-label="Send"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
