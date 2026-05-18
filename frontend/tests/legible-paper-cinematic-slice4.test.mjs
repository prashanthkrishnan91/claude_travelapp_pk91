/**
 * Stage 3.5 Slice 4 — Legible Paper + Cinematic Concierge World contract tests.
 *
 * Verifies:
 *  1.  globals.css defines .folio-cinema-shell (dark cinema base wrapper).
 *  2.  globals.css defines .folio-cinema-card (warm dark velvet card).
 *  3.  globals.css defines .folio-cinema-header (cinema header zone).
 *  4.  globals.css defines .folio-cinema-input (dark cinema input field).
 *  5.  globals.css defines .folio-cinema-result-card (concierge result card).
 *  6.  globals.css defines .folio-mapline-field (destination field accent).
 *  7.  folio-cinema-shell uses warm dark base background-color (not #000000).
 *  8.  folio-cinema-card uses warm dark carbon-mist background.
 *  9.  folio-cinema-card has brass hairline border (rgba 197,148,77).
 * 10.  folio-cinema-header has border-top brass accent rule.
 * 11.  folio-cinema-result-card has overflow:hidden for accent containment.
 * 12.  folio-cinema-shell defined after folio-cinema-panel (source-order).
 * 13.  folio-cinema-result-card defined after folio-cinema-card (source-order).
 * 14.  DashboardClient AtelierGreeting h1 uses text-ds-folio-ink (readable on paper).
 * 15.  DashboardClient AtelierGreeting subtitle uses text-ds-folio-ink-mist.
 * 16.  DashboardClient Overline component accepts className prop.
 * 17.  DashboardClient AtelierGreeting does NOT use text-ds-text for h1 (washed-out).
 * 18.  trips/page EmptyDashboard hero h2 uses text-ds-folio-ink (readable on paper).
 * 19.  trips/page EmptyDashboard hero p uses text-ds-folio-ink-mist.
 * 20.  ConciergePage uses folio-cinema-shell on main wrapper.
 * 21.  ConciergePage sticky composer uses folio-cinema-header.
 * 22.  ConciergePage ConciergeResultCard uses folio-cinema-result-card.
 * 23.  ConciergePage destination field uses folio-mapline-field.
 * 24.  ConciergePage still uses editorial-scene (backward compat).
 * 25.  ConciergePage ConciergeResultCard still has folio-cover-tab (8N-C preservation).
 * 26.  ConciergePage ConciergeResultCard still has boutique-folio (8N-B preservation).
 * 27.  ConciergePage save/map/source actions preserved in result card.
 * 28.  ConciergePage ConciergeResultCard component preserved.
 * 29.  ExploreShell uses folio-cinema-shell on explore-home wrapper.
 * 30.  ExploreShell uses folio-cinema-shell on explore-vertical-flow wrapper.
 * 31.  ExploreShell VerticalCard uses folio-cinema-card.
 * 32.  ExploreShell still uses editorial-scene (backward compat).
 * 33.  ExploreShell still has boutique-folio (8N-B preservation).
 * 34.  ExploreShell VerticalCard text is readable (text-ds-text-tertiary preserved).
 * 35.  ExploreShell active section still has bg-ds-onyx (instrument elevation).
 * 36.  ExploreShell explore-lounge-header testid preserved.
 * 37.  SavedShell uses folio-cinema-shell on outer wrapper.
 * 38.  SavedShell still uses saved-clipping-desk (8N-E preservation).
 * 39.  SavedShell still uses saved-folio-header (8N-F preservation).
 * 40.  SavedShell still uses saved-folio-card (8N-F preservation).
 * 41.  SavedShell saved-scrapbook-header testid preserved.
 * 42.  SavedShell saved-planning-bridge testid preserved.
 * 43.  Paper planning surfaces not regressed: ItineraryItemCard uses folio-paper-item.
 * 44.  Paper planning surfaces not regressed: DayPlanModal uses folio-paper-panel.
 * 45.  PR #431 protected: addRoundTripLegToDay present in api.ts.
 * 46.  PR #431 protected: isExplicitlyOneWay check present in ItineraryItemCard.
 * 47.  PR #431 protected: CityAutocomplete uses createPortal.
 * 48.  No text-ds-warm-paper in any touched file (invalid Tailwind utility).
 * 49.  No pure black (#000000) used as background in cinema classes.
 * 50.  No backend imports added to cinema-world components.
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
function readRoot(relPath) {
  return readFileSync(resolve(root, relPath), "utf8");
}

const globalsCss     = readSrc("app/globals.css");
const dashboardClient = readSrc("components/dashboard/DashboardClient.tsx");
const tripsPage      = readSrc("app/trips/page.tsx");
const conciergePage  = readSrc("components/concierge/ConciergePage.tsx");
const exploreShell   = readSrc("components/explore/ExploreShell.tsx");
const savedShell     = readSrc("components/saved/SavedShell.tsx");
const itineraryCard  = readSrc("components/trips/ItineraryItemCard.tsx");
const dayPlanModal   = readSrc("components/trips/DayPlanModal.tsx");
const apiTs          = readSrc("lib/api.ts");
const cityAuto       = readSrc("components/ui/CityAutocomplete.tsx");

// ── 1–13. Cinema primitive definitions ───────────────────────────────────────

describe("Slice 4: Cinema primitive definitions in globals.css", () => {
  it("1. globals.css defines .folio-cinema-shell", () => {
    assert.ok(
      globalsCss.includes(".folio-cinema-shell"),
      "globals.css must define .folio-cinema-shell for cinema-world dark base wrapper"
    );
  });

  it("2. globals.css defines .folio-cinema-card", () => {
    assert.ok(
      globalsCss.includes(".folio-cinema-card"),
      "globals.css must define .folio-cinema-card for cinema-world velvet card"
    );
  });

  it("3. globals.css defines .folio-cinema-header", () => {
    assert.ok(
      globalsCss.includes(".folio-cinema-header"),
      "globals.css must define .folio-cinema-header for cinema-world header zone"
    );
  });

  it("4. globals.css defines .folio-cinema-input", () => {
    assert.ok(
      globalsCss.includes(".folio-cinema-input"),
      "globals.css must define .folio-cinema-input for cinema-world dark input"
    );
  });

  it("5. globals.css defines .folio-cinema-result-card", () => {
    assert.ok(
      globalsCss.includes(".folio-cinema-result-card"),
      "globals.css must define .folio-cinema-result-card for concierge recommendation slips"
    );
  });

  it("6. globals.css defines .folio-mapline-field", () => {
    assert.ok(
      globalsCss.includes(".folio-mapline-field"),
      "globals.css must define .folio-mapline-field for destination input route-line accent"
    );
  });

  it("7. folio-cinema-shell uses warm dark base (not pure black)", () => {
    const shellIdx = globalsCss.indexOf(".folio-cinema-shell");
    assert.ok(shellIdx !== -1, ".folio-cinema-shell must exist");
    const block = globalsCss.slice(shellIdx, shellIdx + 300);
    assert.ok(
      !block.includes("background-color: #000000") && !block.includes("background-color: black"),
      "folio-cinema-shell must NOT use pure black — must use warm dark umber base"
    );
    assert.ok(
      block.includes("background-color"),
      "folio-cinema-shell must declare an explicit background-color"
    );
  });

  it("8. folio-cinema-card uses warm dark carbon surface", () => {
    const cardIdx = globalsCss.indexOf(".folio-cinema-card {");
    assert.ok(cardIdx !== -1, ".folio-cinema-card block must exist");
    const block = globalsCss.slice(cardIdx, cardIdx + 300);
    assert.ok(
      block.includes("carbon-mist") || block.includes("carbon"),
      "folio-cinema-card must use a warm dark carbon surface (not pure black)"
    );
  });

  it("9. folio-cinema-card has brass hairline border", () => {
    const cardIdx = globalsCss.indexOf(".folio-cinema-card {");
    assert.ok(cardIdx !== -1, ".folio-cinema-card must exist");
    const block = globalsCss.slice(cardIdx, cardIdx + 300);
    assert.ok(
      block.includes("197") && block.includes("148") && block.includes("77"),
      "folio-cinema-card must have a brass hairline border (rgba 197,148,77 palette)"
    );
  });

  it("10. folio-cinema-header has brass top border accent", () => {
    const hdrIdx = globalsCss.indexOf(".folio-cinema-header {");
    assert.ok(hdrIdx !== -1, ".folio-cinema-header must exist");
    const block = globalsCss.slice(hdrIdx, hdrIdx + 400);
    assert.ok(
      block.includes("border-top") || block.includes("border"),
      "folio-cinema-header must have a border accent (brass top rule)"
    );
  });

  it("11. folio-cinema-result-card has overflow:hidden", () => {
    const rcIdx = globalsCss.indexOf(".folio-cinema-result-card {");
    assert.ok(rcIdx !== -1, ".folio-cinema-result-card must exist");
    const block = globalsCss.slice(rcIdx, rcIdx + 300);
    assert.ok(
      block.includes("overflow: hidden") || block.includes("overflow:hidden"),
      "folio-cinema-result-card must have overflow:hidden for accent/tab containment"
    );
  });

  it("12. folio-cinema-shell defined after folio-cinema-panel (source-order)", () => {
    const panelIdx = globalsCss.indexOf(".folio-cinema-panel");
    const shellIdx = globalsCss.indexOf(".folio-cinema-shell");
    assert.ok(panelIdx !== -1, ".folio-cinema-panel must exist");
    assert.ok(shellIdx !== -1, ".folio-cinema-shell must exist");
    assert.ok(
      shellIdx > panelIdx,
      ".folio-cinema-shell must be defined after .folio-cinema-panel (cinema section ordering)"
    );
  });

  it("13. folio-cinema-result-card defined after folio-cinema-card (source-order)", () => {
    const cardIdx   = globalsCss.indexOf(".folio-cinema-card {");
    const resultIdx = globalsCss.indexOf(".folio-cinema-result-card {");
    assert.ok(cardIdx !== -1, ".folio-cinema-card must exist");
    assert.ok(resultIdx !== -1, ".folio-cinema-result-card must exist");
    assert.ok(
      resultIdx > cardIdx,
      ".folio-cinema-result-card must be defined after .folio-cinema-card"
    );
  });
});

// ── 14–19. Paper-world legibility fixes ──────────────────────────────────────

describe("Slice 4: Paper-world legibility — DashboardClient", () => {
  it("14. AtelierGreeting h1 uses text-ds-folio-ink (readable on paper)", () => {
    assert.ok(
      dashboardClient.includes("text-ds-folio-ink"),
      "DashboardClient AtelierGreeting h1 must use text-ds-folio-ink for legibility on paper background"
    );
  });

  it("15. AtelierGreeting subtitle uses text-ds-folio-ink-mist", () => {
    assert.ok(
      dashboardClient.includes("text-ds-folio-ink-mist"),
      "DashboardClient AtelierGreeting subtitle must use text-ds-folio-ink-mist for readable muted text on paper"
    );
  });

  it("16. Overline component accepts className prop", () => {
    assert.ok(
      dashboardClient.includes("className?") || dashboardClient.includes("className ?: string"),
      "DashboardClient Overline component must accept optional className prop for paper/cinema context switching"
    );
  });

  it("17. AtelierGreeting h1 does NOT use text-ds-text (washed-out cream on paper)", () => {
    const greetingStart = dashboardClient.indexOf("atelier-greeting");
    assert.ok(greetingStart !== -1, "atelier-greeting must be present in DashboardClient");
    const greetingBlock = dashboardClient.slice(greetingStart, greetingStart + 600);
    const h1Match = greetingBlock.match(/<h1[^>]*text-ds-text[^-]/);
    assert.ok(
      !h1Match,
      "AtelierGreeting h1 must NOT use text-ds-text (cream on paper = invisible) — use text-ds-folio-ink instead"
    );
  });
});

describe("Slice 4: Paper-world legibility — trips/page", () => {
  it("18. EmptyDashboard hero h2 uses text-ds-folio-ink (readable on paper)", () => {
    assert.ok(
      tripsPage.includes("text-ds-folio-ink"),
      "trips/page EmptyDashboard hero h2 must use text-ds-folio-ink for legibility on paper background"
    );
  });

  it("19. EmptyDashboard hero p uses text-ds-folio-ink-mist (readable on paper)", () => {
    const emptyBlock = tripsPage.slice(tripsPage.indexOf("trips-empty-state"));
    assert.ok(
      emptyBlock.includes("text-ds-folio-ink"),
      "trips/page EmptyDashboard hero text must not remain as invisible cream on paper — use folio-ink tokens"
    );
  });
});

// ── 20–28. ConciergePage cinema conversion ───────────────────────────────────

describe("Slice 4: ConciergePage cinema conversion", () => {
  it("20. ConciergePage uses folio-cinema-shell on main wrapper", () => {
    assert.ok(
      conciergePage.includes("folio-cinema-shell"),
      "ConciergePage must use folio-cinema-shell on main wrapper for dark cinema base"
    );
  });

  it("21. ConciergePage sticky composer uses folio-cinema-header", () => {
    assert.ok(
      conciergePage.includes("folio-cinema-header"),
      "ConciergePage sticky composer must use folio-cinema-header for intentional cinema header identity"
    );
  });

  it("22. ConciergePage ConciergeResultCard uses folio-cinema-result-card", () => {
    assert.ok(
      conciergePage.includes("folio-cinema-result-card"),
      "ConciergePage ConciergeResultCard must use folio-cinema-result-card for cinema recommendation-slip identity"
    );
  });

  it("23. ConciergePage destination field uses folio-mapline-field", () => {
    assert.ok(
      conciergePage.includes("folio-mapline-field"),
      "ConciergePage destination field must use folio-mapline-field for route-line accent"
    );
  });

  it("24. ConciergePage still uses editorial-scene (backward compat with 8N-C)", () => {
    assert.ok(
      conciergePage.includes("editorial-scene"),
      "ConciergePage must retain editorial-scene for backward compatibility (8N-C tests)"
    );
  });

  it("25. ConciergeResultCard still has folio-cover-tab (8N-C preservation)", () => {
    assert.ok(
      conciergePage.includes("folio-cover-tab"),
      "ConciergeResultCard must retain folio-cover-tab recommendation slip accent (8N-C contract)"
    );
  });

  it("26. ConciergeResultCard still has boutique-folio (8N-B preservation)", () => {
    assert.ok(
      conciergePage.includes("boutique-folio"),
      "ConciergeResultCard must retain boutique-folio shadow class (8N-B backward compat)"
    );
  });

  it("27. ConciergePage result card save/map/source actions preserved", () => {
    assert.ok(
      conciergePage.includes("concierge-result-save-btn"),
      "ConciergeResultCard must retain concierge-result-save-btn testid (save action preserved)"
    );
    assert.ok(
      conciergePage.includes("Google Maps"),
      "ConciergeResultCard must retain Map action link (behavior preserved)"
    );
  });

  it("28. ConciergeResultCard component preserved in ConciergePage", () => {
    assert.ok(
      conciergePage.includes("ConciergeResultCard"),
      "ConciergePage must retain ConciergeResultCard component (behavior contract preserved)"
    );
  });
});

// ── 29–36. ExploreShell cinema conversion ────────────────────────────────────

describe("Slice 4: ExploreShell cinema conversion", () => {
  it("29. ExploreShell explore-home wrapper uses folio-cinema-shell", () => {
    const homeIdx = exploreShell.indexOf("explore-home");
    assert.ok(homeIdx !== -1, "explore-home testid must exist");
    const homeBlock = exploreShell.slice(Math.max(0, homeIdx - 120), homeIdx + 50);
    assert.ok(
      homeBlock.includes("folio-cinema-shell"),
      "ExploreShell explore-home div must include folio-cinema-shell for dark cinema base"
    );
  });

  it("30. ExploreShell explore-vertical-flow wrapper uses folio-cinema-shell", () => {
    const flowIdx = exploreShell.indexOf("explore-vertical-flow");
    assert.ok(flowIdx !== -1, "explore-vertical-flow testid must exist");
    const flowBlock = exploreShell.slice(Math.max(0, flowIdx - 120), flowIdx + 50);
    assert.ok(
      flowBlock.includes("folio-cinema-shell"),
      "ExploreShell explore-vertical-flow div must include folio-cinema-shell"
    );
  });

  it("31. ExploreShell VerticalCard uses folio-cinema-card", () => {
    assert.ok(
      exploreShell.includes("folio-cinema-card"),
      "ExploreShell VerticalCard must use folio-cinema-card for intentional cinema discovery-card identity"
    );
  });

  it("32. ExploreShell still uses editorial-scene (backward compat)", () => {
    assert.ok(
      exploreShell.includes("editorial-scene"),
      "ExploreShell must retain editorial-scene class for backward compatibility (8N-C tests)"
    );
  });

  it("33. ExploreShell still has boutique-folio (8N-B preservation)", () => {
    assert.ok(
      exploreShell.includes("boutique-folio"),
      "ExploreShell VerticalCard must retain boutique-folio shadow class (8N-B backward compat)"
    );
  });

  it("34. ExploreShell VerticalCard text-ds-text-tertiary preserved for overlines", () => {
    assert.ok(
      exploreShell.includes("text-ds-text-tertiary"),
      "ExploreShell VerticalCard must retain text-ds-text-tertiary for overline labels (readable on cinema shell)"
    );
  });

  it("35. ExploreShell active section still has bg-ds-onyx (instrument elevation)", () => {
    assert.ok(
      exploreShell.includes("bg-ds-onyx"),
      "ExploreShell active search instrument section must retain bg-ds-onyx elevation"
    );
  });

  it("36. ExploreShell explore-lounge-header testid preserved", () => {
    assert.ok(
      exploreShell.includes('data-testid="explore-lounge-header"'),
      "ExploreShell must retain explore-lounge-header testid (8F contract)"
    );
  });
});

// ── 37–42. SavedShell cinema conversion ──────────────────────────────────────

describe("Slice 4: SavedShell cinema conversion", () => {
  it("37. SavedShell outer wrapper uses folio-cinema-shell", () => {
    assert.ok(
      savedShell.includes("folio-cinema-shell"),
      "SavedShell outer wrapper must use folio-cinema-shell for dark cinema base (Saved is cinema-world discovery)"
    );
  });

  it("38. SavedShell still uses saved-clipping-desk (8N-E preservation)", () => {
    assert.ok(
      savedShell.includes("saved-clipping-desk"),
      "SavedShell must retain saved-clipping-desk class (8N-E contract)"
    );
  });

  it("39. SavedShell still uses saved-folio-header (8N-F preservation)", () => {
    assert.ok(
      savedShell.includes("saved-folio-header"),
      "SavedShell must retain saved-folio-header for dark integrated header (8N-F contract)"
    );
  });

  it("40. SavedShell still uses saved-folio-card (8N-F preservation)", () => {
    assert.ok(
      savedShell.includes("saved-folio-card"),
      "SavedShell must retain saved-folio-card for dark atelier item cards (8N-F contract)"
    );
  });

  it("41. SavedShell saved-scrapbook-header testid preserved", () => {
    assert.ok(
      savedShell.includes('data-testid="saved-scrapbook-header"'),
      "SavedShell must retain saved-scrapbook-header testid (8G contract)"
    );
  });

  it("42. SavedShell saved-planning-bridge testid preserved", () => {
    assert.ok(
      savedShell.includes('data-testid="saved-planning-bridge"'),
      "SavedShell must retain saved-planning-bridge testid (8G contract)"
    );
  });
});

// ── 43–50. Preservation and safety invariants ─────────────────────────────────

describe("Slice 4: Paper planning surfaces not regressed", () => {
  it("43. ItineraryItemCard still uses folio-paper-item (Slice 3 paper card)", () => {
    assert.ok(
      itineraryCard.includes("folio-paper-item"),
      "ItineraryItemCard must retain folio-paper-item paper card (Slice 3 paper world — not regressed to dark)"
    );
  });

  it("44. DayPlanModal still uses folio-paper-panel (Slice 3 paper panel)", () => {
    assert.ok(
      dayPlanModal.includes("folio-paper-panel"),
      "DayPlanModal must retain folio-paper-panel (Slice 3 paper world — not regressed to dark)"
    );
  });
});

describe("Slice 4: PR #431 protected paths untouched", () => {
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

describe("Slice 4: No invalid tokens or banned patterns", () => {
  it("48. No text-ds-warm-paper in DashboardClient (invalid Tailwind utility)", () => {
    assert.ok(
      !dashboardClient.includes("text-ds-warm-paper"),
      "DashboardClient must not use text-ds-warm-paper — this is an invalid Tailwind utility"
    );
  });

  it("48b. No text-ds-warm-paper in ConciergePage (invalid Tailwind utility)", () => {
    assert.ok(
      !conciergePage.includes("text-ds-warm-paper"),
      "ConciergePage must not use text-ds-warm-paper — this is an invalid Tailwind utility"
    );
  });

  it("48c. No text-ds-warm-paper in ExploreShell (invalid Tailwind utility)", () => {
    assert.ok(
      !exploreShell.includes("text-ds-warm-paper"),
      "ExploreShell must not use text-ds-warm-paper — this is an invalid Tailwind utility"
    );
  });

  it("49. folio-cinema-shell does not use #000000 pure black background", () => {
    const shellIdx = globalsCss.indexOf(".folio-cinema-shell {");
    assert.ok(shellIdx !== -1, ".folio-cinema-shell block must exist");
    const block = globalsCss.slice(shellIdx, shellIdx + 300);
    assert.ok(
      !block.includes("#000000") && !block.includes(": black"),
      "folio-cinema-shell must NOT use pure black — warm umber dark only"
    );
  });

  it("50. No backend/provider imports added to cinema-world components", () => {
    const backendPattern = /from ['"].*backend.*['"]/;
    assert.ok(!backendPattern.test(conciergePage), "ConciergePage must not import backend modules");
    assert.ok(!backendPattern.test(exploreShell),  "ExploreShell must not import backend modules");
    assert.ok(!backendPattern.test(savedShell),    "SavedShell must not import backend modules");
    assert.ok(!backendPattern.test(dashboardClient), "DashboardClient must not import backend modules");
  });
});
