"use client";

import { useDroppable } from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CalendarDays, Car, Footprints, Loader2, Plus, Sparkles } from "lucide-react";
import { ItineraryDay, ItineraryItem } from "@/types";
import { ItineraryItemCard } from "./ItineraryItemCard";
import { estimateTravel, formatTravelBadge } from "@/lib/travelTime";

interface ItineraryDayColumnProps {
  day: ItineraryDay;
  /** True when this day is the current target for left-panel "+" additions. */
  isSelected?: boolean;
  /** Called when the user clicks this day header to make it the target day. */
  onSelect?: (dayId: string) => void;
  onRemoveItem: (itemId: string, dayId: string) => void;
  onAddItem: (dayId: string) => void;
  onToggleCompare?: (item: ItineraryItem) => void;
  compareSet?: Set<string>;
  onPlanDay?: (dayId: string, dayNumber: number) => void;
  planDayLoading?: boolean;
}

function formatDate(dateStr: string): string {
  if (!dateStr) return "";
  const [year, month, day] = dateStr.split("-").map(Number);
  if (!year || !month || !day) return "";
  const d = new Date(Date.UTC(year, month - 1, day));
  if (isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

export function ItineraryDayColumn({
  day,
  isSelected,
  onSelect,
  onRemoveItem,
  onAddItem,
  onToggleCompare,
  compareSet,
  onPlanDay,
  planDayLoading,
}: ItineraryDayColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: `day-${day.id}`,
    data: { type: "day", dayId: day.id },
  });

  const itemIds = day.items.map((item: ItineraryItem) => item.id);

  return (
    <div className={`card overflow-hidden transition-all ${isSelected ? "ring-2 ring-sky-500 ring-offset-1" : ""}`}>
      {/* Day header — click to set as the target day for left-panel additions */}
      <div
        className={`shrink-0 flex items-center justify-between px-3 py-2 border-b border-slate-100 transition-colors cursor-pointer ${
          isSelected ? "bg-sky-50" : "bg-slate-50 hover:bg-slate-100"
        }`}
        onClick={() => onSelect?.(day.id)}
        title={isSelected ? "Currently adding to this day" : "Click to add items to this day"}
      >
        <div className="flex items-center gap-2 min-w-0">
          <div className={`w-6 h-6 rounded-md text-white flex items-center justify-center text-[11px] font-bold ${isSelected ? "bg-sky-600" : "bg-slate-400"}`}>
            {day.dayNumber}
          </div>
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-slate-800 truncate">{`Day ${day.dayNumber}`}</h3>
            {day.date && (
              <p className="text-[11px] text-slate-500 flex items-center gap-1">
                <CalendarDays className="w-3 h-3" />
                {formatDate(day.date)}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-[11px] text-slate-500 bg-white border border-slate-200 rounded-full px-2 py-0.5">
            {day.items.length} {day.items.length === 1 ? "item" : "items"}
          </span>
          {onPlanDay && (
            <button
              onClick={() => onPlanDay(day.id, day.dayNumber)}
              disabled={planDayLoading}
              title="Generate AI day plan"
              className="flex items-center gap-1 px-2 py-1 rounded-md bg-amber-50 hover:bg-amber-100 text-amber-700 text-[11px] font-medium transition-colors disabled:opacity-50"
            >
              {planDayLoading ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <Sparkles className="w-3 h-3" />
              )}
              Plan My Day
            </button>
          )}
          <button
            onClick={() => onAddItem(day.id)}
            className="w-6 h-6 rounded-md bg-slate-100 hover:bg-sky-50 hover:text-sky-600 text-slate-500 flex items-center justify-center transition-colors"
            aria-label={`Add item to Day ${day.dayNumber}`}
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Scrollable drop zone */}
      <div
        ref={setNodeRef}
        className={`p-2.5 min-h-[68px] max-h-[55vh] sm:max-h-[420px] overflow-y-auto overflow-x-hidden space-y-1.5 border-t border-slate-100 transition-colors duration-150 ${
          isOver ? "bg-sky-50/60" : "bg-white"
        }`}
      >
        <SortableContext
          items={itemIds}
          strategy={verticalListSortingStrategy}
        >
          {day.items.flatMap((item: ItineraryItem, idx: number) => {
            const card = (
              <ItineraryItemCard
                key={item.id}
                item={item}
                onRemove={(itemId) => onRemoveItem(itemId, day.id)}
                onToggleCompare={onToggleCompare}
                isComparing={compareSet?.has(item.id)}
              />
            );
            if (idx >= day.items.length - 1) return [card];
            const next = day.items[idx + 1];
            const d = item.details as Record<string, unknown> | undefined;
            const nd = next.details as Record<string, unknown> | undefined;
            const lat1 = d?.lat as number | null | undefined;
            const lng1 = d?.lng as number | null | undefined;
            const lat2 = nd?.lat as number | null | undefined;
            const lng2 = nd?.lng as number | null | undefined;
            if (lat1 == null || lng1 == null || lat2 == null || lng2 == null) return [card];
            const est = estimateTravel(lat1, lng1, lat2, lng2);
            const { label, mode } = formatTravelBadge(est);
            const connector = (
              <div key={`travel-${item.id}`} className="flex items-center gap-1.5 px-3 -my-0.5">
                <div className="w-px h-3 bg-slate-200 ml-[17px] flex-shrink-0" />
                {mode === "walk" ? (
                  <Footprints className="w-3 h-3 text-slate-300 flex-shrink-0" />
                ) : (
                  <Car className="w-3 h-3 text-slate-300 flex-shrink-0" />
                )}
                <span className="text-[10px] text-slate-300 leading-none">{label}</span>
                <span className="text-[10px] text-slate-200 leading-none">· {est.distanceKm} km</span>
              </div>
            );
            return [card, connector];
          })}
        </SortableContext>

        {day.items.length === 0 ? (
          <div
            className={`flex-1 flex flex-col items-center justify-center border border-dashed rounded-lg py-2.5 px-2 gap-0.5 transition-colors duration-150 ${
              isOver
                ? "border-sky-400 bg-sky-50 text-sky-500"
                : "border-slate-200 text-slate-300"
            }`}
          >
            <p className="text-[11px] text-center">
              {isOver ? "Drop here" : "No plans yet for Day " + day.dayNumber}
            </p>
            {!isOver && (
              <p className="text-[10px] text-center text-slate-300">
                Drag items here or use +
              </p>
            )}
          </div>
        ) : isOver && (
          <div className="border-2 border-dashed border-sky-400 rounded-xl py-2 flex items-center justify-center transition-colors duration-150 bg-sky-50">
            <p className="text-xs text-sky-500 font-medium">Drop here</p>
          </div>
        )}
      </div>
    </div>
  );
}
