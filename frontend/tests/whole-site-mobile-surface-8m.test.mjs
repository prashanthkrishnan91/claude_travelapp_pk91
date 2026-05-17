/**
 * Phase 8M — Whole-Site Mobile Surface Pass contract tests.
 *
 * Verifies:
 *  1.  TripBuilderForm has data-testid="new-trip-builder-form" on the form element.
 *  2.  TripBuilderForm has data-testid="new-trip-loading-state" on loading view.
 *  3.  TripBuilderForm has data-testid="new-trip-form-container" on outer wrapper.
 *  4.  TripBuilderForm uses w-full on outer containers (mobile-safe width).
 *  5.  TripBuilderForm date row uses sm:grid-cols-2 (responsive, not bare grid-cols-2).
 *  6.  TripBuilderForm loading state: no legacy sky/slate/emerald/amber/red color classes.
 *  7.  TripBuilderForm form: no legacy sky/slate/amber/red color classes.
 *  8.  TripBuilderForm loading state uses ds-token color classes.
 *  9.  TripBuilderForm loading card uses bg-ds-onyx surface (not legacy card class alone).
 * 10.  TripBuilderForm provider-unavailable block uses border-ds-caution pattern.
 * 11.  TripBuilderForm error block uses border-ds-warning pattern.
 * 12.  TripBuilderForm footer note uses text-ds-text-tertiary (not text-slate-*).
 * 13.  New Trip page wrapper has data-testid="new-trip-page".
 * 14.  My Trips page header has data-testid="my-trips-page-header".
 * 15.  My Trips title div has min-w-0 flex-1 for safe narrow-screen layout.
 * 16.  ConciergePage sticky composer uses concierge-sticky-bottom class (not bare bottom-0).
 * 17.  globals.css defines .concierge-sticky-bottom for mobile bottom offset.
 * 18.  globals.css .concierge-sticky-bottom has lg override restoring bottom: 0.
 * 19.  Home surface: atelier-home testid in DashboardClient.
 * 20.  Home surface: concierge-entry testid present.
 * 21.  Home surface: home-new-trip-action testid present.
 * 22.  Home surface: atelier-planning-strip testid present.
 * 23.  Home surface: empty state flex-col sm:flex-row for CTA stack.
 * 24.  My Trips surface: trips-new-trip-action testid present.
 * 25.  My Trips surface: continue-planning-hero testid present.
 * 26.  My Trips surface: journey-card testid present.
 * 27.  My Trips surface: planning-tools-strip testid present.
 * 28.  My Trips: action footer uses flex flex-wrap gap-2 (no rigid row).
 * 29.  Explore surface: explore-lounge-header testid present.
 * 30.  Explore surface: explore-vertical-grid testid present.
 * 31.  Explore surface: vertical-card-flights testid present.
 * 32.  Explore surface: vertical-card-hotels testid present.
 * 33.  Explore surface: explore-instrument-header testid present.
 * 34.  Explore: vertical grid uses sm:grid-cols-2 (responsive).
 * 35.  Saved surface: saved-scrapbook-header testid present.
 * 36.  Saved surface: saved-item-card testid present.
 * 37.  Saved surface: saved-planning-bridge testid present.
 * 38.  Saved: action buttons have 44px touch target (min-w-[44px] min-h-[44px]).
 * 39.  Concierge: concierge-page testid present.
 * 40.  Concierge: concierge-instrument-header testid present.
 * 41.  Concierge: concierge-results-canvas testid present.
 * 42.  Concierge: concierge-instrument-composer testid present.
 * 43.  Concierge: no bare bottom-0 z-10 on sticky composer (replaced with class).
 * 44.  Phase 8J preserved: mobile-bottom-nav testid in MobileNav.
 * 45.  Phase 8J preserved: mobile-nav-spacer in AppShell.
 * 46.  Phase 8J preserved: mobile-top-bar testid in MobileNav.
 * 47.  Phase 8K preserved: trip-mobile-workspace testid in trips/[id]/page.
 * 48.  Phase 8K preserved: trip-mobile-workspace-switcher testid.
 * 49.  Phase 8L preserved: itinerary-day-mobile-chapter in ItineraryDayColumn.
 * 50.  Phase 8L preserved: itinerary-item-mobile-timeline-card in ItineraryItemCard.
 * 51.  No backend/provider/Supabase files imported in TripBuilderForm.
 * 52.  No backend/provider/Supabase files imported in trips/new page.
 * 53.  TripBuilderForm primary submit button has w-full for mobile.
 * 54.  TripBuilderForm date inputs use responsive grid (not bare grid-cols-2).
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root      = resolve(__dirname, "..");
const srcRoot   = resolve(root, "src");

function readSrc(relPath) {
  return readFileSync(resolve(srcRoot, relPath), "utf8");
}
function srcExists(relPath) {
  return existsSync(resolve(srcRoot, relPath));
}
function readRoot(relPath) {
  return readFileSync(resolve(root, relPath), "utf8");
}

const tripBuilderForm = readSrc("components/trips/TripBuilderForm.tsx");
const newTripPage     = readSrc("app/trips/new/page.tsx");
const tripsPage       = readSrc("app/trips/page.tsx");
const conciergePage   = readSrc("components/concierge/ConciergePage.tsx");
const dashboard       = readSrc("components/dashboard/DashboardClient.tsx");
const exploreShell    = readSrc("components/explore/ExploreShell.tsx");
const savedShell      = readSrc("components/saved/SavedShell.tsx");
const mobileNav       = readSrc("components/layout/MobileNav.tsx");
const appShell        = readSrc("components/layout/AppShell.tsx");
const itineraryDay    = readSrc("components/trips/ItineraryDayColumn.tsx");
const itineraryItem   = readSrc("components/trips/ItineraryItemCard.tsx");
const tripDetailPage  = readSrc("app/trips/[id]/page.tsx");
const globalsCss      = readRoot("src/app/globals.css");

// ── 1–12. TripBuilderForm ds-token migration ─────────────────────────────────

describe("Phase 8M: TripBuilderForm testids and mobile surface", () => {
  it("1. form element has data-testid new-trip-builder-form", () => {
    assert.ok(
      tripBuilderForm.includes('data-testid="new-trip-builder-form"'),
      "TripBuilderForm form must have data-testid='new-trip-builder-form'"
    );
  });

  it("2. loading view has data-testid new-trip-loading-state", () => {
    assert.ok(
      tripBuilderForm.includes('data-testid="new-trip-loading-state"'),
      "TripBuilderForm loading view must have data-testid='new-trip-loading-state'"
    );
  });

  it("3. outer wrapper has data-testid new-trip-form-container", () => {
    assert.ok(
      tripBuilderForm.includes('data-testid="new-trip-form-container"'),
      "TripBuilderForm outer wrapper must have data-testid='new-trip-form-container'"
    );
  });

  it("4. outer containers use w-full for mobile-safe width", () => {
    assert.ok(
      tripBuilderForm.includes("w-full max-w-lg") &&
      tripBuilderForm.includes("w-full max-w-md"),
      "TripBuilderForm containers must use w-full max-w-* for full-width mobile behavior"
    );
  });

  it("5. date row uses sm:grid-cols-2 responsive (not bare grid-cols-2)", () => {
    assert.ok(
      tripBuilderForm.includes("grid-cols-1 sm:grid-cols-2"),
      "TripBuilderForm date row must use grid-cols-1 sm:grid-cols-2"
    );
    assert.ok(
      !tripBuilderForm.includes('"grid grid-cols-2"'),
      "TripBuilderForm must not use bare grid-cols-2 without mobile-first breakpoint"
    );
  });

  it("6. loading state: no legacy sky/slate/emerald raw classes", () => {
    const legacyPatterns = [
      "bg-sky-50", "text-sky-500", "text-sky-600",
      "text-slate-900", "text-slate-500", "text-slate-400", "text-slate-300",
      "text-emerald-500",
    ];
    for (const pat of legacyPatterns) {
      assert.ok(
        !tripBuilderForm.includes(pat),
        `TripBuilderForm must not use legacy color class: ${pat}`
      );
    }
  });

  it("7. form: no legacy amber/red raw classes", () => {
    const legacyPatterns = [
      "bg-amber-50", "border-amber-200", "text-amber-800", "text-amber-900",
      "bg-red-50", "border-red-200", "text-red-700",
    ];
    for (const pat of legacyPatterns) {
      assert.ok(
        !tripBuilderForm.includes(pat),
        `TripBuilderForm must not use legacy color class: ${pat}`
      );
    }
  });

  it("8. loading state uses ds-token color classes", () => {
    assert.ok(
      tripBuilderForm.includes("text-ds-accent animate-pulse"),
      "loading state Sparkles icon must use text-ds-accent animate-pulse"
    );
    assert.ok(
      tripBuilderForm.includes("text-ds-trust"),
      "done step icon must use text-ds-trust"
    );
    assert.ok(
      tripBuilderForm.includes("text-ds-text-tertiary"),
      "loading state text must use text-ds-text-tertiary"
    );
  });

  it("9. loading card uses bg-ds-onyx surface", () => {
    assert.ok(
      tripBuilderForm.includes("bg-ds-onyx"),
      "TripBuilderForm loading card must use bg-ds-onyx surface"
    );
  });

  it("10. provider-unavailable block uses ds-caution pattern", () => {
    assert.ok(
      tripBuilderForm.includes("border-ds-caution"),
      "provider-unavailable alert must use border-ds-caution"
    );
    assert.ok(
      tripBuilderForm.includes("text-ds-caution"),
      "provider-unavailable title must use text-ds-caution"
    );
  });

  it("11. error block uses ds-warning pattern", () => {
    assert.ok(
      tripBuilderForm.includes("border-ds-warning"),
      "error alert must use border-ds-warning"
    );
    assert.ok(
      tripBuilderForm.includes("text-ds-warning"),
      "error alert text must use text-ds-warning"
    );
  });

  it("12. footer note uses text-ds-text-tertiary", () => {
    assert.ok(
      tripBuilderForm.includes("text-ds-text-tertiary text-center"),
      "footer note must use text-ds-text-tertiary text-center"
    );
  });

  it("53. primary submit button uses w-full", () => {
    assert.ok(
      tripBuilderForm.includes('className="btn-primary w-full"'),
      "TripBuilderForm submit button must have w-full for mobile"
    );
  });

  it("54. date inputs use responsive grid (not bare grid-cols-2)", () => {
    assert.ok(
      tripBuilderForm.includes("sm:grid-cols-2"),
      "TripBuilderForm date grid must use sm:grid-cols-2"
    );
  });
});

// ── 13. New Trip page wrapper ─────────────────────────────────────────────────

describe("Phase 8M: New Trip page testid", () => {
  it("13. new trip page wrapper has data-testid new-trip-page", () => {
    assert.ok(
      newTripPage.includes('data-testid="new-trip-page"'),
      "trips/new/page.tsx must have data-testid='new-trip-page' wrapper"
    );
  });
});

// ── 14–15. My Trips page header ────────────────────────────────────────────────

describe("Phase 8M: My Trips page mobile header", () => {
  it("14. page header has data-testid my-trips-page-header", () => {
    assert.ok(
      tripsPage.includes('data-testid="my-trips-page-header"'),
      "trips/page.tsx header must have data-testid='my-trips-page-header'"
    );
  });

  it("15. title div has min-w-0 flex-1 for safe narrow-screen layout", () => {
    assert.ok(
      tripsPage.includes("min-w-0 flex-1"),
      "My Trips title div must have min-w-0 flex-1 to prevent narrow-screen overflow"
    );
  });
});

// ── 16–18. ConciergePage sticky composer ────────────────────────────────────────

describe("Phase 8M: ConciergePage sticky composer mobile clearance", () => {
  it("16. sticky composer uses concierge-sticky-bottom class", () => {
    assert.ok(
      conciergePage.includes("concierge-sticky-bottom"),
      "concierge-instrument-composer must use concierge-sticky-bottom class"
    );
  });

  it("17. globals.css defines .concierge-sticky-bottom for mobile", () => {
    assert.ok(
      globalsCss.includes(".concierge-sticky-bottom"),
      "globals.css must define .concierge-sticky-bottom CSS class"
    );
  });

  it("18. globals.css concierge-sticky-bottom has lg override with bottom: 0", () => {
    const idx = globalsCss.indexOf(".concierge-sticky-bottom");
    const window = globalsCss.slice(idx, idx + 400);
    assert.ok(
      window.includes("bottom: 0"),
      "globals.css .concierge-sticky-bottom must have bottom: 0 override for lg+ viewports"
    );
  });

  it("43. sticky composer does not use bare bottom-0 z-10 class string", () => {
    assert.ok(
      !conciergePage.includes('"sticky bottom-0 z-10"'),
      "concierge sticky composer must not use bare 'sticky bottom-0 z-10' — must use concierge-sticky-bottom class"
    );
  });
});

// ── 19–23. Home surface ────────────────────────────────────────────────────────

describe("Phase 8M: Home surface structural contracts", () => {
  it("19. atelier-home testid present in DashboardClient", () => {
    assert.ok(
      dashboard.includes('data-testid="atelier-home"'),
      "DashboardClient must have data-testid='atelier-home'"
    );
  });

  it("20. concierge-entry testid present", () => {
    assert.ok(
      dashboard.includes('data-testid="concierge-entry"'),
      "DashboardClient must have data-testid='concierge-entry'"
    );
  });

  it("21. home-new-trip-action testid present", () => {
    assert.ok(
      dashboard.includes('data-testid="home-new-trip-action"'),
      "DashboardClient must have data-testid='home-new-trip-action'"
    );
  });

  it("22. atelier-planning-strip testid present", () => {
    assert.ok(
      dashboard.includes('data-testid="atelier-planning-strip"'),
      "DashboardClient must have data-testid='atelier-planning-strip'"
    );
  });

  it("23. empty state CTA cluster uses flex-col sm:flex-row for mobile stacking", () => {
    assert.ok(
      dashboard.includes("flex-col sm:flex-row"),
      "Home empty state CTA cluster must use flex-col sm:flex-row for mobile-first stacking"
    );
  });
});

// ── 24–28. My Trips surface ────────────────────────────────────────────────────

describe("Phase 8M: My Trips surface structural contracts", () => {
  it("24. trips-new-trip-action testid present", () => {
    assert.ok(
      tripsPage.includes('data-testid="trips-new-trip-action"'),
      "trips/page.tsx must have data-testid='trips-new-trip-action'"
    );
  });

  it("25. continue-planning-hero testid present", () => {
    assert.ok(
      tripsPage.includes('data-testid="continue-planning-hero"'),
      "trips/page.tsx must have data-testid='continue-planning-hero'"
    );
  });

  it("26. journey-card testid present", () => {
    assert.ok(
      tripsPage.includes('data-testid="journey-card"'),
      "trips/page.tsx must have data-testid='journey-card'"
    );
  });

  it("27. planning-tools-strip testid present", () => {
    assert.ok(
      tripsPage.includes('data-testid="planning-tools-strip"'),
      "trips/page.tsx must have data-testid='planning-tools-strip'"
    );
  });

  it("28. ContinuePlanningHero action footer uses flex flex-wrap for safe mobile layout", () => {
    assert.ok(
      tripsPage.includes("flex flex-wrap gap-2"),
      "ContinuePlanningHero action footer must use flex-wrap for mobile"
    );
  });
});

// ── 29–34. Explore surface ────────────────────────────────────────────────────

describe("Phase 8M: Explore surface structural contracts", () => {
  it("29. explore-lounge-header testid present", () => {
    assert.ok(
      exploreShell.includes('data-testid="explore-lounge-header"'),
      "ExploreShell must have data-testid='explore-lounge-header'"
    );
  });

  it("30. explore-vertical-grid testid present", () => {
    assert.ok(
      exploreShell.includes('data-testid="explore-vertical-grid"'),
      "ExploreShell must have data-testid='explore-vertical-grid'"
    );
  });

  it("31. vertical-card-flights testid present", () => {
    assert.ok(
      exploreShell.includes('data-testid="vertical-card-flights"') ||
      exploreShell.includes('data-testid={`vertical-card-${meta.id}`}') ||
      exploreShell.includes("vertical-card-${meta.id}"),
      "ExploreShell must have vertical-card-flights testid (or dynamic testid pattern)"
    );
  });

  it("32. vertical-card-hotels testid pattern present", () => {
    assert.ok(
      exploreShell.includes('data-testid={`vertical-card-${meta.id}`}') ||
      exploreShell.includes("vertical-card-${meta.id}") ||
      exploreShell.includes('data-testid="vertical-card-hotels"'),
      "ExploreShell must have vertical-card testid pattern"
    );
  });

  it("33. explore-instrument-header testid present", () => {
    assert.ok(
      exploreShell.includes('data-testid="explore-instrument-header"'),
      "ExploreShell active section must have data-testid='explore-instrument-header'"
    );
  });

  it("34. vertical card grid uses sm:grid-cols-2 responsive layout", () => {
    assert.ok(
      exploreShell.includes("sm:grid-cols-2"),
      "ExploreShell vertical grid must use sm:grid-cols-2 for responsive layout"
    );
  });
});

// ── 35–38. Saved surface ──────────────────────────────────────────────────────

describe("Phase 8M: Saved surface structural contracts", () => {
  it("35. saved-scrapbook-header testid present", () => {
    assert.ok(
      savedShell.includes('data-testid="saved-scrapbook-header"'),
      "SavedShell must have data-testid='saved-scrapbook-header'"
    );
  });

  it("36. saved-item-card testid present", () => {
    assert.ok(
      savedShell.includes('data-testid="saved-item-card"'),
      "SavedShell must have data-testid='saved-item-card'"
    );
  });

  it("37. saved-planning-bridge testid present", () => {
    assert.ok(
      savedShell.includes('data-testid="saved-planning-bridge"'),
      "SavedShell must have data-testid='saved-planning-bridge'"
    );
  });

  it("38. action buttons have 44px touch targets", () => {
    assert.ok(
      savedShell.includes("min-w-[44px]") && savedShell.includes("min-h-[44px]"),
      "SavedShell action buttons must have min-w-[44px] and min-h-[44px] touch targets"
    );
  });
});

// ── 39–43. Concierge surface ──────────────────────────────────────────────────

describe("Phase 8M: Standalone Concierge surface structural contracts", () => {
  it("39. concierge-page testid present", () => {
    assert.ok(
      conciergePage.includes('data-testid="concierge-page"'),
      "ConciergePage must have data-testid='concierge-page'"
    );
  });

  it("40. concierge-instrument-header testid present", () => {
    assert.ok(
      conciergePage.includes('data-testid="concierge-instrument-header"'),
      "ConciergePage must have data-testid='concierge-instrument-header'"
    );
  });

  it("41. concierge-results-canvas testid present", () => {
    assert.ok(
      conciergePage.includes('data-testid="concierge-results-canvas"'),
      "ConciergePage must have data-testid='concierge-results-canvas'"
    );
  });

  it("42. concierge-instrument-composer testid present", () => {
    assert.ok(
      conciergePage.includes('data-testid="concierge-instrument-composer"'),
      "ConciergePage must have data-testid='concierge-instrument-composer'"
    );
  });
});

// ── 44–46. Phase 8J preservation ─────────────────────────────────────────────

describe("Phase 8M: 8J shell/nav testids preserved", () => {
  it("44. mobile-bottom-nav testid preserved in MobileNav", () => {
    assert.ok(
      mobileNav.includes('data-testid="mobile-bottom-nav"'),
      "MobileNav must preserve data-testid='mobile-bottom-nav' from Phase 8J"
    );
  });

  it("45. mobile-nav-spacer preserved in AppShell", () => {
    assert.ok(
      appShell.includes("mobile-nav-spacer"),
      "AppShell must preserve mobile-nav-spacer class from Phase 8J"
    );
  });

  it("46. mobile-top-bar testid preserved in MobileNav", () => {
    assert.ok(
      mobileNav.includes('data-testid="mobile-top-bar"'),
      "MobileNav must preserve data-testid='mobile-top-bar' from Phase 8J"
    );
  });
});

// ── 47–48. Phase 8K preservation ─────────────────────────────────────────────

describe("Phase 8M: 8K workspace testids preserved", () => {
  it("47. trip-mobile-workspace testid preserved in trips/[id]/page.tsx", () => {
    assert.ok(
      tripDetailPage.includes("trip-mobile-workspace"),
      "trips/[id]/page.tsx must preserve trip-mobile-workspace testid from Phase 8K"
    );
  });

  it("48. trip-mobile-workspace-switcher testid preserved", () => {
    assert.ok(
      tripDetailPage.includes("trip-mobile-workspace-switcher"),
      "trips/[id]/page.tsx must preserve trip-mobile-workspace-switcher testid from Phase 8K"
    );
  });
});

// ── 49–50. Phase 8L preservation ─────────────────────────────────────────────

describe("Phase 8M: 8L itinerary testids preserved", () => {
  it("49. itinerary-day-mobile-chapter testid preserved in ItineraryDayColumn", () => {
    assert.ok(
      itineraryDay.includes("itinerary-day-mobile-chapter"),
      "ItineraryDayColumn must preserve itinerary-day-mobile-chapter testid from Phase 8L"
    );
  });

  it("50. itinerary-item-mobile-timeline-card testid preserved in ItineraryItemCard", () => {
    assert.ok(
      itineraryItem.includes("itinerary-item-mobile-timeline-card"),
      "ItineraryItemCard must preserve itinerary-item-mobile-timeline-card testid from Phase 8L"
    );
  });
});

// ── 51–52. No backend imports ─────────────────────────────────────────────────

describe("Phase 8M: no backend/provider imports in frontend entry flow", () => {
  it("51. TripBuilderForm has no backend/provider imports", () => {
    const prohibited = ["supabase", "backend", "provider_registry", "duffel"];
    for (const p of prohibited) {
      assert.ok(
        !tripBuilderForm.toLowerCase().includes(`from "${p}`),
        `TripBuilderForm must not import from ${p}`
      );
    }
  });

  it("52. trips/new page has no backend/provider imports", () => {
    const prohibited = ["supabase", "backend", "provider_registry", "duffel"];
    for (const p of prohibited) {
      assert.ok(
        !newTripPage.toLowerCase().includes(`from "${p}`),
        `trips/new/page.tsx must not import from ${p}`
      );
    }
  });
});
