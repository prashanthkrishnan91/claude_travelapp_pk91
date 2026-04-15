import Link from "next/link";
import { MapPin, Calendar, Users, ArrowRight } from "lucide-react";
import { TripStatusBadge } from "@/components/ui/TripStatusBadge";
import type { Trip } from "@/types";

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

interface RecentTripsProps {
  trips: Trip[];
}

export function RecentTrips({ trips }: RecentTripsProps) {
  const recent = trips.slice(0, 5);

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

      {recent.length === 0 ? (
        <div className="px-6 py-8 text-center text-slate-400">
          <p className="text-sm">No trips yet.</p>
          <Link href="/trips/new" className="text-sm text-sky-600 hover:text-sky-700 font-medium mt-2 inline-block">
            Plan your first trip →
          </Link>
        </div>
      ) : (
        <ul className="divide-y divide-slate-100">
          {recent.map((trip) => (
            <li key={trip.id}>
              <Link
                href={`/trips/${trip.id}`}
                className="flex items-start gap-4 px-6 py-4 hover:bg-slate-50 transition-all duration-150 group border-l-2 border-transparent hover:border-sky-400"
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
                  <p className="text-xs text-slate-500 mt-0.5 truncate">
                    {trip.destination}
                  </p>
                  <div className="flex items-center gap-3 mt-1.5 text-xs text-slate-400">
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
                </div>

                {trip.budgetCash && (
                  <div className="shrink-0 text-right space-y-1">
                    <p className="text-sm font-semibold text-slate-800">
                      {new Intl.NumberFormat("en-US", {
                        style: "currency",
                        currency: trip.budgetCurrency,
                        maximumFractionDigits: 0,
                      }).format(Number(trip.budgetCash))}
                    </p>
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
                  </div>
                )}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
