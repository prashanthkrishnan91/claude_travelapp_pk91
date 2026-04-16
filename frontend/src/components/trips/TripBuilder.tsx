"use client";

import { useState, useCallback, useRef, useEffect, useMemo } from "react";
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
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  Clock,
  X,
  AlertCircle,
  Zap,
} from "lucide-react";
import type { ItineraryDay, ItineraryItem, ResearchResult, ResearchCategory, ItemType, CompareResult, FlightSearchResult } from "@/types";
import {
  createDay,
  deleteItem,
  createItem,
  updateItem,
  compareItems,
  searchFlights,
  searchHotels,
  addFlightToTrip,
  addHotelToTrip,
  fetchTripItems,
} from "@/lib/api";
import { CityAutocomplete } from "@/components/ui/CityAutocomplete";
import type { AirportSelection } from "@/components/ui/CityAutocomplete";
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
  tripOrigin?: string;
  tripDestination?: string;
}

// ─── Main component ───────────────────────────────────────────────────────────

export function TripBuilder({ tripId, initialDays, initialResults, tripOrigin = "", tripDestination = "" }: TripBuilderProps) {
  const [days,          setDays]         = useState<ItineraryDay[]>(initialDays);
  const [results]                        = useState<ResearchResult[]>(initialResults);
  const [activeFilter,  setActiveFilter] = useState<ResearchCategory | "all">("all");
  const [searchQuery,   setSearchQuery]  = useState("");
  const [activeId,      setActiveId]     = useState<UniqueIdentifier | null>(null);

  // ── Flight search state ─────────────────────────────────────────────────────
  const [flightPanelOpen,   setFlightPanelOpen]   = useState(true);
  const [flightOriginSel,   setFlightOriginSel]   = useState<AirportSelection | null>(null);
  const [flightDestSel,     setFlightDestSel]     = useState<AirportSelection | null>(null);
  const [flightDate,        setFlightDate]        = useState("");
  const [flightResults,     setFlightResults]     = useState<FlightSearchResult[]>([]);
  const [flightLoading,     setFlightLoading]     = useState(false);
  const [savedFlights,      setSavedFlights]      = useState<ItineraryItem[]>([]);
  const [savedHotels,       setSavedHotels]       = useState<ItineraryItem[]>([]);
  const [addingFlight,      setAddingFlight]      = useState<string | null>(null);
  const [flightError,       setFlightError]       = useState<string | null>(null);
  const [flightSearched,    setFlightSearched]    = useState(false);
  const [toast,             setToast]             = useState<string | null>(null);

  // ── Hotel search state ───────────────────────────────────────────────────────
  const [hotelPanelOpen,    setHotelPanelOpen]    = useState(true);
  const [hotelDestination,  setHotelDestination]  = useState("");
  const [hotelCheckIn,      setHotelCheckIn]      = useState("");
  const [hotelCheckOut,     setHotelCheckOut]     = useState("");
  const [hotelGuests,       setHotelGuests]       = useState(1);
  const [hotelResults,      setHotelResults]      = useState<ResearchResult[]>([]);
  const [hotelLoading,      setHotelLoading]      = useState(false);
  const [hotelError,        setHotelError]        = useState<string | null>(null);
  const [hotelSearched,     setHotelSearched]     = useState(false);
  const [addingHotel,       setAddingHotel]       = useState<string | null>(null);

  // ── Sort state ───────────────────────────────────────────────────────────────
  const [flightSortKey,     setFlightSortKey]     = useState<"price" | "cpp" | "duration">("price");
  const [hotelSortKey,      setHotelSortKey]      = useState<"price" | "rating" | "value">("price");

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

  // Fetch saved flights and hotels on mount
  useEffect(() => {
    fetchTripItems(tripId).then((items) => {
      console.log("[TripBuilder] fetched trip items:", items);
      setSavedFlights(items.filter((i) => i.itemType === "flight"));
      setSavedHotels(items.filter((i) => i.itemType === "hotel"));
    });
  }, [tripId]);

  // Pre-fill flight selections from trip props when they are valid IATA codes
  useEffect(() => {
    if (/^[A-Za-z]{3}$/.test(tripOrigin)) {
      setFlightOriginSel({ city: tripOrigin.toUpperCase(), country: "", airports: [tripOrigin.toUpperCase()] });
    }
    if (/^[A-Za-z]{3}$/.test(tripDestination)) {
      setFlightDestSel({ city: tripDestination.toUpperCase(), country: "", airports: [tripDestination.toUpperCase()] });
    }
  }, [tripOrigin, tripDestination]);

  const showToast = useCallback((msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }, []);

  const handleFlightSearch = useCallback(async () => {
    if (!flightOriginSel || !flightDestSel || !flightDate) return;
    const totalRoutes = flightOriginSel.airports.length * flightDestSel.airports.length;
    setFlightLoading(true);
    setFlightResults([]);
    setFlightError(null);
    setFlightSearched(false);
    try {
      const results = await searchFlights(flightOriginSel.airports, flightDestSel.airports, flightDate);
      setFlightResults(results);
      setFlightSearched(true);
      if (totalRoutes > 1) {
        showToast(`Searched ${totalRoutes} routes — ${results.length} flights found`);
      }
    } catch (err) {
      setFlightError(err instanceof Error ? err.message : "Search failed — please try again");
    } finally {
      setFlightLoading(false);
    }
  }, [flightOriginSel, flightDestSel, flightDate, showToast]);

  const handleAddFlightToTrip = useCallback(async (flight: FlightSearchResult) => {
    setAddingFlight(flight.id);
    try {
      const saved = await addFlightToTrip(tripId, flight);
      setSavedFlights((prev) => [...prev, saved]);
      showToast("Flight added to trip");
    } catch {
      showToast("Failed to add flight — please try again");
    } finally {
      setAddingFlight(null);
    }
  }, [tripId, showToast]);

  const handleHotelSearch = useCallback(async () => {
    if (!hotelDestination || !hotelCheckIn || !hotelCheckOut) return;
    setHotelLoading(true);
    setHotelResults([]);
    setHotelError(null);
    setHotelSearched(false);
    try {
      const results = await searchHotels(hotelDestination, hotelCheckIn, hotelCheckOut, hotelGuests);
      setHotelResults(results);
      setHotelSearched(true);
    } catch (err) {
      setHotelError(err instanceof Error ? err.message : "Search failed — please try again");
    } finally {
      setHotelLoading(false);
    }
  }, [hotelDestination, hotelCheckIn, hotelCheckOut, hotelGuests]);

  const handleAddHotelFromSearch = useCallback(async (hotel: ResearchResult) => {
    setAddingHotel(hotel.id);
    try {
      await addHotelToTrip(tripId, hotel);
      showToast("Hotel added to trip");
      const items = await fetchTripItems(tripId);
      setSavedHotels(items.filter((i) => i.itemType === "hotel"));
    } catch {
      showToast("Failed to add hotel — please try again");
    } finally {
      setAddingHotel(null);
    }
  }, [tripId, showToast]);

  // ── Sorted results ───────────────────────────────────────────────────────────

  const sortedFlightResults = useMemo(() => {
    const arr = [...flightResults];
    if (flightSortKey === "price")    arr.sort((a, b) => (a.price ?? 0) - (b.price ?? 0));
    if (flightSortKey === "cpp")      arr.sort((a, b) => (b.cpp ?? 0) - (a.cpp ?? 0));
    if (flightSortKey === "duration") arr.sort((a, b) => (a.durationMinutes ?? 0) - (b.durationMinutes ?? 0));
    return arr;
  }, [flightResults, flightSortKey]);

  const sortedHotelResults = useMemo(() => {
    const arr = [...hotelResults];
    if (hotelSortKey === "price") {
      arr.sort((a, b) => ((a.metadata?.pricePerNight as number) ?? 0) - ((b.metadata?.pricePerNight as number) ?? 0));
    }
    if (hotelSortKey === "rating") {
      arr.sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0));
    }
    if (hotelSortKey === "value") {
      const score = (r: ResearchResult) => (r.rating ?? 0) * 100 / (((r.metadata?.pricePerNight as number) ?? 0) || 100);
      arr.sort((a, b) => score(b) - score(a));
    }
    return arr;
  }, [hotelResults, hotelSortKey]);

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
    if (result.category === "hotel") {
      try {
        await addHotelToTrip(tripId, result);
        showToast("Hotel added to trip");
        // Refetch all trip items to update the saved hotels list
        const items = await fetchTripItems(tripId);
        console.log("[TripBuilder] refetched trip items after hotel add:", items);
        setSavedHotels(items.filter((i) => i.itemType === "hotel"));
      } catch {
        showToast("Failed to add hotel — please try again");
      }
      return;
    }

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
  }, [days, tripId, showToast]);

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

          {/* Flight Search Panel */}
          <div className="card p-3 flex flex-col gap-2">
            <button
              onClick={() => setFlightPanelOpen((v) => !v)}
              className="flex items-center justify-between w-full text-sm font-semibold text-slate-700"
            >
              <span className="flex items-center gap-1.5">
                <Plane className="w-3.5 h-3.5 text-sky-500" />
                Search Flights
              </span>
              {flightPanelOpen ? <ChevronUp className="w-3.5 h-3.5 text-slate-400" /> : <ChevronDown className="w-3.5 h-3.5 text-slate-400" />}
            </button>

            {flightPanelOpen && (
              <div className="flex flex-col gap-2 pt-1">
                <CityAutocomplete
                  placeholder="From city or airport…"
                  value={flightOriginSel}
                  onChange={setFlightOriginSel}
                  inputClassName="py-1.5 text-xs"
                />
                <CityAutocomplete
                  placeholder="To city or airport…"
                  value={flightDestSel}
                  onChange={setFlightDestSel}
                  inputClassName="py-1.5 text-xs"
                />
                <input
                  type="date"
                  value={flightDate}
                  onChange={(e) => setFlightDate(e.target.value)}
                  className="input py-1.5 text-xs"
                />
                {flightOriginSel && flightDestSel &&
                  (flightOriginSel.airports.length > 1 || flightDestSel.airports.length > 1) && (
                  <p className="text-xs text-sky-600 flex items-center gap-1">
                    <Plane className="w-3 h-3" />
                    {`Searching ${flightOriginSel.airports.length * flightDestSel.airports.length} routes`}
                  </p>
                )}
                <button
                  onClick={handleFlightSearch}
                  disabled={!flightOriginSel || !flightDestSel || !flightDate || flightLoading}
                  className="btn-primary py-1.5 text-xs disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {flightLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
                  {flightLoading
                    ? (flightOriginSel && flightDestSel && flightOriginSel.airports.length * flightDestSel.airports.length > 1)
                      ? `Searching ${flightOriginSel.airports.length * flightDestSel.airports.length} routes…`
                      : "Searching…"
                    : "Search Flights"}
                </button>

                {/* Error state */}
                {flightError && (
                  <div className="flex items-start gap-1.5 p-2.5 rounded-lg bg-rose-50 text-rose-700 text-xs">
                    <AlertCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                    {flightError}
                  </div>
                )}

                {/* Empty state after a completed search */}
                {flightSearched && !flightLoading && !flightError && flightResults.length === 0 && (
                  <div className="py-4 text-center text-slate-400">
                    <Plane className="w-5 h-5 mx-auto mb-1 opacity-40" />
                    <p className="text-xs">No flights found for this route.</p>
                  </div>
                )}

                {/* Flight sort controls */}
                {flightResults.length > 0 && (
                  <div className="flex items-center gap-1 flex-wrap">
                    <span className="text-xs text-slate-400 mr-0.5">Sort:</span>
                    {(["price", "cpp", "duration"] as const).map((key) => (
                      <button
                        key={key}
                        onClick={() => setFlightSortKey(key)}
                        className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${flightSortKey === key ? "bg-sky-600 text-white" : "bg-slate-100 text-slate-500 hover:bg-slate-200"}`}
                      >
                        {key === "price" ? "Lowest Price" : key === "cpp" ? "Best CPP" : "Shortest"}
                      </button>
                    ))}
                  </div>
                )}

                {/* Flight result cards */}
                {sortedFlightResults.length > 0 && (
                  <div className="flex flex-col gap-2 max-h-[480px] overflow-y-auto pt-1">
                    {sortedFlightResults.map((flight) => (
                      <div key={flight.id} className="border border-slate-200 rounded-lg p-2.5 bg-white flex flex-col gap-1.5">
                        {/* Header: airline + value badge */}
                        <div className="flex items-center justify-between">
                          <div>
                            <span className="text-xs font-semibold text-slate-700">{flight.airline}</span>
                            <span className="ml-1.5 text-xs text-slate-400">{flight.flightNumber}</span>
                          </div>
                          {flight.recommendationTag && (
                            <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-xs font-semibold ${flight.recommendationTag === "Good Points Value" ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                              {flight.recommendationTag === "Good Points Value" && <Zap className="w-2.5 h-2.5" />}
                              {flight.recommendationTag}
                            </span>
                          )}
                        </div>
                        {/* Route + timing */}
                        <div className="flex items-center gap-1 text-xs text-slate-500">
                          <span className="font-medium">{flight.origin}</span>
                          <span>→</span>
                          <span className="font-medium">{flight.destination}</span>
                          <span className="ml-auto">{flight.stops === 0 ? "Nonstop" : `${flight.stops} stop${flight.stops > 1 ? "s" : ""}`}</span>
                        </div>
                        <div className="flex items-center gap-1 text-xs text-slate-400">
                          <Clock className="w-3 h-3" />
                          <span>{flight.departureTime ? new Date(flight.departureTime).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "N/A"}</span>
                          <span>·</span>
                          <span>{Math.floor(flight.durationMinutes / 60)}h {flight.durationMinutes % 60}m</span>
                        </div>
                        {/* Pricing row: cash / points / CPP */}
                        <div className="flex items-center justify-between pt-0.5 border-t border-slate-100">
                          <div className="flex items-center gap-2.5">
                            <div>
                              <p className="text-xs text-slate-400">Cash</p>
                              <p className="text-xs font-semibold text-slate-800">${flight.price}</p>
                            </div>
                            {flight.pointsCost > 0 && (
                              <div>
                                <p className="text-xs text-slate-400">Points</p>
                                <p className="text-xs font-semibold text-violet-700">{flight.pointsCost.toLocaleString()} pts</p>
                              </div>
                            )}
                            {flight.cpp > 0 && (
                              <div>
                                <p className="text-xs text-slate-400">CPP</p>
                                <p className={`text-xs font-semibold ${flight.cpp >= 2 ? "text-emerald-600" : "text-slate-700"}`}>{flight.cpp.toFixed(2)}¢</p>
                              </div>
                            )}
                          </div>
                          <button
                            onClick={() => handleAddFlightToTrip(flight)}
                            disabled={addingFlight === flight.id}
                            className="px-2.5 py-1 rounded-md bg-sky-600 hover:bg-sky-500 text-white text-xs font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                          >
                            {addingFlight === flight.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plane className="w-3 h-3" />}
                            Add to Trip
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Hotel Search Panel */}
          <div className="card p-3 flex flex-col gap-2">
            <button
              onClick={() => setHotelPanelOpen((v) => !v)}
              className="flex items-center justify-between w-full text-sm font-semibold text-slate-700"
            >
              <span className="flex items-center gap-1.5">
                <Hotel className="w-3.5 h-3.5 text-violet-500" />
                Search Hotels
              </span>
              {hotelPanelOpen ? <ChevronUp className="w-3.5 h-3.5 text-slate-400" /> : <ChevronDown className="w-3.5 h-3.5 text-slate-400" />}
            </button>

            {hotelPanelOpen && (
              <div className="flex flex-col gap-2 pt-1">
                <input
                  type="text"
                  placeholder="Destination city…"
                  value={hotelDestination}
                  onChange={(e) => setHotelDestination(e.target.value)}
                  className="input py-1.5 text-xs"
                />
                <div className="flex gap-1.5">
                  <div className="flex-1">
                    <label className="text-xs text-slate-400 mb-0.5 block">Check-in</label>
                    <input
                      type="date"
                      value={hotelCheckIn}
                      onChange={(e) => setHotelCheckIn(e.target.value)}
                      className="input py-1.5 text-xs w-full"
                    />
                  </div>
                  <div className="flex-1">
                    <label className="text-xs text-slate-400 mb-0.5 block">Check-out</label>
                    <input
                      type="date"
                      value={hotelCheckOut}
                      onChange={(e) => setHotelCheckOut(e.target.value)}
                      className="input py-1.5 text-xs w-full"
                    />
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-xs text-slate-500">Guests:</label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={hotelGuests}
                    onChange={(e) => setHotelGuests(Math.max(1, parseInt(e.target.value) || 1))}
                    className="input py-1.5 text-xs w-20"
                  />
                </div>
                <button
                  onClick={handleHotelSearch}
                  disabled={!hotelDestination || !hotelCheckIn || !hotelCheckOut || hotelLoading}
                  className="btn-primary py-1.5 text-xs disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {hotelLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
                  {hotelLoading ? "Searching…" : "Search Hotels"}
                </button>

                {hotelError && (
                  <div className="flex items-start gap-1.5 p-2.5 rounded-lg bg-rose-50 text-rose-700 text-xs">
                    <AlertCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                    {hotelError}
                  </div>
                )}

                {hotelSearched && !hotelLoading && !hotelError && hotelResults.length === 0 && (
                  <div className="py-4 text-center text-slate-400">
                    <Hotel className="w-5 h-5 mx-auto mb-1 opacity-40" />
                    <p className="text-xs">No hotels found for this destination.</p>
                  </div>
                )}

                {/* Hotel sort controls */}
                {hotelResults.length > 0 && (
                  <div className="flex items-center gap-1 flex-wrap">
                    <span className="text-xs text-slate-400 mr-0.5">Sort:</span>
                    {(["price", "rating", "value"] as const).map((key) => (
                      <button
                        key={key}
                        onClick={() => setHotelSortKey(key)}
                        className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${hotelSortKey === key ? "bg-violet-600 text-white" : "bg-slate-100 text-slate-500 hover:bg-slate-200"}`}
                      >
                        {key === "price" ? "Price" : key === "rating" ? "Rating" : "Value"}
                      </button>
                    ))}
                  </div>
                )}

                {/* Hotel result cards */}
                {sortedHotelResults.length > 0 && (
                  <div className="flex flex-col gap-2 max-h-[480px] overflow-y-auto pt-1">
                    {sortedHotelResults.map((hotel) => {
                      const pricePerNight = hotel.metadata?.pricePerNight as number | undefined;
                      const stars = hotel.metadata?.stars as number | undefined;
                      const amenities = hotel.metadata?.amenities as string[] | undefined;
                      const valueScore = (hotel.rating ?? 0) > 0 && pricePerNight
                        ? ((hotel.rating! * 100) / pricePerNight).toFixed(2)
                        : null;
                      return (
                        <div key={hotel.id} className="border border-slate-200 rounded-lg p-2.5 bg-white flex flex-col gap-1.5">
                          <div className="flex items-start justify-between gap-1">
                            <span className="text-xs font-semibold text-slate-700 leading-tight">{hotel.title}</span>
                            {stars != null && (
                              <span className="text-xs text-amber-500 flex-shrink-0">{"★".repeat(Math.round(stars))}</span>
                            )}
                          </div>
                          {hotel.location && (
                            <div className="flex items-center gap-1 text-xs text-slate-500">
                              <MapPin className="w-3 h-3 flex-shrink-0" />
                              <span>{hotel.location}</span>
                            </div>
                          )}
                          <div className="flex items-center gap-2.5 pt-0.5 border-t border-slate-100">
                            {pricePerNight != null && (
                              <div>
                                <p className="text-xs text-slate-400">Price/night</p>
                                <p className="text-xs font-semibold text-slate-800">${pricePerNight}</p>
                              </div>
                            )}
                            {hotel.rating != null && (
                              <div>
                                <p className="text-xs text-slate-400">Rating</p>
                                <p className="text-xs font-semibold text-slate-700">★ {hotel.rating}</p>
                              </div>
                            )}
                            {valueScore && (
                              <div>
                                <p className="text-xs text-slate-400">Value</p>
                                <p className="text-xs font-semibold text-emerald-600">{valueScore}</p>
                              </div>
                            )}
                          </div>
                          {amenities && amenities.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {amenities.slice(0, 3).map((a) => (
                                <span key={a} className="px-1.5 py-0.5 bg-slate-100 rounded text-xs text-slate-500">{a}</span>
                              ))}
                            </div>
                          )}
                          <button
                            onClick={() => handleAddHotelFromSearch(hotel)}
                            disabled={addingHotel === hotel.id}
                            className="mt-0.5 px-2.5 py-1 rounded-md bg-violet-600 hover:bg-violet-500 text-white text-xs font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1 self-end"
                          >
                            {addingHotel === hotel.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Hotel className="w-3 h-3" />}
                            Add to Trip
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>

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
              {(() => {
                const allItems = days.flatMap((d) => d.items);
                console.log("[TripBuilder] rendering itinerary days:", days.length, "total items:", allItems.length, allItems);
                return null;
              })()}
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

            {/* Saved Hotels Section */}
            {savedHotels.length > 0 && (
              <div className="card p-3 flex flex-col gap-2">
                <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-1.5">
                  <Hotel className="w-3.5 h-3.5 text-violet-500" />
                  Saved Hotels
                  <span className="ml-1 text-xs font-normal text-slate-400">({savedHotels.length})</span>
                </h3>
                <div className="flex flex-col gap-2">
                  {savedHotels.map((hotel) => {
                    const d = (hotel.details ?? {}) as Record<string, unknown>;
                    const name     = (d.name     as string) ?? hotel.title;
                    const location = (d.location as string) ?? hotel.location ?? "";
                    const price    = (d.pricePerNight as number) ?? hotel.cashPrice ?? null;
                    const rating   = (d.rating   as number) ?? null;
                    console.log("[TripBuilder] rendering hotel item:", hotel.id, { name, location, price, rating });
                    return (
                      <div key={hotel.id} className="flex items-center justify-between rounded-lg border border-slate-200 bg-violet-50 px-3 py-2">
                        <div className="flex flex-col gap-0.5">
                          <span className="text-xs font-semibold text-slate-700">{name}</span>
                          {location && (
                            <span className="text-xs text-slate-500">{location}</span>
                          )}
                          <span className="text-xs text-slate-400">
                            {rating != null && <span className="mr-2">★ {rating}</span>}
                            {price != null && <span className="font-medium text-slate-600">${price}/night</span>}
                          </span>
                        </div>
                        <CheckCircle2 className="w-4 h-4 text-violet-500 flex-shrink-0" />
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Saved Flights Section */}
            {savedFlights.length > 0 && (
              <div className="card p-3 flex flex-col gap-2">
                <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-1.5">
                  <Plane className="w-3.5 h-3.5 text-sky-500" />
                  Saved Flights
                  <span className="ml-1 text-xs font-normal text-slate-400">({savedFlights.length})</span>
                </h3>
                <div className="flex flex-col gap-2">
                  {savedFlights.map((flight) => {
                    const d = (flight.details ?? {}) as Record<string, unknown>;
                    const origin      = (d.origin      as string) ?? "";
                    const destination = (d.destination as string) ?? "";
                    const depTime     = (d.departureTime as string) ?? flight.startTime ?? "";
                    const airline     = (d.airline     as string) ?? "";
                    const flightNum   = (d.flightNumber as string) ?? "";
                    const stops       = (d.stops       as number) ?? 0;
                    return (
                      <div key={flight.id} className="flex items-center justify-between rounded-lg border border-slate-200 bg-sky-50 px-3 py-2">
                        <div className="flex flex-col gap-0.5">
                          <span className="text-xs font-semibold text-slate-700">
                            {airline} {flightNum}
                          </span>
                          <span className="text-xs text-slate-500">
                            {origin} → {destination}
                            {depTime && (
                              <span className="ml-1.5 text-slate-400">
                                {new Date(depTime).toLocaleDateString([], { month: "short", day: "numeric" })}
                              </span>
                            )}
                          </span>
                          <span className="text-xs text-slate-400">
                            {stops === 0 ? "Nonstop" : `${stops} stop`}
                            {flight.cashPrice && <span className="ml-2 font-medium text-slate-600">${flight.cashPrice}</span>}
                          </span>
                        </div>
                        <CheckCircle2 className="w-4 h-4 text-sky-500 flex-shrink-0" />
                      </div>
                    );
                  })}
                </div>
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

    {/* ── Toast notification ───────────────────────────────────────────────── */}
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
