"use client";
/**
 * Visual proof page for PR #514 — Check route button.
 * Shows all 4 states (idle, loading, success, error) with real Tailwind classes.
 * Not linked from app navigation; used only for screenshot capture.
 */
import { Navigation, Loader2, Info, X } from "lucide-react";

const dismissBtnClass =
  "flex items-center justify-center min-w-[44px] min-h-[44px] -mr-1 rounded text-ds-folio-ink-mist hover:text-ds-folio-ink transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2";

function IdleState() {
  return (
    <div className="flex justify-end mt-1" data-testid="check-route-idle">
      <button
        data-testid="check-route-btn"
        className="flex items-center gap-1.5 px-2.5 rounded-lg bg-ds-bone hover:bg-ds-linen text-ds-folio-ink-mist hover:text-ds-folio-ink border border-ds-hairline text-[11px] font-medium transition-colors duration-[120ms] focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2 min-h-[44px]"
      >
        <Navigation className="w-3 h-3" aria-hidden="true" />
        Check route
      </button>
    </div>
  );
}

function LoadingState() {
  return (
    <div
      data-testid="check-route-loading"
      className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg bg-ds-linen border border-ds-hairline mt-1"
    >
      <Loader2 className="w-3 h-3 text-ds-folio-ink-mist animate-spin flex-shrink-0" aria-hidden="true" />
      <span className="text-[10px] text-ds-folio-ink-mist">Estimating route…</span>
    </div>
  );
}

function SuccessState() {
  const legs = [
    { from: "Senso-ji Temple", to: "Ueno Park", durationSeconds: 900, distanceMeters: 2300 },
    { from: "Ueno Park", to: "Akihabara Electric Town", durationSeconds: 480, distanceMeters: 1100 },
    { from: "Akihabara Electric Town", to: "Tokyo National Museum", durationSeconds: 660, distanceMeters: 1600 },
  ];
  function dur(s: number) {
    const m = Math.round(s / 60);
    return m < 60 ? `${m} min` : `${Math.floor(m / 60)}h ${m % 60}m`;
  }
  function dist(m: number) {
    return m < 1000 ? `${m} m` : `${(m / 1000).toFixed(1)} km`;
  }
  return (
    <div
      data-testid="check-route-result"
      className="rounded-lg bg-ds-linen border border-ds-hairline mt-1 overflow-hidden"
    >
      <div className="flex items-center justify-between px-2 py-1.5 border-b border-ds-hairline/50">
        <div className="flex items-center gap-1.5">
          <Navigation className="w-3 h-3 text-ds-marine-ink flex-shrink-0" aria-hidden="true" />
          <span className="text-[10px] font-semibold text-ds-folio-ink">Route estimate</span>
          <span className="text-[10px] text-ds-folio-ink-mist italic">· estimated only</span>
        </div>
        <button aria-label="Clear route estimate" className={dismissBtnClass}>
          <X className="w-3 h-3" />
        </button>
      </div>
      <div className="px-2 py-1.5 space-y-1">
        {legs.map((leg, i) => (
          <div key={i} className="flex items-baseline gap-1.5 text-[10px]">
            <span className="text-ds-folio-ink-mist/50 flex-shrink-0" aria-hidden="true">·</span>
            <span className="text-ds-folio-ink-soft truncate flex-1">{leg.from} → {leg.to}</span>
            <span className="text-ds-marine-ink font-medium flex-shrink-0">~{dur(leg.durationSeconds)}</span>
            <span className="text-ds-folio-ink-mist/60 flex-shrink-0">{dist(leg.distanceMeters)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ErrorState() {
  return (
    <div
      data-testid="check-route-error"
      className="flex items-start gap-1.5 px-2 py-1.5 rounded-lg bg-ds-linen border border-ds-hairline mt-1"
    >
      <Info className="w-3 h-3 text-ds-folio-ink-mist flex-shrink-0 mt-px" aria-hidden="true" />
      <span className="text-[10px] text-ds-folio-ink-mist leading-tight flex-1">
        Route estimate is not available for this itinerary.
      </span>
      <button aria-label="Dismiss" className={dismissBtnClass}>
        <X className="w-3 h-3" />
      </button>
    </div>
  );
}

function MockDayPanel({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border border-ds-hairline shadow-sm p-4 w-[340px]">
      <div className="text-xs font-semibold text-ds-folio-ink mb-3 pb-2 border-b border-ds-hairline">
        Day 2 · Tokyo — Temples &amp; Gardens
      </div>
      <div className="space-y-1.5 mb-3">
        <div className="flex items-center gap-2 text-[11px] text-ds-folio-ink-soft">
          <span className="w-1.5 h-1.5 rounded-full bg-ds-marine-ink flex-shrink-0" />
          Senso-ji Temple
        </div>
        <div className="flex items-center gap-2 text-[11px] text-ds-folio-ink-soft">
          <span className="w-1.5 h-1.5 rounded-full bg-ds-marine-ink flex-shrink-0" />
          Ueno Park
        </div>
        <div className="flex items-center gap-2 text-[11px] text-ds-folio-ink-soft">
          <span className="w-1.5 h-1.5 rounded-full bg-ds-marine-ink flex-shrink-0" />
          Akihabara Electric Town
        </div>
        <div className="flex items-center gap-2 text-[11px] text-ds-folio-ink-soft">
          <span className="w-1.5 h-1.5 rounded-full bg-ds-marine-ink flex-shrink-0" />
          Tokyo National Museum
        </div>
      </div>
      {children}
      <div className="mt-2 pt-1 border-t border-ds-hairline/40 text-[9px] text-ds-folio-ink-mist/50 text-right">{label}</div>
    </div>
  );
}

export default function CheckRouteDemoPage() {
  return (
    <div className="min-h-screen bg-[#F7F4EE] p-8">
      <div className="max-w-5xl mx-auto">
        <div className="mb-8">
          <h1 className="text-lg font-semibold text-ds-folio-ink mb-1">
            CheckRoutePanel — PR #514 Visual Proof
          </h1>
          <p className="text-sm text-ds-folio-ink-mist">
            All 4 component states. Idle and loading are before any API call; success and error are post-click responses.
            Button only renders when ≥2 activity/meal stops with coordinates are present.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-6 lg:grid-cols-4">
          <div>
            <p className="text-[11px] font-semibold text-ds-folio-ink-mist uppercase tracking-wide mb-3">
              Idle — check-route-btn
            </p>
            <MockDayPanel label="state: idle">
              <IdleState />
            </MockDayPanel>
          </div>

          <div>
            <p className="text-[11px] font-semibold text-ds-folio-ink-mist uppercase tracking-wide mb-3">
              Loading — check-route-loading
            </p>
            <MockDayPanel label="state: loading">
              <LoadingState />
            </MockDayPanel>
          </div>

          <div>
            <p className="text-[11px] font-semibold text-ds-folio-ink-mist uppercase tracking-wide mb-3">
              Success — check-route-result
            </p>
            <MockDayPanel label="state: success">
              <SuccessState />
            </MockDayPanel>
          </div>

          <div>
            <p className="text-[11px] font-semibold text-ds-folio-ink-mist uppercase tracking-wide mb-3">
              Error / not-configured — check-route-error
            </p>
            <MockDayPanel label="state: error">
              <ErrorState />
            </MockDayPanel>
          </div>
        </div>

        <div className="mt-8 text-[10px] text-ds-folio-ink-mist/60">
          Demo page — not linked from app navigation.
          Error state copy surfaces <code>response.message</code> from backend (no internal status codes exposed).
          GOOGLE_ROUTES_API_KEY is never referenced in frontend source.
        </div>
      </div>
    </div>
  );
}
