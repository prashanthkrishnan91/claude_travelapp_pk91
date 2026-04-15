"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Map,
  PlusCircle,
  CreditCard,
  Settings,
  Plane,
} from "lucide-react";
import clsx from "clsx";

interface NavLink {
  label: string;
  href: string;
  icon: React.ElementType;
}

const primaryLinks: NavLink[] = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "My Trips", href: "/trips", icon: Map },
  { label: "New Trip", href: "/trips/new", icon: PlusCircle },
];

const secondaryLinks: NavLink[] = [
  { label: "Travel Cards", href: "/cards", icon: CreditCard },
  { label: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  function isActive(href: string) {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  }

  return (
    <aside className="hidden lg:flex lg:flex-col w-64 bg-white border-r border-slate-200 min-h-screen">
      {/* Brand */}
      <div className="flex items-center gap-2.5 px-5 py-5 border-b border-slate-100">
        <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-sky-600 text-white">
          <Plane className="w-5 h-5" />
        </div>
        <div>
          <p className="text-sm font-bold text-slate-900 leading-tight">Travel Concierge</p>
          <p className="text-xs text-slate-400">Trip Planner</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        <p className="px-3 mb-2 text-xs font-semibold uppercase tracking-widest text-slate-400">
          Planning
        </p>
        {primaryLinks.map(({ label, href, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={clsx("nav-item", isActive(href) && "nav-item-active")}
          >
            <Icon className="w-4 h-4 shrink-0" />
            {label}
          </Link>
        ))}

        <div className="pt-4">
          <p className="px-3 mb-2 text-xs font-semibold uppercase tracking-widest text-slate-400">
            Account
          </p>
          {secondaryLinks.map(({ label, href, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={clsx("nav-item", isActive(href) && "nav-item-active")}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </Link>
          ))}
        </div>
      </nav>

      {/* Footer / User */}
      <div className="px-4 py-4 border-t border-slate-100">
        <div className="flex items-center gap-3 rounded-xl px-2 py-2">
          <div className="w-8 h-8 rounded-full bg-sky-100 text-sky-700 flex items-center justify-center text-sm font-semibold">
            T
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-slate-800 truncate">Traveler</p>
            <p className="text-xs text-slate-400 truncate">traveler@example.com</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
