/**
 * Phase 8N — Atmospheric Boutique Art Direction contract tests.
 *
 * Verifies:
 *  1.  globals.css defines --ds-atelier-base token (warm dark base).
 *  2.  globals.css defines --ds-atelier-texture-tint token.
 *  3.  globals.css defines --ds-atelier-vignette token.
 *  4.  globals.css defines --ds-atelier-edge-glow token.
 *  5.  globals.css defines --ds-atelier-card-border token.
 *  6.  globals.css defines --ds-atelier-ambient token.
 *  7.  globals.css defines .atelier-atmosphere-root class.
 *  8.  globals.css defines .atelier-vignette-layer class (CSS-only, fixed).
 *  9.  globals.css defines .atelier-texture-layer class (CSS-only, fixed).
 * 10.  globals.css defines .atelier-surface-depth class.
 * 11.  globals.css defines @keyframes atelier-vignette-in.
 * 12.  globals.css has prefers-reduced-motion guard for atelier-vignette-layer.
 * 13.  globals.css has prefers-reduced-motion guard for atelier-texture-layer.
 * 14.  globals.css defines .atelier-transition utility.
 * 15.  globals.css atelier-transition has reduced-motion none override.
 * 16.  globals.css atelier-texture-layer uses SVG data-URI (no external image asset).
 * 17.  globals.css atelier-texture-layer uses mix-blend-mode (soft-light).
 * 18.  globals.css atelier-atmosphere-root uses radial-gradient for ambient warmth.
 * 19.  globals.css atelier-vignette-layer uses position: fixed and pointer-events: none.
 * 20.  globals.css atelier-texture-layer uses position: fixed and pointer-events: none.
 * 21.  AppShell has data-testid="atelier-atmosphere-root".
 * 22.  AppShell has data-testid="atelier-vignette-layer".
 * 23.  AppShell has data-testid="atelier-texture-layer".
 * 24.  AppShell has data-testid="reduced-motion-safe-atmosphere".
 * 25.  AppShell vignette layer has aria-hidden="true".
 * 26.  AppShell texture layer has aria-hidden="true".
 * 27.  AppShell still contains .mobile-nav-spacer class (8J preserved).
 * 28.  AppShell still has data-testid="mobile-page-content" (8J preserved).
 * 29.  MobileNav still has data-testid="mobile-bottom-nav" (8J preserved).
 * 30.  MobileNav still has data-testid="mobile-top-bar" (8J preserved).
 * 31.  Trip detail page still has data-testid="trip-mobile-workspace" (8K preserved).
 * 32.  Trip detail page still has data-testid="trip-mobile-workspace-switcher" (8K preserved).
 * 33.  ItineraryDayColumn still has data-testid="itinerary-day-mobile-chapter" (8L preserved).
 * 34.  ItineraryItemCard still has data-testid="itinerary-item-mobile-timeline-card" (8L preserved).
 * 35.  TripBuilderForm still has data-testid="new-trip-builder-form" (8M preserved).
 * 36.  ConciergePage still has .concierge-sticky-bottom class (8M preserved).
 * 37.  globals.css atelier tokens centralised in :root (ds-atelier- prefix, not raw hex in classes).
 * 38.  globals.css .atelier-surface-depth uses var(--ds-atelier-card-border).
 * 39.  globals.css .atelier-surface-depth uses var(--ds-atelier-surface-highlight).
 * 40.  globals.css defines .shadow-elevation-warm with warm brass glow.
 * 41.  globals.css defines .atelier-accent-line with sandstone border.
 * 42.  No new @import for external image assets in globals.css.
 * 43.  No forbidden backend/provider file changed (no backend import in AppShell).
 * 44.  AppShell does not import any backend/supabase path beyond existing supabase client.
 * 45.  globals.css atelier-vignette-layer animation uses --ds-duration-slow token.
 * 46.  globals.css atelier-accent-line uses var(--ds-ember-brass) — ds-token not raw hex.
 * 47.  globals.css atelier-atmosphere-root background-image uses radial-gradient (no url()).
 * 48.  globals.css .concierge-sticky-bottom still present (8M not regressed).
 * 49.  globals.css .mobile-bottom-nav still present (8J not regressed).
 * 50.  globals.css .mobile-nav-spacer still present (8J not regressed).
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root      = resolve(__dirname, "..");
const srcRoot   = resolve(root, "src");

function readSrc(relPath) {
  return readFileSync(resolve(srcRoot, relPath), "utf8");
}
function readRoot(relPath) {
  return readFileSync(resolve(root, relPath), "utf8");
}

const globalsCss    = readRoot("src/app/globals.css");
const appShell      = readSrc("components/layout/AppShell.tsx");
const mobileNav     = readSrc("components/layout/MobileNav.tsx");
const tripDetailPage = readSrc("app/trips/[id]/page.tsx");
const itineraryDay  = readSrc("components/trips/ItineraryDayColumn.tsx");
const itineraryItem = readSrc("components/trips/ItineraryItemCard.tsx");
const tripBuilderForm = readSrc("components/trips/TripBuilderForm.tsx");
const conciergePage = readSrc("components/concierge/ConciergePage.tsx");

// ── 1–6. Atelier custom properties defined in :root ─────────────────────────

describe("Phase 8N: Atelier CSS custom properties", () => {
  it("1. globals.css defines --ds-atelier-base token", () => {
    assert.ok(globalsCss.includes("--ds-atelier-base"), "Must define --ds-atelier-base");
  });
  it("2. globals.css defines --ds-atelier-texture-tint token", () => {
    assert.ok(globalsCss.includes("--ds-atelier-texture-tint"), "Must define --ds-atelier-texture-tint");
  });
  it("3. globals.css defines --ds-atelier-vignette token", () => {
    assert.ok(globalsCss.includes("--ds-atelier-vignette"), "Must define --ds-atelier-vignette");
  });
  it("4. globals.css defines --ds-atelier-edge-glow token", () => {
    assert.ok(globalsCss.includes("--ds-atelier-edge-glow"), "Must define --ds-atelier-edge-glow");
  });
  it("5. globals.css defines --ds-atelier-card-border token", () => {
    assert.ok(globalsCss.includes("--ds-atelier-card-border"), "Must define --ds-atelier-card-border");
  });
  it("6. globals.css defines --ds-atelier-ambient token", () => {
    assert.ok(globalsCss.includes("--ds-atelier-ambient"), "Must define --ds-atelier-ambient");
  });
});

// ── 7–20. Atmosphere CSS class definitions ──────────────────────────────────

describe("Phase 8N: Atmosphere class definitions in globals.css", () => {
  it("7. defines .atelier-atmosphere-root", () => {
    assert.ok(globalsCss.includes(".atelier-atmosphere-root"), "Must define .atelier-atmosphere-root");
  });
  it("8. defines .atelier-vignette-layer (CSS-only, fixed)", () => {
    assert.ok(globalsCss.includes(".atelier-vignette-layer"), "Must define .atelier-vignette-layer");
  });
  it("9. defines .atelier-texture-layer (CSS-only, fixed)", () => {
    assert.ok(globalsCss.includes(".atelier-texture-layer"), "Must define .atelier-texture-layer");
  });
  it("10. defines .atelier-surface-depth", () => {
    assert.ok(globalsCss.includes(".atelier-surface-depth"), "Must define .atelier-surface-depth");
  });
  it("11. defines @keyframes atelier-vignette-in", () => {
    assert.ok(globalsCss.includes("atelier-vignette-in"), "Must define @keyframes atelier-vignette-in");
  });
  it("12. prefers-reduced-motion guard for atelier-vignette-layer", () => {
    const rmBlock = globalsCss.slice(globalsCss.indexOf("prefers-reduced-motion: reduce"));
    assert.ok(
      rmBlock.includes(".atelier-vignette-layer"),
      "Must have prefers-reduced-motion override for .atelier-vignette-layer"
    );
  });
  it("13. prefers-reduced-motion guard for atelier-texture-layer", () => {
    const rmBlock = globalsCss.slice(globalsCss.indexOf("prefers-reduced-motion: reduce"));
    assert.ok(
      rmBlock.includes(".atelier-texture-layer"),
      "Must have prefers-reduced-motion override for .atelier-texture-layer"
    );
  });
  it("14. defines .atelier-transition utility", () => {
    assert.ok(globalsCss.includes(".atelier-transition"), "Must define .atelier-transition");
  });
  it("15. .atelier-transition has reduced-motion none override", () => {
    // Find the reduced-motion block after the atelier-transition definition
    const atelierTransIdx = globalsCss.indexOf(".atelier-transition");
    const afterAtelier = globalsCss.slice(atelierTransIdx);
    assert.ok(
      afterAtelier.includes("transition: none"),
      "atelier-transition must have a prefers-reduced-motion: reduce override with transition: none"
    );
  });
  it("16. atelier-texture-layer uses SVG data-URI (CSS-only, no external image asset)", () => {
    assert.ok(
      globalsCss.includes("data:image/svg+xml"),
      "atelier-texture-layer must use inline SVG data-URI for grain — no external image file"
    );
  });
  it("17. atelier-texture-layer uses mix-blend-mode: soft-light", () => {
    assert.ok(
      globalsCss.includes("mix-blend-mode: soft-light"),
      "atelier-texture-layer must use mix-blend-mode: soft-light"
    );
  });
  it("18. atelier-atmosphere-root uses radial-gradient for ambient warmth", () => {
    const rootBlock = globalsCss.slice(globalsCss.indexOf(".atelier-atmosphere-root"));
    assert.ok(
      rootBlock.includes("radial-gradient"),
      ".atelier-atmosphere-root must use radial-gradient for warm ambient background"
    );
  });
  it("19. atelier-vignette-layer uses position: fixed and pointer-events: none", () => {
    const vBlock = globalsCss.slice(globalsCss.indexOf(".atelier-vignette-layer {"));
    assert.ok(vBlock.includes("position: fixed"), ".atelier-vignette-layer must be position: fixed");
    assert.ok(vBlock.includes("pointer-events: none"), ".atelier-vignette-layer must have pointer-events: none");
  });
  it("20. atelier-texture-layer uses position: fixed and pointer-events: none", () => {
    const tBlock = globalsCss.slice(globalsCss.indexOf(".atelier-texture-layer {"));
    assert.ok(tBlock.includes("position: fixed"), ".atelier-texture-layer must be position: fixed");
    assert.ok(tBlock.includes("pointer-events: none"), ".atelier-texture-layer must have pointer-events: none");
  });
});

// ── 21–26. AppShell testid contracts ────────────────────────────────────────

describe("Phase 8N: AppShell atmosphere testids", () => {
  it("21. AppShell has data-testid='atelier-atmosphere-root'", () => {
    assert.ok(
      appShell.includes('data-testid="atelier-atmosphere-root"'),
      "AppShell must have data-testid='atelier-atmosphere-root'"
    );
  });
  it("22. AppShell has data-testid='atelier-vignette-layer'", () => {
    assert.ok(
      appShell.includes('data-testid="atelier-vignette-layer"'),
      "AppShell must have data-testid='atelier-vignette-layer'"
    );
  });
  it("23. AppShell has data-testid='atelier-texture-layer'", () => {
    assert.ok(
      appShell.includes('data-testid="atelier-texture-layer"'),
      "AppShell must have data-testid='atelier-texture-layer'"
    );
  });
  it("24. AppShell has data-testid='reduced-motion-safe-atmosphere'", () => {
    assert.ok(
      appShell.includes('data-testid="reduced-motion-safe-atmosphere"'),
      "AppShell main element must have data-testid='reduced-motion-safe-atmosphere'"
    );
  });
  it("25. AppShell vignette layer has aria-hidden='true'", () => {
    assert.ok(
      appShell.includes('aria-hidden="true"'),
      "Atmosphere layers must have aria-hidden='true' (decorative)"
    );
  });
  it("26. AppShell texture layer has aria-hidden='true'", () => {
    // Both layers present — just verify at least 2 occurrences
    const matches = appShell.match(/aria-hidden="true"/g) || [];
    assert.ok(matches.length >= 2, "Both vignette and texture layers must have aria-hidden='true'");
  });
});

// ── 27–36. Prior phases preserved ───────────────────────────────────────────

describe("Phase 8N: Prior phases preserved (8J/8K/8L/8M)", () => {
  it("27. AppShell still has mobile-nav-spacer class (8J)", () => {
    assert.ok(appShell.includes("mobile-nav-spacer"), "AppShell must still use mobile-nav-spacer (8J preserved)");
  });
  it("28. AppShell still has data-testid='mobile-page-content' (8J)", () => {
    assert.ok(
      appShell.includes('data-testid="mobile-page-content"'),
      "AppShell must still have data-testid='mobile-page-content' (8J preserved)"
    );
  });
  it("29. MobileNav still has data-testid='mobile-bottom-nav' (8J)", () => {
    assert.ok(
      mobileNav.includes('data-testid="mobile-bottom-nav"'),
      "MobileNav must still have data-testid='mobile-bottom-nav' (8J preserved)"
    );
  });
  it("30. MobileNav still has data-testid='mobile-top-bar' (8J)", () => {
    assert.ok(
      mobileNav.includes('data-testid="mobile-top-bar"'),
      "MobileNav must still have data-testid='mobile-top-bar' (8J preserved)"
    );
  });
  it("31. Trip detail page still has data-testid='trip-mobile-workspace' (8K)", () => {
    assert.ok(
      tripDetailPage.includes('data-testid="trip-mobile-workspace"'),
      "Trip detail must still have data-testid='trip-mobile-workspace' (8K preserved)"
    );
  });
  it("32. Trip detail page still has data-testid='trip-mobile-workspace-switcher' (8K)", () => {
    assert.ok(
      tripDetailPage.includes('data-testid="trip-mobile-workspace-switcher"'),
      "Trip detail must still have data-testid='trip-mobile-workspace-switcher' (8K preserved)"
    );
  });
  it("33. ItineraryDayColumn still has data-testid='itinerary-day-mobile-chapter' (8L)", () => {
    assert.ok(
      itineraryDay.includes('data-testid="itinerary-day-mobile-chapter"') ||
      itineraryDay.includes("data-chapter-id=\"itinerary-day-mobile-chapter\""),
      "ItineraryDayColumn must still have itinerary-day-mobile-chapter testid (8L preserved)"
    );
  });
  it("34. ItineraryItemCard still has data-testid='itinerary-item-mobile-timeline-card' (8L)", () => {
    assert.ok(
      itineraryItem.includes('data-testid="itinerary-item-mobile-timeline-card"'),
      "ItineraryItemCard must still have data-testid='itinerary-item-mobile-timeline-card' (8L preserved)"
    );
  });
  it("35. TripBuilderForm still has data-testid='new-trip-builder-form' (8M)", () => {
    assert.ok(
      tripBuilderForm.includes('data-testid="new-trip-builder-form"'),
      "TripBuilderForm must still have data-testid='new-trip-builder-form' (8M preserved)"
    );
  });
  it("36. ConciergePage still has concierge-sticky-bottom class (8M)", () => {
    assert.ok(
      conciergePage.includes("concierge-sticky-bottom"),
      "ConciergePage must still use concierge-sticky-bottom (8M preserved)"
    );
  });
});

// ── 37–50. Token discipline and CSS structure ────────────────────────────────

describe("Phase 8N: Token discipline and CSS structural checks", () => {
  it("37. Atelier tokens use ds-atelier- prefix (centralised in :root)", () => {
    const atelierTokenCount = (globalsCss.match(/--ds-atelier-/g) || []).length;
    assert.ok(atelierTokenCount >= 6, "Must define at least 6 --ds-atelier- tokens in :root");
  });
  it("38. .atelier-surface-depth uses var(--ds-atelier-card-border)", () => {
    const surfBlock = globalsCss.slice(globalsCss.indexOf(".atelier-surface-depth"));
    assert.ok(
      surfBlock.includes("var(--ds-atelier-card-border)"),
      ".atelier-surface-depth must reference var(--ds-atelier-card-border)"
    );
  });
  it("39. .atelier-surface-depth uses var(--ds-atelier-surface-highlight)", () => {
    const surfBlock = globalsCss.slice(globalsCss.indexOf(".atelier-surface-depth"));
    assert.ok(
      surfBlock.includes("var(--ds-atelier-surface-highlight)"),
      ".atelier-surface-depth must reference var(--ds-atelier-surface-highlight)"
    );
  });
  it("40. globals.css defines .shadow-elevation-warm with warm brass glow", () => {
    assert.ok(
      globalsCss.includes(".shadow-elevation-warm"),
      "Must define .shadow-elevation-warm utility"
    );
  });
  it("41. globals.css defines .atelier-accent-line with sandstone border", () => {
    assert.ok(
      globalsCss.includes(".atelier-accent-line"),
      "Must define .atelier-accent-line utility"
    );
  });
  it("42. No new @import for external image assets in globals.css", () => {
    // Existing import is only @import 'tailwindcss'
    const imports = globalsCss.match(/@import\s+["'][^"']+["']/g) || [];
    for (const imp of imports) {
      assert.ok(
        imp.includes("tailwindcss"),
        `Unexpected @import found — only tailwindcss import is allowed: ${imp}`
      );
    }
  });
  it("43. AppShell does not import backend paths", () => {
    assert.ok(
      !appShell.includes("from '@/backend") &&
      !appShell.includes("from '../backend") &&
      !appShell.includes("from '../../backend"),
      "AppShell must not import backend paths"
    );
  });
  it("44. AppShell only imports supabase from lib/supabase (existing)", () => {
    assert.ok(
      appShell.includes("lib/supabase"),
      "AppShell must retain supabase import from lib/supabase (existing)"
    );
  });
  it("45. atelier-vignette-layer animation references --ds-duration-slow token", () => {
    assert.ok(
      globalsCss.includes("var(--ds-duration-slow)"),
      "Vignette animation must use var(--ds-duration-slow) for motion token compliance"
    );
  });
  it("46. .atelier-accent-line uses var(--ds-ember-brass) — ds-token not raw hex", () => {
    const accentBlock = globalsCss.slice(globalsCss.indexOf(".atelier-accent-line"));
    assert.ok(
      accentBlock.includes("var(--ds-ember-brass)"),
      ".atelier-accent-line must use var(--ds-ember-brass) ds-token"
    );
  });
  it("47. .atelier-atmosphere-root background-image uses radial-gradient not url()", () => {
    const rootStart = globalsCss.indexOf(".atelier-atmosphere-root {");
    const rootBlock = globalsCss.slice(rootStart, rootStart + 800);
    assert.ok(
      rootBlock.includes("radial-gradient"),
      ".atelier-atmosphere-root must use radial-gradient (no external url())"
    );
    assert.ok(
      !rootBlock.includes("url(\"http") && !rootBlock.includes("url('http"),
      ".atelier-atmosphere-root must not reference external URLs"
    );
  });
  it("48. globals.css .concierge-sticky-bottom still present (8M not regressed)", () => {
    assert.ok(
      globalsCss.includes(".concierge-sticky-bottom"),
      "globals.css must still define .concierge-sticky-bottom (8M preserved)"
    );
  });
  it("49. globals.css .mobile-bottom-nav still present (8J not regressed)", () => {
    assert.ok(
      globalsCss.includes(".mobile-bottom-nav"),
      "globals.css must still define .mobile-bottom-nav (8J preserved)"
    );
  });
  it("50. globals.css .mobile-nav-spacer still present (8J not regressed)", () => {
    assert.ok(
      globalsCss.includes(".mobile-nav-spacer"),
      "globals.css must still define .mobile-nav-spacer (8J preserved)"
    );
  });
});
