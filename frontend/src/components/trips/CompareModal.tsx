"use client";

import { X, Trophy, DollarSign, Coins, BarChart2 } from "lucide-react";
import { CompareResult } from "@/types";

interface CompareModalProps {
  results: CompareResult[];
  onClose: () => void;
}

export function CompareModal({ results, onClose }: CompareModalProps) {
  const maxScore = Math.max(...results.map((r) => r.valueScore));

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 flex-shrink-0">
          <div className="flex items-center gap-2">
            <BarChart2 className="w-5 h-5 text-sky-600" />
            <h2 className="text-lg font-semibold text-slate-800">Compare Options</h2>
            <span className="text-sm text-slate-400">{results.length} items</span>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
            aria-label="Close compare"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Table */}
        <div className="overflow-auto flex-1">
          <table className="w-full border-collapse">
            <thead className="sticky top-0 z-10">
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide w-32">
                  Metric
                </th>
                {results.map((r) => (
                  <th key={r.id} className="px-4 py-3 text-center min-w-[180px]">
                    <div className="flex flex-col items-center gap-1">
                      {r.valueScore === maxScore && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 text-xs font-medium">
                          <Trophy className="w-3 h-3" />
                          Best
                        </span>
                      )}
                      <span className="text-sm font-semibold text-slate-800 leading-tight">
                        {r.name}
                      </span>
                      <span className="text-xs text-slate-400 capitalize">{r.type}</span>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {/* Value Score */}
              <tr>
                <td className="px-6 py-3 text-xs font-medium text-slate-500 whitespace-nowrap">
                  Value Score
                </td>
                {results.map((r) => (
                  <td key={r.id} className="px-4 py-3 text-center">
                    <div className="flex flex-col items-center gap-1.5">
                      <span
                        className={`text-2xl font-bold ${
                          r.valueScore === maxScore ? "text-sky-600" : "text-slate-700"
                        }`}
                      >
                        {r.valueScore}
                      </span>
                      <div className="w-full max-w-[120px] h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${
                            r.valueScore === maxScore ? "bg-sky-500" : "bg-slate-300"
                          }`}
                          style={{ width: `${r.valueScore}%` }}
                        />
                      </div>
                    </div>
                  </td>
                ))}
              </tr>

              {/* Cash Price */}
              <tr>
                <td className="px-6 py-3 text-xs font-medium text-slate-500 whitespace-nowrap">
                  Cash Price
                </td>
                {results.map((r) => (
                  <td key={r.id} className="px-4 py-3 text-center">
                    {r.price > 0 ? (
                      <span className="inline-flex items-center gap-0.5 text-sm font-medium text-emerald-600">
                        <DollarSign className="w-3.5 h-3.5" />
                        {r.price.toLocaleString()}
                      </span>
                    ) : (
                      <span className="text-sm text-slate-300">—</span>
                    )}
                  </td>
                ))}
              </tr>

              {/* Points */}
              <tr>
                <td className="px-6 py-3 text-xs font-medium text-slate-500 whitespace-nowrap">
                  Points
                </td>
                {results.map((r) => (
                  <td key={r.id} className="px-4 py-3 text-center">
                    {r.points > 0 ? (
                      <span className="inline-flex items-center gap-0.5 text-sm font-medium text-violet-600">
                        <Coins className="w-3.5 h-3.5" />
                        {r.points.toLocaleString()}
                      </span>
                    ) : (
                      <span className="text-sm text-slate-300">—</span>
                    )}
                  </td>
                ))}
              </tr>

              {/* CPP */}
              <tr>
                <td className="px-6 py-3 text-xs font-medium text-slate-500 whitespace-nowrap">
                  CPP
                </td>
                {results.map((r) => (
                  <td key={r.id} className="px-4 py-3 text-center">
                    <span className="text-sm font-medium text-slate-700">
                      {r.cpp != null ? `${r.cpp.toFixed(2)}¢` : "—"}
                    </span>
                  </td>
                ))}
              </tr>

              {/* Tags */}
              <tr>
                <td className="px-6 py-3 text-xs font-medium text-slate-500 whitespace-nowrap">
                  Tags
                </td>
                {results.map((r) => (
                  <td key={r.id} className="px-4 py-3 text-center">
                    {r.tags.length > 0 ? (
                      <div className="flex flex-wrap gap-1 justify-center">
                        {r.tags.map((tag) => (
                          <span
                            key={tag}
                            className="px-1.5 py-0.5 text-xs rounded-full bg-sky-50 text-sky-700 font-medium"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-sm text-slate-300">—</span>
                    )}
                  </td>
                ))}
              </tr>

              {/* Recommendation */}
              <tr>
                <td className="px-6 py-3 text-xs font-medium text-slate-500 whitespace-nowrap align-top pt-4">
                  Why
                </td>
                {results.map((r) => (
                  <td key={r.id} className="px-4 py-4 text-center align-top">
                    <p className="text-xs text-slate-500 leading-relaxed">
                      {r.recommendationReason}
                    </p>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
