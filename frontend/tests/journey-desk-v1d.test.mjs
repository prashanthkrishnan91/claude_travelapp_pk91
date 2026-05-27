/**
 * Journey Desk v1D — workspace consolidation + polish.
 *
 * Makes Trip Detail read as one coherent Journey Desk. Updated for Journey Desk
 * PR 1: the legacy readiness cockpit is now REMOVED from the page (not merely
 * demoted), and the desktop overview is a two-zone planning desk (Plan Rail +
 * Working Surface) rather than a centered max-width column. The decision-strip
 * copy is honest about trip-level vs day-level ideas; an "Edit in Itinerary"
 * fallback points to the legacy tab; duplicate tray launchers stay gone.
 *
 * Source-scan contract tests (no DOM/browser in this environment).
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const page = readFileSync(
  new URL("../src/app/trips/[id]/page.tsx", import.meta.url),
  "utf8",
);
const panel = readFileSync(
  new URL("../src/components/trips/ExpandedDayPanel.tsx", import.meta.url),
  "utf8",
);
const tray = readFileSync(
  new URL("../src/components/trips/IdeasTray.tsx", import.meta.url),
  "utf8",
);

// ── Journey Desk PR 1: the legacy readiness cockpit is removed from the page ──
// (it duplicated the Brief + Dayboard signal and was mobile noise — see blueprint
//  docs/ai/design/JOURNEY_DESK_PAGE_DIRECTION_AND_BLUEPRINT.md §4).

test("the readiness cockpit + its disclosure are removed from the page", () => {
  assert.doesNotMatch(page, /cockpitOpen/);
  assert.doesNotMatch(page, /data-testid="trip-readiness-toggle"/);
  assert.doesNotMatch(page, /<TripReadinessCockpit/);
  assert.doesNotMatch(page, /Trip readiness · concierge notes/);
});

test("cover → Brief → builder order preserved (no cockpit between them)", () => {
  const cover = page.indexOf('data-testid="trip-chapter-cover"');
  const brief = page.indexOf("<TripBrief");
  const builder = page.indexOf("<TripBuilder");
  assert.ok(cover < brief && brief < builder, "cover < Brief < builder order preserved");
});

// ── Decision strip copy honesty (trip-level, not day-specific) ────────────────

test("decision strip copy is honest about trip-level ideas (no implied day filter)", () => {
  assert.match(panel, /still in the tray/);
  assert.doesNotMatch(panel, /ideas? not placed/);
  assert.doesNotMatch(panel, /Still deciding/);
});

// ── Edit-in-Itinerary fallback to the legacy tab ──────────────────────────────

test("expanded day offers a quiet 'Edit in Itinerary' fallback to the legacy tab", () => {
  assert.match(panel, /data-testid="jd-day-edit-in-itinerary"/);
  assert.match(panel, /Edit in Itinerary/);
  assert.match(page, /onEditInItinerary=\{\(\) => setActiveMobileWorkspace\("itinerary"\)\}/);
});

// ── No duplicate launchers; one tray entry point ──────────────────────────────

test("no duplicate Journey Desk tray launcher (Brief 'Review ideas' is the entry)", () => {
  assert.doesNotMatch(page, /journey-desk-ideas-launcher/);
  // Brief's review action switches to the canonical Ideas tab (IA pivot, PR #481).
  assert.match(page, /onReview=\{\(\) => setActiveMobileWorkspace\("ideas"\)\}/);
});

// ── Legacy fallback remains available ─────────────────────────────────────────

test("legacy Itinerary/Ideas tabs remain (Build reached via Add-to-Day handoff, PR #478)", () => {
  assert.match(page, /<TripBuilder/);
  // Build is no longer a mobile tab (removed in #478); it's reached via Add-to-Day.
  assert.match(page, /trip-mobile-tab-itinerary/);
  assert.match(page, /trip-mobile-tab-ideas/);
  // Ideas Tray still links into the legacy Ideas workspace for fuller management.
  assert.match(tray, /Manage in Ideas/);
});

// ── Desktop two-zone planning desk (Journey Desk PR 1) ────────────────────────

test("desktop lays out a Plan Rail + Working Surface (no narrow max-w-4xl cap)", () => {
  // The old centered max-w-4xl cap is gone; the brief panel is now the Plan Rail.
  assert.doesNotMatch(page, /lg:max-w-4xl/);
  assert.match(page, /journey-desk-layout/);
  assert.match(page, /trip-mobile-panel-brief[\s\S]{0,160}journey-desk-plan-rail/);
  // brief panel still uses the 8K hidden/lg:block visibility contract
  assert.match(page, /activeMobileWorkspace !== "brief" \? "hidden lg:block" : ""/);
});

// ── v1A/v1B/v1C surfaces preserved ────────────────────────────────────────────

test("v1A/v1B/v1C surfaces are not regressed", () => {
  assert.match(page, /data-testid="trip-chapter-cover"/);
  assert.match(page, /<TripBrief/);
  assert.match(page, /<Dayboard/);
  assert.match(page, /<ExpandedDayPanel/);
  assert.match(page, /<IdeasTray/);
});
