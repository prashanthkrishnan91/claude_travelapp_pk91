import type { Metadata } from "next";
import { Search } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";

export const metadata: Metadata = { title: "Search Flights" };

export default function SearchPage() {
  return (
    <>
      <PageHeader
        title="Search Flights"
        description="Find the best routes, fares and award availability."
      />
      <div className="card p-8 text-center text-slate-400">
        <Search className="w-8 h-8 mx-auto mb-3 opacity-40" />
        <p className="text-sm">Flight search coming soon.</p>
      </div>
    </>
  );
}
