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
  Crown,
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
  FlightSearchResult,
  ResearchResult,
  BookingOption,
} from "@/types";

// Sentinel host stamped into every `_mock_*` booking URL on the backend.
// Any URL containing this host is, by construction, fabricated.
const MOCK_BOOKING_HOST = "book.example.com";

function hasMockBookingUrl(
  url: string | undefined,
  options: BookingOption[] | undefined,
): boolean {
  if (url && url.includes(MOCK_BOOKING_HOST)) return true;
  if (options) {
    for (const opt of options) {
      if (opt?.url && opt.url.includes(MOCK_BOOKING_HOST)) return true;
    }
  }
  return false;
}

function anyMockDerivedFlights(flights: FlightSearchResult[]): boolean {
  return flights.some((f) => hasMockBookingUrl(f.bookingUrl, f.bookingOptions));
}

function anyMockDerivedHotels(hotels: ResearchResult[]): boolean {
  return hotels.some((h) => hasMockBookingUrl(h.bookingUrl, h.bookingOptions));
}

// Hotels Product Contract v1 — a hotel row carries a true nightly rate
// when ``metadata.hasRealRate === true`` AND ``metadata.pricePerNight``
// is a positive number.  Discovery-only rows (e.g. Google Places
// lodging) MUST be excluded from priced package optimization, otherwise
// ``optimizeTrip()`` would build packages with $0/night hotels.
export function hotelHasRealRate(hotel: ResearchResult): boolean {
  const meta = (hotel.metadata ?? {}) as Record<string, unknown>;
  const ppn = meta.pricePerNight;
  return (
    meta.hasRealRate === true &&
    typeof ppn === "number" &&
    ppn > 0
  );
}

export function anyHotelHasRealRate(hotels: ResearchResult[]): boolean {
  return hotels.some(hotelHasRealRate);
}

interface Props {
  trip: Trip;
  itineraryDays: ItineraryDay[];
  onClose: () => void;
  onPlanSelected: () => void;
}

// Provider-unavailable copy. Used when /search/flights or /search/hotels
// returns no results — currently the dominant case while flights/hotels
// search is not yet provider-backed (Fail-Closed UX v1). Do NOT suggest
// the user adjust dates: dates are not the problem.
const PROVIDER_UNAVAILABLE_TITLE =
  "Flights & hotels search is temporarily unavailable";
const PROVIDER_UNAVAILABLE_BODY =
  "Provider-backed flight and hotel search is not enabled yet. You can still build the trip manually and add details later.";

const RANK_LABELS = ["Best Value", "Runner-Up", "Budget Pick"];
const RANK_BADGE = [
  "text-ds-accent",
  "text-ds-text-secondary",
  "text-ds-text-tertiary",
];
const RANK_BORDER = [
  "border-ds-accent",
  "border-ds-pen-stroke",
  "border-ds-pen-stroke",
];
const RANK_GLOW = [
  "boutique-instrument",
  "boutique-folio",
  "",
];

function scoreColor(s: number): string {
  if (s >= 70) return "text-ds-trust";
  if (s >= 50) return "text-ds-caution";
  return "text-ds-text-tertiary";
}

function fmtDuration(mins: number): string {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m ? `${h}h ${m}m` : `${h}h`;
}

export function OptimizeTripModal({ trip, itineraryDays, onClose, onPlanSelected }: Props) {
  const [phase, setPhase] = useState<"loading" | "error" | "provider_unavailable" | "results">("loading");
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

      if (!rawFlights.length || !rawHotels.length) {
        // Fail-Closed UX v1: empty flight/hotel results almost always mean
        // provider-backed search is not yet enabled (BLOCK_LEGACY_PRODUCT_MOCK
        // on, or the route returned []). Surface honest copy instead of
        // suggesting the user "adjust dates" — that is misleading here.
        setPhase("provider_unavailable");
        return;
      }

      // Mock-derived persistence guard: if /search/flights or /search/hotels
      // returns rows whose booking URLs come from the legacy `_mock_*`
      // fixtures (`book.example.com`), refuse to surface them as Selectable
      // plans. Backend `/trips/create-with-search` is fully protected by the
      // `_any_mock_derived` guard; this client-side check makes sure
      // `addOptimizedFlightToDay` / `addOptimizedHotelToTrip` (which use
      // separate persistence routes) never receive mock-derived rows either.
      // Note: `FlightSearchResult` / `RawHotelResult` don't expose `source`
      // today, so we rely on the booking-URL host signal. While
      // `BLOCK_LEGACY_PRODUCT_MOCK` remains the operator-side gate, this
      // guard hardens the UX path.
      if (anyMockDerivedFlights(rawFlights) || anyMockDerivedHotels(rawHotels)) {
        setPhase("provider_unavailable");
        return;
      }

      // Hotels Product Contract v1: refuse to call ``optimizeTrip`` with
      // discovery-only hotel rows.  Google Places lodging discovery has
      // no true nightly rate, so a priced package built from those rows
      // would show $0/night hotels — misleading.  Wait for Hotels v2
      // (Booking.com Demand API or Amadeus Hotels) before priced
      // package optimization is honest.
      if (!anyHotelHasRealRate(rawHotels)) {
        setPhase("provider_unavailable");
        return;
      }

      // Drop any discovery-only rows from the optimizer input so a
      // mixed batch (some priced, some discovery) cannot mix $0/night
      // entries into the ranked packages.
      const pricedHotels = rawHotels.filter(hotelHasRealRate);

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

      const hotels: OptimizeHotelInput[] = pricedHotels.slice(0, 10).map((h) => {
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
    <div className="fixed inset-0 bg-black/60 z-50 flex items-start justify-center p-4 overflow-y-auto">
      {/* Modal shell — boutique atelier dark surface */}
      <div
        data-testid="optimize-trip-modal"
        className="advisor-desk-panel w-full max-w-4xl my-8"
      >
        {/* Header — two-zone desk header */}
        <div className="concierge-desk-header flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-ds-accent" />
            <h2 className="text-base font-semibold text-ds-text">Optimize My Trip</h2>
            {trip.destination && (
              <span className="text-sm text-ds-text-tertiary">— {trip.destination}</span>
            )}
          </div>
          <button
            onClick={onClose}
            aria-label="Close optimize modal"
            className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg hover:bg-ds-pen-stroke text-ds-text-tertiary transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-6">
          {/* Loading — atelier search state, not sky-blue spinner */}
          {phase === "loading" && (
            <div
              data-testid="optimize-loading-state"
              className="flex flex-col items-center justify-center py-16 gap-3 text-center"
            >
              <Loader2 className="w-10 h-10 text-ds-accent animate-spin" />
              <p className="text-sm font-medium text-ds-text-secondary">Finding best options…</p>
              <p className="text-xs text-ds-text-tertiary">Analyzing flights, hotels & rewards value</p>
            </div>
          )}

          {/* Error — editorial warning state */}
          {phase === "error" && (
            <div
              data-testid="optimize-error-state"
              className="flex flex-col items-center justify-center py-12 gap-3 text-center"
            >
              <AlertCircle className="w-8 h-8 text-ds-warning" />
              <p className="text-sm font-medium text-ds-text-secondary">{error}</p>
              <button
                onClick={run}
                className="btn-primary mt-1"
              >
                Try Again
              </button>
            </div>
          )}

          {/* Provider unavailable — Fail-Closed UX v1 — honest boutique advisory */}
          {phase === "provider_unavailable" && (
            <div
              role="alert"
              data-testid="optimize-provider-unavailable"
              className="flex flex-col items-center justify-center py-12 gap-3 text-center"
            >
              <AlertCircle className="w-8 h-8 text-ds-caution" />
              <p className="text-sm font-semibold text-ds-text">{PROVIDER_UNAVAILABLE_TITLE}</p>
              <p className="text-sm text-ds-text-secondary max-w-md">{PROVIDER_UNAVAILABLE_BODY}</p>
              <button
                onClick={onClose}
                className="btn-ghost mt-1"
              >
                Build trip manually
              </button>
            </div>
          )}

          {/* Results — boutique rank cards */}
          {phase === "results" && options.length > 0 && (() => {
            const avgCost = options.reduce((s, o) => s + o.totalCost, 0) / options.length;
            const bestSavings = options[0] ? Math.round(avgCost - options[0].totalCost) : 0;
            const cppVals = options.map(o => o.flight.cpp).filter((c): c is number => c != null);
            const avgCpp = cppVals.length ? cppVals.reduce((s, c) => s + c, 0) / cppVals.length : null;

            return (
              <div
                data-testid="optimize-results"
                className="grid grid-cols-1 md:grid-cols-3 gap-5 items-start"
              >
                {options.map((opt, idx) => (
                  <div
                    key={opt.rank}
                    data-testid={`optimize-result-card-${idx}`}
                    className={`rounded-xl border bg-ds-onyx ${RANK_BORDER[idx]} ${RANK_GLOW[idx]} overflow-hidden flex flex-col transition-shadow`}
                  >
                    {/* Primary Recommendation banner — warm atelier treatment */}
                    {idx === 0 && (
                      <div className="concierge-desk-header px-4 py-1.5 flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <Crown className="w-3 h-3 text-ds-accent" />
                          <span className="text-[11px] font-semibold text-ds-accent uppercase tracking-wider">
                            Primary Recommendation
                          </span>
                        </div>
                        {bestSavings > 0 && (
                          <span className="text-[10px] font-medium text-ds-text-tertiary">
                            Save ${bestSavings.toLocaleString()} vs avg
                          </span>
                        )}
                      </div>
                    )}

                    {/* Rank banner */}
                    <div className="px-4 py-3 flex items-center justify-between border-b border-ds-pen-stroke">
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded bg-ds-carbon border border-ds-pen-stroke ${RANK_BADGE[idx]}`}>
                        Option {opt.rank} · {RANK_LABELS[idx]}
                      </span>
                      <span className={`text-xl font-bold leading-none ${scoreColor(opt.totalValueScore)}`}>
                        {Math.round(opt.totalValueScore)}
                        <span className="text-xs font-normal text-ds-text-tertiary ml-0.5">/100</span>
                      </span>
                    </div>

                    <div className={`${idx === 0 ? "p-5" : "p-4"} flex flex-col gap-3 flex-1`}>
                      {/* Flight */}
                      <div>
                        <div className="flex items-center gap-1.5 mb-1">
                          <Plane className="w-3.5 h-3.5 text-ds-accent" />
                          <span className="text-[10px] font-semibold text-ds-text-tertiary uppercase tracking-widest">
                            Flight
                          </span>
                        </div>
                        <p className="text-sm font-semibold text-ds-text">
                          {opt.flight.airline} {opt.flight.flightNumber}
                        </p>
                        <p className="text-xs text-ds-text-secondary mt-0.5">
                          {fmtDuration(opt.flight.durationMinutes)} ·{" "}
                          {opt.flight.stops === 0
                            ? "Nonstop"
                            : `${opt.flight.stops} stop${opt.flight.stops > 1 ? "s" : ""}`}{" "}
                          · {opt.flight.cabinClass}
                        </p>
                        <p className="text-sm font-medium text-ds-text-secondary mt-1">
                          ${opt.flight.price.toLocaleString()}
                          {opt.flight.pointsCost > 0 && (
                            <span className="text-xs text-ds-accent ml-1.5">
                              · {opt.flight.pointsCost.toLocaleString()} pts
                            </span>
                          )}
                        </p>
                      </div>

                      <div className="h-px bg-ds-pen-stroke" />

                      {/* Hotel */}
                      <div>
                        <div className="flex items-center gap-1.5 mb-1">
                          <Building2 className="w-3.5 h-3.5 text-ds-accent-muted" />
                          <span className="text-[10px] font-semibold text-ds-text-tertiary uppercase tracking-widest">
                            Hotel
                          </span>
                        </div>
                        <p className="text-sm font-semibold text-ds-text line-clamp-1">{opt.hotel.name}</p>
                        <div className="flex items-center gap-2 mt-0.5">
                          {opt.hotel.rating != null && (
                            <span className="flex items-center gap-0.5 text-xs text-ds-caution">
                              <Star className="w-3 h-3 fill-ds-caution text-ds-caution" />
                              {opt.hotel.rating.toFixed(1)}
                            </span>
                          )}
                          {opt.hotel.areaLabel && (
                            <span className="text-xs text-ds-text-tertiary">{opt.hotel.areaLabel}</span>
                          )}
                        </div>
                        <p className="text-sm font-medium text-ds-text-secondary mt-1">
                          ${opt.hotel.pricePerNight.toLocaleString()}/night · {opt.hotel.nights}n
                        </p>
                      </div>

                      {/* Expanded score breakdown */}
                      {expanded === idx && (
                        <>
                          <div className="h-px bg-ds-pen-stroke" />
                          <div className="grid grid-cols-3 gap-2 text-center">
                            {[
                              { label: "Flight", score: opt.flightScore },
                              { label: "Hotel", score: opt.hotelScore },
                              { label: "Rewards", score: opt.rewardsEfficiency },
                            ].map(({ label, score }) => (
                              <div
                                key={label}
                                className="rounded-lg bg-ds-carbon border border-ds-pen-stroke p-2"
                              >
                                <p className="text-[10px] text-ds-text-tertiary">{label}</p>
                                <p className={`text-sm font-bold ${scoreColor(score)}`}>
                                  {Math.round(score)}
                                </p>
                              </div>
                            ))}
                          </div>
                          {opt.flight.explanation && (
                            <p className="text-xs text-ds-text-secondary leading-relaxed italic">
                              {opt.flight.explanation}
                            </p>
                          )}
                        </>
                      )}

                      <div className="h-px bg-ds-pen-stroke" />

                      {/* Totals + summary */}
                      <div className="space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-ds-text-tertiary">Total cost</span>
                          <span className={`font-bold ${idx === 0 ? "text-base text-ds-text" : "text-sm text-ds-text"}`}>
                            ${opt.totalCost.toLocaleString()}
                          </span>
                        </div>
                        {opt.totalPoints > 0 && (
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-ds-text-tertiary">Points used</span>
                            <span className="text-xs font-semibold text-ds-accent">
                              {opt.totalPoints.toLocaleString()} pts
                            </span>
                          </div>
                        )}
                        {opt.flight.cpp != null && (
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-ds-text-tertiary">CPP</span>
                            <span className="text-xs font-semibold text-ds-accent">
                              {opt.flight.cpp.toFixed(2)}¢
                              {idx === 0 && avgCpp != null && opt.flight.cpp > avgCpp && (
                                <span className="ml-1 font-normal text-ds-trust">
                                  +{(opt.flight.cpp - avgCpp).toFixed(1)}¢ vs avg
                                </span>
                              )}
                            </span>
                          </div>
                        )}
                        <p className="text-xs text-ds-text-secondary italic leading-relaxed pt-1">
                          {opt.summary}
                        </p>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="px-4 pb-4 flex flex-col gap-2 border-t border-ds-pen-stroke pt-4">
                      <button
                        onClick={() => handleSelect(opt, idx)}
                        disabled={selecting !== null || selected !== null}
                        className={`w-full rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition min-h-[44px] ${
                          selected === idx
                            ? "bg-ds-carbon text-ds-trust border border-ds-pen-stroke cursor-default"
                            : "btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
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
                        className="btn-ghost w-full flex items-center justify-center gap-1 text-xs"
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
            );
          })()}
        </div>
      </div>
    </div>
  );
}
