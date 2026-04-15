import { CreditCard, TrendingUp } from "lucide-react";

const PLACEHOLDER_CARDS = [
  { name: "AMEX Gold", issuer: "American Express", points: 87_450, cpp: 2.0, color: "bg-amber-400" },
  { name: "Chase Sapphire Reserve", issuer: "Chase", points: 124_200, cpp: 1.8, color: "bg-sky-500" },
  { name: "Capital One Venture X", issuer: "Capital One", points: 53_100, cpp: 1.85, color: "bg-violet-500" },
];

export function PointsSummary() {
  const totalPoints = PLACEHOLDER_CARDS.reduce((s, c) => s + c.points, 0);
  const avgCpp =
    PLACEHOLDER_CARDS.reduce((s, c) => s + c.cpp, 0) / PLACEHOLDER_CARDS.length;
  const estimatedValue = (totalPoints * avgCpp) / 100;

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-slate-900">Points Summary</h2>
        <span className="badge badge-planned">
          <TrendingUp className="w-3 h-3" />
          {avgCpp.toFixed(2)}¢/pt avg
        </span>
      </div>

      {/* Total */}
      <div className="rounded-xl bg-slate-50 border border-slate-100 p-4 mb-4">
        <p className="text-xs text-slate-500 font-medium">Total Points</p>
        <p className="text-3xl font-bold text-slate-900 mt-0.5">
          {totalPoints.toLocaleString()}
        </p>
        <p className="text-sm text-emerald-600 font-medium mt-1">
          ≈ {new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(estimatedValue)} in travel value
        </p>
      </div>

      {/* Per card */}
      <ul className="space-y-2.5">
        {PLACEHOLDER_CARDS.map((card) => (
          <li key={card.name} className="flex items-center gap-3">
            <div className={`w-8 h-8 rounded-lg ${card.color} flex items-center justify-center shrink-0`}>
              <CreditCard className="w-4 h-4 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-800 truncate">{card.name}</p>
              <p className="text-xs text-slate-400">{card.issuer}</p>
            </div>
            <div className="text-right shrink-0">
              <p className="text-sm font-semibold text-slate-800">
                {card.points.toLocaleString()}
              </p>
              <p className="text-xs text-slate-400">{card.cpp}¢/pt</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
