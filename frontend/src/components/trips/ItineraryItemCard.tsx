"use client";

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
} from "lucide-react";
import { ItineraryItem, ItemType } from "@/types";

interface ItineraryItemCardProps {
  item: ItineraryItem;
  onRemove: (itemId: string) => void;
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

export function ItineraryItemCard({ item, onRemove }: ItineraryItemCardProps) {
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
    <div
      ref={setNodeRef}
      style={style}
      className={`group relative flex items-start gap-2 p-2.5 rounded-xl border bg-white transition-all ${
        isDragging
          ? "opacity-50 shadow-xl scale-95 border-sky-300"
          : `border-slate-200 hover:border-slate-300 hover:shadow-sm`
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
          <button
            onClick={() => onRemove(item.id)}
            className="flex-shrink-0 w-5 h-5 rounded-full opacity-0 group-hover:opacity-100 bg-slate-100 hover:bg-rose-100 text-slate-400 hover:text-rose-500 flex items-center justify-center transition-all"
            aria-label={`Remove ${item.title}`}
          >
            <X className="w-3 h-3" />
          </button>
        </div>

        {item.description && (
          <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">
            {item.description}
          </p>
        )}

        <div className="flex items-center gap-3 mt-1 flex-wrap">
          {(item.startTime || item.endTime) && (
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
          {item.cashPrice !== undefined && (
            <span className="flex items-center gap-0.5 text-xs font-medium text-emerald-600">
              <DollarSign className="w-3 h-3" />
              {item.cashPrice.toLocaleString()}{" "}
              {item.cashCurrency ?? "USD"}
            </span>
          )}
          {item.pointsPrice !== undefined && (
            <span className="flex items-center gap-0.5 text-xs font-medium text-violet-600">
              <Coins className="w-3 h-3" />
              {item.pointsPrice.toLocaleString()} pts
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
