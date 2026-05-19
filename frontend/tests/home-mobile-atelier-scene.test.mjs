/**
 * Home Mobile Atelier Scene System — Stage 3.5
 *
 * Verifies that:
 *  A.  New reusable Folio scene/motion/layering primitives exist in globals.css.
 *  B.  New React primitives are exported from Folio.tsx.
 *  C.  DashboardClient consumes the new reusable patterns correctly.
 *  D.  Prefers-reduced-motion handling exists for all motion classes.
 *  E.  Existing Home testids, routes, and data bindings are preserved.
 *  F.  No orphan folio-home-* reusable typography/surface/button/input styling.
 *  G.  No cream-on-paper or orphan dark paper-world regressions.
 */

import test, { describe } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

function readSrc(rel) {
  return readFileSync(new URL(`../src/${rel}`, import.meta.url), "utf8");
}

const globalsCss      = readSrc("app/globals.css");
const folioTsx        = readSrc("components/ui/Folio.tsx");
const dashboardClient = readSrc("components/dashboard/DashboardClient.tsx");

// ── A. CSS primitive contracts ────────────────────────────────────────────────

describe("Atelier Scene: CSS primitives exist", () => {
  test("A1. globals.css defines .folio-scene", () => {
    assert.ok(globalsCss.includes(".folio-scene {"), ".folio-scene must be defined");
  });

  test("A2. folio-scene uses isolation: isolate for correct stacking", () => {
    const idx = globalsCss.indexOf(".folio-scene {");
    const block = globalsCss.slice(idx, idx + 400);
    assert.ok(block.includes("isolation: isolate"), ".folio-scene must have isolation: isolate");
  });

  test("A3. folio-scene::before exists for drifting glow", () => {
    assert.ok(globalsCss.includes(".folio-scene::before {"), ".folio-scene::before must be defined");
  });

  test("A4. folio-scene::before has z-index: -1 (behind in-flow children)", () => {
    const idx = globalsCss.indexOf(".folio-scene::before {");
    const block = globalsCss.slice(idx, idx + 300);
    assert.ok(block.includes("z-index: -1"), ".folio-scene::before must use z-index: -1");
  });

  test("A5. folio-scene-drift keyframe is defined", () => {
    assert.ok(
      globalsCss.includes("folio-scene-drift"),
      "@keyframes folio-scene-drift must be defined",
    );
  });

  test("A6. globals.css defines .folio-route-thread", () => {
    assert.ok(globalsCss.includes(".folio-route-thread {"), ".folio-route-thread must be defined");
  });

  test("A7. folio-route-thread::before renders the dashed route line", () => {
    assert.ok(
      globalsCss.includes(".folio-route-thread::before {"),
      ".folio-route-thread::before must be defined",
    );
  });

  test("A8. folio-route-thread::after renders the start-point dot", () => {
    assert.ok(
      globalsCss.includes(".folio-route-thread::after {"),
      ".folio-route-thread::after must be defined",
    );
  });

  test("A9. folio-route-draw keyframe is defined", () => {
    assert.ok(
      globalsCss.includes("folio-route-draw"),
      "@keyframes folio-route-draw must be defined",
    );
  });

  test("A10. globals.css defines .folio-invitation-panel", () => {
    assert.ok(
      globalsCss.includes(".folio-invitation-panel {"),
      ".folio-invitation-panel must be defined",
    );
  });

  test("A11. folio-invitation-panel has an elevated warm box-shadow", () => {
    const idx = globalsCss.indexOf(".folio-invitation-panel {");
    const block = globalsCss.slice(idx, idx + 400);
    assert.ok(block.includes("box-shadow"), ".folio-invitation-panel must define box-shadow");
  });

  test("A12. globals.css defines .folio-journey-entry", () => {
    assert.ok(
      globalsCss.includes(".folio-journey-entry {"),
      ".folio-journey-entry must be defined",
    );
  });

  test("A13. folio-journey-entry has position: relative (for pseudo-elements)", () => {
    const idx = globalsCss.indexOf(".folio-journey-entry {");
    const block = globalsCss.slice(idx, idx + 200);
    assert.ok(
      block.includes("position: relative"),
      ".folio-journey-entry must have position: relative",
    );
  });

  test("A14. folio-journey-entry::before renders the left accent stripe", () => {
    assert.ok(
      globalsCss.includes(".folio-journey-entry::before {"),
      ".folio-journey-entry::before must be defined",
    );
  });

  test("A15. folio-journey-entry::after renders the top-edge travel rule", () => {
    assert.ok(
      globalsCss.includes(".folio-journey-entry::after {"),
      ".folio-journey-entry::after must be defined",
    );
  });

  test("A16. globals.css defines .folio-reveal", () => {
    assert.ok(globalsCss.includes(".folio-reveal {"), ".folio-reveal must be defined");
  });

  test("A17. folio-reveal-in keyframe is defined", () => {
    assert.ok(
      globalsCss.includes("folio-reveal-in"),
      "@keyframes folio-reveal-in must be defined",
    );
  });

  test("A18. folio-reveal uses animation: folio-reveal-in", () => {
    const idx = globalsCss.indexOf(".folio-reveal {");
    const block = globalsCss.slice(idx, idx + 200);
    assert.ok(
      block.includes("folio-reveal-in"),
      ".folio-reveal must animate folio-reveal-in",
    );
  });

  test("A19. folio-reveal uses --folio-reveal-delay CSS custom property", () => {
    const idx = globalsCss.indexOf(".folio-reveal {");
    const block = globalsCss.slice(idx, idx + 200);
    assert.ok(
      block.includes("--folio-reveal-delay"),
      ".folio-reveal must use --folio-reveal-delay for stagger control",
    );
  });

  test("A20. folio-reveal stagger variants exist (stagger-1 through stagger-4)", () => {
    assert.ok(globalsCss.includes(".folio-reveal-stagger-1"), ".folio-reveal-stagger-1 must exist");
    assert.ok(globalsCss.includes(".folio-reveal-stagger-2"), ".folio-reveal-stagger-2 must exist");
    assert.ok(globalsCss.includes(".folio-reveal-stagger-3"), ".folio-reveal-stagger-3 must exist");
    assert.ok(globalsCss.includes(".folio-reveal-stagger-4"), ".folio-reveal-stagger-4 must exist");
  });
});

// ── B. React primitive exports ────────────────────────────────────────────────

describe("Atelier Scene: Folio.tsx exports new primitives", () => {
  test("B1. Folio.tsx exports FolioScene", () => {
    assert.ok(
      folioTsx.includes("export function FolioScene"),
      "Folio.tsx must export FolioScene",
    );
  });

  test("B2. FolioScene uses folio-scene CSS class", () => {
    const idx = folioTsx.indexOf("export function FolioScene");
    const block = folioTsx.slice(idx, idx + 300);
    assert.ok(block.includes("folio-scene"), "FolioScene must apply folio-scene CSS class");
  });

  test("B3. FolioScene carries data-folio-world='paper'", () => {
    const idx = folioTsx.indexOf("export function FolioScene");
    const block = folioTsx.slice(idx, idx + 300);
    assert.ok(
      block.includes('data-folio-world="paper"'),
      "FolioScene must carry data-folio-world=paper",
    );
  });

  test("B4. Folio.tsx exports FolioReveal", () => {
    assert.ok(
      folioTsx.includes("export function FolioReveal"),
      "Folio.tsx must export FolioReveal",
    );
  });

  test("B5. FolioReveal uses folio-reveal CSS class", () => {
    const idx = folioTsx.indexOf("export function FolioReveal");
    const block = folioTsx.slice(idx, idx + 400);
    assert.ok(block.includes("folio-reveal"), "FolioReveal must apply folio-reveal CSS class");
  });

  test("B6. FolioReveal accepts stagger prop (1–4)", () => {
    const idx = folioTsx.indexOf("export function FolioReveal");
    const block = folioTsx.slice(idx, idx + 400);
    assert.ok(
      block.includes("stagger"),
      "FolioReveal must accept a stagger prop for sequential reveal",
    );
  });

  test("B7. Folio.tsx exports FolioRouteThread", () => {
    assert.ok(
      folioTsx.includes("export function FolioRouteThread"),
      "Folio.tsx must export FolioRouteThread",
    );
  });

  test("B8. FolioRouteThread renders aria-hidden for decorative intent", () => {
    const idx = folioTsx.indexOf("export function FolioRouteThread");
    const block = folioTsx.slice(idx, idx + 300);
    assert.ok(
      block.includes('aria-hidden="true"'),
      "FolioRouteThread must be aria-hidden — decorative only",
    );
  });

  test("B9. FolioRouteThread uses folio-route-thread CSS class", () => {
    const idx = folioTsx.indexOf("export function FolioRouteThread");
    const block = folioTsx.slice(idx, idx + 300);
    assert.ok(
      block.includes("folio-route-thread"),
      "FolioRouteThread must apply folio-route-thread CSS class",
    );
  });
});

// ── C. DashboardClient adoption ──────────────────────────────────────────────

describe("Atelier Scene: DashboardClient uses new scene primitives", () => {
  test("C1. DashboardClient imports FolioScene", () => {
    assert.ok(
      dashboardClient.includes("FolioScene"),
      "DashboardClient must import FolioScene",
    );
  });

  test("C2. DashboardClient imports FolioReveal", () => {
    assert.ok(
      dashboardClient.includes("FolioReveal"),
      "DashboardClient must import FolioReveal",
    );
  });

  test("C3. DashboardClient imports FolioRouteThread", () => {
    assert.ok(
      dashboardClient.includes("FolioRouteThread"),
      "DashboardClient must import FolioRouteThread",
    );
  });

  test("C4. Root wrapper uses FolioScene (not a plain div)", () => {
    const mainReturn = dashboardClient.slice(dashboardClient.indexOf("return ("));
    assert.ok(
      mainReturn.includes("<FolioScene"),
      "DashboardClient main return must use <FolioScene> as root wrapper",
    );
  });

  test("C5. Root wrapper preserves editorial-scene in className", () => {
    assert.ok(
      dashboardClient.includes("editorial-scene"),
      "editorial-scene must still appear in DashboardClient (test 40 contract)",
    );
  });

  test("C6. AtelierGreeting header has folio-reveal class", () => {
    const start = dashboardClient.indexOf("function AtelierGreeting");
    const end   = dashboardClient.indexOf("function ConciergeEntry");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("folio-reveal"),
      "AtelierGreeting header must have folio-reveal entrance animation",
    );
  });

  test("C7. ConciergeEntry FolioPanel has folio-invitation-panel class", () => {
    const start = dashboardClient.indexOf("function ConciergeEntry");
    const end   = dashboardClient.indexOf("function ContinuePlanningStrip");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("folio-invitation-panel"),
      "ConciergeEntry FolioPanel must add folio-invitation-panel for the doorway treatment",
    );
  });

  test("C8. ContinuePlanningStrip article has folio-journey-entry class", () => {
    const start = dashboardClient.indexOf("function ContinuePlanningStrip");
    const end   = dashboardClient.indexOf("function JourneyShelfTeaser");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("folio-journey-entry"),
      "ContinuePlanningStrip article must add folio-journey-entry for active trip identity",
    );
  });

  test("C9. ContinuePlanningStrip uses FolioRouteThread within the trip card", () => {
    const start = dashboardClient.indexOf("function ContinuePlanningStrip");
    const end   = dashboardClient.indexOf("function JourneyShelfTeaser");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("FolioRouteThread"),
      "ContinuePlanningStrip must include FolioRouteThread as a route motif",
    );
  });

  test("C10. Main return wraps ConciergeEntry in FolioReveal", () => {
    const mainReturn = dashboardClient.slice(dashboardClient.indexOf("return ("));
    assert.ok(
      mainReturn.includes("<FolioReveal") && mainReturn.includes("stagger={2}"),
      "Main return must wrap ConciergeEntry in FolioReveal stagger=2",
    );
  });

  test("C11. Main return wraps ContinuePlanningStrip in FolioReveal stagger=3", () => {
    const mainReturn = dashboardClient.slice(dashboardClient.indexOf("return ("));
    assert.ok(
      mainReturn.includes("stagger={3}"),
      "Main return must include FolioReveal stagger=3 for ContinuePlanningStrip",
    );
  });

  test("C12. Main return wraps JourneyShelfTeaser in FolioReveal stagger=4", () => {
    const mainReturn = dashboardClient.slice(dashboardClient.indexOf("return ("));
    assert.ok(
      mainReturn.includes("stagger={4}"),
      "Main return must include FolioReveal stagger=4 for JourneyShelfTeaser",
    );
  });
});

// ── D. Reduced-motion handling ────────────────────────────────────────────────

describe("Atelier Scene: prefers-reduced-motion guards", () => {
  test("D1. folio-scene::before drift is disabled under prefers-reduced-motion", () => {
    const idx = globalsCss.indexOf("@media (prefers-reduced-motion: reduce)");
    assert.ok(idx !== -1, "globals.css must have at least one reduced-motion media query");
    // Find the folio-scene-specific reduced-motion block
    const afterIdx = globalsCss.indexOf(
      ".folio-scene::before { animation: none; }",
    );
    assert.ok(
      afterIdx !== -1,
      "folio-scene::before animation must be disabled under prefers-reduced-motion",
    );
  });

  test("D2. folio-route-thread::before draw is disabled under prefers-reduced-motion", () => {
    assert.ok(
      globalsCss.includes(".folio-route-thread::before { animation: none; }"),
      "folio-route-thread::before animation must be disabled under prefers-reduced-motion",
    );
  });

  test("D3. folio-reveal animation is disabled under prefers-reduced-motion", () => {
    assert.ok(
      globalsCss.includes(".folio-reveal { animation: none; }"),
      "folio-reveal animation must be disabled under prefers-reduced-motion",
    );
  });

  test("D4. folio-scene drift is also disabled on mobile (max-width: 600px)", () => {
    const mobileQuery = globalsCss.indexOf("@media (max-width: 600px)");
    assert.ok(mobileQuery !== -1, "A max-width: 600px media query must exist");
    const block = globalsCss.slice(mobileQuery, mobileQuery + 200);
    assert.ok(
      block.includes("folio-scene::before"),
      "folio-scene::before drift must be disabled on mobile (≤600px) for battery/render budget",
    );
  });
});

// ── E. Behavior preservation ─────────────────────────────────────────────────

describe("Atelier Scene: existing behavior fully preserved", () => {
  test("E1. atelier-greeting testid preserved", () => {
    assert.match(dashboardClient, /data-testid="atelier-greeting"/);
  });

  test("E2. concierge-entry testid preserved", () => {
    assert.match(dashboardClient, /data-testid="concierge-entry"/);
  });

  test("E3. concierge-advisor-desk testid preserved on FolioPanel", () => {
    assert.match(dashboardClient, /<FolioPanel\b[^>]*concierge-advisor-desk/);
  });

  test("E4. atelier-continue-planning testid preserved", () => {
    assert.match(dashboardClient, /data-testid="atelier-continue-planning"/);
  });

  test("E5. journey-shelf-teaser testid preserved", () => {
    assert.match(dashboardClient, /data-testid="journey-shelf-teaser"/);
  });

  test("E6. atelier-planning-strip testid preserved", () => {
    assert.match(dashboardClient, /data-testid="atelier-planning-strip"/);
  });

  test("E7. href=/concierge in ConciergeEntry preserved", () => {
    const start = dashboardClient.indexOf("function ConciergeEntry");
    const end   = dashboardClient.indexOf("function ContinuePlanningStrip");
    const block = dashboardClient.slice(start, end);
    assert.match(block, /href="\/concierge"/);
  });

  test("E8. trip.title and trip.destination bindings preserved in ContinuePlanningStrip", () => {
    const start = dashboardClient.indexOf("function ContinuePlanningStrip");
    const end   = dashboardClient.indexOf("function JourneyShelfTeaser");
    const block = dashboardClient.slice(start, end);
    assert.match(block, /trip\.title/);
    assert.match(block, /trip\.destination/);
  });

  test("E9. folio-paper-card preserved on ContinuePlanningStrip article", () => {
    const start = dashboardClient.indexOf("function ContinuePlanningStrip");
    const end   = dashboardClient.indexOf("function JourneyShelfTeaser");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("folio-paper-card"),
      "ContinuePlanningStrip article must keep folio-paper-card (test 38 contract)",
    );
  });

  test("E10. mapline-rule preserved in AtelierGreeting", () => {
    assert.match(dashboardClient, /mapline-rule/);
  });

  test("E11. editorial-scene preserved in root wrapper className", () => {
    assert.match(dashboardClient, /editorial-scene/);
  });

  test("E12. btn-marine preserved in ConciergeEntry", () => {
    const start = dashboardClient.indexOf("function ConciergeEntry");
    const end   = dashboardClient.indexOf("function ContinuePlanningStrip");
    const block = dashboardClient.slice(start, end);
    assert.ok(block.includes("btn-marine"), "ConciergeEntry must keep btn-marine CTA");
  });

  test("E13. folio-heading preserved in ConciergeEntry", () => {
    const start = dashboardClient.indexOf("function ConciergeEntry");
    const end   = dashboardClient.indexOf("function ContinuePlanningStrip");
    const block = dashboardClient.slice(start, end);
    assert.ok(block.includes("folio-heading"), "ConciergeEntry h2 must keep folio-heading");
  });

  test("E14. 'Your private concierge.' editorial copy preserved", () => {
    const start = dashboardClient.indexOf("function ConciergeEntry");
    const end   = dashboardClient.indexOf("function ContinuePlanningStrip");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("Your private concierge."),
      "ConciergeEntry must keep editorial voice copy",
    );
  });

  test("E15. folio-display and folio-issue-eyebrow preserved in AtelierGreeting", () => {
    const start = dashboardClient.indexOf("function AtelierGreeting");
    const end   = dashboardClient.indexOf("function ConciergeEntry");
    const block = dashboardClient.slice(start, end);
    assert.ok(block.includes("folio-display"), "AtelierGreeting must keep folio-display h1");
    assert.ok(
      block.includes("folio-issue-eyebrow"),
      "AtelierGreeting must keep folio-issue-eyebrow",
    );
  });

  test("E16. home-new-trip-action testid preserved", () => {
    assert.match(dashboardClient, /data-testid="home-new-trip-action"/);
  });
});

// ── F. No orphan folio-home-* reusable styling ───────────────────────────────

describe("Atelier Scene: no orphan home-only reusable classes", () => {
  test("F1. DashboardClient does not use orphan folio-home-* typography classes", () => {
    assert.doesNotMatch(
      dashboardClient,
      /folio-home-greeting-title|folio-home-hero-sub|folio-home-issue-eyebrow|folio-home-editorial-caption|folio-home-serial|folio-home-trip-title|folio-home-concierge-card-accent|folio-home-concierge-serif/,
      "DashboardClient must not use orphan folio-home-* typography classes",
    );
  });

  test("F2. New CSS primitives are NOT prefixed folio-home-* (they are reusable)", () => {
    assert.doesNotMatch(
      globalsCss,
      /\.folio-home-scene|\.folio-home-reveal|\.folio-home-route-thread|\.folio-home-invitation|\.folio-home-journey/,
      "New scene/motion primitives must not be folio-home-* — they are reusable",
    );
  });
});

// ── G. No cream-on-paper / orphan dark regressions ───────────────────────────

describe("Atelier Scene: no regression — cream-on-paper and orphan dark", () => {
  test("G1. DashboardClient does not use text-ds-text (cream) in paper-world blocks", () => {
    assert.doesNotMatch(
      dashboardClient,
      /\btext-ds-text\b(?!-)/,
      "DashboardClient must not use text-ds-text (cream) — use text-ds-folio-ink* on paper",
    );
  });

  test("G2. DashboardClient does not use bg-ds-onyx orphan dark surfaces", () => {
    // Loading skeleton bg-ds-linen is allowed; bg-ds-onyx is a cinema surface
    assert.doesNotMatch(
      dashboardClient,
      /bg-ds-onyx/,
      "DashboardClient must not use bg-ds-onyx — it is a cinema surface, not paper",
    );
  });

  test("G3. folio-invitation-panel is not using cream text tokens in CSS", () => {
    const idx = globalsCss.indexOf(".folio-invitation-panel {");
    const block = globalsCss.slice(idx, idx + 400);
    assert.ok(
      !block.includes("--ds-text-primary") && !block.includes("--ds-pearl-cream"),
      ".folio-invitation-panel must not use cinema cream text tokens",
    );
  });
});
