import type { Metadata } from "next";
import Link from "next/link";
import { ChevronLeft, Pencil, Sparkles } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { TripBuilder } from "@/components/trips/TripBuilder";
import {
  fetchTrip,
  fetchItinerary,
  searchHotels,
  searchAttractions,
} from "@/lib/api";

export const metadata: Metadata = { title: "Trip Builder" };

export default async function TripDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  // Fetch trip and itinerary in parallel
  const [trip, itineraryDays] = await Promise.all([
    fetchTrip(id),
    fetchItinerary(id),
  ]);

  // Fetch research results (hotels + attractions) if we have a destination
  const destination = trip?.destination ?? "";
  const checkIn  = trip?.startDate  ?? new Date().toISOString().slice(0, 10);
  const checkOut = trip?.endDate    ?? new Date(Date.now() + 7 * 86_400_000).toISOString().slice(0, 10);
  const guests   = trip?.travelers  ?? 1;

  const [hotels, attractions] = destination
    ? await Promise.all([
        searchHotels(destination, checkIn, checkOut, guests),
        searchAttractions(destination, checkIn),
      ])
    : [[], []];

  const initialResults = [...hotels, ...attractions];

  const pageTitle  = trip?.title       ?? "Trip Builder";
  const pageSubtitle = trip?.destination
    ? `${trip.destination}${trip.startDate ? ` · ${trip.startDate}` : ""}`
    : `Trip ID: ${id}`;

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
        title={pageTitle}
        description={pageSubtitle}
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

      <TripBuilder
        tripId={id}
        initialDays={itineraryDays}
        initialResults={initialResults}
      />
    </>
  );
}
