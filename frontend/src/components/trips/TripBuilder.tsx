"use client";

import { useState, useCallback } from "react";
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
} from "lucide-react";
import { ItineraryDay, ItineraryItem, ResearchResult, ResearchCategory, ItemType } from "@/types";
import { SearchResultCard } from "./SearchResultCard";
import { ItineraryDayColumn } from "./ItineraryDayColumn";
import { ItineraryItemCard } from "./ItineraryItemCard";

// ─── Mock research results ────────────────────────────────────────────────────

const MOCK_RESULTS: ResearchResult[] = [
  {
    id: "r1",
    category: "flight",
    title: "JFK → CDG — Air France AF007",
    description: "Nonstop, 7h 20m. Business class award available.",
    duration: "7h 20m",
    priceDisplay: "60k pts",
    rating: 4.5,
    tags: ["Nonstop", "Business"],
  },
  {
    id: "r2",
    category: "hotel",
    title: "Hôtel Le Marais Boutique",
    description: "4-star hotel in the heart of Le Marais district.",
    location: "Le Marais, Paris",
    duration: "Per night",
    priceDisplay: "$220/night",
    rating: 4.7,
    tags: ["Breakfast", "Free Wi-Fi"],
  },
  {
    id: "r3",
    category: "activity",
    title: "Skip-the-Line Louvre Tour",
    description: "Guided 3h tour of the Louvre's highlights.",
    location: "Louvre, Paris",
    duration: "3 hours",
    priceDisplay: "$65/person",
    rating: 4.8,
    tags: ["Guided", "Skip-the-line"],
  },
  {
    id: "r4",
    category: "meal",
    title: "Dinner at Septime",
    description: "Award-winning bistro with seasonal tasting menus.",
    location: "11th arrondissement",
    duration: "2 hours",
    priceDisplay: "$90/person",
    rating: 4.9,
    tags: ["Fine dining", "Reservations required"],
  },
  {
    id: "r5",
    category: "transit",
    title: "CDG Airport → City (RER B)",
    description: "Direct train from Charles de Gaulle to central Paris.",
    duration: "35 min",
    priceDisplay: "$12",
    tags: ["Train", "Direct"],
  },
  {
    id: "r6",
    category: "activity",
    title: "Eiffel Tower Evening Visit",
    description: "Timed-entry tickets for the summit at sunset.",
    location: "Champ de Mars, Paris",
    duration: "2 hours",
    priceDisplay: "$35/person",
    rating: 4.6,
    tags: ["Landmark", "Timed entry"],
  },
  {
    id: "r7",
    category: "hotel",
    title: "Novotel Paris Eiffel Tower",
    description: "Modern hotel with Eiffel Tower views, near Champ de Mars.",
    location: "7th arrondissement",
    duration: "Per night",
    priceDisplay: "$180/night",
    rating: 4.3,
    tags: ["Pool", "Gym"],
  },
  {
    id: "r8",
    category: "meal",
    title: "Café de Flore Breakfast",
    description: "Iconic Saint-Germain café with classic French breakfast.",
    location: "Saint-Germain-des-Prés",
    duration: "1 hour",
    priceDisplay: "$25/person",
    rating: 4.2,
    tags: ["Iconic", "Historic"],
  },
  {
    id: "r9",
    category: "activity",
    title: "Seine River Cruise",
    description: "1-hour scenic cruise past Notre-Dame and the Louvre.",
    location: "Pont de l'Alma",
    duration: "1 hour",
    priceDisplay: "$18/person",
    rating: 4.4,
    tags: ["Scenic", "Family-friendly"],
  },
  {
    id: "r10",
    category: "flight",
    title: "CDG → JFK — Delta DL264",
    description: "Return flight, 8h 45m. Economy award space available.",
    duration: "8h 45m",
    priceDisplay: "35k pts",
    rating: 4.1,
    tags: ["Nonstop", "Economy"],
  },
];

// ─── Mock itinerary days ──────────────────────────────────────────────────────

const MOCK_DAYS: ItineraryDay[] = [
  {
    id: "day-1",
    tripId: "trip-1",
    dayNumber: 1,
    date: "2025-06-14",
    title: "Arrival Day",
    summary: "Arrive in Paris, check in, first impressions.",
    items: [
      {
        id: "item-1",
        dayId: "day-1",
        tripId: "trip-1",
        itemType: "flight",
        title: "JFK → CDG — Air France AF007",
        description: "Nonstop business class",
        startTime: "18:30",
        endTime: "08:50+1",
        position: 0,
      },
      {
        id: "item-2",
        dayId: "day-1",
        tripId: "trip-1",
        itemType: "transit",
        title: "CDG → City Centre (RER B)",
        startTime: "10:00",
        endTime: "10:35",
        position: 1,
      },
      {
        id: "item-3",
        dayId: "day-1",
        tripId: "trip-1",
        itemType: "hotel",
        title: "Check in — Hôtel Le Marais Boutique",
        location: "Le Marais, Paris",
        startTime: "15:00",
        position: 2,
      },
    ],
  },
  {
    id: "day-2",
    tripId: "trip-1",
    dayNumber: 2,
    date: "2025-06-15",
    title: "Museums & Culture",
    summary: "Visit the Louvre and explore Saint-Germain.",
    items: [
      {
        id: "item-4",
        dayId: "day-2",
        tripId: "trip-1",
        itemType: "meal",
        title: "Café de Flore Breakfast",
        location: "Saint-Germain-des-Prés",
        startTime: "09:00",
        endTime: "10:00",
        position: 0,
      },
      {
        id: "item-5",
        dayId: "day-2",
        tripId: "trip-1",
        itemType: "activity",
        title: "Skip-the-Line Louvre Tour",
        location: "Louvre, Paris",
        startTime: "11:00",
        endTime: "14:00",
        cashPrice: 65,
        cashCurrency: "USD",
        position: 1,
      },
    ],
  },
  {
    id: "day-3",
    tripId: "trip-1",
    dayNumber: 3,
    date: "2025-06-16",
    title: "Eiffel Tower & Fine Dining",
    summary: "Iconic Paris sights and a special dinner.",
    items: [],
  },
];

// ─── Category filter config ───────────────────────────────────────────────────

const CATEGORY_FILTERS: {
  value: ResearchCategory | "all";
  label: string;
  icon: React.ReactNode;
}[] = [
  { value: "all", label: "All", icon: <Sparkles className="w-3.5 h-3.5" /> },
  { value: "flight", label: "Flights", icon: <Plane className="w-3.5 h-3.5" /> },
  { value: "hotel", label: "Hotels", icon: <Hotel className="w-3.5 h-3.5" /> },
  { value: "activity", label: "Activities", icon: <MapPin className="w-3.5 h-3.5" /> },
  { value: "meal", label: "Meals", icon: <Utensils className="w-3.5 h-3.5" /> },
  { value: "transit", label: "Transit", icon: <Train className="w-3.5 h-3.5" /> },
  { value: "note", label: "Notes", icon: <FileText className="w-3.5 h-3.5" /> },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function categoryToItemType(cat: ResearchCategory): ItemType {
  return cat as ItemType;
}

function resultToItem(result: ResearchResult, dayId: string, position: number): ItineraryItem {
  return {
    id: `item-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    dayId,
    tripId: "trip-1",
    itemType: categoryToItemType(result.category),
    title: result.title,
    description: result.description,
    location: result.location,
    position,
  };
}

// ─── Main component ───────────────────────────────────────────────────────────

export function TripBuilder() {
  const [days, setDays] = useState<ItineraryDay[]>(MOCK_DAYS);
  const [results] = useState<ResearchResult[]>(MOCK_RESULTS);
  const [activeFilter, setActiveFilter] = useState<ResearchCategory | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [activeId, setActiveId] = useState<UniqueIdentifier | null>(null);

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

  // ── Add result by clicking "+" ───────────────────────────────────────────────

  const handleAddResult = useCallback((result: ResearchResult) => {
    setDays((prev) => {
      const targetDay = prev[0]; // default to first day
      if (!targetDay) return prev;
      const newItem = resultToItem(result, targetDay.id, targetDay.items.length);
      return prev.map((d) =>
        d.id === targetDay.id ? { ...d, items: [...d.items, newItem] } : d
      );
    });
  }, []);

  // ── Remove item from a day ──────────────────────────────────────────────────

  const handleRemoveItem = useCallback((itemId: string, dayId: string) => {
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
  }, []);

  // ── Add empty item to a day (placeholder) ──────────────────────────────────

  const handleAddToDay = useCallback((dayId: string) => {
    setDays((prev) =>
      prev.map((d) =>
        d.id === dayId
          ? {
              ...d,
              items: [
                ...d.items,
                {
                  id: `item-${Date.now()}`,
                  dayId,
                  tripId: "trip-1",
                  itemType: "note" as ItemType,
                  title: "New item",
                  position: d.items.length,
                },
              ],
            }
          : d
      )
    );
  }, []);

  // ── Add new day ─────────────────────────────────────────────────────────────

  const handleAddDay = useCallback(() => {
    setDays((prev) => {
      const nextNum = prev.length + 1;
      const newDay: ItineraryDay = {
        id: `day-${Date.now()}`,
        tripId: "trip-1",
        dayNumber: nextNum,
        title: `Day ${nextNum}`,
        items: [],
      };
      return [...prev, newDay];
    });
  }, []);

  // ── DnD: drag start ─────────────────────────────────────────────────────────

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(event.active.id);
  }, []);

  // ── DnD: drag over (cross-day reorder preview) ──────────────────────────────

  const handleDragOver = useCallback(
    (event: DragOverEvent) => {
      const { active, over } = event;
      if (!over) return;

      const activeData = active.data.current;
      const overData = over.data.current;

      if (!activeData) return;

      // Dragging a research result — no preview needed, handled on dragEnd
      if (activeData.type === "result") return;

      // Dragging an itinerary item over another item or a day
      if (activeData.type === "itinerary-item") {
        const sourceItem: ItineraryItem = activeData.item;
        const sourceDayId = sourceItem.dayId;

        let targetDayId: string | null = null;

        if (overData?.type === "itinerary-item") {
          targetDayId = overData.item.dayId;
        } else if (overData?.type === "day") {
          targetDayId = overData.dayId;
        } else {
          // over.id might be `day-${id}`
          const idStr = String(over.id);
          if (idStr.startsWith("day-")) {
            targetDayId = idStr.replace("day-", "");
          }
        }

        if (!targetDayId || targetDayId === sourceDayId) return;

        // Move item to new day for live preview
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
      const overData = over.data.current;

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
          if (idStr.startsWith("day-")) {
            targetDayId = idStr.replace("day-", "");
          }
        }

        if (!targetDayId) return;

        setDays((prev) =>
          prev.map((d) => {
            if (d.id !== targetDayId) return d;
            const newItem = resultToItem(result, d.id, d.items.length);
            return { ...d, items: [...d.items, newItem] };
          })
        );
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

        // If same day, reorder
        if (targetDayId === sourceItem.dayId) {
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
              return { ...d, items: reordered };
            })
          );
        }
        // Cross-day move was already handled by dragOver
      }
    },
    []
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
    activeDragItem !== null &&
    "category" in activeDragItem;

  // ─────────────────────────────────────────────────────────────────────────────

  return (
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
            {filteredResults.length > 0 ? (
              filteredResults.map((result) => (
                <SearchResultCard
                  key={result.id}
                  result={result}
                  onAdd={handleAddResult}
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
            <button
              onClick={handleAddDay}
              className="btn-ghost py-1.5 text-xs"
            >
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
                />
              ))}
            </SortableContext>

            {days.length === 0 && (
              <div className="card p-8 text-center text-slate-400">
                <CalendarPlus className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                <p className="text-sm font-medium text-slate-500">No days yet</p>
                <p className="text-xs mt-1">Click &ldquo;Add Day&rdquo; to start building your itinerary.</p>
              </div>
            )}
          </div>
        </div>
      </div>

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
  );
}
