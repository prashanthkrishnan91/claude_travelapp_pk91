"use client";

import { useDroppable } from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CalendarDays, Loader2, Plus, Sparkles } from "lucide-react";
import { ItineraryDay, ItineraryItem } from "@/types";
import { ItineraryItemCard } from "./ItineraryItemCard";

interface ItineraryDayColumnProps {
  day: ItineraryDay;
  onRemoveItem: (itemId: string, dayId: string) => void;
  onAddItem: (dayId: string) => void;
  onToggleCompare?: (item: ItineraryItem) => void;
  compareSet?: Set<string>;
  onPlanDay?: (dayId: string, dayNumber: number) => void;
  planDayLoading?: boolean;
}

function formatDate(dateStr: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export function ItineraryDayColumn({
  day,
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
    <div className="card overflow-hidden">
      {/* Day header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-sky-600 text-white flex items-center justify-center text-xs font-bold">
            {day.dayNumber}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-800">
              {day.title ?? `Day ${day.dayNumber}`}
            </h3>
            {day.date && (
              <p className="text-xs text-slate-400 flex items-center gap-1">
                <CalendarDays className="w-3 h-3" />
                {formatDate(day.date)}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">
            {day.items.length} {day.items.length === 1 ? "item" : "items"}
          </span>
          {onPlanDay && (
            <button
              onClick={() => onPlanDay(day.id, day.dayNumber)}
              disabled={planDayLoading}
              title="Generate AI day plan"
              className="flex items-center gap-1 px-2 py-1 rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-600 text-xs font-medium transition-colors disabled:opacity-50"
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
            className="w-6 h-6 rounded-full bg-slate-100 hover:bg-sky-50 hover:text-sky-600 text-slate-400 flex items-center justify-center transition-colors"
            aria-label={`Add item to Day ${day.dayNumber}`}
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Drop zone */}
      <div
        ref={setNodeRef}
        className={`p-3 min-h-[80px] flex flex-col gap-2 transition-colors duration-150 ${
          isOver ? "bg-sky-50/60" : "bg-white"
        }`}
      >
        <SortableContext
          items={itemIds}
          strategy={verticalListSortingStrategy}
        >
          {day.items.map((item: ItineraryItem) => (
            <ItineraryItemCard
              key={item.id}
              item={item}
              onRemove={(itemId) => onRemoveItem(itemId, day.id)}
              onToggleCompare={onToggleCompare}
              isComparing={compareSet?.has(item.id)}
            />
          ))}
        </SortableContext>

        {day.items.length === 0 ? (
          <div
            className={`flex-1 flex items-center justify-center border-2 border-dashed rounded-xl py-4 transition-colors duration-150 ${
              isOver
                ? "border-sky-400 bg-sky-50 text-sky-500"
                : "border-slate-200 text-slate-300"
            }`}
          >
            <p className="text-xs text-center">
              {isOver ? "Drop here" : "Drag items here"}
            </p>
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
