import type { Metadata } from "next";
import Link from "next/link";
import { Map, Plane, CreditCard, Coins, PlusCircle } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { RecentTrips } from "@/components/dashboard/RecentTrips";
import { QuickActions } from "@/components/dashboard/QuickActions";
import { PointsSummary } from "@/components/dashboard/PointsSummary";
import { fetchTrips, fetchCards } from "@/lib/api";
import type { Trip } from "@/types";

export const metadata: Metadata = { title: "Dashboard" };

const TODAY = new Date().toISOString().slice(0, 10);

function isUpcoming(trip: Trip): boolean {
  const upcoming = ["planned", "booked", "researching"];
  return upcoming.includes(trip.status) && (!trip.startDate || trip.startDate >= TODAY);
}

function nextTripLabel(trips: Trip[]): string | undefined {
  const upcomingWithDate = trips
    .filter((t) => t.startDate && t.startDate >= TODAY)
    .sort((a, b) => (a.startDate! < b.startDate! ? -1 : 1));
  if (!upcomingWithDate.length) return undefined;
  const d = new Date(upcomingWithDate[0].startDate!);
  return `Next: ${d.toLocaleDateString("en-US", { month: "short", day: "numeric" })}`;
}

export default async function DashboardPage() {
  const [trips, cards] = await Promise.all([fetchTrips(), fetchCards()]);

  const totalTrips    = trips.length;
  const upcomingCount = trips.filter(isUpcoming).length;
  const totalCards    = cards.length;
  const totalPoints   = cards.reduce((s, c) => s + (c.pointsBalance ?? 0), 0);

  const avgCpp =
    cards.length > 0
      ? cards.reduce((s, c) => s + (c.pointValueCpp ?? 0), 0) / cards.length
      : 0;
  const pointsValue = avgCpp > 0 ? (totalPoints * avgCpp) / 100 : 0;

  const nextTrip = nextTripLabel(trips);

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Welcome back. Here's your travel overview."
        action={
          <Link href="/trips/new" className="btn-primary">
            <PlusCircle className="w-4 h-4" />
            New Trip
          </Link>
        }
      />

      {/* Stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Total Trips"
          value={totalTrips}
          icon={<Map className="w-5 h-5" />}
          trend={upcomingCount > 0 ? `${upcomingCount} in planning` : undefined}
          trendUp={upcomingCount > 0}
          colorClass="bg-sky-50 text-sky-600"
        />
        <StatCard
          label="Upcoming"
          value={upcomingCount}
          icon={<Plane className="w-5 h-5" />}
          trend={nextTrip}
          trendUp={!!nextTrip}
          colorClass="bg-violet-50 text-violet-600"
        />
        <StatCard
          label="Travel Cards"
          value={totalCards}
          icon={<CreditCard className="w-5 h-5" />}
          colorClass="bg-emerald-50 text-emerald-600"
        />
        <StatCard
          label="Total Points"
          value={totalPoints > 0 ? totalPoints.toLocaleString() : "0"}
          icon={<Coins className="w-5 h-5" />}
          trend={
            pointsValue > 0
              ? `≈ ${new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(pointsValue)} in value`
              : undefined
          }
          trendUp={pointsValue > 0}
          colorClass="bg-amber-50 text-amber-600"
        />
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column — spans 2 */}
        <div className="lg:col-span-2 space-y-6">
          <RecentTrips trips={trips} />
          <QuickActions />
        </div>

        {/* Right column */}
        <div className="space-y-6">
          <PointsSummary cards={cards} />
        </div>
      </div>
    </>
  );
}
