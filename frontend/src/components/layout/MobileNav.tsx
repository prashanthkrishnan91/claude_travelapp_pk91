"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Menu,
  X,
  LayoutDashboard,
  Map,
  PlusCircle,
  CreditCard,
  Settings,
  Plane,
  LogOut,
  Compass,
} from "lucide-react";
import clsx from "clsx";
import { supabase } from "@/lib/supabase";
import type { User } from "@supabase/supabase-js";

const links = [
  { label: "Dashboard",    href: "/",         icon: LayoutDashboard },
  { label: "Explore",      href: "/explore",  icon: Compass },
  { label: "My Trips",     href: "/trips",    icon: Map },
  { label: "New Trip",     href: "/trips/new", icon: PlusCircle },
  { label: "Travel Cards", href: "/cards",    icon: CreditCard },
  { label: "Settings",     href: "/settings", icon: Settings },
];

const tabLinks = [
  { label: "Dashboard",    href: "/",         icon: LayoutDashboard },
  { label: "Explore",      href: "/explore",  icon: Compass },
  { label: "New Trip",     href: "/trips/new", icon: PlusCircle },
  { label: "My Trips",     href: "/trips",    icon: Map },
  { label: "Cards",        href: "/cards",    icon: CreditCard },
];

function getUserDisplay(user: User): { name: string; initial: string } {
  const meta = user.user_metadata ?? {};
  const name: string =
    meta.full_name || meta.name || (user.email ? user.email.split("@")[0] : "");
  const initial = (name || user.email || "?").charAt(0).toUpperCase();
  return { name: name || user.email || "", initial };
}

export function MobileNav() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => setUser(user));
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });
    return () => subscription.unsubscribe();
  }, []);

  async function handleSignOut() {
    setOpen(false);
    await supabase.auth.signOut();
    router.push("/auth/login");
  }

  function isActive(href: string) {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  }

  const display = user ? getUserDisplay(user) : null;

  return (
    <>
      {/* ── Glass top bar ───────────────────────────────────── */}
      <header className="lg:hidden sticky top-0 z-40 flex items-center justify-between px-4 py-3 glass border-b border-white/[.07]">
        <div className="flex items-center gap-2">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-brand-500 text-dark-50">
            <Plane className="w-4 h-4" />
          </div>
          <span className="text-sm font-bold text-cream-100">Travel Concierge</span>
        </div>
        <button
          onClick={() => setOpen(!open)}
          className="p-2 rounded-lg text-cream-400 hover:bg-white/[.06] transition"
          aria-label="Toggle menu"
        >
          {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </header>

      {/* ── Drawer overlay ──────────────────────────────────── */}
      {open && (
        <div
          className="lg:hidden fixed inset-0 z-30 bg-black/60 backdrop-blur-sm"
          onClick={() => setOpen(false)}
        />
      )}

      {/* ── Slide-out drawer ────────────────────────────────── */}
      <div
        className={clsx(
          "lg:hidden fixed inset-y-0 left-0 z-40 w-64 glass border-r border-white/[.07] flex flex-col",
          "transition-transform duration-300 ease-out",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-center gap-2 px-5 py-4 border-b border-white/[.06]">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-brand-500 text-dark-50">
            <Plane className="w-4 h-4" />
          </div>
          <span className="text-sm font-bold text-cream-100">Travel Concierge</span>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-0.5">
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

        {/* User identity + sign out at bottom of drawer */}
        <div className="px-4 py-4 border-t border-white/[.06] space-y-1">
          {display && (
            <div className="flex items-center gap-3 px-2 py-2">
              <div className="w-7 h-7 rounded-full bg-brand-500/20 text-brand-400 flex items-center justify-center text-xs font-semibold shrink-0">
                {display.initial}
              </div>
              <p className="text-sm font-medium text-cream-200 truncate">{display.name}</p>
            </div>
          )}
          <button
            onClick={handleSignOut}
            className="nav-item w-full text-cream-500 hover:text-rose-300"
            aria-label="Sign out"
          >
            <LogOut className="w-4 h-4 shrink-0" />
            Sign out
          </button>
        </div>
      </div>

      {/* ── Bottom tab bar (Apple-style) ─────────────────────── */}
      <nav className="lg:hidden fixed bottom-0 inset-x-0 z-40 glass border-t border-white/[.07] flex items-stretch pb-safe">
        {tabLinks.map(({ label, href, icon: Icon }) => {
          const active = isActive(href);
          const isNew = href === "/trips/new";
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex-1 flex flex-col items-center justify-center gap-0.5 py-2.5 min-w-0 transition-colors",
                active ? "text-brand-400" : "text-cream-500 hover:text-cream-300"
              )}
              aria-label={label}
            >
              <span
                className={clsx(
                  "flex items-center justify-center rounded-xl transition-all",
                  isNew
                    ? "w-10 h-10 bg-brand-500 text-dark-50 shadow-md shadow-brand-500/30 -mt-4"
                    : "w-7 h-7",
                  isNew && active && "bg-brand-600"
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
