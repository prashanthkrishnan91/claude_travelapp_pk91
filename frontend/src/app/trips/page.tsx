import type { Metadata } from "next";
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
import type { Trip, TripStatus } from "@/types";

export const metadata: Metadata = { title: "My Trips" };

const ALL_TRIPS: Trip[] = [
  {
    id: "1",
    title: "Tokyo Cherry Blossom",
    destination: "Tokyo, Japan",
    origin: "New York, USA",
    startDate: "2026-03-25",
    endDate: "2026-04-05",
    travelers: 2,
    budgetCash: 6000,
    budgetCurrency: "USD",
    status: "planned",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: "2",
    title: "Amalfi Coast Getaway",
    destination: "Amalfi, Italy",
    origin: "Boston, USA",
    startDate: "2026-06-10",
    endDate: "2026-06-20",
    travelers: 2,
    budgetCash: 8500,
    budgetCurrency: "USD",
    status: "researching",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: "3",
    title: "Patagonia Trekking",
    destination: "Patagonia, Argentina",
    origin: "Miami, USA",
    startDate: "2026-11-01",
    endDate: "2026-11-14",
    travelers: 1,
    budgetCash: 4200,
    budgetCurrency: "USD",
    status: "draft",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: "4",
    title: "Maldives Honeymoon",
    destination: "Male, Maldives",
    origin: "Los Angeles, USA",
    startDate: "2025-12-26",
    endDate: "2026-01-04",
    travelers: 2,
    budgetCash: 14000,
    budgetCurrency: "USD",
    status: "booked",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: "5",
    title: "Kyoto Fall Foliage",
    destination: "Kyoto, Japan",
    origin: "San Francisco, USA",
    startDate: "2025-11-01",
    endDate: "2025-11-10",
    travelers: 1,
    budgetCash: 3800,
    budgetCurrency: "USD",
    status: "completed",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
];

function formatDateRange(start?: string, end?: string) {
  if (!start) return "Dates TBD";
  const fmt = (d: string) =>
    new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  return end ? `${fmt(start)} – ${fmt(end)}` : fmt(start);
}

const STATUS_GROUPS: { label: string; statuses: TripStatus[] }[] = [
  { label: "Active", statuses: ["draft", "researching", "planned", "booked"] },
  { label: "Past", statuses: ["completed", "archived"] },
];

export default function TripsPage() {
  const groupedTrips = STATUS_GROUPS.map(({ label, statuses }) => ({
    label,
    trips: ALL_TRIPS.filter((t) => statuses.includes(t.status)),
  }));

  const hasAny = ALL_TRIPS.length > 0;

  return (
    <>
      <PageHeader
        title="My Trips"
        description={`${ALL_TRIPS.length} trip${ALL_TRIPS.length !== 1 ? "s" : ""} in total`}
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
          {groupedTrips.map(({ label, trips }) =>
            trips.length === 0 ? null : (
              <section key={label}>
                <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3 px-1">
                  {label}
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                  {trips.map((trip) => (
                    <Link
                      key={trip.id}
                      href={`/trips/${trip.id}`}
                      className="card p-5 flex flex-col gap-3 hover:shadow-md hover:border-slate-300 transition group"
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
                          {trip.travelers} {trip.travelers === 1 ? "traveler" : "travelers"}
                        </span>
                      </div>

                      {/* Budget */}
                      {trip.budgetCash && (
                        <div className="pt-2 mt-auto border-t border-slate-100 flex items-center justify-between">
                          <span className="text-xs text-slate-400">Budget</span>
                          <span className="text-sm font-semibold text-slate-800">
                            {new Intl.NumberFormat("en-US", {
                              style: "currency",
                              currency: trip.budgetCurrency,
                              maximumFractionDigits: 0,
                            }).format(trip.budgetCash)}
                          </span>
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
