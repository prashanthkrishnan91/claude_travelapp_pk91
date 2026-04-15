"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Menu,
  X,
  LayoutDashboard,
  Map,
  PlusCircle,
  CreditCard,
  Settings,
  Plane,
} from "lucide-react";
import clsx from "clsx";

const links = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "My Trips", href: "/trips", icon: Map },
  { label: "New Trip", href: "/trips/new", icon: PlusCircle },
  { label: "Travel Cards", href: "/cards", icon: CreditCard },
  { label: "Settings", href: "/settings", icon: Settings },
];

export function MobileNav() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  function isActive(href: string) {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  }

  return (
    <>
      {/* Top bar */}
      <header className="lg:hidden sticky top-0 z-40 flex items-center justify-between px-4 py-3 bg-white border-b border-slate-200">
        <div className="flex items-center gap-2">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-sky-600 text-white">
            <Plane className="w-4 h-4" />
          </div>
          <span className="text-sm font-bold text-slate-900">Travel Concierge</span>
        </div>
        <button
          onClick={() => setOpen(!open)}
          className="p-2 rounded-lg text-slate-600 hover:bg-slate-100 transition"
          aria-label="Toggle menu"
        >
          {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </header>

      {/* Drawer overlay */}
      {open && (
        <div
          className="lg:hidden fixed inset-0 z-30 bg-slate-900/40 backdrop-blur-sm"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Drawer */}
      <div
        className={clsx(
          "lg:hidden fixed inset-y-0 left-0 z-40 w-64 bg-white border-r border-slate-200",
          "transition-transform duration-300",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-center gap-2 px-5 py-4 border-b border-slate-100">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-sky-600 text-white">
            <Plane className="w-4 h-4" />
          </div>
          <span className="text-sm font-bold text-slate-900">Travel Concierge</span>
        </div>
        <nav className="px-3 py-4 space-y-0.5">
          {links.map(({ label, href, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              onClick={() => setOpen(false)}
              className={clsx("nav-item", isActive(href) && "nav-item-active")}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </Link>
          ))}
        </nav>
      </div>
    </>
  );
}
