"use client";

import { useState, useEffect } from "react";
import type { ReactNode } from "react";
import Link from "next/link";
import {
  PlusCircle,
  Users,
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

// Status rendered as quiet small-caps text (not a colored pill) — the Reading
// Room reads as an editorial library, not a dashboard of status chips.
const STATUS_LABEL: Record<TripStatus, string> = {
  draft: "Draft",
  researching: "Researching",
  planned: "Planned",
  booked: "Booked",
  completed: "Completed",
  archived: "Archived",
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

// ── Status text — small-caps editorial label, never a colored pill ────────────

function StatusText({
  status,
  past = false,
}: {
  status: TripStatus;
  past?: boolean;
}) {
  return (
    <span
      className={
        past ? "trips-volume-status trips-volume-status-past" : "trips-volume-status"
      }
      data-testid="trip-status-text"
    >
      {STATUS_LABEL[status] ?? STATUS_LABEL.draft}
    </span>
  );
}

// ── Chapter header — editorial section rule (not a tab or labelled box) ───────

function Chapter({
  title,
  count,
}: {
  title: string;
  count?: string;
}) {
  return (
    <div className="trips-chapter" data-testid="trips-chapter">
      <h3 className="trips-chapter-title">{title}</h3>
      <span className="trips-chapter-rule" aria-hidden="true" />
      {count ? (
        <span className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-folio-ink-mist shrink-0">
          {count}
        </span>
      ) : null}
    </div>
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
      <Skeleton variant="card" className="h-56 w-full" />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} variant="card" className="h-48" />
        ))}
      </div>
    </div>
  );
}

// ── Empty state — an empty shelf, waiting for its first volume ────────────────

function EmptyDashboard() {
  return (
    <div className="trips-empty-shelf" data-testid="trips-empty-state">
      {/* A single bound-spine / plate motif — the first volume, not yet written */}
      <div className="trips-empty-plate" aria-hidden="true" />
      <h2 className="trips-shelf-heading text-center" data-testid="empty-state-heading">
        An empty shelf, waiting for its first volume.
      </h2>
      <p className="trips-empty-lede">
        Your journey starts here — name a destination and the concierge will help
        you bind the first edition: flights, stays, tables, and the moments in
        between.
      </p>
      <div className="trips-empty-actions">
        <Link
          href="/trips/new"
          className="btn-marine inline-flex items-center"
          data-testid="trips-empty-action-plan"
        >
          <PlusCircle className="w-4 h-4" />
          Begin your first journey
        </Link>
      </div>
      <p className="trips-empty-aside">
        Already have places in mind?{" "}
        <Link
          href="/saved"
          className="text-ds-marine-ink hover:text-ds-marine-soft font-medium transition"
        >
          Open your saved ideas
        </Link>
        , or{" "}
        <Link
          href="/concierge"
          className="text-ds-marine-ink hover:text-ds-marine-soft font-medium transition"
          data-testid="trips-empty-action-concierge"
        >
          Ask the AI Concierge
        </Link>
        .
      </p>
    </div>
  );
}

// ── Edition plate — the single cinematic moment (typeset monogram, no photo) ──

function EditionPlate({ trip }: { trip: Trip }) {
  const monogram = (trip.destination || trip.title || "·").trim().charAt(0).toUpperCase();
  return (
    <div className="trips-edition-plate" data-testid="trips-edition-plate" aria-hidden="true">
      <span className="trips-edition-plate-label">Current edition</span>
      <span className="trips-edition-plate-monogram">{monogram}</span>
      <span className="trips-edition-plate-bar" />
    </div>
  );
}

// ── Current edition — the open volume on the desk ─────────────────────────────

interface ContinuePlanningHeroProps {
  trip: Trip;
  onEdit: (trip: Trip) => void;
  onDelete: (id: string) => void;
}

function ContinuePlanningHero({ trip, onEdit, onDelete }: ContinuePlanningHeroProps) {
  return (
    <section aria-label="Continue planning your trip">
      <article
        className="folio-paper-panel folio-journey-entry trips-edition flex flex-col lg:flex-row"
        data-testid="continue-planning-hero"
      >
        {/* Left spread — the editorial page */}
        <div
          className="trips-edition-spread flex-1 min-w-0"
          data-testid="continue-planning-main"
        >
          <p className="folio-issue-eyebrow mb-3" data-testid="continue-planning-eyebrow">
            Continue planning
          </p>
          <p
            className="trips-volume-destination trips-hero-destination"
            data-testid="continue-planning-destination"
          >
            {trip.destination}
          </p>
          <h2 className="text-base font-medium text-ds-folio-ink-soft mt-2 leading-snug">
            {trip.title}
          </h2>
          <p className="folio-caption mt-4" data-testid="continue-planning-metadata">
            {formatDateRange(trip.startDate, trip.endDate)}
            {trip.travelers
              ? ` · ${trip.travelers} ${trip.travelers === 1 ? "traveler" : "travelers"}`
              : ""}
            {trip.budgetCash
              ? ` · ${formatBudget(Number(trip.budgetCash), trip.budgetCurrency)}`
              : ""}
          </p>

          <div
            className="trips-edition-actions flex flex-wrap gap-2 items-center"
            data-testid="continue-planning-aside"
          >
            <Link
              href={`/trips/${trip.id}`}
              className="btn-marine inline-flex items-center justify-center"
            >
              Open Trip
              <ArrowRight className="w-4 h-4 ml-1" />
            </Link>
            <Link
              href="/concierge"
              className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border border-ds-hairline bg-ds-warm-paper text-ds-folio-ink-soft text-sm font-medium hover:border-ds-marine-ink/40 hover:text-ds-marine-ink transition-all duration-200 min-h-[44px]"
            >
              <Sparkles className="w-4 h-4" aria-hidden="true" />
              AI Concierge
            </Link>
            {/* Edit/delete — quiet, secondary, pushed to the end of the row */}
            <div className="flex items-center gap-0.5 sm:ml-auto">
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
        </div>

        {/* Right column — the single cinematic plate + the compact reference
            drawer stacked beneath it (integrated into the current edition). */}
        <div className="trips-edition-aside" data-testid="trips-reference-drawer">
          <EditionPlate trip={trip} />
          <PlanningToolsStrip />
        </div>
      </article>
    </section>
  );
}

// ── Journey volume — a bound travel volume on the shelf ───────────────────────

interface JourneyCardProps {
  trip: Trip;
  onEdit: (trip: Trip) => void;
  onDelete: (id: string) => void;
  past?: boolean;
}

function JourneyCard({ trip, onEdit, onDelete, past = false }: JourneyCardProps) {
  return (
    <FolioCard
      className={`group folio-paper-card folio-journey-entry trips-volume flex flex-col transition-shadow duration-200${
        past ? " trips-volume-past" : ""
      }`}
      data-testid="journey-card"
    >
      {/* Volume cover body — destination as the visual hero */}
      <div className="trips-volume-cover flex-1 p-5 pb-3 flex flex-col gap-1.5">
        <div className="flex items-start justify-between gap-3">
          <h3 className="trips-volume-destination flex-1 min-w-0" data-testid="journey-card-destination">
            <Link
              href={`/trips/${trip.id}`}
              className="hover:text-ds-marine-ink transition"
            >
              {trip.destination}
            </Link>
          </h3>
          <StatusText status={getDisplayTripStatus(trip)} past={past} />
        </div>
        <p className="text-sm text-ds-folio-ink-soft leading-snug">{trip.title}</p>
        {/* Editorial caption — date range in italic editorial serif (real data) */}
        <p className="folio-caption mt-auto pt-1.5" data-testid="journey-card-date-caption">
          {formatDateRange(trip.startDate, trip.endDate)}
        </p>
      </div>

      {/* Volume footer — travelers, quiet edit/delete, open link */}
      <div className="px-5 py-3 border-t border-ds-hairline bg-ds-bone flex items-center justify-between gap-2">
        <div
          className="flex items-center gap-1"
          data-testid="journey-card-edit-controls"
        >
          <span className="flex items-center gap-1 text-xs text-ds-folio-ink-mist mr-1">
            <Users className="w-3 h-3" aria-hidden="true" />
            {trip.travelers} {trip.travelers === 1 ? "traveler" : "travelers"}
          </span>
          {/* Quiet on desktop (hover/focus-revealed), always accessible on mobile */}
          <button
            onClick={() => onEdit(trip)}
            className="trips-volume-manage p-1 rounded hover:bg-ds-linen text-ds-folio-ink-mist hover:text-ds-folio-ink transition min-h-[44px] min-w-[44px] flex items-center justify-center"
            aria-label={`Edit ${trip.title}`}
          >
            <Pencil className="w-3 h-3" />
          </button>
          <button
            onClick={() => onDelete(trip.id)}
            className="trips-volume-manage p-1 rounded hover:bg-ds-linen text-ds-folio-ink-mist hover:text-ds-warning transition min-h-[44px] min-w-[44px] flex items-center justify-center"
            aria-label={`Delete ${trip.title}`}
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
        <Link
          href={`/trips/${trip.id}`}
          className="flex items-center gap-1 text-xs font-semibold text-ds-marine-ink hover:text-ds-marine-soft transition min-h-[44px]"
        >
          {past ? "Revisit" : "Open"} <ArrowRight className="w-3 h-3" aria-hidden="true" />
        </Link>
      </div>
    </FolioCard>
  );
}

// ── Trip section — a chapter of volumes ───────────────────────────────────────

interface TripSectionProps {
  title: string;
  trips: Trip[];
  onEdit: (trip: Trip) => void;
  onDelete: (id: string) => void;
  past?: boolean;
  /** dense = lives in the two-column lower shelf (half width): 1-up, 2-up at xl. */
  dense?: boolean;
}

function TripSection({ title, trips, onEdit, onDelete, past = false, dense = false }: TripSectionProps) {
  if (!trips.length) return null;
  const count = `${trips.length} ${past ? "completed" : "in progress"}`;
  return (
    <section aria-label={`${title} journeys`}>
      <Chapter title={title} count={count} />
      <div
        className={
          dense
            ? "grid grid-cols-1 xl:grid-cols-2 gap-5"
            : "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5"
        }
        data-testid="journey-card-grid"
      >
        {trips.map((trip) => (
          <JourneyCard
            key={trip.id}
            trip={trip}
            onEdit={onEdit}
            onDelete={onDelete}
            past={past}
          />
        ))}
      </div>
    </section>
  );
}

// ── Reference drawer — "Elsewhere in the house" (compact stacked rail) ────────
// Integrated into the current-edition right column on desktop (under the plate)
// and stacked there on mobile — never a separate full-width chapter.

function ReferenceLink({
  href,
  label,
  hint,
  children,
}: {
  href: string;
  label: string;
  hint: string;
  children: ReactNode;
}) {
  return (
    <Link
      href={href}
      className="group flex items-center gap-2.5 px-3.5 py-2.5 hover:bg-ds-linen transition-colors duration-150 min-h-[44px]"
    >
      <span className="flex items-center justify-center w-7 h-7 rounded-lg bg-ds-accent-subtle text-ds-accent shrink-0">
        {children}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-[13px] font-medium text-ds-folio-ink group-hover:text-ds-marine-ink transition-colors leading-tight">
          {label}
        </p>
        <p className="text-[11px] text-ds-folio-ink-mist truncate">{hint}</p>
      </div>
      <ChevronRight
        className="w-3.5 h-3.5 text-ds-folio-ink-mist shrink-0 group-hover:text-ds-marine-ink transition-colors"
        aria-hidden="true"
      />
    </Link>
  );
}

function PlanningToolsStrip() {
  return (
    <section
      aria-label="Planning tools"
      data-testid="planning-tools-strip"
      className="trips-reference-rail"
    >
      <p className="folio-muted-label trips-reference-label">Elsewhere in the house</p>
      <div className="trips-tool-panel bg-ds-bone">
        <div className="flex flex-col divide-y divide-ds-hairline">
          <ReferenceLink href="/concierge" label="The Concierge" hint="A composed second opinion">
            <Sparkles className="w-3.5 h-3.5" aria-hidden="true" />
          </ReferenceLink>
          <ReferenceLink href="/saved" label="Saved Ideas" hint="Loose clippings, kept">
            <BookmarkCheck className="w-3.5 h-3.5" aria-hidden="true" />
          </ReferenceLink>
          <ReferenceLink href="/explore" label="Explore" hint="Hotels, tables &amp; more">
            <Compass className="w-3.5 h-3.5" aria-hidden="true" />
          </ReferenceLink>
        </div>
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
              onChange={(e) => onChange({ ...form, startDate: e.target.value })}
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
      <div className="trips-room-canvas">
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
      </div>
    );
  }

  const continuePlanning = pickContinuePlanning(trips);
  const continuePlanningId = continuePlanning?.id ?? null;

  const activeTrips = trips.filter(
    (t) => getTripStatusGroup(t) === "Active" && t.id !== continuePlanningId,
  );
  const pastTrips = trips.filter((t) => getTripStatusGroup(t) === "Past");

  const hasAny = trips.length > 0;
  const activeCount = trips.filter((t) => getTripStatusGroup(t) === "Active").length;
  const roomSub = `${trips.length} ${trips.length === 1 ? "volume" : "volumes"} on the shelf${
    activeCount ? ` · ${activeCount} in progress` : ""
  }`;
  // When both shelves have volumes, balance them into a desktop two-column shelf
  // (On the table | Bound) so a small count doesn't strand one card with a big gap.
  const lowerTwoCol = activeTrips.length > 0 && pastTrips.length > 0;

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

      {/* The Reading Room — a floating paper folio library on a warm canvas */}
      <div className="trips-room-canvas">
      <div className="trips-shelf-stage" data-testid="trips-shelf-stage">
        {/* Masthead — the library line */}
        <div className="trips-shelf-masthead" data-testid="my-trips-page-header">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <p className="folio-issue-eyebrow mb-2" data-testid="trips-shelf-eyebrow">
                The Folio Library
              </p>
              <h1 className="trips-shelf-heading" data-testid="trips-shelf-heading">
                My Journeys
              </h1>
              {hasAny && <p className="folio-caption mt-2">{roomSub}</p>}
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

        {/* Shelf body */}
        <div className="trips-shelf-body">
          {!hasAny ? (
            <EmptyDashboard />
          ) : (
            <div className="flex flex-col gap-7">
              {/* The current edition — open on the desk, with the reference
                  drawer integrated into its right column (above the fold). */}
              {continuePlanning && (
                <div>
                  <Chapter title="The current edition" />
                  <ContinuePlanningHero
                    trip={continuePlanning}
                    onEdit={openEdit}
                    onDelete={(id) => setConfirmDeleteId(id)}
                  />
                </div>
              )}

              {/* Fallback: no current edition (e.g. only past trips) — surface
                  the reference drawer on its own so the routes stay reachable. */}
              {!continuePlanning && <PlanningToolsStrip />}

              {/* Lower shelves — balanced two-column on desktop when both have
                  volumes; otherwise a single full-width shelf. Single column on
                  mobile either way. */}
              {lowerTwoCol ? (
                <div
                  className="grid grid-cols-1 lg:grid-cols-2 gap-7 lg:gap-8"
                  data-testid="trips-lower-shelf"
                >
                  <TripSection
                    title="On the table"
                    trips={activeTrips}
                    onEdit={openEdit}
                    onDelete={(id) => setConfirmDeleteId(id)}
                    dense
                  />
                  <TripSection
                    title="Bound"
                    trips={pastTrips}
                    onEdit={openEdit}
                    onDelete={(id) => setConfirmDeleteId(id)}
                    past
                    dense
                  />
                </div>
              ) : (
                <>
                  <TripSection
                    title="On the table"
                    trips={activeTrips}
                    onEdit={openEdit}
                    onDelete={(id) => setConfirmDeleteId(id)}
                  />
                  <TripSection
                    title="Bound"
                    trips={pastTrips}
                    onEdit={openEdit}
                    onDelete={(id) => setConfirmDeleteId(id)}
                    past
                  />
                </>
              )}
            </div>
          )}
        </div>
      </div>
      </div>
    </>
  );
}
