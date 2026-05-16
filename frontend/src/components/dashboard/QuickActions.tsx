import Link from "next/link";
import { PlusCircle, Search, CreditCard, Sparkles } from "lucide-react";
import { Card } from "@/components/ui/Card";

const actions = [
  {
    label: "New Trip",
    description: "Start planning your next adventure",
    href: "/trips/new",
    icon: PlusCircle,
  },
  {
    label: "Search Flights",
    description: "Search flights inside any trip",
    href: "/trips",
    icon: Search,
  },
  {
    label: "Manage Cards",
    description: "Track points across all your cards",
    href: "/cards",
    icon: CreditCard,
  },
  {
    label: "AI Concierge",
    description: "Get personalised travel recommendations",
    href: "/concierge",
    icon: Sparkles,
  },
];

export function QuickActions() {
  return (
    <Card as="div" tone="dark" className="p-6">
      <h2 className="text-base font-semibold text-ds-text mb-4">
        Quick Actions
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {actions.map(({ label, description, href, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className="group flex items-center gap-3 p-3.5 rounded-xl border border-ds-pen-stroke bg-ds-carbon hover:border-ds-accent/40 hover:bg-ds-onyx transition-all duration-200"
          >
            <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-ds-accent-subtle text-ds-accent shrink-0">
              <Icon className="w-4 h-4" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-ds-text group-hover:text-ds-accent transition">
                {label}
              </p>
              <p className="text-xs text-ds-text-tertiary truncate">
                {description}
              </p>
            </div>
          </Link>
        ))}
      </div>
    </Card>
  );
}
