import Link from "next/link";
import { MapPin, Calendar, Users, ArrowRight } from "lucide-react";
import { TripStatusBadge } from "@/components/ui/TripStatusBadge";
import type { Trip } from "@/types";

const PLACEHOLDER_TRIPS: Trip[] = [
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
];

function formatDateRange(start?: string, end?: string) {
  if (!start) return "Dates TBD";
  const fmt = (d: string) =>
    new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  return end ? `${fmt(start)} – ${fmt(end)}` : fmt(start);
}

export function RecentTrips() {
  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
        <h2 className="text-base font-semibold text-slate-900">Recent Trips</h2>
        <Link
          href="/trips"
          className="flex items-center gap-1 text-sm text-sky-600 hover:text-sky-700 font-medium transition"
        >
          View all <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      <ul className="divide-y divide-slate-100">
        {PLACEHOLDER_TRIPS.map((trip) => (
          <li key={trip.id}>
            <Link
              href={`/trips/${trip.id}`}
              className="flex items-start gap-4 px-6 py-4 hover:bg-slate-50 transition group"
            >
              {/* Destination icon */}
              <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-sky-50 text-sky-600 shrink-0 mt-0.5">
                <MapPin className="w-4 h-4" />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-slate-900 group-hover:text-sky-700 transition truncate">
                    {trip.title}
                  </span>
                  <TripStatusBadge status={trip.status} />
                </div>
                <p className="text-xs text-slate-500 mt-0.5 truncate">{trip.destination}</p>
                <div className="flex items-center gap-3 mt-1.5 text-xs text-slate-400">
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {formatDateRange(trip.startDate, trip.endDate)}
                  </span>
                  <span className="flex items-center gap-1">
                    <Users className="w-3 h-3" />
                    {trip.travelers} {trip.travelers === 1 ? "traveler" : "travelers"}
                  </span>
                </div>
              </div>

              {trip.budgetCash && (
                <div className="shrink-0 text-right">
                  <p className="text-sm font-semibold text-slate-800">
                    {new Intl.NumberFormat("en-US", {
                      style: "currency",
                      currency: trip.budgetCurrency,
                      maximumFractionDigits: 0,
                    }).format(trip.budgetCash)}
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">budget</p>
                </div>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
