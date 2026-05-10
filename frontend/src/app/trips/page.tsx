"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  PlusCircle,
  MapPin,
  Calendar,
  Users,
  Map,
  Pencil,
  Trash2,
  X,
} from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { TripStatusBadge } from "@/components/ui/TripStatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { fetchTrips, updateTrip, deleteTrip } from "@/lib/api";
import { getDisplayTripStatus, getTripStatusGroup } from "@/lib/tripStatus";
import type { Trip } from "@/types";

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


interface EditForm {
  title: string;
  startDate: string;
  endDate: string;
}

export default function TripsPage() {
  const router = useRouter();
  const [trips, setTrips] = useState<Trip[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingTrip, setEditingTrip] = useState<Trip | null>(null);
  const [editForm, setEditForm] = useState<EditForm>({ title: "", startDate: "", endDate: "" });
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      console.log("[TripsPage] Fetching trips via GET /trips…");
      const result = await fetchTrips();
      console.log("[TripsPage] GET /trips response:", result);
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

  const groupedTrips = ["Active", "Past"].map((label) => ({
    label,
    trips: trips.filter((t: Trip) => getTripStatusGroup(t) === label),
  }));

  const hasAny = trips.length > 0;

  if (loading) {
    return (
      <>
        <PageHeader
          title="My Trips"
          description="Loading…"
          action={
            <Link href="/trips/new" className="btn-primary">
              <PlusCircle className="w-4 h-4" />
              New Trip
            </Link>
          }
        />
        <div className="card p-8 text-center text-cream-500 text-sm">
          Loading your trips…
        </div>
      </>
    );
  }

  return (
    <>
      {/* Toast */}
      {toast && (
        <div className="fixed bottom-4 right-4 z-50 bg-dark-400 text-cream-100 border border-white/[.10] text-sm px-4 py-2 rounded-lg shadow-lg">
          {toast}
        </div>
      )}

      {/* Edit Modal */}
      {editingTrip && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="card rounded-xl shadow-2xl p-6 w-full max-w-md border border-white/[.10]">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-cream-100">Edit Trip</h2>
              <button
                onClick={() => setEditingTrip(null)}
                className="p-1 rounded hover:bg-white/[.06] text-cream-500"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="label">Trip Name</label>
                <input
                  className="input"
                  value={editForm.title}
                  onChange={(e) => setEditForm((f) => ({ ...f, title: e.target.value }))}
                />
              </div>
              <div>
                <label className="label">Start Date</label>
                <input
                  type="date"
                  className="input"
                  value={editForm.startDate}
                  onChange={(e) => setEditForm((f) => ({ ...f, startDate: e.target.value }))}
                />
              </div>
              <div>
                <label className="label">End Date</label>
                <input
                  type="date"
                  className="input"
                  value={editForm.endDate}
                  onChange={(e) => setEditForm((f) => ({ ...f, endDate: e.target.value }))}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setEditingTrip(null)} className="btn-ghost">
                Cancel
              </button>
              <button
                onClick={handleUpdate}
                disabled={saving || !editForm.title.trim()}
                className="btn-primary"
              >
                {saving ? "Saving…" : "Save Changes"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {confirmDeleteId && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="card rounded-xl shadow-2xl p-6 w-full max-w-sm border border-white/[.10]">
            <h2 className="text-base font-semibold text-cream-100 mb-2">Delete Trip</h2>
            <p className="text-sm text-cream-400 mb-6">
              This will permanently delete the trip and all its itinerary items. This cannot be undone.
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setConfirmDeleteId(null)} className="btn-ghost">
                Cancel
              </button>
              <button
                onClick={() => handleDelete(confirmDeleteId)}
                className="px-4 py-2 text-sm font-medium bg-rose-600 text-white rounded-lg hover:bg-rose-700 transition"
              >
                Delete Trip
              </button>
            </div>
          </div>
        </div>
      )}

      <PageHeader
        title="My Trips"
        description={`${trips.length} trip${trips.length !== 1 ? "s" : ""} in total`}
        action={
          <Link href="/trips/new" className="btn-primary">
            <PlusCircle className="w-4 h-4" />
            New Trip
          </Link>
        }
      />

      {!hasAny ? (
        <div className="card">
          <EmptyState
            icon={<Map className="w-6 h-6" />}
            title="No trips yet"
            description="Start planning your first trip and let the AI concierge help you build the perfect itinerary."
            action={
              <Link href="/trips/new" className="btn-primary">
                <PlusCircle className="w-4 h-4" />
                Plan a Trip
              </Link>
            }
          />
        </div>
      ) : (
        <div className="space-y-8">
          {groupedTrips.map(({ label, trips: groupTrips }) =>
            groupTrips.length === 0 ? null : (
              <section key={label}>
                <h2 className="text-xs font-semibold uppercase tracking-widest text-cream-500 mb-3 px-1">
                  {label}
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                  {groupTrips.map((trip: Trip) => (
                    <div
                      key={trip.id}
                      className="card card-lift p-5 flex flex-col gap-3 group cursor-pointer"
                      onClick={() => router.push(`/trips/${trip.id}`)}
                    >
                      {/* Header */}
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="text-sm font-semibold text-cream-100 group-hover:text-brand-400 transition leading-snug">
                          {trip.title}
                        </h3>
                        <div className="flex items-center gap-1">
                          <TripStatusBadge status={getDisplayTripStatus(trip)} />
                          <button
                            onClick={(e) => { e.stopPropagation(); openEdit(trip); }}
                            className="p-1 rounded hover:bg-white/[.06] text-cream-500 hover:text-cream-300 transition"
                            title="Edit trip"
                          >
                            <Pencil className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(trip.id); }}
                            className="p-1 rounded hover:bg-rose-500/10 text-cream-500 hover:text-rose-400 transition"
                            title="Delete trip"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>

                      {/* Destination */}
                      <div className="flex items-center gap-1.5 text-sm text-cream-300">
                        <MapPin className="w-3.5 h-3.5 text-cream-500 shrink-0" />
                        {trip.destination}
                      </div>

                      {/* Meta */}
                      <div className="flex flex-wrap gap-3 text-xs text-cream-500">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {formatDateRange(trip.startDate, trip.endDate)}
                        </span>
                        <span className="flex items-center gap-1">
                          <Users className="w-3 h-3" />
                          {trip.travelers}{" "}
                          {trip.travelers === 1 ? "traveler" : "travelers"}
                        </span>
                      </div>

                      {/* Budget */}
                      {trip.budgetCash && (
                        <div className="pt-2 mt-auto border-t border-white/[.06] flex items-center justify-between gap-2">
                          <span className="text-xs text-cream-500">Budget</span>
                          <div className="flex items-center gap-1.5">
                            {trip.travelers > 1 && (
                              <span className="badge badge-value text-[10px] px-1.5 py-0.5">
                                {new Intl.NumberFormat("en-US", {
                                  style: "currency",
                                  currency: trip.budgetCurrency,
                                  maximumFractionDigits: 0,
                                }).format(Number(trip.budgetCash) / trip.travelers)}
                                /pp
                              </span>
                            )}
                            <span className="text-sm font-semibold text-cream-100">
                              {new Intl.NumberFormat("en-US", {
                                style: "currency",
                                currency: trip.budgetCurrency,
                                maximumFractionDigits: 0,
                              }).format(Number(trip.budgetCash))}
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            )
          )}
        </div>
      )}
    </>
  );
}
