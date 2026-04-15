import type { Metadata } from "next";
import Link from "next/link";
import { ChevronLeft, Pencil, Sparkles } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";

export const metadata: Metadata = { title: "Trip Details" };

export default async function TripDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <>
      <div className="mb-6">
        <Link
          href="/trips"
          className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 transition"
        >
          <ChevronLeft className="w-4 h-4" />
          My Trips
        </Link>
      </div>

      <PageHeader
        title="Trip Details"
        description={`Trip ID: ${id}`}
        action={
          <div className="flex items-center gap-2">
            <button className="btn-ghost">
              <Pencil className="w-4 h-4" />
              Edit
            </button>
            <button className="btn-primary">
              <Sparkles className="w-4 h-4" />
              AI Concierge
            </button>
          </div>
        }
      />

      <div className="card p-8 text-center text-slate-400">
        <p className="text-sm">Itinerary view coming in the next step.</p>
      </div>
    </>
  );
}
