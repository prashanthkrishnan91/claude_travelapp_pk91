"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  MapPin,
  Plane,
  Calendar,
  Users,
  DollarSign,
  FileText,
  ChevronRight,
  ChevronLeft,
  CheckCircle2,
} from "lucide-react";
import clsx from "clsx";
import type { TripBuilderFormData } from "@/types";

// ─── Step definitions ────────────────────────────────────────────────────────

interface Step {
  id: number;
  label: string;
  description: string;
  icon: React.ElementType;
}

const STEPS: Step[] = [
  { id: 1, label: "Destination",  description: "Where are you going?",         icon: MapPin       },
  { id: 2, label: "Travel Dates", description: "When are you traveling?",       icon: Calendar     },
  { id: 3, label: "Travelers",    description: "Who's coming along?",           icon: Users        },
  { id: 4, label: "Budget",       description: "What's your budget?",           icon: DollarSign   },
  { id: 5, label: "Notes",        description: "Anything else to note?",        icon: FileText     },
];

// ─── Default form values ─────────────────────────────────────────────────────

const DEFAULT_DATA: TripBuilderFormData = {
  title:          "",
  destination:    "",
  origin:         "",
  startDate:      "",
  endDate:        "",
  travelers:      1,
  budgetCash:     "",
  budgetCurrency: "USD",
  notes:          "",
};

// ─── Step progress indicator ─────────────────────────────────────────────────

function StepIndicator({ current }: { current: number }) {
  return (
    <ol className="flex items-center gap-1 mb-8 overflow-x-auto pb-1">
      {STEPS.map((step, i) => {
        const done    = current > step.id;
        const active  = current === step.id;
        return (
          <li key={step.id} className="flex items-center gap-1 shrink-0">
            <div
              className={clsx(
                "flex items-center justify-center w-8 h-8 rounded-full text-xs font-semibold transition",
                done   && "bg-sky-600 text-white",
                active && "bg-sky-600 text-white ring-4 ring-sky-100",
                !done && !active && "bg-slate-100 text-slate-400"
              )}
            >
              {done ? <CheckCircle2 className="w-4 h-4" /> : step.id}
            </div>
            <span
              className={clsx(
                "text-xs font-medium hidden sm:inline",
                active ? "text-sky-700" : done ? "text-slate-600" : "text-slate-400"
              )}
            >
              {step.label}
            </span>
            {i < STEPS.length - 1 && (
              <div
                className={clsx(
                  "w-8 h-0.5 mx-1 rounded-full transition",
                  current > step.id ? "bg-sky-400" : "bg-slate-200"
                )}
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}

// ─── Individual step panes ────────────────────────────────────────────────────

function DestinationStep({
  data,
  onChange,
}: {
  data: TripBuilderFormData;
  onChange: (patch: Partial<TripBuilderFormData>) => void;
}) {
  return (
    <div className="space-y-5">
      <div>
        <label className="label" htmlFor="trip-title">Trip name</label>
        <input
          id="trip-title"
          className="input"
          placeholder="e.g. Tokyo Cherry Blossom 2026"
          value={data.title}
          onChange={(e) => onChange({ title: e.target.value })}
        />
        <p className="mt-1 text-xs text-slate-400">Give your trip a memorable name.</p>
      </div>
      <div>
        <label className="label" htmlFor="trip-destination">Destination</label>
        <div className="relative">
          <MapPin className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          <input
            id="trip-destination"
            className="input pl-10"
            placeholder="City, Country — e.g. Tokyo, Japan"
            value={data.destination}
            onChange={(e) => onChange({ destination: e.target.value })}
          />
        </div>
      </div>
      <div>
        <label className="label" htmlFor="trip-origin">Flying from (optional)</label>
        <div className="relative">
          <Plane className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          <input
            id="trip-origin"
            className="input pl-10"
            placeholder="Your home city or airport"
            value={data.origin}
            onChange={(e) => onChange({ origin: e.target.value })}
          />
        </div>
      </div>
    </div>
  );
}

function DatesStep({
  data,
  onChange,
}: {
  data: TripBuilderFormData;
  onChange: (patch: Partial<TripBuilderFormData>) => void;
}) {
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="label" htmlFor="start-date">Departure date</label>
          <input
            id="start-date"
            type="date"
            className="input"
            value={data.startDate}
            onChange={(e) => onChange({ startDate: e.target.value })}
          />
        </div>
        <div>
          <label className="label" htmlFor="end-date">Return date</label>
          <input
            id="end-date"
            type="date"
            className="input"
            value={data.endDate}
            min={data.startDate}
            onChange={(e) => onChange({ endDate: e.target.value })}
          />
        </div>
      </div>
      {data.startDate && data.endDate && (
        <div className="rounded-xl bg-sky-50 border border-sky-100 p-4 text-sm text-sky-700">
          <span className="font-medium">Trip length: </span>
          {Math.ceil(
            (new Date(data.endDate).getTime() - new Date(data.startDate).getTime()) /
              (1000 * 60 * 60 * 24)
          )}{" "}
          nights
        </div>
      )}
    </div>
  );
}

function TravelersStep({
  data,
  onChange,
}: {
  data: TripBuilderFormData;
  onChange: (patch: Partial<TripBuilderFormData>) => void;
}) {
  return (
    <div className="space-y-5">
      <div>
        <label className="label">Number of travelers</label>
        <div className="flex items-center gap-4 mt-2">
          <button
            type="button"
            className="btn-ghost w-10 h-10 p-0 items-center justify-center text-lg font-bold"
            onClick={() => onChange({ travelers: Math.max(1, data.travelers - 1) })}
          >
            −
          </button>
          <span className="text-3xl font-bold text-slate-900 w-12 text-center">
            {data.travelers}
          </span>
          <button
            type="button"
            className="btn-ghost w-10 h-10 p-0 items-center justify-center text-lg font-bold"
            onClick={() => onChange({ travelers: data.travelers + 1 })}
          >
            +
          </button>
        </div>
        <p className="mt-3 text-xs text-slate-400">
          {data.travelers === 1
            ? "Solo traveler"
            : `${data.travelers} travelers`}
        </p>
      </div>

      <div className="grid grid-cols-3 gap-3">
        {[1, 2, 4].map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => onChange({ travelers: n })}
            className={clsx(
              "rounded-xl border py-3 text-sm font-medium transition",
              data.travelers === n
                ? "border-sky-500 bg-sky-50 text-sky-700"
                : "border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-50"
            )}
          >
            {n === 1 ? "Solo" : n === 2 ? "Couple" : "Group"}
          </button>
        ))}
      </div>
    </div>
  );
}

const CURRENCIES = [
  { code: "USD", label: "USD — US Dollar"         },
  { code: "EUR", label: "EUR — Euro"              },
  { code: "GBP", label: "GBP — British Pound"     },
  { code: "JPY", label: "JPY — Japanese Yen"      },
  { code: "AUD", label: "AUD — Australian Dollar" },
  { code: "CAD", label: "CAD — Canadian Dollar"   },
];

function BudgetStep({
  data,
  onChange,
}: {
  data: TripBuilderFormData;
  onChange: (patch: Partial<TripBuilderFormData>) => void;
}) {
  return (
    <div className="space-y-5">
      <div>
        <label className="label" htmlFor="budget-cash">Total cash budget (optional)</label>
        <div className="flex gap-3">
          <div className="relative flex-1">
            <DollarSign className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            <input
              id="budget-cash"
              type="number"
              min="0"
              step="100"
              className="input pl-10"
              placeholder="0"
              value={data.budgetCash}
              onChange={(e) => onChange({ budgetCash: e.target.value })}
            />
          </div>
          <select
            className="select w-36"
            value={data.budgetCurrency}
            onChange={(e) => onChange({ budgetCurrency: e.target.value })}
          >
            {CURRENCIES.map(({ code, label }) => (
              <option key={code} value={code}>{label}</option>
            ))}
          </select>
        </div>
        <p className="mt-1 text-xs text-slate-400">
          We&apos;ll show cash and points costs side-by-side so you can pick the best option.
        </p>
      </div>

      {data.budgetCash && data.travelers > 0 && (
        <div className="rounded-xl bg-slate-50 border border-slate-100 p-4">
          <p className="text-xs text-slate-500 font-medium">Per person</p>
          <p className="text-lg font-bold text-slate-800 mt-0.5">
            {new Intl.NumberFormat("en-US", {
              style: "currency",
              currency: data.budgetCurrency,
              maximumFractionDigits: 0,
            }).format(Number(data.budgetCash) / data.travelers)}
          </p>
        </div>
      )}
    </div>
  );
}

function NotesStep({
  data,
  onChange,
}: {
  data: TripBuilderFormData;
  onChange: (patch: Partial<TripBuilderFormData>) => void;
}) {
  return (
    <div className="space-y-5">
      <div>
        <label className="label" htmlFor="trip-notes">Notes &amp; preferences</label>
        <textarea
          id="trip-notes"
          rows={5}
          className="input resize-none"
          placeholder="Any specific preferences, must-see places, dietary restrictions, accommodation preferences, or other notes for the AI concierge..."
          value={data.notes}
          onChange={(e) => onChange({ notes: e.target.value })}
        />
        <p className="mt-1 text-xs text-slate-400">
          The more context you provide, the better the AI can personalize your trip.
        </p>
      </div>
    </div>
  );
}

// ─── Review summary ───────────────────────────────────────────────────────────

function ReviewSummary({ data }: { data: TripBuilderFormData }) {
  const rows = [
    { label: "Trip name",    value: data.title        || "—" },
    { label: "Destination",  value: data.destination  || "—" },
    { label: "Flying from",  value: data.origin       || "—" },
    { label: "Dates",        value: data.startDate ? `${data.startDate} → ${data.endDate || "TBD"}` : "—" },
    { label: "Travelers",    value: String(data.travelers) },
    {
      label: "Budget",
      value: data.budgetCash
        ? new Intl.NumberFormat("en-US", { style: "currency", currency: data.budgetCurrency, maximumFractionDigits: 0 }).format(Number(data.budgetCash))
        : "—",
    },
  ];

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">
        Review your trip details before saving. You can always edit them later.
      </p>
      <dl className="divide-y divide-slate-100 rounded-xl border border-slate-200 overflow-hidden">
        {rows.map(({ label, value }) => (
          <div key={label} className="flex items-center px-4 py-3 gap-4">
            <dt className="text-xs text-slate-400 font-medium w-28 shrink-0">{label}</dt>
            <dd className="text-sm text-slate-800 font-medium">{value}</dd>
          </div>
        ))}
      </dl>
      {data.notes && (
        <div className="rounded-xl bg-slate-50 border border-slate-100 p-4">
          <p className="text-xs text-slate-400 font-medium mb-1">Notes</p>
          <p className="text-sm text-slate-700 whitespace-pre-line">{data.notes}</p>
        </div>
      )}
    </div>
  );
}

// ─── Main form component ──────────────────────────────────────────────────────

export function TripBuilderForm() {
  const router  = useRouter();
  const [step,  setStep]  = useState(1);
  const [data,  setData]  = useState<TripBuilderFormData>(DEFAULT_DATA);
  const [saving, setSaving] = useState(false);

  const totalSteps = STEPS.length + 1; // +1 for review
  const isReview   = step === totalSteps;

  function patch(update: Partial<TripBuilderFormData>) {
    setData((prev) => ({ ...prev, ...update }));
  }

  function canAdvance() {
    if (step === 1) return data.title.trim() !== "" && data.destination.trim() !== "";
    return true;
  }

  function handleSave() {
    setSaving(true);
    // No data integration yet — simulate brief delay then redirect
    setTimeout(() => {
      setSaving(false);
      router.push("/trips");
    }, 800);
  }

  const currentStep = STEPS[step - 1];

  return (
    <div className="max-w-xl">
      <StepIndicator current={step} />

      <div className="card p-6 sm:p-8">
        {/* Step header */}
        {!isReview && currentStep && (
          <div className="mb-6">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-1">
              Step {step} of {STEPS.length}
            </p>
            <h2 className="text-xl font-bold text-slate-900">{currentStep.label}</h2>
            <p className="text-sm text-slate-500 mt-0.5">{currentStep.description}</p>
          </div>
        )}

        {isReview && (
          <div className="mb-6">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-1">
              Review
            </p>
            <h2 className="text-xl font-bold text-slate-900">Looks good?</h2>
          </div>
        )}

        {/* Step content */}
        <div>
          {step === 1 && <DestinationStep data={data} onChange={patch} />}
          {step === 2 && <DatesStep       data={data} onChange={patch} />}
          {step === 3 && <TravelersStep   data={data} onChange={patch} />}
          {step === 4 && <BudgetStep      data={data} onChange={patch} />}
          {step === 5 && <NotesStep       data={data} onChange={patch} />}
          {isReview   && <ReviewSummary   data={data}                  />}
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between mt-8 pt-6 border-t border-slate-100">
          <button
            type="button"
            className="btn-ghost"
            onClick={() => setStep((s) => Math.max(1, s - 1))}
            disabled={step === 1}
          >
            <ChevronLeft className="w-4 h-4" />
            Back
          </button>

          {isReview ? (
            <button
              type="button"
              className="btn-primary"
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? "Saving…" : "Create Trip"}
              {!saving && <CheckCircle2 className="w-4 h-4" />}
            </button>
          ) : (
            <button
              type="button"
              className="btn-primary"
              onClick={() => setStep((s) => s + 1)}
              disabled={!canAdvance()}
            >
              {step === STEPS.length ? "Review" : "Continue"}
              <ChevronRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
