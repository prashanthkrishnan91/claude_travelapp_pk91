"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  PlusCircle,
  MapPin,
  Calendar,
  Users,
  Map,
} from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { TripStatusBadge } from "@/components/ui/TripStatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { fetchTrips } from "@/lib/api";
import type { Trip, TripStatus } from "@/types";

function formatDateRange(start?: string, end?: string) {
  if (!start) return "Dates TBD";
  const fmt = (d: string) =>
    new Date(d).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  return end ? `${fmt(start)} – ${fmt(end)}` : fmt(start);
}

const STATUS_GROUPS: { label: string; statuses: TripStatus[] }[] = [
  { label: "Active", statuses: ["draft", "researching", "planned", "booked"] },
  { label: "Past",   statuses: ["completed", "archived"] },
];

export default function TripsPage() {
  const [trips, setTrips] = useState<Trip[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      console.log("[TripsPage] Fetching trips via GET /trips…");
      const result = await fetchTrips();
      console.log("[TripsPage] GET /trips response:", result);
      setTrips(result);
      setLoading(false);
    }
    load();
  }, []);

  const groupedTrips = STATUS_GROUPS.map(({ label, statuses }) => ({
    label,
    trips: trips.filter((t: Trip) => statuses.includes(t.status)),
  }));

  const hasAny = trips.length > 0;

  if (loading) {
    return (
      <>
        <PageHeader
          title="My Trips"
          description="Loading…"
          action={
            <Link href="/trips/new" className="btn-primary">
              <PlusCircle className="w-4 h-4" />
              New Trip
            </Link>
          }
        />
        <div className="card p-8 text-center text-slate-400 text-sm">
          Loading your trips…
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="My Trips"
        description={`${trips.length} trip${trips.length !== 1 ? "s" : ""} in total`}
        action={
          <Link href="/trips/new" className="btn-primary">
            <PlusCircle className="w-4 h-4" />
            New Trip
          </Link>
        }
      />

      {!hasAny ? (
        <div className="card">
          <EmptyState
            icon={<Map className="w-6 h-6" />}
            title="No trips yet"
            description="Start planning your first trip and let the AI concierge help you build the perfect itinerary."
            action={
              <Link href="/trips/new" className="btn-primary">
                <PlusCircle className="w-4 h-4" />
                Plan a Trip
              </Link>
            }
          />
        </div>
      ) : (
        <div className="space-y-8">
          {groupedTrips.map(({ label, trips: groupTrips }) =>
            groupTrips.length === 0 ? null : (
              <section key={label}>
                <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3 px-1">
                  {label}
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                  {groupTrips.map((trip: Trip) => (
                    <Link
                      key={trip.id}
                      href={`/trips/${trip.id}`}
                      className="card card-lift p-5 flex flex-col gap-3 group"
                    >
                      {/* Header */}
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="text-sm font-semibold text-slate-900 group-hover:text-sky-700 transition leading-snug">
                          {trip.title}
                        </h3>
                        <TripStatusBadge status={trip.status} />
                      </div>

                      {/* Destination */}
                      <div className="flex items-center gap-1.5 text-sm text-slate-600">
                        <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        {trip.destination}
                      </div>

                      {/* Meta */}
                      <div className="flex flex-wrap gap-3 text-xs text-slate-400">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {formatDateRange(trip.startDate, trip.endDate)}
                        </span>
                        <span className="flex items-center gap-1">
                          <Users className="w-3 h-3" />
                          {trip.travelers}{" "}
                          {trip.travelers === 1 ? "traveler" : "travelers"}
                        </span>
                      </div>

                      {/* Budget */}
                      {trip.budgetCash && (
                        <div className="pt-2 mt-auto border-t border-slate-100 flex items-center justify-between gap-2">
                          <span className="text-xs text-slate-400">Budget</span>
                          <div className="flex items-center gap-1.5">
                            {trip.travelers > 1 && (
                              <span className="badge badge-value text-[10px] px-1.5 py-0.5">
                                {new Intl.NumberFormat("en-US", {
                                  style: "currency",
                                  currency: trip.budgetCurrency,
                                  maximumFractionDigits: 0,
                                }).format(Number(trip.budgetCash) / trip.travelers)}
                                /pp
                              </span>
                            )}
                            <span className="text-sm font-semibold text-slate-800">
                              {new Intl.NumberFormat("en-US", {
                                style: "currency",
                                currency: trip.budgetCurrency,
                                maximumFractionDigits: 0,
                              }).format(Number(trip.budgetCash))}
                            </span>
                          </div>
                        </div>
                      )}
                    </Link>
                  ))}
                </div>
              </section>
            )
          )}
        </div>
      )}
    </>
  );
}
