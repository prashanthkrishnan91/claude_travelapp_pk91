"use client";

import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import type { Session } from "@supabase/supabase-js";
import {
  DndContext,
  DragCancelEvent,
  DragEndEvent,
  DragOverEvent,
  DragStartEvent,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  UniqueIdentifier,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import {
  Plane,
  Hotel,
  MapPin,
  CalendarPlus,
  Sparkles,
  Scale,
  Loader2,
  BarChart2,
  CheckCircle2,
  X,
  Zap,
  Star,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Plus,
  Clock,
  DollarSign,
  UtensilsCrossed,
  Map as MapIcon,
  LayoutList,
  Navigation,
} from "lucide-react";
import { estimateTravel, sumRoute } from "@/lib/travelTime";
import { addDaysToIsoDate, normalizeIsoDate } from "@/lib/tripDays";
import { supabase } from "@/lib/supabase";
import gsap from "gsap";
import type {
  ItineraryDay,
  ItineraryItem,
  ResearchResult,
  ItemType,
  CompareResult,
  AttractionSearchResult,
  RestaurantSearchResult,
  DayPlan,
} from "@/types";
import {
  createDay,
  deleteItem,
  createItem,
  updateItem,
  compareItems,
  fetchTripItems,
  ensureTripDays,
  addOneWayFlightToDay,
  addRoundTripOutboundToDay,
  addRoundTripReturnToDay,
  fetchDayPlan,
  addAttractionToDay,
  addRestaurantToDay,
  addHotelToDay,
  moveIdeaToTripIdeas,
  fetchExploreSnapshot,
} from "@/lib/api";
import { buildTripCandidateBuckets, mergePersistedWithSnapshot } from "@/lib/tripCandidates";
import { SearchResultCard } from "./SearchResultCard";
import { ItineraryDayColumn } from "./ItineraryDayColumn";
import { ItineraryItemCard } from "./ItineraryItemCard";
import { CompareModal } from "./CompareModal";
import { DayPlanModal } from "./DayPlanModal";
import { TripMapView } from "./TripMapView";
import { TripIdeasPanel } from "./TripIdeasPanel";

// ─── Helpers ──────────────────────────────────────────────────────────────────

type SortKey = "ai" | "price" | "cpp" | "duration" | "rating" | "location";

function sortFlights(items: ItineraryItem[], key: SortKey): ItineraryItem[] {
  return [...items].sort((a, b) => {
    const da = (a.details ?? {}) as Record<string, unknown>;
    const db = (b.details ?? {}) as Record<string, unknown>;
    const isRtA = !!da.is_round_trip;
    const isRtB = !!db.is_round_trip;
    if (key === "price") {
      const pa = isRtA ? ((da.total_price as number) ?? 0) : ((da.price as number) ?? a.cashPrice ?? 0);
      const pb = isRtB ? ((db.total_price as number) ?? 0) : ((db.price as number) ?? b.cashPrice ?? 0);
      return pa - pb;
    }
    if (key === "cpp") {
      const ca = isRtA ? ((da.combined_cpp as number) ?? 0) : ((da.cpp as number) ?? 0);
      const cb = isRtB ? ((db.combined_cpp as number) ?? 0) : ((db.cpp as number) ?? 0);
      return cb - ca;
    }
    if (key === "duration") {
      const dura = isRtA ? ((da.total_duration_minutes as number) ?? 0) : ((da.durationMinutes as number) ?? 0);
      const durb = isRtB ? ((db.total_duration_minutes as number) ?? 0) : ((db.durationMinutes as number) ?? 0);
      return dura - durb;
    }
    return ((db.aiScore as number) ?? 0) - ((da.aiScore as number) ?? 0);
  });
}

function sortHotels(items: ItineraryItem[], key: SortKey): ItineraryItem[] {
  return [...items].sort((a, b) => {
    const da = (a.details ?? {}) as Record<string, unknown>;
    const db = (b.details ?? {}) as Record<string, unknown>;
    if (key === "price")    return ((da.price_per_night as number) ?? (da.pricePerNight as number) ?? a.cashPrice ?? 0) - ((db.price_per_night as number) ?? (db.pricePerNight as number) ?? b.cashPrice ?? 0);
    if (key === "rating")   return ((db.rating as number) ?? 0) - ((da.rating as number) ?? 0);
    if (key === "location") return ((db.location_score as number) ?? 0) - ((da.location_score as number) ?? 0);
    return ((db.ai_score as number) ?? (db.aiScore as number) ?? 0) - ((da.ai_score as number) ?? (da.aiScore as number) ?? 0);
  });
}

function sortAttractions(items: AttractionSearchResult[], key: SortKey): AttractionSearchResult[] {
  return [...items].sort((a, b) => {
    if (key === "rating") return (b.rating ?? 0) - (a.rating ?? 0);
    return (b.aiScore ?? 0) - (a.aiScore ?? 0);
  });
}

function sortRestaurants(items: RestaurantSearchResult[], key: SortKey): RestaurantSearchResult[] {
  return [...items].sort((a, b) => {
    if (key === "rating") return (b.rating ?? 0) - (a.rating ?? 0);
    if (key === "price")  return (a.priceLevel ?? 0) - (b.priceLevel ?? 0);
    return (b.aiScore ?? 0) - (a.aiScore ?? 0);
  });
}

function filterAttractions(
  items: AttractionSearchResult[],
  ratingMin: number | null,
  type: string | null,
): AttractionSearchResult[] {
  return items.filter((a) => {
    if (ratingMin !== null && (a.rating ?? 0) < ratingMin) return false;
    if (type !== null) {
      const cat = a.category?.toLowerCase() ?? "";
      if (type === "landmarks" ? (cat !== "landmarks" && cat !== "top_attractions") : cat !== type) return false;
    }
    return true;
  });
}

function filterRestaurants(
  items: RestaurantSearchResult[],
  cuisine: string | null,
  priceLevel: number | null,
  ratingMin: number | null,
): RestaurantSearchResult[] {
  return items.filter((r) => {
    if (cuisine !== null && r.cuisine?.toLowerCase() !== cuisine.toLowerCase()) return false;
    if (priceLevel !== null && r.priceLevel !== priceLevel) return false;
    if (ratingMin !== null && (r.rating ?? 0) < ratingMin) return false;
    return true;
  });
}

function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
  } catch {
    return iso;
  }
}

// ─── Recommendation tag badge ─────────────────────────────────────────────────

function RecTag({ tag }: { tag: string }) {
  const style =
    tag === "Points Better"   ? "bg-violet-100 text-violet-700" :
    tag === "Best Value"      ? "bg-emerald-100 text-emerald-700" :
    tag === "Great Rating"    ? "bg-amber-100 text-amber-700" :
    tag === "Budget Pick"     ? "bg-teal-100 text-teal-700" :
    tag === "High CPP"        ? "bg-purple-100 text-purple-700" :
    tag === "Non-stop"        ? "bg-sky-100 text-sky-700" :
    tag === "Cheapest"        ? "bg-green-100 text-green-700" :
    tag === "Luxury Pick"     ? "bg-rose-100 text-rose-700" :
    tag === "Budget Friendly" ? "bg-teal-100 text-teal-700" :
    tag === "Top Rated"       ? "bg-amber-100 text-amber-700" :
    tag === "Cash Better"     ? "bg-slate-100 text-slate-500" :
    "bg-slate-100 text-slate-500";
  const icon =
    tag === "Points Better"   ? <Zap className="w-2.5 h-2.5" /> :
    tag === "Best Value"      ? <Star className="w-2.5 h-2.5" /> :
    tag === "High CPP"        ? <Zap className="w-2.5 h-2.5" /> :
    tag === "Top Rated"       ? <Star className="w-2.5 h-2.5" /> :
    null;
  return (
    <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-xs font-semibold ${style}`}>
      {icon}{tag}
    </span>
  );
}

// ─── AI score badge ───────────────────────────────────────────────────────────

function AiScoreBadge({ score }: { score?: number | null }) {
  if (typeof score !== "number" || !Number.isFinite(score) || score <= 0) return null;
  const { bg, text, ring } =
    score >= 70 ? { bg: "bg-emerald-500/15", text: "text-emerald-200", ring: "ring-emerald-400/45" } :
    score >= 50 ? { bg: "bg-amber-500/15",   text: "text-amber-200",   ring: "ring-amber-400/45"   } :
                  { bg: "bg-slate-500/15",   text: "text-slate-200",   ring: "ring-white/20"   };
  return (
    <div className={`flex flex-col items-center justify-center w-10 h-10 rounded-full ring-2 ${ring} ${bg} flex-shrink-0`}>
      <p className={`text-xs font-bold leading-none ${text}`}>{Math.round(score ?? 0)}</p>
      <p className="text-[9px] text-cream-300 leading-none mt-0.5">score</p>
    </div>
  );
}

const PREMIUM_CARD_BASE = "candidate-card relative border rounded-2xl p-4 flex flex-col gap-3 transition-all duration-200 shadow-sm hover:shadow-md border-white/12 bg-gradient-to-br from-dark-200/95 to-dark-300/95 hover:border-white/25";
const SECONDARY_CTA = "flex-1 flex items-center justify-center gap-1.5 px-2 py-2 rounded-xl border border-white/15 bg-dark-300/75 text-cream-200 hover:bg-dark-200 hover:border-white/30 text-xs font-medium transition-all";
const PRIMARY_CTA = "flex-1 flex items-center justify-center gap-1.5 px-2 py-2 rounded-xl bg-brand-500 hover:bg-brand-400 text-dark-900 text-xs font-semibold transition-all disabled:opacity-50 shadow-sm";

// ─── Sort control ─────────────────────────────────────────────────────────────

function SortControl({
  keys,
  current,
  onChange,
}: {
  keys: { key: SortKey; label: string }[];
  current: SortKey;
  onChange: (k: SortKey) => void;
}) {
  return (
    <div className="flex items-center gap-1 flex-wrap">
      <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wide">Sort:</span>
      {keys.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => onChange(key)}
          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold transition-all ${
            current === key
              ? "bg-brand-500/85 text-dark-900 shadow-sm"
              : "bg-dark-300/80 text-cream-300 border border-white/10 hover:bg-dark-200"
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

// ─── Summary bar ─────────────────────────────────────────────────────────────

function SummaryBar({
  topFlight,
  topHotel,
}: {
  topFlight: ItineraryItem | null;
  topHotel: ItineraryItem | null;
}) {
  if (!topFlight && !topHotel) return null;
  const fd = (topFlight?.details ?? {}) as Record<string, unknown>;
  const hd = (topHotel?.details ?? {}) as Record<string, unknown>;
  const isRoundTrip = !!fd.is_round_trip;
  const outFd = (fd.outbound ?? {}) as Record<string, unknown>;
  const topAirline  = isRoundTrip ? (outFd.airline as string) : (fd.airline as string);
  const topOrigin   = isRoundTrip ? (outFd.origin as string) : (fd.origin as string);
  const topDest     = isRoundTrip ? (outFd.destination as string) : (fd.destination as string);
  const topPrice    = isRoundTrip ? (fd.total_price as number) : (fd.price as number);
  return (
    <div className="glass border border-white/12 rounded-2xl p-3 flex gap-3 shadow-sm">
      {topFlight && (
        <div className="flex-1 min-w-0">
          <p className="text-[10px] text-cream-300 uppercase tracking-wide font-semibold mb-1 flex items-center gap-1">
            <Plane className="w-3 h-3 text-brand-300" /> {isRoundTrip ? "Best Round-Trip" : "Best Flight"}
          </p>
          <p className="text-xs font-bold text-cream-100 truncate">
            {topAirline ?? topFlight.title}
          </p>
          <p className="text-xs text-cream-300">
            {topOrigin ?? ""}
            {topDest ? ` → ${topDest}` : ""}
            {topPrice ? ` · $${Math.round(topPrice)}` : ""}
          </p>
        </div>
      )}
      {topFlight && topHotel && <div className="w-px bg-white/12 self-stretch" />}
      {topHotel && (
        <div className="flex-1 min-w-0">
          <p className="text-[10px] text-cream-300 uppercase tracking-wide font-semibold mb-1 flex items-center gap-1">
            <Hotel className="w-3 h-3 text-brand-400" /> Best Hotel
          </p>
          <p className="text-xs font-bold text-cream-100 truncate">
            {(hd.name as string) ?? topHotel.title}
          </p>
          <p className="text-xs text-cream-300">
            {hd.pricePerNight ? `$${Math.round(hd.pricePerNight as number)}/night` : ""}
            {hd.rating ? ` · ★ ${(hd.rating as number).toFixed(1)}` : ""}
          </p>
        </div>
      )}
    </div>
  );
}

// ─── Flight candidate card ────────────────────────────────────────────────────

function FlightCandidateCard({
  item,
  onAddToItinerary,
  onToggleCompare,
  adding,
  isTopPick,
  isLowScore,
  isComparing,
}: {
  item: ItineraryItem;
  onAddToItinerary: (item: ItineraryItem) => void;
  onToggleCompare?: (item: ItineraryItem) => void;
  adding: boolean;
  isTopPick?: boolean;
  isLowScore?: boolean;
  isComparing?: boolean;
}) {
  const d = (item.details ?? {}) as Record<string, unknown>;
  const airline     = (d.airline          as string)   ?? "";
  const flightNum   = (d.flightNumber     as string)   ?? item.title;
  const origin      = (d.origin           as string)   ?? "";
  const destination = (d.destination      as string)   ?? "";
  const depTime     = (d.departureTime    as string)   ?? "";
  const arrTime     = (d.arrivalTime      as string)   ?? "";
  const duration    = (d.durationMinutes  as number)   ?? 0;
  const stops       = (d.stops            as number)   ?? 0;
  const price       = (d.price            as number)   ?? item.cashPrice ?? 0;
  const points      = (d.pointsCost       as number)   ?? item.pointsPrice ?? 0;
  const cpp         = (d.cpp              as number)   ?? 0;
  const aiScore     = (d.aiScore          as number)   ?? 0;
  const tags        = (d.tags             as string[]) ?? [];
  const bookingUrl  = (d.bookingUrl       as string)   ?? "";

  const containerClass = `${PREMIUM_CARD_BASE} ${isTopPick ? "border-brand-400/45" : ""} ${isLowScore ? "opacity-55" : ""}`;

  return (
    <div className={containerClass}>
      {isTopPick && (
        <div className="absolute -top-2.5 left-3">
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500 text-white shadow-sm">
            <Zap className="w-2.5 h-2.5" />
            Best Pick
          </span>
        </div>
      )}

      {/* Header: airline + flight number + one-way badge + AI score */}
      <div className="flex items-start justify-between gap-2 pt-0.5">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 flex-wrap">
            <p className="text-sm font-bold text-cream-100 leading-tight">{airline || flightNum}</p>
            <span className="px-1.5 py-0.5 rounded-full text-[9px] font-semibold bg-sky-500/15 text-sky-300 border border-sky-400/20">One-way</span>
          </div>
          {airline && <p className="text-xs text-cream-300 mt-0.5">{flightNum}</p>}
        </div>
        <AiScoreBadge score={aiScore} />
      </div>

      {/* Route row */}
      {origin && destination && (
        <div className="flex items-center gap-2">
          <div className="text-center min-w-[40px]">
            <p className="text-sm font-bold text-cream-100">{origin}</p>
            {depTime && <p className="text-[11px] text-cream-300">{formatTime(depTime)}</p>}
          </div>
          <div className="flex-1 flex flex-col items-center gap-0.5 px-1">
            <div className="flex items-center gap-1 w-full">
              <div className="flex-1 h-px bg-white/20" />
              <Plane className="w-3 h-3 text-sky-500" />
              <div className="flex-1 h-px bg-white/20" />
            </div>
            <p className="text-[10px] text-cream-300 text-center">
              {duration > 0 ? formatDuration(duration) : ""}
              {duration > 0 && " · "}
              {stops === 0 ? "Nonstop" : `${stops} stop${stops > 1 ? "s" : ""}`}
            </p>
          </div>
          <div className="text-center min-w-[40px]">
            <p className="text-sm font-bold text-cream-100">{destination}</p>
            {arrTime && <p className="text-[11px] text-cream-300">{formatTime(arrTime)}</p>}
          </div>
        </div>
      )}

      {/* Tags — cap at 2 to avoid cramping on mobile */}
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {tags.slice(0, 2).map((tag) => <RecTag key={tag} tag={tag} />)}
        </div>
      )}

      {/* Pricing grid */}
      <div className="grid grid-cols-3 gap-2 pt-2 border-t border-white/10">
        {price > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-cream-300 uppercase tracking-wide">Cash</p>
            <p className="text-sm font-bold text-cream-100">${Math.round(price)}</p>
          </div>
        )}
        {points > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-cream-300 uppercase tracking-wide">Points</p>
            <p className="text-sm font-bold text-brand-300">
              {points >= 1000 ? `${(points / 1000).toFixed(0)}k` : points}
            </p>
          </div>
        )}
        {cpp > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-cream-300 uppercase tracking-wide">CPP</p>
            <p className={`text-sm font-bold ${cpp >= 2 ? "text-emerald-300" : "text-cream-200"}`}>
              {cpp.toFixed(2)}¢
            </p>
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-1.5 pt-1">
        {onToggleCompare && (
          <button
            onClick={() => onToggleCompare(item)}
            title="Compare"
            className={`${SECONDARY_CTA} ${isComparing ? "bg-brand-500/25 border-brand-400/40 text-brand-200" : ""}`}
          >
            <Scale className="w-3.5 h-3.5" />
            Compare
          </button>
        )}
        {bookingUrl && (
          <a
            href={bookingUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            title="Book externally"
            className={SECONDARY_CTA}
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Book
          </a>
        )}
        <button
          onClick={() => onAddToItinerary(item)}
          disabled={adding}
          className={PRIMARY_CTA}
        >
          {adding ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
          Add
        </button>
      </div>
    </div>
  );
}

// ─── Round-trip flight leg row ────────────────────────────────────────────────

function FlightLegRow({
  leg,
  label,
}: {
  leg: Record<string, unknown>;
  label: string;
}) {
  const airline   = (leg.airline as string) ?? "";
  // Support both camelCase (API response after toCamel) and snake_case (legacy stored data)
  const flightNum = ((leg.flightNumber  ?? leg.flight_number)  as string) ?? "";
  const origin    = (leg.origin    as string) ?? "";
  const dest      = (leg.destination as string) ?? "";
  const depTime   = ((leg.departureTime ?? leg.departure_time) as string) ?? "";
  const arrTime   = ((leg.arrivalTime   ?? leg.arrival_time)   as string) ?? "";
  const duration  = ((leg.durationMinutes ?? leg.duration_minutes) as number) ?? 0;
  const stops     = (leg.stops as number) ?? 0;
  const price     = (leg.price as number) ?? 0;
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-wide text-cream-300">{label}</span>
        <span className="text-xs text-cream-200">{airline} <span className="text-cream-300">{flightNum}</span></span>
      </div>
      <div className="flex items-center gap-2">
        <div className="text-center min-w-[36px]">
          <p className="text-sm font-bold text-cream-100">{origin}</p>
          {depTime && <p className="text-[10px] text-cream-300">{formatTime(depTime)}</p>}
        </div>
        <div className="flex-1 flex flex-col items-center gap-0.5 px-1">
          <div className="flex items-center gap-1 w-full">
            <div className="flex-1 h-px bg-white/20" />
            <Plane className="w-3 h-3 text-sky-400" />
            <div className="flex-1 h-px bg-white/20" />
          </div>
          <p className="text-[10px] text-cream-300">
            {duration > 0 ? formatDuration(duration) : ""}
            {duration > 0 && " · "}
            {stops === 0 ? "Nonstop" : `${stops} stop${stops > 1 ? "s" : ""}`}
          </p>
        </div>
        <div className="text-center min-w-[36px]">
          <p className="text-sm font-bold text-cream-100">{dest}</p>
          {arrTime && <p className="text-[10px] text-cream-300">{formatTime(arrTime)}</p>}
        </div>
        {price > 0 && (
          <p className="text-xs font-semibold text-cream-200 ml-1">${Math.round(price)}</p>
        )}
      </div>
    </div>
  );
}

// ─── Round-trip flight candidate card ────────────────────────────────────────

function RoundTripFlightCard({
  item,
  onAddToItinerary,
  adding,
  isTopPick,
  isLowScore,
}: {
  item: ItineraryItem;
  onAddToItinerary: (item: ItineraryItem) => void;
  adding: boolean;
  isTopPick?: boolean;
  isLowScore?: boolean;
}) {
  const d           = (item.details ?? {}) as Record<string, unknown>;
  const outbound    = (d.outbound as Record<string, unknown>) ?? {};
  // toCamel transforms return_flight → returnFlight; support both for backwards compat
  const returnFlight = ((d.returnFlight ?? d.return_flight) as Record<string, unknown>) ?? {};
  // toCamel transforms total_price → totalPrice, etc.
  const totalPrice  = ((d.totalPrice  ?? d.total_price)   as number) ?? 0;
  const totalPoints = ((d.totalPoints ?? d.total_points)  as number) ?? 0;
  const combinedCpp = ((d.combinedCpp ?? d.combined_cpp)  as number) ?? 0;
  const aiScore     = ((d.aiScore     ?? d.ai_score)      as number) ?? 0;

  const containerClass = `${PREMIUM_CARD_BASE} ${isTopPick ? "border-brand-400/45" : ""} ${isLowScore ? "opacity-55" : ""}`;

  return (
    <div className={containerClass}>
      {isTopPick && (
        <div className="absolute -top-2.5 left-3">
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500 text-white shadow-sm">
            <Zap className="w-2.5 h-2.5" />
            Best Pair
          </span>
        </div>
      )}

      {/* Header: round-trip label + AI score */}
      <div className="flex items-start justify-between gap-2 pt-0.5">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-cream-100 leading-tight">Round-Trip</p>
          <p className="text-xs text-cream-300 mt-0.5">Outbound + Return pair</p>
        </div>
        <AiScoreBadge score={aiScore} />
      </div>

      {/* Outbound leg */}
      <div className="rounded-xl bg-dark-300/70 border border-white/10 px-3 py-2.5">
        <FlightLegRow leg={outbound} label="Outbound" />
      </div>

      {/* Return leg */}
      <div className="rounded-xl bg-dark-300/70 border border-white/10 px-3 py-2.5">
        <FlightLegRow leg={returnFlight} label="Return" />
      </div>

      {/* Combined pricing */}
      <div className="grid grid-cols-3 gap-2 pt-2 border-t border-white/10">
        {totalPrice > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-cream-300 uppercase tracking-wide">Total Cash</p>
            <p className="text-sm font-bold text-cream-100">${Math.round(totalPrice)}</p>
          </div>
        )}
        {totalPoints > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-cream-300 uppercase tracking-wide">Total Pts</p>
            <p className="text-sm font-bold text-brand-300">
              {totalPoints >= 1000 ? `${(totalPoints / 1000).toFixed(0)}k` : totalPoints}
            </p>
          </div>
        )}
        {combinedCpp > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-cream-300 uppercase tracking-wide">CPP</p>
            <p className={`text-sm font-bold ${combinedCpp >= 2 ? "text-emerald-300" : "text-cream-200"}`}>
              {combinedCpp.toFixed(2)}¢
            </p>
          </div>
        )}
      </div>

      {/* Add button */}
      <button
        onClick={() => onAddToItinerary(item)}
        disabled={adding}
        className={`${PRIMARY_CTA} w-full`}
      >
        {adding ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
        Add Round Trip
      </button>
    </div>
  );
}

// ─── Hotel candidate card ─────────────────────────────────────────────────────

function HotelCandidateCard({
  item,
  onAddToItinerary,
  onToggleCompare,
  adding,
  isTopPick,
  isLowScore,
  isComparing,
}: {
  item: ItineraryItem;
  onAddToItinerary: (item: ItineraryItem) => void;
  onToggleCompare?: (item: ItineraryItem) => void;
  adding: boolean;
  isTopPick?: boolean;
  isLowScore?: boolean;
  isComparing?: boolean;
}) {
  const d = (item.details ?? {}) as Record<string, unknown>;
  const name          = (d.name            as string)   ?? item.title;
  const location      = (d.location        as string)   ?? item.location ?? "";
  const pricePerNight = (d.price_per_night as number)   ?? (d.pricePerNight as number) ?? item.cashPrice ?? 0;
  const rating        = (d.rating          as number)   ?? null;
  const stars         = (d.stars           as number)   ?? null;
  const amenities     = (d.amenities       as string[]) ?? [];
  const aiScore       = (d.ai_score        as number)   ?? (d.aiScore as number) ?? 0;
  const tags          = (d.tags            as string[]) ?? [];
  const explanation   = (d.explanation     as string)   ?? "";
  const nights        = (d.nights          as number)   ?? 1;
  const bookingUrl    = (d.booking_url     as string)   ?? (d.bookingUrl as string) ?? "";
  const locationScore   = (d.location_score  as number) ?? null;
  const proximityLabel  = (d.proximity_label as string) ?? null;
  const areaLabel       = (d.area_label      as string) ?? null;

  const containerClass = `${PREMIUM_CARD_BASE} ${isTopPick ? "border-brand-400/45" : ""} ${isLowScore ? "opacity-55" : ""}`;

  return (
    <div className={containerClass}>
      {isTopPick && (
        <div className="absolute -top-2.5 left-3">
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-violet-500 text-white shadow-sm">
            <Star className="w-2.5 h-2.5" />
            Top Hotel
          </span>
        </div>
      )}

      {/* Header: name + stars + AI score */}
      <div className="flex items-start justify-between gap-2 pt-0.5">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-cream-100 leading-tight">{name}</p>
          <div className="flex items-center gap-2 mt-0.5">
            {stars != null && (
              <span className="text-xs text-amber-400">{"★".repeat(Math.min(5, Math.round(stars)))}</span>
            )}
            {/* Only show raw location when it differs from the hotel name and no richer
                area/proximity badges are available — avoids repeating the address as filler. */}
            {location && location.trim().toLowerCase() !== name.trim().toLowerCase() && !(proximityLabel && areaLabel) && (
              <span className="flex items-center gap-0.5 text-xs text-cream-300 truncate">
                <MapPin className="w-3 h-3 flex-shrink-0" />
                {location}
              </span>
            )}
          </div>
        </div>
        <AiScoreBadge score={aiScore} />
      </div>

      {/* Location intelligence badges */}
      {(proximityLabel || areaLabel) && (
        <div className="flex flex-wrap gap-1.5">
          {proximityLabel && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
              <MapPin className="w-2.5 h-2.5" />
              {proximityLabel}
            </span>
          )}
          {areaLabel && areaLabel !== "Farther from center" && (
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border ${
              areaLabel === "In best area"
                ? "bg-violet-50 text-violet-700 border-violet-200"
                : "bg-sky-50 text-sky-700 border-sky-200"
            }`}>
              {areaLabel === "In best area" ? "★ " : ""}{areaLabel}
            </span>
          )}
          {locationScore !== null && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-50 text-slate-500 border border-slate-200">
              Location {Math.round(locationScore)}/100
            </span>
          )}
        </div>
      )}

      {/* Tags */}
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {tags.slice(0, 3).map((tag) => <RecTag key={tag} tag={tag} />)}
        </div>
      )}

      {/* Explanation */}
      {explanation && (
        <p className="text-xs text-cream-300 leading-relaxed">{explanation}</p>
      )}

      {/* Pricing grid */}
      <div className="grid grid-cols-3 gap-2 pt-2 border-t border-white/10">
        {pricePerNight > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-slate-400 uppercase tracking-wide">Per Night</p>
            <p className="text-sm font-bold text-cream-100">${Math.round(pricePerNight)}</p>
          </div>
        )}
        {nights > 1 && pricePerNight > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-slate-400 uppercase tracking-wide">Total</p>
            <p className="text-sm font-bold text-cream-100">${Math.round(pricePerNight * nights)}</p>
          </div>
        )}
        {rating != null && (
          <div className="text-center">
            <p className="text-[10px] text-slate-400 uppercase tracking-wide">Rating</p>
            <p className="text-sm font-bold text-amber-600">★ {rating.toFixed(1)}</p>
          </div>
        )}
      </div>

      {/* Amenities */}
      {amenities.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {amenities.slice(0, 3).map((a) => (
            <span key={a} className="px-2 py-0.5 bg-white/10 border border-white/10 rounded-full text-xs text-cream-300">{a}</span>
          ))}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-1.5 pt-1">
        {onToggleCompare && (
          <button
            onClick={() => onToggleCompare(item)}
            title="Compare"
            className={`${SECONDARY_CTA} ${isComparing ? "bg-brand-500/25 border-brand-400/40 text-brand-200" : ""}`}
          >
            <Scale className="w-3.5 h-3.5" />
            Compare
          </button>
        )}
        {bookingUrl && (
          <a
            href={bookingUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            title="Book externally"
            className={SECONDARY_CTA}
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Book
          </a>
        )}
        <button
          onClick={() => onAddToItinerary(item)}
          disabled={adding}
          className={PRIMARY_CTA}
        >
          {adding ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
          Add
        </button>
      </div>
    </div>
  );
}

// ─── Attraction tag badge ──────────────────────────────────────────────────────

function AttractionTag({ tag }: { tag: string }) {
  const style =
    tag === "Must Visit"       ? "bg-emerald-100 text-emerald-700" :
    tag === "Highly Rated"     ? "bg-amber-100 text-amber-700" :
    tag === "Top Rated"        ? "bg-amber-100 text-amber-600" :
    tag === "Tourist Favorite" ? "bg-sky-100 text-sky-700" :
    tag === "Hidden Gem"       ? "bg-violet-100 text-violet-700" :
    "bg-slate-100 text-slate-500";
  const icon =
    tag === "Must Visit"       ? <Zap className="w-2.5 h-2.5" /> :
    tag === "Highly Rated"     ? <Star className="w-2.5 h-2.5" /> :
    tag === "Hidden Gem"       ? <Sparkles className="w-2.5 h-2.5" /> :
    null;
  return (
    <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-xs font-semibold ${style}`}>
      {icon}{tag}
    </span>
  );
}

// ─── Price level indicator ─────────────────────────────────────────────────────

function PriceLevelDots({ level }: { level: number }) {
  return (
    <span className="flex items-center gap-px" title={["Free", "Inexpensive", "Moderate", "Expensive", "Very Expensive"][level] ?? ""}>
      {[0, 1, 2, 3].map((i) => (
        <DollarSign
          key={i}
          className={`w-2.5 h-2.5 ${i < level ? "text-slate-600" : "text-slate-200"}`}
        />
      ))}
    </span>
  );
}

// ─── Attraction candidate card ─────────────────────────────────────────────────

function AttractionCandidateCard({
  attraction,
  onAddToTrip,
  adding,
  isTopPick,
}: {
  attraction: AttractionSearchResult;
  onAddToTrip: (a: AttractionSearchResult) => void;
  adding: boolean;
  isTopPick?: boolean;
}) {
  const aiScore       = attraction.aiScore ?? 0;
  const rating        = attraction.rating;
  const numReviews    = attraction.numReviews;
  const mapsUrl       = `https://www.google.com/maps/search/${encodeURIComponent(attraction.name + " " + attraction.location)}`;

  const containerClass = `${PREMIUM_CARD_BASE} ${isTopPick ? "border-brand-400/45" : ""}`;

  return (
    <div className={containerClass}>
      {isTopPick && (
        <div className="absolute -top-2.5 left-3">
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500 text-white shadow-sm">
            <Zap className="w-2.5 h-2.5" />
            Top Pick
          </span>
        </div>
      )}

      {/* Header: name + AI score */}
      <div className="flex items-start justify-between gap-2 pt-0.5">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-cream-100 leading-tight">{attraction.name}</p>
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            {rating != null && (
              <span className="text-xs text-amber-500 font-semibold">★ {rating.toFixed(1)}</span>
            )}
            {numReviews != null && (
              <span className="text-xs text-cream-300">
                {numReviews >= 1000 ? `${(numReviews / 1000).toFixed(0)}k` : numReviews} reviews
              </span>
            )}
          </div>
        </div>
        <AiScoreBadge score={aiScore} />
      </div>

      {/* Description */}
      {attraction.description && (
        <p className="text-xs text-cream-300 leading-relaxed line-clamp-2">{attraction.description}</p>
      )}

      {/* Tags */}
      {attraction.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {attraction.tags.map((tag) => <AttractionTag key={tag} tag={tag} />)}
        </div>
      )}

      {/* Meta row: address, hours, duration, price */}
      <div className="flex flex-col gap-1">
        {attraction.address && (
          <div className="flex items-center gap-1 text-xs text-cream-300">
            <MapPin className="w-3 h-3 flex-shrink-0" />
            <span className="truncate">{attraction.address}</span>
          </div>
        )}
        <div className="flex items-center gap-3 flex-wrap">
          {attraction.openingHours && (
            <div className="flex items-center gap-1 text-xs text-cream-300">
              <Clock className="w-3 h-3 flex-shrink-0" />
              <span>{attraction.openingHours}</span>
            </div>
          )}
          {attraction.durationMinutes != null && (
            <span className="text-xs text-cream-300">
              {formatDuration(attraction.durationMinutes)}
            </span>
          )}
          {attraction.priceLevel != null && (
            <PriceLevelDots level={attraction.priceLevel} />
          )}
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-1.5 pt-1">
        <a
          href={mapsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className={SECONDARY_CTA}
        >
          <ExternalLink className="w-3.5 h-3.5" />
          View
        </a>
        <button
          onClick={() => onAddToTrip(attraction)}
          disabled={adding}
          className={PRIMARY_CTA}
        >
          {adding ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
          Add to Trip
        </button>
      </div>
    </div>
  );
}

// ─── Restaurant tag badge ──────────────────────────────────────────────────────

function RestaurantTag({ tag }: { tag: string }) {
  const style =
    tag === "Must Try"       ? "bg-rose-100 text-rose-700" :
    tag === "Local Favorite" ? "bg-amber-100 text-amber-700" :
    tag === "Fine Dining"    ? "bg-violet-100 text-violet-700" :
    tag === "Budget Friendly"? "bg-green-100 text-green-700" :
                               "bg-slate-100 text-slate-600";
  return <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${style}`}>{tag}</span>;
}

// ─── Restaurant candidate card ─────────────────────────────────────────────────

function RestaurantCandidateCard({
  restaurant,
  onAddToTrip,
  adding,
  isTopPick,
}: {
  restaurant: RestaurantSearchResult;
  onAddToTrip: (r: RestaurantSearchResult) => void;
  adding: boolean;
  isTopPick?: boolean;
}) {
  const aiScore    = restaurant.aiScore ?? 0;
  const rating     = restaurant.rating;
  const numReviews = restaurant.numReviews;
  const mapsUrl =
    restaurant.googleMapsUri
      ? restaurant.googleMapsUri
      : restaurant.providerPlaceId
        ? `https://www.google.com/maps/place/?q=place_id:${encodeURIComponent(restaurant.providerPlaceId)}`
        : restaurant.placeId
          ? `https://www.google.com/maps/place/?q=place_id:${encodeURIComponent(restaurant.placeId)}`
          : `https://www.google.com/maps/search/${encodeURIComponent(restaurant.name + " " + restaurant.location)}`;

  const containerClass = `${PREMIUM_CARD_BASE} gap-2 p-3 ${isTopPick ? "border-brand-400/45" : ""}`;

  return (
    <div className={containerClass}>
      {isTopPick && (
        <span className="absolute top-2 right-2 text-[9px] font-bold uppercase tracking-wide text-brand-200 bg-brand-500/20 border border-brand-400/30 px-1.5 py-0.5 rounded-full">Top Pick</span>
      )}

      <div className="flex items-start justify-between gap-2 pt-0.5">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-cream-100 leading-tight">{restaurant.name}</p>
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            <span className="text-[10px] text-cream-300 font-medium">{restaurant.cuisine}</span>
            {rating != null && (
              <span className="flex items-center gap-0.5 text-xs text-amber-500 font-semibold">
                <Star className="w-3 h-3 fill-amber-400 stroke-amber-400" />
                {rating.toFixed(1)}
                {numReviews != null && (
                  <span className="text-slate-400 font-normal ml-0.5">
                    ({numReviews >= 1000 ? `${(numReviews / 1000).toFixed(0)}k` : numReviews})
                  </span>
                )}
              </span>
            )}
          </div>
        </div>
        <AiScoreBadge score={aiScore} />
      </div>

      {/* Tags */}
      {restaurant.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {restaurant.tags.map((tag) => <RestaurantTag key={tag} tag={tag} />)}
        </div>
      )}

      {/* Meta row */}
      <div className="flex flex-col gap-1">
        {restaurant.address && (
          <div className="flex items-center gap-1 text-xs text-cream-300">
            <MapPin className="w-3 h-3 flex-shrink-0" />
            <span className="truncate">{restaurant.address}</span>
          </div>
        )}
        <div className="flex items-center gap-3 flex-wrap">
          {restaurant.openingHours && (
            <div className="flex items-center gap-1 text-xs text-cream-300">
              <Clock className="w-3 h-3 flex-shrink-0" />
              <span>{restaurant.openingHours}</span>
            </div>
          )}
          {restaurant.priceLevel != null && (
            <PriceLevelDots level={restaurant.priceLevel} />
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2 mt-1">
        <a
          href={mapsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className={SECONDARY_CTA}
        >
          <ExternalLink className="w-3.5 h-3.5" />
          Maps
        </a>
        <button
          onClick={() => onAddToTrip(restaurant)}
          disabled={adding}
          className={PRIMARY_CTA}
        >
          {adding ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
          Add to Trip
        </button>
      </div>
    </div>
  );
}

// ─── Filter pills ─────────────────────────────────────────────────────────────

function FilterPills({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { label: string; value: string | number | null }[];
  value: string | number | null;
  onChange: (v: string | number | null) => void;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[9px] font-semibold uppercase tracking-wider text-cream-300">{label}</span>
      <div className="flex flex-wrap gap-1">
        {options.map((opt) => (
          <button
            key={String(opt.value ?? "all")}
            onClick={() => onChange(opt.value === value ? null : opt.value)}
            className={`px-2 py-0.5 rounded-full text-[10px] font-medium transition-all border ${
              opt.value === value
                ? "bg-brand-500/80 text-dark-900 border-brand-400"
                : "bg-dark-300/60 text-cream-300 border-white/15 hover:border-white/35 hover:text-cream-100"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── Collapsible panel wrapper ────────────────────────────────────────────────

function CandidatePanel({
  title,
  icon,
  count,
  totalCount,
  accentColor,
  open,
  onToggle,
  sortControls,
  listRef,
  emptyMessage = "No candidates yet.",
  children,
}: {
  title: string;
  icon: React.ReactNode;
  count: number;
  totalCount?: number;
  accentColor: string;
  open: boolean;
  onToggle: () => void;
  sortControls?: React.ReactNode;
  listRef?: React.Ref<HTMLDivElement>;
  emptyMessage?: string;
  children: React.ReactNode;
}) {
  const hasData = (totalCount ?? count) > 0;
  return (
    <div className="card p-3 flex flex-col gap-2">
      <button
        onClick={onToggle}
        className="flex items-center justify-between w-full text-sm font-semibold text-cream-100"
      >
        <span className="flex items-center gap-1.5">
          {icon}
          {title}
          <span className={`text-xs font-normal ${accentColor}`}>
            ({totalCount !== undefined && totalCount !== count ? `${count}/${totalCount}` : count})
          </span>
        </span>
        {open
          ? <ChevronUp className="w-3.5 h-3.5 text-cream-300" />
          : <ChevronDown className="w-3.5 h-3.5 text-cream-300" />}
      </button>
      {open && sortControls && <div className="pt-0.5">{sortControls}</div>}
      {open && !hasData && (
        <p className="text-xs text-slate-400 py-2 text-center">
          {emptyMessage}
        </p>
      )}
      {open && hasData && (
        <div ref={listRef} className="flex flex-col gap-3 max-h-[540px] overflow-y-auto py-1 px-0.5">
          {children}
        </div>
      )}
    </div>
  );
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface TripBuilderProps {
  tripId: string;
  destination: string;
  /** ISO date strings (YYYY-MM-DD). When both are present, days are auto-derived
   *  from the date range and the "Add Day" button is hidden. */
  startDate?: string;
  endDate?: string;
  initialDays: ItineraryDay[];
  initialResults: ResearchResult[];
  /** Bump to trigger TripIdeasPanel to re-fetch saved ideas. */
  ideasRefreshKey?: number;
  /** Called when a saved idea is assigned to a day from TripIdeasPanel. */
  onIdeaAssigned?: () => void;
}

// ─── Main component ───────────────────────────────────────────────────────────

export function TripBuilder({ tripId, destination, startDate, endDate, initialDays, initialResults, ideasRefreshKey, onIdeaAssigned }: TripBuilderProps) {
  const [days,           setDays]          = useState<ItineraryDay[]>(
    [...initialDays].sort((a, b) => a.dayNumber - b.dayNumber)
  );
  const [results]                          = useState<ResearchResult[]>(initialResults);
  // Single source of truth for which day receives left-panel "+" additions.
  const [selectedDayId,  setSelectedDayId] = useState<string | null>(initialDays[0]?.id ?? null);
  const [expandedDayNumber, setExpandedDayNumber] = useState<number | null>(initialDays[0]?.dayNumber ?? null);
  const ensuredSignatureRef                = useRef<string | null>(null);

  // ── Flight / hotel candidates (trip-level items, AI pre-populated) ───────────
  const [candidateFlights,     setCandidateFlights]     = useState<ItineraryItem[]>([]);
  const [candidateHotels,      setCandidateHotels]      = useState<ItineraryItem[]>([]);
  const [candidateAttractions, setCandidateAttractions] = useState<AttractionSearchResult[]>([]);
  const [candidateRestaurants, setCandidateRestaurants] = useState<RestaurantSearchResult[]>([]);
  const [authSessionReady, setAuthSessionReady] = useState(false);
  const [flightPanelOpen,      setFlightPanelOpen]      = useState(true);
  const [hotelPanelOpen,       setHotelPanelOpen]       = useState(true);
  const [attractionPanelOpen,  setAttractionPanelOpen]  = useState(true);
  const [restaurantPanelOpen,  setRestaurantPanelOpen]  = useState(true);
  const [flightSort,           setFlightSort]           = useState<SortKey>("ai");
  const [hotelSort,            setHotelSort]            = useState<SortKey>("ai");
  const [attractionSort,       setAttractionSort]       = useState<SortKey>("ai");
  const [restaurantSort,       setRestaurantSort]       = useState<SortKey>("ai");
  const [attractionRatingFilter,    setAttractionRatingFilter]    = useState<number | null>(null);
  const [attractionTypeFilter,      setAttractionTypeFilter]      = useState<string | null>(null);
  const [restaurantCuisineFilter,   setRestaurantCuisineFilter]   = useState<string | null>(null);
  const [restaurantPriceLevelFilter, setRestaurantPriceLevelFilter] = useState<number | null>(null);
  const [restaurantRatingFilter,    setRestaurantRatingFilter]    = useState<number | null>(null);
  const [addingId,             setAddingId]             = useState<string | null>(null);
  const [toast,                setToast]                = useState<string | null>(null);
  const [activeId,             setActiveId]             = useState<UniqueIdentifier | null>(null);
  const [viewMode,             setViewMode]             = useState<"list" | "map">("list");
  const [activeMarkerId,       setActiveMarkerId]       = useState<string | null>(null);

  // ── Day plan state ───────────────────────────────────────────────────────────
  const [dayPlan,            setDayPlan]            = useState<DayPlan | null>(null);
  const [dayPlanLoading,     setDayPlanLoading]     = useState(false);
  const [dayPlanTargetDayId, setDayPlanTargetDayId] = useState<string | null>(null);

  const flightListRef      = useRef<HTMLDivElement>(null);
  const hotelListRef       = useRef<HTMLDivElement>(null);
  const attractionListRef  = useRef<HTMLDivElement>(null);
  const restaurantListRef  = useRef<HTMLDivElement>(null);
  const prevViewModeRef    = useRef<"list" | "map">("list");

  // ── Compare state ────────────────────────────────────────────────────────────
  const [compareSet,     setCompareSet]     = useState<Set<string>>(new Set());
  const [compareOpen,    setCompareOpen]    = useState(false);
  const [compareResults, setCompareResults] = useState<CompareResult[]>([]);
  const [compareLoading, setCompareLoading] = useState(false);
  const [ideasRefreshNonce, setIdeasRefreshNonce] = useState(0);
  const compareDataRef = useRef<Map<string, { name: string; itemType: string; cashPrice: number; pointsCost: number; rating?: number; lat?: number; lng?: number }>>(new Map());

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  useEffect(() => {
    setDays([...initialDays].sort((a, b) => a.dayNumber - b.dayNumber));
  }, [initialDays]);

  useEffect(() => {
    let active = true;

    const applySession = (session: Session | null) => {
      if (!active) return;
      setAuthSessionReady(!!session?.access_token);
    };

    supabase.auth.getSession().then(({ data }) => applySession(data.session));
    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => applySession(session));

    return () => {
      active = false;
      listener.subscription.unsubscribe();
    };
  }, []);

  const canonicalStartDate = normalizeIsoDate(startDate);
  const displayDays = useMemo(
    () =>
      days.map((day) => ({
        ...day,
        date: canonicalStartDate
          ? addDaysToIsoDate(canonicalStartDate, day.dayNumber - 1)
          : normalizeIsoDate(day.date),
      })),
    [days, canonicalStartDate]
  );

  // Canonical trip-candidate hydration — Level 3 Trip Data Contract Rescue.
  //
  // Single source of truth: persisted itinerary_items (day_id IS NULL) returned
  // by GET /trips/{id}/items.  The buildTripCandidateBuckets selector groups
  // them into the four product verticals + a round-trip-flight bucket.
  //
  // Replaces the prior split where flights/hotels were read from itinerary_items
  // but attractions/restaurants were read from the legacy explore_snapshot
  // cache (which could be empty after fresh creation and would then trigger a
  // slow AI Concierge "Top attractions in <city>" fallback that wrote an
  // empty snapshot back, locking the UI at 0).
  useEffect(() => {
    if (!authSessionReady) return;
    void (async () => {
      const items = await fetchTripItems(tripId);
      const buckets = buildTripCandidateBuckets(items);

      // Snapshot is a deprecated fallback: it can hydrate empty buckets but
      // it CANNOT override non-empty persisted buckets.  This guarantees that
      // create-with-search ACTIVITY/MEAL rows are always visible regardless
      // of snapshot state.
      let merged = buckets;
      if (buckets.attractions.length === 0 || buckets.restaurants.length === 0) {
        const snapshot = await fetchExploreSnapshot(tripId);
        if (snapshot) {
          merged = mergePersistedWithSnapshot(buckets, {
            attractions: snapshot.attractions,
            restaurants: snapshot.restaurants,
          });
        }
      }

      // Combine one-way + round-trip flights into the flight panel; the
      // existing card components branch on details.isRoundTrip.
      setCandidateFlights([...merged.flights, ...merged.roundTripFlights]);
      setCandidateHotels(merged.hotels);
      setCandidateAttractions(merged.attractions);
      setCandidateRestaurants(merged.restaurants);
    })();
  }, [tripId, authSessionReady]);

  // GSAP entrance animations for flight cards
  useEffect(() => {
    if (!flightListRef.current || candidateFlights.length === 0) return;
    const cards = flightListRef.current.querySelectorAll(".candidate-card");
    gsap.from(cards, { y: 24, opacity: 0, duration: 0.45, stagger: 0.07, ease: "power2.out", clearProps: "all" });
  }, [candidateFlights.length]);

  // GSAP entrance animations for hotel cards
  useEffect(() => {
    if (!hotelListRef.current || candidateHotels.length === 0) return;
    const cards = hotelListRef.current.querySelectorAll(".candidate-card");
    gsap.from(cards, { y: 24, opacity: 0, duration: 0.45, stagger: 0.07, ease: "power2.out", clearProps: "all" });
  }, [candidateHotels.length]);

  // Legacy snapshot-first Explore hydration removed (Level 3 Trip Data
  // Contract Rescue).  Attractions and restaurants are now hydrated from
  // persisted ACTIVITY / MEAL itinerary_items via the canonical selector in
  // the effect above.  The snapshot survives only as a deprecated empty-bucket
  // fallback inside that effect (it cannot zero out persisted rows).

  // GSAP entrance animations for attraction cards
  useEffect(() => {
    if (!attractionListRef.current || candidateAttractions.length === 0) return;
    const cards = attractionListRef.current.querySelectorAll(".candidate-card");
    gsap.from(cards, { y: 24, opacity: 0, duration: 0.45, stagger: 0.05, ease: "power2.out", clearProps: "all" });
  }, [candidateAttractions.length]);

  // GSAP entrance animations for restaurant cards
  useEffect(() => {
    if (!restaurantListRef.current || candidateRestaurants.length === 0) return;
    const cards = restaurantListRef.current.querySelectorAll(".candidate-card");
    gsap.from(cards, { y: 24, opacity: 0, duration: 0.45, stagger: 0.05, ease: "power2.out", clearProps: "all" });
  }, [candidateRestaurants.length]);

  // Product Surface Migration v1B — TripBuilder Explore previously rendered
  // a grouped "Areas" view and a "Best Area to Stay" card whose backends
  // derived from `_mock_attractions` and so produced fabricated
  // recommendations.  The canonical AI Concierge surface does not yet emit
  // cluster / best-area shapes, so v1B fails closed: the legacy callers are
  // removed and the grouped view + best-area card are intentionally dropped
  // from the UI rather than hidden behind a new adapter that smuggles mock
  // data through.  A canonical clustering / best-area replacement is a
  // follow-up (v1C).

  // Scroll to highlighted list item when switching from map → list view
  useEffect(() => {
    if (prevViewModeRef.current === "map" && viewMode === "list" && activeMarkerId) {
      setTimeout(() => {
        const el = document.querySelector(`[data-marker-id="${activeMarkerId}"]`);
        el?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }, 120);
    }
    prevViewModeRef.current = viewMode;
  }, [viewMode, activeMarkerId]);

  // Ensure persisted itinerary days exist for the trip date range, then re-sync.
  // Runs once per trip/date signature (handles StrictMode and avoids loops).
  useEffect(() => {
    const signature = `${tripId}:${startDate ?? ""}:${endDate ?? ""}`;
    if (ensuredSignatureRef.current === signature) return;
    ensuredSignatureRef.current = signature;

    (async () => {
      const ensured = await ensureTripDays(tripId, startDate, endDate);
      setDays(ensured.sort((a, b) => a.dayNumber - b.dayNumber));
    })();
  }, [tripId, startDate, endDate]);

  // Keep selectedDayId valid whenever days array changes (e.g. on initial load).
  useEffect(() => {
    setSelectedDayId((prev) => {
      if (prev && days.some((d) => d.id === prev)) return prev; // still valid
      return days[0]?.id ?? null;
    });
  }, [days]);

  useEffect(() => {
    setExpandedDayNumber((prev) => {
      if (prev != null && days.some((day) => day.dayNumber === prev)) return prev;
      return days[0]?.dayNumber ?? null;
    });
  }, [days]);

  const showToast = useCallback((msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }, []);

  // ── Add candidate to selected itinerary day ──────────────────────────────────

  const handleAddCandidateToItinerary = useCallback(async (item: ItineraryItem) => {
    setAddingId(item.id);
    try {
      // targetDay: use the currently selected day; fall back to first day
      const targetDay = days.find((d) => d.id === selectedDayId) ?? days[0];
      if (!targetDay) {
        showToast("No day available — days are generated from trip dates");
        return;
      }

      let newItem: ItineraryItem;
      if (item.itemType === "flight") {
        newItem = await addOneWayFlightToDay(tripId, targetDay.id, item, targetDay.items.length);
      } else if (item.itemType === "hotel") {
        // Preserve all hotel details (stars, rating, amenities, area_label, etc.)
        newItem = await addHotelToDay(tripId, targetDay.id, item, targetDay.items.length);
      } else {
        newItem = await createItem(tripId, targetDay.id, {
          itemType: item.itemType as ItemType,
          title: item.title,
          description: item.description ?? undefined,
          location: item.location ?? undefined,
          position: targetDay.items.length,
        });
      }

      setDays((prev) =>
        prev.map((d) =>
          d.id === targetDay.id ? { ...d, items: [...d.items, newItem] } : d
        )
      );
      showToast(`${item.itemType === "flight" ? "Flight" : "Hotel"} added to Day ${targetDay.dayNumber}`);
    } catch {
      showToast("Failed to add — please try again");
    } finally {
      setAddingId(null);
    }
  }, [days, selectedDayId, tripId, showToast]);

  // ── Add attraction to selected itinerary day ─────────────────────────────────

  const handleAddAttractionToItinerary = useCallback(async (attraction: AttractionSearchResult) => {
    setAddingId(attraction.id);
    try {
      const targetDay = days.find((d) => d.id === selectedDayId) ?? days[0];
      if (!targetDay) {
        showToast("No day available — days are generated from trip dates");
        return;
      }

      // addAttractionToDay sets the day_id correctly on the backend
      const newItem = await addAttractionToDay(tripId, targetDay.id, attraction);

      setDays((prev) =>
        prev.map((d) =>
          d.id === targetDay.id ? { ...d, items: [...d.items, newItem] } : d
        )
      );
      showToast(`${attraction.name.split(" —")[0]} added to Day ${targetDay.dayNumber}`);
    } catch {
      showToast("Failed to add — please try again");
    } finally {
      setAddingId(null);
    }
  }, [days, selectedDayId, tripId, showToast]);

  // ── Add restaurant to selected itinerary day ────────────────────────────────

  const handleAddRestaurantToItinerary = useCallback(async (restaurant: RestaurantSearchResult) => {
    setAddingId(restaurant.id);
    try {
      const targetDay = days.find((d) => d.id === selectedDayId) ?? days[0];
      if (!targetDay) {
        showToast("No day available — days are generated from trip dates");
        return;
      }

      // addRestaurantToDay sets the day_id correctly on the backend
      const newItem = await addRestaurantToDay(tripId, targetDay.id, restaurant);

      setDays((prev) =>
        prev.map((d) =>
          d.id === targetDay.id ? { ...d, items: [...d.items, newItem] } : d
        )
      );
      showToast(`${restaurant.name} added to Day ${targetDay.dayNumber}`);
    } catch {
      showToast("Failed to add — please try again");
    } finally {
      setAddingId(null);
    }
  }, [days, selectedDayId, tripId, showToast]);

  // ── Add round-trip pair: outbound to day 1, return to last day ──────────────

  // Outbound goes to Day 1 (departure day); return goes to the final day (arrival home).
  const handleAddRoundTripToItinerary = useCallback(async (item: ItineraryItem) => {
    setAddingId(item.id);
    try {
      const d = (item.details ?? {}) as Record<string, unknown>;
      const outbound = (d.outbound as Record<string, unknown>) ?? {};
      // toCamel converts return_flight → returnFlight; support both
      const ret = ((d.returnFlight ?? d.return_flight) as Record<string, unknown>) ?? {};

      const firstDay = days[0];
      const lastDay  = days.length > 1 ? days[days.length - 1] : days[0];

      if (!firstDay) {
        showToast("No days available — days are generated from trip dates");
        return;
      }

      const outboundItem = await addRoundTripOutboundToDay(
        tripId, firstDay.id, outbound, firstDay.items.length
      );
      const returnItem = await addRoundTripReturnToDay(
        tripId, lastDay.id, ret, lastDay.items.length
      );

      setDays((prev) =>
        prev.map((day) => {
          if (day.id === firstDay.id && day.id === lastDay.id) {
            return { ...day, items: [...day.items, outboundItem, returnItem] };
          }
          if (day.id === firstDay.id) return { ...day, items: [...day.items, outboundItem] };
          if (day.id === lastDay.id)  return { ...day, items: [...day.items, returnItem]  };
          return day;
        })
      );
      const returnDayNum = lastDay.dayNumber;
      showToast(`Round-trip added — outbound on Day 1, return on Day ${returnDayNum}`);
    } catch {
      showToast("Failed to add — please try again");
    } finally {
      setAddingId(null);
    }
  }, [days, tripId, showToast]);

  // ── Remove item from a day ───────────────────────────────────────────────────

  const handleRemoveItem = useCallback(async (itemId: string, dayId: string) => {
    setDays((prev) =>
      prev.map((d) =>
        d.id === dayId
          ? { ...d, items: d.items.filter((i) => i.id !== itemId).map((i, idx) => ({ ...i, position: idx })) }
          : d
      )
    );
    try { await deleteItem(itemId); } catch { /* silently ignore */ }
  }, []);

  const handleMoveItemToIdeas = useCallback(async (itemId: string, dayId: string) => {
    setDays((prev) =>
      prev.map((d) =>
        d.id === dayId
          ? { ...d, items: d.items.filter((i) => i.id !== itemId).map((i, idx) => ({ ...i, position: idx })) }
          : d
      )
    );
    try {
      await moveIdeaToTripIdeas(itemId);
      setIdeasRefreshNonce((k) => k + 1);
    } catch {
      showToast("Failed to move idea back to Trip Ideas");
    }
  }, [showToast]);

  // ── Add empty note to a day ──────────────────────────────────────────────────

  const handleAddToDay = useCallback(async (dayId: string) => {
    const day = days.find((d) => d.id === dayId);
    if (!day) return;
    try {
      const newItem = await createItem(tripId, dayId, {
        itemType: "note" as ItemType,
        title: "New item",
        position: day.items.length,
      });
      setDays((prev) =>
        prev.map((d) => d.id === dayId ? { ...d, items: [...d.items, newItem] } : d)
      );
    } catch { /* silently ignore */ }
  }, [days, tripId]);

  // ── Add new day (only when trip has no fixed dates) ──────────────────────────
  const handleAddDay = useCallback(async () => {
    const nextNum = days.length + 1;
    try {
      const newDay = await createDay(tripId, { dayNumber: nextNum, title: `Day ${nextNum}` });
      setDays((prev) => [...prev, newDay].sort((a, b) => a.dayNumber - b.dayNumber));
    } catch { /* silently ignore */ }
  }, [days.length, tripId]);

  // Whether days are date-locked (derived from trip dates) — disables manual Add Day
  const daysAreDateLocked = Boolean(startDate && endDate);
  const canManuallyAddExpectedDay = !daysAreDateLocked;

  // ── Day plan: fetch suggestions and add items to a specific day ─────────────

  const handlePlanDay = useCallback(async (dayId: string, dayNumber: number) => {
    setDayPlanTargetDayId(dayId);
    setDayPlanLoading(true);
    try {
      const plan = await fetchDayPlan(tripId, dayNumber);
      setDayPlan(plan);
    } catch {
      showToast("Failed to generate day plan — please try again");
    } finally {
      setDayPlanLoading(false);
    }
  }, [tripId, showToast]);

  const handlePlanAddAttraction = useCallback(async (attraction: AttractionSearchResult) => {
    if (!dayPlanTargetDayId) return;
    const newItem = await addAttractionToDay(tripId, dayPlanTargetDayId, attraction);
    setDays((prev) =>
      prev.map((d) => d.id === dayPlanTargetDayId ? { ...d, items: [...d.items, newItem] } : d)
    );
  }, [dayPlanTargetDayId, tripId]);

  const handlePlanAddRestaurant = useCallback(async (restaurant: RestaurantSearchResult) => {
    if (!dayPlanTargetDayId) return;
    const newItem = await addRestaurantToDay(tripId, dayPlanTargetDayId, restaurant);
    setDays((prev) =>
      prev.map((d) => d.id === dayPlanTargetDayId ? { ...d, items: [...d.items, newItem] } : d)
    );
  }, [dayPlanTargetDayId, tripId]);

  // ── Add research result by clicking "+" ─────────────────────────────────────

  const handleAddResult = useCallback(async (result: ResearchResult) => {
    const targetDay = days.find((d) => d.id === selectedDayId) ?? days[0];
    if (!targetDay) return;
    try {
      const newItem = await createItem(tripId, targetDay.id, {
        itemType: result.category as ItemType,
        title: result.title,
        description: result.description,
        location: result.location,
        position: targetDay.items.length,
        bookingOptions: result.bookingOptions,
      });
      setDays((prev) =>
        prev.map((d) => d.id === targetDay.id ? { ...d, items: [...d.items, newItem] } : d)
      );
    } catch { /* silently ignore */ }
  }, [days, selectedDayId, tripId]);

  // ── Compare ──────────────────────────────────────────────────────────────────

  const handleToggleCompareItem = useCallback((item: ItineraryItem) => {
    setCompareSet((prev) => {
      const next = new Set(prev);
      if (next.has(item.id)) {
        next.delete(item.id);
        compareDataRef.current.delete(item.id);
      } else {
        next.add(item.id);
        compareDataRef.current.set(item.id, {
          name: item.title,
          itemType: item.itemType,
          cashPrice: item.cashPrice ?? 0,
          pointsCost: item.pointsPrice ?? 0,
          lat: (item.details as Record<string, unknown>)?.lat as number | undefined,
          lng: (item.details as Record<string, unknown>)?.lng as number | undefined,
        });
      }
      return next;
    });
  }, []);

  const handleCompare = useCallback(async () => {
    const items = Array.from(compareSet).map((id) => {
      const data = compareDataRef.current.get(id)!;
      return { id, ...data };
    });
    if (items.length < 2) return;
    setCompareLoading(true);
    try {
      const results = await compareItems(items);
      setCompareResults(results);
      setCompareOpen(true);
    } catch { /* silently ignore */ }
    finally { setCompareLoading(false); }
  }, [compareSet]);

  // ── Route summary for selected items that have coordinates ───────────────────
  const compareRouteSummary = useMemo(() => {
    const geoPoints = Array.from(compareSet)
      .map((id) => compareDataRef.current.get(id))
      .filter((d): d is NonNullable<typeof d> => d != null && d.lat != null && d.lng != null);
    if (geoPoints.length < 2) return null;
    const estimates = [];
    for (let i = 0; i < geoPoints.length - 1; i++) {
      estimates.push(estimateTravel(geoPoints[i].lat!, geoPoints[i].lng!, geoPoints[i + 1].lat!, geoPoints[i + 1].lng!));
    }
    return sumRoute(estimates);
  }, [compareSet]);

  // ── DnD ──────────────────────────────────────────────────────────────────────

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(event.active.id);
  }, []);

  const handleDragCancel = useCallback(({}: DragCancelEvent) => {
    setActiveId(null);
  }, []);

  const resolveTargetDayId = useCallback((overId: UniqueIdentifier, overData?: Record<string, unknown>) => {
    if (overData?.type === "itinerary-item") {
      const overItem = overData.item as ItineraryItem | undefined;
      return overItem?.dayId ?? null;
    }
    if (overData?.type === "day") {
      const dayId = overData.dayId;
      return typeof dayId === "string" ? dayId : null;
    }
    const overIdStr = String(overId);
    return overIdStr.startsWith("day-") ? overIdStr.replace("day-", "") : null;
  }, []);

  const handleDragOver = useCallback((event: DragOverEvent) => {
    const { active, over } = event;
    if (!over) return;
    const activeData = active.data.current;
    if (!activeData || activeData.type !== "itinerary-item") return;
    // Keep hover behavior as visual-only (useDroppable isOver styles in day columns).
    // Do not mutate committed itinerary state until onDragEnd.
  }, []);

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    setActiveId(null);
    const { active, over } = event;
    if (!over) return;
    const activeData = active.data.current;
    const overData   = over.data.current;

    if (activeData?.type === "result") {
      const result: ResearchResult = activeData.result;
      let targetDayId: string | null = null;
      if (overData?.type === "day") targetDayId = overData.dayId;
      else if (overData?.type === "itinerary-item") targetDayId = overData.item.dayId;
      else { const s = String(over.id); if (s.startsWith("day-")) targetDayId = s.replace("day-", ""); }
      if (!targetDayId) return;
      const targetDay = days.find((d) => d.id === targetDayId);
      if (!targetDay) return;
      createItem(tripId, targetDayId, {
        itemType: result.category as ItemType,
        title: result.title,
        description: result.description,
        location: result.location,
        position: targetDay.items.length,
        bookingOptions: result.bookingOptions,
      }).then((newItem) => {
        setDays((prev) => prev.map((d) => d.id !== targetDayId ? d : { ...d, items: [...d.items, newItem] }));
      }).catch(() => {});
      return;
    }

    if (activeData?.type === "itinerary-item") {
      const sourceItem: ItineraryItem = activeData.item;
      const targetDayId = resolveTargetDayId(over.id, overData as Record<string, unknown> | undefined);
      if (!targetDayId) return;

      const updates: Array<{ itemId: string; patch: Partial<ItineraryItem> }> = [];
      setDays((prev) => {
        const sourceDay = prev.find((day) => day.items.some((item) => item.id === sourceItem.id));
        const destinationDay = prev.find((day) => day.id === targetDayId);
        if (!sourceDay || !destinationDay) return prev;

        const sourceIndex = sourceDay.items.findIndex((item) => item.id === sourceItem.id);
        if (sourceIndex === -1) return prev;
        const overItemId = overData?.type === "itinerary-item" ? String(over.id) : null;

        if (sourceDay.id === destinationDay.id) {
          if (!overItemId) return prev;
          const destinationIndex = sourceDay.items.findIndex((item) => item.id === overItemId);
          if (destinationIndex === -1 || destinationIndex === sourceIndex) return prev;
          const nextDays = prev.map((day) => (
            day.id === sourceDay.id
              ? { ...day, items: arrayMove(day.items, sourceIndex, destinationIndex).map((item, idx) => ({ ...item, position: idx })) }
              : day
          ));
          const persistedDay = nextDays.find((day) => day.id === sourceDay.id);
          persistedDay?.items.forEach((item) => updates.push({ itemId: item.id, patch: { position: item.position } }));
          return nextDays;
        }

        const movedItem = sourceDay.items[sourceIndex];
        const sourceItems = sourceDay.items.filter((item) => item.id !== sourceItem.id);
        const destinationItems = [...destinationDay.items.filter((item) => item.id !== sourceItem.id)];
        const insertIndex = overItemId
          ? destinationItems.findIndex((item) => item.id === overItemId)
          : destinationItems.length;
        const boundedInsertIndex = Math.max(0, Math.min(insertIndex === -1 ? destinationItems.length : insertIndex, destinationItems.length));
        destinationItems.splice(boundedInsertIndex, 0, { ...movedItem, dayId: destinationDay.id });

        const nextDays = prev.map((day) => {
          if (day.id === sourceDay.id) {
            return { ...day, items: sourceItems.map((item, idx) => ({ ...item, position: idx })) };
          }
          if (day.id === destinationDay.id) {
            return { ...day, items: destinationItems.map((item, idx) => ({ ...item, position: idx })) };
          }
          return day;
        });
        const persistedSourceDay = nextDays.find((day) => day.id === sourceDay.id);
        const persistedDestinationDay = nextDays.find((day) => day.id === destinationDay.id);
        persistedSourceDay?.items.forEach((item) => updates.push({ itemId: item.id, patch: { position: item.position } }));
        persistedDestinationDay?.items.forEach((item) => {
          if (item.id === sourceItem.id) {
            updates.push({ itemId: item.id, patch: { dayId: destinationDay.id, position: item.position } });
            return;
          }
          updates.push({ itemId: item.id, patch: { position: item.position } });
        });
        return nextDays;
      });

      updates.forEach(({ itemId, patch }) => updateItem(itemId, patch).catch(() => {}));
    }
  }, [days, tripId, resolveTargetDayId]);

  // ── Drag overlay source item ─────────────────────────────────────────────────

  const activeDragItem: ItineraryItem | ResearchResult | null = (() => {
    if (!activeId) return null;
    const idStr = String(activeId);
    if (idStr.startsWith("result-")) {
      return results.find((r) => r.id === idStr.replace("result-", "")) ?? null;
    }
    for (const day of days) {
      const item = day.items.find((i) => i.id === idStr);
      if (item) return item;
    }
    return null;
  })();
  const isResultDrag = activeDragItem !== null && "category" in activeDragItem;

  // ─────────────────────────────────────────────────────────────────────────────

  const sortedFlights     = sortFlights(candidateFlights, flightSort);
  const sortedHotels      = sortHotels(candidateHotels, hotelSort);
  const sortedAttractions = sortAttractions(candidateAttractions, attractionSort);
  const sortedRestaurants = sortRestaurants(candidateRestaurants, restaurantSort);

  const availableCuisines = useMemo(
    () => [...new Set(candidateRestaurants.map((r) => r.cuisine).filter(Boolean))].sort() as string[],
    [candidateRestaurants],
  );
  const filteredAttractions = filterAttractions(sortedAttractions, attractionRatingFilter, attractionTypeFilter);
  const filteredRestaurants = filterRestaurants(sortedRestaurants, restaurantCuisineFilter, restaurantPriceLevelFilter, restaurantRatingFilter);

  const topFlight = sortedFlights[0] ?? null;
  const topHotel  = sortedHotels[0] ?? null;

  return (
    <>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragCancel={handleDragCancel}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
      >
        <div className="flex items-start gap-4 min-h-[500px]">

          {/* ── Left Panel: AI-ranked candidates ──────────────────────────── */}
          <div className="w-80 flex-shrink-0 flex flex-col gap-3 overflow-y-auto pr-0.5">

            {/* Summary bar */}
            <SummaryBar topFlight={topFlight} topHotel={topHotel} />

            {/* Flights section */}
            <CandidatePanel
              title="Flights"
              icon={<Plane className="w-3.5 h-3.5 text-sky-500" />}
              count={sortedFlights.length}
              accentColor="text-sky-500"
              open={flightPanelOpen}
              onToggle={() => setFlightPanelOpen((v) => !v)}
              emptyMessage="No flight options are available yet. Try refreshing this trip or creating it again if this continues."
              sortControls={
                <SortControl
                  keys={[
                    { key: "ai",       label: "AI Score" },
                    { key: "price",    label: "Price"    },
                    { key: "cpp",      label: "CPP"      },
                    { key: "duration", label: "Duration" },
                  ]}
                  current={flightSort}
                  onChange={setFlightSort}
                />
              }
              listRef={flightListRef}
            >
              {(() => {
                // Render one-way first, then round-trip pairs, each with a section label.
                // Sorting within each group is preserved from sortedFlights (AI-score order).
                const oneWay     = sortedFlights.filter((it) => { const d = (it.details ?? {}) as Record<string, unknown>; return !(d.isRoundTrip ?? d.is_round_trip); });
                const roundTrip  = sortedFlights.filter((it) => { const d = (it.details ?? {}) as Record<string, unknown>; return !!(d.isRoundTrip ?? d.is_round_trip); });
                const showOWLabel = oneWay.length > 0 && roundTrip.length > 0;
                const showRTLabel = roundTrip.length > 0 && oneWay.length > 0;
                const owTop20 = Math.max(1, Math.ceil(oneWay.length * 0.2));
                const rtTop20 = Math.max(1, Math.ceil(roundTrip.length * 0.2));
                const nodes: React.ReactNode[] = [];
                if (showOWLabel) {
                  nodes.push(
                    <p key="ow-label" className="text-[10px] font-semibold uppercase tracking-[0.08em] text-sky-400/70">
                      One-way options
                    </p>
                  );
                }
                oneWay.forEach((item, idx) => {
                  nodes.push(
                    <FlightCandidateCard
                      key={item.id}
                      item={item}
                      onAddToItinerary={handleAddCandidateToItinerary}
                      onToggleCompare={handleToggleCompareItem}
                      adding={addingId === item.id}
                      isTopPick={flightSort === "ai" && idx < owTop20}
                      isLowScore={false}
                      isComparing={compareSet.has(item.id)}
                    />
                  );
                });
                if (showRTLabel) {
                  nodes.push(
                    <p key="rt-label" className="text-[10px] font-semibold uppercase tracking-[0.08em] text-sky-400/70 pt-1">
                      Round-trip pairs
                    </p>
                  );
                }
                roundTrip.forEach((item, idx) => {
                  nodes.push(
                    <RoundTripFlightCard
                      key={item.id}
                      item={item}
                      onAddToItinerary={handleAddRoundTripToItinerary}
                      adding={addingId === item.id}
                      isTopPick={flightSort === "ai" && idx < rtTop20}
                      isLowScore={false}
                    />
                  );
                });
                return nodes;
              })()}
            </CandidatePanel>

            {/* Hotels section */}
            <CandidatePanel
              title="Hotels"
              icon={<Hotel className="w-3.5 h-3.5 text-violet-500" />}
              count={sortedHotels.length}
              accentColor="text-violet-500"
              open={hotelPanelOpen}
              onToggle={() => setHotelPanelOpen((v) => !v)}
              emptyMessage="No hotel options are available yet. Try refreshing this trip or creating it again if this continues."
              sortControls={
                <SortControl
                  keys={[
                    { key: "ai",       label: "AI Score" },
                    { key: "price",    label: "Price"    },
                    { key: "rating",   label: "Rating"   },
                    { key: "location", label: "Location" },
                  ]}
                  current={hotelSort}
                  onChange={setHotelSort}
                />
              }
              listRef={hotelListRef}
            >
              {(() => {
                const top20 = Math.max(1, Math.ceil(sortedHotels.length * 0.2));
                const bot20 = sortedHotels.length > 2
                  ? Math.max(1, Math.ceil(sortedHotels.length * 0.2))
                  : 0;
                return sortedHotels.map((item, idx) => (
                  <HotelCandidateCard
                    key={item.id}
                    item={item}
                    onAddToItinerary={handleAddCandidateToItinerary}
                    onToggleCompare={handleToggleCompareItem}
                    adding={addingId === item.id}
                    isTopPick={hotelSort === "ai" && idx < top20}
                    isLowScore={hotelSort === "ai" && bot20 > 0 && idx >= sortedHotels.length - bot20}
                    isComparing={compareSet.has(item.id)}
                  />
                ));
              })()}
            </CandidatePanel>

            {/* ── Explore: List / Map / Group toggle ────────────────────── */}
            <div className="flex items-center justify-between px-1 pt-0.5">
              <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Explore</span>
              <div className="flex items-center bg-slate-100 rounded-lg p-0.5 gap-0.5">
                <button
                  onClick={() => setViewMode("list")}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                    viewMode === "list"
                      ? "bg-white text-slate-700 shadow-sm"
                      : "text-slate-500 hover:text-slate-700"
                  }`}
                >
                  <LayoutList className="w-3 h-3" />
                  List
                </button>
                <button
                  onClick={() => setViewMode("map")}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                    viewMode === "map"
                      ? "bg-white text-slate-700 shadow-sm"
                      : "text-slate-500 hover:text-slate-700"
                  }`}
                >
                  <MapIcon className="w-3 h-3" />
                  Map
                </button>
              </div>
            </div>

            {viewMode === "map" ? (
              /* ── Map view ──────────────────────────────────────────────── */
              <div className="flex-1" style={{ minHeight: 520 }}>
                <TripMapView
                  destination={destination}
                  attractions={filteredAttractions}
                  restaurants={filteredRestaurants}
                  activeMarkerId={activeMarkerId}
                  bestArea={null}
                  onMarkerClick={(id) => setActiveMarkerId(id)}
                  onAddAttraction={handleAddAttractionToItinerary}
                  onAddRestaurant={handleAddRestaurantToItinerary}
                />
              </div>
            ) : (
              /* ── List view ─────────────────────────────────────────────── */
              <>
                {/* Attractions section */}
                <CandidatePanel
                  title="Attractions"
                  icon={<Sparkles className="w-3.5 h-3.5 text-emerald-500" />}
                  count={filteredAttractions.length}
                  totalCount={candidateAttractions.length}
                  accentColor="text-emerald-500"
                  open={attractionPanelOpen}
                  onToggle={() => setAttractionPanelOpen((v) => !v)}
                  emptyMessage="No attractions are available yet. Try refreshing this trip or creating it again if this continues."
                  sortControls={
                    <div className="flex flex-col gap-2">
                      <SortControl
                        keys={[
                          { key: "ai",     label: "AI Score" },
                          { key: "rating", label: "Rating"   },
                        ]}
                        current={attractionSort}
                        onChange={setAttractionSort}
                      />
                      <FilterPills
                        label="Rating"
                        options={[
                          { label: "All",  value: null },
                          { label: "3.5+", value: 3.5  },
                          { label: "4.0+", value: 4.0  },
                          { label: "4.5+", value: 4.5  },
                        ]}
                        value={attractionRatingFilter}
                        onChange={(v) => setAttractionRatingFilter(v as number | null)}
                      />
                      <FilterPills
                        label="Type"
                        options={[
                          { label: "All",       value: null        },
                          { label: "Nature",    value: "outdoor"   },
                          { label: "Museum",    value: "museums"   },
                          { label: "Landmark",  value: "landmarks" },
                          { label: "Tours",     value: "tours"     },
                          { label: "Shopping",  value: "shopping"  },
                          { label: "Nightlife", value: "nightlife" },
                        ]}
                        value={attractionTypeFilter}
                        onChange={(v) => setAttractionTypeFilter(v as string | null)}
                      />
                    </div>
                  }
                  listRef={attractionListRef}
                >
                  {filteredAttractions.length === 0 ? (
                    <p className="text-xs text-slate-400 py-4 text-center">No attractions match the selected filters.</p>
                  ) : (
                    (() => {
                      const top20 = Math.max(1, Math.ceil(filteredAttractions.length * 0.2));
                      return filteredAttractions.map((attraction, idx) => (
                        <div
                          key={attraction.id}
                          data-marker-id={attraction.id}
                          onMouseEnter={() => setActiveMarkerId(attraction.id)}
                          onMouseLeave={() => setActiveMarkerId(null)}
                          className={`rounded-2xl transition-all ${
                            activeMarkerId === attraction.id
                              ? "ring-2 ring-sky-400 ring-offset-1"
                              : ""
                          }`}
                        >
                          <AttractionCandidateCard
                            attraction={attraction}
                            onAddToTrip={handleAddAttractionToItinerary}
                            adding={addingId === attraction.id}
                            isTopPick={attractionSort === "ai" && idx < top20 && (attraction.aiScore ?? 0) > 0}
                          />
                        </div>
                      ));
                    })()
                  )}
                </CandidatePanel>

                {/* Restaurants section */}
                <CandidatePanel
                  title="Restaurants"
                  icon={<UtensilsCrossed className="w-3.5 h-3.5 text-rose-500" />}
                  count={filteredRestaurants.length}
                  totalCount={candidateRestaurants.length}
                  accentColor="text-rose-500"
                  open={restaurantPanelOpen}
                  onToggle={() => setRestaurantPanelOpen((v) => !v)}
                  emptyMessage="No restaurants are available yet. Try refreshing this trip or creating it again if this continues."
                  sortControls={
                    <div className="flex flex-col gap-2">
                      <SortControl
                        keys={[
                          { key: "ai",     label: "Best Value" },
                          { key: "rating", label: "Rating"     },
                          { key: "price",  label: "Price"      },
                        ]}
                        current={restaurantSort}
                        onChange={setRestaurantSort}
                      />
                      <FilterPills
                        label="Rating"
                        options={[
                          { label: "All",  value: null },
                          { label: "3.5+", value: 3.5  },
                          { label: "4.0+", value: 4.0  },
                          { label: "4.5+", value: 4.5  },
                        ]}
                        value={restaurantRatingFilter}
                        onChange={(v) => setRestaurantRatingFilter(v as number | null)}
                      />
                      <FilterPills
                        label="Price"
                        options={[
                          { label: "All",  value: null },
                          { label: "$",    value: 1    },
                          { label: "$$",   value: 2    },
                          { label: "$$$",  value: 3    },
                          { label: "$$$$", value: 4    },
                        ]}
                        value={restaurantPriceLevelFilter}
                        onChange={(v) => setRestaurantPriceLevelFilter(v as number | null)}
                      />
                      {availableCuisines.length > 0 && (
                        <FilterPills
                          label="Cuisine"
                          options={[
                            { label: "All", value: null },
                            ...availableCuisines.map((c) => ({ label: c, value: c.toLowerCase() })),
                          ]}
                          value={restaurantCuisineFilter}
                          onChange={(v) => setRestaurantCuisineFilter(v as string | null)}
                        />
                      )}
                    </div>
                  }
                  listRef={restaurantListRef}
                >
                  {filteredRestaurants.length === 0 ? (
                    <p className="text-xs text-slate-400 py-4 text-center">No restaurants match the selected filters.</p>
                  ) : (
                    (() => {
                      const top20 = Math.max(1, Math.ceil(filteredRestaurants.length * 0.2));
                      return filteredRestaurants.map((restaurant, idx) => (
                        <div
                          key={restaurant.id}
                          data-marker-id={restaurant.id}
                          onMouseEnter={() => setActiveMarkerId(restaurant.id)}
                          onMouseLeave={() => setActiveMarkerId(null)}
                          className={`rounded-2xl transition-all ${
                            activeMarkerId === restaurant.id
                              ? "ring-2 ring-orange-400 ring-offset-1"
                              : ""
                          }`}
                        >
                          <RestaurantCandidateCard
                            restaurant={restaurant}
                            onAddToTrip={handleAddRestaurantToItinerary}
                            adding={addingId === restaurant.id}
                            isTopPick={restaurantSort === "ai" && idx < top20 && (restaurant.aiScore ?? 0) > 0}
                          />
                        </div>
                      ));
                    })()
                  )}
                </CandidatePanel>
              </>
            )}

            {/* Activities / research results */}
            {results.length > 0 && (
              <div className="card p-3 flex flex-col gap-2">
                <h2 className="text-sm font-semibold text-slate-700 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-slate-400" />
                  Activities
                </h2>
                <div className="flex flex-col gap-2 max-h-[360px] overflow-y-auto">
                  {results.map((result) => (
                    <SearchResultCard
                      key={result.id}
                      result={result}
                      onAdd={handleAddResult}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* ── Right Panel: Itinerary Timeline ───────────────────────────── */}
          <div className="flex-1 flex flex-col gap-3 overflow-visible">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <h2 className="text-sm font-semibold text-slate-700">
                Itinerary
                <span className="ml-2 text-slate-400 font-normal">
                  {days.reduce((sum, d) => sum + d.items.length, 0)} items across {days.length} day{days.length !== 1 ? "s" : ""}
                </span>
              </h2>
              <div className="flex items-center gap-2">
                {/* Target day selector — left-panel "+" buttons add to this day */}
                {days.length > 0 && (
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wide">Adding to:</span>
                    <select
                      value={selectedDayId ?? ""}
                      onChange={(e) => setSelectedDayId(e.target.value || null)}
                      className="text-xs font-semibold text-sky-700 bg-sky-50 border border-sky-200 rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-sky-400"
                    >
                      {displayDays.map((d) => (
                        <option key={d.id} value={d.id}>
                          Day {d.dayNumber}{d.date ? ` · ${d.date}` : ""}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                {/* "Add Day" only shown when days are not auto-derived from trip dates */}
                {canManuallyAddExpectedDay && (
                  <button onClick={handleAddDay} className="btn-ghost py-1.5 text-xs">
                    <CalendarPlus className="w-3.5 h-3.5" />
                    Add Day
                  </button>
                )}
              </div>
            </div>

            <TripIdeasPanel
              tripId={tripId}
              days={displayDays}
              refreshKey={(ideasRefreshKey ?? 0) + ideasRefreshNonce}
              onIdeaAssigned={onIdeaAssigned}
            />

            <div className="flex flex-col gap-3 pr-0.5 overflow-visible">
              <SortableContext items={days.map((d) => d.id)} strategy={verticalListSortingStrategy}>
                {displayDays.map((day) => (
                  <ItineraryDayColumn
                    key={day.id}
                    day={day}
                    isSelected={day.id === selectedDayId}
                    isExpanded={expandedDayNumber === day.dayNumber}
                    onSelect={setSelectedDayId}
                    onToggleExpanded={(dayNumber) =>
                      setExpandedDayNumber((prev) => (prev === dayNumber ? null : dayNumber))
                    }
                    onRemoveItem={handleRemoveItem}
                    onMoveItemToIdeas={handleMoveItemToIdeas}
                    onAddItem={handleAddToDay}
                    onToggleCompare={handleToggleCompareItem}
                    compareSet={compareSet}
                    onPlanDay={handlePlanDay}
                    planDayLoading={dayPlanLoading && dayPlanTargetDayId === day.id}
                  />
                ))}
              </SortableContext>

              {days.length === 0 && (
                <div className="card p-8 text-center text-slate-400">
                  <CalendarPlus className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                  <p className="text-sm font-medium text-slate-500">No days yet</p>
                  <p className="text-xs mt-1">
                    {daysAreDateLocked
                      ? "Days are being generated from your trip dates…"
                      : "Click “Add Day” or set trip start/end dates to auto-generate days."}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── Compare bar ──────────────────────────────────────────────────── */}
        {compareSet.size > 0 && (
          <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-3 px-5 py-3 bg-slate-900 text-white rounded-2xl shadow-2xl ring-1 ring-white/10">
            <Scale className="w-4 h-4 text-violet-400 flex-shrink-0" />
            <div className="flex items-center gap-1">
              {Array.from({ length: Math.min(compareSet.size, 10) }).map((_, i) => (
                <div key={i} className="w-2 h-2 rounded-full bg-violet-400" />
              ))}
            </div>
            <span className="text-sm font-medium text-slate-200">
              {compareSet.size} item{compareSet.size !== 1 ? "s" : ""}
              {compareSet.size < 2 && <span className="text-slate-400 text-xs ml-1">(need 2+)</span>}
            </span>
            {compareRouteSummary && (
              <>
                <div className="w-px h-4 bg-slate-700" />
                <span className="flex items-center gap-1 text-xs text-emerald-400">
                  <Navigation className="w-3 h-3" />
                  {compareRouteSummary.totalKm} km · ~{compareRouteSummary.totalDriveMin} min drive
                </span>
              </>
            )}
            <div className="w-px h-4 bg-slate-700" />
            <button
              onClick={handleCompare}
              disabled={compareSet.size < 2 || compareLoading}
              className="px-4 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed text-sm font-semibold transition-colors flex items-center gap-1.5"
            >
              {compareLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <BarChart2 className="w-3.5 h-3.5" />}
              Compare
            </button>
            <button
              onClick={() => { setCompareSet(new Set()); compareDataRef.current.clear(); }}
              className="text-slate-500 hover:text-slate-200 text-xs transition-colors"
            >
              Clear
            </button>
          </div>
        )}

        {/* ── Drag Overlay ─────────────────────────────────────────────────── */}
        <DragOverlay>
          {activeDragItem && isResultDrag && (
            <div className="rotate-1 scale-105 shadow-2xl opacity-95 w-72">
              <SearchResultCard result={activeDragItem as ResearchResult} onAdd={() => {}} />
            </div>
          )}
          {activeDragItem && !isResultDrag && (
            <div className="rotate-1 scale-105 shadow-2xl opacity-95">
              <ItineraryItemCard item={activeDragItem as ItineraryItem} onRemove={() => {}} />
            </div>
          )}
        </DragOverlay>
      </DndContext>

      {/* ── Compare Modal ──────────────────────────────────────────────────── */}
      {compareOpen && compareResults.length > 0 && (
        <CompareModal results={compareResults} onClose={() => setCompareOpen(false)} />
      )}

      {/* ── Day Plan Modal ───────────────────────────────────────────────────── */}
      {dayPlan && (
        <DayPlanModal
          plan={dayPlan}
          onClose={() => setDayPlan(null)}
          onAddAttraction={handlePlanAddAttraction}
          onAddRestaurant={handlePlanAddRestaurant}
        />
      )}

      {/* ── Toast ────────────────────────────────────────────────────────────── */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 bg-slate-900 text-white rounded-xl shadow-2xl ring-1 ring-white/10 text-sm font-medium animate-in fade-in slide-in-from-bottom-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          {toast}
          <button onClick={() => setToast(null)} className="ml-1 text-slate-400 hover:text-slate-200">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </>
  );
}
