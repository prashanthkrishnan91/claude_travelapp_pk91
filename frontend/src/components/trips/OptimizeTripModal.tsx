"use client";

import { useState, useEffect, useCallback } from "react";
import {
  X,
  Sparkles,
  Plane,
  Building2,
  Star,
  ChevronDown,
  ChevronUp,
  Loader2,
  AlertCircle,
  Check,
} from "lucide-react";
import {
  resolveAirports,
  searchFlights,
  searchHotels,
  optimizeTrip,
  addOptimizedFlightToDay,
  addOptimizedHotelToTrip,
  createDay,
} from "@/lib/api";
import type {
  Trip,
  ItineraryDay,
  TripOption,
  OptimizeFlightInput,
  OptimizeHotelInput,
} from "@/types";

interface Props {
  trip: Trip;
  itineraryDays: ItineraryDay[];
  onClose: () => void;
  onPlanSelected: () => void;
}

const RANK_LABELS = ["Best Value", "Runner-Up", "Budget Pick"];
const RANK_BADGE = [
  "bg-emerald-100 text-emerald-700",
  "bg-sky-100 text-sky-700",
  "bg-amber-100 text-amber-700",
];
const RANK_BORDER = [
  "border-emerald-300",
  "border-sky-300",
  "border-amber-300",
];
const RANK_BANNER = ["bg-emerald-50", "bg-sky-50", "bg-amber-50"];

function scoreColor(s: number): string {
  if (s >= 70) return "text-emerald-600";
  if (s >= 50) return "text-amber-600";
  return "text-slate-400";
}

function fmtDuration(mins: number): string {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m ? `${h}h ${m}m` : `${h}h`;
}

export function OptimizeTripModal({ trip, itineraryDays, onClose, onPlanSelected }: Props) {
  const [phase, setPhase] = useState<"loading" | "error" | "results">("loading");
  const [error, setError] = useState("");
  const [options, setOptions] = useState<TripOption[]>([]);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [selecting, setSelecting] = useState<number | null>(null);
  const [selected, setSelected] = useState<number | null>(null);

  const run = useCallback(async () => {
    setPhase("loading");
    setError("");
    try {
      if (!trip.destination) throw new Error("Trip has no destination set.");
      if (!trip.origin) throw new Error("Add an origin city to your trip to find flights.");

      const startDate = trip.startDate ?? new Date().toISOString().slice(0, 10);
      const endDate = trip.endDate ?? new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10);
      const nights = Math.max(
        1,
        Math.round((+new Date(endDate) - +new Date(startDate)) / 86400000)
      );

      const [originRes, destRes] = await Promise.all([
        resolveAirports(trip.origin).catch(() => null),
        resolveAirports(trip.destination).catch(() => null),
      ]);

      const isValidIata = (c: string) => /^[A-Z]{3}$/.test(c);
      const originCodes = (originRes?.matches?.[0]?.airports ?? []).filter(isValidIata).slice(0, 3);
      const destCodes = (destRes?.matches?.[0]?.airports ?? []).filter(isValidIata).slice(0, 3);

      if (!originCodes.length) {
        throw new Error(`Could not find airports for "${trip.origin}". Check your origin city.`);
      }
      if (!destCodes.length) {
        throw new Error(`Could not find airports for "${trip.destination}".`);
      }

      const [rawFlights, rawHotels] = await Promise.all([
        searchFlights(originCodes, destCodes, startDate).catch(() => []),
        searchHotels(trip.destination, startDate, endDate, trip.travelers ?? 1).catch(() => []),
      ]);

      if (!rawFlights.length) throw new Error("No flights found for your route. Try adjusting your dates.");
      if (!rawHotels.length) throw new Error("No hotels found for your destination.");

      const flights: OptimizeFlightInput[] = rawFlights.slice(0, 10).map((f) => ({
        id: f.id,
        airline: f.airline,
        flightNumber: f.flightNumber,
        price: f.price,
        pointsCost: f.pointsCost,
        cpp: f.cpp,
        durationMinutes: f.durationMinutes,
        stops: f.stops,
        cabinClass: f.cabinClass,
        rating: f.rating,
        decision: f.decision ?? "Cash Better",
        tags: f.tags ?? [],
        explanation: f.explanation ?? "",
      }));

      const hotels: OptimizeHotelInput[] = rawHotels.slice(0, 10).map((h) => {
        const meta = (h.metadata ?? {}) as Record<string, unknown>;
        const ppn = (meta.pricePerNight as number) ?? 0;
        return {
          id: h.id,
          name: h.title,
          price: ppn * nights,
          pricePerNight: ppn,
          nights,
          pointsEstimate: 0,
          rating: h.rating,
          stars: meta.stars as number | undefined,
          locationScore: meta.locationScore as number | undefined,
          areaLabel: meta.areaLabel as string | undefined,
          tags: h.tags ?? [],
          explanation: "",
        };
      });

      const resp = await optimizeTrip(flights, hotels);
      setOptions(resp.bestOptions);
      setPhase("results");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Optimization failed. Please try again.");
      setPhase("error");
    }
  }, [trip]);

  useEffect(() => {
    run();
  }, [run]);

  async function handleSelect(opt: TripOption, idx: number) {
    setSelecting(idx);
    try {
      let dayId: string;
      const day1 = itineraryDays.find((d) => d.dayNumber === 1);
      if (day1) {
        dayId = day1.id;
      } else {
        const nd = await createDay(trip.id, {
          dayNumber: 1,
          title: "Day 1",
          date: trip.startDate,
        });
        dayId = nd.id;
      }

      await Promise.all([
        addOptimizedFlightToDay(trip.id, dayId, opt.flight),
        addOptimizedHotelToTrip(trip.id, opt.hotel),
      ]);

      setSelected(idx);
      setTimeout(onPlanSelected, 1000);
    } catch (e) {
      console.error("Failed to add plan:", e);
    } finally {
      setSelecting(null);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-start justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl my-8">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-sky-500" />
            <h2 className="text-base font-semibold text-slate-900">Optimize My Trip</h2>
            {trip.destination && (
              <span className="text-sm text-slate-400">— {trip.destination}</span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-6">
          {/* Loading */}
          {phase === "loading" && (
            <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
              <Loader2 className="w-10 h-10 text-sky-400 animate-spin" />
              <p className="text-sm font-medium text-slate-700">Finding best options…</p>
              <p className="text-xs text-slate-400">Analyzing flights, hotels & rewards value</p>
            </div>
          )}

          {/* Error */}
          {phase === "error" && (
            <div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
              <AlertCircle className="w-8 h-8 text-red-400" />
              <p className="text-sm font-medium text-slate-700">{error}</p>
              <button
                onClick={run}
                className="mt-1 px-4 py-2 text-sm font-medium bg-sky-600 text-white rounded-lg hover:bg-sky-700 transition"
              >
                Try Again
              </button>
            </div>
          )}

          {/* Results */}
          {phase === "results" && options.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {options.map((opt, idx) => (
                <div
                  key={opt.rank}
                  className={`rounded-xl border-2 ${RANK_BORDER[idx]} overflow-hidden flex flex-col`}
                >
                  {/* Rank banner */}
                  <div className={`px-4 py-3 flex items-center justify-between ${RANK_BANNER[idx]}`}>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${RANK_BADGE[idx]}`}>
                      Option {opt.rank} · {RANK_LABELS[idx]}
                    </span>
                    <span className={`text-xl font-bold leading-none ${scoreColor(opt.totalValueScore)}`}>
                      {Math.round(opt.totalValueScore)}
                      <span className="text-xs font-normal text-slate-400 ml-0.5">/100</span>
                    </span>
                  </div>

                  <div className="p-4 flex flex-col gap-3 flex-1">
                    {/* Flight */}
                    <div>
                      <div className="flex items-center gap-1.5 mb-1">
                        <Plane className="w-3.5 h-3.5 text-sky-500" />
                        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest">
                          Flight
                        </span>
                      </div>
                      <p className="text-sm font-semibold text-slate-800">
                        {opt.flight.airline} {opt.flight.flightNumber}
                      </p>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {fmtDuration(opt.flight.durationMinutes)} ·{" "}
                        {opt.flight.stops === 0
                          ? "Nonstop"
                          : `${opt.flight.stops} stop${opt.flight.stops > 1 ? "s" : ""}`}{" "}
                        · {opt.flight.cabinClass}
                      </p>
                      <p className="text-sm font-medium text-slate-700 mt-1">
                        ${opt.flight.price.toLocaleString()}
                        {opt.flight.pointsCost > 0 && (
                          <span className="text-xs text-sky-600 ml-1.5">
                            · {opt.flight.pointsCost.toLocaleString()} pts
                          </span>
                        )}
                      </p>
                    </div>

                    <div className="h-px bg-slate-100" />

                    {/* Hotel */}
                    <div>
                      <div className="flex items-center gap-1.5 mb-1">
                        <Building2 className="w-3.5 h-3.5 text-violet-500" />
                        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest">
                          Hotel
                        </span>
                      </div>
                      <p className="text-sm font-semibold text-slate-800 line-clamp-1">{opt.hotel.name}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        {opt.hotel.rating != null && (
                          <span className="flex items-center gap-0.5 text-xs text-amber-600">
                            <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                            {opt.hotel.rating.toFixed(1)}
                          </span>
                        )}
                        {opt.hotel.areaLabel && (
                          <span className="text-xs text-slate-400">{opt.hotel.areaLabel}</span>
                        )}
                      </div>
                      <p className="text-sm font-medium text-slate-700 mt-1">
                        ${opt.hotel.pricePerNight.toLocaleString()}/night · {opt.hotel.nights}n
                      </p>
                    </div>

                    {/* Expanded score breakdown */}
                    {expanded === idx && (
                      <>
                        <div className="h-px bg-slate-100" />
                        <div className="grid grid-cols-3 gap-2 text-center">
                          {[
                            { label: "Flight", score: opt.flightScore },
                            { label: "Hotel", score: opt.hotelScore },
                            { label: "Rewards", score: opt.rewardsEfficiency },
                          ].map(({ label, score }) => (
                            <div
                              key={label}
                              className="rounded-lg bg-slate-50 border border-slate-100 p-2"
                            >
                              <p className="text-[10px] text-slate-400">{label}</p>
                              <p className={`text-sm font-bold ${scoreColor(score)}`}>
                                {Math.round(score)}
                              </p>
                            </div>
                          ))}
                        </div>
                        {opt.flight.explanation && (
                          <p className="text-xs text-slate-500 leading-relaxed italic">
                            {opt.flight.explanation}
                          </p>
                        )}
                      </>
                    )}

                    <div className="h-px bg-slate-100" />

                    {/* Totals + summary */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-slate-400">Total cost</span>
                        <span className="text-sm font-bold text-slate-900">
                          ${opt.totalCost.toLocaleString()}
                        </span>
                      </div>
                      {opt.totalPoints > 0 && (
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-slate-400">Points used</span>
                          <span className="text-xs font-semibold text-sky-600">
                            {opt.totalPoints.toLocaleString()} pts
                          </span>
                        </div>
                      )}
                      <p className="text-xs text-slate-500 italic leading-relaxed pt-1">
                        {opt.summary}
                      </p>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="px-4 pb-4 flex flex-col gap-2">
                    <button
                      onClick={() => handleSelect(opt, idx)}
                      disabled={selecting !== null || selected !== null}
                      className={`w-full py-2 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition ${
                        selected === idx
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-sky-600 text-white hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      }`}
                    >
                      {selecting === idx ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Adding…
                        </>
                      ) : selected === idx ? (
                        <>
                          <Check className="w-4 h-4" />
                          Added to Itinerary
                        </>
                      ) : (
                        "Select This Plan"
                      )}
                    </button>
                    <button
                      onClick={() => setExpanded(expanded === idx ? null : idx)}
                      className="w-full py-1.5 rounded-lg text-xs text-slate-500 hover:bg-slate-50 border border-slate-200 flex items-center justify-center gap-1 transition"
                    >
                      {expanded === idx ? (
                        <>
                          <ChevronUp className="w-3.5 h-3.5" />
                          Hide Details
                        </>
                      ) : (
                        <>
                          <ChevronDown className="w-3.5 h-3.5" />
                          View Details
                        </>
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
