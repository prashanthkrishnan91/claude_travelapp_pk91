"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  CalendarDays,
  ChevronLeft,
  Pencil,
  Sparkles,
  Trash2,
  X,
  Zap,
} from "lucide-react";
import { TripBuilder } from "@/components/trips/TripBuilder";
import { TripReadinessCockpit } from "@/components/trips/TripReadinessCockpit";
import { OptimizeTripModal } from "@/components/trips/OptimizeTripModal";
import { AIConciergePanel } from "@/components/trips/AIConciergePanel";
import { fetchTrip, ensureTripDays, fetchTripContext, updateTrip, deleteTrip } from "@/lib/api";
import type { Trip, TripContext, ItineraryDay } from "@/types";

interface EditForm {
  title: string;
  startDate: string;
  endDate: string;
}

// ── Shared button classes ─────────────────────────────────────────────────────

const COVER_BTN_BASE =
  "inline-flex items-center gap-1.5 px-3 py-2 min-h-[44px] rounded-lg text-xs font-medium transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2";

const COVER_PRIMARY = `${COVER_BTN_BASE} bg-ds-accent text-ds-text-inverse hover:opacity-90`;
const COVER_GHOST = `${COVER_BTN_BASE} border border-ds-pen-stroke text-ds-text-secondary hover:bg-ds-carbon`;
const COVER_DANGER = `${COVER_BTN_BASE} border border-ds-pen-stroke text-ds-warning hover:bg-ds-carbon`;

export default function TripDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [trip,          setTrip]          = useState<Trip | null>(null);
  const [itineraryDays, setItineraryDays] = useState<ItineraryDay[]>([]);
  const [tripContext,   setTripContext]   = useState<TripContext | null>(null);
  const [contextLoading, setContextLoading] = useState(false);
  const [loading,       setLoading]       = useState(true);
  const [editOpen,      setEditOpen]      = useState(false);
  const [editForm,      setEditForm]      = useState<EditForm>({ title: "", startDate: "", endDate: "" });
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [saving,        setSaving]        = useState(false);
  const [toast,         setToast]         = useState<string | null>(null);
  const [optimizeOpen,  setOptimizeOpen]  = useState(false);
  const [conciergeOpen, setConciergeOpen] = useState(false);
  const [tripBuilderKey, setTripBuilderKey] = useState(0);
  const [tripIdeasKey,  setTripIdeasKey]  = useState(0);

  useEffect(() => {
    if (!id) return;
    async function load() {
      const tripData = await fetchTrip(id);
      const startDate = (tripData as (Trip & { start_date?: string }) | null)?.startDate
        ?? (tripData as (Trip & { start_date?: string }) | null)?.start_date;
      const endDate = (tripData as (Trip & { end_date?: string }) | null)?.endDate
        ?? (tripData as (Trip & { end_date?: string }) | null)?.end_date;
      const days = await ensureTripDays(id, startDate, endDate);
      setTrip(tripData);
      setItineraryDays(days);
      setLoading(false);

      if (tripData) {
        setContextLoading(true);
        fetchTripContext(id).then((ctx) => {
          setTripContext(ctx);
          setContextLoading(false);
        });
      }
    }
    load();
  }, [id]);

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }

  function openEdit() {
    setEditForm({ title: trip?.title ?? "", startDate: trip?.startDate ?? "", endDate: trip?.endDate ?? "" });
    setEditOpen(true);
  }

  async function handleUpdate() {
    if (!trip) return;
    setSaving(true);
    try {
      const updated = await updateTrip(trip.id, {
        title: editForm.title || undefined,
        startDate: editForm.startDate || undefined,
        endDate: editForm.endDate || undefined,
      });
      const days = await ensureTripDays(trip.id, updated.startDate, updated.endDate);
      setTrip(updated);
      setItineraryDays(days);
      setTripBuilderKey((k) => k + 1);
      setEditOpen(false);
      showToast("Trip updated");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!trip) return;
    await deleteTrip(trip.id);
    router.push("/trips");
  }

  async function handlePlanSelected() {
    const startDate = (trip as (Trip & { start_date?: string }) | null)?.startDate
      ?? (trip as (Trip & { start_date?: string }) | null)?.start_date;
    const endDate = (trip as (Trip & { end_date?: string }) | null)?.endDate
      ?? (trip as (Trip & { end_date?: string }) | null)?.end_date;
    const days = await ensureTripDays(id, startDate, endDate);
    setItineraryDays(days);
    setTripBuilderKey((k) => k + 1);
    setOptimizeOpen(false);
    showToast("Plan added to your itinerary!");
  }

  // ── Loading state ─────────────────────────────────────────────────────────

  if (loading) {
    return (
      <>
        <div className="mb-4">
          <Link
            href="/trips"
            className="inline-flex items-center gap-1.5 text-xs text-ds-text-tertiary hover:text-ds-text transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
          >
            <ChevronLeft className="w-3.5 h-3.5" aria-hidden="true" />
            My Journeys
          </Link>
        </div>
        <div className="mb-8 rounded-2xl border border-ds-pen-stroke bg-ds-onyx shadow-[var(--ds-elevation-2)] p-6 animate-pulse">
          <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-text-tertiary mb-2">Travel Chapter</p>
          <div className="h-7 w-48 rounded bg-ds-carbon mb-2" />
          <div className="h-4 w-32 rounded bg-ds-carbon" />
        </div>
      </>
    );
  }

  // ── Main render ───────────────────────────────────────────────────────────

  return (
    <>
      {toast && (
        <div
          role="status"
          aria-live="polite"
          className="fixed bottom-4 right-4 z-50 bg-ds-onyx border border-ds-pen-stroke text-ds-text text-sm px-4 py-2 rounded-lg shadow-[var(--ds-elevation-2)]"
        >
          {toast}
        </div>
      )}

      {/* Optimize My Trip Modal */}
      {optimizeOpen && trip && (
        <OptimizeTripModal
          trip={trip}
          itineraryDays={itineraryDays}
          onClose={() => setOptimizeOpen(false)}
          onPlanSelected={handlePlanSelected}
        />
      )}

      {/* Edit Modal */}
      {editOpen && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-ds-onyx border border-ds-pen-stroke rounded-2xl shadow-[var(--ds-elevation-4)] p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-base font-semibold text-ds-text">Edit Trip</h2>
              <button
                onClick={() => setEditOpen(false)}
                aria-label="Close edit dialog"
                className="p-1.5 rounded-lg hover:bg-ds-carbon text-ds-text-tertiary focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
              >
                <X className="w-4 h-4" aria-hidden="true" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-ds-text-secondary mb-1.5">Trip Name</label>
                <input
                  className="w-full border border-ds-pen-stroke rounded-lg px-3 py-2 text-sm bg-ds-carbon text-ds-text placeholder:text-ds-text-tertiary focus:outline-none focus:ring-2 focus:ring-ds-accent"
                  value={editForm.title}
                  onChange={(e) => setEditForm((f) => ({ ...f, title: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-ds-text-secondary mb-1.5">Start Date</label>
                <input
                  type="date"
                  className="w-full border border-ds-pen-stroke rounded-lg px-3 py-2 text-sm bg-ds-carbon text-ds-text focus:outline-none focus:ring-2 focus:ring-ds-accent"
                  value={editForm.startDate}
                  onChange={(e) => setEditForm((f) => ({ ...f, startDate: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-ds-text-secondary mb-1.5">End Date</label>
                <input
                  type="date"
                  className="w-full border border-ds-pen-stroke rounded-lg px-3 py-2 text-sm bg-ds-carbon text-ds-text focus:outline-none focus:ring-2 focus:ring-ds-accent"
                  value={editForm.endDate}
                  onChange={(e) => setEditForm((f) => ({ ...f, endDate: e.target.value }))}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setEditOpen(false)} className={COVER_GHOST}>Cancel</button>
              <button onClick={handleUpdate} disabled={saving || !editForm.title.trim()} className={COVER_PRIMARY}>
                {saving ? "Saving…" : "Save Changes"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-ds-onyx border border-ds-pen-stroke rounded-2xl shadow-[var(--ds-elevation-4)] p-6 w-full max-w-sm">
            <h2 className="text-base font-semibold text-ds-text mb-2">Delete Trip</h2>
            <p className="text-sm text-ds-text-secondary mb-6 leading-relaxed">
              This will permanently delete the trip and all its itinerary items. This cannot be undone.
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setConfirmDelete(false)} className={COVER_GHOST}>Cancel</button>
              <button
                onClick={handleDelete}
                className="inline-flex items-center gap-1.5 px-4 py-2 min-h-[44px] text-sm font-medium bg-ds-warning text-ds-text-inverse rounded-lg hover:opacity-90 transition-opacity duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
              >
                Delete Trip
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Trip Chapter Cover ─────────────────────────────────────────────── */}
      <section
        data-testid="trip-chapter-cover"
        aria-labelledby="chapter-destination-heading"
        className="mb-8 rounded-2xl border border-ds-pen-stroke bg-ds-onyx shadow-[var(--ds-elevation-2)] overflow-hidden"
      >
        {/* Back navigation */}
        <div className="px-6 pt-5">
          <Link
            href="/trips"
            className="inline-flex items-center gap-1.5 text-xs text-ds-text-tertiary hover:text-ds-text transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
          >
            <ChevronLeft className="w-3.5 h-3.5" aria-hidden="true" />
            My Journeys
          </Link>
        </div>

        {/* Chapter cover body */}
        <div className="px-6 pt-4 pb-6">
          {/* Overline: chapter classification */}
          <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-text-tertiary mb-2">
            Travel Chapter
          </p>

          {/* Destination as editorial chapter heading */}
          <h1
            id="chapter-destination-heading"
            className="text-2xl font-bold tracking-tight text-ds-text leading-tight sm:text-3xl"
          >
            {trip?.destination ?? trip?.title ?? "Your Trip"}
          </h1>

          {/* Trip title — subtitle if not same as destination */}
          {trip?.title && trip.title !== trip.destination && (
            <p className="mt-1 text-base text-ds-text-secondary leading-snug">
              {trip.title}
            </p>
          )}

          {/* Destination context / vibe — shown when available */}
          {contextLoading && (
            <p className="mt-2 text-sm italic text-ds-text-tertiary">
              Composing destination context…
            </p>
          )}
          {tripContext && !contextLoading && (
            <p className="mt-2 text-sm italic text-ds-text-tertiary leading-snug">
              {tripContext.dateRange
                ? `${tripContext.vibe} · ${tripContext.dateRange}`
                : tripContext.vibe}
            </p>
          )}

          {/* Dates + duration — caption row */}
          {(trip?.startDate || trip?.endDate) && (
            <div className="mt-3 flex items-center flex-wrap gap-x-4 gap-y-1">
              <span className="inline-flex items-center gap-1.5 text-xs text-ds-text-tertiary">
                <CalendarDays className="w-3.5 h-3.5 text-ds-accent" aria-hidden="true" />
                {trip.startDate && trip.endDate
                  ? `${trip.startDate} – ${trip.endDate}`
                  : trip.startDate || trip.endDate}
              </span>
              {itineraryDays.length > 0 && (
                <span className="text-xs text-ds-text-tertiary">
                  {itineraryDays.length} day{itineraryDays.length !== 1 ? "s" : ""}
                </span>
              )}
            </div>
          )}

          {/* Action cluster — semantic buttons, not a toolbar */}
          <div
            className="mt-5 flex items-center flex-wrap gap-2"
            data-testid="chapter-actions"
          >
            <button
              onClick={() => setConciergeOpen(true)}
              data-testid="chapter-action-concierge"
              className={COVER_PRIMARY}
            >
              <Sparkles className="w-3.5 h-3.5" aria-hidden="true" />
              AI Concierge
            </button>
            <button
              onClick={() => setOptimizeOpen(true)}
              data-testid="chapter-action-optimize"
              className={COVER_GHOST}
            >
              <Zap className="w-3.5 h-3.5" aria-hidden="true" />
              Optimize
            </button>
            <button
              onClick={openEdit}
              data-testid="chapter-action-edit"
              className={COVER_GHOST}
            >
              <Pencil className="w-3.5 h-3.5" aria-hidden="true" />
              Edit Trip
            </button>
            <button
              onClick={() => setConfirmDelete(true)}
              data-testid="chapter-action-delete"
              className={COVER_DANGER}
            >
              <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
              Delete
            </button>
          </div>
        </div>
      </section>

      {/* ── Advisor Briefing (TripReadinessCockpit) ────────────────────────── */}
      {trip && (
        <TripReadinessCockpit
          trip={trip}
          itineraryDays={itineraryDays}
          onOpenConcierge={() => setConciergeOpen(true)}
          onOpenOptimize={() => setOptimizeOpen(true)}
          onOpenEdit={openEdit}
        />
      )}

      {/* ── Planning Canvas (TripBuilder) ──────────────────────────────────── */}
      <TripBuilder
        key={tripBuilderKey}
        tripId={id}
        destination={trip?.destination ?? ""}
        startDate={trip?.startDate}
        endDate={trip?.endDate}
        initialDays={itineraryDays}
        initialResults={[]}
        ideasRefreshKey={tripIdeasKey}
        onIdeaAssigned={() => {
          const startDate = (trip as (Trip & { start_date?: string }) | null)?.startDate
            ?? (trip as (Trip & { start_date?: string }) | null)?.start_date;
          const endDate = (trip as (Trip & { end_date?: string }) | null)?.endDate
            ?? (trip as (Trip & { end_date?: string }) | null)?.end_date;
          ensureTripDays(id, startDate, endDate).then((days) => {
            setItineraryDays(days);
            setTripBuilderKey((k) => k + 1);
            showToast("Added to itinerary!");
          });
        }}
      />

      {/* ── AI Concierge Panel ─────────────────────────────────────────────── */}
      <AIConciergePanel
        tripId={id}
        destination={trip?.destination ?? ""}
        tripDays={itineraryDays}
        isOpen={conciergeOpen}
        onClose={() => setConciergeOpen(false)}
        onItemAdded={() => {
          const startDate = (trip as (Trip & { start_date?: string }) | null)?.startDate
            ?? (trip as (Trip & { start_date?: string }) | null)?.start_date;
          const endDate = (trip as (Trip & { end_date?: string }) | null)?.endDate
            ?? (trip as (Trip & { end_date?: string }) | null)?.end_date;
          ensureTripDays(id, startDate, endDate).then((days) => {
            setItineraryDays(days);
            setTripBuilderKey((k) => k + 1);
            showToast("Added to your itinerary!");
          });
        }}
        onIdeaSaved={() => setTripIdeasKey((k) => k + 1)}
      />
    </>
  );
}
