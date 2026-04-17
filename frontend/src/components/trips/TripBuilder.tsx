"use client";

import { useState, useCallback, useRef, useEffect } from "react";
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
  CalendarPlus,
  Sparkles,
  Scale,
  Loader2,
  BarChart2,
  CheckCircle2,
  X,
  Zap,
  Star,
  Clock,
  ArrowRight,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import type {
  ItineraryDay,
  ItineraryItem,
  ResearchResult,
  ItemType,
  CompareResult,
} from "@/types";
import {
  createDay,
  deleteItem,
  createItem,
  updateItem,
  compareItems,
  fetchTripItems,
} from "@/lib/api";
import { SearchResultCard } from "./SearchResultCard";
import { ItineraryDayColumn } from "./ItineraryDayColumn";
import { ItineraryItemCard } from "./ItineraryItemCard";
import { CompareModal } from "./CompareModal";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function aiScoreOf(item: ItineraryItem): number {
  return ((item.details as Record<string, unknown>)?.aiScore as number) ?? 0;
}

function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
  } catch {
    return iso;
  }
}

// ─── Recommendation tag badge ─────────────────────────────────────────────────

function RecTag({ tag }: { tag: string }) {
  const style =
    tag === "Points Better" ? "bg-violet-100 text-violet-700" :
    tag === "Best Value"    ? "bg-emerald-100 text-emerald-700" :
    tag === "Great Rating"  ? "bg-amber-100 text-amber-700" :
    tag === "Budget Pick"   ? "bg-teal-100 text-teal-700" :
    "bg-slate-100 text-slate-500";
  const icon =
    tag === "Points Better" ? <Zap className="w-2.5 h-2.5" /> :
    tag === "Best Value"    ? <Star className="w-2.5 h-2.5" /> :
    null;
  return (
    <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-xs font-semibold ${style}`}>
      {icon}{tag}
    </span>
  );
}

// ─── AI score ring ────────────────────────────────────────────────────────────

function AiScoreBadge({ score }: { score: number }) {
  const color =
    score >= 70 ? "text-emerald-600" :
    score >= 50 ? "text-amber-600" :
    "text-slate-500";
  return (
    <div className={`text-center ${color}`}>
      <p className="text-xs text-slate-400">AI Score</p>
      <p className="text-xs font-bold">{Math.round(score)}</p>
    </div>
  );
}

// ─── Flight candidate card ────────────────────────────────────────────────────

function FlightCandidateCard({
  item,
  onAddToItinerary,
  adding,
}: {
  item: ItineraryItem;
  onAddToItinerary: (item: ItineraryItem) => void;
  adding: boolean;
}) {
  const d = (item.details ?? {}) as Record<string, unknown>;
  const airline     = (d.airline      as string) ?? "";
  const flightNum   = (d.flightNumber as string) ?? item.title;
  const origin      = (d.origin       as string) ?? "";
  const destination = (d.destination  as string) ?? "";
  const depTime     = (d.departureTime as string) ?? "";
  const duration    = (d.durationMinutes as number) ?? 0;
  const stops       = (d.stops        as number) ?? 0;
  const price       = (d.price        as number) ?? item.cashPrice ?? 0;
  const points      = (d.pointsCost   as number) ?? item.pointsPrice ?? 0;
  const cpp         = (d.cpp          as number) ?? 0;
  const aiScore     = (d.aiScore      as number) ?? 0;
  const recTag      = (d.recommendationTag as string) ?? "";

  return (
    <div className="border border-slate-200 rounded-xl p-3 bg-white flex flex-col gap-2 hover:border-slate-300 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between gap-1">
        <div>
          <p className="text-xs font-semibold text-slate-800">{airline}</p>
          <p className="text-xs text-slate-400">{flightNum}</p>
        </div>
        <RecTag tag={recTag} />
      </div>

      {/* Route + time */}
      {origin && destination && (
        <div className="flex items-center gap-1.5 text-xs text-slate-600">
          <span className="font-medium">{origin}</span>
          <ArrowRight className="w-3 h-3 text-slate-400 flex-shrink-0" />
          <span className="font-medium">{destination}</span>
          <span className="ml-auto text-slate-400">
            {stops === 0 ? "Nonstop" : `${stops} stop${stops > 1 ? "s" : ""}`}
          </span>
        </div>
      )}

      {depTime && duration > 0 && (
        <div className="flex items-center gap-1 text-xs text-slate-400">
          <Clock className="w-3 h-3" />
          {formatTime(depTime)} · {formatDuration(duration)}
        </div>
      )}

      {/* Pricing row */}
      <div className="flex items-center justify-between pt-1.5 border-t border-slate-100">
        <div className="flex items-center gap-3">
          {price > 0 && (
            <div>
              <p className="text-xs text-slate-400">Cash</p>
              <p className="text-xs font-bold text-slate-800">${Math.round(price)}</p>
            </div>
          )}
          {points > 0 && (
            <div>
              <p className="text-xs text-slate-400">Points</p>
              <p className="text-xs font-bold text-violet-700">
                {points >= 1000 ? `${(points / 1000).toFixed(0)}k` : points}
              </p>
            </div>
          )}
          {cpp > 0 && (
            <div>
              <p className="text-xs text-slate-400">CPP</p>
              <p className={`text-xs font-bold ${cpp >= 2 ? "text-emerald-600" : "text-slate-700"}`}>
                {cpp.toFixed(2)}¢
              </p>
            </div>
          )}
          <AiScoreBadge score={aiScore} />
        </div>
        <button
          onClick={() => onAddToItinerary(item)}
          disabled={adding}
          className="px-2.5 py-1 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
        >
          {adding ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plane className="w-3 h-3" />}
          Add
        </button>
      </div>
    </div>
  );
}

// ─── Hotel candidate card ─────────────────────────────────────────────────────

function HotelCandidateCard({
  item,
  onAddToItinerary,
  adding,
}: {
  item: ItineraryItem;
  onAddToItinerary: (item: ItineraryItem) => void;
  adding: boolean;
}) {
  const d = (item.details ?? {}) as Record<string, unknown>;
  const name         = (d.name         as string) ?? item.title;
  const location     = (d.location     as string) ?? item.location ?? "";
  const pricePerNight = (d.pricePerNight as number) ?? item.cashPrice ?? 0;
  const rating       = (d.rating       as number) ?? null;
  const stars        = (d.stars        as number) ?? null;
  const amenities    = (d.amenities    as string[]) ?? [];
  const aiScore      = (d.aiScore      as number) ?? 0;
  const recTag       = (d.recommendationTag as string) ?? "";
  const nights       = (d.nights       as number) ?? 1;

  return (
    <div className="border border-slate-200 rounded-xl p-3 bg-white flex flex-col gap-2 hover:border-slate-300 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between gap-1">
        <div className="min-w-0">
          <p className="text-xs font-semibold text-slate-800 leading-tight truncate">{name}</p>
          {stars != null && (
            <p className="text-xs text-amber-400">{"★".repeat(Math.round(stars))}</p>
          )}
        </div>
        <RecTag tag={recTag} />
      </div>

      {location && (
        <div className="flex items-center gap-1 text-xs text-slate-500">
          <MapPin className="w-3 h-3 flex-shrink-0" />
          <span className="truncate">{location}</span>
        </div>
      )}

      {/* Pricing + rating */}
      <div className="flex items-center gap-3 pt-1.5 border-t border-slate-100">
        {pricePerNight > 0 && (
          <div>
            <p className="text-xs text-slate-400">Per night</p>
            <p className="text-xs font-bold text-slate-800">${Math.round(pricePerNight)}</p>
          </div>
        )}
        {nights > 1 && pricePerNight > 0 && (
          <div>
            <p className="text-xs text-slate-400">Total</p>
            <p className="text-xs font-bold text-slate-700">${Math.round(pricePerNight * nights)}</p>
          </div>
        )}
        {rating != null && (
          <div>
            <p className="text-xs text-slate-400">Rating</p>
            <p className="text-xs font-bold text-slate-700">★ {rating.toFixed(1)}</p>
          </div>
        )}
        <AiScoreBadge score={aiScore} />
        <button
          onClick={() => onAddToItinerary(item)}
          disabled={adding}
          className="ml-auto px-2.5 py-1 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-xs font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1 flex-shrink-0"
        >
          {adding ? <Loader2 className="w-3 h-3 animate-spin" /> : <Hotel className="w-3 h-3" />}
          Add
        </button>
      </div>

      {amenities.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {amenities.slice(0, 3).map((a) => (
            <span key={a} className="px-1.5 py-0.5 bg-slate-100 rounded text-xs text-slate-500">{a}</span>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Collapsible panel wrapper ────────────────────────────────────────────────

function CandidatePanel({
  title,
  icon,
  count,
  accentColor,
  open,
  onToggle,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  count: number;
  accentColor: string;
  open: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="card p-3 flex flex-col gap-2">
      <button
        onClick={onToggle}
        className="flex items-center justify-between w-full text-sm font-semibold text-slate-700"
      >
        <span className="flex items-center gap-1.5">
          {icon}
          {title}
          <span className={`text-xs font-normal ${accentColor}`}>({count})</span>
        </span>
        {open
          ? <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
          : <ChevronDown className="w-3.5 h-3.5 text-slate-400" />}
      </button>
      {open && count === 0 && (
        <p className="text-xs text-slate-400 py-2 text-center">
          No candidates yet — create a new trip to auto-populate.
        </p>
      )}
      {open && count > 0 && (
        <div className="flex flex-col gap-2 max-h-[420px] overflow-y-auto">
          {children}
        </div>
      )}
    </div>
  );
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface TripBuilderProps {
  tripId: string;
  initialDays: ItineraryDay[];
  initialResults: ResearchResult[];
}

// ─── Main component ───────────────────────────────────────────────────────────

export function TripBuilder({ tripId, initialDays, initialResults }: TripBuilderProps) {
  const [days,        setDays]       = useState<ItineraryDay[]>(initialDays);
  const [results]                    = useState<ResearchResult[]>(initialResults);

  // ── Flight / hotel candidates (trip-level items, AI pre-populated) ───────────
  const [candidateFlights, setCandidateFlights] = useState<ItineraryItem[]>([]);
  const [candidateHotels,  setCandidateHotels]  = useState<ItineraryItem[]>([]);
  const [flightPanelOpen,  setFlightPanelOpen]  = useState(true);
  const [hotelPanelOpen,   setHotelPanelOpen]   = useState(true);
  const [addingId,         setAddingId]         = useState<string | null>(null);
  const [toast,            setToast]            = useState<string | null>(null);
  const [activeId,         setActiveId]         = useState<UniqueIdentifier | null>(null);

  // ── Compare state ────────────────────────────────────────────────────────────
  const [compareSet,     setCompareSet]     = useState<Set<string>>(new Set());
  const [compareOpen,    setCompareOpen]    = useState(false);
  const [compareResults, setCompareResults] = useState<CompareResult[]>([]);
  const [compareLoading, setCompareLoading] = useState(false);
  const compareDataRef = useRef<Map<string, { name: string; itemType: string; cashPrice: number; pointsCost: number; rating?: number }>>(new Map());

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  // Load trip-level items on mount, sort by AI score
  useEffect(() => {
    fetchTripItems(tripId).then((items) => {
      const flights = items
        .filter((i) => i.itemType === "flight")
        .sort((a, b) => aiScoreOf(b) - aiScoreOf(a));
      const hotels = items
        .filter((i) => i.itemType === "hotel")
        .sort((a, b) => aiScoreOf(b) - aiScoreOf(a));
      setCandidateFlights(flights);
      setCandidateHotels(hotels);
    });
  }, [tripId]);

  const showToast = useCallback((msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }, []);

  // ── Add candidate to first itinerary day ─────────────────────────────────────

  const handleAddCandidateToItinerary = useCallback(async (item: ItineraryItem) => {
    setAddingId(item.id);
    try {
      let targetDay = days[0];
      if (!targetDay) {
        targetDay = await createDay(tripId, { dayNumber: 1, title: "Day 1" });
        setDays([targetDay]);
      }

      const newItem = await createItem(tripId, targetDay.id, {
        itemType: item.itemType as ItemType,
        title: item.title,
        description: item.description ?? undefined,
        location: item.location ?? undefined,
        position: targetDay.items.length,
      });

      setDays((prev) =>
        prev.map((d) =>
          d.id === targetDay.id ? { ...d, items: [...d.items, newItem] } : d
        )
      );
      showToast(`${item.itemType === "flight" ? "Flight" : "Hotel"} added to itinerary`);
    } catch {
      showToast("Failed to add — please try again");
    } finally {
      setAddingId(null);
    }
  }, [days, tripId, showToast]);

  // ── Remove item from a day ───────────────────────────────────────────────────

  const handleRemoveItem = useCallback(async (itemId: string, dayId: string) => {
    setDays((prev) =>
      prev.map((d) =>
        d.id === dayId
          ? { ...d, items: d.items.filter((i) => i.id !== itemId).map((i, idx) => ({ ...i, position: idx })) }
          : d
      )
    );
    try { await deleteItem(itemId); } catch { /* silently ignore */ }
  }, []);

  // ── Add empty note to a day ──────────────────────────────────────────────────

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
        prev.map((d) => d.id === dayId ? { ...d, items: [...d.items, newItem] } : d)
      );
    } catch { /* silently ignore */ }
  }, [days, tripId]);

  // ── Add new day ──────────────────────────────────────────────────────────────

  const handleAddDay = useCallback(async () => {
    const nextNum = days.length + 1;
    try {
      const newDay = await createDay(tripId, { dayNumber: nextNum, title: `Day ${nextNum}` });
      setDays((prev) => [...prev, newDay]);
    } catch { /* silently ignore */ }
  }, [days.length, tripId]);

  // ── Add research result by clicking "+" ─────────────────────────────────────

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
        prev.map((d) => d.id === targetDay.id ? { ...d, items: [...d.items, newItem] } : d)
      );
    } catch { /* silently ignore */ }
  }, [days, tripId]);

  // ── Compare ──────────────────────────────────────────────────────────────────

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
    } catch { /* silently ignore */ }
    finally { setCompareLoading(false); }
  }, [compareSet]);

  // ── DnD ──────────────────────────────────────────────────────────────────────

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(event.active.id);
  }, []);

  const handleDragOver = useCallback((event: DragOverEvent) => {
    const { active, over } = event;
    if (!over) return;
    const activeData = active.data.current;
    const overData   = over.data.current;
    if (!activeData || activeData.type !== "itinerary-item") return;

    const sourceItem: ItineraryItem = activeData.item;
    const sourceDayId = sourceItem.dayId;
    let targetDayId: string | null = null;
    if (overData?.type === "itinerary-item") targetDayId = overData.item.dayId;
    else if (overData?.type === "day") targetDayId = overData.dayId;
    else { const s = String(over.id); if (s.startsWith("day-")) targetDayId = s.replace("day-", ""); }
    if (!targetDayId || targetDayId === sourceDayId) return;

    setDays((prev) => {
      const sourceDay = prev.find((d) => d.id === sourceDayId);
      const targetDay = prev.find((d) => d.id === targetDayId);
      if (!sourceDay || !targetDay) return prev;
      return prev.map((d) => {
        if (d.id === sourceDayId) return { ...d, items: d.items.filter((i) => i.id !== sourceItem.id).map((i, idx) => ({ ...i, position: idx })) };
        if (d.id === targetDayId) return { ...d, items: [...d.items, { ...sourceItem, dayId: targetDayId! }].map((i, idx) => ({ ...i, position: idx })) };
        return d;
      });
    });
  }, []);

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    setActiveId(null);
    const { active, over } = event;
    if (!over) return;
    const activeData = active.data.current;
    const overData   = over.data.current;

    if (activeData?.type === "result") {
      const result: ResearchResult = activeData.result;
      let targetDayId: string | null = null;
      if (overData?.type === "day") targetDayId = overData.dayId;
      else if (overData?.type === "itinerary-item") targetDayId = overData.item.dayId;
      else { const s = String(over.id); if (s.startsWith("day-")) targetDayId = s.replace("day-", ""); }
      if (!targetDayId) return;
      const targetDay = days.find((d) => d.id === targetDayId);
      if (!targetDay) return;
      createItem(tripId, targetDayId, {
        itemType: result.category as ItemType,
        title: result.title,
        description: result.description,
        location: result.location,
        position: targetDay.items.length,
        bookingOptions: result.bookingOptions,
      }).then((newItem) => {
        setDays((prev) => prev.map((d) => d.id !== targetDayId ? d : { ...d, items: [...d.items, newItem] }));
      }).catch(() => {});
      return;
    }

    if (activeData?.type === "itinerary-item") {
      const sourceItem: ItineraryItem = activeData.item;
      if (!overData) return;
      const overId = String(over.id);
      const targetDayId =
        overData.type === "itinerary-item" ? overData.item.dayId :
        overData.type === "day" ? overData.dayId :
        overId.startsWith("day-") ? overId.replace("day-", "") : null;
      if (!targetDayId) return;
      if (targetDayId === sourceItem.dayId) {
        setDays((prev) => prev.map((d) => {
          if (d.id !== targetDayId) return d;
          const oldIdx = d.items.findIndex((i) => i.id === sourceItem.id);
          const newIdx = d.items.findIndex((i) => i.id === String(over.id));
          if (oldIdx === -1 || newIdx === -1 || oldIdx === newIdx) return d;
          const reordered = arrayMove(d.items, oldIdx, newIdx).map((i, idx) => ({ ...i, position: idx }));
          reordered.forEach((item) => updateItem(item.id, { position: item.position }).catch(() => {}));
          return { ...d, items: reordered };
        }));
      } else {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        updateItem(sourceItem.id, { dayId: targetDayId } as any).catch(() => {});
      }
    }
  }, [days, tripId]);

  // ── Drag overlay source item ─────────────────────────────────────────────────

  const activeDragItem: ItineraryItem | ResearchResult | null = (() => {
    if (!activeId) return null;
    const idStr = String(activeId);
    if (idStr.startsWith("result-")) {
      return results.find((r) => r.id === idStr.replace("result-", "")) ?? null;
    }
    for (const day of days) {
      const item = day.items.find((i) => i.id === idStr);
      if (item) return item;
    }
    return null;
  })();
  const isResultDrag = activeDragItem !== null && "category" in activeDragItem;

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

          {/* ── Left Panel: AI-ranked candidates ──────────────────────────── */}
          <div className="w-80 flex-shrink-0 flex flex-col gap-3 overflow-y-auto pr-0.5">

            {/* Flights section */}
            <CandidatePanel
              title="Flights"
              icon={<Plane className="w-3.5 h-3.5 text-sky-500" />}
              count={candidateFlights.length}
              accentColor="text-sky-500"
              open={flightPanelOpen}
              onToggle={() => setFlightPanelOpen((v) => !v)}
            >
              {candidateFlights.map((item) => (
                <FlightCandidateCard
                  key={item.id}
                  item={item}
                  onAddToItinerary={handleAddCandidateToItinerary}
                  adding={addingId === item.id}
                />
              ))}
            </CandidatePanel>

            {/* Hotels section */}
            <CandidatePanel
              title="Hotels"
              icon={<Hotel className="w-3.5 h-3.5 text-violet-500" />}
              count={candidateHotels.length}
              accentColor="text-violet-500"
              open={hotelPanelOpen}
              onToggle={() => setHotelPanelOpen((v) => !v)}
            >
              {candidateHotels.map((item) => (
                <HotelCandidateCard
                  key={item.id}
                  item={item}
                  onAddToItinerary={handleAddCandidateToItinerary}
                  adding={addingId === item.id}
                />
              ))}
            </CandidatePanel>

            {/* Activities / research results */}
            {results.length > 0 && (
              <div className="card p-3 flex flex-col gap-2">
                <h2 className="text-sm font-semibold text-slate-700 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-slate-400" />
                  Activities
                </h2>
                <div className="flex flex-col gap-2 max-h-[360px] overflow-y-auto">
                  {results.map((result) => (
                    <SearchResultCard
                      key={result.id}
                      result={result}
                      onAdd={handleAddResult}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* ── Right Panel: Itinerary Timeline ───────────────────────────── */}
          <div className="flex-1 flex flex-col gap-3 overflow-hidden">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-700">
                Itinerary
                <span className="ml-2 text-slate-400 font-normal">
                  {days.reduce((sum, d) => sum + d.items.length, 0)} items across {days.length} day{days.length !== 1 ? "s" : ""}
                </span>
              </h2>
              <button onClick={handleAddDay} className="btn-ghost py-1.5 text-xs">
                <CalendarPlus className="w-3.5 h-3.5" />
                Add Day
              </button>
            </div>

            <div className="flex-1 overflow-y-auto flex flex-col gap-3 pr-0.5">
              <SortableContext items={days.map((d) => d.id)} strategy={verticalListSortingStrategy}>
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
                  <p className="text-xs mt-1">Click &ldquo;Add Day&rdquo; or use &ldquo;Add&rdquo; on a flight or hotel to begin.</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── Compare bar ──────────────────────────────────────────────────── */}
        {compareSet.size > 0 && (
          <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-3 px-5 py-3 bg-slate-900 text-white rounded-2xl shadow-2xl ring-1 ring-white/10">
            <Scale className="w-4 h-4 text-violet-400 flex-shrink-0" />
            <div className="flex items-center gap-1">
              {Array.from({ length: Math.min(compareSet.size, 10) }).map((_, i) => (
                <div key={i} className="w-2 h-2 rounded-full bg-violet-400" />
              ))}
            </div>
            <span className="text-sm font-medium text-slate-200">
              {compareSet.size} item{compareSet.size !== 1 ? "s" : ""}
              {compareSet.size < 2 && <span className="text-slate-400 text-xs ml-1">(need 2+)</span>}
            </span>
            <div className="w-px h-4 bg-slate-700" />
            <button
              onClick={handleCompare}
              disabled={compareSet.size < 2 || compareLoading}
              className="px-4 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed text-sm font-semibold transition-colors flex items-center gap-1.5"
            >
              {compareLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <BarChart2 className="w-3.5 h-3.5" />}
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

        {/* ── Drag Overlay ─────────────────────────────────────────────────── */}
        <DragOverlay>
          {activeDragItem && isResultDrag && (
            <div className="rotate-1 scale-105 shadow-2xl opacity-95 w-72">
              <SearchResultCard result={activeDragItem as ResearchResult} onAdd={() => {}} />
            </div>
          )}
          {activeDragItem && !isResultDrag && (
            <div className="rotate-1 scale-105 shadow-2xl opacity-95">
              <ItineraryItemCard item={activeDragItem as ItineraryItem} onRemove={() => {}} />
            </div>
          )}
        </DragOverlay>
      </DndContext>

      {/* ── Compare Modal ──────────────────────────────────────────────────── */}
      {compareOpen && compareResults.length > 0 && (
        <CompareModal results={compareResults} onClose={() => setCompareOpen(false)} />
      )}

      {/* ── Toast ────────────────────────────────────────────────────────────── */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 bg-slate-900 text-white rounded-xl shadow-2xl ring-1 ring-white/10 text-sm font-medium animate-in fade-in slide-in-from-bottom-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          {toast}
          <button onClick={() => setToast(null)} className="ml-1 text-slate-400 hover:text-slate-200">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </>
  );
}
