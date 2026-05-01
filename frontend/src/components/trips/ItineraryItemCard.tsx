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
} from "lucide-react";
import { ItineraryItem, ItemType } from "@/types";
import { BookingChecklistModal } from "./BookingChecklistModal";
import { RewardsIntelligencePanel } from "./RewardsIntelligencePanel";

interface ItineraryItemCardProps {
  item: ItineraryItem;
  onRemove: (itemId: string) => void;
  onMoveToIdeas?: (itemId: string) => void;
  onToggleCompare?: (item: ItineraryItem) => void;
  isComparing?: boolean;
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

export function ItineraryItemCard({ item, onRemove, onMoveToIdeas, onToggleCompare, isComparing }: ItineraryItemCardProps) {
  const [bookingOpen, setBookingOpen] = useState(false);

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
            {isConciergeIdea && onMoveToIdeas && (
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
        {isConciergeIdea && onMoveToIdeas && (
          <button
            onClick={() => onMoveToIdeas(item.id)}
            className="mt-1 rounded-md border border-amber-300/35 bg-amber-300/10 px-2 py-1 text-[11px] font-medium text-amber-200 hover:bg-amber-300/20 transition-colors"
            aria-label={`Move ${item.title} back to Trip Ideas`}
          >
            Move to Ideas
          </button>
        )}

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

        {/* Hotel stay span: show check-in/out dates when available */}
        {item.itemType === "hotel" && (() => {
          const d = (item.details ?? {}) as Record<string, unknown>;
          const checkIn  = (d.check_in_date  as string | undefined) ?? (d.checkInDate  as string | undefined);
          const checkOut = (d.check_out_date as string | undefined) ?? (d.checkOutDate as string | undefined);
          const rating = (d.rating as number | undefined) ?? undefined;
          const location = (d.location as string | undefined) ?? item.location ?? undefined;
          if (!checkIn && !checkOut && !rating && !location) return null;
          return (
            <div className="mt-0.5 flex items-center gap-1 text-[11px] text-violet-300 font-medium min-w-0">
              <Hotel className="w-3 h-3 flex-shrink-0" />
              {checkIn || checkOut ? <span className="shrink-0">Stay: {checkIn ?? "?"} → {checkOut ?? "?"}</span> : null}
              {location ? <span className="text-slate-400 font-normal truncate" title={location}>· {location}</span> : null}
              {rating ? <span className="text-amber-300 font-semibold">· ★ {rating.toFixed(1)}</span> : null}
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
          {item.location && (
            <span className="flex items-center gap-1 text-xs text-slate-400 min-w-0">
              <MapPin className="w-3 h-3" />
              <span className="truncate" title={item.location}>{item.location}</span>
            </span>
          )}
          {item.cashPrice != null && (
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
      </div>
    </div>

      {bookingOpen && (
        <BookingChecklistModal item={item} onClose={() => setBookingOpen(false)} />
      )}
    </>
  );
}
