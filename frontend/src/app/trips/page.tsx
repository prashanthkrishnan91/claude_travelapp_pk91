"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  PlusCircle,
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
import { Skeleton } from "@/components/ui/Skeleton";
import { TripStatusBadge } from "@/components/ui/TripStatusBadge";
import { fetchTrips, updateTrip, deleteTrip } from "@/lib/api";
import { getDisplayTripStatus, getTripStatusGroup } from "@/lib/tripStatus";
import { FolioCard } from "@/components/ui/Folio";
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

// Derive a short folio serial code from the trip destination (first 3 letters)
function deriveSerialCode(destination?: string): string {
  if (!destination) return "---";
  const clean = destination.replace(/[^a-zA-Z]/g, "");
  return clean.substring(0, 3).toUpperCase() || "---";
}

interface EditForm {
  title: string;
  startDate: string;
  endDate: string;
}

// ── Overline label ────────────────────────────────────────────────────────────

function Overline({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-folio-ink-mist mb-3">
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
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {[1, 2].map((i) => (
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
      <div className="text-center py-10 px-4">
        <div className="flex items-center justify-center w-16 h-16 rounded-2xl bg-ds-accent-subtle border border-ds-hairline text-ds-accent mx-auto mb-6">
          <Map className="w-8 h-8" />
        </div>
        <h2
          className="trips-shelf-heading text-center mb-2"
          data-testid="empty-state-heading"
        >
          Your journey starts here.
        </h2>
        <p className="text-ds-folio-ink-mist max-w-sm mx-auto leading-relaxed text-sm">
          Plan your first trip with an AI travel concierge that thinks about
          every detail — flights, stays, restaurants, and the moments in
          between.
        </p>
      </div>

      {/* Action cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <FolioCard className="p-6 flex flex-col gap-4 transition-shadow duration-200" data-testid="trips-empty-action-plan">
          <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-ds-accent-subtle text-ds-accent">
            <PlusCircle className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-ds-folio-ink mb-1">
              Plan a Trip
            </h3>
            <p className="text-sm text-ds-folio-ink-mist leading-relaxed">
              Name your destination, set dates, and let the planning canvas
              help you build a complete itinerary.
            </p>
          </div>
          <div className="mt-auto">
            <Link href="/trips/new" className="btn-marine inline-flex items-center">
              <PlusCircle className="w-4 h-4" />
              New Trip
            </Link>
          </div>
        </FolioCard>

        <FolioCard className="p-6 flex flex-col gap-4 transition-shadow duration-200" data-testid="trips-empty-action-concierge">
          <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-ds-accent-subtle text-ds-accent">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-ds-folio-ink mb-1">
              Ask the AI Concierge
            </h3>
            <p className="text-sm text-ds-folio-ink-mist leading-relaxed">
              Get personalised recommendations for hotels, restaurants, and
              activities — anywhere in the world.
            </p>
          </div>
          <div className="mt-auto">
            <Link
              href="/concierge"
              className="inline-flex items-center gap-2 min-h-[44px] text-sm font-semibold text-ds-marine-ink hover:text-ds-marine-soft transition"
            >
              Open Concierge <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </FolioCard>
      </div>

      {/* Saved ideas nudge */}
      <p className="text-center text-sm text-ds-folio-ink-mist">
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

// ── Continue planning hero — featured current volume ──────────────────────────

interface ContinuePlanningHeroProps {
  trip: Trip;
  onEdit: (trip: Trip) => void;
  onDelete: (id: string) => void;
}

function ContinuePlanningHero({ trip, onEdit, onDelete }: ContinuePlanningHeroProps) {
  const serialCode = deriveSerialCode(trip.destination);

  return (
    <section aria-label="Continue planning your trip">
      <p
        className="folio-issue-eyebrow mb-3"
        data-testid="continue-planning-eyebrow"
      >
        Continue planning
      </p>
      <article
        className="folio-paper-panel folio-journey-entry transition-shadow duration-200"
        data-testid="continue-planning-hero"
      >
        {/* Folio cover tab — restrained brass detail at very top */}
        <div className="folio-cover-tab" aria-hidden="true" />

        {/* Featured volume cover zone — warm gradient, richer editorial depth */}
        <div className="trips-featured-volume px-6 pt-5 pb-4">
          {/* Serial + edit/delete row */}
          <div className="flex items-start justify-between gap-2 mb-4">
            <p
              className="folio-serial"
              data-testid="continue-planning-serial"
            >
              {serialCode} · Current Journey
            </p>
            {/* Edit/delete — accessible, visually secondary */}
            <div className="flex items-center gap-0.5 shrink-0">
              <button
                onClick={() => onEdit(trip)}
                className="p-1.5 rounded-lg hover:bg-ds-linen text-ds-folio-ink-mist hover:text-ds-folio-ink transition min-h-[44px] min-w-[44px] flex items-center justify-center"
                aria-label={`Edit ${trip.title}`}
              >
                <Pencil className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => onDelete(trip.id)}
                className="p-1.5 rounded-lg hover:bg-ds-linen text-ds-folio-ink-mist hover:text-ds-warning transition min-h-[44px] min-w-[44px] flex items-center justify-center"
                aria-label={`Delete ${trip.title}`}
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Volume title — destination as the editorial focal point */}
          <div className="mb-3">
            <p
              className="trips-volume-destination trips-hero-destination"
              data-testid="continue-planning-destination"
            >
              {trip.destination}
            </p>
            <div className="flex flex-wrap items-center gap-2 mt-2">
              <h2 className="text-sm font-medium text-ds-folio-ink-soft leading-snug">
                {trip.title}
              </h2>
              <TripStatusBadge status={getDisplayTripStatus(trip)} />
            </div>
          </div>

          {/* Folio caption — dates + travelers + budget as one italic metadata line */}
          <p className="folio-caption" data-testid="continue-planning-metadata">
            {formatDateRange(trip.startDate, trip.endDate)}
            {trip.travelers
              ? ` · ${trip.travelers} ${trip.travelers === 1 ? "traveler" : "travelers"}`
              : ""}
            {trip.budgetCash
              ? ` · ${formatBudget(Number(trip.budgetCash), trip.budgetCurrency)}`
              : ""}
          </p>
        </div>

        {/* Action footer — unchanged behavior */}
        <div className="px-6 py-4 flex flex-wrap gap-2 bg-ds-warm-paper border-t border-ds-hairline">
          <Link
            href={`/trips/${trip.id}`}
            className="btn-marine inline-flex items-center"
          >
            Open Trip
            <ArrowRight className="w-4 h-4 ml-1" />
          </Link>
          <Link
            href="/concierge"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-ds-hairline bg-ds-bone text-ds-folio-ink-soft text-sm font-medium hover:border-ds-marine-ink/40 hover:text-ds-marine-ink transition-all duration-200 min-h-[44px]"
          >
            <Sparkles className="w-4 h-4" aria-hidden="true" />
            AI Concierge
          </Link>
        </div>
      </article>
    </section>
  );
}

// ── Journey card — personal travel volume ─────────────────────────────────────

interface JourneyCardProps {
  trip: Trip;
  onEdit: (trip: Trip) => void;
  onDelete: (id: string) => void;
}

function JourneyCard({ trip, onEdit, onDelete }: JourneyCardProps) {
  const serialCode = deriveSerialCode(trip.destination);

  return (
    <article
      className="folio-paper-card folio-journey-entry flex flex-col transition-shadow duration-200"
      data-testid="journey-card"
    >
      {/* Folio cover tab — restrained brass detail */}
      <div className="folio-cover-tab" aria-hidden="true" />

      {/* Volume cover body — warm paper-to-bone gradient */}
      <div className="trips-volume-cover flex-1 p-5 pb-3 flex flex-col gap-2">
        {/* Folio serial + status badge */}
        <div className="flex items-center justify-between gap-2">
          <p className="folio-serial" data-testid="journey-card-serial">
            {serialCode} · {getDisplayTripStatus(trip)}
          </p>
          <TripStatusBadge status={getDisplayTripStatus(trip)} />
        </div>

        {/* Destination as editorial volume title — the card hero */}
        <div className="flex-1 mt-1">
          <p
            className="trips-volume-destination"
            data-testid="journey-card-destination"
          >
            {trip.destination}
          </p>
          <h3 className="text-sm text-ds-folio-ink-soft mt-0.5 leading-snug">
            <Link
              href={`/trips/${trip.id}`}
              className="hover:text-ds-marine-ink transition"
            >
              {trip.title}
            </Link>
          </h3>
          {/* Editorial caption — date range in italic Fraunces */}
          <p
            className="folio-caption mt-1.5"
            data-testid="journey-card-date-caption"
          >
            {formatDateRange(trip.startDate, trip.endDate)}
          </p>
        </div>
      </div>

      {/* Volume footer — travelers, edit/delete, open link */}
      <div
        className="px-5 py-3 border-t border-ds-hairline flex items-center justify-between gap-2 bg-ds-bone"
      >
        <div className="flex items-center gap-1" data-testid="journey-card-edit-controls">
          <span className="flex items-center gap-1 text-xs text-ds-folio-ink-mist mr-1">
            <Users className="w-3 h-3" aria-hidden="true" />
            {trip.travelers}{" "}
            {trip.travelers === 1 ? "traveler" : "travelers"}
          </span>
          {/* Edit/delete demoted to secondary footer position */}
          <button
            onClick={() => onEdit(trip)}
            className="p-1 rounded hover:bg-ds-linen text-ds-folio-ink-mist hover:text-ds-folio-ink transition min-h-[44px] min-w-[44px] flex items-center justify-center"
            aria-label={`Edit ${trip.title}`}
          >
            <Pencil className="w-3 h-3" />
          </button>
          <button
            onClick={() => onDelete(trip.id)}
            className="p-1 rounded hover:bg-ds-linen text-ds-folio-ink-mist hover:text-ds-warning transition min-h-[44px] min-w-[44px] flex items-center justify-center"
            aria-label={`Delete ${trip.title}`}
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
        <Link
          href={`/trips/${trip.id}`}
          className="flex items-center gap-1 text-xs font-semibold text-ds-marine-ink hover:text-ds-marine-soft transition min-h-[44px]"
        >
          Open <ArrowRight className="w-3 h-3" aria-hidden="true" />
        </Link>
      </div>
    </article>
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
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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

// ── Planning tools strip — integrated shelf rail ──────────────────────────────

function PlanningToolsStrip() {
  return (
    <section
      aria-label="Planning tools"
      data-testid="planning-tools-strip"
      className="trips-tools-shelf"
    >
      <Overline>Planning tools</Overline>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Link
          href="/concierge"
          className="group flex items-center gap-3 p-4 rounded-xl border border-ds-hairline bg-ds-bone hover:border-ds-marine-ink/40 transition-all duration-200"
        >
          <span className="flex items-center justify-center w-9 h-9 rounded-lg bg-ds-accent-subtle text-ds-accent shrink-0">
            <Sparkles className="w-4 h-4" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-medium text-ds-folio-ink group-hover:text-ds-marine-ink transition">
              AI Concierge
            </p>
            <p className="text-xs text-ds-folio-ink-mist truncate">
              Personalised recommendations
            </p>
          </div>
          <ChevronRight
            className="w-4 h-4 text-ds-folio-ink-mist shrink-0 ml-auto"
            aria-hidden="true"
          />
        </Link>

        <Link
          href="/saved"
          className="group flex items-center gap-3 p-4 rounded-xl border border-ds-hairline bg-ds-bone hover:border-ds-marine-ink/40 transition-all duration-200"
        >
          <span className="flex items-center justify-center w-9 h-9 rounded-lg bg-ds-accent-subtle text-ds-accent shrink-0">
            <BookmarkCheck className="w-4 h-4" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-medium text-ds-folio-ink group-hover:text-ds-marine-ink transition">
              Saved Ideas
            </p>
            <p className="text-xs text-ds-folio-ink-mist truncate">
              Your travel scrapbook
            </p>
          </div>
          <ChevronRight
            className="w-4 h-4 text-ds-folio-ink-mist shrink-0 ml-auto"
            aria-hidden="true"
          />
        </Link>

        <Link
          href="/explore"
          className="group flex items-center gap-3 p-4 rounded-xl border border-ds-hairline bg-ds-bone hover:border-ds-marine-ink/40 transition-all duration-200"
        >
          <span className="flex items-center justify-center w-9 h-9 rounded-lg bg-ds-accent-subtle text-ds-accent shrink-0">
            <Compass className="w-4 h-4" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-medium text-ds-folio-ink group-hover:text-ds-marine-ink transition">
              Explore
            </p>
            <p className="text-xs text-ds-folio-ink-mist truncate">
              Hotels, restaurants &amp; more
            </p>
          </div>
          <ChevronRight
            className="w-4 h-4 text-ds-folio-ink-mist shrink-0 ml-auto"
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
      <div
        className="folio-paper-panel p-6 w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-ds-folio-ink">Edit Trip</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-ds-linen text-ds-folio-ink-mist hover:text-ds-folio-ink transition min-h-[44px] min-w-[44px] flex items-center justify-center"
            aria-label="Close edit dialog"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="folio-muted-label block mb-1.5" htmlFor="edit-trip-name">
              Trip Name
            </label>
            <input
              id="edit-trip-name"
              className="folio-input"
              value={form.title}
              onChange={(e) => onChange({ ...form, title: e.target.value })}
            />
          </div>
          <div>
            <label className="folio-muted-label block mb-1.5" htmlFor="edit-start-date">
              Start Date
            </label>
            <input
              id="edit-start-date"
              type="date"
              className="folio-input"
              value={form.startDate}
              onChange={(e) =>
                onChange({ ...form, startDate: e.target.value })
              }
            />
          </div>
          <div>
            <label className="folio-muted-label block mb-1.5" htmlFor="edit-end-date">
              End Date
            </label>
            <input
              id="edit-end-date"
              type="date"
              className="folio-input"
              value={form.endDate}
              onChange={(e) => onChange({ ...form, endDate: e.target.value })}
            />
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-6">
          <button
            onClick={onClose}
            className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg border border-ds-hairline text-ds-folio-ink-soft hover:bg-ds-linen transition min-h-[44px] text-sm font-medium"
          >
            Cancel
          </button>
          <button
            onClick={onSave}
            disabled={saving || !form.title.trim()}
            className="btn-marine"
          >
            {saving ? "Saving…" : "Save Changes"}
          </button>
        </div>
      </div>
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
      <div
        className="folio-paper-panel p-6 w-full max-w-sm"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-base font-semibold text-ds-folio-ink mb-2">
          Delete Trip
        </h2>
        <p className="text-sm text-ds-folio-ink-mist mb-6 leading-relaxed">
          This will permanently delete the trip and all its itinerary items.
          This cannot be undone.
        </p>
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg border border-ds-hairline text-ds-folio-ink-soft hover:bg-ds-linen transition min-h-[44px] text-sm font-medium"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(tripId)}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-ds-warning/15 text-ds-warning border border-ds-warning/30 hover:bg-ds-warning/25 transition min-h-[44px]"
          >
            Delete Trip
          </button>
        </div>
      </div>
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
      <div className="trips-shelf-stage" data-testid="trips-shelf-stage">
        <div className="trips-shelf-masthead">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-2">
              <Skeleton className="h-8 w-44" />
              <Skeleton className="h-4 w-32" />
            </div>
            <Skeleton variant="button" className="w-32" />
          </div>
        </div>
        <div className="trips-shelf-body">
          <DashboardSkeleton />
        </div>
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
      {/* Toast — fixed, outside the shelf stage */}
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

      {/* Edit modal — fixed, outside the shelf stage */}
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

      {/* Delete modal — fixed, outside the shelf stage */}
      {confirmDeleteId && (
        <DeleteModal
          tripId={confirmDeleteId}
          onConfirm={handleDelete}
          onClose={() => setConfirmDeleteId(null)}
        />
      )}

      {/* Floating paper shelf stage — the containing travel shelf */}
      <div className="trips-shelf-stage" data-testid="trips-shelf-stage">
        {/* Shelf masthead — linen-tinted header zone with bottom hairline */}
        <div
          className="trips-shelf-masthead"
          data-testid="my-trips-page-header"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <p
                className="folio-issue-eyebrow mb-2"
                data-testid="trips-shelf-eyebrow"
              >
                Your Travel Shelf
              </p>
              <h1
                className="trips-shelf-heading"
                data-testid="trips-shelf-heading"
              >
                My Journeys
              </h1>
              {hasAny && (
                <p className="mt-1 text-sm text-ds-folio-ink-mist">{tripLabel}</p>
              )}
            </div>
            <div className="shrink-0 pt-1">
              <Link
                href="/trips/new"
                className="btn-marine inline-flex items-center"
                data-testid="trips-new-trip-action"
              >
                <PlusCircle className="w-4 h-4" aria-hidden="true" />
                Plan a Trip
              </Link>
            </div>
          </div>
        </div>

        {/* Shelf body — volume content zone */}
        <div className="trips-shelf-body">
          {!hasAny ? (
            <EmptyDashboard />
          ) : (
            <div className="space-y-8">
              {/* Featured current volume */}
              {continuePlanning && (
                <ContinuePlanningHero
                  trip={continuePlanning}
                  onEdit={openEdit}
                  onDelete={(id) => setConfirmDeleteId(id)}
                />
              )}

              {/* Active journeys grid */}
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

              {/* Planning tools — integrated shelf rail */}
              <PlanningToolsStrip />
            </div>
          )}
        </div>
      </div>
    </>
  );
}
