/**
 * Phase 8N-B — Visible Boutique Art Direction Adoption contract tests.
 *
 * Verifies:
 *  1.  globals.css surface tokens are warm dark (no cold navy #0F1A2C / #1A2538).
 *  2.  globals.css --ds-midnight-ink is warm (no cold navy blue).
 *  3.  globals.css --ds-onyx-velvet is warm (no cold navy blue).
 *  4.  globals.css --ds-carbon-mist is warm (no cold navy blue).
 *  5.  globals.css --ds-pen-stroke is warm dark border (no cold navy blue).
 *  6.  globals.css .card background is warm (no cold purple/blue rgba(22, 22, 42)).
 *  7.  globals.css .card inner-shadow uses warm rgba highlight.
 *  8.  globals.css defines .boutique-folio class.
 *  9.  globals.css defines .boutique-instrument class.
 * 10.  globals.css .boutique-folio uses warm brass border ring (rgba(197, 148, 77)).
 * 11.  globals.css .boutique-instrument uses warm ambient glow.
 * 12.  globals.css .boutique-instrument uses warm brass border ring.
 * 13.  DashboardClient applies boutique-instrument to ConciergeEntry card.
 * 14.  DashboardClient applies atelier-surface-depth to ContinuePlanningStrip.
 * 15.  DashboardClient applies atelier-surface-depth to discovery tool tiles.
 * 16.  DashboardClient main wrapper applies atelier-transition.
 * 17.  trips/page applies boutique-instrument to ContinuePlanningHero.
 * 18.  trips/page applies boutique-folio to JourneyCard.
 * 19.  trips/page applies atelier-surface-depth to PlanningToolsStrip tiles.
 * 20.  ExploreShell applies boutique-instrument to active vertical instrument section.
 * 21.  ExploreShell applies atelier-surface-depth to VerticalCard.
 * 22.  AppShell page content wrapper applies atelier-transition.
 * 23.  8N preservation: globals.css still defines .atelier-atmosphere-root.
 * 24.  8N preservation: globals.css still defines .atelier-surface-depth.
 * 25.  8N preservation: globals.css still defines .shadow-elevation-warm.
 * 26.  8N preservation: globals.css still defines .atelier-accent-line.
 * 27.  8N preservation: globals.css still defines .atelier-vignette-layer.
 * 28.  8N preservation: globals.css still defines .atelier-texture-layer.
 * 29.  8J preservation: AppShell still has data-testid="mobile-page-content".
 * 30.  8J preservation: globals.css still defines .mobile-nav-spacer.
 * 31.  8K preservation: trips/[id] still has trip-mobile-workspace-switcher.
 * 32.  8L preservation: ItineraryDayColumn still has itinerary-day-mobile-chapter.
 * 33.  8M preservation: TripBuilderForm still has new-trip-builder-form testid.
 * 34.  8M preservation: ConciergePage still has .concierge-sticky-bottom.
 * 35.  No backend/provider imports added to frontend visual components.
 * 36.  No new npm packages added (package.json unchanged scope).
 * 37.  boutique-folio defined after atelier-surface-depth (source-order override).
 * 38.  boutique-instrument defined after boutique-folio (source-order override).
 * 39.  globals.css .boutique-folio uses inset top highlight (warm hairline).
 * 40.  globals.css .boutique-instrument uses inset top highlight (warm hairline).
 * 41.  trips/page boutique-folio applied to empty-state action cards.
 * 42.  DashboardClient JourneyShelfTeaser link uses atelier-surface-depth.
 * 43.  No inline cold boxShadow style remaining on ConciergeEntry card.
 * 44.  No inline cold boxShadow style remaining on ContinuePlanningHero.
 * 45.  No inline cold boxShadow style remaining on JourneyCard.
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

const globalsCss      = readRoot("src/app/globals.css");
const dashboardClient = readSrc("components/dashboard/DashboardClient.tsx");
const tripsPage       = readSrc("app/trips/page.tsx");
const exploreShell    = readSrc("components/explore/ExploreShell.tsx");
const appShell        = readSrc("components/layout/AppShell.tsx");
const tripDetailPage  = readSrc("app/trips/[id]/page.tsx");
const itineraryDay    = readSrc("components/trips/ItineraryDayColumn.tsx");
const tripBuilderForm = readSrc("components/trips/TripBuilderForm.tsx");
const conciergePage   = readSrc("components/concierge/ConciergePage.tsx");
const savedShell      = readSrc("components/saved/SavedShell.tsx");
const tripBuilder     = readSrc("components/trips/TripBuilder.tsx");

// ── 1–5. Surface token warmth ───────────────────────────────────────────────

describe("Phase 8N-B: Warm surface tokens (no cold navy)", () => {
  it("1. --ds-midnight-ink is warm dark (no cold #0B1320)", () => {
    assert.ok(
      !globalsCss.includes("--ds-midnight-ink:   #0B1320") &&
      !globalsCss.includes("--ds-midnight-ink: #0B1320"),
      "Cold navy --ds-midnight-ink #0B1320 must not remain"
    );
    assert.ok(
      globalsCss.includes("--ds-midnight-ink"),
      "--ds-midnight-ink must still be defined"
    );
  });

  it("2. --ds-onyx-velvet is warm dark (no cold #0F1A2C)", () => {
    assert.ok(
      !globalsCss.includes("--ds-onyx-velvet:    #0F1A2C") &&
      !globalsCss.includes("--ds-onyx-velvet: #0F1A2C"),
      "Cold navy --ds-onyx-velvet #0F1A2C must not remain"
    );
    assert.ok(
      globalsCss.includes("--ds-onyx-velvet"),
      "--ds-onyx-velvet must still be defined"
    );
  });

  it("3. --ds-carbon-mist is warm dark (no cold #1A2538)", () => {
    assert.ok(
      !globalsCss.includes("--ds-carbon-mist:    #1A2538") &&
      !globalsCss.includes("--ds-carbon-mist: #1A2538"),
      "Cold navy --ds-carbon-mist #1A2538 must not remain"
    );
    assert.ok(
      globalsCss.includes("--ds-carbon-mist"),
      "--ds-carbon-mist must still be defined"
    );
  });

  it("4. --ds-pen-stroke is warm dark border (no cold #22324A)", () => {
    assert.ok(
      !globalsCss.includes("--ds-pen-stroke:     #22324A") &&
      !globalsCss.includes("--ds-pen-stroke: #22324A"),
      "Cold navy --ds-pen-stroke #22324A must not remain"
    );
    assert.ok(
      globalsCss.includes("--ds-pen-stroke"),
      "--ds-pen-stroke must still be defined"
    );
  });

  it("5. --ds-atelier-base is warm near-black (no cold #0A1018)", () => {
    assert.ok(
      !globalsCss.includes("--ds-atelier-base:        #0A1018") &&
      !globalsCss.includes("--ds-atelier-base: #0A1018"),
      "Cold --ds-atelier-base #0A1018 must not remain"
    );
    assert.ok(
      globalsCss.includes("--ds-atelier-base"),
      "--ds-atelier-base must still be defined"
    );
  });
});

// ── 6–7. Warm .card CSS ──────────────────────────────────────────────────────

describe("Phase 8N-B: Warm .card CSS class", () => {
  it("6. .card background is warm dark (no cold rgba(22, 22, 42))", () => {
    assert.ok(
      !globalsCss.includes("rgba(22, 22, 42"),
      "Cold purple-blue card background rgba(22, 22, 42) must be replaced"
    );
  });

  it("7. .card inner-shadow uses warm rgba highlight", () => {
    const cardBlock = globalsCss.slice(
      globalsCss.indexOf(".card {"),
      globalsCss.indexOf(".card {") + 600
    );
    assert.ok(
      cardBlock.includes("rgba(235") || cardBlock.includes("rgba(220") || cardBlock.includes("rgba(240"),
      ".card must use warm rgba highlight in box-shadow (not cold white)"
    );
  });
});

// ── 8–12. New boutique utility classes ──────────────────────────────────────

describe("Phase 8N-B: New boutique CSS utility classes", () => {
  it("8. globals.css defines .boutique-folio class", () => {
    assert.ok(
      globalsCss.includes(".boutique-folio"),
      "globals.css must define .boutique-folio editorial card class"
    );
  });

  it("9. globals.css defines .boutique-instrument class", () => {
    assert.ok(
      globalsCss.includes(".boutique-instrument"),
      "globals.css must define .boutique-instrument primary focal surface class"
    );
  });

  it("10. .boutique-folio uses warm brass border ring", () => {
    const folioIdx = globalsCss.indexOf(".boutique-folio");
    const folioBlock = globalsCss.slice(folioIdx, folioIdx + 400);
    assert.ok(
      folioBlock.includes("197, 148, 77") || folioBlock.includes("var(--ds-atelier-card-border)"),
      ".boutique-folio must use warm brass border ring (rgba(197, 148, 77) or atelier-card-border token)"
    );
  });

  it("11. .boutique-instrument uses warm ambient glow", () => {
    const instIdx = globalsCss.indexOf(".boutique-instrument");
    const instBlock = globalsCss.slice(instIdx, instIdx + 500);
    assert.ok(
      instBlock.includes("180, 130, 60") || instBlock.includes("197, 148, 77"),
      ".boutique-instrument must use warm glow (amber-brass tones)"
    );
  });

  it("12. .boutique-instrument uses warm brass border ring", () => {
    const instIdx = globalsCss.indexOf(".boutique-instrument");
    const instBlock = globalsCss.slice(instIdx, instIdx + 500);
    assert.ok(
      instBlock.includes("0 0 0 1px"),
      ".boutique-instrument must include a warm brass border ring via inset/outset box-shadow"
    );
  });
});

// ── 13–16. DashboardClient visual adoption ───────────────────────────────────

describe("Phase 8N-B: DashboardClient boutique adoption", () => {
  it("13. DashboardClient applies boutique-instrument to ConciergeEntry card", () => {
    assert.ok(
      dashboardClient.includes("boutique-instrument"),
      "DashboardClient must apply boutique-instrument class to primary concierge card"
    );
  });

  it("14. DashboardClient applies atelier-surface-depth to ContinuePlanningStrip", () => {
    assert.ok(
      dashboardClient.includes("atelier-surface-depth"),
      "DashboardClient must apply atelier-surface-depth to card surfaces"
    );
  });

  it("15. DashboardClient discovery tiles use atelier-surface-depth", () => {
    const count = (dashboardClient.match(/atelier-surface-depth/g) || []).length;
    assert.ok(
      count >= 2,
      "DashboardClient must apply atelier-surface-depth to multiple surfaces (discovery tiles + planning strip)"
    );
  });

  it("16. DashboardClient main wrapper applies atelier-transition", () => {
    assert.ok(
      dashboardClient.includes("atelier-transition"),
      "DashboardClient main content wrapper must apply atelier-transition for page entrance"
    );
  });
});

// ── 17–19. trips/page visual adoption ───────────────────────────────────────

describe("Phase 8N-B: My Trips page boutique adoption", () => {
  it("17. trips/page applies folio-paper-panel to ContinuePlanningHero (Slice 2 paper conversion)", () => {
    assert.ok(
      tripsPage.includes("folio-paper-panel"),
      "trips/page must apply folio-paper-panel to ContinuePlanningHero (replaced boutique-instrument in Slice 2)"
    );
  });

  it("18. trips/page applies folio-paper-card to JourneyCard (Slice 2 paper conversion)", () => {
    assert.ok(
      tripsPage.includes("folio-paper-card"),
      "trips/page must apply folio-paper-card to JourneyCard (replaced boutique-folio in Slice 2)"
    );
  });

  it("19. trips/page uses bg-ds-bone for PlanningToolsStrip (Slice 2 paper conversion)", () => {
    assert.ok(
      tripsPage.includes("bg-ds-bone"),
      "trips/page PlanningToolsStrip must use bg-ds-bone (replaced atelier-surface-depth in Slice 2)"
    );
  });
});

// ── 20–21. ExploreShell visual adoption ──────────────────────────────────────

describe("Phase 8N-B: ExploreShell boutique adoption", () => {
  it("20. ExploreShell applies boutique-instrument to active vertical instrument section", () => {
    assert.ok(
      exploreShell.includes("boutique-instrument"),
      "ExploreShell must apply boutique-instrument to active instrument section"
    );
  });

  it("21. ExploreShell applies atelier-surface-depth to VerticalCard", () => {
    assert.ok(
      exploreShell.includes("atelier-surface-depth"),
      "ExploreShell must apply atelier-surface-depth to VerticalCard tiles"
    );
  });
});

// ── 22. AppShell transition ──────────────────────────────────────────────────

describe("Phase 8N-B: AppShell page transition", () => {
  it("22. AppShell page content wrapper applies atelier-transition", () => {
    assert.ok(
      appShell.includes("atelier-transition"),
      "AppShell mobile-page-content wrapper must apply atelier-transition"
    );
  });
});

// ── 23–34. Phase preservation (8N/8J/8K/8L/8M) ──────────────────────────────

describe("Phase 8N-B: Prior phase preservation", () => {
  it("23. 8N: globals.css still defines .atelier-atmosphere-root", () => {
    assert.ok(
      globalsCss.includes(".atelier-atmosphere-root"),
      ".atelier-atmosphere-root must be preserved from Phase 8N"
    );
  });

  it("24. 8N: globals.css still defines .atelier-surface-depth", () => {
    assert.ok(
      globalsCss.includes(".atelier-surface-depth"),
      ".atelier-surface-depth must be preserved from Phase 8N"
    );
  });

  it("25. 8N: globals.css still defines .shadow-elevation-warm", () => {
    assert.ok(
      globalsCss.includes(".shadow-elevation-warm"),
      ".shadow-elevation-warm must be preserved from Phase 8N"
    );
  });

  it("26. 8N: globals.css still defines .atelier-accent-line", () => {
    assert.ok(
      globalsCss.includes(".atelier-accent-line"),
      ".atelier-accent-line must be preserved from Phase 8N"
    );
  });

  it("27. 8N: globals.css still defines .atelier-vignette-layer", () => {
    assert.ok(
      globalsCss.includes(".atelier-vignette-layer"),
      ".atelier-vignette-layer must be preserved from Phase 8N"
    );
  });

  it("28. 8N: globals.css still defines .atelier-texture-layer", () => {
    assert.ok(
      globalsCss.includes(".atelier-texture-layer"),
      ".atelier-texture-layer must be preserved from Phase 8N"
    );
  });

  it("29. 8J: AppShell still has data-testid='mobile-page-content'", () => {
    assert.ok(
      appShell.includes('data-testid="mobile-page-content"'),
      "AppShell must retain mobile-page-content testid from Phase 8J"
    );
  });

  it("30. 8J: globals.css still defines .mobile-nav-spacer", () => {
    assert.ok(
      globalsCss.includes(".mobile-nav-spacer"),
      ".mobile-nav-spacer must be preserved from Phase 8J"
    );
  });

  it("31. 8K: trips/[id] still has trip-mobile-workspace-switcher", () => {
    assert.ok(
      tripDetailPage.includes("trip-mobile-workspace-switcher"),
      "Trip detail page must retain trip-mobile-workspace-switcher from Phase 8K"
    );
  });

  it("32. 8L: ItineraryDayColumn still has itinerary-day-mobile-chapter", () => {
    assert.ok(
      itineraryDay.includes("itinerary-day-mobile-chapter"),
      "ItineraryDayColumn must retain itinerary-day-mobile-chapter from Phase 8L"
    );
  });

  it("33. 8M: TripBuilderForm still has new-trip-builder-form testid", () => {
    assert.ok(
      tripBuilderForm.includes('new-trip-builder-form'),
      "TripBuilderForm must retain new-trip-builder-form testid from Phase 8M"
    );
  });

  it("34. 8M: ConciergePage still has .concierge-sticky-bottom class", () => {
    assert.ok(
      conciergePage.includes("concierge-sticky-bottom"),
      "ConciergePage must retain concierge-sticky-bottom from Phase 8M"
    );
  });
});

// ── 35–36. Safety: no backend/provider/package changes ──────────────────────

describe("Phase 8N-B: Safety — no backend/provider/package drift", () => {
  it("35. DashboardClient has no backend import", () => {
    assert.ok(
      !dashboardClient.includes("from '@/backend") &&
      !dashboardClient.includes("from '../backend"),
      "DashboardClient must not import from backend"
    );
  });

  it("36. ExploreShell has no backend import", () => {
    assert.ok(
      !exploreShell.includes("from '@/backend") &&
      !exploreShell.includes("from '../backend"),
      "ExploreShell must not import from backend"
    );
  });
});

// ── 37–40. CSS source-order and warm highlights ──────────────────────────────

describe("Phase 8N-B: CSS source-order and inset highlights", () => {
  it("37. boutique-folio defined after atelier-surface-depth in globals.css", () => {
    const depthIdx = globalsCss.indexOf(".atelier-surface-depth");
    const folioIdx = globalsCss.indexOf(".boutique-folio");
    assert.ok(
      folioIdx > depthIdx,
      ".boutique-folio must be defined after .atelier-surface-depth for correct override"
    );
  });

  it("38. boutique-instrument defined after boutique-folio in globals.css", () => {
    const folioIdx = globalsCss.indexOf(".boutique-folio");
    const instIdx  = globalsCss.indexOf(".boutique-instrument");
    assert.ok(
      instIdx > folioIdx,
      ".boutique-instrument must be defined after .boutique-folio"
    );
  });

  it("39. .boutique-folio uses inset top highlight", () => {
    const folioIdx = globalsCss.indexOf(".boutique-folio");
    const folioBlock = globalsCss.slice(folioIdx, folioIdx + 400);
    assert.ok(
      folioBlock.includes("inset 0 1px 0"),
      ".boutique-folio must include inset 0 1px 0 warm top hairline"
    );
  });

  it("40. .boutique-instrument uses inset top highlight", () => {
    const instIdx = globalsCss.indexOf(".boutique-instrument");
    const instBlock = globalsCss.slice(instIdx, instIdx + 500);
    assert.ok(
      instBlock.includes("inset 0 1px 0"),
      ".boutique-instrument must include inset 0 1px 0 warm top hairline"
    );
  });
});

// ── 41–45. Additional adoption checks ───────────────────────────────────────

describe("Phase 8N-B: Additional adoption and cleanup checks", () => {
  it("41. trips/page applies folio-paper-card to empty-state action cards (Slice 2 paper conversion)", () => {
    const count = (tripsPage.match(/folio-paper-card/g) || []).length;
    assert.ok(
      count >= 2,
      "trips/page must apply folio-paper-card to multiple surfaces (JourneyCard + empty state cards)"
    );
  });

  it("42. DashboardClient JourneyShelfTeaser link uses atelier-surface-depth", () => {
    assert.ok(
      dashboardClient.includes("atelier-surface-depth"),
      "DashboardClient must apply atelier-surface-depth to JourneyShelfTeaser link card"
    );
  });

  it("43. ConciergeEntry no longer uses cold inline boxShadow elevation-2", () => {
    const conciergeEntrySection = dashboardClient.slice(
      dashboardClient.indexOf("concierge-entry"),
      dashboardClient.indexOf("concierge-entry") + 600
    );
    assert.ok(
      !conciergeEntrySection.includes('"var(--ds-elevation-2)"') ||
      conciergeEntrySection.includes("boutique-instrument"),
      "ConciergeEntry must use boutique-instrument class instead of inline elevation-2"
    );
  });

  it("44. ContinuePlanningHero uses folio-paper-panel (Slice 2 paper conversion)", () => {
    assert.ok(
      tripsPage.includes("folio-paper-panel"),
      "ContinuePlanningHero must use folio-paper-panel (replaced boutique-instrument in Slice 2)"
    );
  });

  it("45. JourneyCard uses folio-paper-card (Slice 2 paper conversion)", () => {
    assert.ok(
      tripsPage.includes("folio-paper-card"),
      "JourneyCard must use folio-paper-card (replaced boutique-folio in Slice 2)"
    );
  });
});

// ── 46–50. Saved Ideas boutique adoption ────────────────────────────────────

describe("Phase 8N-B: Saved Ideas boutique adoption (direct, not token-only)", () => {
  it("46. SavedItemCard applies a dark folio card class (8N-F: saved-folio-card replaces boutique-folio)", () => {
    // boutique-folio was removed from SavedItemCard in Phase 8N-F (true visual correction).
    // The dark atelier saved-folio-card class is now the canonical saved card surface.
    assert.ok(
      savedShell.includes("saved-folio-card"),
      "SavedShell must apply saved-folio-card to SavedItemCard (dark atelier surface, replaces boutique-folio after 8N-F)"
    );
  });

  it("47. SavedShell applies atelier-transition to outer wrapper", () => {
    assert.ok(
      savedShell.includes("atelier-transition"),
      "SavedShell outer wrapper must apply atelier-transition for page entrance"
    );
  });

  it("48. SavedShell has no backend or provider imports", () => {
    assert.ok(
      !savedShell.includes("from '@/backend") &&
      !savedShell.includes("from '../backend") &&
      !savedShell.includes("from '@/services"),
      "SavedShell must not import from backend or services"
    );
  });
});

// ── 51–55. Concierge boutique adoption ──────────────────────────────────────

describe("Phase 8N-B: Concierge boutique adoption (direct, not token-only)", () => {
  it("51. ConciergeResultCard applies boutique-folio class directly", () => {
    assert.ok(
      conciergePage.includes("boutique-folio"),
      "ConciergePage must apply boutique-folio to result cards — token warming alone is not sufficient"
    );
  });

  it("52. Concierge composer instrument applies boutique-instrument class", () => {
    assert.ok(
      conciergePage.includes("boutique-instrument"),
      "concierge-instrument-composer must apply boutique-instrument as primary focal surface"
    );
  });

  it("53. ConciergePage root applies atelier-transition", () => {
    assert.ok(
      conciergePage.includes("atelier-transition"),
      "ConciergePage root div must apply atelier-transition for page entrance"
    );
  });

  it("54. ConciergePage concierge-sticky-bottom preserved from 8M", () => {
    assert.ok(
      conciergePage.includes("concierge-sticky-bottom"),
      "ConciergePage must retain concierge-sticky-bottom from Phase 8M"
    );
  });
});

// ── 56–59. New Trip boutique adoption ───────────────────────────────────────

describe("Phase 8N-B: New Trip boutique adoption (direct, not token-only)", () => {
  it("56. TripBuilderForm form container applies boutique-folio class", () => {
    assert.ok(
      tripBuilderForm.includes("boutique-folio"),
      "TripBuilderForm form must apply boutique-folio — inline elevation-1 must be replaced"
    );
  });

  it("57. TripBuilderForm loading state applies boutique-instrument class", () => {
    assert.ok(
      tripBuilderForm.includes("boutique-instrument"),
      "TripBuilderForm loading state card must apply boutique-instrument"
    );
  });

  it("58. TripBuilderForm outer wrapper applies atelier-transition", () => {
    assert.ok(
      tripBuilderForm.includes("atelier-transition"),
      "TripBuilderForm outer wrapper must apply atelier-transition for page entrance"
    );
  });

  it("59. TripBuilderForm no longer uses cold inline elevation-1 or elevation-2", () => {
    assert.ok(
      !tripBuilderForm.includes('"var(--ds-elevation-1)"') &&
      !tripBuilderForm.includes('"var(--ds-elevation-2)"'),
      "TripBuilderForm must not use inline elevation boxShadow — replaced with boutique classes"
    );
  });
});

// ── 60–63. Trip Detail workspace boutique adoption ──────────────────────────

describe("Phase 8N-B: Trip Detail workspace boutique adoption (direct, not token-only)", () => {
  it("60. Trip chapter cover applies folio-paper-panel (Slice 2 paper conversion)", () => {
    assert.ok(
      tripDetailPage.includes("folio-paper-panel"),
      "trip-chapter-cover section must use folio-paper-panel (replaced boutique-instrument in Slice 2)"
    );
  });

  it("61. Mobile workspace switcher uses bg-ds-bone (Slice 2 paper conversion)", () => {
    assert.ok(
      tripDetailPage.includes("bg-ds-bone"),
      "trip-mobile-workspace-switcher must use bg-ds-bone (replaced atelier-surface-depth in Slice 2)"
    );
  });

  it("62. Trip detail loading skeleton uses folio-paper-panel (Slice 2 paper conversion)", () => {
    const skeletonIdx = tripDetailPage.indexOf("animate-pulse");
    const skeletonBlock = tripDetailPage.slice(Math.max(0, skeletonIdx - 200), skeletonIdx + 100);
    assert.ok(
      skeletonBlock.includes("folio-paper-panel"),
      "Trip detail loading skeleton must use folio-paper-panel (replaced boutique-instrument in Slice 2)"
    );
  });

  it("63. TripBuilder workspace panels apply boutique-folio to CollapsiblePanel and candidate cards", () => {
    assert.ok(
      tripBuilder.includes("boutique-folio"),
      "TripBuilder must apply boutique-folio to CollapsiblePanel containers and candidate card surfaces"
    );
  });

  it("64. TripBuilder SummaryBar applies atelier-surface-depth", () => {
    assert.ok(
      tripBuilder.includes("atelier-surface-depth"),
      "TripBuilder SummaryBar must apply atelier-surface-depth"
    );
  });
});
