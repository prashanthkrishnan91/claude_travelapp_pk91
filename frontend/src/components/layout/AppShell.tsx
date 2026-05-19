"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Sidebar } from "./Sidebar";
import { MobileNav } from "./MobileNav";
import { supabase } from "@/lib/supabase";

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const isAuthPage = pathname.startsWith("/auth");
  const [checking, setChecking] = useState(!isAuthPage);

  useEffect(() => {
    if (isAuthPage) return;

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) {
        router.push("/auth/login");
      } else {
        setChecking(false);
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        if (!session && !pathname.startsWith("/auth")) {
          router.push("/auth/login");
        }
      }
    );

    return () => subscription.unsubscribe();
  }, [isAuthPage, pathname, router]);

  // Auth pages: render without sidebar
  if (isAuthPage) {
    return <>{children}</>;
  }

  // Protected pages: show loading until session confirmed
  if (checking) {
    return (
      <div className="flex h-full min-h-screen items-center justify-center bg-ds-midnight">
        <p className="text-ds-text-tertiary text-sm">Loading…</p>
      </div>
    );
  }

  // Home page renders edge-to-edge so the destination scenery can extend the
  // full width of the main area. Every other route keeps the centered, padded
  // page shell. The home page is then responsible for its own internal gutters.
  const isHomePage = pathname === "/";

  return (
    <>
      {/* Phase 8N: fixed atmospheric layers — vignette + CSS grain texture */}
      <div className="atelier-vignette-layer" data-testid="atelier-vignette-layer" aria-hidden="true" />
      <div className="atelier-texture-layer" data-testid="atelier-texture-layer" aria-hidden="true" />
      <MobileNav />
      <div
        className="atelier-atmosphere-root flex h-full min-h-screen"
        data-testid="atelier-atmosphere-root"
      >
        <Sidebar />
        <main className="flex-1 overflow-y-auto" data-testid="reduced-motion-safe-atmosphere">
          {isHomePage ? (
            <div
              className="mobile-nav-spacer atelier-transition home-edge-bleed"
              data-testid="mobile-page-content"
              data-home-edge-bleed="true"
            >
              {children}
            </div>
          ) : (
            <div
              className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-5 sm:pt-8 mobile-nav-spacer atelier-transition"
              data-testid="mobile-page-content"
            >
              {children}
            </div>
          )}
        </main>
      </div>
    </>
  );
}
