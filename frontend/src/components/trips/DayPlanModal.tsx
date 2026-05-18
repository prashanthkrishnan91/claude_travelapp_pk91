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
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      {/* Modal shell — paper planning sheet */}
      <div
        data-testid="day-plan-modal"
        className="folio-paper-panel w-full max-w-xl max-h-[88vh] flex flex-col overflow-hidden"
      >
        {/* Header — paper header zone */}
        <div className="folio-paper-header flex items-center justify-between px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold text-ds-folio-ink flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-ds-marine-ink" />
              Day {plan.dayNumber} Plan — {plan.destination}
            </h2>
            <p className="text-xs text-ds-folio-ink-mist mt-0.5">AI-curated picks based on rating and variety</p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close day plan"
            className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg hover:bg-ds-linen text-ds-folio-ink-mist transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body — scrollable recommendation slips */}
        <div className="overflow-y-auto flex-1 px-5 py-4 space-y-5">

          {/* Attractions */}
          <div>
            <h3 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-folio-ink-mist mb-2.5 flex items-center gap-1.5">
              <Sparkles className="w-3 h-3 text-ds-marine-ink" />
              Attractions ({plan.attractions.length})
            </h3>
            <div className="space-y-2">
              {plan.attractions.map((a) => {
                const isAdded = added.has(a.id);
                const isAdding = addingId === a.id;
                return (
                  <div
                    key={a.id}
                    data-testid="day-plan-attraction-card"
                    className={`flex items-start gap-3 p-3 rounded-xl border transition-colors ${
                      isAdded
                        ? "border-ds-hairline bg-ds-bone"
                        : "border-ds-hairline bg-ds-linen"
                    }`}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-ds-folio-ink leading-tight">{a.name}</p>
                      {a.description && (
                        <p className="text-xs text-ds-folio-ink-soft mt-0.5 line-clamp-1">{a.description}</p>
                      )}
                      <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                        {a.rating != null && (
                          <span className="flex items-center gap-0.5 text-xs text-ds-caution font-medium">
                            <Star className="w-3 h-3 fill-ds-caution text-ds-caution" />
                            {a.rating.toFixed(1)}
                          </span>
                        )}
                        {a.durationMinutes != null && (
                          <span className="flex items-center gap-0.5 text-xs text-ds-folio-ink-mist">
                            <Clock className="w-3 h-3" />
                            {formatDuration(a.durationMinutes)}
                          </span>
                        )}
                        {a.address && (
                          <span className="flex items-center gap-0.5 text-xs text-ds-folio-ink-mist truncate max-w-[140px]">
                            <MapPin className="w-3 h-3 flex-shrink-0" />
                            {a.address.split(",")[0]}
                          </span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => handleAdd(a.id, () => onAddAttraction(a))}
                      disabled={isAdded || isAdding || acceptingAll}
                      className={`flex-shrink-0 flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink ${
                        isAdded
                          ? "bg-ds-bone text-ds-trust border border-ds-hairline cursor-default"
                          : "bg-ds-marine-ink text-ds-paper hover:bg-ds-marine-soft disabled:opacity-50"
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
            <h3 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-folio-ink-mist mb-2.5 flex items-center gap-1.5">
              <UtensilsCrossed className="w-3 h-3 text-ds-marine-soft" />
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
                    data-testid="day-plan-dining-card"
                    className={`flex items-start gap-3 p-3 rounded-xl border transition-colors ${
                      isAdded
                        ? "border-ds-hairline bg-ds-bone"
                        : "border-ds-hairline bg-ds-linen"
                    }`}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-[10px] font-bold uppercase tracking-wide text-ds-marine-ink">{label}</span>
                        <span className="text-[10px] text-ds-folio-ink-mist">{meal.cuisine}</span>
                      </div>
                      <p className="text-sm font-semibold text-ds-folio-ink leading-tight">{meal.name}</p>
                      <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                        {meal.rating != null && (
                          <span className="flex items-center gap-0.5 text-xs text-ds-caution font-medium">
                            <Star className="w-3 h-3 fill-ds-caution text-ds-caution" />
                            {meal.rating.toFixed(1)}
                          </span>
                        )}
                        {meal.openingHours && (
                          <span className="flex items-center gap-0.5 text-xs text-ds-folio-ink-mist">
                            <Clock className="w-3 h-3" />
                            {meal.openingHours.split(",")[0]}
                          </span>
                        )}
                        {meal.address && (
                          <span className="flex items-center gap-0.5 text-xs text-ds-folio-ink-mist truncate max-w-[140px]">
                            <MapPin className="w-3 h-3 flex-shrink-0" />
                            {meal.address.split(",")[0]}
                          </span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => handleAdd(mealKey, () => onAddRestaurant(meal))}
                      disabled={isAdded || isAdding || acceptingAll}
                      className={`flex-shrink-0 flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink ${
                        isAdded
                          ? "bg-ds-bone text-ds-trust border border-ds-hairline cursor-default"
                          : "bg-ds-marine-ink text-ds-paper hover:bg-ds-marine-soft disabled:opacity-50"
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

        {/* Footer — paper planning bottom bar */}
        <div className="flex items-center justify-between px-5 py-4 border-t border-ds-hairline">
          <button onClick={onClose} className="btn-folio-ghost">
            {allAdded ? "Done" : "Close"}
          </button>
          <button
            onClick={handleAcceptAll}
            disabled={allAdded || acceptingAll}
            className="btn-marine flex items-center gap-1.5 disabled:opacity-50"
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
