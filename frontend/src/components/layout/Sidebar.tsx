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
  LogOut,
  Compass,
  Bookmark,
  Sparkles,
} from "lucide-react";
import clsx from "clsx";
import { supabase } from "@/lib/supabase";
import { BrandMark } from "./BrandMark";
import type { User } from "@supabase/supabase-js";

interface NavLink {
  label: string;
  href: string;
  icon: React.ElementType;
}

const primaryLinks: NavLink[] = [
  { label: "Home", href: "/", icon: LayoutDashboard },
  { label: "Discover", href: "/explore", icon: Compass },
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

export function Sidebar() {
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
    await supabase.auth.signOut();
    router.push("/auth/login");
  }

  function isActive(href: string) {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  }

  const display = user ? getUserDisplay(user) : null;

  return (
    <aside className="hidden lg:flex lg:flex-col w-64 folio-sidebar min-h-screen">
      {/* Brand */}
      <div className="flex items-center gap-2.5 px-5 py-5 border-b border-ds-hairline">
        <BrandMark />
        <div>
          <p className="text-sm font-semibold folio-display-serif text-ds-folio-ink leading-tight">Travel Concierge</p>
          <p className="text-xs text-ds-folio-ink-mist">Trip Planner</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        <p className="folio-section-label px-3 mb-2">Planning</p>
        {primaryLinks.map(({ label, href, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={clsx("folio-nav-item", isActive(href) && "folio-nav-item-active")}
          >
            <Icon className="w-4 h-4 shrink-0" />
            {label}
          </Link>
        ))}

        <div className="pt-4">
          <p className="folio-section-label px-3 mb-2">Account</p>
          {secondaryLinks.map(({ label, href, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={clsx("folio-nav-item", isActive(href) && "folio-nav-item-active")}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </Link>
          ))}
        </div>
      </nav>

      {/* Footer / User */}
      <div className="px-4 py-4 border-t border-ds-hairline space-y-1">
        <div className="flex items-center gap-3 rounded-lg px-2 py-2">
          <div className="w-8 h-8 rounded-full bg-ds-marine-ink text-ds-paper flex items-center justify-center text-sm font-semibold shrink-0">
            {display?.initial ?? "?"}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-ds-folio-ink truncate">{display?.name ?? "…"}</p>
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
      </div>
    </aside>
  );
}
