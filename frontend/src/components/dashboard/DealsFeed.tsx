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
      ? "bg-emerald-500/12 text-emerald-400 border border-emerald-500/20"
      : score >= 60
      ? "bg-brand-500/12 text-brand-400 border border-brand-500/20"
      : "bg-white/[.05] text-cream-400 border border-white/[.08]";

  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${color}`}
    >
      <TrendingUp className="w-3 h-3" />
      {score}
    </span>
  );
}

function DealCard({ deal }: { deal: DealItem }) {
  return (
    <div className="flex items-start gap-4 px-6 py-4 hover:bg-white/[.04] transition-all duration-150 group border-l-2 border-transparent hover:border-brand-400">
      <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-amber-500/15 text-amber-400 shrink-0 mt-0.5">
        <Tag className="w-4 h-4" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-semibold text-cream-100 truncate">
            {deal.title}
          </span>
          <ScoreBadge score={deal.valueScore} />
        </div>

        <p className="text-xs text-cream-400 mt-0.5 line-clamp-2">
          {deal.description}
        </p>

        {deal.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1.5">
            {deal.tags.map((tag) => (
              <span
                key={tag}
                className="inline-block text-[10px] font-medium px-1.5 py-0.5 rounded bg-brand-500/12 text-brand-400 border border-brand-500/20"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      <Link
        href="/trips/new"
        className="shrink-0 mt-0.5 text-xs font-medium text-brand-400 hover:text-brand-300 whitespace-nowrap transition"
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
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/[.06]">
        <h2 className="text-base font-semibold text-cream-100">Deals For You</h2>
        <Link
          href="/trips/new"
          className="flex items-center gap-1 text-sm text-brand-400 hover:text-brand-300 font-medium transition"
        >
          Explore all <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {deals.length === 0 ? (
        <div className="px-6 py-8 text-center text-cream-500">
          <Tag className="w-8 h-8 mx-auto mb-2 text-cream-500/60" />
          <p className="text-sm font-medium text-cream-400">No deals yet</p>
          <p className="text-xs text-cream-500 mt-1">
            Search for flights or hotels to see personalised deals here.
          </p>
          <Link
            href="/trips/new"
            className="text-sm text-brand-400 hover:text-brand-300 font-medium mt-3 inline-block"
          >
            Start researching →
          </Link>
        </div>
      ) : (
        <ul className="divide-y divide-white/[.05]">
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
