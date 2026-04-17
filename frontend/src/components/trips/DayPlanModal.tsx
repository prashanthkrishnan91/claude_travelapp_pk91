"use client";

import { useState } from "react";
import {
  X,
  MapPin,
  Clock,
  Star,
  Loader2,
  CheckCircle2,
  Sparkles,
  UtensilsCrossed,
  Plus,
} from "lucide-react";
import type { DayPlan, AttractionSearchResult, RestaurantSearchResult } from "@/types";

interface DayPlanModalProps {
  plan: DayPlan;
  onClose: () => void;
  onAddAttraction: (attraction: AttractionSearchResult) => Promise<void>;
  onAddRestaurant: (restaurant: RestaurantSearchResult) => Promise<void>;
}

function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

export function DayPlanModal({
  plan,
  onClose,
  onAddAttraction,
  onAddRestaurant,
}: DayPlanModalProps) {
  const [added, setAdded] = useState<Set<string>>(new Set());
  const [addingId, setAddingId] = useState<string | null>(null);
  const [acceptingAll, setAcceptingAll] = useState(false);

  const totalItems = plan.attractions.length + 2;

  async function handleAdd(id: string, addFn: () => Promise<void>) {
    setAddingId(id);
    try {
      await addFn();
      setAdded((prev) => new Set([...prev, id]));
    } finally {
      setAddingId(null);
    }
  }

  async function handleAcceptAll() {
    setAcceptingAll(true);
    try {
      const pending = [
        ...plan.attractions.filter((a) => !added.has(a.id)).map((a) => ({
          id: a.id,
          fn: () => onAddAttraction(a),
        })),
        ...(!added.has(`lunch-${plan.lunch.id}`)
          ? [{ id: `lunch-${plan.lunch.id}`, fn: () => onAddRestaurant(plan.lunch) }]
          : []),
        ...(!added.has(`dinner-${plan.dinner.id}`)
          ? [{ id: `dinner-${plan.dinner.id}`, fn: () => onAddRestaurant(plan.dinner) }]
          : []),
      ];
      for (const { id, fn } of pending) {
        await fn();
        setAdded((prev) => new Set([...prev, id]));
      }
    } finally {
      setAcceptingAll(false);
    }
  }

  const allAdded = added.size >= totalItems;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-xl max-h-[88vh] flex flex-col overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <div>
            <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-500" />
              Day {plan.dayNumber} Plan — {plan.destination}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">AI-curated picks based on rating and variety</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1 px-5 py-4 space-y-5">

          {/* Attractions */}
          <div>
            <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2.5 flex items-center gap-1.5">
              <Sparkles className="w-3 h-3 text-emerald-500" />
              Attractions ({plan.attractions.length})
            </h3>
            <div className="space-y-2">
              {plan.attractions.map((a) => {
                const isAdded = added.has(a.id);
                const isAdding = addingId === a.id;
                return (
                  <div
                    key={a.id}
                    className={`flex items-start gap-3 p-3 rounded-xl border transition-colors ${
                      isAdded ? "border-emerald-200 bg-emerald-50/40" : "border-slate-100 bg-slate-50/40"
                    }`}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-slate-900 leading-tight">{a.name}</p>
                      {a.description && (
                        <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">{a.description}</p>
                      )}
                      <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                        {a.rating != null && (
                          <span className="flex items-center gap-0.5 text-xs text-amber-500 font-medium">
                            <Star className="w-3 h-3 fill-amber-400 stroke-amber-400" />
                            {a.rating.toFixed(1)}
                          </span>
                        )}
                        {a.durationMinutes != null && (
                          <span className="flex items-center gap-0.5 text-xs text-slate-400">
                            <Clock className="w-3 h-3" />
                            {formatDuration(a.durationMinutes)}
                          </span>
                        )}
                        {a.address && (
                          <span className="flex items-center gap-0.5 text-xs text-slate-400 truncate max-w-[140px]">
                            <MapPin className="w-3 h-3 flex-shrink-0" />
                            {a.address.split(",")[0]}
                          </span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => handleAdd(a.id, () => onAddAttraction(a))}
                      disabled={isAdded || isAdding || acceptingAll}
                      className={`flex-shrink-0 flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                        isAdded
                          ? "bg-emerald-100 text-emerald-700 cursor-default"
                          : "bg-emerald-600 hover:bg-emerald-500 text-white disabled:opacity-50"
                      }`}
                    >
                      {isAdding ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : isAdded ? (
                        <CheckCircle2 className="w-3 h-3" />
                      ) : (
                        <Plus className="w-3 h-3" />
                      )}
                      {isAdded ? "Added" : "Add"}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Dining */}
          <div>
            <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2.5 flex items-center gap-1.5">
              <UtensilsCrossed className="w-3 h-3 text-rose-500" />
              Dining
            </h3>
            <div className="space-y-2">
              {(
                [
                  { meal: plan.lunch, mealKey: `lunch-${plan.lunch.id}`, label: "Lunch" },
                  { meal: plan.dinner, mealKey: `dinner-${plan.dinner.id}`, label: "Dinner" },
                ] as { meal: RestaurantSearchResult; mealKey: string; label: string }[]
              ).map(({ meal, mealKey, label }) => {
                const isAdded = added.has(mealKey);
                const isAdding = addingId === mealKey;
                return (
                  <div
                    key={mealKey}
                    className={`flex items-start gap-3 p-3 rounded-xl border transition-colors ${
                      isAdded ? "border-rose-200 bg-rose-50/40" : "border-slate-100 bg-slate-50/40"
                    }`}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-[10px] font-bold uppercase tracking-wide text-rose-500">{label}</span>
                        <span className="text-[10px] text-slate-400">{meal.cuisine}</span>
                      </div>
                      <p className="text-sm font-semibold text-slate-900 leading-tight">{meal.name}</p>
                      <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                        {meal.rating != null && (
                          <span className="flex items-center gap-0.5 text-xs text-amber-500 font-medium">
                            <Star className="w-3 h-3 fill-amber-400 stroke-amber-400" />
                            {meal.rating.toFixed(1)}
                          </span>
                        )}
                        {meal.openingHours && (
                          <span className="flex items-center gap-0.5 text-xs text-slate-400">
                            <Clock className="w-3 h-3" />
                            {meal.openingHours.split(",")[0]}
                          </span>
                        )}
                        {meal.address && (
                          <span className="flex items-center gap-0.5 text-xs text-slate-400 truncate max-w-[140px]">
                            <MapPin className="w-3 h-3 flex-shrink-0" />
                            {meal.address.split(",")[0]}
                          </span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => handleAdd(mealKey, () => onAddRestaurant(meal))}
                      disabled={isAdded || isAdding || acceptingAll}
                      className={`flex-shrink-0 flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                        isAdded
                          ? "bg-rose-100 text-rose-700 cursor-default"
                          : "bg-rose-600 hover:bg-rose-500 text-white disabled:opacity-50"
                      }`}
                    >
                      {isAdding ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : isAdded ? (
                        <CheckCircle2 className="w-3 h-3" />
                      ) : (
                        <Plus className="w-3 h-3" />
                      )}
                      {isAdded ? "Added" : "Add"}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-4 border-t border-slate-100">
          <button onClick={onClose} className="btn-ghost">
            {allAdded ? "Done" : "Close"}
          </button>
          <button
            onClick={handleAcceptAll}
            disabled={allAdded || acceptingAll}
            className="btn-primary flex items-center gap-1.5 disabled:opacity-50"
          >
            {acceptingAll ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5" />
            )}
            {allAdded ? "All Added" : added.size > 0 ? "Add Remaining" : "Accept All"}
          </button>
        </div>
      </div>
    </div>
  );
}
