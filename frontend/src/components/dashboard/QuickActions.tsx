import Link from "next/link";
import { PlusCircle, Search, CreditCard, Sparkles } from "lucide-react";

const actions = [
  {
    label: "New Trip",
    description: "Start planning your next adventure",
    href: "/trips/new",
    icon: PlusCircle,
    colorClass: "bg-sky-50 text-sky-600",
  },
  {
    label: "Search Flights",
    description: "Find the best routes and fares",
    href: "/search",
    icon: Search,
    colorClass: "bg-violet-50 text-violet-600",
  },
  {
    label: "Manage Cards",
    description: "Track points across all your cards",
    href: "/cards",
    icon: CreditCard,
    colorClass: "bg-emerald-50 text-emerald-600",
  },
  {
    label: "AI Concierge",
    description: "Get personalized travel recommendations",
    href: "/concierge",
    icon: Sparkles,
    colorClass: "bg-amber-50 text-amber-600",
  },
];

export function QuickActions() {
  return (
    <div className="card p-6">
      <h2 className="text-base font-semibold text-slate-900 mb-4">Quick Actions</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {actions.map(({ label, description, href, icon: Icon, colorClass }) => (
          <Link
            key={href}
            href={href}
            className="flex items-center gap-3 p-3.5 rounded-xl border border-slate-200
                       hover:border-slate-300 hover:bg-slate-50 transition group"
          >
            <div className={`flex items-center justify-center w-9 h-9 rounded-lg shrink-0 ${colorClass}`}>
              <Icon className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-slate-800 group-hover:text-slate-900">
                {label}
              </p>
              <p className="text-xs text-slate-400 truncate">{description}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
