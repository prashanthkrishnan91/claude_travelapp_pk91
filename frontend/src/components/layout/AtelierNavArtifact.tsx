"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
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
  X,
} from "lucide-react";
import clsx from "clsx";
import { supabase } from "@/lib/supabase";
import type { User } from "@supabase/supabase-js";

// ════════════════════════════════════════════════════════════════
// AtelierNavArtifact — Silent floating navigation
//
// Replaces the SaaS sidebar on the Home / Atelier surface with a
// single tactile artifact in the corner: a small brass-edged paper
// dock that whispers the wordmark and opens into a private travel
// navigation drawer on click. Navigation, account, and sign-out
// stay reachable; the chrome stays out of the room.
// ════════════════════════════════════════════════════════════════

interface NavLink {
  label: string;
  href: string;
  icon: React.ElementType;
}

const primaryLinks: NavLink[] = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Explore", href: "/explore", icon: Compass },
  { label: "Concierge", href: "/concierge", icon: Sparkles },
  { label: "Saved", href: "/saved", icon: Bookmark },
  { label: "My Trips", href: "/trips", icon: Map },
  { label: "New Trip", href: "/trips/new", icon: PlusCircle },
];

const secondaryLinks: NavLink[] = [
  { label: "Travel Cards", href: "/cards", icon: CreditCard },
  { label: "Settings", href: "/settings", icon: Settings },
];

function getUserDisplay(user: User): { name: string; sub: string; initial: string } {
  const meta = user.user_metadata ?? {};
  const name: string =
    meta.full_name || meta.name || (user.email ? user.email.split("@")[0] : "");
  const sub: string = user.email ?? "";
  const initial = (name || sub).charAt(0).toUpperCase() || "?";
  return { name: name || sub, sub, initial };
}

export function AtelierNavArtifact() {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => setUser(user));
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });
    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  async function handleSignOut() {
    await supabase.auth.signOut();
    router.push("/auth/login");
  }

  function isActive(href: string) {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  }

  const display = user ? getUserDisplay(user) : null;

  return (
    <div className="atelier-nav-artifact-root hidden lg:block" data-testid="atelier-nav-artifact">
      {/* Floating dock — the only visible chrome on Home until opened. */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="atelier-nav-dock"
        aria-label={open ? "Close navigation" : "Open navigation"}
        aria-expanded={open}
        data-testid="atelier-nav-dock"
      >
        <span className="atelier-nav-dock-mark" aria-hidden="true">
          <Plane className="w-4 h-4" />
        </span>
        <span className="atelier-nav-dock-wordmark">The Atelier</span>
        <span className="atelier-nav-dock-rule" aria-hidden="true" />
      </button>

      {/* Opening drawer — paper-glass panel slides into view. */}
      {open && (
        <>
          <button
            type="button"
            className="atelier-nav-scrim"
            aria-label="Close navigation"
            onClick={() => setOpen(false)}
          />
          <nav
            aria-label="Atelier navigation"
            className="atelier-nav-drawer"
            data-testid="atelier-nav-drawer"
          >
            <header className="atelier-nav-drawer-head">
              <div className="atelier-nav-drawer-brand">
                <span className="atelier-nav-drawer-mark" aria-hidden="true">
                  <Plane className="w-4 h-4" />
                </span>
                <div className="leading-tight">
                  <p className="text-sm font-semibold folio-display-serif text-ds-folio-ink">
                    Travel Concierge
                  </p>
                  <p className="text-[11px] text-ds-folio-ink-mist tracking-[0.18em] uppercase">
                    The Atelier
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="atelier-nav-drawer-close"
                aria-label="Close navigation"
              >
                <X className="w-4 h-4" />
              </button>
            </header>

            <div className="atelier-nav-drawer-body">
              <p className="folio-section-label mb-2 px-3">Planning</p>
              <div className="space-y-0.5">
                {primaryLinks.map(({ label, href, icon: Icon }) => (
                  <Link
                    key={href}
                    href={href}
                    onClick={() => setOpen(false)}
                    className={clsx("folio-nav-item", isActive(href) && "folio-nav-item-active")}
                  >
                    <Icon className="w-4 h-4 shrink-0" />
                    {label}
                  </Link>
                ))}
              </div>

              <p className="folio-section-label mt-4 mb-2 px-3">Account</p>
              <div className="space-y-0.5">
                {secondaryLinks.map(({ label, href, icon: Icon }) => (
                  <Link
                    key={href}
                    href={href}
                    onClick={() => setOpen(false)}
                    className={clsx("folio-nav-item", isActive(href) && "folio-nav-item-active")}
                  >
                    <Icon className="w-4 h-4 shrink-0" />
                    {label}
                  </Link>
                ))}
              </div>
            </div>

            <footer className="atelier-nav-drawer-foot">
              <div className="flex items-center gap-3 rounded-lg px-2 py-2">
                <div className="w-8 h-8 rounded-full bg-ds-marine-ink text-ds-paper flex items-center justify-center text-sm font-semibold shrink-0">
                  {display?.initial ?? "?"}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-ds-folio-ink truncate">
                    {display?.name ?? "…"}
                  </p>
                  {display?.sub && display.sub !== display.name && (
                    <p className="text-xs text-ds-folio-ink-mist truncate">{display.sub}</p>
                  )}
                </div>
              </div>
              <button
                onClick={handleSignOut}
                className="folio-nav-item w-full text-ds-folio-ink-mist hover:text-ds-warning"
                aria-label="Sign out"
              >
                <LogOut className="w-4 h-4 shrink-0" />
                Sign out
              </button>
            </footer>
          </nav>
        </>
      )}
    </div>
  );
}
