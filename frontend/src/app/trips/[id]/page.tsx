"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  CalendarDays,
  ChevronDown,
  ChevronLeft,
  Pencil,
  Sparkles,
  Trash2,
  X,
  Zap,
} from "lucide-react";
import { TripBuilder } from "@/components/trips/TripBuilder";
import { TripBrief } from "@/components/trips/TripBrief";
import { Dayboard } from "@/components/trips/Dayboard";
import { ExpandedDayPanel } from "@/components/trips/ExpandedDayPanel";
import { AddToDayDrawer } from "@/components/trips/AddToDayDrawer";
import type { AddToDayVertical } from "@/components/trips/AddToDayDrawer";
import { IdeasTray } from "@/components/trips/IdeasTray";
import { MapFoldOut } from "@/components/trips/MapFoldOut";
import { TripReadinessCockpit } from "@/components/trips/TripReadinessCockpit";
import { OptimizeTripModal } from "@/components/trips/OptimizeTripModal";
import { AIConciergePanel } from "@/components/trips/AIConciergePanel";
import {
  fetchTrip,
  ensureTripDays,
  fetchTripContext,
  fetchTripIdeas,
  assignIdeaToDay,
  unplaceItemToIdeas,
  updateIdeaMeta,
  deleteItem,
  updateTrip,
  deleteTrip,
} from "@/lib/api";
import type { Trip, TripContext, ItineraryDay, ItineraryItem } from "@/types";

interface EditForm {
  title: string;
  startDate: string;
  endDate: string;
}

// ── Shared button classes ─────────────────────────────────────────────────────

const COVER_BTN_BASE =
  "inline-flex items-center gap-1.5 px-3 py-2 min-h-[44px] rounded-lg text-xs font-medium transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2";

// Quiet icon-only buttons for the secondary cover actions — the hero is a trip
// folio, not an admin panel, so Optimize/Edit/Delete recede to a calm overflow
// row and Delete only warms to its warning tone on hover.
const COVER_ICON_BASE =
  "inline-flex items-center justify-center min-h-[44px] min-w-[44px] rounded-lg transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2";

const COVER_PRIMARY = `${COVER_BTN_BASE} bg-ds-marine-ink text-ds-paper hover:bg-ds-marine-soft`;
const COVER_GHOST = `${COVER_ICON_BASE} text-ds-text-tertiary hover:text-ds-text`;
const COVER_DANGER = `${COVER_ICON_BASE} text-ds-text-tertiary hover:text-ds-warning`;

// ── Mobile workspace IA ───────────────────────────────────────────────────────

type MobileWorkspace = "brief" | "build" | "itinerary" | "ideas";

// Build is intentionally omitted from mobile nav — it is the internal
// implementation surface reached via the Add-to-Day handoff from Itinerary.
const WORKSPACE_TABS: { id: MobileWorkspace; label: string; testId: string }[] = [
  { id: "brief",     label: "Brief",     testId: "trip-mobile-tab-brief"     },
  { id: "itinerary", label: "Itinerary", testId: "trip-mobile-tab-itinerary" },
  { id: "ideas",     label: "Ideas",     testId: "trip-mobile-tab-ideas"     },
];

export default function TripDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [trip,          setTrip]          = useState<Trip | null>(null);
  const [itineraryDays, setItineraryDays] = useState<ItineraryDay[]>([]);
  const [tripIdeas,     setTripIdeas]     = useState<ItineraryItem[]>([]);
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
  const [ideasTrayOpen, setIdeasTrayOpen] = useState(false);
  const [selectedDayId, setSelectedDayId] = useState<string | null>(null);
  const [cockpitOpen,   setCockpitOpen]   = useState(false);
  const [mapOpen,       setMapOpen]       = useState(false);
  const [tripBuilderKey, setTripBuilderKey] = useState(0);
  const [tripIdeasKey,  setTripIdeasKey]  = useState(0);
  const [activeMobileWorkspace, setActiveMobileWorkspace] = useState<MobileWorkspace>("brief");
  // Add-to-Day flow: drawer state + which day + which Build vertical to focus
  const [addToDayOpen,       setAddToDayOpen]       = useState(false);
  const [addToDayDayId,      setAddToDayDayId]      = useState<string | null>(null);
  const [buildFocusDayId,    setBuildFocusDayId]    = useState<string | null>(null);
  const [buildFocusVertical, setBuildFocusVertical] = useState<string | null>(null);

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
        fetchTripIdeas(id).then(setTripIdeas);
        setContextLoading(true);
        fetchTripContext(id).then((ctx) => {
          setTripContext(ctx);
          setContextLoading(false);
        });
      }
    }
    load();
  }, [id]);

  function refreshIdeas() {
    fetchTripIdeas(id).then(setTripIdeas);
  }

  // ── Ideas Tray placement writes (durable, day-level) ──────────────────────
  async function handleIdeaAssign(itemId: string, dayId: string) {
    await assignIdeaToDay(itemId, dayId);
    const startDate = (trip as (Trip & { start_date?: string }) | null)?.startDate
      ?? (trip as (Trip & { start_date?: string }) | null)?.start_date;
    const endDate = (trip as (Trip & { end_date?: string }) | null)?.endDate
      ?? (trip as (Trip & { end_date?: string }) | null)?.end_date;
    const days = await ensureTripDays(id, startDate, endDate);
    setItineraryDays(days);
    setTripBuilderKey((k) => k + 1);
    refreshIdeas();
    showToast("Placed in your itinerary");
  }

  async function handleIdeaMeta(
    itemId: string,
    currentDetails: Record<string, unknown>,
    patch: { ideaStatus?: string; userNote?: string },
  ) {
    await updateIdeaMeta(itemId, currentDetails, patch);
    refreshIdeas();
  }

  async function refreshDaysAndIdeas() {
    const startDate = (trip as (Trip & { start_date?: string }) | null)?.startDate
      ?? (trip as (Trip & { start_date?: string }) | null)?.start_date;
    const endDate = (trip as (Trip & { end_date?: string }) | null)?.endDate
      ?? (trip as (Trip & { end_date?: string }) | null)?.end_date;
    const days = await ensureTripDays(id, startDate, endDate);
    setItineraryDays(days);
    setTripBuilderKey((k) => k + 1);
    refreshIdeas();
  }

  // Refreshes parent itinerary + ideas after a TripBuilder add — does NOT bump
  // tripBuilderKey so TripBuilder state (search results, selected vertical, etc.)
  // is preserved while Brief/Dayboard/ExpandedDayPanel pick up the new item.
  function refreshParentItinerary() {
    const startDate = (trip as (Trip & { start_date?: string }) | null)?.startDate
      ?? (trip as (Trip & { start_date?: string }) | null)?.start_date;
    const endDate = (trip as (Trip & { end_date?: string }) | null)?.endDate
      ?? (trip as (Trip & { end_date?: string }) | null)?.end_date;
    ensureTripDays(id, startDate, endDate).then((days) => {
      setItineraryDays(days);
      refreshIdeas();
    });
  }

  async function handleIdeaRemove(itemId: string) {
    // Durable delete; refresh days too so a placed item removed from the map
    // also drops out of the Dayboard/Expanded Day/Trip lens counts.
    await deleteItem(itemId);
    await refreshDaysAndIdeas();
  }

  // Durable unplace (unplaceItemToIdeas → PATCH day_id:null + curated source_kind):
  // the placed item leaves the day and reappears in Trip Ideas with all details
  // (note/coordinates/rating/maps URL) preserved. NOT a delete.
  async function handleItemUnplace(itemId: string, currentDetails: Record<string, unknown>) {
    await unplaceItemToIdeas(itemId, currentDetails);
    await refreshDaysAndIdeas();
    showToast("Moved back to your Ideas");
  }

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }

  // ── Add-to-Day flow — day-scoped vertical picker → Build handoff ──────────
  function handleOpenAddToDay(day: ItineraryDay) {
    setSelectedDayId(day.id);
    setAddToDayDayId(day.id);
    setAddToDayOpen(true);
  }

  function handleAddToDaySelectVertical(vertical: AddToDayVertical) {
    setAddToDayOpen(false);
    setBuildFocusDayId(addToDayDayId);
    setBuildFocusVertical(vertical);
    setActiveMobileWorkspace("build");
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
            className="inline-flex items-center gap-1.5 text-xs text-ds-folio-ink-mist hover:text-ds-folio-ink transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2"
          >
            <ChevronLeft className="w-3.5 h-3.5" aria-hidden="true" />
            My Journeys
          </Link>
        </div>
        <div className="mb-8 folio-paper-panel p-6 animate-pulse">
          <p className="folio-muted-label mb-2">Travel Chapter</p>
          <div className="h-7 w-48 rounded bg-ds-linen mb-2" />
          <div className="h-4 w-32 rounded bg-ds-linen" />
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
          <div className="folio-paper-panel p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-base font-semibold text-ds-folio-ink">Edit Trip</h2>
              <button
                type="button"
                onClick={() => setEditOpen(false)}
                aria-label="Close edit dialog"
                className="p-1.5 rounded-lg hover:bg-ds-linen text-ds-folio-ink-mist hover:text-ds-folio-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 min-h-[44px] min-w-[44px] flex items-center justify-center"
              >
                <X className="w-4 h-4" aria-hidden="true" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="folio-muted-label block mb-1.5">Trip Name</label>
                <input
                  className="folio-input"
                  value={editForm.title}
                  onChange={(e) => setEditForm((f) => ({ ...f, title: e.target.value }))}
                />
              </div>
              <div>
                <label className="folio-muted-label block mb-1.5">Start Date</label>
                <input
                  type="date"
                  className="folio-input"
                  value={editForm.startDate}
                  onChange={(e) => setEditForm((f) => ({ ...f, startDate: e.target.value }))}
                />
              </div>
              <div>
                <label className="folio-muted-label block mb-1.5">End Date</label>
                <input
                  type="date"
                  className="folio-input"
                  value={editForm.endDate}
                  onChange={(e) => setEditForm((f) => ({ ...f, endDate: e.target.value }))}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button type="button" onClick={() => setEditOpen(false)} className={COVER_GHOST}>Cancel</button>
              <button type="button" onClick={handleUpdate} disabled={saving || !editForm.title.trim()} className={COVER_PRIMARY}>
                {saving ? "Saving…" : "Save Changes"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="folio-paper-panel p-6 w-full max-w-sm">
            <h2 className="text-base font-semibold text-ds-folio-ink mb-2">Delete Trip</h2>
            <p className="text-sm text-ds-folio-ink-soft mb-6 leading-relaxed">
              This will permanently delete the trip and all its itinerary items. This cannot be undone.
            </p>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setConfirmDelete(false)} className={COVER_GHOST}>Cancel</button>
              <button
                type="button"
                onClick={handleDelete}
                className="inline-flex items-center gap-1.5 px-4 py-2 min-h-[44px] text-sm font-medium bg-ds-warning text-ds-text-inverse rounded-lg hover:opacity-90 transition-opacity duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2"
              >
                Delete Trip
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Mobile workspace shell ─────────────────────────────────────────── */}
      <div data-testid="trip-mobile-workspace" className="editorial-scene">

        {/* Mobile-only workspace switcher */}
        <nav
          data-testid="trip-mobile-workspace-switcher"
          aria-label="Trip workspace"
          className="lg:hidden flex items-stretch mb-4 rounded-xl border border-ds-hairline bg-ds-bone overflow-hidden"
        >
          {WORKSPACE_TABS.map((tab) => {
            const isActive = activeMobileWorkspace === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                data-testid={tab.testId}
                aria-pressed={isActive}
                onClick={() => setActiveMobileWorkspace(tab.id)}
                className={`flex-1 flex flex-col items-center justify-center min-h-[44px] py-2.5 gap-0.5 relative text-[10px] font-semibold uppercase tracking-[0.1em] transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 ${
                  isActive
                    ? "text-ds-marine-ink"
                    : "text-ds-folio-ink-mist hover:text-ds-folio-ink-soft"
                }`}
              >
                {tab.label}
                {isActive && (
                  <span
                    className="absolute bottom-0 left-2 right-2 h-[2px] rounded-full bg-ds-marine-ink"
                    aria-hidden="true"
                  />
                )}
              </button>
            );
          })}
        </nav>

        {/* Brief panel — trip chapter cover + readiness (mobile: brief only; desktop: always) */}
        <div
          data-testid="trip-mobile-panel-brief"
          className={`${activeMobileWorkspace !== "brief" ? "hidden lg:block" : ""} lg:max-w-4xl lg:mx-auto`}
        >

      {/* ── Trip Chapter Cover ─────────────────────────────────────────────── */}
      <section
        data-testid="trip-chapter-cover"
        aria-labelledby="chapter-destination-heading"
        className="mb-4 sm:mb-6 journey-desk-cover"
      >
        <div className="folio-cover-tab" aria-hidden="true" />
        {/* Back navigation */}
        <div className="px-4 pt-3 sm:px-6 sm:pt-5">
          <Link
            href="/trips"
            className="inline-flex items-center gap-1.5 text-xs text-ds-text-secondary hover:text-ds-text transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2"
          >
            <ChevronLeft className="w-3.5 h-3.5" aria-hidden="true" />
            My Journeys
          </Link>
        </div>

        {/* Chapter cover body */}
        <div className="px-4 pt-3 pb-4 sm:px-6 sm:pt-4 sm:pb-6">
          {/* Overline: chapter classification */}
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-ds-accent mb-2">
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
            <p className="mt-2 text-sm italic text-ds-text-secondary leading-snug">
              {tripContext.dateRange
                ? `${tripContext.vibe} · ${tripContext.dateRange}`
                : tripContext.vibe}
            </p>
          )}

          {/* Dates + duration — caption row */}
          {(trip?.startDate || trip?.endDate) && (
            <div className="mt-2.5 sm:mt-3 flex items-center flex-wrap gap-x-4 gap-y-1">
              <span className="inline-flex items-center gap-1.5 text-xs text-ds-text-secondary">
                <CalendarDays className="w-3.5 h-3.5 text-ds-accent" aria-hidden="true" />
                {trip.startDate && trip.endDate
                  ? `${trip.startDate} – ${trip.endDate}`
                  : trip.startDate || trip.endDate}
              </span>
              {itineraryDays.length > 0 && (
                <span className="text-xs text-ds-text-secondary">
                  {itineraryDays.length} day{itineraryDays.length !== 1 ? "s" : ""}
                </span>
              )}
            </div>
          )}

          {/* Action cluster — one folio primary (Concierge); the rest recede to
              a quiet icon row so the hero never reads as an admin toolbar. */}
          <div
            className="mt-3 sm:mt-5 flex items-center gap-1.5"
            data-testid="chapter-actions"
          >
            <button
              type="button"
              onClick={() => setConciergeOpen(true)}
              data-testid="chapter-action-concierge"
              className={COVER_PRIMARY}
            >
              <Sparkles className="w-3.5 h-3.5" aria-hidden="true" />
              AI Concierge
            </button>
            <span className="mx-0.5 h-5 w-px bg-ds-accent/20" aria-hidden="true" />
            <button
              type="button"
              onClick={() => setOptimizeOpen(true)}
              data-testid="chapter-action-optimize"
              aria-label="Optimize trip"
              title="Optimize"
              className={COVER_GHOST}
            >
              <Zap className="w-4 h-4" aria-hidden="true" />
              <span className="sr-only">Optimize</span>
            </button>
            <button
              type="button"
              onClick={openEdit}
              data-testid="chapter-action-edit"
              aria-label="Edit Trip"
              title="Edit Trip"
              className={COVER_GHOST}
            >
              <Pencil className="w-4 h-4" aria-hidden="true" />
              <span className="sr-only">Edit Trip</span>
            </button>
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              data-testid="chapter-action-delete"
              aria-label="Delete trip"
              title="Delete"
              className={COVER_DANGER}
            >
              <Trash2 className="w-4 h-4" aria-hidden="true" />
              <span className="sr-only">Delete</span>
            </button>
          </div>
        </div>
      </section>

      {/* ── The Brief — where · what is fixed · what still needs choosing ──── */}
      {trip && (
        <TripBrief
          trip={trip}
          days={itineraryDays}
          ideas={tripIdeas}
          onReview={() => setActiveMobileWorkspace("ideas")}
        />
      )}

      {/* ── Dayboard — collapsed day cards (the 10-second read) ────────────── */}
      {/* Expanded day panel renders INLINE under the selected day card so Day 10
          detail is immediately visible without scrolling past the full list. */}
      {(() => {
        const expandedDay = selectedDayId ? itineraryDays.find((d) => d.id === selectedDayId) : null;
        return (
          <Dayboard
            days={itineraryDays}
            selectedDayId={selectedDayId}
            onSelectDay={(day) => setSelectedDayId(day.id)}
            onOpenMap={() => setMapOpen(true)}
            inlineDayPanel={expandedDay ? (
              <ExpandedDayPanel
                day={expandedDay}
                ideasCount={tripIdeas.length}
                onAddFromIdeas={() => setIdeasTrayOpen(true)}
                onEditInItinerary={() => setActiveMobileWorkspace("itinerary")}
                onUnplace={handleItemUnplace}
                onRemoveItem={handleIdeaRemove}
              />
            ) : null}
          />
        );
      })()}

      <div className="editorial-section-rule mb-4" aria-hidden="true" />

      {/* ── Trip readiness — demoted below Journey Desk to a quiet, collapsed
            secondary disclosure (the Brief above is the primary at-a-glance). ── */}
      {trip && (
        <div data-testid="trip-readiness-section" className="mb-2">
          <button
            type="button"
            onClick={() => setCockpitOpen((v) => !v)}
            aria-expanded={cockpitOpen}
            data-testid="trip-readiness-toggle"
            className="flex w-full items-center justify-between gap-2 min-h-[44px] px-1 text-left text-xs font-semibold uppercase tracking-[0.12em] text-ds-folio-ink-mist hover:text-ds-folio-ink transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 rounded"
          >
            <span>Trip readiness · concierge notes</span>
            <ChevronDown className={`w-4 h-4 transition-transform duration-[120ms] ${cockpitOpen ? "rotate-180" : ""}`} aria-hidden="true" />
          </button>
          {cockpitOpen && (
            <div className="mt-2">
              <TripReadinessCockpit
                trip={trip}
                itineraryDays={itineraryDays}
                onOpenConcierge={() => setConciergeOpen(true)}
                onOpenOptimize={() => setOptimizeOpen(true)}
                onOpenEdit={openEdit}
              />
            </div>
          )}
        </div>
      )}

        </div>{/* end trip-mobile-panel-brief */}

        {/* Build / Itinerary / Ideas workspaces — hidden on mobile when brief is active */}
        <div className={activeMobileWorkspace === "brief" ? "hidden lg:block" : ""}>

          {/* "Back to Day N" return affordance — shown on mobile when arriving from
              the Add-to-Day drawer so the user always has a clear path back. */}
          {activeMobileWorkspace === "build" && buildFocusDayId && (() => {
            const focusedDay = itineraryDays.find((d) => d.id === buildFocusDayId);
            return focusedDay ? (
              <div
                data-testid="jd-build-return-banner"
                className="lg:hidden mb-3 flex items-center justify-between gap-3 px-3.5 py-2.5 rounded-xl border border-ds-marine-ink/20 bg-ds-bone"
              >
                <span className="text-xs text-ds-folio-ink-soft italic">
                  Adding to <span className="font-semibold not-italic text-ds-marine-ink">Day {focusedDay.dayNumber}</span>
                </span>
                <button
                  type="button"
                  data-testid="jd-build-return-btn"
                  onClick={() => {
                    setActiveMobileWorkspace("itinerary");
                    setBuildFocusDayId(null);
                    setBuildFocusVertical(null);
                  }}
                  className="text-xs font-medium text-ds-marine-ink hover:text-ds-marine-soft transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 rounded"
                >
                  ← Done · Back to Day {focusedDay.dayNumber}
                </button>
              </div>
            ) : null;
          })()}

          {/* ── Planning Canvas (TripBuilder) ──────────────────────────────── */}
          <TripBuilder
            key={tripBuilderKey}
            tripId={id}
            destination={trip?.destination ?? ""}
            startDate={trip?.startDate}
            endDate={trip?.endDate}
            initialDays={itineraryDays}
            initialResults={[]}
            ideasRefreshKey={tripIdeasKey}
            mobileWorkspace={activeMobileWorkspace === "brief" ? null : activeMobileWorkspace}
            focusDayId={buildFocusDayId}
            focusVertical={buildFocusVertical}
            onAddToDay={handleOpenAddToDay}
            onItineraryChanged={refreshParentItinerary}
            onIdeaAssigned={() => {
              const startDate = (trip as (Trip & { start_date?: string }) | null)?.startDate
                ?? (trip as (Trip & { start_date?: string }) | null)?.start_date;
              const endDate = (trip as (Trip & { end_date?: string }) | null)?.endDate
                ?? (trip as (Trip & { end_date?: string }) | null)?.end_date;
              ensureTripDays(id, startDate, endDate).then((days) => {
                setItineraryDays(days);
                setTripBuilderKey((k) => k + 1);
                refreshIdeas();
                showToast("Added to itinerary!");
              });
            }}
          />
        </div>

      </div>{/* end trip-mobile-workspace */}

      {/* ── Map Fold-Out — Trip Lens (mobile sheet · desktop right drawer) ───── */}
      <MapFoldOut
        open={mapOpen}
        onClose={() => setMapOpen(false)}
        days={itineraryDays}
        ideas={tripIdeas}
        selectedDayId={selectedDayId}
        onSelectDay={(dayId) => setSelectedDayId(dayId)}
        onAssign={handleIdeaAssign}
        onUpdateMeta={handleIdeaMeta}
        onRemove={handleIdeaRemove}
        onUnplace={handleItemUnplace}
        onManage={() => {
          setMapOpen(false);
          setActiveMobileWorkspace("ideas");
        }}
        onManageItinerary={() => {
          setMapOpen(false);
          setActiveMobileWorkspace("itinerary");
        }}
      />

      {/* ── Add-to-Day Drawer — day-scoped vertical picker ──────────────────── */}
      <AddToDayDrawer
        open={addToDayOpen}
        onClose={() => setAddToDayOpen(false)}
        day={addToDayDayId ? itineraryDays.find((d) => d.id === addToDayDayId) ?? null : null}
        onSelectVertical={handleAddToDaySelectVertical}
      />

      {/* ── Ideas Tray — placement-first (mobile sheet · desktop right drawer) ── */}
      <IdeasTray
        open={ideasTrayOpen}
        onClose={() => setIdeasTrayOpen(false)}
        days={itineraryDays}
        ideas={tripIdeas}
        onAssign={handleIdeaAssign}
        onUpdateMeta={handleIdeaMeta}
        onRemove={handleIdeaRemove}
        onManage={() => {
          setIdeasTrayOpen(false);
          setActiveMobileWorkspace("ideas");
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
        onIdeaSaved={() => {
          setTripIdeasKey((k) => k + 1);
          refreshIdeas();
        }}
      />
    </>
  );
}
