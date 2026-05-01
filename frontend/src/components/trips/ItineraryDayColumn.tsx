"use client";

import { useEffect, useMemo, useState } from "react";
import { useDroppable } from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CalendarDays, Car, ChevronDown, ChevronUp, Clock, Footprints, Loader2, Plus, Sparkles } from "lucide-react";
import { ItineraryDay, ItineraryItem } from "@/types";
import { ItineraryItemCard } from "./ItineraryItemCard";
import { estimateTravel, formatTravelBadge } from "@/lib/travelTime";

// ─── Timeline helpers ────────────────────────────────────────────────────────

type DayPart = "morning" | "afternoon" | "evening" | "unscheduled";

const DAY_PART_META: Record<DayPart, { label: string; timeHint: string; colorClass: string }> = {
  morning:     { label: "Morning",     timeHint: "5 AM – 12 PM",  colorClass: "text-amber-300" },
  afternoon:   { label: "Afternoon",   timeHint: "12 PM – 5 PM",  colorClass: "text-sky-300" },
  evening:     { label: "Evening",     timeHint: "5 PM – 10 PM",  colorClass: "text-violet-300" },
  unscheduled: { label: "Unscheduled", timeHint: "no time set",   colorClass: "text-slate-400" },
};

function getItemDayPart(item: ItineraryItem): DayPart {
  const d = (item.details ?? {}) as Record<string, unknown>;

  // Explicit override stored in details.dayPart
  const explicit = d.dayPart as string | undefined;
  if (explicit === "morning" || explicit === "afternoon" || explicit === "evening") return explicit;

  // Keyword in details.timeLabel
  const label = ((d.timeLabel as string | undefined) ?? "").toLowerCase();
  if (label.includes("morning")) return "morning";
  if (label.includes("afternoon")) return "afternoon";
  if (label.includes("evening") || label.includes("night")) return "evening";

  // Parse startTime (ISO datetime or HH:MM)
  const raw = item.startTime;
  if (raw) {
    const isoMatch = raw.match(/T(\d{2}):/);
    const hour = isoMatch
      ? Number(isoMatch[1])
      : (() => {
          const hhMM = raw.match(/^(\d{1,2}):\d{2}/);
          if (hhMM) return Number(hhMM[1]);
          const parsed = new Date(raw);
          return isNaN(parsed.getTime()) ? null : parsed.getHours();
        })();
    if (hour !== null) {
      if (hour >= 5 && hour < 12) return "morning";
      if (hour >= 12 && hour < 17) return "afternoon";
      if (hour >= 17) return "evening";
    }
  }

  return "unscheduled";
}

interface GroupedItems {
  morning: ItineraryItem[];
  afternoon: ItineraryItem[];
  evening: ItineraryItem[];
  unscheduled: ItineraryItem[];
}

function groupByDayPart(items: ItineraryItem[]): GroupedItems {
  const result: GroupedItems = { morning: [], afternoon: [], evening: [], unscheduled: [] };
  for (const item of items) {
    result[getItemDayPart(item)].push(item);
  }
  return result;
}

const PREVIEW_ITEM_LIMIT = 4;

// ─── TimelineSections ────────────────────────────────────────────────────────

interface TimelineSectionsProps {
  items: ItineraryItem[];
  dayId: string;
  onRemoveItem: (itemId: string, dayId: string) => void;
  onMoveItemToIdeas?: (itemId: string, dayId: string) => void;
  onToggleCompare?: (item: ItineraryItem) => void;
  compareSet?: Set<string>;
}

function renderItemsWithConnectors(
  items: ItineraryItem[],
  dayId: string,
  onRemoveItem: (itemId: string, dayId: string) => void,
  onMoveItemToIdeas?: (itemId: string, dayId: string) => void,
  onToggleCompare?: (item: ItineraryItem) => void,
  compareSet?: Set<string>,
) {
  return items.flatMap((item, idx) => {
    const card = (
      <ItineraryItemCard
        key={item.id}
        item={item}
        onRemove={(itemId) => onRemoveItem(itemId, dayId)}
        onMoveToIdeas={onMoveItemToIdeas ? (itemId) => onMoveItemToIdeas(itemId, dayId) : undefined}
        onToggleCompare={onToggleCompare}
        isComparing={compareSet?.has(item.id)}
      />
    );
    if (idx >= items.length - 1) return [card];
    const next = items[idx + 1];
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
        <div className="w-px h-3 bg-slate-700 ml-[17px] flex-shrink-0" />
        {mode === "walk" ? (
          <Footprints className="w-3 h-3 text-slate-500 flex-shrink-0" />
        ) : (
          <Car className="w-3 h-3 text-slate-500 flex-shrink-0" />
        )}
        <span className="text-[10px] text-slate-500 leading-none">{label}</span>
        <span className="text-[10px] text-slate-600 leading-none">· {est.distanceKm} km</span>
      </div>
    );
    return [card, connector];
  });
}

function TimelineSections({
  items,
  dayId,
  onRemoveItem,
  onMoveItemToIdeas,
  onToggleCompare,
  compareSet,
}: TimelineSectionsProps) {
  const grouped = groupByDayPart(items);
  const hasTimedItems =
    grouped.morning.length > 0 ||
    grouped.afternoon.length > 0 ||
    grouped.evening.length > 0;

  const orderedSections: DayPart[] = ["morning", "afternoon", "evening", "unscheduled"];

  // When nothing is timed, render plain list with a single "Unscheduled" label
  if (!hasTimedItems) {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-1.5 px-1 pt-1 pb-0.5">
          <Clock className="w-3 h-3 text-slate-500 flex-shrink-0" />
          <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wide">
            Unscheduled · {items.length} {items.length === 1 ? "item" : "items"}
          </span>
        </div>
        <div className="space-y-2">
          {renderItemsWithConnectors(items, dayId, onRemoveItem, onMoveItemToIdeas, onToggleCompare, compareSet)}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {orderedSections.map((part) => {
        const sectionItems = grouped[part];
        if (sectionItems.length === 0) return null;
        const meta = DAY_PART_META[part];
        return (
          <div key={part} className="space-y-1.5">
            <div className="flex items-center gap-1.5 px-1 pt-0.5">
              <Clock className={`w-3 h-3 flex-shrink-0 ${meta.colorClass}`} />
              <span className={`text-[10px] font-semibold uppercase tracking-wide ${meta.colorClass}`}>
                {meta.label}
              </span>
              <span className="text-[10px] text-slate-600">{meta.timeHint}</span>
            </div>
            <div className="space-y-2">
              {renderItemsWithConnectors(sectionItems, dayId, onRemoveItem, onMoveItemToIdeas, onToggleCompare, compareSet)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

interface ItineraryDayColumnProps {
  day: ItineraryDay;
  /** True when this day is the current target for left-panel "+" additions. */
  isSelected?: boolean;
  /** Called when the user clicks this day header to make it the target day. */
  onSelect?: (dayId: string) => void;
  isExpanded?: boolean;
  onToggleExpanded?: (dayNumber: number) => void;
  onRemoveItem: (itemId: string, dayId: string) => void;
  onMoveItemToIdeas?: (itemId: string, dayId: string) => void;
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
  isExpanded = false,
  onToggleExpanded,
  onRemoveItem,
  onMoveItemToIdeas,
  onAddItem,
  onToggleCompare,
  compareSet,
  onPlanDay,
  planDayLoading,
}: ItineraryDayColumnProps) {
  const [expandedItemDays, setExpandedItemDays] = useState<Record<number, boolean>>({});

  useEffect(() => {
    if (!isExpanded) {
      setExpandedItemDays((prev) => ({
        ...prev,
        [day.dayNumber]: false,
      }));
    }
  }, [day.dayNumber, isExpanded]);

  const { setNodeRef, isOver } = useDroppable({
    id: `day-${day.id}`,
    data: { type: "day", dayId: day.id },
  });

  const showAllItems = expandedItemDays[day.dayNumber] ?? false;
  const hasHiddenItems = day.items.length > PREVIEW_ITEM_LIMIT;
  const visibleItems = useMemo(
    () => (showAllItems ? day.items : day.items.slice(0, PREVIEW_ITEM_LIMIT)),
    [day.items, showAllItems]
  );
  const itemIds = visibleItems.map((item: ItineraryItem) => item.id);
  const hiddenItemsCount = Math.max(day.items.length - 1, 0);
  const firstItem = day.items[0];
  const itemTypeCounts = day.items.reduce<Record<string, number>>((acc, item) => {
    acc[item.itemType] = (acc[item.itemType] ?? 0) + 1;
    return acc;
  }, {});
  const itemSummary = Object.entries(itemTypeCounts)
    .map(([type, count]) => `${count} ${type}${count > 1 ? "s" : ""}`)
    .join(" · ");

  return (
    <div className={`overflow-hidden rounded-2xl border border-slate-800/90 bg-gradient-to-b from-slate-900 to-slate-950 shadow-[0_16px_40px_rgba(2,6,23,0.45)] transition-all ${isSelected ? "ring-2 ring-amber-400/55 ring-offset-1 ring-offset-slate-950 shadow-[0_0_0_1px_rgba(251,191,36,0.22),0_18px_38px_rgba(2,6,23,0.5)]" : ""}`}>
      {/* Day header — click to set as the target day for left-panel additions */}
      <div
        className={`shrink-0 flex items-center justify-between px-3 py-2 border-b border-slate-800 transition-colors cursor-pointer ${
          isSelected ? "bg-slate-800/90" : "bg-slate-900/80 hover:bg-slate-800/80"
        }`}
        onClick={() => {
          onSelect?.(day.id);
          onToggleExpanded?.(day.dayNumber);
        }}
        title={isSelected ? "Currently adding to this day" : "Click to add items to this day"}
      >
        <div className="flex items-center gap-2 min-w-0">
          <div className={`w-6 h-6 rounded-md text-white flex items-center justify-center text-[11px] font-bold ${isSelected ? "bg-amber-500" : "bg-slate-700"}`}>
            {day.dayNumber}
          </div>
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-slate-100 truncate">{`Day ${day.dayNumber}`}</h3>
            {day.date && (
              <p className="text-[11px] text-slate-400 flex items-center gap-1">
                <CalendarDays className="w-3 h-3" />
                {formatDate(day.date)}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-[11px] text-slate-300 bg-slate-800/80 border border-slate-700 rounded-full px-2 py-0.5">
            {day.items.length} {day.items.length === 1 ? "item" : "items"}
          </span>
          {onPlanDay && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onPlanDay(day.id, day.dayNumber);
              }}
              disabled={planDayLoading}
              title="Generate AI day plan"
              className="flex items-center gap-1 px-2 py-1 rounded-md bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 border border-amber-500/35 text-[11px] font-medium transition-colors disabled:opacity-50"
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
            onClick={(e) => {
              e.stopPropagation();
              onSelect?.(day.id);
              onAddItem(day.id);
            }}
            className="w-6 h-6 rounded-md bg-slate-800 hover:bg-amber-500/20 hover:text-amber-300 text-slate-300 border border-slate-700 flex items-center justify-center transition-colors"
            aria-label={`Add item to Day ${day.dayNumber}`}
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggleExpanded?.(day.dayNumber);
            }}
            className="w-6 h-6 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 flex items-center justify-center transition-colors"
            aria-label={`${isExpanded ? "Collapse" : "Expand"} Day ${day.dayNumber}`}
          >
            {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {!isExpanded ? (
        <div
          ref={setNodeRef}
          className={`p-2.5 border-t border-slate-800 transition-colors duration-150 ${
            isOver ? "bg-amber-500/10" : "bg-slate-950/70"
          }`}
        >
          {day.items.length === 0 ? (
            <p className="text-xs text-slate-500">No items yet.</p>
          ) : (
            <div className="space-y-1">
              <p className="text-xs text-slate-200 truncate">{firstItem?.title ?? "Itinerary item"}</p>
              <p className="text-[11px] text-slate-500">
                {hiddenItemsCount > 0 ? `+${hiddenItemsCount} more item${hiddenItemsCount > 1 ? "s" : ""}` : "1 item"}
                {itemSummary ? ` · ${itemSummary}` : ""}
              </p>
            </div>
          )}
        </div>
      ) : (
      <div
        ref={setNodeRef}
        className={`p-3 min-h-[68px] h-auto overflow-hidden space-y-1.5 border-t border-slate-800 transition-colors duration-150 ${
          isOver ? "bg-amber-500/10" : "bg-slate-950/70"
        }`}
      >
        <SortableContext
          items={itemIds}
          strategy={verticalListSortingStrategy}
        >
          <div className={`relative rounded-xl p-1 ${isSelected ? "bg-slate-900/55 ring-1 ring-amber-300/20" : "bg-transparent"}`}>
            <TimelineSections
              items={visibleItems}
              dayId={day.id}
              onRemoveItem={onRemoveItem}
              onMoveItemToIdeas={onMoveItemToIdeas}
              onToggleCompare={onToggleCompare}
              compareSet={compareSet}
            />
            {!showAllItems && hasHiddenItems && (
              <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-14 bg-gradient-to-b from-transparent to-slate-950/95" />
            )}
          </div>
        </SortableContext>

        {day.items.length === 0 ? (
          <div
            className={`flex-1 flex flex-col items-center justify-center border border-dashed rounded-lg py-2.5 px-2 gap-0.5 transition-colors duration-150 ${
              isOver
                ? "border-amber-400/70 bg-amber-500/10 text-amber-300"
                : "border-slate-700 text-slate-500"
            }`}
          >
            <p className="text-[11px] text-center">
              {isOver ? "Drop here" : "No plans yet for Day " + day.dayNumber}
            </p>
            {!isOver && (
              <p className="text-[10px] text-center text-slate-500">
                Drag items here or use +
              </p>
            )}
          </div>
        ) : isOver && (
          <div className="border-2 border-dashed border-amber-400/70 rounded-xl py-2 flex items-center justify-center transition-colors duration-150 bg-amber-500/10">
            <p className="text-xs text-amber-300 font-medium">Drop here</p>
          </div>
        )}

        {hasHiddenItems && (
          <div className="mt-3 flex justify-center border-t border-slate-800 pt-3">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setExpandedItemDays((prev) => ({
                  ...prev,
                  [day.dayNumber]: !showAllItems,
                }));
              }}
              className="rounded-full border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-medium text-slate-300 shadow-sm hover:bg-slate-800"
            >
              {showAllItems ? "Show less ↑" : `Show all ${day.items.length} items ↓`}
            </button>
          </div>
        )}
      </div>
      )}
    </div>
  );
}
