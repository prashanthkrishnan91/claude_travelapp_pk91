"use client";

/**
 * [TEMPORARY DEV-ONLY] AI Concierge Debug Trace UI
 * Remove this page before production launch.
 */

import { useState } from "react";
import { callConciergeDebugTrace, type ConciergeDebugTrace } from "@/lib/api";

// ── Collapsible JSON section ─────────────────────────────────────────────────

function JsonSection({
  title,
  data,
  defaultOpen = false,
}: {
  title: string;
  data: unknown;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const json = JSON.stringify(data, null, 2);
  const isEmpty =
    data === null ||
    data === undefined ||
    (Array.isArray(data) && data.length === 0) ||
    (typeof data === "object" && Object.keys(data as object).length === 0);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        type="button"
        className="w-full flex items-center justify-between px-4 py-2 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="text-sm font-mono font-medium text-gray-700">
          {title}
          {isEmpty && (
            <span className="ml-2 text-xs text-gray-400 font-sans">(empty)</span>
          )}
        </span>
        <span className="text-gray-400 text-xs">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <pre className="p-4 text-xs font-mono bg-white overflow-x-auto max-h-96 leading-relaxed text-gray-800 whitespace-pre-wrap">
          {json}
        </pre>
      )}
    </div>
  );
}

// ── Summary card ─────────────────────────────────────────────────────────────

function SummaryRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-1 border-b border-gray-100 last:border-0">
      <span className="text-sm text-gray-600">{label}</span>
      <span className="text-sm font-semibold text-gray-900">{value}</span>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ConciergeDebugPage() {
  const [query, setQuery] = useState("");
  const [location, setLocation] = useState("");
  const [limit, setLimit] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [trace, setTrace] = useState<ConciergeDebugTrace | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim() || !location.trim()) return;

    setLoading(true);
    setError(null);
    setTrace(null);

    try {
      const result = await callConciergeDebugTrace(query.trim(), location.trim(), limit);
      setTrace(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  function copyJson() {
    if (!trace) return;
    navigator.clipboard.writeText(JSON.stringify(trace, null, 2)).catch(() => {});
  }

  const rejectedByReason = trace?.summary.rejectedCountByReason ?? {};
  const rejectedTotal = Object.values(rejectedByReason).reduce((s, n) => s + n, 0);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="bg-amber-50 border border-amber-300 rounded-lg px-4 py-3 flex items-start gap-3">
        <span className="text-amber-500 text-lg mt-0.5">⚠</span>
        <div>
          <p className="text-sm font-semibold text-amber-800">Developer Tool — Temporary</p>
          <p className="text-xs text-amber-700 mt-0.5">
            This page is internal debug tooling for inspecting the AI Concierge pipeline. Remove
            before production launch. Do not share this URL.
          </p>
        </div>
      </div>

      <h1 className="text-xl font-bold text-gray-900">AI Concierge Debug Trace</h1>

      {/* Form */}
      <form
        onSubmit={handleSubmit}
        className="bg-white border border-gray-200 rounded-xl p-5 space-y-4 shadow-sm"
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">User Query</label>
            <input
              type="text"
              required
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. cocktail bars in Chicago"
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
            <input
              type="text"
              required
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g. Chicago"
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="flex items-end gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Limit <span className="font-normal text-gray-400">(max results from provider)</span>
            </label>
            <input
              type="number"
              min={1}
              max={20}
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="w-24 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {loading ? "Running…" : "Run Debug Trace"}
          </button>
        </div>
      </form>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
          <span className="font-semibold">Error: </span>
          {error}
        </div>
      )}

      {/* Results */}
      {trace && (
        <div className="space-y-6">
          {/* Summary */}
          <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-gray-900">Summary</h2>
              <button
                type="button"
                onClick={copyJson}
                className="text-xs px-3 py-1 border border-gray-300 rounded-md hover:bg-gray-50 text-gray-600 transition-colors"
              >
                Copy full JSON
              </button>
            </div>

            <div className="divide-y divide-gray-100">
              <SummaryRow label="Parsed intent" value={
                <span className="font-mono bg-gray-100 px-2 py-0.5 rounded text-xs">
                  {trace.parsedIntent}
                </span>
              } />
              <SummaryRow label="Cache hit" value={
                <span className={trace.cacheStatus.hit ? "text-green-600" : "text-gray-500"}>
                  {trace.cacheStatus.hit ? "Yes" : "No"}
                </span>
              } />
              <SummaryRow label="Raw candidate count" value={trace.summary.rawCandidateCount} />
              <SummaryRow label="Deduped candidate count" value={trace.summary.dedupedCandidateCount} />
              <SummaryRow label="Google matched count" value={trace.summary.googleMatchedCount} />
              <SummaryRow
                label="Rejected count"
                value={
                  rejectedTotal > 0 ? (
                    <span>
                      {rejectedTotal}
                      <span className="ml-2 text-xs text-gray-400 font-normal">
                        ({Object.entries(rejectedByReason)
                          .map(([k, v]) => `${k}: ${v}`)
                          .join(", ")})
                      </span>
                    </span>
                  ) : (
                    "0"
                  )
                }
              />
              <SummaryRow
                label="Final addable cards"
                value={
                  <span className={trace.summary.finalAddableCount > 0 ? "text-green-700" : "text-gray-500"}>
                    {trace.summary.finalAddableCount}
                  </span>
                }
              />
              <SummaryRow label="Research-only sources" value={trace.summary.researchOnlyCount} />
              {Object.keys(trace.summary.whyPickSourceDistribution).length > 0 && (
                <SummaryRow
                  label="why_pick source distribution"
                  value={
                    <span className="text-xs font-mono text-gray-700">
                      {JSON.stringify(trace.summary.whyPickSourceDistribution)}
                    </span>
                  }
                />
              )}
            </div>
          </div>

          {/* JSON sections */}
          <div className="space-y-2">
            <h2 className="font-semibold text-gray-900">Raw Data</h2>

            <JsonSection title="parsed_intent" data={trace.parsedIntent} defaultOpen />
            <JsonSection title="search_queries" data={trace.searchQueries} defaultOpen />
            <JsonSection title="raw_candidates" data={trace.rawCandidates} />
            <JsonSection title="deduped_candidates" data={trace.dedupedCandidates} />
            <JsonSection title="google_verification" data={trace.googleVerification} />
            <JsonSection title="rejection_reasons" data={trace.rejectionReasons} />
            <JsonSection title="final_addable_cards" data={trace.finalAddableCards} />
            <JsonSection title="final_display_payload" data={trace.finalDisplayPayload} />
            <JsonSection title="cache_status" data={trace.cacheStatus} defaultOpen />
          </div>
        </div>
      )}
    </div>
  );
}
