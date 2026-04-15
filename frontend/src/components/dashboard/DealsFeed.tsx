import Link from "next/link";
import { Tag, TrendingUp, ArrowRight } from "lucide-react";
import type { DealItem } from "@/types";

interface DealsFeedProps {
  deals: DealItem[];
}

function ScoreBadge({ score }: { score: number }) {
  if (score >= 90) {
    return (
      <span className="badge badge-gold text-xs gap-1">
        <TrendingUp className="w-3 h-3" />
        {score}
      </span>
    );
  }
  const color =
    score >= 75
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : score >= 60
      ? "bg-sky-50 text-sky-700 border-sky-200"
      : "bg-slate-50 text-slate-600 border-slate-200";

  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full border ${color}`}
    >
      <TrendingUp className="w-3 h-3" />
      {score}
    </span>
  );
}

function DealCard({ deal }: { deal: DealItem }) {
  return (
    <div className="flex items-start gap-4 px-6 py-4 hover:bg-slate-50 transition-all duration-150 group border-l-2 border-transparent hover:border-sky-400">
      <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-amber-50 text-amber-600 shrink-0 mt-0.5">
        <Tag className="w-4 h-4" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-semibold text-slate-900 truncate">
            {deal.title}
          </span>
          <ScoreBadge score={deal.valueScore} />
        </div>

        <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">
          {deal.description}
        </p>

        {deal.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1.5">
            {deal.tags.map((tag) => (
              <span
                key={tag}
                className="inline-block text-[10px] font-medium px-1.5 py-0.5 rounded bg-sky-50 text-sky-700 border border-sky-100"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      <Link
        href="/trips/new"
        className="shrink-0 mt-0.5 text-xs font-medium text-sky-600 hover:text-sky-700 whitespace-nowrap transition"
        aria-label={`Plan a trip using ${deal.title}`}
      >
        Plan trip
      </Link>
    </div>
  );
}

export function DealsFeed({ deals }: DealsFeedProps) {
  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
        <h2 className="text-base font-semibold text-slate-900">Deals For You</h2>
        <Link
          href="/trips/new"
          className="flex items-center gap-1 text-sm text-sky-600 hover:text-sky-700 font-medium transition"
        >
          Explore all <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {deals.length === 0 ? (
        <div className="px-6 py-8 text-center text-slate-400">
          <Tag className="w-8 h-8 mx-auto mb-2 text-slate-300" />
          <p className="text-sm font-medium text-slate-500">No deals yet</p>
          <p className="text-xs text-slate-400 mt-1">
            Search for flights or hotels to see personalised deals here.
          </p>
          <Link
            href="/trips/new"
            className="text-sm text-sky-600 hover:text-sky-700 font-medium mt-3 inline-block"
          >
            Start researching →
          </Link>
        </div>
      ) : (
        <ul className="divide-y divide-slate-100">
          {deals.map((deal) => (
            <li key={deal.itemId}>
              <DealCard deal={deal} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
