import Link from "next/link";
import { PlusCircle, Search, CreditCard, Sparkles } from "lucide-react";

const actions = [
  {
    label: "New Trip",
    description: "Start planning your next adventure",
    href: "/trips/new",
    icon: PlusCircle,
    colorClass: "bg-brand-500/15 text-brand-400",
  },
  {
    label: "Search Flights",
    description: "Search flights inside any trip",
    href: "/trips",
    icon: Search,
    colorClass: "bg-violet-500/15 text-violet-400",
  },
  {
    label: "Manage Cards",
    description: "Track points across all your cards",
    href: "/cards",
    icon: CreditCard,
    colorClass: "bg-emerald-500/15 text-emerald-400",
  },
  {
    label: "AI Concierge",
    description: "Get personalized travel recommendations",
    href: "/concierge",
    icon: Sparkles,
    colorClass: "bg-amber-500/15 text-amber-400",
  },
];

export function QuickActions() {
  return (
    <div className="card p-6">
      <h2 className="text-base font-semibold text-cream-100 mb-4">Quick Actions</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {actions.map(({ label, description, href, icon: Icon, colorClass }) => (
          <Link
            key={href}
            href={href}
            className="flex items-center gap-3 p-3.5 rounded-xl border border-white/[.08] bg-white/[.04] backdrop-blur-[16px] transition-all duration-200 group hover:bg-white/[.08] hover:border-white/[.14] hover:-translate-y-0.5"
          >
            <div className={`flex items-center justify-center w-9 h-9 rounded-lg shrink-0 ${colorClass}`}>
              <Icon className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-cream-200 group-hover:text-cream-100 transition">
                {label}
              </p>
              <p className="text-xs text-cream-500 truncate">{description}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
