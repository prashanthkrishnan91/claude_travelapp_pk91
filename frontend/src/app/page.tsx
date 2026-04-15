import type { Metadata } from "next";
import Link from "next/link";
import { Map, Plane, CreditCard, Coins, PlusCircle } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { RecentTrips } from "@/components/dashboard/RecentTrips";
import { QuickActions } from "@/components/dashboard/QuickActions";
import { PointsSummary } from "@/components/dashboard/PointsSummary";

export const metadata: Metadata = { title: "Dashboard" };

export default function DashboardPage() {
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
          value={7}
          icon={<Map className="w-5 h-5" />}
          trend="2 in planning"
          trendUp
          colorClass="bg-sky-50 text-sky-600"
        />
        <StatCard
          label="Upcoming"
          value={3}
          icon={<Plane className="w-5 h-5" />}
          trend="Next: Mar 25"
          trendUp
          colorClass="bg-violet-50 text-violet-600"
        />
        <StatCard
          label="Travel Cards"
          value={3}
          icon={<CreditCard className="w-5 h-5" />}
          colorClass="bg-emerald-50 text-emerald-600"
        />
        <StatCard
          label="Total Points"
          value="264,750"
          icon={<Coins className="w-5 h-5" />}
          trend="≈ $4,900 in value"
          trendUp
          colorClass="bg-amber-50 text-amber-600"
        />
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column — spans 2 */}
        <div className="lg:col-span-2 space-y-6">
          <RecentTrips />
          <QuickActions />
        </div>

        {/* Right column */}
        <div className="space-y-6">
          <PointsSummary />
        </div>
      </div>
    </>
  );
}
