import { CreditCard, TrendingUp } from "lucide-react";
import Link from "next/link";
import type { TravelCard } from "@/types";

interface PointsSummaryProps {
  cards: TravelCard[];
}

const CARD_COLORS = [
  "bg-brand-500/80",
  "bg-violet-500/80",
  "bg-emerald-500/80",
  "bg-amber-500/80",
  "bg-rose-500/80",
];

export function PointsSummary({ cards }: PointsSummaryProps) {
  const totalPoints = cards.reduce((s, c) => s + (c.pointsBalance ?? 0), 0);
  const avgCpp =
    cards.length > 0
      ? cards.reduce((s, c) => s + (c.pointValueCpp ?? 0), 0) / cards.length
      : 0;
  const estimatedValue = avgCpp > 0 ? (totalPoints * avgCpp) / 100 : 0;

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-cream-100">Points Summary</h2>
        {avgCpp > 0 && (
          <span className="badge badge-planned">
            <TrendingUp className="w-3 h-3" />
            {avgCpp.toFixed(2)}¢/pt avg
          </span>
        )}
      </div>

      {cards.length === 0 ? (
        <div className="text-center py-6 text-cream-500">
          <CreditCard className="w-8 h-8 mx-auto mb-2 text-cream-500/60" />
          <p className="text-sm font-medium text-cream-400">No cards added yet</p>
          <Link
            href="/cards"
            className="text-sm text-brand-400 hover:text-brand-300 font-medium mt-2 inline-block"
          >
            Add a travel card →
          </Link>
        </div>
      ) : (
        <>
          {/* Total */}
          <div className="rounded-xl bg-white/[.05] backdrop-blur-[16px] border border-white/[.08] p-4 mb-4">
            <p className="text-xs text-cream-500 font-medium">Total Points</p>
            <p className="text-3xl font-bold text-cream-100 mt-0.5">
              {totalPoints.toLocaleString()}
            </p>
            {estimatedValue > 0 && (
              <span className="badge badge-value mt-2">
                ≈{" "}
                {new Intl.NumberFormat("en-US", {
                  style: "currency",
                  currency: "USD",
                  maximumFractionDigits: 0,
                }).format(estimatedValue)}{" "}
                value
              </span>
            )}
          </div>

          {/* Per card */}
          <ul className="space-y-2.5">
            {cards.map((card, idx) => (
              <li key={card.id} className="flex items-center gap-3">
                <div
                  className={`w-8 h-8 rounded-lg ${CARD_COLORS[idx % CARD_COLORS.length]} flex items-center justify-center shrink-0`}
                >
                  <CreditCard className="w-4 h-4 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-cream-200 truncate">
                    {card.displayName}
                  </p>
                  <p className="text-xs text-cream-500">{card.issuer}</p>
                </div>
                <div className="text-right shrink-0 space-y-1">
                  <p className="text-sm font-semibold text-cream-100">
                    {(card.pointsBalance ?? 0).toLocaleString()}
                  </p>
                  {card.pointValueCpp && (
                    <span className="badge badge-savings text-[10px] px-1.5 py-0.5">
                      {card.pointValueCpp}¢/pt
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
