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
  FileText,
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
  addRoundTripLegToDay,
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
import { FolioPanel, FolioButton } from "@/components/ui/Folio";

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
  const icon =
    tag === "Points Better"   ? <Zap className="w-2.5 h-2.5" /> :
    tag === "Best Value"      ? <Star className="w-2.5 h-2.5" /> :
    tag === "High CPP"        ? <Zap className="w-2.5 h-2.5" /> :
    tag === "Top Rated"       ? <Star className="w-2.5 h-2.5" /> :
    null;
  return (
    <span
      className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-xs font-semibold text-ds-accent border border-ds-hairline"
      style={{ backgroundColor: "var(--ds-accent-subtle)" }}
    >
      {icon}{tag}
    </span>
  );
}

// ─── AI score badge ───────────────────────────────────────────────────────────

function AiScoreBadge({ score }: { score?: number | null }) {
  if (typeof score !== "number" || !Number.isFinite(score) || score <= 0) return null;
  const { text, ring } =
    score >= 70 ? { text: "text-ds-trust-verified", ring: "ring-ds-trust-verified/45" } :
    score >= 50 ? { text: "text-ds-caution",        ring: "ring-ds-caution/45" } :
                  { text: "text-ds-folio-ink-mist",  ring: "ring-ds-hairline" };
  return (
    <div
      className={`flex flex-col items-center justify-center w-10 h-10 rounded-full ring-2 ${ring} flex-shrink-0`}
    >
      <p className={`text-xs font-bold leading-none ${text}`}>{Math.round(score ?? 0)}</p>
      <p className="text-[9px] text-ds-folio-ink-mist leading-none mt-0.5">score</p>
    </div>
  );
}

const PREMIUM_CARD_BASE = "candidate-card relative border border-ds-hairline rounded-2xl p-4 flex flex-col gap-3 transition-all duration-200 bg-ds-bone hover:shadow-[var(--ds-paper-elevation-1)] hover:border-ds-accent/30";
const SECONDARY_CTA = "flex-1 min-h-[44px] flex items-center justify-center gap-1.5 px-2 py-2 rounded-xl border border-ds-hairline bg-ds-linen text-ds-folio-ink-mist hover:bg-ds-bone hover:border-ds-accent/40 hover:text-ds-folio-ink text-xs font-medium transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2";
const PRIMARY_CTA = "flex-1 min-h-[44px] flex items-center justify-center gap-1.5 px-2 py-2 rounded-xl bg-ds-accent hover:bg-ds-accent-muted text-ds-text-inverse text-xs font-semibold transition-all disabled:opacity-50 shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2";

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
      <span className="text-[10px] text-ds-folio-ink-mist font-semibold uppercase tracking-wide">Sort:</span>
      {keys.map(({ key, label }) => (
        <button
          type="button"
          key={key}
          onClick={() => onChange(key)}
          className="group min-h-[44px] flex items-center justify-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
        >
          <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold transition-all border ${
            current === key
              ? "bg-ds-accent text-ds-text-inverse border-ds-accent shadow-sm"
              : "bg-ds-linen text-ds-folio-ink-soft border-ds-hairline group-hover:bg-ds-bone group-hover:text-ds-folio-ink"
          }`}>
            {label}
          </span>
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
    <div className="bg-ds-bone border border-ds-hairline rounded-2xl p-3 flex gap-3">
      {topFlight && (
        <div className="flex-1 min-w-0">
          <p className="text-[10px] text-ds-folio-ink-mist uppercase tracking-wide font-semibold mb-1 flex items-center gap-1">
            <Plane className="w-3 h-3 text-ds-accent" /> {isRoundTrip ? "Best Round-Trip" : "Best Flight"}
          </p>
          <p className="text-xs font-bold text-ds-folio-ink truncate">
            {topAirline ?? topFlight.title}
          </p>
          <p className="text-xs text-ds-folio-ink-mist">
            {topOrigin ?? ""}
            {topDest ? ` → ${topDest}` : ""}
            {topPrice ? ` · $${Math.round(topPrice)}` : ""}
          </p>
        </div>
      )}
      {topFlight && topHotel && <div className="w-px bg-ds-hairline self-stretch" />}
      {topHotel && (
        <div className="flex-1 min-w-0">
          <p className="text-[10px] text-ds-folio-ink-mist uppercase tracking-wide font-semibold mb-1 flex items-center gap-1">
            <Hotel className="w-3 h-3 text-ds-accent" /> Best Hotel
          </p>
          <p className="text-xs font-bold text-ds-folio-ink truncate">
            {(hd.name as string) ?? topHotel.title}
          </p>
          <p className="text-xs text-ds-folio-ink-mist">
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
  // Canonical field is cash_price → cashPrice (after toCamel); legacy rows used price
  const price       = (d.cashPrice as number) ?? (d.cash_price as number) ?? (d.price as number) ?? item.cashPrice ?? 0;
  const points      = (d.pointsCost       as number)   ?? item.pointsPrice ?? 0;
  const cpp         = (d.cpp              as number)   ?? 0;
  const aiScore     = (d.aiScore          as number)   ?? 0;
  const tags        = (d.tags             as string[]) ?? [];
  // Canonical booking link: google_flights_search_url + booking_link (after toCamel)
  const bookingLinkObj  = (d.bookingLink as Record<string, unknown>) ?? (d.booking_link as Record<string, unknown>) ?? {};
  const googleFlightsUrl = (d.googleFlightsSearchUrl as string) || (d.google_flights_search_url as string) || (bookingLinkObj.url as string) || "";
  const blLinkType       = (bookingLinkObj.linkType as string) || (bookingLinkObj.link_type as string) || (bookingLinkObj.kind as string) || "";
  const isSearchRedirect = blLinkType === "search_redirect" || blLinkType === "search_redirect_only";
  // Legacy rows: bookingUrl present and not a SEARCH_REDIRECT canonical row
  const legacyBookingUrl = !isSearchRedirect ? ((d.bookingUrl as string) ?? "") : "";

  const containerClass = `${PREMIUM_CARD_BASE} ${isTopPick ? "border-ds-accent/45" : ""} ${isLowScore ? "opacity-55" : ""}`;

  return (
    <div className={containerClass}>
      {isTopPick && (
        <div className="absolute -top-2.5 left-3">
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-ds-accent text-ds-text-inverse shadow-sm">
            <Zap className="w-2.5 h-2.5" />
            Best Pick
          </span>
        </div>
      )}

      {/* Header: airline + flight number + one-way badge + AI score */}
      <div className="flex items-start justify-between gap-2 pt-0.5">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 flex-wrap">
            <p className="text-sm font-bold text-ds-folio-ink leading-tight">{airline || flightNum}</p>
            <span className="px-1.5 py-0.5 rounded-full text-[9px] font-semibold text-ds-folio-ink-mist border border-ds-hairline" style={{ backgroundColor: "var(--ds-accent-subtle)" }}>One-way</span>
          </div>
          {airline && <p className="text-xs text-ds-folio-ink-mist mt-0.5">{flightNum}</p>}
        </div>
        <AiScoreBadge score={aiScore} />
      </div>

      {/* Route row */}
      {origin && destination && (
        <div className="flex items-center gap-2">
          <div className="text-center min-w-[40px]">
            <p className="text-sm font-bold text-ds-folio-ink">{origin}</p>
            {depTime && <p className="text-[11px] text-ds-folio-ink-mist">{formatTime(depTime)}</p>}
          </div>
          <div className="flex-1 flex flex-col items-center gap-0.5 px-1">
            <div className="flex items-center gap-1 w-full">
              <div className="flex-1 h-px bg-ds-bone" />
              <Plane className="w-3 h-3 text-ds-accent" />
              <div className="flex-1 h-px bg-ds-bone" />
            </div>
            <p className="text-[10px] text-ds-folio-ink-mist text-center">
              {duration > 0 ? formatDuration(duration) : ""}
              {duration > 0 && " · "}
              {stops === 0 ? "Nonstop" : `${stops} stop${stops > 1 ? "s" : ""}`}
            </p>
          </div>
          <div className="text-center min-w-[40px]">
            <p className="text-sm font-bold text-ds-folio-ink">{destination}</p>
            {arrTime && <p className="text-[11px] text-ds-folio-ink-mist">{formatTime(arrTime)}</p>}
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
      <div className="grid grid-cols-3 gap-2 pt-2 border-t border-ds-hairline">
        {price > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-ds-folio-ink-mist uppercase tracking-wide">Cash</p>
            <p className="text-sm font-bold text-ds-folio-ink">${Math.round(price)}</p>
          </div>
        )}
        {points > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-ds-folio-ink-mist uppercase tracking-wide">Points</p>
            <p className="text-sm font-bold text-ds-accent">
              {points >= 1000 ? `${(points / 1000).toFixed(0)}k` : points}
            </p>
          </div>
        )}
        {cpp > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-ds-folio-ink-mist uppercase tracking-wide">CPP</p>
            <p className={`text-sm font-bold ${cpp >= 2 ? "text-ds-trust-verified" : "text-ds-folio-ink-soft"}`}>
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
            className={`${SECONDARY_CTA} ${isComparing ? "bg-ds-accent/20 border-ds-accent/40 text-ds-accent" : ""}`}
          >
            <Scale className="w-3.5 h-3.5" />
            Compare
          </button>
        )}
        {googleFlightsUrl && isSearchRedirect && (
          <a
            href={googleFlightsUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            title="Search on Google Flights"
            className={SECONDARY_CTA}
            data-testid="google-flights-cta"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Google Flights
          </a>
        )}
        {legacyBookingUrl && (
          <a
            href={legacyBookingUrl}
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
          data-testid="flight-add-btn"
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
  // Canonical outbound/return legs store airline + flight_number only in segments[0], not at leg level
  const segs      = (leg.segments as Array<Record<string, unknown>>) ?? [];
  const firstSeg  = segs[0] as Record<string, unknown> | undefined;
  const airline   = (leg.airline as string) || (firstSeg?.airline as string) || "";
  // Support both camelCase (API response after toCamel) and snake_case (legacy stored data)
  const flightNum = ((leg.flightNumber ?? leg.flight_number) as string) || (firstSeg?.flightNumber as string) || (firstSeg?.flight_number as string) || "";
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
        <span className="text-[10px] font-semibold uppercase tracking-wide text-ds-folio-ink-mist">{label}</span>
        <span className="text-xs text-ds-folio-ink-soft">{airline} <span className="text-ds-folio-ink-mist">{flightNum}</span></span>
      </div>
      <div className="flex items-center gap-2">
        <div className="text-center min-w-[36px]">
          <p className="text-sm font-bold text-ds-folio-ink">{origin}</p>
          {depTime && <p className="text-[10px] text-ds-folio-ink-mist">{formatTime(depTime)}</p>}
        </div>
        <div className="flex-1 flex flex-col items-center gap-0.5 px-1">
          <div className="flex items-center gap-1 w-full">
            <div className="flex-1 h-px bg-ds-bone" />
            <Plane className="w-3 h-3 text-ds-accent" />
            <div className="flex-1 h-px bg-ds-bone" />
          </div>
          <p className="text-[10px] text-ds-folio-ink-mist">
            {duration > 0 ? formatDuration(duration) : ""}
            {duration > 0 && " · "}
            {stops === 0 ? "Nonstop" : `${stops} stop${stops > 1 ? "s" : ""}`}
          </p>
        </div>
        <div className="text-center min-w-[36px]">
          <p className="text-sm font-bold text-ds-folio-ink">{dest}</p>
          {arrTime && <p className="text-[10px] text-ds-folio-ink-mist">{formatTime(arrTime)}</p>}
        </div>
        {price > 0 && (
          <p className="text-xs font-semibold text-ds-folio-ink-soft ml-1">${Math.round(price)}</p>
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
  // Canonical: outbound_leg → outboundLeg after toCamel; legacy rows used outbound
  const outbound    = (d.outboundLeg as Record<string, unknown>) ?? (d.outbound_leg as Record<string, unknown>) ?? (d.outbound as Record<string, unknown>) ?? {};
  // Canonical: return_leg → returnLeg after toCamel; legacy rows used returnFlight / return_flight
  const returnFlight = (d.returnLeg as Record<string, unknown>) ?? (d.return_leg as Record<string, unknown>) ?? ((d.returnFlight ?? d.return_flight) as Record<string, unknown>) ?? {};
  // Canonical price: cash_price → cashPrice; legacy rows used totalPrice / total_price
  const totalPrice  = (d.cashPrice as number) ?? (d.cash_price as number) ?? ((d.totalPrice ?? d.total_price) as number) ?? item.cashPrice ?? 0;
  const totalPoints = ((d.totalPoints ?? d.total_points)  as number) ?? 0;
  const combinedCpp = ((d.combinedCpp ?? d.combined_cpp)  as number) ?? 0;
  const aiScore     = ((d.aiScore     ?? d.ai_score)      as number) ?? 0;
  // Canonical booking link
  const rtBookingLinkObj  = (d.bookingLink as Record<string, unknown>) ?? (d.booking_link as Record<string, unknown>) ?? {};
  const rtGoogleFlightsUrl = (d.googleFlightsSearchUrl as string) || (d.google_flights_search_url as string) || (rtBookingLinkObj.url as string) || "";
  const rtLinkType         = (rtBookingLinkObj.linkType as string) || (rtBookingLinkObj.link_type as string) || (rtBookingLinkObj.kind as string) || "";
  const rtIsSearchRedirect = rtLinkType === "search_redirect" || rtLinkType === "search_redirect_only";

  const containerClass = `${PREMIUM_CARD_BASE} ${isTopPick ? "border-ds-accent/45" : ""} ${isLowScore ? "opacity-55" : ""}`;

  return (
    <div className={containerClass}>
      {isTopPick && (
        <div className="absolute -top-2.5 left-3">
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-ds-accent text-ds-text-inverse shadow-sm">
            <Zap className="w-2.5 h-2.5" />
            Best Pair
          </span>
        </div>
      )}

      {/* Header: round-trip label + AI score */}
      <div className="flex items-start justify-between gap-2 pt-0.5">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-ds-folio-ink leading-tight">Round-Trip</p>
          <p className="text-xs text-ds-folio-ink-mist mt-0.5">Outbound + Return pair</p>
        </div>
        <AiScoreBadge score={aiScore} />
      </div>

      {/* Outbound leg */}
      <div className="rounded-xl bg-ds-linen border border-ds-hairline px-3 py-2.5">
        <FlightLegRow leg={outbound} label="Outbound" />
      </div>

      {/* Return leg */}
      <div className="rounded-xl bg-ds-linen border border-ds-hairline px-3 py-2.5">
        <FlightLegRow leg={returnFlight} label="Return" />
      </div>

      {/* Combined pricing */}
      <div className="grid grid-cols-3 gap-2 pt-2 border-t border-ds-hairline">
        {totalPrice > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-ds-folio-ink-mist uppercase tracking-wide">Total Cash</p>
            <p className="text-sm font-bold text-ds-folio-ink">${Math.round(totalPrice)}</p>
          </div>
        )}
        {totalPoints > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-ds-folio-ink-mist uppercase tracking-wide">Total Pts</p>
            <p className="text-sm font-bold text-ds-accent">
              {totalPoints >= 1000 ? `${(totalPoints / 1000).toFixed(0)}k` : totalPoints}
            </p>
          </div>
        )}
        {combinedCpp > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-ds-folio-ink-mist uppercase tracking-wide">CPP</p>
            <p className={`text-sm font-bold ${combinedCpp >= 2 ? "text-ds-trust-verified" : "text-ds-folio-ink-soft"}`}>
              {combinedCpp.toFixed(2)}¢
            </p>
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-1.5 pt-1">
        {rtGoogleFlightsUrl && rtIsSearchRedirect && (
          <a
            href={rtGoogleFlightsUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            title="Search on Google Flights"
            className={SECONDARY_CTA}
            data-testid="google-flights-cta"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Google Flights
          </a>
        )}
        <button
          onClick={() => onAddToItinerary(item)}
          disabled={adding}
          className={`${PRIMARY_CTA} flex-1`}
          data-testid="flight-add-btn"
        >
          {adding ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
          Add Round Trip
        </button>
      </div>
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

  const containerClass = `${PREMIUM_CARD_BASE} ${isTopPick ? "border-ds-accent/45" : ""} ${isLowScore ? "opacity-55" : ""}`;

  return (
    <div className={containerClass}>
      {isTopPick && (
        <div className="absolute -top-2.5 left-3">
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-ds-accent text-ds-text-inverse shadow-sm">
            <Star className="w-2.5 h-2.5" />
            Top Hotel
          </span>
        </div>
      )}

      {/* Header: name + stars + AI score */}
      <div className="flex items-start justify-between gap-2 pt-0.5">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-ds-folio-ink leading-tight">{name}</p>
          <div className="flex items-center gap-2 mt-0.5">
            {stars != null && (
              <span className="text-xs text-ds-caution">{"★".repeat(Math.min(5, Math.round(stars)))}</span>
            )}
            {/* Only show raw location when it differs from the hotel name and no richer
                area/proximity badges are available — avoids repeating the address as filler. */}
            {location && location.trim().toLowerCase() !== name.trim().toLowerCase() && !(proximityLabel && areaLabel) && (
              <span className="flex items-center gap-0.5 text-xs text-ds-folio-ink-mist truncate">
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
            <span
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium text-ds-trust-verified border border-ds-trust-verified/30"
            >
              <MapPin className="w-2.5 h-2.5" />
              {proximityLabel}
            </span>
          )}
          {areaLabel && areaLabel !== "Farther from center" && (
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border ${
                areaLabel === "In best area"
                  ? "text-ds-accent border-ds-accent/30"
                  : "text-ds-folio-ink-soft border-ds-hairline"
              }`}
              style={areaLabel === "In best area" ? { backgroundColor: "var(--ds-accent-subtle)" } : undefined}
            >
              {areaLabel === "In best area" ? "★ " : ""}{areaLabel}
            </span>
          )}
          {locationScore !== null && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-ds-linen text-ds-folio-ink-mist border border-ds-hairline">
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
        <p className="text-xs text-ds-folio-ink-mist leading-relaxed">{explanation}</p>
      )}

      {/* Pricing grid */}
      <div className="grid grid-cols-3 gap-2 pt-2 border-t border-ds-hairline">
        {pricePerNight > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-ds-folio-ink-mist uppercase tracking-wide">Per Night</p>
            <p className="text-sm font-bold text-ds-folio-ink">${Math.round(pricePerNight)}</p>
          </div>
        )}
        {nights > 1 && pricePerNight > 0 && (
          <div className="text-center">
            <p className="text-[10px] text-ds-folio-ink-mist uppercase tracking-wide">Total</p>
            <p className="text-sm font-bold text-ds-folio-ink">${Math.round(pricePerNight * nights)}</p>
          </div>
        )}
        {rating != null && (
          <div className="text-center">
            <p className="text-[10px] text-ds-folio-ink-mist uppercase tracking-wide">Rating</p>
            <p className="text-sm font-bold text-ds-caution">★ {rating.toFixed(1)}</p>
          </div>
        )}
      </div>

      {/* Amenities */}
      {amenities.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {amenities.slice(0, 3).map((a) => (
            <span key={a} className="px-2 py-0.5 bg-ds-linen border border-ds-hairline rounded-full text-xs text-ds-folio-ink-mist">{a}</span>
          ))}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-1.5 pt-1">
        {onToggleCompare && (
          <button
            onClick={() => onToggleCompare(item)}
            title="Compare"
            className={`${SECONDARY_CTA} ${isComparing ? "bg-ds-accent/20 border-ds-accent/40 text-ds-accent" : ""}`}
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
  const icon =
    tag === "Must Visit"   ? <Zap className="w-2.5 h-2.5" /> :
    tag === "Highly Rated" ? <Star className="w-2.5 h-2.5" /> :
    tag === "Hidden Gem"   ? <Sparkles className="w-2.5 h-2.5" /> :
    null;
  return (
    <span
      className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-xs font-semibold text-ds-accent border border-ds-hairline"
      style={{ backgroundColor: "var(--ds-accent-subtle)" }}
    >
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
          className={`w-2.5 h-2.5 ${i < level ? "text-ds-folio-ink" : "text-ds-folio-ink-mist"}`}
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

  const containerClass = `${PREMIUM_CARD_BASE} ${isTopPick ? "border-ds-accent/45" : ""}`;

  return (
    <div className={containerClass}>
      {isTopPick && (
        <div className="absolute -top-2.5 left-3">
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-ds-accent text-ds-text-inverse shadow-sm">
            <Zap className="w-2.5 h-2.5" />
            Top Pick
          </span>
        </div>
      )}

      {/* Header: name + AI score */}
      <div className="flex items-start justify-between gap-2 pt-0.5">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-ds-folio-ink leading-tight">{attraction.name}</p>
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            {rating != null && (
              <span className="text-xs text-ds-caution font-semibold">★ {rating.toFixed(1)}</span>
            )}
            {numReviews != null && (
              <span className="text-xs text-ds-folio-ink-mist">
                {numReviews >= 1000 ? `${(numReviews / 1000).toFixed(0)}k` : numReviews} reviews
              </span>
            )}
          </div>
        </div>
        <AiScoreBadge score={aiScore} />
      </div>

      {/* Description */}
      {attraction.description && (
        <p className="text-xs text-ds-folio-ink-mist leading-relaxed line-clamp-2">{attraction.description}</p>
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
          <div className="flex items-center gap-1 text-xs text-ds-folio-ink-mist">
            <MapPin className="w-3 h-3 flex-shrink-0" />
            <span className="truncate">{attraction.address}</span>
          </div>
        )}
        <div className="flex items-center gap-3 flex-wrap">
          {attraction.openingHours && (
            <div className="flex items-center gap-1 text-xs text-ds-folio-ink-mist">
              <Clock className="w-3 h-3 flex-shrink-0" />
              <span>{attraction.openingHours}</span>
            </div>
          )}
          {attraction.durationMinutes != null && (
            <span className="text-xs text-ds-folio-ink-mist">
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
  return (
    <span
      className="text-[10px] font-medium px-1.5 py-0.5 rounded-full text-ds-accent border border-ds-hairline"
      style={{ backgroundColor: "var(--ds-accent-subtle)" }}
    >
      {tag}
    </span>
  );
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

  const containerClass = `${PREMIUM_CARD_BASE} gap-2 p-3 ${isTopPick ? "border-ds-accent/45" : ""}`;

  return (
    <div className={containerClass}>
      {isTopPick && (
        <span
          className="absolute top-2 right-2 text-[9px] font-bold uppercase tracking-wide text-ds-accent border border-ds-hairline px-1.5 py-0.5 rounded-full"
          style={{ backgroundColor: "var(--ds-accent-subtle)" }}
        >Top Pick</span>
      )}

      <div className="flex items-start justify-between gap-2 pt-0.5">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-ds-folio-ink leading-tight">{restaurant.name}</p>
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            <span className="text-[10px] text-ds-folio-ink-mist font-medium">{restaurant.cuisine}</span>
            {rating != null && (
              <span className="flex items-center gap-0.5 text-xs text-ds-caution font-semibold">
                <Star className="w-3 h-3 fill-current" />
                {rating.toFixed(1)}
                {numReviews != null && (
                  <span className="text-ds-folio-ink-mist font-normal ml-0.5">
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
          <div className="flex items-center gap-1 text-xs text-ds-folio-ink-mist">
            <MapPin className="w-3 h-3 flex-shrink-0" />
            <span className="truncate">{restaurant.address}</span>
          </div>
        )}
        <div className="flex items-center gap-3 flex-wrap">
          {restaurant.openingHours && (
            <div className="flex items-center gap-1 text-xs text-ds-folio-ink-mist">
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
      <span className="text-[9px] font-semibold uppercase tracking-wider text-ds-folio-ink-mist">{label}</span>
      <div className="flex flex-wrap gap-1">
        {options.map((opt) => (
          <button
            type="button"
            key={String(opt.value ?? "all")}
            onClick={() => onChange(opt.value === value ? null : opt.value)}
            className="group min-h-[44px] flex items-center justify-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
          >
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium transition-all border ${
              opt.value === value
                ? "bg-ds-accent text-ds-text-inverse border-ds-accent"
                : "bg-ds-linen text-ds-folio-ink-soft border-ds-hairline group-hover:border-ds-carbon group-hover:text-ds-folio-ink"
            }`}>
              {opt.label}
            </span>
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
  open: boolean;
  onToggle: () => void;
  sortControls?: React.ReactNode;
  listRef?: React.Ref<HTMLDivElement>;
  emptyMessage?: string;
  children: React.ReactNode;
}) {
  const hasData = (totalCount ?? count) > 0;
  const displayCount = totalCount !== undefined && totalCount !== count
    ? `${count}/${totalCount}` : count;
  return (
    <div className="folio-paper-panel overflow-hidden">
      <button
        type="button"
        onClick={onToggle}
        className="flex items-center justify-between w-full px-4 py-3 min-h-[44px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
      >
        <span className="flex items-center gap-2">
          {icon}
          <span className="text-sm font-semibold text-ds-folio-ink">{title}</span>
          <span
            className="px-1.5 py-0.5 rounded-full text-[10px] font-semibold text-ds-accent border border-ds-hairline"
            style={{ backgroundColor: "var(--ds-accent-subtle)" }}
          >
            {displayCount}
          </span>
        </span>
        {open
          ? <ChevronUp className="w-4 h-4 text-ds-folio-ink-mist" />
          : <ChevronDown className="w-4 h-4 text-ds-folio-ink-mist" />}
      </button>
      {open && (
        <div className="border-t border-ds-hairline">
          {sortControls && (
            <div className="px-4 py-3 border-b border-ds-hairline">{sortControls}</div>
          )}
          {!hasData && (
            <p className="px-4 py-4 text-xs text-ds-folio-ink-mist text-center">{emptyMessage}</p>
          )}
          {hasData && (
            <div ref={listRef} className="flex flex-col gap-3 max-h-[540px] overflow-y-auto py-3 px-4">
              {children}
            </div>
          )}
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
  /** Mobile workspace IA — controls which panel is visible on mobile.
   *  null (or omitted) = show all panels (desktop behaviour). */
  mobileWorkspace?: "build" | "itinerary" | "ideas" | null;
  /** Pre-select a day when arriving from the Add-to-Day flow (Journey Desk handoff).
   *  Updates the day selector without resetting any other Build state. */
  focusDayId?: string | null;
  /** Open and scroll to the matching CandidatePanel when arriving from the Add-to-Day drawer.
   *  "flight" | "hotel" | "restaurant" | "attraction" — maps to the four existing panels. */
  focusVertical?: string | null;
}

// ─── Main component ───────────────────────────────────────────────────────────

export function TripBuilder({ tripId, destination, startDate, endDate, initialDays, initialResults, ideasRefreshKey, onIdeaAssigned, mobileWorkspace, focusDayId, focusVertical }: TripBuilderProps) {
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

  // ── Add Note modal state ─────────────────────────────────────────────────────
  const [addNoteTargetDayId, setAddNoteTargetDayId] = useState<string | null>(null);

  const flightListRef      = useRef<HTMLDivElement>(null);
  const hotelListRef       = useRef<HTMLDivElement>(null);
  const attractionListRef  = useRef<HTMLDivElement>(null);
  const restaurantListRef  = useRef<HTMLDivElement>(null);
  const prevViewModeRef    = useRef<"list" | "map">("list");
  // Panel-level refs for scroll-into-view on Add-to-Day vertical handoff.
  const flightPanelRef     = useRef<HTMLDivElement>(null);
  const hotelPanelRef      = useRef<HTMLDivElement>(null);
  const attractionPanelRef = useRef<HTMLDivElement>(null);
  const restaurantPanelRef = useRef<HTMLDivElement>(null);

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

  // Add-to-Day handoff: sync the Build day selector to the Journey Desk choice.
  useEffect(() => {
    if (focusDayId && days.some((d) => d.id === focusDayId)) {
      setSelectedDayId(focusDayId);
    }
  }, [focusDayId, days]);

  // Add-to-Day vertical handoff: open the matching CandidatePanel and scroll it into view.
  // For attraction/restaurant, also ensure list view is active (panels live in list-only branch).
  useEffect(() => {
    if (!focusVertical) return;
    let t: ReturnType<typeof setTimeout> | null = null;
    if (focusVertical === "flight") {
      setFlightPanelOpen(true);
      t = setTimeout(() => flightPanelRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }), 0);
    } else if (focusVertical === "hotel") {
      setHotelPanelOpen(true);
      t = setTimeout(() => hotelPanelRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }), 0);
    } else if (focusVertical === "attraction") {
      setViewMode("list");
      setAttractionPanelOpen(true);
      t = setTimeout(() => attractionPanelRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }), 0);
    } else if (focusVertical === "restaurant") {
      setViewMode("list");
      setRestaurantPanelOpen(true);
      t = setTimeout(() => restaurantPanelRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }), 0);
    }
    return () => { if (t !== null) clearTimeout(t); };
  }, [focusVertical]);

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

  // ── Add round-trip flight: two leg items on actual departure days ────────────

  // Extract a plain ISO date (YYYY-MM-DD) from a round-trip leg object.
  // Tries camelCase, snake_case, and segment[0] departure fields in sequence.
  // Returns undefined (never today's date) when no valid date is found.
  const extractLegDepartureDate = useCallback(
    (legData: Record<string, unknown> | undefined): string | undefined => {
      if (!legData) return undefined;
      const segs = Array.isArray(legData.segments) ? (legData.segments as Record<string, unknown>[]) : [];
      const seg0 = segs[0] as Record<string, unknown> | undefined;
      const raw =
        (legData.departureTime as string | undefined) ??
        (legData.departure_time as string | undefined) ??
        (legData.departureDateTime as string | undefined) ??
        (legData.departure_datetime as string | undefined) ??
        (legData.departureDate as string | undefined) ??
        (legData.departure_date as string | undefined) ??
        (legData.date as string | undefined) ??
        (seg0?.departureTime as string | undefined) ??
        (seg0?.departure_time as string | undefined) ??
        (seg0?.departureDateTime as string | undefined) ??
        (seg0?.departure_datetime as string | undefined) ??
        (seg0?.departureDate as string | undefined) ??
        (seg0?.departure_date as string | undefined);
      return normalizeIsoDate(raw?.slice(0, 10));
    },
    []
  );

  // Find the itinerary day whose date matches the given ISO date exactly.
  const resolveItineraryDayByDate = useCallback(
    (isoDate: string | undefined): import("@/types").ItineraryDay | null => {
      if (!isoDate) return null;
      return days.find((dy) => normalizeIsoDate(dy.date) === isoDate) ?? null;
    },
    [days]
  );

  // A canonical round-trip Duffel offer is split into two standalone one-way
  // flight items: outbound on the outbound departure day, return on the return
  // departure day. Days are resolved from each leg's departure timestamp.
  // If dates cannot be extracted or matched, nothing is persisted and a toast explains why.
  // Price: outbound carries the full round-trip price; return carries 0.
  const handleAddRoundTripToItinerary = useCallback(async (item: ItineraryItem) => {
    setAddingId(item.id);
    try {
      if (days.length === 0) {
        showToast("No days available — days are generated from trip dates");
        return;
      }

      const d = (item.details ?? {}) as Record<string, unknown>;
      const outbound = (d.outboundLeg ?? d.outbound_leg ?? d.outbound) as Record<string, unknown> | undefined;
      const ret = (d.returnLeg ?? d.return_leg ?? d.returnFlight ?? d.return_flight) as Record<string, unknown> | undefined;

      const outboundDate = extractLegDepartureDate(outbound);
      const returnDate = extractLegDepartureDate(ret);

      // Fail closed — never place legs on arbitrary days if dates are missing
      if (!outboundDate || !returnDate) {
        showToast("Could not place round-trip flight because flight dates were missing.");
        return;
      }

      const outboundDay = resolveItineraryDayByDate(outboundDate);
      const returnDay = resolveItineraryDayByDate(returnDate);

      if (!outboundDay || !returnDay) {
        showToast("Flight date does not match this trip's itinerary days.");
        return;
      }

      const outboundItem = await addRoundTripLegToDay(
        tripId, outboundDay.id, item, "outbound", outboundDay.items.length
      );

      const returnPosition =
        outboundDay.id === returnDay.id
          ? outboundDay.items.length + 1
          : returnDay.items.length;

      let returnItem: ItineraryItem;
      try {
        returnItem = await addRoundTripLegToDay(
          tripId, returnDay.id, item, "return", returnPosition
        );
      } catch (returnErr) {
        // Outbound succeeded but return failed — best-effort rollback to avoid half-added state
        try { await deleteItem(outboundItem.id); } catch { /* ignore rollback failure */ }
        throw returnErr;
      }

      // Both legs succeeded — update local state together
      setDays((prev) =>
        prev.map((day) => {
          if (day.id === outboundDay.id && day.id === returnDay.id) {
            return { ...day, items: [...day.items, outboundItem, returnItem] };
          }
          if (day.id === outboundDay.id) return { ...day, items: [...day.items, outboundItem] };
          if (day.id === returnDay.id) return { ...day, items: [...day.items, returnItem] };
          return day;
        })
      );

      const msg =
        outboundDay.dayNumber === returnDay.dayNumber
          ? `Round-trip flight added to Day ${outboundDay.dayNumber}`
          : `Round-trip: outbound Day ${outboundDay.dayNumber}, return Day ${returnDay.dayNumber}`;
      showToast(msg);
    } catch {
      showToast("Failed to add round-trip flight — please try again");
    } finally {
      setAddingId(null);
    }
  }, [days, tripId, showToast, extractLegDepartureDate, resolveItineraryDayByDate]);

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

  const handleAddToDay = useCallback((dayId: string) => {
    if (!days.find((d) => d.id === dayId)) return;
    setAddNoteTargetDayId(dayId);
  }, [days]);

  const handleSaveNote = useCallback(async (title: string, description: string) => {
    const dayId = addNoteTargetDayId;
    if (!dayId) return;
    const day = days.find((d) => d.id === dayId);
    if (!day) return;
    setAddNoteTargetDayId(null);
    try {
      const newItem = await createItem(tripId, dayId, {
        itemType: "note" as ItemType,
        title,
        ...(description ? { description } : {}),
        position: day.items.length,
      });
      setDays((prev) =>
        prev.map((d) => d.id === dayId ? { ...d, items: [...d.items, newItem] } : d)
      );
    } catch {
      showToast("Failed to add note — please try again");
    }
  }, [addNoteTargetDayId, days, tripId, showToast]);

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
        <div className="flex flex-col gap-4 min-h-[500px] lg:flex-row lg:items-start">

          {/* ── Left Panel: AI-ranked candidates ──────────────────────────── */}
          <div
            data-testid="trip-mobile-panel-build"
            className={`w-full flex flex-col gap-3 overflow-y-auto pr-0.5 lg:w-80 lg:flex-shrink-0 ${
              mobileWorkspace != null && mobileWorkspace !== "build" ? "hidden lg:flex" : ""
            }`}
          >

            {/* Planning cockpit context header */}
            <div className="flex flex-col gap-0.5 px-1 pt-1 pb-0.5">
              <span className="text-[10px] font-semibold text-ds-folio-ink-mist uppercase tracking-[0.1em]">Planning</span>
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-semibold text-ds-folio-ink truncate">{destination}</span>
                {selectedDayId && displayDays.find((d) => d.id === selectedDayId) && (
                  <>
                    <span className="text-ds-folio-ink-mist text-sm">·</span>
                    <span className="text-xs text-ds-marine-ink font-medium">
                      Day {displayDays.find((d) => d.id === selectedDayId)!.dayNumber}
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* Summary bar */}
            <SummaryBar topFlight={topFlight} topHotel={topHotel} />

            {/* Flights section */}
            <div ref={flightPanelRef}>
            <CandidatePanel
              title="Flights"
              icon={<Plane className="w-3.5 h-3.5 text-ds-accent" />}
              count={sortedFlights.length}
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
                // Canonical round-trip detection — must match `isRoundTripFlight` in
                // tripCandidates.ts so create-with-search-seeded canonical offers
                // (trip_type="round_trip" / returnLeg present) render in the
                // round-trip group, not the one-way group.
                const isRT = (it: ItineraryItem): boolean => {
                  const d = (it.details ?? {}) as Record<string, unknown>;
                  if (d.isRoundTrip != null) return Boolean(d.isRoundTrip);
                  if (d.is_round_trip != null) return Boolean(d.is_round_trip);
                  if (d.tripType === "round_trip" || d.trip_type === "round_trip") return true;
                  if (d.returnLeg != null || d.return_leg != null) return true;
                  return false;
                };
                const oneWay     = sortedFlights.filter((it) => !isRT(it));
                const roundTrip  = sortedFlights.filter((it) => isRT(it));
                const showOWLabel = oneWay.length > 0 && roundTrip.length > 0;
                const showRTLabel = roundTrip.length > 0 && oneWay.length > 0;
                const owTop20 = Math.max(1, Math.ceil(oneWay.length * 0.2));
                const rtTop20 = Math.max(1, Math.ceil(roundTrip.length * 0.2));
                const nodes: React.ReactNode[] = [];
                if (showOWLabel) {
                  nodes.push(
                    <p key="ow-label" className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-folio-ink-mist px-1 pb-1">
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
                    <p key="rt-label" className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-folio-ink-mist pt-2 pb-1 px-1">
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
            </div>

            {/* Hotels section */}
            <div ref={hotelPanelRef}>
            <CandidatePanel
              title="Hotels"
              icon={<Hotel className="w-3.5 h-3.5 text-ds-accent" />}
              count={sortedHotels.length}
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
            </div>

            {/* ── Explore: List / Map / Group toggle ────────────────────── */}
            <div className="flex items-center justify-between px-1 pt-1">
              <span className="text-[10px] font-semibold text-ds-folio-ink-mist uppercase tracking-[0.1em]">Explore</span>
              <div className="flex items-center bg-ds-linen rounded-lg p-0.5 gap-0.5 border border-ds-hairline">
                <button
                  type="button"
                  onClick={() => setViewMode("list")}
                  className={`flex items-center gap-1 px-2.5 min-h-[44px] rounded-md text-xs font-medium transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-1 ${
                    viewMode === "list"
                      ? "bg-ds-bone text-ds-folio-ink shadow-sm"
                      : "text-ds-folio-ink-mist hover:text-ds-folio-ink"
                  }`}
                >
                  <LayoutList className="w-3 h-3" />
                  List
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode("map")}
                  className={`flex items-center gap-1 px-2.5 min-h-[44px] rounded-md text-xs font-medium transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-1 ${
                    viewMode === "map"
                      ? "bg-ds-bone text-ds-folio-ink shadow-sm"
                      : "text-ds-folio-ink-mist hover:text-ds-folio-ink"
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
                <div ref={attractionPanelRef}>
                <CandidatePanel
                  title="Attractions"
                  icon={<Sparkles className="w-3.5 h-3.5 text-ds-accent" />}
                  count={filteredAttractions.length}
                  totalCount={candidateAttractions.length}
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
                    <p className="text-xs text-ds-folio-ink-mist py-4 text-center">Nothing matches the current filters — try widening the selection.</p>
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
                              ? "ring-2 ring-ds-accent ring-offset-1"
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
                </div>

                {/* Restaurants section */}
                <div ref={restaurantPanelRef}>
                <CandidatePanel
                  title="Restaurants"
                  icon={<UtensilsCrossed className="w-3.5 h-3.5 text-ds-accent" />}
                  count={filteredRestaurants.length}
                  totalCount={candidateRestaurants.length}
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
                    <p className="text-xs text-ds-folio-ink-mist py-4 text-center">Nothing matches the current filters — try widening the selection.</p>
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
                              ? "ring-2 ring-ds-accent ring-offset-1"
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
                </div>
              </>
            )}

            {/* Activities / research results */}
            {results.length > 0 && (
              <FolioPanel data-testid="trip-build-activities-panel">
                <div className="px-4 py-3 flex items-center gap-2 border-b border-ds-hairline">
                  <Sparkles className="w-3.5 h-3.5 text-ds-accent" />
                  <span className="text-sm font-semibold text-ds-folio-ink">Activities</span>
                  <span className="px-1.5 py-0.5 rounded-full text-[10px] font-semibold text-ds-accent border border-ds-hairline" style={{ backgroundColor: "var(--ds-accent-subtle)" }}>
                    {results.length}
                  </span>
                </div>
                <div className="flex flex-col gap-2 max-h-[360px] overflow-y-auto py-3 px-4">
                  {results.map((result) => (
                    <SearchResultCard
                      key={result.id}
                      result={result}
                      onAdd={handleAddResult}
                    />
                  ))}
                </div>
              </FolioPanel>
            )}
          </div>

          {/* ── Right Panel: Itinerary Timeline ───────────────────────────── */}
          <div className={`flex-1 flex flex-col gap-3 overflow-visible ${
            mobileWorkspace === "build" ? "hidden lg:flex" : ""
          }`}>
            <div
              data-testid="trip-mobile-itinerary-chrome"
              className={`flex items-center justify-between gap-2 flex-wrap ${
                mobileWorkspace === "ideas" ? "hidden lg:flex" : ""
              }`}
            >
              <div className="flex flex-col gap-0.5">
                <span className="text-[10px] font-semibold text-ds-folio-ink-mist uppercase tracking-[0.1em]">Your Itinerary</span>
                <span className="text-xs text-ds-folio-ink-mist">
                  {days.reduce((sum, d) => sum + d.items.length, 0)} items · {days.length} day{days.length !== 1 ? "s" : ""}
                </span>
              </div>
              <div className="flex items-center gap-2">
                {/* Target day selector — left-panel "+" buttons add to this day */}
                {days.length > 0 && (
                  <label className="flex items-center gap-2 bg-ds-linen rounded-xl border border-ds-hairline px-3 min-h-[44px] cursor-pointer focus-within:outline focus-within:outline-2 focus-within:outline-ds-accent focus-within:outline-offset-2 transition-colors">
                    <span className="text-[10px] font-semibold text-ds-folio-ink-mist uppercase tracking-[0.1em] whitespace-nowrap">Add to</span>
                    <select
                      value={selectedDayId ?? ""}
                      onChange={(e) => setSelectedDayId(e.target.value || null)}
                      className="text-xs font-semibold text-ds-folio-ink bg-ds-linen border-none outline-none focus:outline-none focus-visible:outline-none cursor-pointer py-0"
                    >
                      {displayDays.map((d) => (
                        <option key={d.id} value={d.id}>
                          Day {d.dayNumber}{d.date ? ` · ${d.date}` : ""}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                {/* "Add Day" only shown when days are not auto-derived from trip dates */}
                {canManuallyAddExpectedDay && (
                  <button
                    type="button"
                    onClick={handleAddDay}
                    className="flex items-center gap-1.5 min-h-[44px] px-3 rounded-xl border border-ds-hairline bg-ds-linen text-xs font-medium text-ds-folio-ink-soft hover:bg-ds-bone hover:text-ds-folio-ink transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
                  >
                    <CalendarPlus className="w-3.5 h-3.5" />
                    Add Day
                  </button>
                )}
              </div>
            </div>

            <div
              data-testid="trip-mobile-panel-ideas"
              className={mobileWorkspace != null && mobileWorkspace !== "ideas" ? "hidden lg:block" : ""}
            >
              <TripIdeasPanel
                tripId={tripId}
                days={displayDays}
                refreshKey={(ideasRefreshKey ?? 0) + ideasRefreshNonce}
                onIdeaAssigned={onIdeaAssigned}
              />
            </div>

            <div
              data-testid="trip-mobile-panel-itinerary"
              className={`flex flex-col gap-3 pr-0.5 overflow-visible ${
                mobileWorkspace != null && mobileWorkspace !== "itinerary" ? "hidden lg:flex" : ""
              }`}
            >
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
                <div className="rounded-lg border border-ds-hairline bg-ds-bone p-8 text-center text-ds-folio-ink-mist">
                  <CalendarPlus className="w-8 h-8 mx-auto mb-2 text-ds-folio-ink-mist" />
                  <p className="text-sm font-medium text-ds-folio-ink-soft">No days yet</p>
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
          <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-40 flex items-center gap-3 px-4 py-3 bg-ds-onyx border border-ds-pen-stroke rounded-2xl shadow-[var(--ds-elevation-4)] max-w-[calc(100vw-2rem)] sm:bottom-6 sm:px-5">
            <div className="flex flex-col gap-0.5">
              <span className="text-[10px] font-semibold text-ds-text-tertiary uppercase tracking-[0.1em]">Compare</span>
              <div className="flex items-center gap-1">
                {Array.from({ length: Math.min(compareSet.size, 10) }).map((_, i) => (
                  <div key={i} className="w-1.5 h-1.5 rounded-full bg-ds-accent" />
                ))}
              </div>
            </div>
            <div className="w-px h-6 bg-ds-pen-stroke" />
            <span className="text-sm font-medium text-ds-text">
              {compareSet.size} item{compareSet.size !== 1 ? "s" : ""}
              {compareSet.size < 2 && <span className="text-ds-text-tertiary text-xs ml-1">(need 2+)</span>}
            </span>
            {compareRouteSummary && (
              <>
                <div className="w-px h-4 bg-ds-pen-stroke" />
                <span className="flex items-center gap-1 text-xs text-ds-trust-verified">
                  <Navigation className="w-3 h-3" />
                  {compareRouteSummary.totalKm} km · ~{compareRouteSummary.totalDriveMin} min drive
                </span>
              </>
            )}
            <div className="w-px h-4 bg-ds-pen-stroke" />
            <button
              type="button"
              onClick={handleCompare}
              disabled={compareSet.size < 2 || compareLoading}
              className="min-h-[44px] px-4 rounded-lg bg-ds-accent hover:bg-ds-accent-muted text-ds-text-inverse disabled:opacity-40 disabled:cursor-not-allowed text-sm font-semibold transition-colors flex items-center gap-1.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
            >
              {compareLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <BarChart2 className="w-3.5 h-3.5" />}
              Compare
            </button>
            <button
              type="button"
              onClick={() => { setCompareSet(new Set()); compareDataRef.current.clear(); }}
              className="min-h-[44px] min-w-[44px] flex items-center justify-center text-ds-text-tertiary hover:text-ds-text text-xs transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
            >
              Clear
            </button>
          </div>
        )}

        {/* ── Drag Overlay ─────────────────────────────────────────────────── */}
        <DragOverlay>
          {activeDragItem && isResultDrag && (
            <div className="rotate-1 scale-105 shadow-[var(--ds-elevation-3)] opacity-95 w-72">
              <SearchResultCard result={activeDragItem as ResearchResult} onAdd={() => {}} />
            </div>
          )}
          {activeDragItem && !isResultDrag && (
            <div className="rotate-1 scale-105 shadow-[var(--ds-elevation-3)] opacity-95">
              <ItineraryItemCard item={activeDragItem as ItineraryItem} onRemove={() => {}} />
            </div>
          )}
        </DragOverlay>
      </DndContext>

      {/* ── Add Note Modal ───────────────────────────────────────────────────── */}
      {addNoteTargetDayId && (
        <AddNoteModal
          dayNumber={days.find((d) => d.id === addNoteTargetDayId)?.dayNumber ?? 1}
          onSave={handleSaveNote}
          onCancel={() => setAddNoteTargetDayId(null)}
        />
      )}

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
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 bg-ds-onyx border border-ds-pen-stroke text-ds-text rounded-xl shadow-[var(--ds-elevation-3)] text-sm font-medium animate-in fade-in slide-in-from-bottom-2">
          <CheckCircle2 className="w-4 h-4 text-ds-trust-verified flex-shrink-0" />
          {toast}
          <button type="button" onClick={() => setToast(null)} className="ml-1 min-h-[44px] min-w-[44px] flex items-center justify-center text-ds-text-tertiary hover:text-ds-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </>
  );
}

// ─── AddNoteModal ─────────────────────────────────────────────────────────────

function AddNoteModal({
  dayNumber,
  onSave,
  onCancel,
}: {
  dayNumber: number;
  onSave: (title: string, description: string) => void;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const titleRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    titleRef.current?.focus();
  }, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const t = title.trim();
    if (!t) return;
    onSave(t, description.trim());
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Add note to Day ${dayNumber}`}
      data-testid="add-note-modal"
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60"
      onClick={(e) => { if (e.target === e.currentTarget) onCancel(); }}
    >
      <div
        data-folio-world="paper"
        data-testid="add-note-modal-panel"
        className="w-full sm:max-w-md rounded-t-2xl sm:rounded-2xl bg-ds-paper border border-ds-hairline shadow-[var(--ds-elevation-3)]"
        style={{ padding: "var(--ds-space-6)" }}
      >
        <div className="flex items-center gap-2 mb-4">
          <FileText className="h-4 w-4 text-ds-accent shrink-0" aria-hidden="true" />
          <h2
            className="text-ds-folio-ink font-semibold"
            style={{ fontSize: "var(--ds-type-body-l-size)" }}
          >
            Add note — Day {dayNumber}
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label
              htmlFor="add-note-title"
              className="text-ds-folio-ink-mist uppercase tracking-[0.1em]"
              style={{
                display: "block",
                fontSize: "var(--ds-type-overline-size)",
                fontWeight: "var(--ds-type-overline-weight)",
                marginBottom: "var(--ds-space-1)",
              }}
            >
              Title <span aria-hidden="true">*</span>
            </label>
            <input
              ref={titleRef}
              id="add-note-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Place or note title"
              required
              data-testid="add-note-title-input"
              data-folio-world="paper"
              className="folio-input rounded-xl"
              style={{
                padding: "var(--ds-space-3) var(--ds-space-4)",
                fontSize: "var(--ds-type-body-size)",
                minHeight: "44px",
              }}
            />
          </div>

          <div>
            <label
              htmlFor="add-note-description"
              className="text-ds-folio-ink-mist uppercase tracking-[0.1em]"
              style={{
                display: "block",
                fontSize: "var(--ds-type-overline-size)",
                fontWeight: "var(--ds-type-overline-weight)",
                marginBottom: "var(--ds-space-1)",
              }}
            >
              Details <span className="text-ds-folio-ink-mist normal-case tracking-normal" style={{ fontSize: "var(--ds-type-caption-size)" }}>(optional)</span>
            </label>
            <textarea
              id="add-note-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Paste Google Maps links or reservation links here — they'll become clickable in the itinerary."
              rows={3}
              data-testid="add-note-description-input"
              data-folio-world="paper"
              className="folio-input resize-none rounded-xl"
              style={{
                padding: "var(--ds-space-3) var(--ds-space-4)",
                fontSize: "var(--ds-type-body-size)",
                minHeight: "auto",
              }}
            />
          </div>

          <p
            className="text-ds-folio-ink-mist"
            style={{ fontSize: "var(--ds-type-caption-size)", lineHeight: "var(--ds-type-caption-leading)" }}
          >
            To add restaurants, attractions, hotels, or flights, use Build, Saved Ideas, or AI Concierge.
          </p>

          <div className="flex items-center gap-2 pt-1">
            <FolioButton
              type="submit"
              variant="primary"
              disabled={!title.trim()}
              data-testid="add-note-save-btn"
              className="flex-1 justify-center"
            >
              Save note
            </FolioButton>
            <FolioButton
              type="button"
              variant="secondary"
              onClick={onCancel}
              data-testid="add-note-cancel-btn"
              className="justify-center"
            >
              Cancel
            </FolioButton>
          </div>
        </form>
      </div>
    </div>
  );
}
