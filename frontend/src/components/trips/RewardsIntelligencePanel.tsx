"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Zap } from "lucide-react";
import { RewardsIntelligence } from "@/types";

interface RewardsIntelligencePanelProps {
  rewards: RewardsIntelligence;
}

export function RewardsIntelligencePanel({ rewards }: RewardsIntelligencePanelProps) {
  const [expanded, setExpanded] = useState(false);
  const isPoints = rewards.decision === "points";
  const currency = rewards.effectiveCurrency ?? "USD";
  const { breakdown } = rewards;
  const hasBreakdown =
    breakdown && (breakdown.earnRate || breakdown.opportunityCost || breakdown.transferPartner);

  return (
    <div className="mt-1.5 rounded-lg border border-slate-100 bg-slate-50/60 overflow-hidden">
      <div className="flex items-center gap-2 px-2 pt-2 pb-1 flex-wrap">
        <span
          className={`badge text-[10px] px-2 py-0.5 shrink-0 gap-1 ${
            isPoints ? "badge-best-value" : "badge-saved"
          }`}
        >
          <Zap className="w-2.5 h-2.5" />
          {isPoints ? "Use Points" : "Pay Cash"}
        </span>
        <div className="flex items-center gap-1.5 text-[10px] text-slate-500 flex-wrap">
          <span>
            <span className="font-medium text-slate-600">{rewards.cpp.toFixed(2)}</span>¢ CPP
          </span>
          <span className="text-slate-300">·</span>
          <span>
            <span className="font-medium text-slate-600">{rewards.adjustedCpp.toFixed(2)}</span>¢ adj.
          </span>
          <span className="text-slate-300">·</span>
          <span>
            eff.{" "}
            <span className="font-medium text-slate-700">
              {currency === "USD" ? "$" : ""}
              {rewards.effectiveCost.toFixed(0)}
              {currency !== "USD" ? ` ${currency}` : ""}
            </span>
          </span>
        </div>
      </div>

      <p className="px-2 pb-1.5 text-[10px] text-slate-400 italic leading-relaxed">
        {rewards.explanation}
      </p>

      {hasBreakdown && (
        <>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setExpanded((v) => !v);
            }}
            className="w-full flex items-center gap-0.5 px-2 py-1 text-[10px] text-slate-400 hover:text-slate-600 hover:bg-slate-100/70 transition-colors border-t border-slate-100"
          >
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            See breakdown
          </button>
          {expanded && (
            <div className="grid grid-cols-3 gap-2 px-2 pb-2 pt-1.5 border-t border-slate-100">
              {breakdown.earnRate && (
                <div>
                  <p className="text-[9px] uppercase tracking-wide text-slate-400 mb-0.5">
                    Earn Rate
                  </p>
                  <p className="text-[10px] font-semibold text-slate-700">{breakdown.earnRate}</p>
                </div>
              )}
              {breakdown.opportunityCost && (
                <div>
                  <p className="text-[9px] uppercase tracking-wide text-slate-400 mb-0.5">
                    Opp. Cost
                  </p>
                  <p className="text-[10px] font-semibold text-slate-700">
                    {breakdown.opportunityCost}
                  </p>
                </div>
              )}
              {breakdown.transferPartner && (
                <div>
                  <p className="text-[9px] uppercase tracking-wide text-slate-400 mb-0.5">
                    Transfer
                  </p>
                  <p className="text-[10px] font-semibold text-slate-700">
                    {breakdown.transferPartner}
                  </p>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
