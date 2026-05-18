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
  Bookmark,
  Sparkles,
} from "lucide-react";
import clsx from "clsx";
import { supabase } from "@/lib/supabase";
import type { User } from "@supabase/supabase-js";

// Full drawer navigation (all destinations)
const drawerLinks = [
  { label: "Home",         href: "/",            icon: LayoutDashboard },
  { label: "Discover",     href: "/explore",     icon: Compass },
  { label: "Concierge",    href: "/concierge",   icon: Sparkles },
  { label: "Saved",        href: "/saved",       icon: Bookmark },
  { label: "My Trips",     href: "/trips",       icon: Map },
  { label: "New Trip",     href: "/trips/new",   icon: PlusCircle },
  { label: "Travel Cards", href: "/cards",       icon: CreditCard },
  { label: "Settings",     href: "/settings",    icon: Settings },
];

// Bottom 4-tab quiet boutique nav — no giant center CTA
const tabLinks = [
  { label: "Home",     href: "/",        icon: LayoutDashboard, testid: "mobile-nav-tab-home" },
  { label: "Discover", href: "/explore", icon: Compass,          testid: "mobile-nav-tab-discover" },
  { label: "Saved",    href: "/saved",   icon: Bookmark,         testid: "mobile-nav-tab-saved" },
  { label: "My Trips", href: "/trips",   icon: Map,              testid: "mobile-nav-tab-my-trips" },
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
      {/* ── Top bar — boutique atelier header ─────────────────── */}
      <header
        className="lg:hidden sticky top-0 z-40 flex items-center justify-between px-4 py-2.5 mobile-top-bar"
        data-testid="mobile-top-bar"
      >
        <div className="flex items-center gap-2">
          <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-ds-linen text-ds-marine-ink">
            <Plane className="w-3.5 h-3.5" aria-hidden="true" />
          </div>
          <span className="text-sm font-semibold text-ds-folio-ink tracking-tight">
            Travel Concierge
          </span>
        </div>
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="p-2 rounded-lg text-ds-folio-ink-soft hover:bg-ds-linen transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-marine-ink focus-visible:outline-offset-2"
          aria-label="Toggle menu"
          aria-expanded={open}
        >
          {open ? <X className="w-5 h-5" aria-hidden="true" /> : <Menu className="w-5 h-5" aria-hidden="true" />}
        </button>
      </header>

      {/* ── Drawer overlay ──────────────────────────────────────── */}
      {open && (
        <div
          className="lg:hidden fixed inset-0 z-30 bg-black/60 backdrop-blur-sm"
          onClick={() => setOpen(false)}
        />
      )}

      {/* ── Slide-out drawer ────────────────────────────────────── */}
      <div
        className={clsx(
          "lg:hidden fixed inset-y-0 left-0 z-40 w-64 bg-ds-onyx border-r border-ds-pen-stroke flex flex-col",
          "transition-transform duration-200 ease-out",
          open ? "translate-x-0" : "-translate-x-full"
        )}
        data-testid="mobile-drawer"
      >
        <div className="flex items-center gap-2 px-5 py-4 border-b border-ds-pen-stroke">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-ds-carbon text-ds-accent">
            <Plane className="w-4 h-4" aria-hidden="true" />
          </div>
          <span className="text-sm font-semibold text-ds-text">Travel Concierge</span>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {drawerLinks.map(({ label, href, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              onClick={() => setOpen(false)}
              className={clsx("nav-item", isActive(href) && "nav-item-active")}
            >
              <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />
              {label}
            </Link>
          ))}
        </nav>

        {/* User identity + sign-out at bottom of drawer */}
        <div className="px-4 py-4 border-t border-ds-pen-stroke space-y-1">
          {display && (
            <div className="flex items-center gap-3 px-2 py-2">
              <div className="w-7 h-7 rounded-full bg-ds-carbon text-ds-accent flex items-center justify-center text-xs font-semibold shrink-0">
                {display.initial}
              </div>
              <p className="text-sm font-medium text-ds-text truncate">{display.name}</p>
            </div>
          )}
          <button
            type="button"
            onClick={handleSignOut}
            className="nav-item w-full text-ds-text-tertiary hover:text-ds-warning"
            aria-label="Sign out"
          >
            <LogOut className="w-4 h-4 shrink-0" aria-hidden="true" />
            Sign out
          </button>
        </div>
      </div>

      {/* ── Bottom tab bar — quiet boutique 4-tab nav ─────────── */}
      <nav
        className="lg:hidden fixed bottom-0 inset-x-0 z-40 flex items-stretch mobile-bottom-nav"
        aria-label="Main navigation"
        data-testid="mobile-bottom-nav"
      >
        {tabLinks.map(({ label, href, icon: Icon, testid }) => {
          const active = isActive(href);
          return (
            <Link
              key={href}
              href={href}
              className="mobile-tab-item"
              aria-label={label}
              aria-current={active ? "page" : undefined}
              data-testid={testid}
            >
              {active && (
                <span className="mobile-tab-active-dot" aria-hidden="true" />
              )}
              <span className={clsx("mobile-tab-icon", active && "mobile-tab-icon-active")}>
                <Icon className="w-[1.1rem] h-[1.1rem]" aria-hidden="true" />
              </span>
              <span className={clsx("mobile-tab-label", active && "mobile-tab-label-active")}>
                {label}
              </span>
            </Link>
          );
        })}
      </nav>
    </>
  );
}
