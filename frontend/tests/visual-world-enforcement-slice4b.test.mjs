/**
 * Stage 3.5 Slice 4B — Visual World Enforcement contract tests.
 *
 * Verifies that each cinema-world surface now uses a single intentional
 * visual composition instead of additive class stacking.
 *
 *  1.  globals.css defines .folio-cinema-lounge (Discover lounge shell).
 *  2.  globals.css defines .folio-cinema-tile (Discover destination tile).
 *  3.  globals.css defines .folio-cinema-collection (Saved collection shell).
 *  4.  globals.css defines .folio-collection-card (Saved collection card).
 *  5.  globals.css defines .folio-cinema-desk (Concierge desk atmosphere).
 *  6.  globals.css defines .folio-cinema-composer (Concierge composer panel).
 *  7.  globals.css defines .folio-home-cinema-card (Home cinema cards).
 *  8.  folio-cinema-lounge uses warm dark base (not pure black).
 *  9.  folio-cinema-lounge has radial-gradient warmth (not flat surface).
 * 10.  folio-cinema-tile has brass hairline border (rgba 197,148,77).
 * 11.  folio-cinema-tile has hover state defined.
 * 12.  folio-collection-card has ::before brass top accent defined.
 * 13.  folio-cinema-composer has position:relative (z-index management).
 * 14.  folio-home-cinema-card has overflow:hidden.
 * 15.  ExploreShell explore-home wrapper uses folio-cinema-lounge.
 * 16.  ExploreShell explore-vertical-flow wrapper uses folio-cinema-lounge.
 * 17.  ExploreShell VerticalCard uses folio-cinema-tile (not additive stack).
 * 18.  ExploreShell does NOT use editorial-scene (additive class removed).
 * 19.  ExploreShell does NOT use boutique-folio on VerticalCard.
 * 20.  ExploreShell explore-lounge-header testid preserved.
 * 21.  ExploreShell explore-vertical-grid testid preserved.
 * 22.  SavedShell outer wrapper uses folio-cinema-collection.
 * 23.  SavedShell does NOT use saved-clipping-desk (replaced).
 * 24.  SavedShell item card uses folio-collection-card.
 * 25.  SavedShell does NOT use saved-folio-card (replaced).
 * 26.  SavedShell saved-scrapbook-header testid preserved.
 * 27.  SavedShell saved-planning-bridge testid preserved.
 * 28.  ConciergePage main wrapper uses folio-cinema-desk.
 * 29.  ConciergePage does NOT use editorial-scene on main wrapper.
 * 30.  ConciergePage composer uses folio-cinema-composer.
 * 31.  ConciergePage does NOT use boutique-instrument on composer.
 * 32.  ConciergePage concierge-instrument-composer testid preserved.
 * 33.  ConciergePage folio-cinema-result-card still present (untouched).
 * 34.  DashboardClient ContinuePlanningStrip uses folio-home-cinema-card.
 * 35.  DashboardClient ContinuePlanningStrip does NOT use tone="dark" Card.
 * 36.  DashboardClient JourneyShelfTeaser link uses folio-home-cinema-card.
 * 37.  DashboardClient AtelierPlanningStrip links use folio-home-cinema-card.
 * 38.  DashboardClient strip links do NOT use bg-ds-onyx + atelier-surface-depth stack.
 * 39.  DashboardClient EmptyAtelierHome h2 uses text-ds-folio-ink (NOT text-ds-text).
 * 40.  DashboardClient EmptyAtelierHome p uses text-ds-folio-ink-mist (NOT text-ds-text-tertiary).
 * 41.  DashboardClient no longer imports Card component (unused after Slice 4B).
 * 42.  TripBuilder Planning overline uses text-ds-folio-ink-mist (NOT text-ds-text-tertiary).
 * 43.  TripBuilder destination uses text-ds-folio-ink (NOT text-ds-text in Planning header).
 * 44.  TripBuilder Day number uses text-ds-marine-ink (NOT text-ds-accent in Planning header).
 * 45.  PR #431 protected: addRoundTripLegToDay present in api.ts.
 * 46.  PR #431 protected: isExplicitlyOneWay check present in ItineraryItemCard.
 * 47.  PR #431 protected: CityAutocomplete uses createPortal.
 * 48.  No text-ds-warm-paper in any changed file (invalid Tailwind utility).
 * 49.  No pure black (#000000) in any new enforcement class definitions.
 * 50.  No backend imports added to cinema-world components.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root    = resolve(__dirname, "..");
const srcRoot = resolve(root, "src");

function readSrc(relPath) {
  return readFileSync(resolve(srcRoot, relPath), "utf8");
}

const globalsCss      = readSrc("app/globals.css");
const exploreShell    = readSrc("components/explore/ExploreShell.tsx");
const savedShell      = readSrc("components/saved/SavedShell.tsx");
const conciergePage   = readSrc("components/concierge/ConciergePage.tsx");
const dashboardClient = readSrc("components/dashboard/DashboardClient.tsx");
const tripBuilder     = readSrc("components/trips/TripBuilder.tsx");
const itineraryCard   = readSrc("components/trips/ItineraryItemCard.tsx");
const apiTs           = readSrc("lib/api.ts");
const cityAuto        = readSrc("components/ui/CityAutocomplete.tsx");

// ── 1–7. New enforcement primitives defined ───────────────────────────────────

describe("Slice 4B: Enforcement primitives defined in globals.css", () => {
  it("1. globals.css defines .folio-cinema-lounge", () => {
    assert.ok(
      globalsCss.includes(".folio-cinema-lounge"),
      "globals.css must define .folio-cinema-lounge for contained cinematic lounge shell"
    );
  });

  it("2. globals.css defines .folio-cinema-tile", () => {
    assert.ok(
      globalsCss.includes(".folio-cinema-tile"),
      "globals.css must define .folio-cinema-tile for destination discovery tile"
    );
  });

  it("3. globals.css defines .folio-cinema-collection", () => {
    assert.ok(
      globalsCss.includes(".folio-cinema-collection"),
      "globals.css must define .folio-cinema-collection for curated Saved collection shell"
    );
  });

  it("4. globals.css defines .folio-collection-card", () => {
    assert.ok(
      globalsCss.includes(".folio-collection-card"),
      "globals.css must define .folio-collection-card for individual Saved collection card"
    );
  });

  it("5. globals.css defines .folio-cinema-desk", () => {
    assert.ok(
      globalsCss.includes(".folio-cinema-desk"),
      "globals.css must define .folio-cinema-desk for Concierge private desk atmosphere"
    );
  });

  it("6. globals.css defines .folio-cinema-composer", () => {
    assert.ok(
      globalsCss.includes(".folio-cinema-composer"),
      "globals.css must define .folio-cinema-composer for Concierge sticky composer panel"
    );
  });

  it("7. globals.css defines .folio-home-cinema-card", () => {
    assert.ok(
      globalsCss.includes(".folio-home-cinema-card"),
      "globals.css must define .folio-home-cinema-card for Home page cinematic cards"
    );
  });
});

// ── 8–14. Enforcement primitive visual properties ─────────────────────────────

describe("Slice 4B: Enforcement primitive visual properties", () => {
  it("8. folio-cinema-lounge uses warm dark base (not pure black)", () => {
    const idx = globalsCss.indexOf(".folio-cinema-lounge");
    assert.ok(idx !== -1, ".folio-cinema-lounge must exist");
    const block = globalsCss.slice(idx, idx + 400);
    assert.ok(
      !block.includes("background-color: #000000") && !block.includes("background-color: black"),
      "folio-cinema-lounge must NOT use pure black — must use warm dark base"
    );
    assert.ok(
      block.includes("background-color"),
      "folio-cinema-lounge must declare an explicit background-color"
    );
  });

  it("9. folio-cinema-lounge has radial-gradient warmth (not flat surface)", () => {
    const idx = globalsCss.indexOf(".folio-cinema-lounge");
    assert.ok(idx !== -1, ".folio-cinema-lounge must exist");
    const block = globalsCss.slice(idx, idx + 600);
    assert.ok(
      block.includes("radial-gradient"),
      "folio-cinema-lounge must use radial-gradient for ambient warmth (not flat dark)"
    );
  });

  it("10. folio-cinema-tile has brass hairline border (rgba 197,148,77)", () => {
    const idx = globalsCss.indexOf(".folio-cinema-tile");
    assert.ok(idx !== -1, ".folio-cinema-tile must exist");
    const block = globalsCss.slice(idx, idx + 500);
    assert.ok(
      block.includes("197") && block.includes("148") && block.includes("77"),
      "folio-cinema-tile must have a brass hairline border (rgba 197,148,77 palette)"
    );
  });

  it("11. folio-cinema-tile has hover state defined", () => {
    assert.ok(
      globalsCss.includes(".folio-cinema-tile:hover"),
      "folio-cinema-tile must define a :hover state for interactive lift"
    );
  });

  it("12. folio-collection-card has ::before brass top accent", () => {
    assert.ok(
      globalsCss.includes(".folio-collection-card::before"),
      "folio-collection-card must have ::before pseudo-element for brass top accent"
    );
  });

  it("13. folio-cinema-composer has position:relative", () => {
    const idx = globalsCss.indexOf(".folio-cinema-composer {");
    assert.ok(idx !== -1, ".folio-cinema-composer block must exist");
    const block = globalsCss.slice(idx, idx + 200);
    assert.ok(
      block.includes("position: relative"),
      "folio-cinema-composer must declare position:relative for z-index management"
    );
  });

  it("14. folio-home-cinema-card has overflow:hidden", () => {
    const idx = globalsCss.indexOf(".folio-home-cinema-card {");
    assert.ok(idx !== -1, ".folio-home-cinema-card block must exist");
    const block = globalsCss.slice(idx, idx + 700);
    assert.ok(
      block.includes("overflow: hidden") || block.includes("overflow:hidden"),
      "folio-home-cinema-card must have overflow:hidden for accent containment"
    );
  });
});

// ── 15–21. ExploreShell visual enforcement ────────────────────────────────────

describe("Slice 4B: ExploreShell visual enforcement", () => {
  it("15. explore-home wrapper uses folio-cinema-lounge", () => {
    const homeIdx = exploreShell.indexOf('data-testid="explore-home"');
    assert.ok(homeIdx !== -1, "explore-home testid must exist");
    const homeCtx = exploreShell.slice(Math.max(0, homeIdx - 150), homeIdx + 30);
    assert.ok(
      homeCtx.includes("folio-cinema-lounge"),
      "explore-home wrapper must use folio-cinema-lounge (not additive editorial-scene folio-cinema-shell stack)"
    );
  });

  it("16. explore-vertical-flow wrapper uses folio-cinema-lounge", () => {
    const flowIdx = exploreShell.indexOf('data-testid="explore-vertical-flow"');
    assert.ok(flowIdx !== -1, "explore-vertical-flow testid must exist");
    const flowCtx = exploreShell.slice(Math.max(0, flowIdx - 150), flowIdx + 30);
    assert.ok(
      flowCtx.includes("folio-cinema-lounge"),
      "explore-vertical-flow wrapper must use folio-cinema-lounge"
    );
  });

  it("17. ExploreShell VerticalCard uses folio-cinema-tile", () => {
    assert.ok(
      exploreShell.includes("folio-cinema-tile"),
      "ExploreShell VerticalCard must use folio-cinema-tile (single intentional composition)"
    );
  });

  it("18. ExploreShell does NOT use editorial-scene (additive class removed)", () => {
    assert.ok(
      !exploreShell.includes("editorial-scene"),
      "ExploreShell must NOT use editorial-scene — it has been replaced by folio-cinema-lounge (Slice 4B)"
    );
  });

  it("19. ExploreShell VerticalCard does NOT use boutique-folio (additive class removed)", () => {
    assert.ok(
      !exploreShell.includes("boutique-folio"),
      "ExploreShell VerticalCard must NOT use boutique-folio — replaced by folio-cinema-tile (Slice 4B)"
    );
  });

  it("20. ExploreShell explore-lounge-header testid preserved", () => {
    assert.ok(
      exploreShell.includes('data-testid="explore-lounge-header"'),
      "ExploreShell must retain explore-lounge-header testid (8F contract)"
    );
  });

  it("21. ExploreShell explore-vertical-grid testid preserved", () => {
    assert.ok(
      exploreShell.includes('data-testid="explore-vertical-grid"'),
      "ExploreShell must retain explore-vertical-grid testid"
    );
  });
});

// ── 22–27. SavedShell visual enforcement ─────────────────────────────────────

describe("Slice 4B: SavedShell visual enforcement", () => {
  it("22. SavedShell outer wrapper uses folio-cinema-collection", () => {
    assert.ok(
      savedShell.includes("folio-cinema-collection"),
      "SavedShell outer wrapper must use folio-cinema-collection (curated collection shell)"
    );
  });

  it("23. SavedShell does NOT use saved-clipping-desk (replaced by folio-cinema-collection)", () => {
    assert.ok(
      !savedShell.includes("saved-clipping-desk"),
      "SavedShell must NOT use saved-clipping-desk — replaced by folio-cinema-collection (Slice 4B)"
    );
  });

  it("24. SavedShell item card uses folio-collection-card", () => {
    assert.ok(
      savedShell.includes("folio-collection-card"),
      "SavedShell SavedItemCard must use folio-collection-card (single intentional card composition)"
    );
  });

  it("25. SavedShell does NOT use saved-folio-card (replaced by folio-collection-card)", () => {
    assert.ok(
      !savedShell.includes("saved-folio-card"),
      "SavedShell must NOT use saved-folio-card — replaced by folio-collection-card (Slice 4B)"
    );
  });

  it("26. SavedShell saved-scrapbook-header testid preserved", () => {
    assert.ok(
      savedShell.includes('data-testid="saved-scrapbook-header"'),
      "SavedShell must retain saved-scrapbook-header testid (8G contract)"
    );
  });

  it("27. SavedShell saved-planning-bridge testid preserved", () => {
    assert.ok(
      savedShell.includes('data-testid="saved-planning-bridge"'),
      "SavedShell must retain saved-planning-bridge testid (8G contract)"
    );
  });
});

// ── 28–33. ConciergePage visual enforcement ───────────────────────────────────

describe("Slice 4B: ConciergePage visual enforcement", () => {
  it("28. ConciergePage main wrapper uses folio-cinema-desk", () => {
    assert.ok(
      conciergePage.includes("folio-cinema-desk"),
      "ConciergePage main wrapper must use folio-cinema-desk (private desk atmosphere)"
    );
  });

  it("29. ConciergePage does NOT use editorial-scene (additive class removed from main wrapper)", () => {
    assert.ok(
      !conciergePage.includes("editorial-scene"),
      "ConciergePage must NOT use editorial-scene — replaced by folio-cinema-desk (Slice 4B)"
    );
  });

  it("30. ConciergePage composer uses folio-cinema-composer", () => {
    assert.ok(
      conciergePage.includes("folio-cinema-composer"),
      "ConciergePage sticky composer must use folio-cinema-composer (single intentional composition)"
    );
  });

  it("31. ConciergePage composer does NOT use boutique-instrument (additive class removed)", () => {
    const composerIdx = conciergePage.indexOf("concierge-instrument-composer");
    assert.ok(composerIdx !== -1, "concierge-instrument-composer testid must exist");
    const composerCtx = conciergePage.slice(Math.max(0, composerIdx - 200), composerIdx + 50);
    assert.ok(
      !composerCtx.includes("boutique-instrument"),
      "ConciergePage composer must NOT use boutique-instrument — replaced by folio-cinema-composer (Slice 4B)"
    );
  });

  it("32. ConciergePage concierge-instrument-composer testid preserved", () => {
    assert.ok(
      conciergePage.includes('data-testid="concierge-instrument-composer"'),
      "ConciergePage must retain concierge-instrument-composer testid"
    );
  });

  it("33. ConciergePage folio-cinema-result-card still present (untouched in Slice 4B)", () => {
    assert.ok(
      conciergePage.includes("folio-cinema-result-card"),
      "ConciergePage ConciergeResultCard must retain folio-cinema-result-card (Slice 4 contract — not touched in 4B)"
    );
  });
});

// ── 34–41. DashboardClient visual enforcement ─────────────────────────────────

describe("Slice 4B: DashboardClient visual enforcement", () => {
  it("34. ContinuePlanningStrip uses folio-home-cinema-card", () => {
    const sectionIdx = dashboardClient.indexOf("atelier-continue-planning");
    assert.ok(sectionIdx !== -1, "atelier-continue-planning testid must exist");
    const sectionCtx = dashboardClient.slice(sectionIdx, sectionIdx + 300);
    assert.ok(
      sectionCtx.includes("folio-home-cinema-card"),
      "ContinuePlanningStrip must use folio-home-cinema-card (replaced dark Card)"
    );
  });

  it("35. ContinuePlanningStrip does NOT use Card tone=dark or atelier-surface-depth", () => {
    const sectionIdx = dashboardClient.indexOf("atelier-continue-planning");
    assert.ok(sectionIdx !== -1, "atelier-continue-planning testid must exist");
    const sectionCtx = dashboardClient.slice(sectionIdx, sectionIdx + 300);
    assert.ok(
      !sectionCtx.includes('tone="dark"') && !sectionCtx.includes("atelier-surface-depth"),
      "ContinuePlanningStrip must NOT use Card tone=dark or atelier-surface-depth (Slice 4B replaced)"
    );
  });

  it("36. JourneyShelfTeaser link uses folio-home-cinema-card", () => {
    const shelfIdx = dashboardClient.indexOf("journey-shelf-teaser");
    assert.ok(shelfIdx !== -1, "journey-shelf-teaser testid must exist");
    const shelfCtx = dashboardClient.slice(shelfIdx, shelfIdx + 1000);
    assert.ok(
      shelfCtx.includes("folio-home-cinema-card"),
      "JourneyShelfTeaser shelf link must use folio-home-cinema-card"
    );
  });

  it("37. AtelierPlanningStrip links use folio-home-cinema-card", () => {
    const stripIdx = dashboardClient.indexOf("atelier-planning-strip");
    assert.ok(stripIdx !== -1, "atelier-planning-strip testid must exist");
    const stripCtx = dashboardClient.slice(stripIdx, stripIdx + 1400);
    const count = (stripCtx.match(/folio-home-cinema-card/g) || []).length;
    assert.ok(
      count >= 2,
      `AtelierPlanningStrip must have at least 2 folio-home-cinema-card links (Explore + Saved Ideas), found ${count}`
    );
  });

  it("38. Strip link cards do NOT use bg-ds-onyx + atelier-surface-depth stack", () => {
    const stripIdx = dashboardClient.indexOf("atelier-planning-strip");
    assert.ok(stripIdx !== -1, "atelier-planning-strip testid must exist");
    const stripCtx = dashboardClient.slice(stripIdx, stripIdx + 800);
    assert.ok(
      !stripCtx.includes("atelier-surface-depth"),
      "AtelierPlanningStrip link cards must NOT use atelier-surface-depth (Slice 4B replaced)"
    );
  });

  it("39. EmptyAtelierHome h2 uses text-ds-folio-ink (NOT text-ds-text)", () => {
    const emptyIdx = dashboardClient.indexOf("atelier-empty-state");
    assert.ok(emptyIdx !== -1, "atelier-empty-state testid must exist");
    const emptyCtx = dashboardClient.slice(emptyIdx, emptyIdx + 600);
    assert.ok(
      emptyCtx.includes("text-ds-folio-ink"),
      "EmptyAtelierHome h2 must use text-ds-folio-ink for legibility on paper background"
    );
    const h2Match = emptyCtx.match(/<h2[^>]*text-ds-text[^-]/);
    assert.ok(
      !h2Match,
      "EmptyAtelierHome h2 must NOT use text-ds-text (cream invisible on paper) — use text-ds-folio-ink"
    );
  });

  it("40. EmptyAtelierHome p uses text-ds-folio-ink-mist (NOT text-ds-text-tertiary)", () => {
    const emptyIdx = dashboardClient.indexOf("atelier-empty-state");
    assert.ok(emptyIdx !== -1, "atelier-empty-state testid must exist");
    const emptyCtx = dashboardClient.slice(emptyIdx, emptyIdx + 600);
    assert.ok(
      emptyCtx.includes("text-ds-folio-ink-mist"),
      "EmptyAtelierHome p must use text-ds-folio-ink-mist for readable muted text on paper"
    );
    const pMatch = emptyCtx.match(/<p[^>]*text-ds-text-tertiary[^"]/);
    assert.ok(
      !pMatch,
      "EmptyAtelierHome p must NOT use text-ds-text-tertiary (low contrast on paper) — use text-ds-folio-ink-mist"
    );
  });

  it("41. DashboardClient no longer imports Card component (unused after Slice 4B)", () => {
    assert.ok(
      !dashboardClient.includes("from \"@/components/ui/Card\"") &&
      !dashboardClient.includes("from '@/components/ui/Card'"),
      "DashboardClient must NOT import Card — it was removed when ContinuePlanningStrip switched to folio-home-cinema-card"
    );
  });
});

// ── 42–44. TripBuilder paper world enforcement (Scope A) ─────────────────────

describe("Slice 4B: TripBuilder Planning header paper tokens", () => {
  it("42. Planning overline uses text-ds-folio-ink-mist (NOT text-ds-text-tertiary)", () => {
    const planningIdx = tripBuilder.indexOf("Planning cockpit context header");
    assert.ok(planningIdx !== -1, "Planning cockpit context header comment must exist in TripBuilder");
    const planningCtx = tripBuilder.slice(planningIdx, planningIdx + 400);
    assert.ok(
      planningCtx.includes("text-ds-folio-ink-mist"),
      "TripBuilder Planning overline must use text-ds-folio-ink-mist (readable on paper background)"
    );
    assert.ok(
      !planningCtx.includes("text-ds-text-tertiary"),
      "TripBuilder Planning overline must NOT use text-ds-text-tertiary (cream/mist, invisible on paper)"
    );
  });

  it("43. Planning destination uses text-ds-folio-ink (NOT text-ds-text)", () => {
    const planningIdx = tripBuilder.indexOf("Planning cockpit context header");
    assert.ok(planningIdx !== -1, "Planning cockpit context header comment must exist in TripBuilder");
    const planningCtx = tripBuilder.slice(planningIdx, planningIdx + 400);
    assert.ok(
      planningCtx.includes("text-ds-folio-ink"),
      "TripBuilder Planning destination must use text-ds-folio-ink (readable on paper background)"
    );
    const textDsTextMatch = planningCtx.match(/text-ds-text[^-\w]/);
    assert.ok(
      !textDsTextMatch,
      "TripBuilder Planning header must NOT use text-ds-text (cream on paper = invisible)"
    );
  });

  it("44. Planning Day number uses text-ds-marine-ink (NOT text-ds-accent)", () => {
    const planningIdx = tripBuilder.indexOf("Planning cockpit context header");
    assert.ok(planningIdx !== -1, "Planning cockpit context header comment must exist in TripBuilder");
    const planningCtx = tripBuilder.slice(planningIdx, planningIdx + 700);
    assert.ok(
      planningCtx.includes("text-ds-marine-ink"),
      "TripBuilder Planning Day number must use text-ds-marine-ink (readable on paper background)"
    );
  });
});

// ── 45–47. PR #431 protected paths ───────────────────────────────────────────

describe("Slice 4B: PR #431 protected paths untouched", () => {
  it("45. addRoundTripLegToDay present in api.ts (PR #431 protection)", () => {
    assert.ok(
      apiTs.includes("addRoundTripLegToDay"),
      "api.ts must retain addRoundTripLegToDay function (PR #431 protected path)"
    );
  });

  it("46. isExplicitlyOneWay check present in ItineraryItemCard (PR #431 protection)", () => {
    assert.ok(
      itineraryCard.includes("isExplicitlyOneWay") || itineraryCard.includes("one_way"),
      "ItineraryItemCard must retain round-trip/one-way detection logic (PR #431 protected)"
    );
  });

  it("47. CityAutocomplete uses createPortal (PR #431 protection)", () => {
    assert.ok(
      cityAuto.includes("createPortal"),
      "CityAutocomplete must retain createPortal portal rendering (PR #431 protected path)"
    );
  });
});

// ── 48–50. Safety invariants ──────────────────────────────────────────────────

describe("Slice 4B: Safety invariants", () => {
  it("48. No text-ds-warm-paper in any changed file (invalid Tailwind utility)", () => {
    const files = { exploreShell, savedShell, conciergePage, dashboardClient, tripBuilder };
    for (const [name, content] of Object.entries(files)) {
      assert.ok(
        !content.includes("text-ds-warm-paper"),
        `${name} must not use text-ds-warm-paper — it is an invalid Tailwind utility`
      );
    }
  });

  it("49. No pure black (#000000) in new enforcement class definitions", () => {
    const classes = [
      ".folio-cinema-lounge",
      ".folio-cinema-tile",
      ".folio-cinema-collection",
      ".folio-collection-card",
      ".folio-cinema-desk",
      ".folio-cinema-composer",
      ".folio-home-cinema-card",
    ];
    for (const cls of classes) {
      const idx = globalsCss.indexOf(cls);
      if (idx === -1) continue;
      const block = globalsCss.slice(idx, idx + 600);
      assert.ok(
        !block.includes("background-color: #000000") && !block.includes("background-color: black"),
        `${cls} must NOT use pure black (#000000) — use warm umber dark`
      );
    }
  });

  it("50. No backend imports added to cinema-world components", () => {
    const backendPattern = /from ['"].*backend.*['"]/;
    assert.ok(!backendPattern.test(conciergePage),   "ConciergePage must not import backend modules");
    assert.ok(!backendPattern.test(exploreShell),    "ExploreShell must not import backend modules");
    assert.ok(!backendPattern.test(savedShell),      "SavedShell must not import backend modules");
    assert.ok(!backendPattern.test(dashboardClient), "DashboardClient must not import backend modules");
  });
});
