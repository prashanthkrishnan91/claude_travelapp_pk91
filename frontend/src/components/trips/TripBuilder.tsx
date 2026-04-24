"use client";

import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import {
  DndContext,
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
  Layers,
  Navigation,
} from "lucide-react";
import { estimateTravel, sumRoute } from "@/lib/travelTime";
import { addDaysToIsoDate, normalizeIsoDate } from "@/lib/tripDays";
import gsap from "gsap";
import type {
  ItineraryDay,
  ItineraryItem,
  ResearchResult,
  ItemType,
  CompareResult,
  AttractionSearchResult,
  BestAreaRecommendation,
  RestaurantSearchResult,
  LocationCluster,
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
  addRoundTripOutboundToDay,
  addRoundTripReturnToDay,
  searchAttractions,
  searchRestaurants,
  searchClusters,
  fetchBestArea,
  fetchDayPlan,
  planClusterDay,
  addAttractionToDay,
  addRestaurantToDay,
} from "@/lib/api";
import { SearchResultCard } from "./SearchResultCard";
import { ItineraryDayColumn } from "./ItineraryDayColumn";
import { ItineraryItemCard } from "./ItineraryItemCard";
import { CompareModal } from "./CompareModal";
import { DayPlanModal } from "./DayPlanModal";
import { TripMapView } from "./TripMapView";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function aiScoreOf(item: ItineraryItem): number {
  return ((item.details as Record<string, unknown>)?.aiScore as number) ?? 0;
}

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

function AiScoreBadge({ score }: { score: number }) {
  const { bg, text, ring } =
    score >= 70 ? { bg: "bg-emerald-50", text: "text-emerald-700", ring: "ring-emerald-300" } :
    score >= 50 ? { bg: "bg-amber-50",   text: "text-amber-700",   ring: "ring-amber-300"   } :
                  { bg: "bg-slate-50",   text: "text-slate-500",   ring: "ring-slate-200"   };
  return (
    <div className={`flex flex-col items-center justify-center w-10 h-10 rounded-full ring-2 ${ring} ${bg} flex-shrink-0`}>
      <p className={`text-xs font-bold leading-none ${text}`}>{Math.round(score)}</p>
      <p className="text-[9px] text-slate-400 leading-none mt-0.5">score</p>
    </div>
  );
}

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
              ? "bg-sky-600 text-white shadow-sm"
              : "bg-slate-100 text-slate-500 hover:bg-slate-200"
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
    <div className="glass border border-white/60 rounded-2xl p-3 flex gap-3 shadow-sm">
      {topFlight && (
        <div className="flex-1 min-w-0">
          <p className="text-[10px] text-slate-400 uppercase tracking-wide font-semibold mb-1 flex items-center gap-1">
            <Plane className="w-3 h-3 text-sky-500" /> {isRoundTrip ? "Best Round-Trip" : "Best Flight"}
          </p>
          <p className="text-xs font-bold text-slate-800 truncate">
            {topAirline ?? topFlight.title}
          </p>
          <p className="text-xs text-slate-500">
            {topOrigin ?? ""}
            {topDest ? ` → ${topDest}` : ""}
            {topPrice ? ` · $${Math.round(topPrice)}` : ""}
          </p>
        </div>
      )}
      {topFlight && topHotel && <div className="w-px bg-slate-200 self-stretch" />}
      {topHotel && (
        <div className="flex-1 min-w-0">
          <p className="text-[10px] text-slate-400 uppercase tracking-wide font-semibold mb-1 flex items-center gap-1">
            <Hotel className="w-3 h-3 text-violet-500" /> Best Hotel
          </p>
          <p className="text-xs font-bold text-slate-800 truncate">
            {(hd.name as string) ?? topHotel.title}
          </p>
          <p className="text-xs text-slate-500">
            {hd.pricePerNight ? `$${Math.round(hd.pricePerNight as number)}/night` : ""}
            {hd.rating ? ` · ★ ${(hd.rating as number).toFixed(1)}` : ""}
          </p>
        </div>
      )}
    </div>
  );
}

// ─── Best Area card ───────────────────────────────────────────────────────────

function BestAreaCard({ bestArea }: { bestArea: BestAreaRecommendation }) {
  return (
    <div className="rounded-2xl border border-violet-200 bg-gradient-to-br from-violet-50 to-purple-50 p-3 shadow-sm flex flex-col gap-1.5">
      <div className="flex items-center gap-1.5">
        <span className="text-base leading-none">📍</span>
        <span className="text-[10px] font-bold text-violet-500 uppercase tracking-wider">Best Area to Stay</span>
        <span className="ml-auto text-[10px] font-bold text-violet-400 bg-violet-100 px-1.5 py-0.5 rounded-full">
          {bestArea.score.toFixed(0)}/100
        </span>
      </div>
      <p className="text-sm font-extrabold text-violet-900 leading-tight">{bestArea.areaName}</p>
      <p className="text-xs text-violet-600 leading-snug">{bestArea.reason}</p>
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
  const explanation = (d.explanation      as string)   ?? "";
  const bookingUrl  = (d.bookingUrl       as string)   ?? "";

  const containerClass = isTopPick
    ? "border-emerald-300/70 bg-gradient-to-br from-emerald-50/60 to-white"
    : isLowScore
    ? "border-slate-200/60 opacity-55"
    : "border-slate-200/80 bg-white";

  return (
    <div className={`candidate-card relative border rounded-2xl p-4 flex flex-col gap-3 transition-all duration-200 hover:shadow-md hover:border-slate-300 shadow-sm ${containerClass}`}>
      {isTopPick && (
        <div className="absolute -top-2.5 left-3">
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500 text-white shadow-sm">
            <Zap className="w-2.5 h-2.5" />
            Best Pick
          </span>
        </div>
      )}

      {/* Header: airline + flight number + AI score */}
      <div className="flex items-start justify-between gap-2 pt-0.5">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-slate-900 leading-tight">{airline || flightNum}</p>
          {airline && <p className="text-xs text-slate-400 mt-0.5">{flightNum}</p>}
        </div>
        <AiScoreBadge score={aiScore} />
      </div>

      {/* Route row */}
      {origin && destination && (
        <div className="flex items-center gap-2">
          <div className="text-center min-w-[40px]">
            <p className="text-sm font-bold text-slate-900">{origin}</p>
            {depTime && <p className="text-[11px] text-slate-400">{formatTime(depTime)}</p>}
          </div>
          <div className="flex-1 flex flex-col items-center gap-0.5 px-1">
            <div className="flex items-center gap-1 w-full">
              <div className="flex-1 h-px bg-slate-200" />
              <Plane className="w-3 h-3 text-sky-500" />
              <div className="flex-1 h-px bg-slate-200" />
            </div>
            <p className="text-[10px] text-slate-400 text-center">
              {duration > 0 ? formatDuration(duration) : ""}
              {duration > 0 && " · "}
              {stops === 0 ? "Nonstop" : `${stops} stop${stops > 1 ? "s" : ""}`}
            </p>
          </div>
          <div className="text-center min-w-[40px]">
            <p className="text-sm font-bold text-slate-900">{destination}</p>
            {arrTime && <p className="text-[11px] text-slate-400">{formatTime(arrTime)}</p>}
          </div>
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
        <p className="text-xs text-slate-500 leading-relaxed">{explanation}</p>
      )}

      {/* Pricing grid */}
      <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-100">
        {price > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-slate-400 uppercase tracking-wide">Cash</p>
            <p className="text-sm font-bold text-slate-900">${Math.round(price)}</p>
          </div>
        )}
        {points > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-slate-400 uppercase tracking-wide">Points</p>
            <p className="text-sm font-bold text-violet-700">
              {points >= 1000 ? `${(points / 1000).toFixed(0)}k` : points}
            </p>
          </div>
        )}
        {cpp > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-slate-400 uppercase tracking-wide">CPP</p>
            <p className={`text-sm font-bold ${cpp >= 2 ? "text-emerald-600" : "text-slate-700"}`}>
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
            className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-2 rounded-xl text-xs font-medium transition-all ${
              isComparing
                ? "bg-violet-600 text-white shadow-sm"
                : "bg-slate-100 hover:bg-violet-50 hover:text-violet-700 text-slate-600"
            }`}
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
            className="flex-1 flex items-center justify-center gap-1.5 px-2 py-2 rounded-xl bg-slate-100 hover:bg-sky-50 hover:text-sky-700 text-slate-600 text-xs font-medium transition-all"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Book
          </a>
        )}
        <button
          onClick={() => onAddToItinerary(item)}
          disabled={adding}
          className="flex-1 flex items-center justify-center gap-1.5 px-2 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold transition-all disabled:opacity-50 shadow-sm"
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
        <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{label}</span>
        <span className="text-xs text-slate-500">{airline} <span className="text-slate-300">{flightNum}</span></span>
      </div>
      <div className="flex items-center gap-2">
        <div className="text-center min-w-[36px]">
          <p className="text-sm font-bold text-slate-900">{origin}</p>
          {depTime && <p className="text-[10px] text-slate-400">{formatTime(depTime)}</p>}
        </div>
        <div className="flex-1 flex flex-col items-center gap-0.5 px-1">
          <div className="flex items-center gap-1 w-full">
            <div className="flex-1 h-px bg-slate-200" />
            <Plane className="w-3 h-3 text-sky-400" />
            <div className="flex-1 h-px bg-slate-200" />
          </div>
          <p className="text-[10px] text-slate-400">
            {duration > 0 ? formatDuration(duration) : ""}
            {duration > 0 && " · "}
            {stops === 0 ? "Nonstop" : `${stops} stop${stops > 1 ? "s" : ""}`}
          </p>
        </div>
        <div className="text-center min-w-[36px]">
          <p className="text-sm font-bold text-slate-900">{dest}</p>
          {arrTime && <p className="text-[10px] text-slate-400">{formatTime(arrTime)}</p>}
        </div>
        {price > 0 && (
          <p className="text-xs font-semibold text-slate-600 ml-1">${Math.round(price)}</p>
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

  const containerClass = isTopPick
    ? "border-emerald-300/70 bg-gradient-to-br from-emerald-50/60 to-white"
    : isLowScore
    ? "border-slate-200/60 opacity-55"
    : "border-slate-200/80 bg-white";

  return (
    <div className={`candidate-card relative border rounded-2xl p-4 flex flex-col gap-3 transition-all duration-200 hover:shadow-md hover:border-slate-300 shadow-sm ${containerClass}`}>
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
          <p className="text-sm font-bold text-slate-900 leading-tight">Round-Trip</p>
          <p className="text-xs text-slate-400 mt-0.5">Outbound + Return pair</p>
        </div>
        <AiScoreBadge score={aiScore} />
      </div>

      {/* Outbound leg */}
      <div className="rounded-xl bg-sky-50/60 px-3 py-2.5">
        <FlightLegRow leg={outbound} label="Outbound" />
      </div>

      {/* Return leg */}
      <div className="rounded-xl bg-violet-50/60 px-3 py-2.5">
        <FlightLegRow leg={returnFlight} label="Return" />
      </div>

      {/* Combined pricing */}
      <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-100">
        {totalPrice > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-slate-400 uppercase tracking-wide">Total Cash</p>
            <p className="text-sm font-bold text-slate-900">${Math.round(totalPrice)}</p>
          </div>
        )}
        {totalPoints > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-slate-400 uppercase tracking-wide">Total Pts</p>
            <p className="text-sm font-bold text-violet-700">
              {totalPoints >= 1000 ? `${(totalPoints / 1000).toFixed(0)}k` : totalPoints}
            </p>
          </div>
        )}
        {combinedCpp > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-slate-400 uppercase tracking-wide">CPP</p>
            <p className={`text-sm font-bold ${combinedCpp >= 2 ? "text-emerald-600" : "text-slate-700"}`}>
              {combinedCpp.toFixed(2)}¢
            </p>
          </div>
        )}
      </div>

      {/* Add button */}
      <button
        onClick={() => onAddToItinerary(item)}
        disabled={adding}
        className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold transition-all disabled:opacity-50 shadow-sm w-full"
      >
        {adding ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
        Add Both Flights to Itinerary
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

  const containerClass = isTopPick
    ? "border-violet-300/70 bg-gradient-to-br from-violet-50/60 to-white"
    : isLowScore
    ? "border-slate-200/60 opacity-55"
    : "border-slate-200/80 bg-white";

  return (
    <div className={`candidate-card relative border rounded-2xl p-4 flex flex-col gap-3 transition-all duration-200 hover:shadow-md hover:border-slate-300 shadow-sm ${containerClass}`}>
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
          <p className="text-sm font-bold text-slate-900 leading-tight">{name}</p>
          <div className="flex items-center gap-2 mt-0.5">
            {stars != null && (
              <span className="text-xs text-amber-400">{"★".repeat(Math.min(5, Math.round(stars)))}</span>
            )}
            {location && (
              <span className="flex items-center gap-0.5 text-xs text-slate-400 truncate">
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
        <p className="text-xs text-slate-500 leading-relaxed">{explanation}</p>
      )}

      {/* Pricing grid */}
      <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-100">
        {pricePerNight > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-slate-400 uppercase tracking-wide">Per Night</p>
            <p className="text-sm font-bold text-slate-900">${Math.round(pricePerNight)}</p>
          </div>
        )}
        {nights > 1 && pricePerNight > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-slate-400 uppercase tracking-wide">Total</p>
            <p className="text-sm font-bold text-slate-700">${Math.round(pricePerNight * nights)}</p>
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
            <span key={a} className="px-2 py-0.5 bg-slate-100 rounded-full text-xs text-slate-500">{a}</span>
          ))}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-1.5 pt-1">
        {onToggleCompare && (
          <button
            onClick={() => onToggleCompare(item)}
            title="Compare"
            className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-2 rounded-xl text-xs font-medium transition-all ${
              isComparing
                ? "bg-violet-600 text-white shadow-sm"
                : "bg-slate-100 hover:bg-violet-50 hover:text-violet-700 text-slate-600"
            }`}
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
            className="flex-1 flex items-center justify-center gap-1.5 px-2 py-2 rounded-xl bg-slate-100 hover:bg-violet-50 hover:text-violet-700 text-slate-600 text-xs font-medium transition-all"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Book
          </a>
        )}
        <button
          onClick={() => onAddToItinerary(item)}
          disabled={adding}
          className="flex-1 flex items-center justify-center gap-1.5 px-2 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold transition-all disabled:opacity-50 shadow-sm"
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

  const containerClass = isTopPick
    ? "border-emerald-300/70 bg-gradient-to-br from-emerald-50/60 to-white"
    : "border-slate-200/80 bg-white";

  return (
    <div className={`candidate-card relative border rounded-2xl p-4 flex flex-col gap-3 transition-all duration-200 hover:shadow-md hover:border-slate-300 shadow-sm ${containerClass}`}>
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
          <p className="text-sm font-bold text-slate-900 leading-tight">{attraction.name}</p>
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            {rating != null && (
              <span className="text-xs text-amber-500 font-semibold">★ {rating.toFixed(1)}</span>
            )}
            {numReviews != null && (
              <span className="text-xs text-slate-400">
                {numReviews >= 1000 ? `${(numReviews / 1000).toFixed(0)}k` : numReviews} reviews
              </span>
            )}
          </div>
        </div>
        <AiScoreBadge score={aiScore} />
      </div>

      {/* Description */}
      {attraction.description && (
        <p className="text-xs text-slate-500 leading-relaxed line-clamp-2">{attraction.description}</p>
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
          <div className="flex items-center gap-1 text-xs text-slate-400">
            <MapPin className="w-3 h-3 flex-shrink-0" />
            <span className="truncate">{attraction.address}</span>
          </div>
        )}
        <div className="flex items-center gap-3 flex-wrap">
          {attraction.openingHours && (
            <div className="flex items-center gap-1 text-xs text-slate-400">
              <Clock className="w-3 h-3 flex-shrink-0" />
              <span>{attraction.openingHours}</span>
            </div>
          )}
          {attraction.durationMinutes != null && (
            <span className="text-xs text-slate-400">
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
          className="flex-1 flex items-center justify-center gap-1.5 px-2 py-2 rounded-xl bg-slate-100 hover:bg-emerald-50 hover:text-emerald-700 text-slate-600 text-xs font-medium transition-all"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          View
        </a>
        <button
          onClick={() => onAddToTrip(attraction)}
          disabled={adding}
          className="flex-1 flex items-center justify-center gap-1.5 px-2 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-all disabled:opacity-50 shadow-sm"
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
  const mapsUrl    = `https://www.google.com/maps/search/${encodeURIComponent(restaurant.name + " " + restaurant.location)}`;

  const containerClass = isTopPick
    ? "candidate-card relative flex flex-col gap-2 p-3 rounded-2xl border border-rose-200 bg-rose-50/40 shadow-sm"
    : "candidate-card relative flex flex-col gap-2 p-3 rounded-2xl border border-slate-100 bg-white shadow-sm";

  const scoreColor =
    aiScore >= 70 ? "bg-rose-500 text-white" :
    aiScore >= 50 ? "bg-amber-400 text-white" :
                    "bg-slate-200 text-slate-600";

  return (
    <div className={containerClass}>
      {isTopPick && (
        <span className="absolute top-2 right-2 text-[9px] font-bold uppercase tracking-wide text-rose-500 bg-rose-100 px-1.5 py-0.5 rounded-full">
          Top Pick
        </span>
      )}

      <div className="flex items-start justify-between gap-2 pt-0.5">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-slate-900 leading-tight">{restaurant.name}</p>
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            <span className="text-[10px] text-slate-400 font-medium">{restaurant.cuisine}</span>
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
        <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-xs font-bold ${scoreColor}`}>
          {Math.round(aiScore)}
        </div>
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
          <div className="flex items-center gap-1 text-xs text-slate-400">
            <MapPin className="w-3 h-3 flex-shrink-0" />
            <span className="truncate">{restaurant.address}</span>
          </div>
        )}
        <div className="flex items-center gap-3 flex-wrap">
          {restaurant.openingHours && (
            <div className="flex items-center gap-1 text-xs text-slate-400">
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
          className="flex-1 flex items-center justify-center gap-1.5 px-2 py-2 rounded-xl bg-slate-100 hover:bg-rose-50 hover:text-rose-700 text-slate-600 text-xs font-medium transition-all"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          Maps
        </a>
        <button
          onClick={() => onAddToTrip(restaurant)}
          disabled={adding}
          className="flex-1 flex items-center justify-center gap-1.5 px-2 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold transition-all disabled:opacity-50 shadow-sm"
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
      <span className="text-[9px] font-semibold uppercase tracking-wider text-slate-400">{label}</span>
      <div className="flex flex-wrap gap-1">
        {options.map((opt) => (
          <button
            key={String(opt.value ?? "all")}
            onClick={() => onChange(opt.value === value ? null : opt.value)}
            className={`px-2 py-0.5 rounded-full text-[10px] font-medium transition-all border ${
              opt.value === value
                ? "bg-slate-700 text-white border-slate-700"
                : "bg-transparent text-slate-500 border-slate-200 hover:border-slate-400 hover:text-slate-700"
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
  children: React.ReactNode;
}) {
  const hasData = (totalCount ?? count) > 0;
  return (
    <div className="card p-3 flex flex-col gap-2">
      <button
        onClick={onToggle}
        className="flex items-center justify-between w-full text-sm font-semibold text-slate-700"
      >
        <span className="flex items-center gap-1.5">
          {icon}
          {title}
          <span className={`text-xs font-normal ${accentColor}`}>
            ({totalCount !== undefined && totalCount !== count ? `${count}/${totalCount}` : count})
          </span>
        </span>
        {open
          ? <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
          : <ChevronDown className="w-3.5 h-3.5 text-slate-400" />}
      </button>
      {open && sortControls && <div className="pt-0.5">{sortControls}</div>}
      {open && !hasData && (
        <p className="text-xs text-slate-400 py-2 text-center">
          No candidates yet — create a new trip to auto-populate.
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
}

// ─── Main component ───────────────────────────────────────────────────────────

export function TripBuilder({ tripId, destination, startDate, endDate, initialDays, initialResults }: TripBuilderProps) {
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
  const [attractionsLoading,   setAttractionsLoading]   = useState(false);
  const [restaurantsLoading,   setRestaurantsLoading]   = useState(false);
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
  const [viewMode,             setViewMode]             = useState<"list" | "map" | "grouped">("list");
  const [activeMarkerId,       setActiveMarkerId]       = useState<string | null>(null);
  const [candidateClusters,    setCandidateClusters]    = useState<LocationCluster[]>([]);
  const [clustersLoading,      setClustersLoading]      = useState(false);
  const [planningClusterId,    setPlanningClusterId]    = useState<string | null>(null);
  const [bestArea,             setBestArea]             = useState<BestAreaRecommendation | null>(null);

  // ── Day plan state ───────────────────────────────────────────────────────────
  const [dayPlan,            setDayPlan]            = useState<DayPlan | null>(null);
  const [dayPlanLoading,     setDayPlanLoading]     = useState(false);
  const [dayPlanTargetDayId, setDayPlanTargetDayId] = useState<string | null>(null);

  const flightListRef      = useRef<HTMLDivElement>(null);
  const hotelListRef       = useRef<HTMLDivElement>(null);
  const attractionListRef  = useRef<HTMLDivElement>(null);
  const restaurantListRef  = useRef<HTMLDivElement>(null);
  const prevViewModeRef    = useRef<"list" | "map" | "grouped">("list");

  // ── Compare state ────────────────────────────────────────────────────────────
  const [compareSet,     setCompareSet]     = useState<Set<string>>(new Set());
  const [compareOpen,    setCompareOpen]    = useState(false);
  const [compareResults, setCompareResults] = useState<CompareResult[]>([]);
  const [compareLoading, setCompareLoading] = useState(false);
  const compareDataRef = useRef<Map<string, { name: string; itemType: string; cashPrice: number; pointsCost: number; rating?: number; lat?: number; lng?: number }>>(new Map());

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  useEffect(() => {
    setDays([...initialDays].sort((a, b) => a.dayNumber - b.dayNumber));
  }, [initialDays]);

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

  // Load trip-level items on mount, sort by AI score
  useEffect(() => {
    fetchTripItems(tripId).then((items) => {
      const flights = items
        .filter((i) => i.itemType === "flight")
        .sort((a, b) => aiScoreOf(b) - aiScoreOf(a));
      const hotels = items
        .filter((i) => i.itemType === "hotel")
        .sort((a, b) => aiScoreOf(b) - aiScoreOf(a));
      setCandidateFlights(flights);
      setCandidateHotels(hotels);
    });
  }, [tripId]);

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

  // Auto-load attractions for the trip destination
  useEffect(() => {
    if (!destination) return;
    setAttractionsLoading(true);
    searchAttractions(destination).then((attractions) => {
      setCandidateAttractions(attractions);
    }).finally(() => setAttractionsLoading(false));
  }, [destination]);

  // GSAP entrance animations for attraction cards
  useEffect(() => {
    if (!attractionListRef.current || candidateAttractions.length === 0) return;
    const cards = attractionListRef.current.querySelectorAll(".candidate-card");
    gsap.from(cards, { y: 24, opacity: 0, duration: 0.45, stagger: 0.05, ease: "power2.out", clearProps: "all" });
  }, [candidateAttractions.length]);

  // Auto-load restaurants for the trip destination
  useEffect(() => {
    if (!destination) return;
    setRestaurantsLoading(true);
    searchRestaurants(destination).then((restaurants) => {
      setCandidateRestaurants(restaurants);
    }).finally(() => setRestaurantsLoading(false));
  }, [destination]);

  // GSAP entrance animations for restaurant cards
  useEffect(() => {
    if (!restaurantListRef.current || candidateRestaurants.length === 0) return;
    const cards = restaurantListRef.current.querySelectorAll(".candidate-card");
    gsap.from(cards, { y: 24, opacity: 0, duration: 0.45, stagger: 0.05, ease: "power2.out", clearProps: "all" });
  }, [candidateRestaurants.length]);

  // Load clusters when grouped view is activated
  useEffect(() => {
    if (viewMode !== "grouped" || !destination || candidateClusters.length > 0) return;
    setClustersLoading(true);
    searchClusters(destination).then(setCandidateClusters).finally(() => setClustersLoading(false));
  }, [viewMode, destination, candidateClusters.length]);

  // Fetch best area recommendation once destination is known
  useEffect(() => {
    if (!destination) return;
    fetchBestArea(destination).then(setBestArea);
  }, [destination]);

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
    const selectedDay = days.find((day) => day.id === selectedDayId);
    if (selectedDay) {
      setExpandedDayNumber(selectedDay.dayNumber);
      return;
    }
    setExpandedDayNumber((prev) => prev ?? days[0]?.dayNumber ?? null);
  }, [days, selectedDayId]);

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

      const newItem = await createItem(tripId, targetDay.id, {
        itemType: item.itemType as ItemType,
        title: item.title,
        description: item.description ?? undefined,
        location: item.location ?? undefined,
        position: targetDay.items.length,
      });

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

  // ── Plan an entire cluster area into a single day ───────────────────────────

  const handlePlanCluster = useCallback(async (cluster: LocationCluster) => {
    setPlanningClusterId(cluster.clusterId);
    try {
      const targetDay = days.find((d) => d.id === selectedDayId) ?? days[0];
      if (!targetDay) {
        showToast("No day available — days are generated from trip dates");
        return;
      }

      const plan = await planClusterDay(tripId, cluster.clusterId, cluster.places);

      const newItems: ItineraryItem[] = [];
      for (const attraction of plan.attractions) {
        const item = await addAttractionToDay(tripId, targetDay.id, attraction);
        newItems.push(item);
      }
      if (plan.lunch) {
        const item = await addRestaurantToDay(tripId, targetDay.id, plan.lunch);
        newItems.push(item);
      }
      if (plan.dinner) {
        const item = await addRestaurantToDay(tripId, targetDay.id, plan.dinner);
        newItems.push(item);
      }

      setDays((prev) =>
        prev.map((d) =>
          d.id === targetDay.id ? { ...d, items: [...d.items, ...newItems] } : d
        )
      );
      const total = newItems.length;
      showToast(`${total} place${total !== 1 ? "s" : ""} from ${cluster.areaName || "Popular Area"} added to Day ${targetDay.dayNumber}`);
    } catch {
      showToast("Failed to plan area — please try again");
    } finally {
      setPlanningClusterId(null);
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

  const handleDragOver = useCallback((event: DragOverEvent) => {
    const { active, over } = event;
    if (!over) return;
    const activeData = active.data.current;
    const overData   = over.data.current;
    if (!activeData || activeData.type !== "itinerary-item") return;

    const sourceItem: ItineraryItem = activeData.item;
    const sourceDayId = sourceItem.dayId;
    let targetDayId: string | null = null;
    if (overData?.type === "itinerary-item") targetDayId = overData.item.dayId;
    else if (overData?.type === "day") targetDayId = overData.dayId;
    else { const s = String(over.id); if (s.startsWith("day-")) targetDayId = s.replace("day-", ""); }
    if (!targetDayId) return;

    if (targetDayId === sourceDayId) {
      // Same-day: reorder via arrayMove for smooth visual feedback
      if (overData?.type !== "itinerary-item") return;
      const overId = String(over.id);
      setDays((prev) => prev.map((d) => {
        if (d.id !== sourceDayId) return d;
        const oldIdx = d.items.findIndex((i) => i.id === sourceItem.id);
        const newIdx = d.items.findIndex((i) => i.id === overId);
        if (oldIdx === -1 || newIdx === -1 || oldIdx === newIdx) return d;
        return { ...d, items: arrayMove(d.items, oldIdx, newIdx).map((i, idx) => ({ ...i, position: idx })) };
      }));
      return;
    }

    setDays((prev) => {
      const sourceDay = prev.find((d) => d.id === sourceDayId);
      const targetDay = prev.find((d) => d.id === targetDayId);
      if (!sourceDay || !targetDay) return prev;
      return prev.map((d) => {
        if (d.id === sourceDayId) return { ...d, items: d.items.filter((i) => i.id !== sourceItem.id).map((i, idx) => ({ ...i, position: idx })) };
        if (d.id === targetDayId) return { ...d, items: [...d.items, { ...sourceItem, dayId: targetDayId! }].map((i, idx) => ({ ...i, position: idx })) };
        return d;
      });
    });
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
      if (!overData) return;
      const overId = String(over.id);
      const targetDayId =
        overData.type === "itinerary-item" ? overData.item.dayId :
        overData.type === "day" ? overData.dayId :
        overId.startsWith("day-") ? overId.replace("day-", "") : null;
      if (!targetDayId) return;
      if (targetDayId === sourceItem.dayId) {
        // State already updated in handleDragOver — persist current positions to backend
        const day = days.find((d) => d.id === targetDayId);
        if (day) {
          day.items.forEach((item) => updateItem(item.id, { position: item.position }).catch(() => {}));
        }
      } else {
        // Cross-day move — persist new day_id and position to backend
        const targetDay = days.find((d) => d.id === targetDayId);
        const movedPosition = targetDay?.items.find((i) => i.id === sourceItem.id)?.position
          ?? (targetDay?.items.length ?? 1) - 1;
        updateItem(sourceItem.id, { dayId: targetDayId, position: movedPosition }).catch(() => {});
        // Persist updated positions for source day items
        const sourceDay = days.find((d) => d.id === sourceItem.dayId);
        if (sourceDay) {
          sourceDay.items.forEach((item) => updateItem(item.id, { position: item.position }).catch(() => {}));
        }
      }
    }
  }, [days, tripId]);

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
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
      >
        <div className="flex items-start gap-4 min-h-[500px]">

          {/* ── Left Panel: AI-ranked candidates ──────────────────────────── */}
          <div className="w-80 flex-shrink-0 flex flex-col gap-3 overflow-y-auto pr-0.5">

            {/* Summary bar */}
            <SummaryBar topFlight={topFlight} topHotel={topHotel} />

            {/* Best area recommendation */}
            {bestArea && <BestAreaCard bestArea={bestArea} />}

            {/* Flights section */}
            <CandidatePanel
              title="Flights"
              icon={<Plane className="w-3.5 h-3.5 text-sky-500" />}
              count={sortedFlights.length}
              accentColor="text-sky-500"
              open={flightPanelOpen}
              onToggle={() => setFlightPanelOpen((v) => !v)}
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
                const top20 = Math.max(1, Math.ceil(sortedFlights.length * 0.2));
                const bot20 = sortedFlights.length > 2
                  ? Math.max(1, Math.ceil(sortedFlights.length * 0.2))
                  : 0;
                return sortedFlights.map((item, idx) => {
                  const d = (item.details ?? {}) as Record<string, unknown>;
                  // toCamel converts is_round_trip → isRoundTrip; check both for compat
                  if (d.isRoundTrip ?? d.is_round_trip) {
                    return (
                      <RoundTripFlightCard
                        key={item.id}
                        item={item}
                        onAddToItinerary={handleAddRoundTripToItinerary}
                        adding={addingId === item.id}
                        isTopPick={flightSort === "ai" && idx < top20}
                        isLowScore={flightSort === "ai" && bot20 > 0 && idx >= sortedFlights.length - bot20}
                      />
                    );
                  }
                  return (
                    <FlightCandidateCard
                      key={item.id}
                      item={item}
                      onAddToItinerary={handleAddCandidateToItinerary}
                      onToggleCompare={handleToggleCompareItem}
                      adding={addingId === item.id}
                      isTopPick={flightSort === "ai" && idx < top20}
                      isLowScore={flightSort === "ai" && bot20 > 0 && idx >= sortedFlights.length - bot20}
                      isComparing={compareSet.has(item.id)}
                    />
                  );
                });
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
                <button
                  onClick={() => setViewMode("grouped")}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                    viewMode === "grouped"
                      ? "bg-white text-slate-700 shadow-sm"
                      : "text-slate-500 hover:text-slate-700"
                  }`}
                >
                  <Layers className="w-3 h-3" />
                  Areas
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
                  bestArea={bestArea}
                  onMarkerClick={(id) => setActiveMarkerId(id)}
                  onAddAttraction={handleAddAttractionToItinerary}
                  onAddRestaurant={handleAddRestaurantToItinerary}
                />
              </div>
            ) : viewMode === "grouped" ? (
              /* ── Grouped / Areas view ──────────────────────────────────── */
              <div className="flex flex-col gap-4">
                {clustersLoading ? (
                  <div className="flex items-center justify-center py-8 gap-2 text-slate-400 text-xs">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Grouping nearby places…
                  </div>
                ) : candidateClusters.length === 0 ? (
                  <div className="text-center py-8 text-slate-400 text-xs">No clusters found.</div>
                ) : (
                  candidateClusters.map((cluster) => (
                    <div key={cluster.clusterId} className="card p-3 flex flex-col gap-2">
                      {/* Cluster header */}
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <MapPin className="w-3.5 h-3.5 text-sky-500 flex-shrink-0" />
                          <span className="text-sm font-bold text-slate-800">{cluster.areaName || "Popular Area"}</span>
                        </div>
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                            cluster.label === "Walkable cluster"
                              ? "bg-emerald-100 text-emerald-700"
                              : cluster.label === "5 min apart"
                              ? "bg-sky-100 text-sky-700"
                              : "bg-amber-100 text-amber-700"
                          }`}
                        >
                          <MapPin className="w-2.5 h-2.5" />
                          {cluster.label}
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-[10px] text-slate-400">
                          {cluster.places.length} place{cluster.places.length !== 1 ? "s" : ""} ·{" "}
                          {cluster.counts.attractions} attraction
                          {cluster.counts.attractions !== 1 ? "s" : ""} ·{" "}
                          {cluster.counts.restaurants} restaurant
                          {cluster.counts.restaurants !== 1 ? "s" : ""}
                        </p>
                        <button
                          onClick={() => handlePlanCluster(cluster)}
                          disabled={planningClusterId === cluster.clusterId}
                          className="flex-shrink-0 flex items-center gap-1 px-2.5 py-1 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-[10px] font-semibold transition-all disabled:opacity-50"
                        >
                          {planningClusterId === cluster.clusterId ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <Zap className="w-3 h-3" />
                          )}
                          Plan this area
                        </button>
                      </div>
                      {/* Places list */}
                      <div className="flex flex-col gap-1.5 mt-1">
                        {cluster.places.map((place) => (
                          <div
                            key={place.id}
                            className="flex items-center gap-2 rounded-xl border border-slate-100 bg-slate-50 px-3 py-2"
                          >
                            <span
                              className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                                place.placeType === "attraction" ? "bg-emerald-400" : "bg-rose-400"
                              }`}
                            />
                            <div className="flex-1 min-w-0">
                              <p className="text-xs font-semibold text-slate-800 truncate">{place.name}</p>
                              <p className="text-[10px] text-slate-400 truncate">{place.category} · {place.address.split(",")[0]}</p>
                            </div>
                            {place.rating != null && (
                              <span className="flex items-center gap-0.5 text-[10px] text-amber-500 font-semibold flex-shrink-0">
                                <Star className="w-2.5 h-2.5 fill-amber-400 stroke-amber-400" />
                                {place.rating.toFixed(1)}
                              </span>
                            )}
                            <button
                              onClick={() => {
                                if (place.placeType === "attraction") {
                                  const match = sortedAttractions.find((a) => a.id === place.id);
                                  if (match) handleAddAttractionToItinerary(match);
                                } else {
                                  const match = sortedRestaurants.find((r) => r.id === place.id);
                                  if (match) handleAddRestaurantToItinerary(match);
                                }
                              }}
                              disabled={addingId === place.id}
                              className="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-lg bg-sky-600 hover:bg-sky-500 text-white transition-all disabled:opacity-50"
                            >
                              {addingId === place.id
                                ? <Loader2 className="w-3 h-3 animate-spin" />
                                : <Plus className="w-3 h-3" />
                              }
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))
                )}
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
                  {attractionsLoading ? (
                    <div className="flex items-center justify-center py-6 gap-2 text-slate-400 text-xs">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Discovering attractions…
                    </div>
                  ) : filteredAttractions.length === 0 ? (
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
                            isTopPick={attractionSort === "ai" && idx < top20}
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
                  {restaurantsLoading ? (
                    <div className="flex items-center justify-center py-6 gap-2 text-slate-400 text-xs">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Discovering restaurants…
                    </div>
                  ) : filteredRestaurants.length === 0 ? (
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
                            isTopPick={restaurantSort === "ai" && idx < top20}
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
