"use client";

import { useState } from "react";
import {
  Plane,
  Search,
  Loader2,
  AlertCircle,
  Clock,
  ArrowRight,
  Star,
  Zap,
  CircleDollarSign,
} from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { searchFlights } from "@/lib/api";
import type { FlightSearchResult } from "@/types";

function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

function formatPoints(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(0)}k` : String(n);
}

function ValueBadge({ tag }: { tag: string }) {
  const isGood = tag === "Good Points Value";
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${
        isGood
          ? "bg-emerald-100 text-emerald-700"
          : "bg-slate-100 text-slate-600"
      }`}
    >
      {isGood && <Zap className="w-3 h-3" />}
      {tag}
    </span>
  );
}

function FlightCard({ flight }: { flight: FlightSearchResult }) {
  return (
    <div className="card p-4 flex flex-col gap-3">
      {/* Header row */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-sky-50 text-sky-600 flex items-center justify-center flex-shrink-0">
            <Plane className="w-4 h-4" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-800 leading-tight">
              {flight.airline}
            </p>
            <p className="text-xs text-slate-400">{flight.flightNumber}</p>
          </div>
        </div>
        <ValueBadge tag={flight.recommendationTag} />
      </div>

      {/* Route + timing */}
      <div className="flex items-center gap-2">
        <div className="text-center">
          <p className="text-base font-bold text-slate-800">
            {formatTime(flight.departureTime)}
          </p>
          <p className="text-xs text-slate-500">{flight.origin}</p>
        </div>

        <div className="flex-1 flex flex-col items-center gap-0.5">
          <p className="text-xs text-slate-400 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatDuration(flight.durationMinutes)}
          </p>
          <div className="w-full flex items-center gap-1">
            <div className="flex-1 h-px bg-slate-200" />
            <ArrowRight className="w-3 h-3 text-slate-400 flex-shrink-0" />
          </div>
          <p className="text-xs text-slate-400">
            {flight.stops === 0
              ? "Nonstop"
              : `${flight.stops} stop${flight.stops > 1 ? "s" : ""}`}
          </p>
        </div>

        <div className="text-center">
          <p className="text-base font-bold text-slate-800">
            {formatTime(flight.arrivalTime)}
          </p>
          <p className="text-xs text-slate-500">{flight.destination}</p>
        </div>
      </div>

      {/* Pricing row */}
      <div className="flex items-center justify-between pt-2 border-t border-slate-100">
        <div className="flex items-center gap-3">
          <div>
            <p className="text-xs text-slate-400">Cash</p>
            <p className="text-sm font-bold text-slate-800">
              ${flight.price.toFixed(2)}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-400">Points</p>
            <p className="text-sm font-bold text-slate-800">
              {formatPoints(flight.pointsCost)} pts
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-400">CPP</p>
            <p
              className={`text-sm font-bold ${
                flight.cpp >= 2 ? "text-emerald-600" : "text-slate-800"
              }`}
            >
              {flight.cpp.toFixed(2)}¢
            </p>
          </div>
        </div>

        {flight.rating !== undefined && (
          <span className="flex items-center gap-0.5 text-xs text-amber-500 font-medium">
            <Star className="w-3 h-3 fill-amber-500" />
            {flight.rating.toFixed(1)}
          </span>
        )}
      </div>
    </div>
  );
}

export default function SearchPage() {
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [date, setDate] = useState("");
  const [results, setResults] = useState<FlightSearchResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!origin || !destination || !date) return;
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const data = await searchFlights(origin, destination, date);
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }

  const goodValueCount = results?.filter((r) => r.recommendationTag === "Good Points Value").length ?? 0;

  return (
    <>
      <PageHeader
        title="Search Flights"
        description="Find the best routes, fares and award availability."
      />

      {/* Search form */}
      <form onSubmit={handleSearch} className="card p-4 mb-6">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-500 uppercase tracking-wide">
              From
            </label>
            <input
              type="text"
              placeholder="JFK"
              value={origin}
              onChange={(e) => setOrigin(e.target.value.toUpperCase().slice(0, 3))}
              maxLength={3}
              required
              className="input uppercase"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-500 uppercase tracking-wide">
              To
            </label>
            <input
              type="text"
              placeholder="LAX"
              value={destination}
              onChange={(e) => setDestination(e.target.value.toUpperCase().slice(0, 3))}
              maxLength={3}
              required
              className="input uppercase"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-500 uppercase tracking-wide">
              Date
            </label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              required
              className="input"
            />
          </div>
        </div>
        <button
          type="submit"
          disabled={loading || !origin || !destination || !date}
          className="btn btn-primary mt-4 w-full sm:w-auto flex items-center gap-2"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Search className="w-4 h-4" />
          )}
          {loading ? "Searching…" : "Search Flights"}
        </button>
      </form>

      {/* Error state */}
      {error && (
        <div className="flex items-center gap-2 p-4 rounded-lg bg-rose-50 text-rose-700 text-sm mb-4">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Results */}
      {results !== null && (
        <>
          {results.length === 0 ? (
            <div className="card p-10 text-center text-slate-400">
              <Plane className="w-8 h-8 mx-auto mb-3 opacity-30" />
              <p className="text-sm">No flights found for this route and date.</p>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm text-slate-500">
                  {results.length} flight{results.length !== 1 ? "s" : ""} found
                </p>
                {goodValueCount > 0 && (
                  <span className="flex items-center gap-1 text-xs font-medium text-emerald-700 bg-emerald-50 px-2 py-1 rounded-full">
                    <Zap className="w-3 h-3" />
                    {goodValueCount} good points value
                  </span>
                )}
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {results.map((flight) => (
                  <FlightCard key={flight.id} flight={flight} />
                ))}
              </div>
              <div className="mt-4 p-3 rounded-lg bg-slate-50 flex items-start gap-2 text-xs text-slate-500">
                <CircleDollarSign className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                <span>
                  <strong>CPP</strong> (cents per point) measures award redemption value.
                  Flights at <strong className="text-emerald-600">≥ 2.0¢</strong> per point
                  are tagged <em>Good Points Value</em>.
                </span>
              </div>
            </>
          )}
        </>
      )}
    </>
  );
}
