/**
 * Home Mobile Folio Redesign — Stage 3.5
 * Contract tests verifying the editorial redesign of the Home mobile screen.
 *
 * What this covers:
 *  1.  globals.css defines .folio-home-greeting-title (Fraunces italic display).
 *  2.  globals.css defines .folio-home-issue-eyebrow (brass rule + overline).
 *  3.  globals.css defines .folio-home-editorial-caption (Fraunces italic caption).
 *  4.  globals.css defines .folio-home-concierge-serif (Fraunces italic heading).
 *  5.  folio-home-greeting-title uses var(--ds-font-editorial) (Fraunces).
 *  6.  folio-home-concierge-serif uses var(--ds-font-editorial) (Fraunces).
 *  7.  folio-home-issue-eyebrow has ::before brass rule.
 *  8.  folio-home-editorial-caption uses font-style italic.
 *  9.  DashboardClient AtelierGreeting uses folio-home-greeting-title for h1.
 * 10.  DashboardClient AtelierGreeting uses folio-home-issue-eyebrow.
 * 11.  DashboardClient ConciergeEntry h2 uses folio-home-concierge-serif.
 * 12.  DashboardClient ConciergeEntry uses btn-marine (marine ink CTA).
 * 13.  DashboardClient ContinuePlanningStrip uses folio-home-editorial-caption.
 * 14.  DashboardClient JourneyShelfTeaser uses folio-home-editorial-caption.
 * 15.  DashboardClient AtelierPlanningStrip uses folio-home-editorial-caption.
 * 16.  DashboardClient does NOT import MapPin (removed with icon-free ContinuePlanning).
 * 17.  DashboardClient AtelierGreeting h1 class is folio-home-greeting-title (not plain text-2xl).
 * 18.  DashboardClient ConciergeEntry h2 text is "Your private concierge." (editorial voice).
 * 19.  All existing testids preserved (behavior unchanged).
 * 20.  folio-home-greeting-title has font-weight: 300 (light italic, not bold dashboard).
 */

import test, { describe } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

function readSrc(rel) {
  return readFileSync(new URL(`../src/${rel}`, import.meta.url), "utf8");
}

const globalsCss = readSrc("app/globals.css");
const dashboardClient = readSrc("components/dashboard/DashboardClient.tsx");

// ── 1–8. CSS primitives ──────────────────────────────────────────────────────

describe("Home Folio: CSS primitives exist", () => {
  test("1. globals.css defines .folio-home-greeting-title", () => {
    assert.ok(
      globalsCss.includes(".folio-home-greeting-title"),
      "globals.css must define .folio-home-greeting-title for editorial greeting heading"
    );
  });

  test("2. globals.css defines .folio-home-issue-eyebrow", () => {
    assert.ok(
      globalsCss.includes(".folio-home-issue-eyebrow"),
      "globals.css must define .folio-home-issue-eyebrow for brass masthead opener"
    );
  });

  test("3. globals.css defines .folio-home-editorial-caption", () => {
    assert.ok(
      globalsCss.includes(".folio-home-editorial-caption"),
      "globals.css must define .folio-home-editorial-caption for italic serif captions"
    );
  });

  test("4. globals.css defines .folio-home-concierge-serif", () => {
    assert.ok(
      globalsCss.includes(".folio-home-concierge-serif"),
      "globals.css must define .folio-home-concierge-serif for concierge entry heading"
    );
  });

  test("5. folio-home-greeting-title uses var(--ds-font-editorial)", () => {
    const idx = globalsCss.indexOf(".folio-home-greeting-title");
    assert.ok(idx !== -1, ".folio-home-greeting-title block must exist");
    const block = globalsCss.slice(idx, idx + 300);
    assert.ok(
      block.includes("var(--ds-font-editorial)"),
      "folio-home-greeting-title must use var(--ds-font-editorial) for Fraunces variable serif"
    );
  });

  test("6. folio-home-concierge-serif uses var(--ds-font-editorial)", () => {
    const idx = globalsCss.indexOf(".folio-home-concierge-serif");
    assert.ok(idx !== -1, ".folio-home-concierge-serif block must exist");
    const block = globalsCss.slice(idx, idx + 300);
    assert.ok(
      block.includes("var(--ds-font-editorial)"),
      "folio-home-concierge-serif must use var(--ds-font-editorial) for Fraunces variable serif"
    );
  });

  test("7. folio-home-issue-eyebrow has ::before brass rule", () => {
    assert.ok(
      globalsCss.includes(".folio-home-issue-eyebrow::before"),
      "folio-home-issue-eyebrow must have ::before pseudo-element for brass rule"
    );
  });

  test("8. folio-home-editorial-caption uses font-style italic", () => {
    const idx = globalsCss.indexOf(".folio-home-editorial-caption");
    assert.ok(idx !== -1, ".folio-home-editorial-caption block must exist");
    const block = globalsCss.slice(idx, idx + 250);
    assert.ok(
      block.includes("font-style: italic"),
      "folio-home-editorial-caption must set font-style: italic for Fraunces italic"
    );
  });

  test("20. folio-home-greeting-title has font-weight: 300", () => {
    const idx = globalsCss.indexOf(".folio-home-greeting-title");
    const block = globalsCss.slice(idx, idx + 300);
    assert.ok(
      block.includes("font-weight: 300"),
      "folio-home-greeting-title must use font-weight: 300 (light italic, not bold)"
    );
  });
});

// ── 9–18. DashboardClient component usage ────────────────────────────────────

describe("Home Folio: DashboardClient editorial adoption", () => {
  test("9. DashboardClient AtelierGreeting uses folio-home-greeting-title for h1", () => {
    const greetingStart = dashboardClient.indexOf("function AtelierGreeting");
    const greetingEnd = dashboardClient.indexOf("function ConciergeEntry");
    const block = dashboardClient.slice(greetingStart, greetingEnd);
    assert.ok(
      block.includes("folio-home-greeting-title"),
      "AtelierGreeting h1 must use folio-home-greeting-title class"
    );
  });

  test("10. DashboardClient AtelierGreeting uses folio-home-issue-eyebrow", () => {
    const greetingStart = dashboardClient.indexOf("function AtelierGreeting");
    const greetingEnd = dashboardClient.indexOf("function ConciergeEntry");
    const block = dashboardClient.slice(greetingStart, greetingEnd);
    assert.ok(
      block.includes("folio-home-issue-eyebrow"),
      "AtelierGreeting must include folio-home-issue-eyebrow for editorial brass masthead line"
    );
  });

  test("11. DashboardClient ConciergeEntry h2 uses folio-home-concierge-serif", () => {
    const start = dashboardClient.indexOf("function ConciergeEntry");
    const end = dashboardClient.indexOf("function ContinuePlanningStrip");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("folio-home-concierge-serif"),
      "ConciergeEntry h2 must use folio-home-concierge-serif for Fraunces italic heading"
    );
  });

  test("12. DashboardClient ConciergeEntry uses btn-marine (marine ink CTA)", () => {
    const start = dashboardClient.indexOf("function ConciergeEntry");
    const end = dashboardClient.indexOf("function ContinuePlanningStrip");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("btn-marine"),
      "ConciergeEntry CTA must use btn-marine (marine ink, not gold fill per folio direction)"
    );
  });

  test("13. DashboardClient ContinuePlanningStrip uses folio-home-editorial-caption for destination", () => {
    const start = dashboardClient.indexOf("function ContinuePlanningStrip");
    const end = dashboardClient.indexOf("function JourneyShelfTeaser");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("folio-home-editorial-caption"),
      "ContinuePlanningStrip must use folio-home-editorial-caption for trip destination line"
    );
  });

  test("14. DashboardClient JourneyShelfTeaser uses folio-home-editorial-caption for subcopy", () => {
    const start = dashboardClient.indexOf("function JourneyShelfTeaser");
    const end = dashboardClient.indexOf("function EmptyAtelierHome");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("folio-home-editorial-caption"),
      "JourneyShelfTeaser subcopy must use folio-home-editorial-caption for italic serif treatment"
    );
  });

  test("15. DashboardClient AtelierPlanningStrip uses folio-home-editorial-caption (at least 2)", () => {
    const start = dashboardClient.indexOf("function AtelierPlanningStrip");
    const end = dashboardClient.indexOf("// ── Main component");
    const block = dashboardClient.slice(start, end);
    const count = (block.match(/folio-home-editorial-caption/g) || []).length;
    assert.ok(
      count >= 2,
      `AtelierPlanningStrip must use folio-home-editorial-caption on both discovery card subcopy lines, found ${count}`
    );
  });

  test("16. DashboardClient does NOT import MapPin (removed with icon-free card)", () => {
    assert.doesNotMatch(
      dashboardClient,
      /MapPin/,
      "DashboardClient must not import MapPin — removed when ContinuePlanningStrip simplified to text-only layout"
    );
  });

  test("17. DashboardClient AtelierGreeting h1 uses folio-home-greeting-title not text-2xl font-semibold", () => {
    const greetingStart = dashboardClient.indexOf("function AtelierGreeting");
    const greetingEnd = dashboardClient.indexOf("function ConciergeEntry");
    const block = dashboardClient.slice(greetingStart, greetingEnd);
    const h1HasOldClass = /h1[^>]*text-2xl font-semibold/.test(block);
    assert.ok(
      !h1HasOldClass,
      "AtelierGreeting h1 must not use text-2xl font-semibold — should use folio-home-greeting-title"
    );
  });

  test("18. DashboardClient ConciergeEntry h2 text is editorial voice ('Your private concierge.')", () => {
    const start = dashboardClient.indexOf("function ConciergeEntry");
    const end = dashboardClient.indexOf("function ContinuePlanningStrip");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("Your private concierge."),
      "ConciergeEntry h2 must use editorial concierge voice instead of generic 'AI Travel Concierge'"
    );
  });
});

// ── 19. Behavior preservation (testids) ──────────────────────────────────────

describe("Home Folio: behavior preservation", () => {
  test("19a. atelier-greeting testid preserved", () => {
    assert.match(dashboardClient, /data-testid="atelier-greeting"/);
  });

  test("19b. concierge-entry testid preserved", () => {
    assert.match(dashboardClient, /data-testid="concierge-entry"/);
  });

  test("19c. concierge-advisor-desk testid preserved", () => {
    assert.match(dashboardClient, /data-testid="concierge-advisor-desk"/);
  });

  test("19d. atelier-continue-planning testid preserved", () => {
    assert.match(dashboardClient, /data-testid="atelier-continue-planning"/);
  });

  test("19e. journey-shelf-teaser testid preserved", () => {
    assert.match(dashboardClient, /data-testid="journey-shelf-teaser"/);
  });

  test("19f. atelier-planning-strip testid preserved", () => {
    assert.match(dashboardClient, /data-testid="atelier-planning-strip"/);
  });

  test("19g. href=/concierge in ConciergeEntry preserved", () => {
    const start = dashboardClient.indexOf("function ConciergeEntry");
    const end = dashboardClient.indexOf("function ContinuePlanningStrip");
    const block = dashboardClient.slice(start, end);
    assert.match(block, /href="\/concierge"/);
  });

  test("19h. trip.title and trip.destination in ContinuePlanningStrip preserved", () => {
    const start = dashboardClient.indexOf("function ContinuePlanningStrip");
    const end = dashboardClient.indexOf("function JourneyShelfTeaser");
    const block = dashboardClient.slice(start, end);
    assert.match(block, /trip\.title/);
    assert.match(block, /trip\.destination/);
  });

  test("19i. folio-paper-card in ContinuePlanningStrip preserved", () => {
    const start = dashboardClient.indexOf("function ContinuePlanningStrip");
    const end = dashboardClient.indexOf("function JourneyShelfTeaser");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("folio-paper-card"),
      "ContinuePlanningStrip article must keep folio-paper-card class"
    );
  });

  test("19j. mapline-rule preserved in file", () => {
    assert.match(dashboardClient, /mapline-rule/);
  });

  test("19k. editorial-scene preserved on root wrapper", () => {
    assert.match(dashboardClient, /editorial-scene/);
  });
});
