"use client";

import { X, Trophy, DollarSign, Coins, BarChart2, Star, Zap, CreditCard } from "lucide-react";
import { CompareResult } from "@/types";

interface CompareModalProps {
  results: CompareResult[];
  onClose: () => void;
}

// ─── SVG score ring ───────────────────────────────────────────────────────────

function ScoreRing({ score, isWinner }: { score: number; isWinner: boolean }) {
  const r = 30;
  const circ = 2 * Math.PI * r;
  const fill = circ * (score / 100);
  const stroke = isWinner ? "#0284c7" : score >= 70 ? "#059669" : score >= 50 ? "#d97706" : "#94a3b8";

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width="76" height="76" viewBox="0 0 76 76" className="-rotate-90">
        <circle cx="38" cy="38" r={r} fill="none" stroke="#e2e8f0" strokeWidth="5" />
        <circle
          cx="38"
          cy="38"
          r={r}
          fill="none"
          stroke={stroke}
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={`${fill} ${circ - fill}`}
        />
      </svg>
      <span
        className={`absolute text-xl font-bold ${
          isWinner ? "text-sky-600" : score >= 70 ? "text-emerald-600" : "text-slate-700"
        }`}
      >
        {score}
      </span>
    </div>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const RANK_LABEL = ["#1", "#2", "#3", "#4", "#5", "#6", "#7", "#8", "#9", "#10"];

const RANK_STYLE = [
  "bg-amber-100 text-amber-700 ring-1 ring-amber-300",
  "bg-slate-100 text-slate-600 ring-1 ring-slate-300",
  "bg-orange-50 text-orange-500 ring-1 ring-orange-200",
  "bg-slate-50 text-slate-400",
  "bg-slate-50 text-slate-400",
];

const TAG_COLOR: Record<string, string> = {
  "Best Value":           "bg-sky-50 text-sky-700 border border-sky-200",
  "Best Points":          "bg-violet-50 text-violet-700 border border-violet-200",
  "Luxury Pick":          "bg-amber-50 text-amber-700 border border-amber-200",
  "Points Better":        "bg-emerald-50 text-emerald-700 border border-emerald-200",
  "Cash Better":          "bg-blue-50 text-blue-700 border border-blue-200",
  "Preferred Airline":    "bg-rose-50 text-rose-700 border border-rose-200",
  "Preferred Hotel":      "bg-rose-50 text-rose-700 border border-rose-200",
  "High Opportunity Cost":"bg-red-50 text-red-700 border border-red-200",
};

const TAG_ICON: Record<string, React.ReactNode> = {
  "Best Value":    <Star className="w-2.5 h-2.5" />,
  "Best Points":   <Coins className="w-2.5 h-2.5" />,
  "Points Better": <Coins className="w-2.5 h-2.5" />,
  "Cash Better":   <CreditCard className="w-2.5 h-2.5" />,
  "Luxury Pick":   <Zap className="w-2.5 h-2.5" />,
};

// ─── Main component ───────────────────────────────────────────────────────────

export function CompareModal({ results, onClose }: CompareModalProps) {
  // Rank items best → worst
  const ranked = [...results].sort((a, b) => b.valueScore - a.valueScore);
  const winner = ranked[0];
  const maxScore = winner.valueScore;
  const minCash = Math.min(...ranked.filter((r) => r.price > 0).map((r) => r.price));
  const minPoints = Math.min(...ranked.filter((r) => r.points > 0).map((r) => r.points));

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl max-h-[92vh] overflow-hidden flex flex-col">

        {/* ── Header ── */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 flex-shrink-0">
          <div className="flex items-center gap-2.5">
            <BarChart2 className="w-5 h-5 text-sky-600" />
            <h2 className="text-lg font-semibold text-slate-800">Side-by-Side Compare</h2>
            <span className="px-2 py-0.5 text-xs font-medium bg-slate-100 text-slate-500 rounded-full">
              {results.length} options
            </span>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* ── Winner verdict banner ── */}
        <div className="flex items-center gap-3 px-6 py-3 bg-gradient-to-r from-amber-50 via-sky-50 to-white border-b border-amber-100 flex-shrink-0">
          <div className="flex-shrink-0 w-7 h-7 rounded-full bg-amber-100 flex items-center justify-center">
            <Trophy className="w-3.5 h-3.5 text-amber-600" />
          </div>
          <p className="text-sm text-slate-700 leading-tight">
            <span className="font-semibold text-slate-900">{winner.name}</span>
            {" "}leads with a value score of{" "}
            <span className="font-semibold text-sky-600">{maxScore}/100</span>
            {winner.tags.length > 0 && (
              <span className="text-slate-400"> · {winner.tags.slice(0, 2).join(" · ")}</span>
            )}
          </p>
        </div>

        {/* ── Item cards ── */}
        <div className="overflow-auto flex-1 p-5">
          <div className="flex gap-4 overflow-x-auto pb-2">
            {ranked.map((r, idx) => {
              const isWinner = idx === 0;
              const isCheapestCash = r.price > 0 && r.price === minCash;
              const isCheapestPoints = r.points > 0 && r.points === minPoints;

              return (
                <div
                  key={r.id}
                  className={`flex-1 min-w-[200px] rounded-xl border p-4 flex flex-col gap-3 ${
                    isWinner
                      ? "border-sky-200 bg-gradient-to-b from-sky-50/60 to-white shadow-sm ring-1 ring-sky-200"
                      : "border-slate-200 bg-white"
                  }`}
                >
                  {/* Rank badge row */}
                  <div className="flex items-center justify-between">
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                        RANK_STYLE[Math.min(idx, RANK_STYLE.length - 1)]
                      }`}
                    >
                      {RANK_LABEL[idx]}
                    </span>
                    {isWinner && (
                      <Trophy className="w-3.5 h-3.5 text-amber-500" />
                    )}
                  </div>

                  {/* Score ring */}
                  <div className="flex flex-col items-center gap-2">
                    <ScoreRing score={r.valueScore} isWinner={isWinner} />
                    <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wide">
                      Value Score
                    </span>
                    {/* Confidence bar relative to leader */}
                    <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          isWinner ? "bg-sky-400" : "bg-slate-300"
                        }`}
                        style={{ width: `${(r.valueScore / maxScore) * 100}%` }}
                      />
                    </div>
                  </div>

                  {/* Name + type */}
                  <div className="text-center pt-0.5">
                    <p className="text-sm font-semibold text-slate-800 leading-snug">{r.name}</p>
                    <p className="text-xs text-slate-400 capitalize mt-0.5">{r.type}</p>
                  </div>

                  {/* Pricing block */}
                  <div className="flex flex-col gap-1.5">
                    {r.price > 0 && (
                      <div
                        className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg ${
                          isCheapestCash
                            ? "bg-emerald-50 border border-emerald-100"
                            : "bg-slate-50"
                        }`}
                      >
                        <div className="flex items-center gap-1 text-xs text-slate-400">
                          <DollarSign className="w-3 h-3" />
                          Cash
                        </div>
                        <span
                          className={`text-sm font-semibold ${
                            isCheapestCash ? "text-emerald-600" : "text-slate-700"
                          }`}
                        >
                          ${r.price.toLocaleString()}
                          {isCheapestCash && (
                            <span className="ml-1 text-[10px] font-normal text-emerald-500">lowest</span>
                          )}
                        </span>
                      </div>
                    )}

                    {r.points > 0 && (
                      <div
                        className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg ${
                          isCheapestPoints
                            ? "bg-violet-50 border border-violet-100"
                            : "bg-slate-50"
                        }`}
                      >
                        <div className="flex items-center gap-1 text-xs text-slate-400">
                          <Coins className="w-3 h-3" />
                          Points
                        </div>
                        <span
                          className={`text-sm font-semibold ${
                            isCheapestPoints ? "text-violet-600" : "text-violet-500"
                          }`}
                        >
                          {r.points.toLocaleString()}
                          {isCheapestPoints && (
                            <span className="ml-1 text-[10px] font-normal text-violet-400">fewest</span>
                          )}
                        </span>
                      </div>
                    )}

                    {r.cpp != null && (
                      <div className="flex items-center justify-between px-2.5 py-1 rounded-lg bg-slate-50">
                        <span className="text-xs text-slate-400">CPP</span>
                        <span className="text-xs font-semibold text-slate-600">
                          {r.cpp.toFixed(2)}¢
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Tags */}
                  {r.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {r.tags.map((tag) => (
                        <span
                          key={tag}
                          className={`inline-flex items-center gap-1 px-1.5 py-0.5 text-[11px] rounded-full font-medium ${
                            TAG_COLOR[tag] ?? "bg-slate-100 text-slate-500 border border-slate-200"
                          }`}
                        >
                          {TAG_ICON[tag]}
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Recommendation reason */}
                  <p className="text-[11px] leading-relaxed text-slate-400 border-t border-slate-100 pt-2.5 mt-auto">
                    {r.recommendationReason}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Score ladder footer ── */}
        <div className="px-6 py-4 border-t border-slate-100 bg-slate-50/60 flex-shrink-0">
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-2.5">
            Score Ladder
          </p>
          <div className="flex flex-col gap-2">
            {ranked.map((r, idx) => (
              <div key={r.id} className="flex items-center gap-3">
                <span className="text-xs text-slate-400 w-4 text-right">{idx + 1}</span>
                <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      idx === 0 ? "bg-sky-400" : idx === 1 ? "bg-slate-400" : "bg-slate-300"
                    }`}
                    style={{ width: `${r.valueScore}%` }}
                  />
                </div>
                <span className="text-xs font-semibold text-slate-600 w-16 truncate">{r.name}</span>
                <span
                  className={`text-xs font-bold w-8 text-right ${
                    idx === 0 ? "text-sky-600" : "text-slate-500"
                  }`}
                >
                  {r.valueScore}
                </span>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}
