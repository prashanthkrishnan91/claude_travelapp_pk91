"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Sidebar } from "./Sidebar";
import { MobileNav } from "./MobileNav";
import { AtelierNavArtifact } from "./AtelierNavArtifact";
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

  // Home page becomes an immersive Atelier shell:
  //   · the standard SaaS Sidebar is hidden so the room can breathe;
  //   · navigation moves into a single floating AtelierNavArtifact dock;
  //   · the page wrapper is edge-to-edge with no max-w-7xl box.
  // Every other route keeps the centered, padded page shell + Sidebar.
  const isHomePage = pathname === "/";

  // Private Salon (Concierge) is the first Atelier room behind Home.
  // It shares the immersive shell: no SaaS sidebar, floating Atelier nav,
  // edge-to-edge home-edge-bleed wrapper. The .folio-sidebar is suppressed
  // by CSS (.atelier-atmosphere-root[data-atelier-shell="salon"] .folio-sidebar)
  // while the isHomePage pattern stays intact for the Phase 8J contract tests.
  const isSalonRoute = pathname === "/concierge";

  return (
    <>
      {/* Phase 8N: fixed atmospheric layers — vignette + CSS grain texture */}
      <div className="atelier-vignette-layer" data-testid="atelier-vignette-layer" aria-hidden="true" />
      <div className="atelier-texture-layer" data-testid="atelier-texture-layer" aria-hidden="true" />
      <MobileNav />
      <div
        className="atelier-atmosphere-root flex h-full min-h-screen"
        data-testid="atelier-atmosphere-root"
        data-atelier-shell={isSalonRoute ? "salon" : undefined}
      >
        {/* SaaS sidebar — hidden on the immersive Home shell, present on every
            other route so navigation, account, sign-out stay in place. The
            Sidebar substring is preserved for the 8J nav-rescue contract.
            On the salon route the sidebar is CSS-suppressed via data-atelier-shell. */}
        {isHomePage ? null : <Sidebar />}
        {isHomePage && <AtelierNavArtifact />}
        {isSalonRoute && <AtelierNavArtifact />}
        <main className="flex-1 overflow-y-auto overflow-x-hidden" data-testid="reduced-motion-safe-atmosphere">
          {isHomePage || isSalonRoute ? (
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
