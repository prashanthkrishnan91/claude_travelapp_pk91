"use client";

import { useEffect, useMemo, useState } from "react";
import { useDroppable } from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CalendarDays, Car, Check, ChevronDown, ChevronUp, Clock, Footprints, Info, Loader2, MapPin, MoreHorizontal, Plus, Sparkles, X } from "lucide-react";
import { ItineraryDay, ItineraryItem } from "@/types";
import { FolioCard } from "@/components/ui/Folio";
import { ItineraryItemCard } from "./ItineraryItemCard";
import { computeAdjacentHints, summarizeHints } from "@/lib/travelHints";
import { suggestDayTimeline, updateItemTimeline, type TimelineSuggestion } from "@/lib/api";

// ─── Timeline helpers ────────────────────────────────────────────────────────

type DayPart = "morning" | "afternoon" | "evening" | "unscheduled";

const DAY_PART_META: Record<DayPart, { label: string; timeHint: string; colorClass: string }> = {
  morning:     { label: "Morning",     timeHint: "12 AM – 12 PM", colorClass: "text-ds-marine-ink" },
  afternoon:   { label: "Afternoon",   timeHint: "12 PM – 5 PM",  colorClass: "text-ds-folio-ink-soft" },
  evening:     { label: "Evening",     timeHint: "5 PM – 10 PM",  colorClass: "text-ds-marine-soft" },
  unscheduled: { label: "Unscheduled", timeHint: "no time set",   colorClass: "text-ds-folio-ink-mist" },
};

function getItemDayPart(item: ItineraryItem): DayPart {
  const d = (item.details ?? {}) as Record<string, unknown>;

  // Explicit override stored in details.dayPart
  const explicit = d.dayPart as string | undefined;
  if (explicit === "morning" || explicit === "afternoon" || explicit === "evening") return explicit;
  // Explicit unscheduled override — bypasses time classification by contract
  if (explicit === "unscheduled") return "unscheduled";

  // Keyword in details.timeLabel
  const label = ((d.timeLabel as string | undefined) ?? "").toLowerCase();
  if (label.includes("morning")) return "morning";
  if (label.includes("afternoon")) return "afternoon";
  if (label.includes("evening") || label.includes("night")) return "evening";

  const parseHour = (raw: unknown): number | null => {
    if (typeof raw !== "string" || raw.trim().length === 0) return null;
    const input = raw.trim();

    const isoMatch = input.match(/T(\d{2}):/);
    if (isoMatch) return Number(isoMatch[1]);

    const hhMM = input.match(/^(\d{1,2}):\d{2}/);
    if (hhMM) return Number(hhMM[1]);

    const parsed = new Date(input);
    return isNaN(parsed.getTime()) ? null : parsed.getHours();
  };

  // Prefer canonical startTime, then known persisted flight departure keys.
  const flightDetails = item.itemType === "flight" ? (d as Record<string, unknown>) : null;
  const hour =
    parseHour(item.startTime) ??
    parseHour(flightDetails?.departureTime) ??
    parseHour(flightDetails?.departure_time) ??
    parseHour(flightDetails?.departureDateTime) ??
    parseHour(flightDetails?.departure_datetime) ??
    parseHour((flightDetails?.outboundLeg as Record<string, unknown> | undefined)?.departureTime) ??
    parseHour((flightDetails?.outbound_leg as Record<string, unknown> | undefined)?.departure_time) ??
    parseHour((flightDetails?.outboundLeg as Record<string, unknown> | undefined)?.departureDateTime) ??
    parseHour((flightDetails?.outbound_leg as Record<string, unknown> | undefined)?.departure_datetime);

  const normalizedHour =
    typeof hour === "number" && Number.isFinite(hour) && hour >= 0 && hour <= 23
      ? hour
      : null;

  if (normalizedHour !== null) {
    if (normalizedHour >= 0 && normalizedHour < 12) return "morning";
    if (normalizedHour >= 12 && normalizedHour < 17) return "afternoon";
    if (normalizedHour >= 17) return "evening";
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
  onMoveItemToIdeas?: (itemId: string, currentDetails: Record<string, unknown>) => void;
  onToggleCompare?: (item: ItineraryItem) => void;
  compareSet?: Set<string>;
  onUpdateTimeline?: (updatedItem: ItineraryItem) => void;
}

function renderItemsWithConnectors(
  items: ItineraryItem[],
  dayId: string,
  onRemoveItem: (itemId: string, dayId: string) => void,
  onMoveItemToIdeas?: (itemId: string, currentDetails: Record<string, unknown>) => void,
  onToggleCompare?: (item: ItineraryItem) => void,
  compareSet?: Set<string>,
  onUpdateTimeline?: (updatedItem: ItineraryItem) => void,
) {
  const hints = computeAdjacentHints(items);
  return items.flatMap((item, idx) => {
    const card = (
      <ItineraryItemCard
        key={item.id}
        item={item}
        onRemove={(itemId) => onRemoveItem(itemId, dayId)}
        onUnplace={onMoveItemToIdeas}
        onToggleCompare={onToggleCompare}
        isComparing={compareSet?.has(item.id)}
        onTimelineUpdated={onUpdateTimeline}
      />
    );
    if (idx >= items.length - 1) return [card];
    const hint = hints[idx];
    let connector: React.ReactNode;
    if (hint.kind === "missing_location") {
      connector = (
        <div key={`hint-${item.id}`} className="flex items-center gap-1.5 px-3 py-1">
          <div className="w-px h-4 bg-ds-hairline ml-[17px] flex-shrink-0" />
          <MapPin className="w-3 h-3 text-ds-folio-ink-mist flex-shrink-0" />
          <span className="text-[10px] text-ds-folio-ink-mist leading-snug italic">{hint.label}</span>
        </div>
      );
    } else if (hint.kind === "far_apart") {
      const est = hint.estimate!;
      const mode = est.walkMinutes <= 20 ? "walk" : "drive";
      const timeLabel = mode === "walk" ? `~${est.walkMinutes} min walk` : `~${est.driveMinutes} min drive`;
      connector = (
        <div key={`travel-${item.id}`} className="flex flex-col gap-1 px-3 py-1">
          <div className="flex items-center gap-1.5">
            <div className="w-px h-4 bg-ds-hairline ml-[17px] flex-shrink-0" />
            {mode === "walk" ? (
              <Footprints className="w-3 h-3 text-ds-folio-ink-mist flex-shrink-0" />
            ) : (
              <Car className="w-3 h-3 text-ds-folio-ink-mist flex-shrink-0" />
            )}
            <span className="text-[10px] text-ds-folio-ink-mist leading-snug">{timeLabel}</span>
            <span className="text-[10px] text-ds-folio-ink-mist/60 leading-snug">· {est.distanceKm} km</span>
          </div>
          <div className="flex items-center gap-1 pl-[29px] pr-1">
            <span className="text-[10px] text-ds-warning/70 leading-snug">{hint.label}</span>
          </div>
        </div>
      );
    } else {
      const est = hint.estimate!;
      const mode = est.walkMinutes <= 20 ? "walk" : "drive";
      connector = (
        <div key={`travel-${item.id}`} className="flex items-center gap-1.5 px-3 py-1">
          <div className="w-px h-4 bg-ds-hairline ml-[17px] flex-shrink-0" />
          {mode === "walk" ? (
            <Footprints className="w-3 h-3 text-ds-folio-ink-mist flex-shrink-0" />
          ) : (
            <Car className="w-3 h-3 text-ds-folio-ink-mist flex-shrink-0" />
          )}
          <span className="text-[10px] text-ds-folio-ink-mist leading-snug">{hint.label}</span>
          <span className="text-[10px] text-ds-folio-ink-mist/60 leading-snug">· {est.distanceKm} km</span>
        </div>
      );
    }
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
  onUpdateTimeline,
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
      <div className="space-y-2" data-testid="day-part-section">
        <div className="flex items-center gap-1.5 px-1 pt-1 pb-0.5">
          <Clock className="w-3 h-3 text-ds-folio-ink-mist flex-shrink-0" />
          <span className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-folio-ink-mist" data-testid="day-part-label">
            Unscheduled · {items.length} {items.length === 1 ? "item" : "items"}
          </span>
        </div>
        <div className="space-y-2">
          {renderItemsWithConnectors(items, dayId, onRemoveItem, onMoveItemToIdeas, onToggleCompare, compareSet, onUpdateTimeline)}
        </div>
      </div>
    );
  }

  // Collect non-empty sections to add editorial hairline rhythm between them
  const filledSections = orderedSections.filter((part) => grouped[part].length > 0);

  return (
    <div className="space-y-0">
      {filledSections.map((part, idx) => {
        const sectionItems = grouped[part];
        const meta = DAY_PART_META[part];
        return (
          <div
            key={part}
            className={`space-y-1.5 ${idx > 0 ? "mt-3 pt-2.5 border-t border-ds-hairline/30" : ""}`}
            data-testid="day-part-section"
          >
            <div className="flex items-center gap-1.5 px-1 pt-0.5">
              <Clock className={`w-3 h-3 flex-shrink-0 ${meta.colorClass}`} />
              <span
                className={`text-[10px] font-semibold uppercase tracking-[0.1em] ${meta.colorClass}`}
                data-testid="day-part-label"
              >
                {meta.label}
              </span>
              <span className="text-[10px] text-ds-folio-ink-mist italic">{meta.timeHint}</span>
            </div>
            <div className="space-y-2">
              {renderItemsWithConnectors(sectionItems, dayId, onRemoveItem, onMoveItemToIdeas, onToggleCompare, compareSet, onUpdateTimeline)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── SuggestionsReviewPanel ───────────────────────────────────────────────────

const DAY_PART_COLOR: Record<string, string> = {
  morning:     "text-ds-marine-ink",
  afternoon:   "text-ds-folio-ink-soft",
  evening:     "text-ds-marine-soft",
  unscheduled: "text-ds-folio-ink-mist",
};

interface SuggestionsReviewPanelProps {
  suggestions: TimelineSuggestion[];
  items: ItineraryItem[];
  applying: boolean;
  onApply: () => void;
  onDismiss: () => void;
}

function SuggestionsReviewPanel({
  suggestions,
  items,
  applying,
  onApply,
  onDismiss,
}: SuggestionsReviewPanelProps) {
  const itemMap = new Map(items.map((i) => [i.id, i]));
  return (
    <div className="rounded-lg border border-ds-hairline bg-ds-linen p-3 mb-2 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold text-ds-folio-ink flex items-center gap-1.5">
          <Sparkles className="w-3 h-3 text-ds-marine-ink" />
          Suggested timing for {suggestions.length} {suggestions.length === 1 ? "item" : "items"}
        </span>
        <button
          onClick={onDismiss}
          className="flex items-center justify-center -m-2 min-w-[44px] min-h-[44px] rounded-lg text-ds-folio-ink-mist hover:text-ds-folio-ink transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2"
          aria-label="Dismiss suggestions"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="space-y-1">
        {suggestions.map((s) => {
          const item = itemMap.get(s.itemId);
          if (!item) return null;
          const colorClass = DAY_PART_COLOR[s.dayPart] ?? "text-ds-folio-ink-mist";
          return (
            <div key={s.itemId} className="flex items-center gap-2 text-[11px]">
              <span className="truncate flex-1 text-ds-folio-ink-soft">{item.title}</span>
              <span className={`font-medium ${colorClass} flex-shrink-0`}>
                {s.dayPart.charAt(0).toUpperCase() + s.dayPart.slice(1)}
              </span>
              {s.timeLabel && (
                <span className="text-ds-folio-ink-mist flex-shrink-0">· {s.timeLabel}</span>
              )}
            </div>
          );
        })}
      </div>

      <button
        onClick={onApply}
        disabled={applying}
        className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg border border-ds-hairline text-ds-marine-ink text-[11px] font-semibold transition-colors duration-[120ms] disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 min-h-[44px]"
        style={{ backgroundColor: "color-mix(in srgb, var(--ds-marine-ink) 8%, var(--ds-bone))" }}
      >
        {applying ? (
          <Loader2 className="w-3 h-3 animate-spin" />
        ) : (
          <Check className="w-3 h-3" />
        )}
        Apply All Suggestions
      </button>
    </div>
  );
}

// ─── DayTravelHintBar ─────────────────────────────────────────────────────────

function DayTravelHintBar({ items }: { items: ItineraryItem[] }) {
  if (items.length < 2) return null;
  const hints = computeAdjacentHints(items);
  const { farApartCount, missingLocationCount, hasIssues } = summarizeHints(hints);
  if (!hasIssues) return null;

  let message: string;
  if (farApartCount > 0 && missingLocationCount > 0) {
    message = "Some stops may be far apart. Add location details to improve hints.";
  } else if (farApartCount > 0) {
    message = "Some stops may be far apart. Consider grouping nearby items.";
  } else {
    message = "Add location details to improve travel hints.";
  }

  return (
    <div className="flex items-start gap-1.5 px-2 py-1.5 rounded-lg bg-ds-linen border border-ds-hairline mt-1.5">
      <Info className="w-3 h-3 text-ds-folio-ink-mist flex-shrink-0 mt-px" />
      <span className="text-[10px] text-ds-folio-ink-mist leading-tight">{message} Rough hints only.</span>
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
  onMoveItemToIdeas?: (itemId: string, currentDetails: Record<string, unknown>) => void;
  onAddItem: (dayId: string) => void;
  onToggleCompare?: (item: ItineraryItem) => void;
  compareSet?: Set<string>;
  onPlanDay?: (dayId: string, dayNumber: number) => void;
  planDayLoading?: boolean;
  onUpdateTimeline?: (updatedItem: ItineraryItem) => void;
  /** Opens the Add-to-Day vertical picker for this day. */
  onAddToDay?: (day: ItineraryDay) => void;
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
  onUpdateTimeline,
  onAddToDay,
}: ItineraryDayColumnProps) {
  const [expandedItemDays, setExpandedItemDays] = useState<Record<number, boolean>>({});
  // Local overrides for optimistic timeline updates — item moves to correct section immediately
  const [itemOverrides, setItemOverrides] = useState<Record<string, ItineraryItem>>({});
  // Smart timeline AI planning state
  const [suggestingTimeline, setSuggestingTimeline] = useState(false);
  const [timelineSuggestions, setTimelineSuggestions] = useState<TimelineSuggestion[] | null>(null);
  const [applyingTimeline, setApplyingTimeline] = useState(false);
  // Mobile action tray — shows secondary actions (Plan My Day, Suggest Timing) on phones
  const [mobileActionTrayOpen, setMobileActionTrayOpen] = useState(false);

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

  const handleTimelineUpdated = (updatedItem: ItineraryItem) => {
    setItemOverrides((prev) => ({ ...prev, [updatedItem.id]: updatedItem }));
    onUpdateTimeline?.(updatedItem);
  };

  const handleSuggestTimeline = async () => {
    if (day.items.length === 0) return;
    setSuggestingTimeline(true);
    setTimelineSuggestions(null);
    try {
      const suggestions = await suggestDayTimeline(day.items);
      setTimelineSuggestions(suggestions);
    } finally {
      setSuggestingTimeline(false);
    }
  };

  const handleApplyTimeline = async () => {
    if (!timelineSuggestions) return;
    setApplyingTimeline(true);
    try {
      await Promise.all(
        timelineSuggestions.map(async (s) => {
          const item = day.items.find((i) => i.id === s.itemId);
          if (!item) return;
          const currentDetails = (item.details ?? {}) as Record<string, unknown>;
          const updated = await updateItemTimeline(item.id, currentDetails, {
            dayPart: s.dayPart,
            timeLabel: s.timeLabel,
          });
          setItemOverrides((prev) => ({ ...prev, [updated.id]: updated }));
          onUpdateTimeline?.(updated);
        })
      );
    } finally {
      setApplyingTimeline(false);
      setTimelineSuggestions(null);
    }
  };

  const showAllItems = expandedItemDays[day.dayNumber] ?? false;
  const hasHiddenItems = day.items.length > PREVIEW_ITEM_LIMIT;
  const visibleItems = useMemo(
    () => {
      const items = showAllItems ? day.items : day.items.slice(0, PREVIEW_ITEM_LIMIT);
      // Apply optimistic timeline overrides so moved items appear in the correct section immediately
      return items.map((item) => itemOverrides[item.id] ?? item);
    },
    [day.items, showAllItems, itemOverrides]
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

  // Shared icon-button class for compact header actions (44×44px touch target)
  const iconBtnClass =
    "flex items-center justify-center min-w-[44px] min-h-[44px] rounded-lg bg-ds-bone hover:bg-ds-linen text-ds-folio-ink-mist hover:text-ds-folio-ink border border-ds-hairline transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 disabled:opacity-50";

  return (
    <FolioCard
      data-testid="day-chapter-frame"
      data-chapter-id="itinerary-day-mobile-chapter"
      className={`transition-all duration-[200ms] ${
        isSelected
          ? "border-ds-marine-ink/40 ring-1 ring-ds-marine-ink/20 ring-offset-1 ring-offset-ds-bone"
          : ""
      }`}
    >
      {/* ── Chapter header ──────────────────────────────────────────── */}
      <div
        data-testid="day-chapter-header"
        data-header-id="itinerary-day-mobile-header"
        className={`shrink-0 flex items-center justify-between px-3 py-2.5 border-b border-ds-hairline transition-colors duration-[120ms] ${
          isSelected ? "bg-ds-linen" : "folio-paper-header"
        }`}
      >
        {/* Chapter identity — semantic button for select + expand */}
        <button
          type="button"
          onClick={() => {
            onSelect?.(day.id);
            onToggleExpanded?.(day.dayNumber);
          }}
          aria-label={isSelected ? `Day ${day.dayNumber} — currently active` : `Select Day ${day.dayNumber}`}
          className="flex items-center gap-3 min-w-0 text-left min-h-[44px] rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2 transition-colors duration-[120ms]"
        >
          {/* Chapter number marker */}
          <div
            data-testid="day-chapter-number"
            className={`flex-shrink-0 flex items-center justify-center w-7 h-7 rounded text-[11px] font-bold tracking-tight transition-colors duration-[120ms] ${
              isSelected
                ? "bg-ds-marine-ink text-ds-paper"
                : "bg-ds-hairline text-ds-folio-ink-mist"
            }`}
          >
            {String(day.dayNumber).padStart(2, "0")}
          </div>
          {/* Chapter title + date */}
          <div className="min-w-0">
            <h3 data-testid="day-chapter-title" className="text-base font-semibold text-ds-folio-ink tracking-tight leading-snug">
              Day {day.dayNumber}
            </h3>
            {day.date && (
              <p data-testid="day-chapter-date" className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-folio-ink-mist leading-none mt-0.5">
                <CalendarDays className="w-2.5 h-2.5 flex-shrink-0" />
                {formatDate(day.date)}
              </p>
            )}
          </div>
        </button>

        {/* Header actions */}
        <div className="flex items-center gap-1 shrink-0">
          <span data-testid="day-item-count" className="text-[11px] text-ds-folio-ink-mist bg-ds-linen border border-ds-hairline rounded-full px-2 py-0.5 mr-0.5">
            {day.items.length}
          </span>

          {onPlanDay && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onPlanDay(day.id, day.dayNumber);
              }}
              disabled={planDayLoading}
              title="Generate AI day plan"
              className="hidden lg:flex items-center gap-1 px-2.5 rounded-lg text-ds-marine-ink border border-ds-hairline text-[11px] font-medium transition-colors duration-[120ms] disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 min-h-[44px]"
              style={{ backgroundColor: "color-mix(in srgb, var(--ds-marine-ink) 8%, var(--ds-bone))" }}
            >
              {planDayLoading ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <Sparkles className="w-3 h-3" />
              )}
              Plan My Day
            </button>
          )}

          {day.items.length > 0 && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleSuggestTimeline();
              }}
              disabled={suggestingTimeline || applyingTimeline}
              title="Suggest timing for items on this day"
              aria-label="Suggest day timing"
              className="hidden lg:flex items-center gap-1 px-2.5 rounded-lg bg-ds-bone hover:bg-ds-linen text-ds-folio-ink-mist hover:text-ds-folio-ink border border-ds-hairline text-[11px] font-medium transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 disabled:opacity-50 min-h-[44px]"
            >
              {suggestingTimeline ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <Clock className="w-3 h-3" />
              )}
              Suggest Timing
            </button>
          )}

          {/* Mobile-only overflow toggle for secondary day actions */}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setMobileActionTrayOpen((v) => !v);
            }}
            className="lg:hidden flex items-center justify-center min-w-[44px] min-h-[44px] rounded-lg bg-ds-bone hover:bg-ds-linen text-ds-folio-ink-mist hover:text-ds-folio-ink border border-ds-hairline transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2"
            aria-label={`Day ${day.dayNumber} actions`}
            data-testid="itinerary-day-mobile-action-tray"
          >
            <MoreHorizontal className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={(e) => {
              e.stopPropagation();
              onSelect?.(day.id);
              onAddItem(day.id);
            }}
            className={iconBtnClass}
            aria-label={`Add item to Day ${day.dayNumber}`}
          >
            <Plus className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggleExpanded?.(day.dayNumber);
            }}
            className={iconBtnClass}
            aria-label={`${isExpanded ? "Collapse" : "Expand"} Day ${day.dayNumber}`}
          >
            {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* ── Mobile action tray — secondary day actions (shown when overflow open) ── */}
      {mobileActionTrayOpen && (
        <div className="lg:hidden border-b border-ds-hairline bg-ds-linen px-3 py-2.5 flex items-center gap-2 flex-wrap">
          {onPlanDay && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setMobileActionTrayOpen(false);
                onPlanDay(day.id, day.dayNumber);
              }}
              disabled={planDayLoading}
              className="flex items-center gap-1.5 px-3 rounded-lg text-ds-marine-ink border border-ds-hairline text-[11px] font-medium transition-colors duration-[120ms] disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 min-h-[44px]"
              style={{ backgroundColor: "color-mix(in srgb, var(--ds-marine-ink) 8%, var(--ds-bone))" }}
              aria-label={`Plan Day ${day.dayNumber}`}
            >
              {planDayLoading ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <Sparkles className="w-3 h-3" />
              )}
              Plan My Day
            </button>
          )}
          {day.items.length > 0 && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setMobileActionTrayOpen(false);
                handleSuggestTimeline();
              }}
              disabled={suggestingTimeline || applyingTimeline}
              className="flex items-center gap-1.5 px-3 rounded-lg bg-ds-bone hover:bg-ds-linen text-ds-folio-ink-mist hover:text-ds-folio-ink border border-ds-hairline text-[11px] font-medium transition-colors duration-[120ms] disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 min-h-[44px]"
              aria-label={`Suggest timing for Day ${day.dayNumber}`}
            >
              {suggestingTimeline ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <Clock className="w-3 h-3" />
              )}
              Suggest Timing
            </button>
          )}
          {onAddToDay && (
            <button
              type="button"
              data-testid="itinerary-add-to-day-btn"
              onClick={(e) => {
                e.stopPropagation();
                setMobileActionTrayOpen(false);
                onAddToDay(day);
              }}
              className="flex items-center gap-1.5 px-3 rounded-lg text-ds-marine-ink border border-ds-marine-ink/30 text-[11px] font-medium transition-colors duration-[120ms] hover:border-ds-marine-ink/60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 min-h-[44px]"
              aria-label={`Add to Day ${day.dayNumber}`}
            >
              <Plus className="w-3 h-3" />
              Add to this day
            </button>
          )}
        </div>
      )}

      {/* ── Collapsed summary ──────────────────────────────────────── */}
      {!isExpanded ? (
        <div
          ref={setNodeRef}
          data-testid="itinerary-day-mobile-summary"
          className="px-3 py-2.5 transition-colors duration-[120ms]"
          style={{ backgroundColor: isOver ? "color-mix(in srgb, var(--ds-marine-ink) 8%, var(--ds-bone))" : "var(--ds-bone)" }}
        >
          {day.items.length === 0 ? (
            <p className="text-xs text-ds-folio-ink-mist italic">No plans yet.</p>
          ) : (
            <div className="space-y-0.5">
              <p className="text-xs text-ds-folio-ink-soft truncate">{firstItem?.title ?? "Itinerary item"}</p>
              <p className="text-[11px] text-ds-folio-ink-mist">
                {hiddenItemsCount > 0 ? `+${hiddenItemsCount} more · ` : ""}
                {itemSummary}
              </p>
            </div>
          )}
        </div>
      ) : (
        /* ── Expanded body ─────────────────────────────────────────── */
        <div
          ref={setNodeRef}
          data-testid="itinerary-day-mobile-expanded"
          className="p-3 min-h-[68px] h-auto overflow-hidden space-y-2 transition-colors duration-[120ms]"
          style={{ backgroundColor: isOver ? "color-mix(in srgb, var(--ds-marine-ink) 8%, var(--ds-bone))" : "var(--ds-warm-paper)" }}
        >
          {timelineSuggestions && (
            <SuggestionsReviewPanel
              suggestions={timelineSuggestions}
              items={day.items}
              applying={applyingTimeline}
              onApply={handleApplyTimeline}
              onDismiss={() => setTimelineSuggestions(null)}
            />
          )}

          <SortableContext items={itemIds} strategy={verticalListSortingStrategy}>
            <div
              data-testid="itinerary-day-mobile-timeline"
              className={`relative rounded-lg p-1 transition-colors duration-[120ms] ${
                isSelected ? "ring-1 ring-ds-marine-ink/15 bg-ds-linen/30" : ""
              }`}
            >
              {/* Mobile timeline vertical rail — editorial day-chapter flow */}
              <div
                className="lg:hidden absolute left-3 top-2 bottom-2 w-px bg-ds-hairline"
                aria-hidden="true"
              />
              <TimelineSections
                items={visibleItems}
                dayId={day.id}
                onRemoveItem={onRemoveItem}
                onMoveItemToIdeas={onMoveItemToIdeas}
                onToggleCompare={onToggleCompare}
                compareSet={compareSet}
                onUpdateTimeline={handleTimelineUpdated}
              />
              {!showAllItems && hasHiddenItems && (
                <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-14 bg-gradient-to-b from-transparent to-ds-bone" />
              )}
            </div>
          </SortableContext>

          {visibleItems.length >= 2 && <DayTravelHintBar items={visibleItems} />}

          {/* ── Empty day invitation ─────────────────────────────────── */}
          {day.items.length === 0 && (
            <div
              data-testid="empty-day-chapter"
              className={`flex-1 flex flex-col items-center justify-center border border-dashed rounded-lg py-5 px-3 gap-1.5 transition-colors duration-[120ms] ${
                isOver
                  ? "border-ds-marine-ink/60 text-ds-marine-ink"
                  : "border-ds-hairline text-ds-folio-ink-mist"
              }`}
              style={isOver ? { backgroundColor: "var(--ds-accent-subtle)" } : undefined}
            >
              {isOver ? (
                <p className="text-xs font-medium text-center">Drop here</p>
              ) : (
                <>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-folio-ink-mist">
                    Day {day.dayNumber}
                  </p>
                  <p className="text-xs text-center text-ds-folio-ink-mist">
                    Begin this chapter — use{" "}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelect?.(day.id);
                        onAddItem(day.id);
                      }}
                      className="inline-flex items-center min-h-[44px] min-w-[44px] px-1 text-ds-marine-ink hover:text-ds-folio-ink-soft underline underline-offset-2 transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2"
                    >
                      + Add
                    </button>{" "}
                    or drag a stop here.
                  </p>
                </>
              )}
            </div>
          )}

          {/* ── Active drop indicator (when day already has items) ────── */}
          {day.items.length > 0 && isOver && (
            <div
              className="border border-dashed border-ds-accent/60 rounded-lg py-2 flex items-center justify-center transition-colors duration-[120ms]"
              style={{ backgroundColor: "var(--ds-accent-subtle)" }}
            >
              <p className="text-xs text-ds-accent font-medium">Drop here</p>
            </div>
          )}

          {/* ── Show all / show less ──────────────────────────────────── */}
          {hasHiddenItems && (
            <div className="mt-2 flex justify-center border-t border-ds-hairline pt-3">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setExpandedItemDays((prev) => ({
                    ...prev,
                    [day.dayNumber]: !showAllItems,
                  }));
                }}
                className="rounded-full border border-ds-hairline bg-ds-linen px-4 text-sm font-medium text-ds-folio-ink-soft hover:bg-ds-bone transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2 min-h-[44px]"
              >
                {showAllItems ? "Show less ↑" : `Show all ${day.items.length} items ↓`}
              </button>
            </div>
          )}
        </div>
      )}
    </FolioCard>
  );
}
