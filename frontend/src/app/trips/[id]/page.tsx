"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ChevronLeft, Pencil, Sparkles, Trash2, X } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { TripBuilder } from "@/components/trips/TripBuilder";
import { fetchTrip, fetchItinerary, updateTrip, deleteTrip } from "@/lib/api";
import type { Trip, ItineraryDay } from "@/types";

interface EditForm {
  title: string;
  startDate: string;
  endDate: string;
}

export default function TripDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [trip,          setTrip]          = useState<Trip | null>(null);
  const [itineraryDays, setItineraryDays] = useState<ItineraryDay[]>([]);
  const [loading,       setLoading]       = useState(true);
  const [editOpen,      setEditOpen]      = useState(false);
  const [editForm,      setEditForm]      = useState<EditForm>({ title: "", startDate: "", endDate: "" });
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [saving,        setSaving]        = useState(false);
  const [toast,         setToast]         = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    async function load() {
      const [tripData, days] = await Promise.all([fetchTrip(id), fetchItinerary(id)]);
      setTrip(tripData);
      setItineraryDays(days);
      setLoading(false);
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
      setTrip(updated);
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

  const pageTitle    = trip?.title ?? "Trip Builder";
  const pageSubtitle = trip?.destination
    ? `${trip.destination}${trip.startDate ? ` · ${trip.startDate}` : ""}`
    : `Trip ID: ${id}`;

  if (loading) {
    return (
      <>
        <div className="mb-6">
          <Link href="/trips" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 transition">
            <ChevronLeft className="w-4 h-4" />
            My Trips
          </Link>
        </div>
        <PageHeader title="Loading…" description={`Trip ID: ${id}`} />
        <div className="card p-8 text-center text-slate-400 text-sm">Loading trip details…</div>
      </>
    );
  }

  return (
    <>
      {toast && (
        <div className="fixed bottom-4 right-4 z-50 bg-slate-800 text-white text-sm px-4 py-2 rounded-lg shadow-lg">
          {toast}
        </div>
      )}

      {/* Edit Modal */}
      {editOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-slate-900">Edit Trip</h2>
              <button onClick={() => setEditOpen(false)} className="p-1 rounded hover:bg-slate-100 text-slate-400">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Trip Name</label>
                <input
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
                  value={editForm.title}
                  onChange={(e) => setEditForm((f) => ({ ...f, title: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Start Date</label>
                <input
                  type="date"
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
                  value={editForm.startDate}
                  onChange={(e) => setEditForm((f) => ({ ...f, startDate: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">End Date</label>
                <input
                  type="date"
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
                  value={editForm.endDate}
                  onChange={(e) => setEditForm((f) => ({ ...f, endDate: e.target.value }))}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setEditOpen(false)} className="btn-ghost">Cancel</button>
              <button onClick={handleUpdate} disabled={saving || !editForm.title.trim()} className="btn-primary">
                {saving ? "Saving…" : "Save Changes"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm">
            <h2 className="text-base font-semibold text-slate-900 mb-2">Delete Trip</h2>
            <p className="text-sm text-slate-500 mb-6">
              This will permanently delete the trip and all its itinerary items. This cannot be undone.
            </p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setConfirmDelete(false)} className="btn-ghost">Cancel</button>
              <button onClick={handleDelete} className="px-4 py-2 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-700 transition">
                Delete Trip
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="mb-6">
        <Link href="/trips" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 transition">
          <ChevronLeft className="w-4 h-4" />
          My Trips
        </Link>
      </div>

      <PageHeader
        title={pageTitle}
        description={pageSubtitle}
        action={
          <div className="flex items-center gap-2">
            <button onClick={() => setConfirmDelete(true)} className="btn-ghost text-red-500 hover:text-red-600 hover:bg-red-50">
              <Trash2 className="w-4 h-4" />
              Delete Trip
            </button>
            <button onClick={openEdit} className="btn-ghost">
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
        initialResults={[]}
      />
    </>
  );
}
