/**
 * Home Mobile Folio Redesign — Architecture Slice
 * Verifies that the Home screen redesign uses canonical Folio primitives
 * (not Home-only orphan classes), and that all behavior is preserved.
 *
 * What this covers:
 *  1-13.  globals.css canonical primitives exist with correct properties.
 * 14-29.  DashboardClient adopts canonical primitives (no orphan folio-home-* classes).
 * 30-40.  Behavior preservation (testids, routes, data bindings).
 */

import test, { describe } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

function readSrc(rel) {
  return readFileSync(new URL(`../src/${rel}`, import.meta.url), "utf8");
}

const globalsCss = readSrc("app/globals.css");
const dashboardClient = readSrc("components/dashboard/DashboardClient.tsx");

// ── 1–13. Canonical CSS primitives ──────────────────────────────────────────

describe("Home Folio: canonical CSS primitives exist", () => {
  test("1. globals.css defines .folio-display", () => {
    assert.ok(
      globalsCss.includes(".folio-display"),
      "globals.css must define .folio-display for the editorial display heading"
    );
  });

  test("2. folio-display uses var(--ds-font-editorial)", () => {
    const idx = globalsCss.indexOf(".folio-display {");
    assert.ok(idx !== -1, ".folio-display block must exist");
    const block = globalsCss.slice(idx, idx + 300);
    assert.ok(
      block.includes("var(--ds-font-editorial)"),
      "folio-display must use var(--ds-font-editorial) for Fraunces variable serif"
    );
  });

  test("3. folio-display has font-weight: 300", () => {
    const idx = globalsCss.indexOf(".folio-display {");
    const block = globalsCss.slice(idx, idx + 300);
    assert.ok(
      block.includes("font-weight: 300"),
      "folio-display must use font-weight: 300 (light italic display)"
    );
  });

  test("4. folio-display has font-style: italic", () => {
    const idx = globalsCss.indexOf(".folio-display {");
    const block = globalsCss.slice(idx, idx + 300);
    assert.ok(
      block.includes("font-style: italic"),
      "folio-display must use font-style: italic"
    );
  });

  test("5. globals.css defines .folio-issue-eyebrow", () => {
    assert.ok(
      globalsCss.includes(".folio-issue-eyebrow"),
      "globals.css must define .folio-issue-eyebrow for brass masthead opener"
    );
  });

  test("6. folio-issue-eyebrow has ::before brass rule", () => {
    assert.ok(
      globalsCss.includes(".folio-issue-eyebrow::before"),
      "folio-issue-eyebrow must have ::before pseudo-element for brass rule"
    );
  });

  test("7. globals.css defines .folio-caption", () => {
    assert.ok(
      globalsCss.includes(".folio-caption"),
      "globals.css must define .folio-caption for 13px italic serif subcopy"
    );
  });

  test("8. folio-caption has font-style: italic", () => {
    const idx = globalsCss.indexOf(".folio-caption {");
    assert.ok(idx !== -1, ".folio-caption block must exist");
    const block = globalsCss.slice(idx, idx + 250);
    assert.ok(
      block.includes("font-style: italic"),
      "folio-caption must use font-style: italic"
    );
  });

  test("9. globals.css defines .folio-heading", () => {
    assert.ok(
      globalsCss.includes(".folio-heading"),
      "globals.css must define .folio-heading for section-level Fraunces italic headings"
    );
  });

  test("10. folio-heading uses var(--ds-font-editorial)", () => {
    const idx = globalsCss.indexOf(".folio-heading {");
    assert.ok(idx !== -1, ".folio-heading block must exist");
    const block = globalsCss.slice(idx, idx + 300);
    assert.ok(
      block.includes("var(--ds-font-editorial)"),
      "folio-heading must use var(--ds-font-editorial)"
    );
  });

  test("11. globals.css defines .folio-editorial-sub", () => {
    assert.ok(
      globalsCss.includes(".folio-editorial-sub"),
      "globals.css must define .folio-editorial-sub for editorial subline"
    );
  });

  test("12. globals.css defines .folio-serial", () => {
    assert.ok(
      globalsCss.includes(".folio-serial"),
      "globals.css must define .folio-serial for small-caps brass serial stamps"
    );
  });

  test("13. globals.css defines .folio-card-title", () => {
    assert.ok(
      globalsCss.includes(".folio-card-title"),
      "globals.css must define .folio-card-title for card-level Fraunces title"
    );
  });
});

// ── 14–29. DashboardClient canonical adoption ─────────────────────────────

describe("Home Folio: DashboardClient uses canonical primitives", () => {
  test("14. AtelierGreeting h1 uses folio-display (not a plain Tailwind size class)", () => {
    const start = dashboardClient.indexOf("function AtelierGreeting");
    const end = dashboardClient.indexOf("function ConciergeEntry");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("folio-display"),
      "AtelierGreeting h1 must use folio-display canonical class"
    );
  });

  test("15. AtelierGreeting uses folio-issue-eyebrow for brass masthead line", () => {
    const start = dashboardClient.indexOf("function AtelierGreeting");
    const end = dashboardClient.indexOf("function ConciergeEntry");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("folio-issue-eyebrow"),
      "AtelierGreeting must include folio-issue-eyebrow for brass masthead"
    );
  });

  test("16. AtelierGreeting uses folio-editorial-sub for subline", () => {
    const start = dashboardClient.indexOf("function AtelierGreeting");
    const end = dashboardClient.indexOf("function ConciergeEntry");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("folio-editorial-sub"),
      "AtelierGreeting must use folio-editorial-sub for the editorial subline"
    );
  });

  test("17. ConciergeEntry h2 uses folio-heading (canonical section heading)", () => {
    const start = dashboardClient.indexOf("function ConciergeEntry");
    const end = dashboardClient.indexOf("function ContinuePlanningStrip");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("folio-heading"),
      "ConciergeEntry h2 must use folio-heading canonical class"
    );
  });

  test("18. ConciergeEntry uses btn-marine (marine ink CTA, not gold fill)", () => {
    const start = dashboardClient.indexOf("function ConciergeEntry");
    const end = dashboardClient.indexOf("function ContinuePlanningStrip");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("btn-marine"),
      "ConciergeEntry CTA must use btn-marine per folio direction (gold is foil-only)"
    );
  });

  test("19. ConciergeEntry uses folio-caption for card subcopy", () => {
    const start = dashboardClient.indexOf("function ConciergeEntry");
    const end = dashboardClient.indexOf("function ContinuePlanningStrip");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("folio-caption"),
      "ConciergeEntry subcopy must use folio-caption canonical class"
    );
  });

  test("20. ContinuePlanningStrip uses folio-card-title for trip name", () => {
    const start = dashboardClient.indexOf("function ContinuePlanningStrip");
    const end = dashboardClient.indexOf("function JourneyShelfTeaser");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("folio-card-title"),
      "ContinuePlanningStrip trip name must use folio-card-title"
    );
  });

  test("21. ContinuePlanningStrip uses folio-caption for destination line", () => {
    const start = dashboardClient.indexOf("function ContinuePlanningStrip");
    const end = dashboardClient.indexOf("function JourneyShelfTeaser");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("folio-caption"),
      "ContinuePlanningStrip destination must use folio-caption"
    );
  });

  test("22. ContinuePlanningStrip uses folio-serial for date/status stamp", () => {
    const start = dashboardClient.indexOf("function ContinuePlanningStrip");
    const end = dashboardClient.indexOf("function JourneyShelfTeaser");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("folio-serial"),
      "ContinuePlanningStrip must use folio-serial for date/status metadata"
    );
  });

  test("23. JourneyShelfTeaser uses folio-caption for subcopy", () => {
    const start = dashboardClient.indexOf("function JourneyShelfTeaser");
    const end = dashboardClient.indexOf("function EmptyAtelierHome");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("folio-caption"),
      "JourneyShelfTeaser subcopy must use folio-caption"
    );
  });

  test("24. JourneyShelfTeaser uses folio-serial for archive stamp", () => {
    const start = dashboardClient.indexOf("function JourneyShelfTeaser");
    const end = dashboardClient.indexOf("function EmptyAtelierHome");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("folio-serial"),
      "JourneyShelfTeaser must use folio-serial for the archive entry stamp"
    );
  });

  test("25. AtelierPlanningStrip uses folio-caption on both discovery cards (at least 2)", () => {
    const start = dashboardClient.indexOf("function AtelierPlanningStrip");
    const end = dashboardClient.indexOf("// ── Main component");
    const block = dashboardClient.slice(start, end);
    const count = (block.match(/folio-caption/g) || []).length;
    assert.ok(
      count >= 2,
      `AtelierPlanningStrip must use folio-caption on both discovery card subcopy lines, found ${count}`
    );
  });

  test("26. AtelierPlanningStrip uses folio-serial on both discovery cards (at least 2)", () => {
    const start = dashboardClient.indexOf("function AtelierPlanningStrip");
    const end = dashboardClient.indexOf("// ── Main component");
    const block = dashboardClient.slice(start, end);
    const count = (block.match(/folio-serial/g) || []).length;
    assert.ok(
      count >= 2,
      `AtelierPlanningStrip must use folio-serial on both discovery card number serials, found ${count}`
    );
  });

  test("27. DashboardClient does NOT import MapPin", () => {
    assert.doesNotMatch(
      dashboardClient,
      /MapPin/,
      "DashboardClient must not import MapPin — icon-free redesign"
    );
  });

  test("28. ConciergeEntry h2 has editorial voice text", () => {
    const start = dashboardClient.indexOf("function ConciergeEntry");
    const end = dashboardClient.indexOf("function ContinuePlanningStrip");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("Your private concierge."),
      "ConciergeEntry h2 must use editorial voice 'Your private concierge.'"
    );
  });

  test("29. DashboardClient does NOT use orphan folio-home-* typography classes", () => {
    assert.doesNotMatch(
      dashboardClient,
      /folio-home-greeting-title|folio-home-hero-sub|folio-home-issue-eyebrow|folio-home-editorial-caption|folio-home-serial|folio-home-trip-title|folio-home-concierge-card-accent|folio-home-concierge-serif/,
      "DashboardClient must use canonical Folio primitives, not orphan folio-home-* typography classes"
    );
  });
});

// ── 30–40. Behavior preservation ─────────────────────────────────────────

describe("Home Folio: behavior preservation", () => {
  test("30. atelier-greeting testid preserved", () => {
    assert.match(dashboardClient, /data-testid="atelier-greeting"/);
  });

  test("31. concierge-entry testid preserved", () => {
    assert.match(dashboardClient, /data-testid="concierge-entry"/);
  });

  test("32. concierge-advisor-desk testid preserved", () => {
    assert.match(dashboardClient, /data-testid="concierge-advisor-desk"/);
  });

  test("33. atelier-continue-planning testid preserved", () => {
    assert.match(dashboardClient, /data-testid="atelier-continue-planning"/);
  });

  test("34. journey-shelf-teaser testid preserved", () => {
    assert.match(dashboardClient, /data-testid="journey-shelf-teaser"/);
  });

  test("35. atelier-planning-strip testid preserved", () => {
    assert.match(dashboardClient, /data-testid="atelier-planning-strip"/);
  });

  test("36. href=/concierge in ConciergeEntry preserved", () => {
    const start = dashboardClient.indexOf("function ConciergeEntry");
    const end = dashboardClient.indexOf("function ContinuePlanningStrip");
    const block = dashboardClient.slice(start, end);
    assert.match(block, /href="\/concierge"/);
  });

  test("37. trip.title and trip.destination in ContinuePlanningStrip preserved", () => {
    const start = dashboardClient.indexOf("function ContinuePlanningStrip");
    const end = dashboardClient.indexOf("function JourneyShelfTeaser");
    const block = dashboardClient.slice(start, end);
    assert.match(block, /trip\.title/);
    assert.match(block, /trip\.destination/);
  });

  test("38. folio-paper-card in ContinuePlanningStrip preserved", () => {
    const start = dashboardClient.indexOf("function ContinuePlanningStrip");
    const end = dashboardClient.indexOf("function JourneyShelfTeaser");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("folio-paper-card"),
      "ContinuePlanningStrip article must keep folio-paper-card class"
    );
  });

  test("39. mapline-rule preserved in AtelierGreeting", () => {
    assert.match(dashboardClient, /mapline-rule/);
  });

  test("40. editorial-scene preserved on root wrapper", () => {
    assert.match(dashboardClient, /editorial-scene/);
  });
});
