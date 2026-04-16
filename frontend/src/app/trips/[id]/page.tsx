"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
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
import type { Trip, ItineraryDay, ResearchResult } from "@/types";

export default function TripDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [trip, setTrip] = useState<Trip | null>(null);
  const [itineraryDays, setItineraryDays] = useState<ItineraryDay[]>([]);
  const [initialResults, setInitialResults] = useState<ResearchResult[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;

    async function load() {
      console.log(`[TripDetailPage] Fetching trip ${id} via GET /trips/${id}…`);
      const [tripData, days] = await Promise.all([
        fetchTrip(id),
        fetchItinerary(id),
      ]);
      console.log(`[TripDetailPage] GET /trips/${id} response:`, tripData);
      console.log(`[TripDetailPage] Itinerary days:`, days);

      setTrip(tripData);
      setItineraryDays(days);

      const destination = tripData?.destination ?? "";
      if (destination) {
        const checkIn  = tripData?.startDate  ?? new Date().toISOString().slice(0, 10);
        const checkOut = tripData?.endDate    ?? new Date(Date.now() + 7 * 86_400_000).toISOString().slice(0, 10);
        const guests   = tripData?.travelers  ?? 1;

        const [hotels, attractions] = await Promise.all([
          searchHotels(destination, checkIn, checkOut, guests),
          searchAttractions(destination, checkIn),
        ]);
        setInitialResults([...hotels, ...attractions]);
      }

      setLoading(false);
    }

    load();
  }, [id]);

  const pageTitle    = trip?.title       ?? "Trip Builder";
  const pageSubtitle = trip?.destination
    ? `${trip.destination}${trip.startDate ? ` · ${trip.startDate}` : ""}`
    : `Trip ID: ${id}`;

  if (loading) {
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
        <PageHeader title="Loading…" description={`Trip ID: ${id}`} />
        <div className="card p-8 text-center text-slate-400 text-sm">
          Loading trip details…
        </div>
      </>
    );
  }

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
        tripOrigin={trip?.origin ?? ""}
        tripDestination={trip?.destination ?? ""}
      />
    </>
  );
}
