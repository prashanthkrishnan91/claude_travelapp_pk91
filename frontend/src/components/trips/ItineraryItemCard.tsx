"use client";

import { useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  Plane,
  Hotel,
  MapPin,
  Utensils,
  Train,
  FileText,
  GripVertical,
  X,
  Clock,
  DollarSign,
  Coins,
  Scale,
  Ticket,
  Zap,
  Star,
  ExternalLink,
} from "lucide-react";
import { ItineraryItem, ItemType } from "@/types";
import { BookingChecklistModal } from "./BookingChecklistModal";
import { RewardsIntelligencePanel } from "./RewardsIntelligencePanel";
import { updateItemTimeline } from "@/lib/api";

// ─── Timeline day-part options ────────────────────────────────────────────────

const DAY_PARTS = [
  { value: "morning",     label: "Morning",     activeClass: "bg-amber-500/20 border-amber-400/50 text-amber-300" },
  { value: "afternoon",   label: "Afternoon",   activeClass: "bg-sky-500/20 border-sky-400/50 text-sky-300" },
  { value: "evening",     label: "Evening",     activeClass: "bg-violet-500/20 border-violet-400/50 text-violet-300" },
  { value: "unscheduled", label: "Unscheduled", activeClass: "bg-slate-700/60 border-slate-500/50 text-slate-300" },
] as const;

// ─── Type icon config ─────────────────────────────────────────────────────────

interface ItineraryItemCardProps {
  item: ItineraryItem;
  onRemove: (itemId: string) => void;
  onMoveToIdeas?: (itemId: string) => void;
  onToggleCompare?: (item: ItineraryItem) => void;
  isComparing?: boolean;
  onTimelineUpdated?: (updatedItem: ItineraryItem) => void;
}

const typeConfig: Record<
  ItemType,
  { icon: React.ReactNode; colorClass: string; bgClass: string; borderClass: string }
> = {
  flight: {
    icon: <Plane className="w-3.5 h-3.5" />,
    colorClass: "text-sky-300",
    bgClass: "bg-sky-500/10",
    borderClass: "border-sky-500/25",
  },
  hotel: {
    icon: <Hotel className="w-3.5 h-3.5" />,
    colorClass: "text-violet-300",
    bgClass: "bg-violet-500/10",
    borderClass: "border-violet-500/25",
  },
  activity: {
    icon: <MapPin className="w-3.5 h-3.5" />,
    colorClass: "text-emerald-300",
    bgClass: "bg-emerald-500/10",
    borderClass: "border-emerald-500/25",
  },
  meal: {
    icon: <Utensils className="w-3.5 h-3.5" />,
    colorClass: "text-amber-300",
    bgClass: "bg-amber-500/10",
    borderClass: "border-amber-500/25",
  },
  transit: {
    icon: <Train className="w-3.5 h-3.5" />,
    colorClass: "text-slate-300",
    bgClass: "bg-slate-700/40",
    borderClass: "border-slate-600/60",
  },
  note: {
    icon: <FileText className="w-3.5 h-3.5" />,
    colorClass: "text-rose-300",
    bgClass: "bg-rose-500/10",
    borderClass: "border-rose-500/25",
  },
};

function formatClock(value?: string): string | null {
  if (!value) return null;
  const hhmm = value.match(/T(\d{2}):(\d{2})/);
  if (hhmm) {
    const hour24 = Number(hhmm[1]);
    const minute = hhmm[2];
    const hour12 = ((hour24 + 11) % 12) + 1;
    const ampm = hour24 >= 12 ? "PM" : "AM";
    return `${hour12}:${minute} ${ampm}`;
  }
  const d = new Date(value);
  if (!Number.isNaN(d.getTime())) {
    return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  }
  return value;
}

export function ItineraryItemCard({ item, onRemove, onMoveToIdeas, onToggleCompare, isComparing, onTimelineUpdated }: ItineraryItemCardProps) {
  const [bookingOpen, setBookingOpen] = useState(false);
  const [timelineOpen, setTimelineOpen] = useState(false);
  const [selectedPart, setSelectedPart] = useState<string>("unscheduled");
  const [timeLabelInput, setTimeLabelInput] = useState("");
  const [saving, setSaving] = useState(false);

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: item.id,
    data: { type: "itinerary-item", item },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const config = typeConfig[item.itemType];
  const details = (item.details ?? {}) as Record<string, unknown>;
  const isConciergeIdea = details.sourceKind === "concierge_idea" || details.source_kind === "concierge_idea";
  const showMoveToIdeasAction = isConciergeIdea && !!onMoveToIdeas;
  // Normalize to typed strings before any JSX use — avoids unknown→ReactNode error in strict builds
  const dayPartValue = typeof details.dayPart === "string" ? details.dayPart : "";
  const timeLabelValue = typeof details.timeLabel === "string" ? details.timeLabel : "";
  const hasSchedule = !!(dayPartValue || timeLabelValue);

  const handleOpenTimeline = () => {
    setSelectedPart(dayPartValue || "unscheduled");
    setTimeLabelInput(timeLabelValue);
    setTimelineOpen(true);
  };

  const handleSaveTimeline = async () => {
    setSaving(true);
    try {
      const currentDetails = (item.details ?? {}) as Record<string, unknown>;
      const updated = await updateItemTimeline(item.id, currentDetails, {
        dayPart: selectedPart,
        timeLabel: timeLabelInput.trim() || undefined,
      });
      onTimelineUpdated?.(updated);
      setTimelineOpen(false);
    } catch (err) {
      console.error("[timeline] save failed:", err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
    <div
      ref={setNodeRef}
      style={style}
      className={`group relative flex items-start gap-2 p-2 rounded-lg border transition-all duration-200 ${
        isDragging
          ? "opacity-60 shadow-xl scale-95 border-amber-400/70 bg-slate-900/85 backdrop-blur-md"
          : "bg-slate-900/90 border-slate-700 shadow-sm hover:border-slate-600 hover:shadow-md"
      }`}
    >
      {/* Drag handle */}
      <button
        {...listeners}
        {...attributes}
        className="mt-0.5 flex-shrink-0 cursor-grab active:cursor-grabbing text-slate-600 group-hover:text-slate-400 transition-colors"
        aria-label="Drag to reorder"
      >
        <GripVertical className="w-4 h-4" />
      </button>

      {/* Type icon */}
      <div className={`flex-shrink-0 w-5 h-5 rounded-md flex items-center justify-center ${config.bgClass} ${config.colorClass}`}>
        {config.icon}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-1">
          <span className="text-xs font-semibold text-slate-100 leading-tight line-clamp-1" title={item.title}>
            {item.title}
          </span>
          <div className="flex items-center gap-1 flex-shrink-0">
            {showMoveToIdeasAction && (
              <button
                onClick={() => onMoveToIdeas(item.id)}
                className="flex-shrink-0 rounded-md border border-amber-300/35 bg-amber-300/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-200 hover:bg-amber-300/20 transition-colors"
                aria-label={`Move ${item.title} back to Trip Ideas`}
              >
                Move to Ideas
              </button>
            )}
            {onToggleCompare && (
              <button
                onClick={() => onToggleCompare(item)}
                className={`w-5 h-5 rounded-md flex items-center justify-center transition-all ${
                  isComparing
                    ? "opacity-100 bg-violet-600 text-white"
                    : "opacity-0 group-hover:opacity-100 bg-slate-800 hover:bg-violet-500/20 text-slate-400 hover:text-violet-300"
                }`}
                aria-label={isComparing ? `Remove ${item.title} from compare` : `Add ${item.title} to compare`}
              >
                <Scale className="w-3 h-3" />
              </button>
            )}
            {/* Timeline edit trigger */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                if (timelineOpen) {
                  setTimelineOpen(false);
                } else {
                  handleOpenTimeline();
                }
              }}
              className={`flex-shrink-0 w-5 h-5 rounded-md flex items-center justify-center transition-all ${
                timelineOpen
                  ? "opacity-100 bg-amber-500/20 text-amber-300"
                  : hasSchedule
                    ? "opacity-75 bg-slate-800 text-slate-500 hover:bg-amber-500/15 hover:text-amber-300"
                    : "opacity-100 md:opacity-0 md:group-hover:opacity-100 bg-slate-800 hover:bg-amber-500/15 text-slate-400 hover:text-amber-300"
              }`}
              aria-label="Set timeline"
              title="Set timeline"
            >
              <Clock className="w-3 h-3" />
            </button>
            <button
              onClick={() => setBookingOpen(true)}
              className="flex-shrink-0 w-5 h-5 rounded-md opacity-0 group-hover:opacity-100 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 flex items-center justify-center transition-all"
              aria-label={`Book ${item.title}`}
            >
              <Ticket className="w-3 h-3" />
            </button>
            <button
              onClick={() => onRemove(item.id)}
              className="flex-shrink-0 w-5 h-5 rounded-md opacity-0 group-hover:opacity-100 bg-slate-800 hover:bg-rose-500/20 text-slate-400 hover:text-rose-300 flex items-center justify-center transition-all"
              aria-label={`Remove ${item.title}`}
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        </div>

        {item.description && (
          <p className="text-[11px] text-slate-400 mt-0.5 line-clamp-1">
            {item.description}
          </p>
        )}

        {/* Flight leg details: route + times extracted from stored details */}
        {item.itemType === "flight" && (() => {
          const d = (item.details ?? {}) as Record<string, unknown>;
          const origin      = d.origin      as string | undefined;
          const destination = d.destination as string | undefined;
          const airline     = (d.airline     as string | undefined) ?? "";
          const flightNum   = (d.flight_number as string | undefined) ?? (d.flightNumber as string | undefined) ?? "";
          const depRaw      = (d.departure_time as string | undefined) ?? (d.departureTime as string | undefined) ?? item.startTime;
          const arrRaw      = (d.arrival_time  as string | undefined) ?? (d.arrivalTime  as string | undefined) ?? item.endTime;
          const dep         = formatClock(depRaw ?? undefined);
          const arr         = formatClock(arrRaw ?? undefined);
          const leg         = d.leg as string | undefined;
          if (!origin && !destination) return null;
          return (
            <div className="mt-0.5 text-[11px] text-slate-400 space-y-0.5">
              {(origin || destination) && (
                <span className="flex items-center gap-1 font-medium text-slate-200 min-w-0">
                  <Plane className="w-3 h-3 text-sky-300 flex-shrink-0" />
                  <span className="truncate" title={`${origin ?? "?"} → ${destination ?? "?"}`}>
                    {origin ?? "?"} → {destination ?? "?"}
                  </span>
                  {leg && <span className={`ml-1 text-[10px] px-1.5 py-0.5 rounded-full font-semibold ${leg === "outbound" ? "bg-sky-500/20 text-sky-200" : "bg-indigo-500/20 text-indigo-200"}`}>{leg}</span>}
                </span>
              )}
              {(airline || flightNum || dep) && (
                <span className="flex items-center gap-1 text-slate-400 min-w-0">
                  <span className="truncate" title={`${airline}${flightNum ? ` ${flightNum}` : ""}`}>
                    {airline}{flightNum ? ` ${flightNum}` : ""}
                  </span>
                  {dep && <>{" · "}{dep}{arr ? ` – ${arr}` : ""}</>}
                </span>
              )}
            </div>
          );
        })()}

        {/* Hotel stay span: check-in/out, rating, stars, area badges, amenities.
            Location is shown
            in the main location line below — don't duplicate it here. */}
        {item.itemType === "hotel" && (() => {
          const d = (item.details ?? {}) as Record<string, unknown>;
          // Backend stores check_in / check_out (ISO date strings).
          const checkIn  = (d.check_in  as string | undefined)
                        ?? (d.check_in_date  as string | undefined)
                        ?? (d.checkInDate  as string | undefined);
          const checkOut = (d.check_out as string | undefined)
                        ?? (d.check_out_date as string | undefined)
                        ?? (d.checkOutDate as string | undefined);
          const rating = (d.rating as number | undefined) ?? undefined;
          const stars = typeof d.stars === "number" ? (d.stars as number) : undefined;
          const areaLabel = (d.areaLabel as string | undefined) ?? (d.area_label as string | undefined);
          const proximityLabel = (d.proximityLabel as string | undefined) ?? (d.proximity_label as string | undefined);
          const amenities = Array.isArray(d.amenities) ? (d.amenities as string[]).slice(0, 3) : [];
          const tags = Array.isArray(d.tags) ? (d.tags as string[]).slice(0, 2) : [];
          const richTags = [...amenities, ...tags].slice(0, 3);
          const hasAny = !!(checkIn || checkOut || rating || stars || areaLabel || proximityLabel || richTags.length);
          if (!hasAny) return null;
          return (
            <div className="mt-0.5 space-y-0.5">
              <div className="flex items-center gap-1 text-[11px] text-violet-300 font-medium min-w-0 flex-wrap">
                <Hotel className="w-3 h-3 flex-shrink-0" />
                {stars != null && (
                  <span className="text-amber-400 flex-shrink-0">{"★".repeat(Math.min(5, Math.round(stars)))}</span>
                )}
                {checkIn || checkOut ? <span className="shrink-0">Stay: {checkIn ?? "?"} → {checkOut ?? "?"}</span> : null}
                {rating ? <span className="text-amber-300 font-semibold flex-shrink-0">{checkIn || checkOut ? " · " : ""}★ {rating.toFixed(1)}</span> : null}
              </div>
              {(areaLabel || proximityLabel) && (
                <div className="flex items-center gap-1 flex-wrap pl-4">
                  {areaLabel && (
                    <span className={`px-1.5 py-0 text-[10px] font-semibold rounded-full ${
                      areaLabel === "In Best Area" ? "bg-emerald-900/50 text-emerald-300 border border-emerald-800/40" :
                      areaLabel === "Close to Best Area" ? "bg-amber-900/50 text-amber-300 border border-amber-800/40" :
                      "bg-slate-800/60 text-slate-400 border border-slate-700/50"
                    }`}>{areaLabel}</span>
                  )}
                  {proximityLabel && proximityLabel.toLowerCase() !== (areaLabel ?? "").toLowerCase() && (
                    <span className="text-[10px] text-slate-500">{proximityLabel}</span>
                  )}
                </div>
              )}
              {richTags.length > 0 && (
                <div className="flex flex-wrap gap-1 pl-4">
                  {richTags.map((tag) => (
                    <span key={tag} className="px-1.5 py-0 text-[10px] rounded-full bg-violet-900/40 text-violet-300/70 border border-violet-800/50">{tag}</span>
                  ))}
                </div>
              )}
            </div>
          );
        })()}

        {/* Attraction (activity) vertical details: rating, category, tags, map link */}
        {item.itemType === "activity" && (() => {
          const d = (item.details ?? {}) as Record<string, unknown>;
          const rating = typeof d.rating === "number" ? (d.rating as number) : undefined;
          const numReviews = typeof d.numReviews === "number" ? (d.numReviews as number) : typeof d.num_reviews === "number" ? (d.num_reviews as number) : undefined;
          const category = (d.category as string | undefined) ?? "";
          const tags = Array.isArray(d.tags) ? (d.tags as string[]).slice(0, 3) : [];
          const mapsUri = (d.googleMapsUri as string | undefined) ?? (d.google_maps_uri as string | undefined);
          const placeId = (d.placeId as string | undefined) ?? (d.place_id as string | undefined);
          const mapsLink = mapsUri ?? (placeId ? `https://www.google.com/maps/place/?q=place_id:${encodeURIComponent(placeId)}` : null);
          if (!rating && !category && tags.length === 0) return null;
          return (
            <div className="mt-0.5 space-y-0.5">
              <div className="flex items-center gap-2 flex-wrap">
                {rating != null && (
                  <span className="flex items-center gap-0.5 text-[11px] text-amber-400 font-medium">
                    <Star className="w-3 h-3 fill-amber-400" />
                    {rating.toFixed(1)}
                    {numReviews != null && (
                      <span className="text-slate-500 font-normal ml-0.5">
                        ({numReviews >= 1000 ? `${(numReviews / 1000).toFixed(0)}k` : numReviews})
                      </span>
                    )}
                  </span>
                )}
                {category && <span className="text-[11px] text-emerald-300/80">{category}</span>}
                {mapsLink && (
                  <a
                    href={mapsLink}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-0.5 text-[11px] text-sky-400/70 hover:text-sky-300 transition-colors"
                    onClick={(e) => e.stopPropagation()}
                    aria-label="Open in Google Maps"
                  >
                    <ExternalLink className="w-2.5 h-2.5" />
                    Map
                  </a>
                )}
              </div>
              {tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {tags.map((tag) => (
                    <span key={tag} className="px-1.5 py-0 text-[10px] rounded-full bg-emerald-900/40 text-emerald-300/70 border border-emerald-800/50">{tag}</span>
                  ))}
                </div>
              )}
            </div>
          );
        })()}

        {/* Restaurant (meal) vertical details: cuisine, rating, price level, tags */}
        {item.itemType === "meal" && (() => {
          const d = (item.details ?? {}) as Record<string, unknown>;
          const rating = typeof d.rating === "number" ? (d.rating as number) : undefined;
          const numReviews = typeof d.numReviews === "number" ? (d.numReviews as number) : typeof d.num_reviews === "number" ? (d.num_reviews as number) : undefined;
          const cuisine = (d.cuisine as string | undefined) ?? "";
          const priceLevel = typeof d.priceLevel === "number" ? (d.priceLevel as number) : typeof d.price_level === "number" ? (d.price_level as number) : undefined;
          const tags = Array.isArray(d.tags) ? (d.tags as string[]).slice(0, 3) : [];
          const priceLevelStr = priceLevel != null ? "$".repeat(Math.min(4, Math.max(1, Math.round(priceLevel)))) : null;
          if (!rating && !cuisine && !priceLevelStr && tags.length === 0) return null;
          return (
            <div className="mt-0.5 space-y-0.5">
              <div className="flex items-center gap-2 flex-wrap">
                {cuisine && <span className="text-[11px] text-amber-300/80">{cuisine}</span>}
                {rating != null && (
                  <span className="flex items-center gap-0.5 text-[11px] text-amber-400 font-medium">
                    <Star className="w-3 h-3 fill-amber-400" />
                    {rating.toFixed(1)}
                    {numReviews != null && (
                      <span className="text-slate-500 font-normal ml-0.5">
                        ({numReviews >= 1000 ? `${(numReviews / 1000).toFixed(0)}k` : numReviews})
                      </span>
                    )}
                  </span>
                )}
                {priceLevelStr && <span className="text-[11px] text-slate-400 font-medium">{priceLevelStr}</span>}
              </div>
              {tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {tags.map((tag) => (
                    <span key={tag} className="px-1.5 py-0 text-[10px] rounded-full bg-amber-900/40 text-amber-300/70 border border-amber-800/50">{tag}</span>
                  ))}
                </div>
              )}
            </div>
          );
        })()}

        <div className="flex items-center gap-2 mt-1 flex-wrap">
          {item.itemType !== "flight" && (item.startTime || item.endTime) && (
            <span className="flex items-center gap-1 text-xs text-slate-400">
              <Clock className="w-3 h-3" />
              {item.startTime}
              {item.endTime && ` – ${item.endTime}`}
            </span>
          )}
          {/* Show user-set timeLabel when present and no startTime */}
          {!item.startTime && timeLabelValue && (
            <span className="flex items-center gap-1 text-[10px] text-slate-500">
              <Clock className="w-2.5 h-2.5" />
              {timeLabelValue}
            </span>
          )}
          {item.location && (
            <span className="flex items-center gap-1 text-xs text-slate-400 min-w-0">
              <MapPin className="w-3 h-3" />
              <span className="truncate" title={item.location}>{item.location}</span>
            </span>
          )}
          {item.cashPrice != null && item.cashPrice > 0 && (
            <span className={`flex items-center gap-0.5 text-xs font-medium ${
              item.bestOption === "cash" ? "text-emerald-700 font-semibold" : "text-emerald-600"
            }`}>
              <DollarSign className="w-3 h-3" />
              {item.cashPrice.toLocaleString()}{" "}
              {item.cashCurrency ?? "USD"}
            </span>
          )}
          {item.pointsPrice != null && (
            <span className={`flex items-center gap-0.5 text-xs font-medium ${
              item.bestOption === "points" ? "text-violet-700 font-semibold" : "text-violet-600"
            }`}>
              <Coins className="w-3 h-3" />
              {item.pointsPrice.toLocaleString()} pts
            </span>
          )}
          {item.bestOption && !item.rewardsIntelligence && (
            <span className={`badge text-[10px] px-1.5 py-0.5 gap-0.5 ${
              item.bestOption === "points" ? "badge-gold" : "badge-saved"
            }`}>
              <Zap className="w-2.5 h-2.5" />
              Best: {item.bestOption === "points" ? "Points" : "Cash"}
            </span>
          )}
        </div>

        {(item.itemType === "flight" || item.itemType === "hotel") &&
          item.rewardsIntelligence && (
            <RewardsIntelligencePanel rewards={item.rewardsIntelligence} />
          )}

        {/* Inline timeline editor */}
        {timelineOpen && (
          <div className="mt-2 pt-2 border-t border-slate-700/60">
            <div className="flex flex-wrap gap-1 mb-1.5">
              {DAY_PARTS.map((part) => (
                <button
                  key={part.value}
                  onClick={() => setSelectedPart(part.value)}
                  className={`px-2 py-0.5 rounded-full text-[10px] font-medium border transition-colors ${
                    selectedPart === part.value
                      ? part.activeClass
                      : "border-slate-700 text-slate-500 hover:border-slate-600 hover:text-slate-300"
                  }`}
                >
                  {part.label}
                </button>
              ))}
            </div>
            <div className="flex gap-1">
              <input
                type="text"
                value={timeLabelInput}
                onChange={(e) => setTimeLabelInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSaveTimeline();
                  if (e.key === "Escape") setTimelineOpen(false);
                }}
                placeholder="Time label, e.g. 9:00 AM (optional)"
                maxLength={40}
                className="flex-1 min-w-0 text-[10px] bg-slate-800 border border-slate-700 rounded px-1.5 py-1 text-slate-300 placeholder-slate-600 focus:outline-none focus:border-slate-500"
              />
              <button
                onClick={handleSaveTimeline}
                disabled={saving}
                className="flex-shrink-0 px-2 py-1 rounded text-[10px] font-medium bg-amber-500/20 text-amber-300 border border-amber-500/30 hover:bg-amber-500/30 transition-colors disabled:opacity-50"
              >
                {saving ? "…" : "Save"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>

      {bookingOpen && (
        <BookingChecklistModal item={item} onClose={() => setBookingOpen(false)} />
      )}
    </>
  );
}
