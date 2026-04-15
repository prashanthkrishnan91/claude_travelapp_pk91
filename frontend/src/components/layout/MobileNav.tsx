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
  { label: "Dashboard",    href: "/",         icon: LayoutDashboard },
  { label: "My Trips",     href: "/trips",    icon: Map },
  { label: "New Trip",     href: "/trips/new", icon: PlusCircle },
  { label: "Travel Cards", href: "/cards",    icon: CreditCard },
  { label: "Settings",     href: "/settings", icon: Settings },
];

/* Bottom tab bar items (5 across) */
const tabLinks = links;

export function MobileNav() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  function isActive(href: string) {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  }

  return (
    <>
      {/* ── Glass top bar ───────────────────────────────────── */}
      <header className="lg:hidden sticky top-0 z-40 flex items-center justify-between px-4 py-3 glass border-b border-slate-200/70">
        <div className="flex items-center gap-2">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-sky-600 text-white">
            <Plane className="w-4 h-4" />
          </div>
          <span className="text-sm font-bold text-slate-900">Travel Concierge</span>
        </div>
        <button
          onClick={() => setOpen(!open)}
          className="p-2 rounded-lg text-slate-600 hover:bg-slate-100/80 transition"
          aria-label="Toggle menu"
        >
          {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </header>

      {/* ── Drawer overlay ──────────────────────────────────── */}
      {open && (
        <div
          className="lg:hidden fixed inset-0 z-30 bg-slate-900/30 backdrop-blur-sm"
          onClick={() => setOpen(false)}
        />
      )}

      {/* ── Slide-out drawer ────────────────────────────────── */}
      <div
        className={clsx(
          "lg:hidden fixed inset-y-0 left-0 z-40 w-64 glass border-r border-slate-200/70",
          "transition-transform duration-300 ease-out",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-center gap-2 px-5 py-4 border-b border-slate-100/80">
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

      {/* ── Bottom tab bar (Apple-style) ─────────────────────── */}
      <nav className="lg:hidden fixed bottom-0 inset-x-0 z-40 glass border-t border-slate-200/70 flex items-stretch pb-safe">
        {tabLinks.map(({ label, href, icon: Icon }) => {
          const active = isActive(href);
          const isNew = href === "/trips/new";
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex-1 flex flex-col items-center justify-center gap-0.5 py-2.5 min-w-0 transition-colors",
                active ? "text-sky-600" : "text-slate-400 hover:text-slate-600"
              )}
              aria-label={label}
            >
              <span
                className={clsx(
                  "flex items-center justify-center rounded-xl transition-all",
                  isNew
                    ? "w-10 h-10 bg-sky-600 text-white shadow-md shadow-sky-200 -mt-4"
                    : "w-7 h-7",
                  isNew && active && "bg-sky-700"
                )}
              >
                <Icon className={isNew ? "w-5 h-5" : "w-5 h-5"} />
              </span>
              <span className={clsx("text-[10px] font-medium leading-none", isNew && "mt-0.5")}>
                {label === "New Trip" ? "New" : label === "Travel Cards" ? "Cards" : label}
              </span>
            </Link>
          );
        })}
      </nav>
    </>
  );
}
