"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  PlusCircle,
  Calendar,
  Users,
  Map,
  Pencil,
  Trash2,
  X,
  ArrowRight,
  Sparkles,
  BookmarkCheck,
  Compass,
  ChevronRight,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { TripStatusBadge } from "@/components/ui/TripStatusBadge";
import { fetchTrips, updateTrip, deleteTrip } from "@/lib/api";
import { getDisplayTripStatus, getTripStatusGroup } from "@/lib/tripStatus";
import type { Trip, TripStatus } from "@/types";

// ── Helpers ───────────────────────────────────────────────────────────────────

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

function formatBudget(amount: number, currency: string) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

const STATUS_PRIORITY: Record<TripStatus, number> = {
  researching: 0,
  planned: 1,
  booked: 2,
  draft: 3,
  completed: 4,
  archived: 5,
};

function pickContinuePlanning(trips: Trip[]): Trip | null {
  const active = trips.filter((t) => getTripStatusGroup(t) === "Active");
  if (!active.length) return null;
  return active.sort(
    (a, b) =>
      (STATUS_PRIORITY[a.status] ?? 99) - (STATUS_PRIORITY[b.status] ?? 99),
  )[0];
}

interface EditForm {
  title: string;
  startDate: string;
  endDate: string;
}

// ── Overline label ────────────────────────────────────────────────────────────

function Overline({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-text-tertiary mb-3">
      {children}
    </p>
  );
}

// ── Loading skeleton ──────────────────────────────────────────────────────────

function DashboardSkeleton() {
  return (
    <div
      className="space-y-6"
      aria-busy="true"
      aria-label="Loading your journeys"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <Skeleton className="h-8 w-44" />
          <Skeleton className="h-4 w-32" />
        </div>
        <Skeleton variant="button" className="w-32" />
      </div>
      <Skeleton variant="card" className="h-48 w-full" />
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} variant="card" className="h-52" />
        ))}
      </div>
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyDashboard() {
  return (
    <div className="space-y-8" data-testid="trips-empty-state">
      {/* Editorial hero */}
      <div className="text-center py-12 px-4">
        <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-ds-accent-subtle border border-ds-pen-stroke text-ds-accent mx-auto mb-6">
          <Map className="w-8 h-8" />
        </div>
        <h2 className="text-2xl font-semibold text-ds-text tracking-tight mb-2">
          Your journey starts here.
        </h2>
        <p className="text-ds-text-tertiary max-w-sm mx-auto leading-relaxed text-sm">
          Plan your first trip with an AI travel concierge that thinks about
          every detail — flights, stays, restaurants, and the moments in
          between.
        </p>
      </div>

      {/* Action cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Card
          as="div"
          tone="dark"
          className="p-6 flex flex-col gap-4 hover:border-ds-accent/50 transition-colors duration-200"
        >
          <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-ds-accent-subtle text-ds-accent">
            <PlusCircle className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-ds-text mb-1">
              Plan a Trip
            </h3>
            <p className="text-sm text-ds-text-tertiary leading-relaxed">
              Name your destination, set dates, and let the planning canvas
              help you build a complete itinerary.
            </p>
          </div>
          <div className="mt-auto">
            <Link href="/trips/new" className="btn-primary inline-flex min-h-[44px] items-center">
              <PlusCircle className="w-4 h-4" />
              New Trip
            </Link>
          </div>
        </Card>

        <Card
          as="div"
          tone="dark"
          className="p-6 flex flex-col gap-4 hover:border-ds-accent/50 transition-colors duration-200"
        >
          <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-ds-accent-subtle text-ds-accent">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-ds-text mb-1">
              Ask the AI Concierge
            </h3>
            <p className="text-sm text-ds-text-tertiary leading-relaxed">
              Get personalised recommendations for hotels, restaurants, and
              activities — anywhere in the world.
            </p>
          </div>
          <div className="mt-auto">
            <Link
              href="/concierge"
              className="inline-flex items-center gap-2 min-h-[44px] text-sm font-semibold text-ds-accent hover:text-ds-accent-muted transition"
            >
              Open Concierge <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </Card>
      </div>

      {/* Saved ideas nudge */}
      <p className="text-center text-sm text-ds-text-tertiary">
        Have places in mind?{" "}
        <Link
          href="/saved"
          className="text-ds-accent hover:text-ds-accent-muted font-medium transition"
        >
          Browse your saved ideas →
        </Link>
      </p>
    </div>
  );
}

// ── Continue planning hero ────────────────────────────────────────────────────

interface ContinuePlanningHeroProps {
  trip: Trip;
  onEdit: (trip: Trip) => void;
  onDelete: (id: string) => void;
}

function ContinuePlanningHero({ trip, onEdit, onDelete }: ContinuePlanningHeroProps) {
  return (
    <section aria-label="Continue planning your trip">
      <Overline>Continue planning</Overline>
      <Card
        as="article"
        tone="dark"
        className="hover:border-ds-accent/40 transition-colors duration-200"
        style={{ boxShadow: "var(--ds-elevation-2)" }}
        data-testid="continue-planning-hero"
      >
        {/* Editorial destination / title header */}
        <div className="p-6 border-b border-ds-pen-stroke">
          <div className="flex items-start justify-between gap-2 mb-4">
            <div className="min-w-0 flex-1">
              <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-text-tertiary mb-1.5">
                {trip.destination}
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-xl font-semibold text-ds-text leading-snug">
                  {trip.title}
                </h2>
                <TripStatusBadge status={getDisplayTripStatus(trip)} />
              </div>
            </div>
            <div className="flex items-center gap-0.5 shrink-0">
              <button
                onClick={() => onEdit(trip)}
                className="p-1.5 rounded-lg hover:bg-ds-pen-stroke text-ds-text-tertiary hover:text-ds-text transition min-h-[44px] min-w-[44px] flex items-center justify-center"
                aria-label={`Edit ${trip.title}`}
              >
                <Pencil className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => onDelete(trip.id)}
                className="p-1.5 rounded-lg hover:bg-ds-pen-stroke text-ds-text-tertiary hover:text-ds-warning transition min-h-[44px] min-w-[44px] flex items-center justify-center"
                aria-label={`Delete ${trip.title}`}
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <div className="flex flex-wrap gap-4 text-xs text-ds-text-tertiary">
            <span className="flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5" aria-hidden="true" />
              {formatDateRange(trip.startDate, trip.endDate)}
            </span>
            <span className="flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5" aria-hidden="true" />
              {trip.travelers}{" "}
              {trip.travelers === 1 ? "traveler" : "travelers"}
            </span>
            {trip.budgetCash && (
              <span className="text-ds-accent font-medium">
                {formatBudget(
                  Number(trip.budgetCash),
                  trip.budgetCurrency,
                )}{" "}
                budget
              </span>
            )}
          </div>
        </div>

        {/* Action footer */}
        <div className="px-6 py-4 flex flex-wrap gap-2">
          <Link
            href={`/trips/${trip.id}`}
            className="btn-primary inline-flex items-center min-h-[44px]"
          >
            Open Trip
            <ArrowRight className="w-4 h-4 ml-1" />
          </Link>
          <Link
            href="/concierge"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-ds-pen-stroke bg-ds-carbon text-ds-text text-sm font-medium hover:border-ds-accent/40 hover:text-ds-accent transition-all duration-200 min-h-[44px]"
          >
            <Sparkles className="w-4 h-4" aria-hidden="true" />
            AI Concierge
          </Link>
        </div>
      </Card>
    </section>
  );
}

// ── Journey card — travel volume cover ────────────────────────────────────────

interface JourneyCardProps {
  trip: Trip;
  onEdit: (trip: Trip) => void;
  onDelete: (id: string) => void;
}

function JourneyCard({ trip, onEdit, onDelete }: JourneyCardProps) {
  return (
    <Card
      as="article"
      tone="dark"
      className="flex flex-col hover:border-ds-accent/40 transition-colors duration-200"
      style={{ boxShadow: "var(--ds-elevation-1)" }}
      data-testid="journey-card"
    >
      {/* Volume cover — destination as hero */}
      <div className="flex-1 p-5 pb-4 flex flex-col gap-3">
        {/* Status marker + edit/delete controls */}
        <div className="flex items-start justify-between gap-2">
          <TripStatusBadge status={getDisplayTripStatus(trip)} />
          <div className="flex items-center gap-0.5 shrink-0">
            <button
              onClick={() => onEdit(trip)}
              className="p-1.5 rounded-lg hover:bg-ds-pen-stroke text-ds-text-tertiary hover:text-ds-text transition min-h-[44px] min-w-[44px] flex items-center justify-center"
              aria-label={`Edit ${trip.title}`}
            >
              <Pencil className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => onDelete(trip.id)}
              className="p-1.5 rounded-lg hover:bg-ds-pen-stroke text-ds-text-tertiary hover:text-ds-warning transition min-h-[44px] min-w-[44px] flex items-center justify-center"
              aria-label={`Delete ${trip.title}`}
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Destination as editorial volume title */}
        <div className="flex-1">
          <p className="text-lg font-semibold text-ds-text leading-snug tracking-tight">
            {trip.destination}
          </p>
          <h3 className="text-sm text-ds-text-secondary mt-0.5">
            <Link
              href={`/trips/${trip.id}`}
              className="hover:text-ds-accent transition"
            >
              {trip.title}
            </Link>
          </h3>
        </div>
      </div>

      {/* Footer — dates and open action */}
      <div className="px-5 py-3 border-t border-ds-pen-stroke flex items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-3 text-xs text-ds-text-tertiary">
          <span className="flex items-center gap-1">
            <Calendar className="w-3 h-3" aria-hidden="true" />
            {formatDateRange(trip.startDate, trip.endDate)}
          </span>
          <span className="flex items-center gap-1">
            <Users className="w-3 h-3" aria-hidden="true" />
            {trip.travelers} {trip.travelers === 1 ? "traveler" : "travelers"}
          </span>
        </div>
        <Link
          href={`/trips/${trip.id}`}
          className="flex items-center gap-1 text-xs font-semibold text-ds-accent hover:text-ds-accent-muted transition min-h-[44px]"
        >
          Open <ArrowRight className="w-3 h-3" aria-hidden="true" />
        </Link>
      </div>
    </Card>
  );
}

// ── Trip section ──────────────────────────────────────────────────────────────

interface TripSectionProps {
  label: string;
  trips: Trip[];
  onEdit: (trip: Trip) => void;
  onDelete: (id: string) => void;
}

function TripSection({ label, trips, onEdit, onDelete }: TripSectionProps) {
  if (!trips.length) return null;
  return (
    <section aria-label={`${label} journeys`}>
      <Overline>{label} journeys</Overline>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {trips.map((trip) => (
          <JourneyCard
            key={trip.id}
            trip={trip}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        ))}
      </div>
    </section>
  );
}

// ── Planning tools strip ──────────────────────────────────────────────────────

function PlanningToolsStrip() {
  return (
    <section aria-label="Planning tools" data-testid="planning-tools-strip">
      <Overline>Planning tools</Overline>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Link
          href="/concierge"
          className="group flex items-center gap-3 p-4 rounded-xl border border-ds-pen-stroke bg-ds-carbon hover:border-ds-accent/40 hover:bg-ds-onyx transition-all duration-200"
        >
          <span className="flex items-center justify-center w-9 h-9 rounded-lg bg-ds-accent-subtle text-ds-accent shrink-0">
            <Sparkles className="w-4 h-4" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-medium text-ds-text group-hover:text-ds-accent transition">
              AI Concierge
            </p>
            <p className="text-xs text-ds-text-tertiary truncate">
              Personalised recommendations
            </p>
          </div>
          <ChevronRight
            className="w-4 h-4 text-ds-text-tertiary shrink-0 ml-auto"
            aria-hidden="true"
          />
        </Link>

        <Link
          href="/saved"
          className="group flex items-center gap-3 p-4 rounded-xl border border-ds-pen-stroke bg-ds-carbon hover:border-ds-accent/40 hover:bg-ds-onyx transition-all duration-200"
        >
          <span className="flex items-center justify-center w-9 h-9 rounded-lg bg-ds-accent-subtle text-ds-accent shrink-0">
            <BookmarkCheck className="w-4 h-4" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-medium text-ds-text group-hover:text-ds-accent transition">
              Saved Ideas
            </p>
            <p className="text-xs text-ds-text-tertiary truncate">
              Your travel scrapbook
            </p>
          </div>
          <ChevronRight
            className="w-4 h-4 text-ds-text-tertiary shrink-0 ml-auto"
            aria-hidden="true"
          />
        </Link>

        <Link
          href="/explore"
          className="group flex items-center gap-3 p-4 rounded-xl border border-ds-pen-stroke bg-ds-carbon hover:border-ds-accent/40 hover:bg-ds-onyx transition-all duration-200"
        >
          <span className="flex items-center justify-center w-9 h-9 rounded-lg bg-ds-accent-subtle text-ds-accent shrink-0">
            <Compass className="w-4 h-4" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-medium text-ds-text group-hover:text-ds-accent transition">
              Explore
            </p>
            <p className="text-xs text-ds-text-tertiary truncate">
              Hotels, restaurants &amp; more
            </p>
          </div>
          <ChevronRight
            className="w-4 h-4 text-ds-text-tertiary shrink-0 ml-auto"
            aria-hidden="true"
          />
        </Link>
      </div>
    </section>
  );
}

// ── Edit modal ────────────────────────────────────────────────────────────────

interface EditModalProps {
  trip: Trip;
  form: EditForm;
  saving: boolean;
  onChange: (form: EditForm) => void;
  onSave: () => void;
  onClose: () => void;
}

function EditModal({ trip, form, saving, onChange, onSave, onClose }: EditModalProps) {
  return (
    <div
      className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label={`Edit ${trip.title}`}
    >
      <Card
        as="div"
        tone="dark"
        className="p-6 w-full max-w-md"
        style={{ boxShadow: "var(--ds-elevation-4)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-ds-text">Edit Trip</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-ds-pen-stroke text-ds-text-tertiary hover:text-ds-text transition min-h-[44px] min-w-[44px] flex items-center justify-center"
            aria-label="Close edit dialog"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="label" htmlFor="edit-trip-name">
              Trip Name
            </label>
            <input
              id="edit-trip-name"
              className="input"
              value={form.title}
              onChange={(e) => onChange({ ...form, title: e.target.value })}
            />
          </div>
          <div>
            <label className="label" htmlFor="edit-start-date">
              Start Date
            </label>
            <input
              id="edit-start-date"
              type="date"
              className="input"
              value={form.startDate}
              onChange={(e) =>
                onChange({ ...form, startDate: e.target.value })
              }
            />
          </div>
          <div>
            <label className="label" htmlFor="edit-end-date">
              End Date
            </label>
            <input
              id="edit-end-date"
              type="date"
              className="input"
              value={form.endDate}
              onChange={(e) => onChange({ ...form, endDate: e.target.value })}
            />
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-6">
          <button onClick={onClose} className="btn-ghost">
            Cancel
          </button>
          <button
            onClick={onSave}
            disabled={saving || !form.title.trim()}
            className="btn-primary"
          >
            {saving ? "Saving…" : "Save Changes"}
          </button>
        </div>
      </Card>
    </div>
  );
}

// ── Delete confirm modal ──────────────────────────────────────────────────────

interface DeleteModalProps {
  tripId: string;
  onConfirm: (id: string) => void;
  onClose: () => void;
}

function DeleteModal({ tripId, onConfirm, onClose }: DeleteModalProps) {
  return (
    <div
      className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Confirm delete trip"
    >
      <Card
        as="div"
        tone="dark"
        className="p-6 w-full max-w-sm"
        style={{ boxShadow: "var(--ds-elevation-4)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-base font-semibold text-ds-text mb-2">
          Delete Trip
        </h2>
        <p className="text-sm text-ds-text-tertiary mb-6 leading-relaxed">
          This will permanently delete the trip and all its itinerary items.
          This cannot be undone.
        </p>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="btn-ghost">
            Cancel
          </button>
          <button
            onClick={() => onConfirm(tripId)}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-xl bg-ds-warning/15 text-ds-warning border border-ds-warning/30 hover:bg-ds-warning/25 transition min-h-[44px]"
          >
            Delete Trip
          </button>
        </div>
      </Card>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function TripsPage() {
  const [trips, setTrips] = useState<Trip[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingTrip, setEditingTrip] = useState<Trip | null>(null);
  const [editForm, setEditForm] = useState<EditForm>({
    title: "",
    startDate: "",
    endDate: "",
  });
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const result = await fetchTrips();
      setTrips(result);
      setLoading(false);
    }
    load();
  }, []);

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }

  function openEdit(trip: Trip) {
    setEditingTrip(trip);
    setEditForm({
      title: trip.title,
      startDate: trip.startDate ?? "",
      endDate: trip.endDate ?? "",
    });
  }

  async function handleUpdate() {
    if (!editingTrip) return;
    setSaving(true);
    try {
      const updated = await updateTrip(editingTrip.id, {
        title: editForm.title || undefined,
        startDate: editForm.startDate || undefined,
        endDate: editForm.endDate || undefined,
      });
      setTrips((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
      setEditingTrip(null);
      showToast("Trip updated");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(tripId: string) {
    await deleteTrip(tripId);
    setTrips((prev) => prev.filter((t) => t.id !== tripId));
    setConfirmDeleteId(null);
    showToast("Trip deleted");
  }

  if (loading) {
    return (
      <div className="space-y-8">
        {/* Header skeleton */}
        <div className="flex items-start justify-between gap-4 mb-8">
          <div className="space-y-2">
            <Skeleton className="h-8 w-44" />
            <Skeleton className="h-4 w-32" />
          </div>
          <Skeleton variant="button" className="w-32" />
        </div>
        <DashboardSkeleton />
      </div>
    );
  }

  const continuePlanning = pickContinuePlanning(trips);
  const continuePlanningId = continuePlanning?.id ?? null;

  const activeTrips = trips.filter(
    (t) =>
      getTripStatusGroup(t) === "Active" && t.id !== continuePlanningId,
  );
  const pastTrips = trips.filter((t) => getTripStatusGroup(t) === "Past");

  const hasAny = trips.length > 0;
  const tripLabel = `${trips.length} trip${trips.length !== 1 ? "s" : ""}`;

  return (
    <>
      {/* Toast */}
      {toast && (
        <div
          role="status"
          aria-live="polite"
          className="fixed bottom-4 right-4 z-50 bg-ds-onyx text-ds-text border border-ds-pen-stroke text-sm px-4 py-2.5 rounded-xl"
          style={{ boxShadow: "var(--ds-elevation-3)" }}
        >
          {toast}
        </div>
      )}

      {/* Edit modal */}
      {editingTrip && (
        <EditModal
          trip={editingTrip}
          form={editForm}
          saving={saving}
          onChange={setEditForm}
          onSave={handleUpdate}
          onClose={() => setEditingTrip(null)}
        />
      )}

      {/* Delete modal */}
      {confirmDeleteId && (
        <DeleteModal
          tripId={confirmDeleteId}
          onConfirm={handleDelete}
          onClose={() => setConfirmDeleteId(null)}
        />
      )}

      {/* Page header — editorial shelf heading */}
      <div className="flex items-start justify-between gap-4 mb-8">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-text-tertiary mb-1">
            Your Travel Shelf
          </p>
          <h1 className="text-2xl font-semibold text-ds-text">My Journeys</h1>
          {hasAny && (
            <p className="mt-1 text-sm text-ds-text-tertiary">{tripLabel}</p>
          )}
        </div>
        <div className="shrink-0">
          <Link
            href="/trips/new"
            className="btn-primary inline-flex items-center min-h-[44px]"
            data-testid="trips-new-trip-action"
          >
            <PlusCircle className="w-4 h-4" aria-hidden="true" />
            Plan a Trip
          </Link>
        </div>
      </div>

      {/* Body */}
      {!hasAny ? (
        <EmptyDashboard />
      ) : (
        <div className="space-y-8">
          {/* Continue planning hero */}
          {continuePlanning && (
            <ContinuePlanningHero
              trip={continuePlanning}
              onEdit={openEdit}
              onDelete={(id) => setConfirmDeleteId(id)}
            />
          )}

          {/* Active journeys grid (excluding the hero trip) */}
          <TripSection
            label="Active"
            trips={activeTrips}
            onEdit={openEdit}
            onDelete={(id) => setConfirmDeleteId(id)}
          />

          {/* Past journeys grid */}
          <TripSection
            label="Past"
            trips={pastTrips}
            onEdit={openEdit}
            onDelete={(id) => setConfirmDeleteId(id)}
          />

          {/* Planning tools */}
          <PlanningToolsStrip />
        </div>
      )}
    </>
  );
}
