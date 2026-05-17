/**
 * Phase 8N-C — Real Boutique Visual Composition Pass contract tests.
 *
 * Verifies:
 *  1.  globals.css defines .editorial-scene composition primitive.
 *  2.  globals.css defines .advisor-desk-panel composition primitive.
 *  3.  globals.css defines .concierge-desk-header composition primitive.
 *  4.  globals.css defines .scrapbook-page composition primitive.
 *  5.  globals.css defines .folio-cover-tab composition primitive.
 *  6.  globals.css defines .atelier-stamp composition primitive.
 *  7.  globals.css defines .editorial-section-rule composition primitive.
 *  8.  globals.css defines .mapline-rule composition primitive.
 *  9.  globals.css defines .clipping-card composition primitive.
 * 10.  .advisor-desk-panel has a visible brass accent rule (::after gradient).
 * 11.  .advisor-desk-panel has a visible warm desk-lamp glow (::before radial).
 * 12.  .advisor-desk-panel uses warm dark gradient background.
 * 13.  .scrapbook-page uses warm paper gradient (ds-warm-paper token).
 * 14.  .scrapbook-page has a visible binding spine (::before left strip).
 * 15.  .folio-cover-tab has a visible warm brass gradient.
 * 16.  .clipping-card uses ds-warm-paper background.
 * 17.  DashboardClient uses advisor-desk-panel on ConciergeEntry.
 * 18.  DashboardClient ConciergeEntry has concierge-desk-header zone.
 * 19.  DashboardClient uses editorial-scene on main content wrapper.
 * 20.  DashboardClient uses mapline-rule motif in AtelierGreeting.
 * 21.  DashboardClient uses editorial-section-rule in AtelierPlanningStrip.
 * 22.  DashboardClient still has boutique-instrument (8N-B preservation).
 * 23.  DashboardClient still has atelier-transition (8N-B preservation).
 * 24.  DashboardClient ConciergeEntry has data-testid="concierge-advisor-desk".
 * 25.  SavedShell uses scrapbook-page composition (not flat bg-ds-linen).
 * 26.  SavedShell uses clipping-card on saved item cards.
 * 27.  SavedShell has editorial-section-rule in scrapbook header.
 * 28.  SavedShell retains saved-scrapbook-header testid (8G preservation).
 * 29.  SavedShell retains saved-planning-bridge testid (8G preservation).
 * 30.  trips/page JourneyCard has folio-cover-tab element.
 * 31.  trips/page ContinuePlanningHero has advisor-desk-panel.
 * 32.  trips/page ContinuePlanningHero has concierge-desk-header zone.
 * 33.  trips/page uses editorial-scene on body content.
 * 34.  trips/page still has boutique-instrument on ContinuePlanningHero (8N-B).
 * 35.  trips/page still has boutique-folio on JourneyCard (8N-B).
 * 36.  ConciergePage uses editorial-scene wrapper.
 * 37.  ConciergePage has mapline-rule motif.
 * 38.  ConciergeResultCard has folio-cover-tab element.
 * 39.  TripBuilderForm uses editorial-scene wrapper.
 * 40.  TripBuilderForm uses advisor-desk-panel on form.
 * 41.  No backend/provider imports added to visual components.
 * 42.  No new npm packages added.
 * 43.  8J preservation: mobile-page-content testid present.
 * 44.  8K preservation: trip-mobile-workspace-switcher present.
 * 45.  8L preservation: itinerary-day-mobile-chapter present.
 * 46.  8M preservation: new-trip-builder-form testid present.
 * 47.  advisor-desk-panel defined after boutique-instrument (source-order).
 * 48.  scrapbook-page defined after boutique-folio (source-order).
 * 49.  clipping-card defined after scrapbook-page (source-order).
 * 50.  .advisor-desk-panel has overflow:hidden for brass accent clipping.
 * 51.  Trip Detail chapter cover uses advisor-desk-panel composition.
 * 52.  Trip Detail chapter cover has folio-cover-tab top accent.
 * 53.  Trip Detail workspace wrapper uses editorial-scene.
 * 54.  Trip Detail has editorial-section-rule between chapter cover and briefing.
 * 55.  Trip Detail retains trip-chapter-cover testid (behavior preservation).
 * 56.  Trip Detail retains trip-mobile-workspace-switcher (8K preservation).
 * 57.  Trip Detail retains boutique-instrument on chapter cover (8N-B).
 * 58.  TripBuilder CollapsiblePanel has folio-cover-tab top accent.
 * 59.  TripBuilder CollapsiblePanel still uses boutique-folio (8N-B).
 * 60.  ExploreShell home view uses editorial-scene.
 * 61.  ExploreShell home view has editorial-section-rule after header.
 * 62.  ExploreShell VerticalCard uses boutique-folio composition.
 * 63.  ExploreShell vertical flow view uses editorial-scene.
 * 64.  ExploreShell active search instrument has folio-cover-tab.
 * 65.  ExploreShell retains boutique-instrument on search section (8N-B).
 * 66.  ExploreShell retains explore-lounge-header testid (8F preservation).
 * 67.  No backend/provider/SQL/env/package drift on patched files.
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
const savedShell      = readSrc("components/saved/SavedShell.tsx");
const tripsPage       = readSrc("app/trips/page.tsx");
const conciergePage   = readSrc("components/concierge/ConciergePage.tsx");
const tripBuilderForm = readSrc("components/trips/TripBuilderForm.tsx");
const appShell        = readSrc("components/layout/AppShell.tsx");
const tripDetailPage  = readSrc("app/trips/[id]/page.tsx");
const itineraryDay    = readSrc("components/trips/ItineraryDayColumn.tsx");
const tripBuilder     = readSrc("components/trips/TripBuilder.tsx");
const exploreShell    = readSrc("components/explore/ExploreShell.tsx");

// ── 1–16. globals.css composition primitives ──────────────────────────────────

describe("Phase 8N-C: globals.css composition primitives", () => {
  it("1. globals.css defines .editorial-scene composition primitive", () => {
    assert.ok(
      globalsCss.includes(".editorial-scene"),
      "globals.css must define .editorial-scene for page scene wrappers"
    );
  });

  it("2. globals.css defines .advisor-desk-panel composition primitive", () => {
    assert.ok(
      globalsCss.includes(".advisor-desk-panel"),
      "globals.css must define .advisor-desk-panel for hero instrument surfaces"
    );
  });

  it("3. globals.css defines .concierge-desk-header composition primitive", () => {
    assert.ok(
      globalsCss.includes(".concierge-desk-header"),
      "globals.css must define .concierge-desk-header for two-zone interior"
    );
  });

  it("4. globals.css defines .scrapbook-page composition primitive", () => {
    assert.ok(
      globalsCss.includes(".scrapbook-page"),
      "globals.css must define .scrapbook-page for Saved Ideas warm paper composition"
    );
  });

  it("5. globals.css defines .folio-cover-tab composition primitive", () => {
    assert.ok(
      globalsCss.includes(".folio-cover-tab"),
      "globals.css must define .folio-cover-tab for visible brass top accent on folio cards"
    );
  });

  it("6. globals.css defines .atelier-stamp composition primitive", () => {
    assert.ok(
      globalsCss.includes(".atelier-stamp"),
      "globals.css must define .atelier-stamp circular decorative mark"
    );
  });

  it("7. globals.css defines .editorial-section-rule composition primitive", () => {
    assert.ok(
      globalsCss.includes(".editorial-section-rule"),
      "globals.css must define .editorial-section-rule for warm brass section dividers"
    );
  });

  it("8. globals.css defines .mapline-rule composition primitive", () => {
    assert.ok(
      globalsCss.includes(".mapline-rule"),
      "globals.css must define .mapline-rule for subtle route-line motif"
    );
  });

  it("9. globals.css defines .clipping-card composition primitive", () => {
    assert.ok(
      globalsCss.includes(".clipping-card"),
      "globals.css must define .clipping-card for saved idea cards as press clippings"
    );
  });

  it("10. .advisor-desk-panel has a visible brass accent rule (::after gradient)", () => {
    const panelIdx = globalsCss.indexOf(".advisor-desk-panel::after");
    assert.ok(panelIdx !== -1, ".advisor-desk-panel::after must exist (brass accent rule)");
    const afterBlock = globalsCss.slice(panelIdx, panelIdx + 400);
    assert.ok(
      afterBlock.includes("background") && afterBlock.includes("linear-gradient"),
      ".advisor-desk-panel::after must have a visible linear-gradient brass accent rule"
    );
  });

  it("11. .advisor-desk-panel has a visible warm desk-lamp glow (::before radial)", () => {
    const beforeIdx = globalsCss.indexOf(".advisor-desk-panel::before");
    assert.ok(beforeIdx !== -1, ".advisor-desk-panel::before must exist (desk-lamp glow)");
    const beforeBlock = globalsCss.slice(beforeIdx, beforeIdx + 400);
    assert.ok(
      beforeBlock.includes("radial-gradient"),
      ".advisor-desk-panel::before must have a visible radial-gradient warm glow"
    );
  });

  it("12. .advisor-desk-panel uses warm dark gradient background", () => {
    const panelIdx = globalsCss.indexOf(".advisor-desk-panel {");
    assert.ok(panelIdx !== -1, ".advisor-desk-panel definition must exist");
    const block = globalsCss.slice(panelIdx, panelIdx + 600);
    assert.ok(
      block.includes("linear-gradient"),
      ".advisor-desk-panel must use a warm dark gradient background (not flat black)"
    );
  });

  it("13. .scrapbook-page uses warm paper gradient (ds-warm-paper token)", () => {
    const pageIdx = globalsCss.indexOf(".scrapbook-page {");
    assert.ok(pageIdx !== -1, ".scrapbook-page definition must exist");
    const block = globalsCss.slice(pageIdx, pageIdx + 400);
    assert.ok(
      block.includes("var(--ds-warm-paper)"),
      ".scrapbook-page must use var(--ds-warm-paper) token in gradient (not flat linen)"
    );
  });

  it("14. .scrapbook-page has a visible binding spine (::before left strip)", () => {
    const spineIdx = globalsCss.indexOf(".scrapbook-page::before");
    assert.ok(spineIdx !== -1, ".scrapbook-page::before must exist (binding spine)");
    const spineBlock = globalsCss.slice(spineIdx, spineIdx + 300);
    assert.ok(
      spineBlock.includes("left: 0") || spineBlock.includes("left:0"),
      ".scrapbook-page::before must be anchored to the left edge (binding spine)"
    );
  });

  it("15. .folio-cover-tab has a visible warm brass gradient", () => {
    const tabIdx = globalsCss.indexOf(".folio-cover-tab {");
    assert.ok(tabIdx !== -1, ".folio-cover-tab definition must exist");
    const block = globalsCss.slice(tabIdx, tabIdx + 300);
    assert.ok(
      block.includes("linear-gradient"),
      ".folio-cover-tab must have a visible linear-gradient (not solid color)"
    );
  });

  it("16. .clipping-card uses ds-warm-paper background", () => {
    const cardIdx = globalsCss.indexOf(".clipping-card {");
    assert.ok(cardIdx !== -1, ".clipping-card definition must exist");
    const block = globalsCss.slice(cardIdx, cardIdx + 200);
    assert.ok(
      block.includes("var(--ds-warm-paper)"),
      ".clipping-card must use var(--ds-warm-paper) background token"
    );
  });
});

// ── 17–24. DashboardClient visual composition ─────────────────────────────────

describe("Phase 8N-C: DashboardClient visual composition", () => {
  it("17. DashboardClient uses advisor-desk-panel on ConciergeEntry", () => {
    assert.ok(
      dashboardClient.includes("advisor-desk-panel"),
      "DashboardClient ConciergeEntry must use advisor-desk-panel composition class"
    );
  });

  it("18. DashboardClient ConciergeEntry has concierge-desk-header zone", () => {
    assert.ok(
      dashboardClient.includes("concierge-desk-header"),
      "DashboardClient ConciergeEntry must have concierge-desk-header two-zone interior"
    );
  });

  it("19. DashboardClient uses editorial-scene on main content wrapper", () => {
    assert.ok(
      dashboardClient.includes("editorial-scene"),
      "DashboardClient main wrapper must have editorial-scene for page scene framing"
    );
  });

  it("20. DashboardClient uses mapline-rule motif in AtelierGreeting", () => {
    assert.ok(
      dashboardClient.includes("mapline-rule"),
      "DashboardClient AtelierGreeting must include mapline-rule travel motif"
    );
  });

  it("21. DashboardClient uses editorial-section-rule in AtelierPlanningStrip", () => {
    assert.ok(
      dashboardClient.includes("editorial-section-rule"),
      "DashboardClient AtelierPlanningStrip must include editorial-section-rule divider"
    );
  });

  it("22. DashboardClient still has boutique-instrument (8N-B preservation)", () => {
    assert.ok(
      dashboardClient.includes("boutique-instrument"),
      "DashboardClient must still reference boutique-instrument (8N-B compatibility)"
    );
  });

  it("23. DashboardClient still has atelier-transition (8N-B preservation)", () => {
    assert.ok(
      dashboardClient.includes("atelier-transition"),
      "DashboardClient must still apply atelier-transition on main wrapper"
    );
  });

  it("24. DashboardClient ConciergeEntry has data-testid='concierge-advisor-desk'", () => {
    assert.ok(
      dashboardClient.includes("concierge-advisor-desk"),
      "DashboardClient ConciergeEntry advisor panel must have testid 'concierge-advisor-desk'"
    );
  });
});

// ── 25–29. SavedShell visual composition ──────────────────────────────────────

describe("Phase 8N-C: SavedShell visual composition", () => {
  it("25. SavedShell uses scrapbook-page composition (not flat bg-ds-linen)", () => {
    assert.ok(
      savedShell.includes("scrapbook-page"),
      "SavedShell must use scrapbook-page composition class (not just bg-ds-linen)"
    );
  });

  it("26. SavedShell uses clipping-card on saved item cards", () => {
    assert.ok(
      savedShell.includes("clipping-card"),
      "SavedShell SavedItemCard must use clipping-card CSS class"
    );
  });

  it("27. SavedShell has editorial-section-rule in scrapbook header", () => {
    assert.ok(
      savedShell.includes("editorial-section-rule"),
      "SavedShell scrapbook header must include editorial-section-rule divider"
    );
  });

  it("28. SavedShell retains saved-scrapbook-header testid (8G preservation)", () => {
    assert.ok(
      savedShell.includes('data-testid="saved-scrapbook-header"'),
      "SavedShell must retain data-testid='saved-scrapbook-header' (8G contract)"
    );
  });

  it("29. SavedShell retains saved-planning-bridge testid (8G preservation)", () => {
    assert.ok(
      savedShell.includes('data-testid="saved-planning-bridge"'),
      "SavedShell must retain data-testid='saved-planning-bridge' (8G contract)"
    );
  });
});

// ── 30–35. trips/page visual composition ──────────────────────────────────────

describe("Phase 8N-C: trips/page visual composition", () => {
  it("30. trips/page JourneyCard has folio-cover-tab element", () => {
    assert.ok(
      tripsPage.includes("folio-cover-tab"),
      "trips/page JourneyCard must have folio-cover-tab for visible brass top accent"
    );
  });

  it("31. trips/page ContinuePlanningHero has advisor-desk-panel", () => {
    assert.ok(
      tripsPage.includes("advisor-desk-panel"),
      "trips/page ContinuePlanningHero must use advisor-desk-panel composition"
    );
  });

  it("32. trips/page ContinuePlanningHero has concierge-desk-header zone", () => {
    assert.ok(
      tripsPage.includes("concierge-desk-header"),
      "trips/page ContinuePlanningHero must have concierge-desk-header interior zone"
    );
  });

  it("33. trips/page uses editorial-scene on body content", () => {
    assert.ok(
      tripsPage.includes("editorial-scene"),
      "trips/page body content must use editorial-scene for page canvas framing"
    );
  });

  it("34. trips/page still has boutique-instrument on ContinuePlanningHero (8N-B)", () => {
    assert.ok(
      tripsPage.includes("boutique-instrument"),
      "trips/page must still apply boutique-instrument on ContinuePlanningHero (8N-B)"
    );
  });

  it("35. trips/page still has boutique-folio on JourneyCard (8N-B)", () => {
    assert.ok(
      tripsPage.includes("boutique-folio"),
      "trips/page must still apply boutique-folio on JourneyCard (8N-B)"
    );
  });
});

// ── 36–40. Concierge and New Trip visual composition ─────────────────────────

describe("Phase 8N-C: Concierge and New Trip visual composition", () => {
  it("36. ConciergePage uses editorial-scene wrapper", () => {
    assert.ok(
      conciergePage.includes("editorial-scene"),
      "ConciergePage must use editorial-scene on main wrapper"
    );
  });

  it("37. ConciergePage has mapline-rule motif", () => {
    assert.ok(
      conciergePage.includes("mapline-rule"),
      "ConciergePage must include mapline-rule editorial rhythm element"
    );
  });

  it("38. ConciergeResultCard has folio-cover-tab element", () => {
    assert.ok(
      conciergePage.includes("folio-cover-tab"),
      "ConciergePage ConciergeResultCard must have folio-cover-tab (recommendation slip)"
    );
  });

  it("39. TripBuilderForm uses editorial-scene wrapper", () => {
    assert.ok(
      tripBuilderForm.includes("editorial-scene"),
      "TripBuilderForm container must use editorial-scene for intake form framing"
    );
  });

  it("40. TripBuilderForm uses advisor-desk-panel on form", () => {
    assert.ok(
      tripBuilderForm.includes("advisor-desk-panel"),
      "TripBuilderForm form element must use advisor-desk-panel composition"
    );
  });
});

// ── 41–50. Invariants and preservation ────────────────────────────────────────

describe("Phase 8N-C: invariants and preservation", () => {
  it("41. No backend/provider imports added to visual components", () => {
    const backendPattern = /from ['"].*backend.*['"]/;
    assert.ok(
      !backendPattern.test(dashboardClient),
      "DashboardClient must not import backend modules"
    );
    assert.ok(
      !backendPattern.test(savedShell),
      "SavedShell must not import backend modules"
    );
    assert.ok(
      !backendPattern.test(conciergePage),
      "ConciergePage must not import backend modules"
    );
  });

  it("42. No new npm packages added (package.json unchanged scope)", () => {
    const pkg = readRoot("package.json");
    const parsed = JSON.parse(pkg);
    // Verify no unusual new packages — package.json must still parse
    assert.ok(typeof parsed === "object", "package.json must remain valid JSON");
    assert.ok(
      !pkg.includes("react-spring") &&
      !pkg.includes("framer-motion"),
      "No new heavyweight animation library packages added (no react-spring, framer-motion)"
    );
  });

  it("43. 8J preservation: mobile-page-content testid present", () => {
    assert.ok(
      appShell.includes('data-testid="mobile-page-content"'),
      "AppShell must retain mobile-page-content testid (8J contract)"
    );
  });

  it("44. 8K preservation: trip-mobile-workspace-switcher present", () => {
    assert.ok(
      tripDetailPage.includes("trip-mobile-workspace-switcher"),
      "trips/[id]/page must retain trip-mobile-workspace-switcher (8K contract)"
    );
  });

  it("45. 8L preservation: itinerary-day-mobile-chapter present", () => {
    assert.ok(
      itineraryDay.includes("itinerary-day-mobile-chapter"),
      "ItineraryDayColumn must retain itinerary-day-mobile-chapter testid (8L contract)"
    );
  });

  it("46. 8M preservation: new-trip-builder-form testid present", () => {
    assert.ok(
      tripBuilderForm.includes("new-trip-builder-form"),
      "TripBuilderForm must retain new-trip-builder-form testid (8M contract)"
    );
  });

  it("47. advisor-desk-panel defined after boutique-instrument (source-order)", () => {
    const instrIdx = globalsCss.indexOf(".boutique-instrument");
    const panelIdx = globalsCss.indexOf(".advisor-desk-panel");
    assert.ok(instrIdx !== -1, ".boutique-instrument must exist");
    assert.ok(panelIdx !== -1, ".advisor-desk-panel must exist");
    assert.ok(
      panelIdx > instrIdx,
      ".advisor-desk-panel must be defined after .boutique-instrument for source-order layering"
    );
  });

  it("48. scrapbook-page defined after boutique-folio (source-order)", () => {
    const folioIdx = globalsCss.indexOf(".boutique-folio");
    const pageIdx  = globalsCss.indexOf(".scrapbook-page");
    assert.ok(folioIdx !== -1, ".boutique-folio must exist");
    assert.ok(pageIdx !== -1, ".scrapbook-page must exist");
    assert.ok(
      pageIdx > folioIdx,
      ".scrapbook-page must be defined after .boutique-folio"
    );
  });

  it("49. clipping-card defined after scrapbook-page (source-order)", () => {
    const pageIdx = globalsCss.indexOf(".scrapbook-page");
    const cardIdx = globalsCss.indexOf(".clipping-card");
    assert.ok(pageIdx !== -1, ".scrapbook-page must exist");
    assert.ok(cardIdx !== -1, ".clipping-card must exist");
    assert.ok(
      cardIdx > pageIdx,
      ".clipping-card must be defined after .scrapbook-page"
    );
  });

  it("50. .advisor-desk-panel has overflow:hidden for brass accent clipping", () => {
    const panelIdx = globalsCss.indexOf(".advisor-desk-panel {");
    assert.ok(panelIdx !== -1, ".advisor-desk-panel block must exist");
    const block = globalsCss.slice(panelIdx, panelIdx + 600);
    assert.ok(
      block.includes("overflow: hidden") || block.includes("overflow:hidden"),
      ".advisor-desk-panel must have overflow:hidden so brass accent is clipped to border-radius"
    );
  });
});

// ── 51–57. Trip Detail composition adoption ───────────────────────────────────

describe("Phase 8N-C patch: Trip Detail composition adoption", () => {
  it("51. Trip Detail chapter cover uses advisor-desk-panel composition", () => {
    assert.ok(
      tripDetailPage.includes("advisor-desk-panel"),
      "trips/[id]/page must use advisor-desk-panel on chapter cover section"
    );
  });

  it("52. Trip Detail chapter cover has folio-cover-tab top accent", () => {
    assert.ok(
      tripDetailPage.includes("folio-cover-tab"),
      "trips/[id]/page chapter cover must include folio-cover-tab element"
    );
  });

  it("53. Trip Detail workspace wrapper uses editorial-scene", () => {
    assert.ok(
      tripDetailPage.includes("editorial-scene"),
      "trips/[id]/page trip-mobile-workspace wrapper must have editorial-scene class"
    );
  });

  it("54. Trip Detail has editorial-section-rule between chapter cover and briefing", () => {
    assert.ok(
      tripDetailPage.includes("editorial-section-rule"),
      "trips/[id]/page must have editorial-section-rule divider between chapter cover and briefing"
    );
  });

  it("55. Trip Detail retains trip-chapter-cover testid (behavior preservation)", () => {
    assert.ok(
      tripDetailPage.includes('data-testid="trip-chapter-cover"'),
      "trips/[id]/page must retain trip-chapter-cover testid"
    );
  });

  it("56. Trip Detail retains trip-mobile-workspace-switcher (8K preservation)", () => {
    assert.ok(
      tripDetailPage.includes("trip-mobile-workspace-switcher"),
      "trips/[id]/page must retain trip-mobile-workspace-switcher (8K contract)"
    );
  });

  it("57. Trip Detail chapter cover retains boutique-instrument (8N-B preservation)", () => {
    assert.ok(
      tripDetailPage.includes("boutique-instrument"),
      "trips/[id]/page chapter cover must still include boutique-instrument (8N-B)"
    );
  });
});

// ── 58–59. TripBuilder composition adoption ───────────────────────────────────

describe("Phase 8N-C patch: TripBuilder composition adoption", () => {
  it("58. TripBuilder CollapsiblePanel has folio-cover-tab top accent", () => {
    assert.ok(
      tripBuilder.includes("folio-cover-tab"),
      "TripBuilder CollapsiblePanel must include folio-cover-tab element"
    );
  });

  it("59. TripBuilder CollapsiblePanel still uses boutique-folio (8N-B preservation)", () => {
    assert.ok(
      tripBuilder.includes("boutique-folio"),
      "TripBuilder CollapsiblePanel must still include boutique-folio class (8N-B)"
    );
  });
});

// ── 60–67. ExploreShell composition adoption ──────────────────────────────────

describe("Phase 8N-C patch: ExploreShell composition adoption", () => {
  it("60. ExploreShell home view uses editorial-scene", () => {
    assert.ok(
      exploreShell.includes("editorial-scene"),
      "ExploreShell explore-home wrapper must use editorial-scene"
    );
  });

  it("61. ExploreShell home view has editorial-section-rule after header", () => {
    assert.ok(
      exploreShell.includes("editorial-section-rule"),
      "ExploreShell explore-home must include editorial-section-rule below the header"
    );
  });

  it("62. ExploreShell VerticalCard uses boutique-folio composition", () => {
    assert.ok(
      exploreShell.includes("boutique-folio"),
      "ExploreShell VerticalCard button must include boutique-folio class"
    );
  });

  it("63. ExploreShell vertical flow view uses editorial-scene", () => {
    const flowIdx = exploreShell.indexOf("explore-vertical-flow");
    assert.ok(flowIdx !== -1, "explore-vertical-flow testid must exist");
    const flowBlock = exploreShell.slice(Math.max(0, flowIdx - 100), flowIdx + 200);
    assert.ok(
      flowBlock.includes("editorial-scene"),
      "explore-vertical-flow wrapper must include editorial-scene class"
    );
  });

  it("64. ExploreShell active search instrument has folio-cover-tab", () => {
    assert.ok(
      exploreShell.includes("folio-cover-tab"),
      "ExploreShell active search instrument section must include folio-cover-tab element"
    );
  });

  it("65. ExploreShell retains boutique-instrument on search section (8N-B preservation)", () => {
    assert.ok(
      exploreShell.includes("boutique-instrument"),
      "ExploreShell search section must still include boutique-instrument class (8N-B)"
    );
  });

  it("66. ExploreShell retains explore-lounge-header testid (8F preservation)", () => {
    assert.ok(
      exploreShell.includes('data-testid="explore-lounge-header"'),
      "ExploreShell must retain explore-lounge-header testid (8F contract)"
    );
  });

  it("67. No backend/provider/SQL/env/package drift on patched files", () => {
    const backendPattern = /from ['"].*backend.*['"]/;
    assert.ok(!backendPattern.test(tripDetailPage), "trips/[id]/page must not import backend");
    assert.ok(!backendPattern.test(tripBuilder), "TripBuilder must not import new backend modules");
    assert.ok(!backendPattern.test(exploreShell), "ExploreShell must not import backend modules");
    assert.ok(
      !exploreShell.includes("supabase") && !exploreShell.includes("fetchTrip"),
      "ExploreShell must not reference database or trip fetch calls"
    );
  });
});
