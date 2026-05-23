/**
 * Journey Desk v1D — workspace consolidation + polish.
 *
 * Makes Trip Detail read as one coherent Journey Desk: the legacy readiness
 * cockpit is demoted below the Journey Desk flow into a quiet collapsed
 * disclosure; the decision-strip copy is honest about trip-level vs day-level
 * ideas; an "Edit in Itinerary" fallback points to the legacy tab; duplicate
 * tray launchers stay gone; and the desktop overview gets an editorial
 * max-width. Legacy Build/Itinerary/Ideas tabs remain as fallback.
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

// ── Journey Desk is primary; cockpit demoted to a quiet collapsed disclosure ──

test("the readiness cockpit is demoted to a collapsed secondary disclosure", () => {
  assert.match(page, /const \[cockpitOpen,\s*setCockpitOpen\]\s*=\s*useState\(false\)/);
  assert.match(page, /data-testid="trip-readiness-toggle"/);
  assert.match(page, /aria-expanded=\{cockpitOpen\}/);
  // The cockpit only renders when expanded (no longer competing above the fold).
  assert.match(page, /\{cockpitOpen && \([\s\S]{0,200}<TripReadinessCockpit/);
});

test("cockpit is still wired + ordered (regression: cover < cockpit < builder)", () => {
  assert.match(page, /<TripReadinessCockpit[\s\S]{0,200}onOpenConcierge=\{\(\) => setConciergeOpen\(true\)\}/);
  const cover = page.indexOf('data-testid="trip-chapter-cover"');
  const cockpit = page.indexOf("<TripReadinessCockpit");
  const builder = page.indexOf("<TripBuilder");
  assert.ok(cover < cockpit && cockpit < builder, "cover < cockpit < builder order preserved");
  assert.match(page, /editorial-section-rule/);
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
  assert.match(page, /onReview=\{\(\) => setIdeasTrayOpen\(true\)\}/);
});

// ── Legacy fallback remains available ─────────────────────────────────────────

test("legacy Build/Itinerary/Ideas tabs remain as fallback", () => {
  assert.match(page, /<TripBuilder/);
  assert.match(page, /trip-mobile-tab-build/);
  assert.match(page, /trip-mobile-tab-itinerary/);
  assert.match(page, /trip-mobile-tab-ideas/);
  // Ideas Tray still links into the legacy Ideas workspace for fuller management.
  assert.match(tray, /Manage in Ideas/);
});

// ── Desktop editorial adaptation (no full rewrite, no four-column) ────────────

test("desktop gives the Journey Desk overview a centered editorial max-width", () => {
  assert.match(page, /trip-mobile-panel-brief[\s\S]{0,160}lg:max-w-4xl lg:mx-auto/);
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
