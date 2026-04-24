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
  onToggleCompare?: (item: ItineraryItem) => void;
  isComparing?: boolean;
}

const typeConfig: Record<
  ItemType,
  { icon: React.ReactNode; colorClass: string; bgClass: string; borderClass: string }
> = {
  flight: {
    icon: <Plane className="w-3.5 h-3.5" />,
    colorClass: "text-sky-600",
    bgClass: "bg-sky-50",
    borderClass: "border-sky-200",
  },
  hotel: {
    icon: <Hotel className="w-3.5 h-3.5" />,
    colorClass: "text-violet-600",
    bgClass: "bg-violet-50",
    borderClass: "border-violet-200",
  },
  activity: {
    icon: <MapPin className="w-3.5 h-3.5" />,
    colorClass: "text-emerald-600",
    bgClass: "bg-emerald-50",
    borderClass: "border-emerald-200",
  },
  meal: {
    icon: <Utensils className="w-3.5 h-3.5" />,
    colorClass: "text-amber-600",
    bgClass: "bg-amber-50",
    borderClass: "border-amber-200",
  },
  transit: {
    icon: <Train className="w-3.5 h-3.5" />,
    colorClass: "text-slate-600",
    bgClass: "bg-slate-100",
    borderClass: "border-slate-200",
  },
  note: {
    icon: <FileText className="w-3.5 h-3.5" />,
    colorClass: "text-rose-600",
    bgClass: "bg-rose-50",
    borderClass: "border-rose-200",
  },
};

export function ItineraryItemCard({ item, onRemove, onToggleCompare, isComparing }: ItineraryItemCardProps) {
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

  return (
    <>
    <div
      ref={setNodeRef}
      style={style}
      className={`group relative flex items-start gap-2 p-2.5 rounded-xl border transition-all duration-200 ${
        isDragging
          ? "opacity-50 shadow-xl scale-95 border-sky-300 bg-white/60 backdrop-blur-md"
          : "bg-white/60 backdrop-blur-[16px] border-white/40 shadow-[0_4px_16px_0_rgb(0_0_0/0.08)] hover:bg-white/75 hover:border-white/60 hover:shadow-[0_12px_36px_0_rgb(0_0_0/0.12)] hover:-translate-y-1"
      }`}
    >
      {/* Drag handle */}
      <button
        {...listeners}
        {...attributes}
        className="mt-0.5 flex-shrink-0 cursor-grab active:cursor-grabbing text-slate-200 group-hover:text-slate-400 transition-colors"
        aria-label="Drag to reorder"
      >
        <GripVertical className="w-4 h-4" />
      </button>

      {/* Type icon */}
      <div
        className={`flex-shrink-0 w-6 h-6 rounded-md flex items-center justify-center ${config.bgClass} ${config.colorClass}`}
      >
        {config.icon}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-1">
          <span className="text-sm font-medium text-slate-800 leading-tight line-clamp-1">
            {item.title}
          </span>
          <div className="flex items-center gap-1 flex-shrink-0">
            {onToggleCompare && (
              <button
                onClick={() => onToggleCompare(item)}
                className={`w-5 h-5 rounded-full flex items-center justify-center transition-all ${
                  isComparing
                    ? "opacity-100 bg-violet-600 text-white"
                    : "opacity-0 group-hover:opacity-100 bg-slate-100 hover:bg-violet-100 text-slate-400 hover:text-violet-600"
                }`}
                aria-label={isComparing ? `Remove ${item.title} from compare` : `Add ${item.title} to compare`}
              >
                <Scale className="w-3 h-3" />
              </button>
            )}
            <button
              onClick={() => setBookingOpen(true)}
              className="flex-shrink-0 w-5 h-5 rounded-full opacity-0 group-hover:opacity-100 bg-emerald-50 hover:bg-emerald-100 text-emerald-600 flex items-center justify-center transition-all"
              aria-label={`Book ${item.title}`}
            >
              <Ticket className="w-3 h-3" />
            </button>
            <button
              onClick={() => onRemove(item.id)}
              className="flex-shrink-0 w-5 h-5 rounded-full opacity-0 group-hover:opacity-100 bg-slate-100 hover:bg-rose-100 text-slate-400 hover:text-rose-500 flex items-center justify-center transition-all"
              aria-label={`Remove ${item.title}`}
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        </div>

        {item.description && (
          <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">
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
          const dep         = (d.departure_time as string | undefined) ?? (d.departureTime as string | undefined) ?? item.startTime;
          const arr         = (d.arrival_time  as string | undefined) ?? (d.arrivalTime  as string | undefined) ?? item.endTime;
          const leg         = d.leg as string | undefined;
          if (!origin && !destination) return null;
          return (
            <div className="mt-1 text-xs text-slate-500 space-y-0.5">
              {(origin || destination) && (
                <span className="flex items-center gap-1 font-medium text-slate-700">
                  <Plane className="w-3 h-3 text-sky-500 flex-shrink-0" />
                  {origin ?? "?"} → {destination ?? "?"}
                  {leg && <span className={`ml-1 text-[10px] px-1.5 py-0.5 rounded-full font-semibold ${leg === "outbound" ? "bg-sky-100 text-sky-700" : "bg-indigo-100 text-indigo-700"}`}>{leg}</span>}
                </span>
              )}
              {(airline || flightNum || dep) && (
                <span className="flex items-center gap-1 text-slate-400">
                  {airline}{flightNum ? ` ${flightNum}` : ""}
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
          if (!checkIn && !checkOut) return null;
          return (
            <div className="mt-1 flex items-center gap-1 text-xs text-violet-600 font-medium">
              <Hotel className="w-3 h-3 flex-shrink-0" />
              Stay: {checkIn ?? "?"} → {checkOut ?? "?"}
            </div>
          );
        })()}

        <div className="flex items-center gap-3 mt-1 flex-wrap">
          {item.itemType !== "flight" && (item.startTime || item.endTime) && (
            <span className="flex items-center gap-1 text-xs text-slate-400">
              <Clock className="w-3 h-3" />
              {item.startTime}
              {item.endTime && ` – ${item.endTime}`}
            </span>
          )}
          {item.location && (
            <span className="flex items-center gap-1 text-xs text-slate-400">
              <MapPin className="w-3 h-3" />
              {item.location}
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
