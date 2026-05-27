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

  // Explore (Observatory) is the sibling outside-trip Atelier room to the
  // Salon. It shares the same immersive shell: SaaS sidebar CSS-suppressed
  // via data-atelier-shell="explore", floating AtelierNavArtifact nav, and the
  // edge-to-edge home-edge-bleed wrapper — so /explore reads as a full mood
  // room, not a centered card on the legacy padded shell. The isHomePage
  // ternary and the max-w-7xl branch are left intact for the 8J/atrium tests.
  const isExploreRoute = pathname === "/explore";

  // Saved (Private Folio) is the third outside-trip Atelier room. Unlike the
  // dark Salon/Observatory it is the PAPER world (light folio on a warm desk),
  // but it shares the immersive shell: SaaS sidebar CSS-suppressed via
  // data-atelier-shell="saved", floating AtelierNavArtifact nav, and the
  // edge-to-edge home-edge-bleed wrapper. The isHomePage ternary + max-w-7xl
  // branch stay intact for the 8J/atrium contracts.
  const isSavedRoute = pathname === "/saved";

  // My Journeys ("The Reading Room") is the fourth outside-trip Atelier room and,
  // like Saved, a PAPER world. It adopts the same immersive shell as the other
  // strong pages: SaaS sidebar CSS-suppressed via data-atelier-shell="trips",
  // floating AtelierNavArtifact nav, and the edge-to-edge home-edge-bleed wrapper —
  // so /trips reads as a wide, staged folio library, not a narrow centered card on
  // the legacy padded shell. The isHomePage ternary + max-w-7xl branch stay intact
  // for the 8J/atrium contracts. (Trip detail /trips/[id] is NOT immersive.)
  const isMyTripsRoute = pathname === "/trips";

  const isImmersiveRoom = isHomePage || isSalonRoute || isExploreRoute || isSavedRoute || isMyTripsRoute;

  return (
    <>
      {/* Phase 8N: fixed atmospheric layers — vignette + CSS grain texture */}
      <div className="atelier-vignette-layer" data-testid="atelier-vignette-layer" aria-hidden="true" />
      <div className="atelier-texture-layer" data-testid="atelier-texture-layer" aria-hidden="true" />
      <MobileNav />
      <div
        className="atelier-atmosphere-root flex h-full min-h-screen"
        data-testid="atelier-atmosphere-root"
        data-atelier-shell={isSalonRoute ? "salon" : isExploreRoute ? "explore" : isSavedRoute ? "saved" : isMyTripsRoute ? "trips" : undefined}
      >
        {/* SaaS sidebar — hidden on the immersive Home shell, present on every
            other route so navigation, account, sign-out stay in place. The
            Sidebar substring is preserved for the 8J nav-rescue contract.
            On the salon + explore routes the sidebar is CSS-suppressed via
            data-atelier-shell. */}
        {isHomePage ? null : <Sidebar />}
        {isHomePage && <AtelierNavArtifact />}
        {isSalonRoute && <AtelierNavArtifact />}
        {isExploreRoute && <AtelierNavArtifact />}
        {isSavedRoute && <AtelierNavArtifact />}
        {isMyTripsRoute && <AtelierNavArtifact />}
        <main className="flex-1 overflow-y-auto overflow-x-hidden" data-testid="reduced-motion-safe-atmosphere">
          {isImmersiveRoom ? (
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
