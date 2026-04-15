"use client";

import { useState, useCallback, useRef } from "react";
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
  Utensils,
  Train,
  FileText,
  Search,
  CalendarPlus,
  Sparkles,
  Scale,
  Loader2,
  BarChart2,
} from "lucide-react";
import type { ItineraryDay, ItineraryItem, ResearchResult, ResearchCategory, ItemType, CompareResult } from "@/types";
import {
  createDay,
  deleteItem,
  createItem,
  updateItem,
  compareItems,
} from "@/lib/api";
import { SearchResultCard } from "./SearchResultCard";
import { ItineraryDayColumn } from "./ItineraryDayColumn";
import { ItineraryItemCard } from "./ItineraryItemCard";
import { CompareModal } from "./CompareModal";

// ─── Category filter config ───────────────────────────────────────────────────

const CATEGORY_FILTERS: {
  value: ResearchCategory | "all";
  label: string;
  icon: React.ReactNode;
}[] = [
  { value: "all",      label: "All",        icon: <Sparkles className="w-3.5 h-3.5" /> },
  { value: "flight",   label: "Flights",    icon: <Plane    className="w-3.5 h-3.5" /> },
  { value: "hotel",    label: "Hotels",     icon: <Hotel    className="w-3.5 h-3.5" /> },
  { value: "activity", label: "Activities", icon: <MapPin   className="w-3.5 h-3.5" /> },
  { value: "meal",     label: "Meals",      icon: <Utensils className="w-3.5 h-3.5" /> },
  { value: "transit",  label: "Transit",    icon: <Train    className="w-3.5 h-3.5" /> },
  { value: "note",     label: "Notes",      icon: <FileText className="w-3.5 h-3.5" /> },
];

// ─── Props ────────────────────────────────────────────────────────────────────

interface TripBuilderProps {
  tripId: string;
  initialDays: ItineraryDay[];
  initialResults: ResearchResult[];
}

// ─── Main component ───────────────────────────────────────────────────────────

export function TripBuilder({ tripId, initialDays, initialResults }: TripBuilderProps) {
  const [days,          setDays]         = useState<ItineraryDay[]>(initialDays);
  const [results]                        = useState<ResearchResult[]>(initialResults);
  const [activeFilter,  setActiveFilter] = useState<ResearchCategory | "all">("all");
  const [searchQuery,   setSearchQuery]  = useState("");
  const [activeId,      setActiveId]     = useState<UniqueIdentifier | null>(null);

  // ── Compare state ───────────────────────────────────────────────────────────
  const [compareSet,     setCompareSet]     = useState<Set<string>>(new Set());
  const [compareOpen,    setCompareOpen]    = useState(false);
  const [compareResults, setCompareResults] = useState<CompareResult[]>([]);
  const [compareLoading, setCompareLoading] = useState(false);
  // Stores full item data for items in the compare set (keyed by id)
  const compareDataRef = useRef<Map<string, { name: string; itemType: string; cashPrice: number; pointsCost: number; rating?: number }>>(new Map());

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  // ── Filtered results ────────────────────────────────────────────────────────

  const filteredResults = results.filter((r) => {
    const matchesFilter = activeFilter === "all" || r.category === activeFilter;
    const matchesSearch =
      !searchQuery ||
      r.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.location?.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  // ── Add research result by clicking "+" ──────────────────────────────────────

  const handleAddResult = useCallback(async (result: ResearchResult) => {
    const targetDay = days[0];
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
        prev.map((d) =>
          d.id === targetDay.id ? { ...d, items: [...d.items, newItem] } : d
        )
      );
    } catch {
      // silently ignore — user can retry
    }
  }, [days, tripId]);

  // ── Remove item from a day ──────────────────────────────────────────────────

  const handleRemoveItem = useCallback(async (itemId: string, dayId: string) => {
    // Optimistic update
    setDays((prev) =>
      prev.map((d) =>
        d.id === dayId
          ? {
              ...d,
              items: d.items
                .filter((i) => i.id !== itemId)
                .map((i, idx) => ({ ...i, position: idx })),
            }
          : d
      )
    );
    try {
      await deleteItem(itemId);
    } catch {
      // silently ignore — state remains updated
    }
  }, []);

  // ── Add empty note item to a day ────────────────────────────────────────────

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
        prev.map((d) =>
          d.id === dayId ? { ...d, items: [...d.items, newItem] } : d
        )
      );
    } catch {
      // silently ignore
    }
  }, [days, tripId]);

  // ── Add new day ─────────────────────────────────────────────────────────────

  const handleAddDay = useCallback(async () => {
    const nextNum = days.length + 1;
    try {
      const newDay = await createDay(tripId, {
        dayNumber: nextNum,
        title: `Day ${nextNum}`,
      });
      setDays((prev) => [...prev, newDay]);
    } catch {
      // silently ignore
    }
  }, [days.length, tripId]);

  // ── Compare: toggle an item in/out of the compare set ───────────────────────

  const handleToggleCompareResult = useCallback((result: ResearchResult) => {
    const price = result.priceDisplay
      ? parseFloat(result.priceDisplay.replace(/[^0-9.]/g, "")) || 0
      : 0;
    setCompareSet((prev) => {
      const next = new Set(prev);
      if (next.has(result.id)) {
        next.delete(result.id);
        compareDataRef.current.delete(result.id);
      } else {
        next.add(result.id);
        compareDataRef.current.set(result.id, {
          name: result.title,
          itemType: result.category,
          cashPrice: price,
          pointsCost: 0,
          rating: result.rating,
        });
      }
      return next;
    });
  }, []);

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
    } catch {
      // silently ignore — user can retry
    } finally {
      setCompareLoading(false);
    }
  }, [compareSet]);

  // ── DnD: drag start ─────────────────────────────────────────────────────────

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(event.active.id);
  }, []);

  // ── DnD: drag over (cross-day live preview) ─────────────────────────────────

  const handleDragOver = useCallback(
    (event: DragOverEvent) => {
      const { active, over } = event;
      if (!over) return;

      const activeData = active.data.current;
      const overData   = over.data.current;

      if (!activeData) return;
      if (activeData.type === "result") return; // handled on dragEnd

      if (activeData.type === "itinerary-item") {
        const sourceItem: ItineraryItem = activeData.item;
        const sourceDayId = sourceItem.dayId;

        let targetDayId: string | null = null;

        if (overData?.type === "itinerary-item") {
          targetDayId = overData.item.dayId;
        } else if (overData?.type === "day") {
          targetDayId = overData.dayId;
        } else {
          const idStr = String(over.id);
          if (idStr.startsWith("day-")) targetDayId = idStr.replace("day-", "");
        }

        if (!targetDayId || targetDayId === sourceDayId) return;

        setDays((prev) => {
          const sourceDay = prev.find((d) => d.id === sourceDayId);
          const targetDay = prev.find((d) => d.id === targetDayId);
          if (!sourceDay || !targetDay) return prev;

          const updatedItem = { ...sourceItem, dayId: targetDayId! };

          return prev.map((d) => {
            if (d.id === sourceDayId) {
              return {
                ...d,
                items: d.items
                  .filter((i) => i.id !== sourceItem.id)
                  .map((i, idx) => ({ ...i, position: idx })),
              };
            }
            if (d.id === targetDayId) {
              return {
                ...d,
                items: [...d.items, updatedItem].map((i, idx) => ({
                  ...i,
                  position: idx,
                })),
              };
            }
            return d;
          });
        });
      }
    },
    []
  );

  // ── DnD: drag end ───────────────────────────────────────────────────────────

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      setActiveId(null);
      const { active, over } = event;
      if (!over) return;

      const activeData = active.data.current;
      const overData   = over.data.current;

      // ── Drop research result onto a day ──
      if (activeData?.type === "result") {
        const result: ResearchResult = activeData.result;

        let targetDayId: string | null = null;
        if (overData?.type === "day") {
          targetDayId = overData.dayId;
        } else if (overData?.type === "itinerary-item") {
          targetDayId = overData.item.dayId;
        } else {
          const idStr = String(over.id);
          if (idStr.startsWith("day-")) targetDayId = idStr.replace("day-", "");
        }

        if (!targetDayId) return;

        const targetDay = days.find((d) => d.id === targetDayId);
        if (!targetDay) return;

        // Create on server then add to state with real ID
        createItem(tripId, targetDayId, {
          itemType: result.category as ItemType,
          title: result.title,
          description: result.description,
          location: result.location,
          position: targetDay.items.length,
          bookingOptions: result.bookingOptions,
        })
          .then((newItem) => {
            setDays((prev) =>
              prev.map((d) =>
                d.id !== targetDayId ? d : { ...d, items: [...d.items, newItem] }
              )
            );
          })
          .catch(() => {
            // silently ignore
          });

        return;
      }

      // ── Reorder itinerary item within same day ──
      if (activeData?.type === "itinerary-item") {
        const sourceItem: ItineraryItem = activeData.item;
        if (!overData) return;

        const overId = String(over.id);
        const targetDayId =
          overData.type === "itinerary-item"
            ? overData.item.dayId
            : overData.type === "day"
            ? overData.dayId
            : overId.startsWith("day-")
            ? overId.replace("day-", "")
            : null;

        if (!targetDayId) return;

        if (targetDayId === sourceItem.dayId) {
          // Same-day reorder
          setDays((prev) =>
            prev.map((d) => {
              if (d.id !== targetDayId) return d;
              const oldIndex = d.items.findIndex((i) => i.id === sourceItem.id);
              const newIndex = d.items.findIndex((i) => i.id === String(over.id));
              if (oldIndex === -1 || newIndex === -1 || oldIndex === newIndex)
                return d;
              const reordered = arrayMove(d.items, oldIndex, newIndex).map(
                (i, idx) => ({ ...i, position: idx })
              );

              // Persist updated positions in background
              reordered.forEach((item) => {
                updateItem(item.id, { position: item.position }).catch(() => {});
              });

              return { ...d, items: reordered };
            })
          );
        } else {
          // Cross-day move: preview was applied in dragOver; now persist
          // Update the moved item's dayId on the server
          updateItem(sourceItem.id, { dayId: targetDayId as unknown as string } as Partial<ItineraryItem>).catch(() => {});
        }
      }
    },
    [days, tripId]
  );

  // ── Active drag overlay item ────────────────────────────────────────────────

  const activeDragItem: ItineraryItem | ResearchResult | null = (() => {
    if (!activeId) return null;
    const idStr = String(activeId);
    if (idStr.startsWith("result-")) {
      const resultId = idStr.replace("result-", "");
      return results.find((r) => r.id === resultId) ?? null;
    }
    for (const day of days) {
      const item = day.items.find((i) => i.id === idStr);
      if (item) return item;
    }
    return null;
  })();

  const isResultDrag =
    activeDragItem !== null && "category" in activeDragItem;

  // ─────────────────────────────────────────────────────────────────────────────

  return (
    <>
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-4 h-[calc(100vh-220px)] min-h-[500px]">
        {/* ── Left Panel: Research Results ──────────────────────────────────── */}
        <div className="w-80 flex-shrink-0 flex flex-col gap-3 overflow-hidden">
          <div className="card p-3 flex flex-col gap-2">
            <h2 className="text-sm font-semibold text-slate-700">Research Results</h2>

            {/* Search */}
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search results…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input pl-8 py-1.5 text-xs"
              />
            </div>

            {/* Category filter chips */}
            <div className="flex flex-wrap gap-1">
              {CATEGORY_FILTERS.map((f) => (
                <button
                  key={f.value}
                  onClick={() => setActiveFilter(f.value)}
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium transition-colors ${
                    activeFilter === f.value
                      ? "bg-sky-600 text-white"
                      : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                  }`}
                >
                  {f.icon}
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          {/* Result cards list */}
          <div className="flex-1 overflow-y-auto flex flex-col gap-2 pr-0.5">
            {results.length === 0 ? (
              <div className="card p-6 text-center text-slate-400">
                <Sparkles className="w-6 h-6 mx-auto mb-2 text-slate-300" />
                <p className="text-xs font-medium text-slate-500">No research results yet</p>
                <p className="text-xs mt-1">Search results will appear here once the AI concierge runs.</p>
              </div>
            ) : filteredResults.length > 0 ? (
              filteredResults.map((result) => (
                <SearchResultCard
                  key={result.id}
                  result={result}
                  onAdd={handleAddResult}
                  onToggleCompare={handleToggleCompareResult}
                  isComparing={compareSet.has(result.id)}
                />
              ))
            ) : (
              <div className="card p-6 text-center text-slate-400">
                <p className="text-xs">No results match your filter.</p>
              </div>
            )}
          </div>
        </div>

        {/* ── Right Panel: Itinerary Timeline ───────────────────────────────── */}
        <div className="flex-1 flex flex-col gap-3 overflow-hidden">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-700">
              Itinerary
              <span className="ml-2 text-slate-400 font-normal">
                {days.reduce((sum, d) => sum + d.items.length, 0)} items across{" "}
                {days.length} days
              </span>
            </h2>
            <button onClick={handleAddDay} className="btn-ghost py-1.5 text-xs">
              <CalendarPlus className="w-3.5 h-3.5" />
              Add Day
            </button>
          </div>

          {/* Day columns */}
          <div className="flex-1 overflow-y-auto flex flex-col gap-3 pr-0.5">
            <SortableContext
              items={days.map((d) => d.id)}
              strategy={verticalListSortingStrategy}
            >
              {days.map((day) => (
                <ItineraryDayColumn
                  key={day.id}
                  day={day}
                  onRemoveItem={handleRemoveItem}
                  onAddItem={handleAddToDay}
                  onToggleCompare={handleToggleCompareItem}
                  compareSet={compareSet}
                />
              ))}
            </SortableContext>

            {days.length === 0 && (
              <div className="card p-8 text-center text-slate-400">
                <CalendarPlus className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                <p className="text-sm font-medium text-slate-500">No days yet</p>
                <p className="text-xs mt-1">
                  Click &ldquo;Add Day&rdquo; to start building your itinerary.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Compare bar ──────────────────────────────────────────────────────── */}
      {compareSet.size > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-3 px-5 py-3 bg-slate-900 text-white rounded-2xl shadow-2xl ring-1 ring-white/10">
          <Scale className="w-4 h-4 text-violet-400 flex-shrink-0" />
          {/* Dot indicators for each selected item */}
          <div className="flex items-center gap-1">
            {Array.from({ length: Math.min(compareSet.size, 10) }).map((_, i) => (
              <div
                key={i}
                className="w-2 h-2 rounded-full bg-violet-400"
              />
            ))}
          </div>
          <span className="text-sm font-medium text-slate-200">
            {compareSet.size} item{compareSet.size !== 1 ? "s" : ""}
            {compareSet.size < 2 && (
              <span className="text-slate-400 text-xs ml-1">(need 2+)</span>
            )}
          </span>
          <div className="w-px h-4 bg-slate-700" />
          <button
            onClick={handleCompare}
            disabled={compareSet.size < 2 || compareLoading}
            className="px-4 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed text-sm font-semibold transition-colors flex items-center gap-1.5"
          >
            {compareLoading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <BarChart2 className="w-3.5 h-3.5" />
            )}
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

      {/* ── Drag Overlay ─────────────────────────────────────────────────────── */}
      <DragOverlay>
        {activeDragItem && isResultDrag && (
          <div className="rotate-1 scale-105 shadow-2xl opacity-95 w-72">
            <SearchResultCard
              result={activeDragItem as ResearchResult}
              onAdd={() => {}}
            />
          </div>
        )}
        {activeDragItem && !isResultDrag && (
          <div className="rotate-1 scale-105 shadow-2xl opacity-95">
            <ItineraryItemCard
              item={activeDragItem as ItineraryItem}
              onRemove={() => {}}
            />
          </div>
        )}
      </DragOverlay>
    </DndContext>

    {/* ── Compare Modal ──────────────────────────────────────────────────────── */}
    {compareOpen && compareResults.length > 0 && (
      <CompareModal
        results={compareResults}
        onClose={() => setCompareOpen(false)}
      />
    )}
    </>
  );
}
