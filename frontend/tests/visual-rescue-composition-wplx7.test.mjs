/**
 * Stage 3.5 Visual Rescue — Screenshot-Led Composition Fix
 * Branch: claude/visual-rescue-composition-wplx7
 *
 * Verifies the five composition changes that address the screenshot-visible failures:
 *
 *  1.  folio-cinema-tile surface is materially brighter than cinema-deep background.
 *  2.  folio-cinema-tile has ::before brass top accent (new).
 *  3.  folio-cinema-tile has overflow:hidden (new, to contain ::before).
 *  4.  folio-cinema-tile brass border is stronger (0.26 vs prior 0.14).
 *  5.  folio-cinema-collection shell uses onyx-velvet (not cinema-deep).
 *  6.  folio-collection-card surface is materially brighter.
 *  7.  folio-collection-card ::before brass accent is stronger (0.60 peak vs 0.40).
 *  8.  folio-collection-card brass border is stronger (0.28 vs prior 0.16).
 *  9.  folio-home-cinema-card has ::before top brass rule (new).
 * 10.  folio-home-cinema-card brass border is stronger (0.20 vs prior 0.14).
 * 11.  folio-cinema-desk radial warmth is stronger (0.13 vs prior 0.09).
 * 12.  folio-concierge-chip CSS class defined in globals.css.
 * 13.  ConciergePage uses folio-concierge-chip class on prompt chips.
 * 14.  ConciergePage has no raw rgba() (pre-existing contract preserved).
 * 15.  ConciergePage prompt chips have data-testid="concierge-prompt-chip".
 * 16.  DashboardClient ContinuePlanningStrip overline uses text-ds-folio-ink-mist.
 * 17.  DashboardClient JourneyShelfTeaser overline uses text-ds-folio-ink-mist.
 * 18.  DashboardClient AtelierPlanningStrip overline uses text-ds-folio-ink-mist.
 * 19.  ExploreShell VerticalCard still uses folio-cinema-tile (unchanged).
 * 20.  SavedShell item card still uses folio-collection-card (unchanged).
 * 21.  SavedShell outer wrapper still uses folio-cinema-collection (unchanged).
 * 22.  ConciergePage main wrapper still uses folio-cinema-desk (unchanged).
 * 23.  PR #431 protected: addRoundTripLegToDay present in api.ts.
 * 24.  PR #431 protected: isExplicitlyOneWay present in ItineraryItemCard.
 * 25.  PR #431 protected: CityAutocomplete uses createPortal.
 * 26.  No backend imports added to any changed component.
 * 27.  folio-cinema-tile ::before respects border-radius (overflow:hidden set).
 * 28.  folio-collection-card ::before still present (not regressed).
 * 29.  folio-home-cinema-card still has overflow:hidden (pre-existing contract).
 * 30.  folio-concierge-chip :hover state defined.
 */

import { describe, it, test } from "node:test";
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
const itineraryCard   = readSrc("components/trips/ItineraryItemCard.tsx");
const apiTs           = readSrc("lib/api.ts");
const cityAuto        = readSrc("components/ui/CityAutocomplete.tsx");

// ── 1–4. folio-cinema-tile brightness fix (Discover) ─────────────────────────

describe("Visual Rescue: folio-cinema-tile brightness", () => {
  it("1. folio-cinema-tile surface uses brighter gradient (40,33,24 top)", () => {
    const idx = globalsCss.indexOf(".folio-cinema-tile {");
    assert.ok(idx !== -1, ".folio-cinema-tile must exist");
    const block = globalsCss.slice(idx, idx + 600);
    assert.ok(
      block.includes("40, 33, 24"),
      "folio-cinema-tile top gradient must be rgba(40,33,24) — brighter than prior rgba(28,24,20)"
    );
  });

  it("2. folio-cinema-tile has ::before brass top accent", () => {
    assert.ok(
      globalsCss.includes(".folio-cinema-tile::before"),
      "folio-cinema-tile must have ::before brass top accent (new in visual rescue)"
    );
  });

  it("3. folio-cinema-tile has overflow:hidden", () => {
    const idx = globalsCss.indexOf(".folio-cinema-tile {");
    assert.ok(idx !== -1, ".folio-cinema-tile must exist");
    const block = globalsCss.slice(idx, idx + 400);
    assert.ok(
      block.includes("overflow: hidden") || block.includes("overflow:hidden"),
      "folio-cinema-tile must have overflow:hidden to contain the ::before accent"
    );
  });

  it("4. folio-cinema-tile brass border is 0.26 (was 0.14)", () => {
    const idx = globalsCss.indexOf(".folio-cinema-tile {");
    assert.ok(idx !== -1);
    const block = globalsCss.slice(idx, idx + 400);
    assert.ok(
      block.includes("0.26"),
      "folio-cinema-tile border opacity must be 0.26 (materially stronger than prior 0.14)"
    );
  });
});

// ── 5–8. folio-cinema-collection / folio-collection-card (Saved) ─────────────

describe("Visual Rescue: Saved collection contrast", () => {
  it("5. folio-cinema-collection uses onyx-velvet (not cinema-deep)", () => {
    const idx = globalsCss.indexOf(".folio-cinema-collection {");
    assert.ok(idx !== -1, ".folio-cinema-collection must exist");
    const block = globalsCss.slice(idx, idx + 400);
    assert.ok(
      block.includes("var(--ds-onyx-velvet)"),
      "folio-cinema-collection must use onyx-velvet base — not cinema-deep — for card contrast"
    );
    assert.ok(
      !block.includes("var(--ds-cinema-deep)"),
      "folio-cinema-collection must NOT use cinema-deep (replaced with onyx-velvet)"
    );
  });

  it("6. folio-collection-card surface uses brighter gradient (44,37,28 top)", () => {
    const idx = globalsCss.indexOf(".folio-collection-card {");
    assert.ok(idx !== -1, ".folio-collection-card must exist");
    const block = globalsCss.slice(idx, idx + 400);
    assert.ok(
      block.includes("44, 37, 28"),
      "folio-collection-card top gradient must be rgba(44,37,28) — brighter than prior rgba(30,26,22)"
    );
  });

  it("7. folio-collection-card ::before peak opacity is 0.60 (was 0.40)", () => {
    const idx = globalsCss.indexOf(".folio-collection-card::before");
    assert.ok(idx !== -1, ".folio-collection-card::before must exist");
    const block = globalsCss.slice(idx, idx + 400);
    assert.ok(
      block.includes("0.60"),
      "folio-collection-card ::before peak brass opacity must be 0.60 (was 0.40)"
    );
  });

  it("8. folio-collection-card brass border is 0.28 (was 0.16)", () => {
    const idx = globalsCss.indexOf(".folio-collection-card {");
    assert.ok(idx !== -1);
    const block = globalsCss.slice(idx, idx + 400);
    assert.ok(
      block.includes("0.28"),
      "folio-collection-card border opacity must be 0.28 (was 0.16)"
    );
  });
});

// ── 9–10. folio-home-cinema-card editorial character (Home) ──────────────────

describe("Visual Rescue: Home cinema card editorial accent", () => {
  it("9. folio-home-cinema-card has ::before top brass rule", () => {
    assert.ok(
      globalsCss.includes(".folio-home-cinema-card::before"),
      "folio-home-cinema-card must have ::before for editorial brass top rule (new)"
    );
  });

  it("10. folio-home-cinema-card brass border is 0.20 (was 0.14)", () => {
    const idx = globalsCss.indexOf(".folio-home-cinema-card {");
    assert.ok(idx !== -1);
    const block = globalsCss.slice(idx, idx + 400);
    assert.ok(
      block.includes("0.20"),
      "folio-home-cinema-card border opacity must be 0.20 (stronger than prior 0.14)"
    );
  });
});

// ── 11. folio-cinema-desk warmer atmosphere (Concierge) ──────────────────────

describe("Visual Rescue: Concierge desk atmosphere", () => {
  it("11. folio-cinema-desk radial warmth is 0.13 (was 0.09)", () => {
    const idx = globalsCss.indexOf(".folio-cinema-desk {");
    assert.ok(idx !== -1, ".folio-cinema-desk must exist");
    const block = globalsCss.slice(idx, idx + 400);
    assert.ok(
      block.includes("0.13"),
      "folio-cinema-desk top radial must be 0.13 opacity (was 0.09)"
    );
  });
});

// ── 12–15. folio-concierge-chip (Concierge prompt chips) ─────────────────────

describe("Visual Rescue: Concierge prompt chip visibility", () => {
  it("12. folio-concierge-chip CSS class defined in globals.css", () => {
    assert.ok(
      globalsCss.includes(".folio-concierge-chip"),
      "globals.css must define .folio-concierge-chip for readable prompt chips"
    );
  });

  it("13. ConciergePage uses folio-concierge-chip class on prompt chips", () => {
    assert.ok(
      conciergePage.includes("folio-concierge-chip"),
      "ConciergePage must apply folio-concierge-chip to starter prompt chip buttons"
    );
  });

  it("14. ConciergePage has no raw rgba() (contract preserved)", () => {
    assert.ok(
      !conciergePage.includes("rgba("),
      "ConciergePage must not use raw rgba() — use CSS classes or ds-tokens"
    );
  });

  it("15. ConciergePage prompt chips have data-testid", () => {
    assert.ok(
      conciergePage.includes('data-testid="concierge-prompt-chip"'),
      "Starter prompt chips must have data-testid='concierge-prompt-chip'"
    );
  });

  it("30. folio-concierge-chip :hover state defined", () => {
    assert.ok(
      globalsCss.includes(".folio-concierge-chip:hover"),
      "folio-concierge-chip must define :hover state for interactive feedback"
    );
  });
});

// ── 16–18. DashboardClient overline paper legibility ─────────────────────────

describe("Visual Rescue: Home overline paper legibility", () => {
  it("16. ContinuePlanningStrip overline uses text-ds-folio-ink-mist", () => {
    assert.ok(
      dashboardClient.includes('text-ds-folio-ink-mist">Continue planning'),
      "ContinuePlanningStrip Overline must carry className text-ds-folio-ink-mist"
    );
  });

  it("17. JourneyShelfTeaser overline uses text-ds-folio-ink-mist", () => {
    assert.ok(
      dashboardClient.includes('text-ds-folio-ink-mist">Your travel shelf'),
      "JourneyShelfTeaser Overline must carry className text-ds-folio-ink-mist"
    );
  });

  it("18. AtelierPlanningStrip overline uses text-ds-folio-ink-mist", () => {
    assert.ok(
      dashboardClient.includes('text-ds-folio-ink-mist">Discovery tools'),
      "AtelierPlanningStrip Overline must carry className text-ds-folio-ink-mist"
    );
  });
});

// ── 19–22. Unchanged surface contracts ───────────────────────────────────────

describe("Visual Rescue: Surface class contracts preserved", () => {
  it("19. ExploreShell VerticalCard still uses folio-cinema-tile", () => {
    assert.ok(
      exploreShell.includes("folio-cinema-tile"),
      "ExploreShell VerticalCard must still use folio-cinema-tile"
    );
  });

  it("20. SavedShell item card still uses folio-collection-card", () => {
    assert.ok(
      savedShell.includes("folio-collection-card"),
      "SavedShell item card must still use folio-collection-card"
    );
  });

  it("21. SavedShell outer wrapper still uses folio-cinema-collection", () => {
    assert.ok(
      savedShell.includes("folio-cinema-collection"),
      "SavedShell outer wrapper must still use folio-cinema-collection"
    );
  });

  it("22. ConciergePage main wrapper still uses folio-cinema-desk", () => {
    assert.ok(
      conciergePage.includes("folio-cinema-desk"),
      "ConciergePage main wrapper must still use folio-cinema-desk"
    );
  });
});

// ── 23–25. PR #431 guard (must not be touched) ───────────────────────────────

describe("Visual Rescue: PR #431 logic paths protected", () => {
  it("23. addRoundTripLegToDay present in api.ts", () => {
    assert.ok(
      apiTs.includes("addRoundTripLegToDay"),
      "api.ts must still export addRoundTripLegToDay (PR #431 protected)"
    );
  });

  it("24. isExplicitlyOneWay check present in ItineraryItemCard", () => {
    assert.ok(
      itineraryCard.includes("isExplicitlyOneWay"),
      "ItineraryItemCard must still contain isExplicitlyOneWay round-trip detection"
    );
  });

  it("25. CityAutocomplete uses createPortal", () => {
    assert.ok(
      cityAuto.includes("createPortal"),
      "CityAutocomplete must still use createPortal for dropdown (PR #431 protected)"
    );
  });
});

// ── 26–29. Sanity + regression guards ────────────────────────────────────────

describe("Visual Rescue: Sanity and regression guards", () => {
  it("26. No backend imports added to changed components", () => {
    for (const [name, src] of [
      ["DashboardClient", dashboardClient],
      ["ExploreShell", exploreShell],
      ["SavedShell", savedShell],
      ["ConciergePage", conciergePage],
    ]) {
      assert.ok(
        !src.includes("from '@/backend'") && !src.includes("from '../backend'"),
        `${name} must not import from backend`
      );
    }
  });

  it("27. folio-cinema-tile overflow:hidden ensures ::before is contained", () => {
    const tileIdx  = globalsCss.indexOf(".folio-cinema-tile {");
    const beforeIdx = globalsCss.indexOf(".folio-cinema-tile::before");
    assert.ok(tileIdx !== -1 && beforeIdx !== -1);
    const tileBlock = globalsCss.slice(tileIdx, tileIdx + 400);
    assert.ok(
      tileBlock.includes("overflow: hidden") || tileBlock.includes("overflow:hidden"),
      "folio-cinema-tile must have overflow:hidden before its ::before is declared"
    );
  });

  it("28. folio-collection-card ::before still present (not regressed)", () => {
    assert.ok(
      globalsCss.includes(".folio-collection-card::before"),
      "folio-collection-card::before must still exist (not accidentally removed)"
    );
  });

  it("29. folio-home-cinema-card still has overflow:hidden (pre-existing contract)", () => {
    const idx = globalsCss.indexOf(".folio-home-cinema-card {");
    assert.ok(idx !== -1);
    const block = globalsCss.slice(idx, idx + 700);
    assert.ok(
      block.includes("overflow: hidden") || block.includes("overflow:hidden"),
      "folio-home-cinema-card must still have overflow:hidden (Slice 4B contract)"
    );
  });
});
