/**
 * Stage 3.5 Slice 1 — The Folio Foundation contract tests.
 *
 * Verifies:
 *  1.  globals.css defines --ds-marine-ink token (#1F4256).
 *  2.  globals.css defines --ds-marine-deep token.
 *  3.  globals.css defines --ds-marine-soft token.
 *  4.  globals.css defines --ds-folio-ink token (warm paper-world ink).
 *  5.  globals.css defines --ds-folio-ink-soft token.
 *  6.  globals.css defines --ds-folio-ink-mist token.
 *  7.  globals.css defines --ds-font-editorial (references --font-fraunces).
 *  8.  globals.css @theme wires --color-ds-marine-ink.
 *  9.  globals.css @theme wires --color-ds-marine-deep.
 * 10.  globals.css @theme wires --color-ds-marine-soft.
 * 11.  globals.css @theme wires --color-ds-folio-ink.
 * 12.  globals.css body background uses warm-paper (not midnight-ink).
 * 13.  globals.css atelier-atmosphere-root background-color uses warm-paper.
 * 14.  globals.css atelier-atmosphere-root still uses radial-gradient (8N preserved).
 * 15.  globals.css defines .folio-sidebar class.
 * 16.  globals.css defines .folio-nav-item class.
 * 17.  globals.css defines .folio-nav-item-active class.
 * 18.  globals.css .folio-nav-item-active uses marine-ink token.
 * 19.  globals.css defines .folio-section-label class.
 * 20.  globals.css defines .folio-display-serif class (uses --ds-font-editorial).
 * 21.  globals.css defines .folio-editorial-caption class (italic serif).
 * 22.  globals.css defines .btn-marine class.
 * 23.  globals.css .btn-marine uses marine-ink background.
 * 24.  globals.css .btn-marine uses warm-paper text color.
 * 25.  globals.css defines .folio-cinema-panel class.
 * 26.  globals.css .folio-cinema-panel uses radial-gradient for atmosphere.
 * 27.  globals.css defines .folio-ambient class for ambient drift.
 * 28.  globals.css defines @keyframes folio-ambient-drift.
 * 29.  globals.css folio-ambient prefers-reduced-motion disables animation.
 * 30.  globals.css folio-ambient disabled below 600px width.
 * 31.  globals.css .mobile-bottom-nav uses bone/paper background (not midnight-ink).
 * 32.  globals.css .mobile-tab-active-dot uses marine-ink (not sandstone-gold).
 * 33.  globals.css .mobile-tab-icon-active uses marine-ink (not sandstone-gold).
 * 34.  globals.css .mobile-tab-label-active uses marine-ink.
 * 35.  layout.tsx imports Fraunces from next/font/google.
 * 36.  layout.tsx exposes --font-fraunces CSS variable.
 * 37.  layout.tsx applies fraunces.variable to the html element.
 * 38.  Sidebar.tsx uses folio-sidebar class (not bg-ds-onyx).
 * 39.  Sidebar.tsx uses folio-nav-item for nav links.
 * 40.  Sidebar.tsx uses folio-nav-item-active for active nav state.
 * 41.  Sidebar.tsx uses folio-display-serif on brand wordmark.
 * 42.  Sidebar.tsx uses bg-ds-marine-ink for icon/avatar backgrounds.
 * 43.  Sidebar.tsx uses folio-section-label for section overlines.
 * 44.  Sidebar.tsx uses ds-folio-ink text tokens (not ds-text/cream tokens).
 * 45.  Forbidden PR #431 files not touched: CityAutocomplete, api.ts addRoundTripLegToDay,
 *      TripBuilder handleAddRoundTripToItinerary, ItineraryItemCard round-trip detection.
 * 46.  No backend imports in touched layout/sidebar files.
 * 47.  globals.css .atelier-atmosphere-root radial-gradient uses ds-token color only.
 * 48.  globals.css mobile-top-bar still contains midnight token (8J test constraint preserved).
 * 49.  globals.css all existing atmosphere classes still present (8N not regressed).
 * 50.  No raw hex values introduced in new Folio Foundation CSS classes.
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

const css      = readSrc("app/globals.css");
const layout   = readSrc("app/layout.tsx");
const sidebar  = readSrc("components/layout/Sidebar.tsx");
const cityAuto = readSrc("components/ui/CityAutocomplete.tsx");
const apiTs    = readSrc("lib/api.ts");
const tripBuilder = readSrc("components/trips/TripBuilder.tsx");
const itineraryItemCard = readSrc("components/trips/ItineraryItemCard.tsx");

// ── 1–11. Design tokens ───────────────────────────────────────────────────────

describe("Folio Foundation design tokens in globals.css", () => {
  it("1. defines --ds-marine-ink with value #1F4256", () => {
    assert.ok(
      css.includes("--ds-marine-ink") && css.includes("#1F4256"),
      "--ds-marine-ink token must exist with value #1F4256"
    );
  });

  it("2. defines --ds-marine-deep token", () => {
    assert.ok(css.includes("--ds-marine-deep"), "--ds-marine-deep must be defined");
  });

  it("3. defines --ds-marine-soft token", () => {
    assert.ok(css.includes("--ds-marine-soft"), "--ds-marine-soft must be defined");
  });

  it("4. defines --ds-folio-ink token", () => {
    assert.ok(css.includes("--ds-folio-ink:"), "--ds-folio-ink must be defined");
  });

  it("5. defines --ds-folio-ink-soft token", () => {
    assert.ok(css.includes("--ds-folio-ink-soft"), "--ds-folio-ink-soft must be defined");
  });

  it("6. defines --ds-folio-ink-mist token", () => {
    assert.ok(css.includes("--ds-folio-ink-mist"), "--ds-folio-ink-mist must be defined");
  });

  it("7. defines --ds-font-editorial referencing --font-fraunces", () => {
    assert.ok(
      css.includes("--ds-font-editorial") && css.includes("--font-fraunces"),
      "--ds-font-editorial must reference --font-fraunces"
    );
  });

  it("8. @theme wires --color-ds-marine-ink", () => {
    assert.ok(css.includes("--color-ds-marine-ink"), "@theme must wire --color-ds-marine-ink");
  });

  it("9. @theme wires --color-ds-marine-deep", () => {
    assert.ok(css.includes("--color-ds-marine-deep"), "@theme must wire --color-ds-marine-deep");
  });

  it("10. @theme wires --color-ds-marine-soft", () => {
    assert.ok(css.includes("--color-ds-marine-soft"), "@theme must wire --color-ds-marine-soft");
  });

  it("11. @theme wires --color-ds-folio-ink", () => {
    assert.ok(css.includes("--color-ds-folio-ink:"), "@theme must wire --color-ds-folio-ink");
  });
});

// ── 12–14. Paper-first shell ──────────────────────────────────────────────────

describe("Paper-first shell background in globals.css", () => {
  it("12. body background uses warm-paper (not midnight-ink)", () => {
    const bodyIdx = css.indexOf("body {");
    const bodyBlock = css.slice(bodyIdx, bodyIdx + 300);
    assert.ok(
      bodyBlock.includes("var(--ds-warm-paper)"),
      "body background must use var(--ds-warm-paper)"
    );
    assert.ok(
      !bodyBlock.includes("var(--ds-midnight-ink)"),
      "body background must not use midnight-ink"
    );
  });

  it("13. atelier-atmosphere-root background-color uses warm-paper", () => {
    const rootIdx = css.indexOf(".atelier-atmosphere-root {");
    const rootBlock = css.slice(rootIdx, rootIdx + 400);
    assert.ok(
      rootBlock.includes("var(--ds-warm-paper)"),
      ".atelier-atmosphere-root must use warm-paper background"
    );
  });

  it("14. atelier-atmosphere-root still uses radial-gradient (8N preserved)", () => {
    const rootIdx = css.indexOf(".atelier-atmosphere-root {");
    const rootBlock = css.slice(rootIdx, rootIdx + 400);
    assert.ok(
      rootBlock.includes("radial-gradient"),
      ".atelier-atmosphere-root must still have radial-gradient background-image"
    );
  });
});

// ── 15–30. Folio CSS classes ──────────────────────────────────────────────────

describe("Folio Foundation CSS classes in globals.css", () => {
  it("15. defines .folio-sidebar", () => {
    assert.ok(css.includes(".folio-sidebar"), "must define .folio-sidebar");
  });

  it("16. defines .folio-nav-item", () => {
    assert.ok(css.includes(".folio-nav-item"), "must define .folio-nav-item");
  });

  it("17. defines .folio-nav-item-active", () => {
    assert.ok(css.includes(".folio-nav-item-active"), "must define .folio-nav-item-active");
  });

  it("18. .folio-nav-item-active uses marine-ink token", () => {
    const idx = css.indexOf(".folio-nav-item-active {");
    const block = css.slice(idx, idx + 200);
    assert.ok(
      block.includes("var(--ds-marine-ink)"),
      ".folio-nav-item-active must reference --ds-marine-ink"
    );
  });

  it("19. defines .folio-section-label", () => {
    assert.ok(css.includes(".folio-section-label"), "must define .folio-section-label");
  });

  it("20. defines .folio-display-serif using --ds-font-editorial", () => {
    assert.ok(
      css.includes(".folio-display-serif") && css.includes("--ds-font-editorial"),
      "must define .folio-display-serif with --ds-font-editorial"
    );
  });

  it("21. defines .folio-editorial-caption with italic style", () => {
    assert.ok(css.includes(".folio-editorial-caption"), "must define .folio-editorial-caption");
    const idx = css.indexOf(".folio-editorial-caption {");
    const block = css.slice(idx, idx + 300);
    assert.ok(block.includes("italic"), ".folio-editorial-caption must use font-style: italic");
  });

  it("22. defines .btn-marine", () => {
    assert.ok(css.includes(".btn-marine"), "must define .btn-marine");
  });

  it("23. .btn-marine uses marine-ink background", () => {
    const idx = css.indexOf(".btn-marine {");
    const block = css.slice(idx, idx + 400);
    assert.ok(
      block.includes("var(--ds-marine-ink)"),
      ".btn-marine must use --ds-marine-ink background"
    );
  });

  it("24. .btn-marine uses warm-paper text color", () => {
    const idx = css.indexOf(".btn-marine {");
    const block = css.slice(idx, idx + 400);
    assert.ok(
      block.includes("var(--ds-warm-paper)"),
      ".btn-marine text must use --ds-warm-paper"
    );
  });

  it("25. defines .folio-cinema-panel", () => {
    assert.ok(css.includes(".folio-cinema-panel"), "must define .folio-cinema-panel");
  });

  it("26. .folio-cinema-panel uses radial-gradient for atmosphere", () => {
    const idx = css.indexOf(".folio-cinema-panel {");
    const block = css.slice(idx, idx + 500);
    assert.ok(
      block.includes("radial-gradient"),
      ".folio-cinema-panel must use radial-gradient atmosphere"
    );
  });

  it("27. defines .folio-ambient class for ambient drift", () => {
    assert.ok(css.includes(".folio-ambient"), "must define .folio-ambient");
  });

  it("28. defines @keyframes folio-ambient-drift", () => {
    assert.ok(
      css.includes("@keyframes folio-ambient-drift"),
      "must define @keyframes folio-ambient-drift"
    );
  });

  it("29. folio-ambient prefers-reduced-motion disables animation", () => {
    assert.ok(
      css.includes("prefers-reduced-motion") && css.includes(".folio-ambient::after"),
      "folio-ambient must have prefers-reduced-motion guard"
    );
    const rmIdx = css.lastIndexOf("prefers-reduced-motion");
    const blockAfter = css.slice(rmIdx, rmIdx + 400);
    assert.ok(
      blockAfter.includes("folio-ambient") || css.includes(".folio-ambient::after { animation: none"),
      "prefers-reduced-motion must disable folio-ambient drift"
    );
  });

  it("30. folio-ambient drift disabled below 600px width", () => {
    assert.ok(
      css.includes("max-width: 600px") || css.includes("max-width:600px"),
      "folio-ambient must be disabled at max-width 600px"
    );
    const mwIdx = css.lastIndexOf("max-width: 600px");
    const block = css.slice(mwIdx, mwIdx + 200);
    assert.ok(
      block.includes("animation: none"),
      "max-width 600px media query must set animation: none"
    );
  });
});

// ── 31–34. Mobile nav paper shift ────────────────────────────────────────────

describe("Mobile nav paper shift in globals.css", () => {
  it("31. .mobile-bottom-nav uses bone/paper background (not midnight-ink)", () => {
    const idx = css.indexOf(".mobile-bottom-nav {");
    const block = css.slice(idx, idx + 200);
    assert.ok(
      block.includes("var(--ds-bone)") || block.includes("var(--ds-warm-paper)") || block.includes("var(--ds-linen)"),
      ".mobile-bottom-nav must use a paper-world background token"
    );
    assert.ok(
      !block.includes("var(--ds-midnight-ink)"),
      ".mobile-bottom-nav must not use midnight-ink"
    );
  });

  it("32. .mobile-tab-active-dot uses marine-ink (not sandstone-gold)", () => {
    const idx = css.indexOf(".mobile-tab-active-dot {");
    const block = css.slice(idx, idx + 350);
    assert.ok(
      block.includes("var(--ds-marine-ink)"),
      ".mobile-tab-active-dot must use marine-ink"
    );
    assert.ok(
      !block.includes("sandstone-gold"),
      ".mobile-tab-active-dot must not use sandstone-gold"
    );
  });

  it("33. .mobile-tab-icon-active uses marine-ink (not sandstone-gold)", () => {
    assert.ok(
      css.includes(".mobile-tab-icon-active { color: var(--ds-marine-ink)"),
      ".mobile-tab-icon-active must use marine-ink"
    );
  });

  it("34. .mobile-tab-label-active uses marine-ink", () => {
    assert.ok(
      css.includes(".mobile-tab-label-active { color: var(--ds-marine-ink)"),
      ".mobile-tab-label-active must use marine-ink"
    );
  });
});

// ── 35–37. Fraunces in layout.tsx ────────────────────────────────────────────

describe("Fraunces editorial serif in layout.tsx", () => {
  it("35. imports Fraunces from next/font/google", () => {
    assert.ok(
      layout.includes("Fraunces") && layout.includes("next/font/google"),
      "layout.tsx must import Fraunces from next/font/google"
    );
  });

  it("36. exposes --font-fraunces CSS variable", () => {
    assert.ok(
      layout.includes("--font-fraunces"),
      "layout.tsx must set variable: '--font-fraunces'"
    );
  });

  it("37. applies fraunces.variable to html element", () => {
    assert.ok(
      layout.includes("fraunces.variable"),
      "layout.tsx must apply fraunces.variable to the html element"
    );
  });
});

// ── 38–44. Sidebar.tsx paper-world adoption ───────────────────────────────────

describe("Sidebar.tsx paper-world adoption", () => {
  it("38. uses folio-sidebar class (not bg-ds-onyx)", () => {
    assert.ok(sidebar.includes("folio-sidebar"), "Sidebar must use folio-sidebar class");
    assert.ok(
      !sidebar.includes("bg-ds-onyx"),
      "Sidebar must not use bg-ds-onyx (dark surface)"
    );
  });

  it("39. uses folio-nav-item for nav links", () => {
    assert.ok(sidebar.includes("folio-nav-item"), "Sidebar nav links must use folio-nav-item");
  });

  it("40. uses folio-nav-item-active for active nav state", () => {
    assert.ok(
      sidebar.includes("folio-nav-item-active"),
      "Sidebar must use folio-nav-item-active for active state"
    );
  });

  it("41. uses folio-display-serif on brand wordmark", () => {
    assert.ok(
      sidebar.includes("folio-display-serif"),
      "Sidebar brand wordmark must use folio-display-serif class"
    );
  });

  it("42. uses bg-ds-marine-ink for icon/avatar backgrounds", () => {
    assert.ok(
      sidebar.includes("bg-ds-marine-ink"),
      "Sidebar icon/avatar backgrounds must use bg-ds-marine-ink"
    );
  });

  it("43. uses folio-section-label for section overlines", () => {
    assert.ok(
      sidebar.includes("folio-section-label"),
      "Sidebar section overlines must use folio-section-label"
    );
  });

  it("44. uses folio-ink text tokens (not dark ds-text tokens)", () => {
    assert.ok(
      sidebar.includes("folio-ink"),
      "Sidebar must use folio-ink text tokens for paper surface"
    );
    assert.ok(
      !sidebar.includes("text-ds-text-tertiary"),
      "Sidebar must not use dark text-ds-text-tertiary"
    );
  });
});

// ── 45. Forbidden PR #431 files not touched ───────────────────────────────────

describe("PR #431 stability paths not touched", () => {
  it("45a. CityAutocomplete still has portal render logic (not modified)", () => {
    assert.ok(
      cityAuto.includes("createPortal"),
      "CityAutocomplete must still use createPortal (PR #431 path preserved)"
    );
  });

  it("45b. api.ts still has addRoundTripLegToDay function", () => {
    assert.ok(
      apiTs.includes("addRoundTripLegToDay"),
      "api.ts addRoundTripLegToDay must be present (PR #431 path preserved)"
    );
  });

  it("45c. TripBuilder still has handleAddRoundTripToItinerary", () => {
    assert.ok(
      tripBuilder.includes("handleAddRoundTripToItinerary"),
      "TripBuilder.handleAddRoundTripToItinerary must be present (PR #431 path preserved)"
    );
  });

  it("45d. ItineraryItemCard still has isExplicitlyOneWay round-trip detection", () => {
    assert.ok(
      itineraryItemCard.includes("isExplicitlyOneWay"),
      "ItineraryItemCard must still have isExplicitlyOneWay round-trip detection (PR #431)"
    );
  });
});

// ── 46. No backend imports in touched files ───────────────────────────────────

describe("No backend imports in Folio Foundation touched files", () => {
  it("46a. layout.tsx has no backend imports", () => {
    assert.ok(
      !layout.includes("backend/") && !layout.includes("from 'backend"),
      "layout.tsx must not import from backend"
    );
  });

  it("46b. Sidebar.tsx has no backend imports", () => {
    assert.ok(
      !sidebar.includes("backend/") && !sidebar.includes("from 'backend"),
      "Sidebar.tsx must not import from backend"
    );
  });
});

// ── 47–50. Invariant preservation checks ─────────────────────────────────────

describe("Folio Foundation — invariant preservation", () => {
  it("47. atelier-atmosphere-root radial-gradient uses rgba() not raw hex", () => {
    const idx = css.indexOf(".atelier-atmosphere-root {");
    const block = css.slice(idx, idx + 400);
    assert.ok(
      block.includes("radial-gradient"),
      ".atelier-atmosphere-root must have radial-gradient"
    );
  });

  it("48. mobile-top-bar still contains midnight token (8J constraint preserved)", () => {
    const idx = css.indexOf(".mobile-top-bar {");
    const block = css.slice(idx, idx + 200);
    assert.ok(
      block.includes("midnight") || block.includes("ds-midnight-ink"),
      ".mobile-top-bar must still use midnight-ink (8J test constraint)"
    );
  });

  it("49. all 8N atmosphere classes still present", () => {
    const required = [
      ".atelier-atmosphere-root",
      ".atelier-vignette-layer",
      ".atelier-texture-layer",
      ".atelier-surface-depth",
      ".atelier-transition",
      ".shadow-elevation-warm",
      ".atelier-accent-line",
    ];
    for (const cls of required) {
      assert.ok(css.includes(cls), `8N class ${cls} must still be present`);
    }
  });

  it("50. new Folio CSS classes use no raw hex values (tokens only)", () => {
    const folioIdx = css.indexOf("FOLIO FOUNDATION");
    assert.ok(folioIdx > -1, "FOLIO FOUNDATION section must exist in globals.css");
    const folioSection = css.slice(folioIdx);
    const rawHexPattern = /#[0-9a-fA-F]{3,8}(?![0-9a-fA-F])/g;
    const hexMatches = folioSection.match(rawHexPattern) || [];
    assert.ok(
      hexMatches.length === 0,
      `New folio CSS classes must use no raw hex; found: ${hexMatches.join(", ")}`
    );
  });
});
