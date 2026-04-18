"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ChevronLeft, Pencil, Sparkles, Trash2, X, Zap } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { TripBuilder } from "@/components/trips/TripBuilder";
import { OptimizeTripModal } from "@/components/trips/OptimizeTripModal";
import { fetchTrip, fetchItinerary, fetchTripContext, updateTrip, deleteTrip } from "@/lib/api";
import type { Trip, TripContext, ItineraryDay } from "@/types";

const DESTINATION_GRADIENTS: Array<{ keywords: string[]; gradient: string }> = [
  { keywords: ["honolulu","hawaii","maui","oahu","waikiki","pacific"],          gradient: "linear-gradient(160deg,#0077b6 0%,#00b4d8 40%,#90e0ef 75%,#caf0f8 100%)" },
  { keywords: ["maldives","caribbean","bahamas","cancun","aruba","turks"],      gradient: "linear-gradient(160deg,#06b6d4 0%,#22d3ee 40%,#67e8f9 75%,#a5f3fc 100%)" },
  { keywords: ["tokyo","japan","osaka","kyoto","shibuya","shinjuku"],           gradient: "linear-gradient(160deg,#0f0c29 0%,#302b63 40%,#4c1d95 75%,#6d28d9 100%)" },
  { keywords: ["new york","nyc","manhattan","chicago","london","hong kong","las vegas","singapore"], gradient: "linear-gradient(160deg,#1c1c2e 0%,#374151 40%,#6b7280 75%,#9ca3af 100%)" },
  { keywords: ["paris","france","nice","lyon","bordeaux","provence"],           gradient: "linear-gradient(160deg,#c9a96e 0%,#d4a853 40%,#e8d5b0 75%,#fef3c7 100%)" },
  { keywords: ["rome","italy","florence","venice","tuscany","amalfi","sicily"], gradient: "linear-gradient(160deg,#9c4221 0%,#dd6b20 40%,#f6ad55 75%,#fef3c7 100%)" },
  { keywords: ["santorini","greece","athens","mykonos","crete","mediterranean"],gradient: "linear-gradient(160deg,#1d4ed8 0%,#3b82f6 40%,#93c5fd 75%,#dbeafe 100%)" },
  { keywords: ["bali","indonesia","thailand","phuket","bangkok","lombok"],      gradient: "linear-gradient(160deg,#1a472a 0%,#52b788 40%,#b7e4c7 75%,#ffd166 100%)" },
  { keywords: ["dubai","abu dhabi","morocco","marrakech","sahara","desert"],    gradient: "linear-gradient(160deg,#e76f51 0%,#f4a261 40%,#e9c46a 75%,#ffd166 100%)" },
  { keywords: ["swiss","switzerland","alps","nepal","himalaya","mountain","colorado","rockies","norway"], gradient: "linear-gradient(160deg,#264653 0%,#2a9d8f 40%,#a8dadc 75%,#e9f5f5 100%)" },
  { keywords: ["barcelona","spain","madrid","lisbon","portugal","seville"],     gradient: "linear-gradient(160deg,#b5179e 0%,#f72585 40%,#ff9a3c 75%,#ffd166 100%)" },
  { keywords: ["sydney","australia","melbourne","queensland","great barrier"],  gradient: "linear-gradient(160deg,#0077b6 0%,#0096c7 40%,#48cae4 75%,#ade8f4 100%)" },
];

const DEFAULT_GRADIENT = "linear-gradient(160deg,#0ea5e9 0%,#38bdf8 40%,#7dd3fc 75%,#e0f2fe 100%)";

const BEACH_KW  = ["honolulu","hawaii","maui","maldives","caribbean","bahamas","cancun","aruba","bali","phuket","lombok","fiji","tahiti","barbados"];
const COLD_KW   = ["swiss","switzerland","alps","himalaya","mountain","colorado","rockies","norway","iceland","alaska","anchorage","aspen","vail"];
const CITY_KW   = ["new york","nyc","chicago","london","tokyo","paris","rome","dubai","singapore","hong kong","las vegas","berlin","sydney","melbourne"];

function getDestinationEmoji(destination: string): string {
  const lower = destination.toLowerCase();
  if (BEACH_KW.some((k) => lower.includes(k))) return "🌴";
  if (COLD_KW.some((k) => lower.includes(k))) return "❄️";
  if (CITY_KW.some((k) => lower.includes(k))) return "🏙";
  return "✈️";
}

function getDestinationGradient(destination: string): string {
  const lower = destination.toLowerCase();
  for (const theme of DESTINATION_GRADIENTS) {
    if (theme.keywords.some((kw) => lower.includes(kw))) return theme.gradient;
  }
  return DEFAULT_GRADIENT;
}

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
  const [tripContext,   setTripContext]   = useState<TripContext | null>(null);
  const [contextLoading, setContextLoading] = useState(false);
  const [loading,       setLoading]       = useState(true);
  const [editOpen,      setEditOpen]      = useState(false);
  const [editForm,      setEditForm]      = useState<EditForm>({ title: "", startDate: "", endDate: "" });
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [saving,        setSaving]        = useState(false);
  const [toast,         setToast]         = useState<string | null>(null);
  const [optimizeOpen,  setOptimizeOpen]  = useState(false);
  const [tripBuilderKey, setTripBuilderKey] = useState(0);

  useEffect(() => {
    if (!id) return;
    async function load() {
      const [tripData, days] = await Promise.all([fetchTrip(id), fetchItinerary(id)]);
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

  async function handlePlanSelected() {
    const days = await fetchItinerary(id);
    setItineraryDays(days);
    setTripBuilderKey((k) => k + 1);
    setOptimizeOpen(false);
    showToast("Plan added to your itinerary!");
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
      {/* Destination-aware background */}
      {trip?.destination && (
        <>
          <div
            aria-hidden="true"
            className="destination-bg"
            style={{ background: getDestinationGradient(trip.destination) }}
          />
          <div aria-hidden="true" className="destination-overlay" />
        </>
      )}

      {toast && (
        <div className="fixed bottom-4 right-4 z-50 bg-slate-800 text-white text-sm px-4 py-2 rounded-lg shadow-lg">
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

      {/* Trip context header */}
      {(contextLoading || tripContext) && (
        <div className="mb-4 flex items-center gap-2">
          {contextLoading ? (
            <p className="text-sm text-slate-400 italic">Fetching destination vibe…</p>
          ) : tripContext ? (
            <>
              <span className="text-xl leading-none" aria-hidden="true">
                {getDestinationEmoji(trip?.destination ?? "")}
              </span>
              <p className="text-sm font-medium text-slate-500 tracking-wide">
                {tripContext.dateRange
                  ? `${tripContext.vibe} • ${tripContext.dateRange}`
                  : tripContext.vibe}
              </p>
            </>
          ) : null}
        </div>
      )}

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
            <button onClick={() => setOptimizeOpen(true)} className="btn-ghost">
              <Zap className="w-4 h-4" />
              Optimize My Trip
            </button>
            <button className="btn-primary">
              <Sparkles className="w-4 h-4" />
              AI Concierge
            </button>
          </div>
        }
      />

      <TripBuilder
        key={tripBuilderKey}
        tripId={id}
        destination={trip?.destination ?? ""}
        initialDays={itineraryDays}
        initialResults={[]}
      />
    </>
  );
}
