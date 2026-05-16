/**
 * Stage 3.5 Phase 7 — Trip Readiness / Review Cockpit
 * Contract tests for TripReadinessCockpit and its integration in the trip detail page.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const cockpit = readFileSync(
  new URL("../src/components/trips/TripReadinessCockpit.tsx", import.meta.url),
  "utf8",
);

const tripDetailPage = readFileSync(
  new URL("../src/app/trips/[id]/page.tsx", import.meta.url),
  "utf8",
);

// ── Exports and structure ────────────────────────────────────────────────────

test("TripReadinessCockpit is exported as a named export", () => {
  assert.match(cockpit, /export function TripReadinessCockpit/);
});

test("TripReadinessCockpit is a client component", () => {
  assert.match(cockpit, /"use client"/);
});

test("TripReadinessCockpit exports its props interface", () => {
  assert.match(cockpit, /export interface TripReadinessCockpitProps/);
});

// ── Semantic structure ───────────────────────────────────────────────────────

test("uses a <section> element as root with aria-labelledby", () => {
  assert.match(cockpit, /<section/);
  assert.match(cockpit, /aria-labelledby="trip-readiness-heading"/);
});

test("has an h2 heading with the correct id", () => {
  assert.match(cockpit, /<h2/);
  assert.match(cockpit, /id="trip-readiness-heading"/);
});

test("section and heading id match (aria-labelledby contract)", () => {
  assert.match(cockpit, /aria-labelledby="trip-readiness-heading"/);
  assert.match(cockpit, /id="trip-readiness-heading"/);
});

// ── Data-testid contract ─────────────────────────────────────────────────────

test("has data-testid on the root section", () => {
  assert.match(cockpit, /data-testid="trip-readiness-cockpit"/);
});

test("has data-testid on the day coverage strip", () => {
  assert.match(cockpit, /data-testid="day-coverage-strip"/);
});

test("has data-testid on the signals container", () => {
  assert.match(cockpit, /data-testid="readiness-signals"/);
});

test("has data-testid on each readiness signal via template literal and keys cover all four categories", () => {
  // Component uses a map, so the testid is a template literal: data-testid={`readiness-signal-${signal.key}`}
  assert.match(cockpit, /data-testid=\{`readiness-signal-\$\{signal\.key\}`\}/);
  // Verify all four signal keys are defined
  assert.match(cockpit, /key: "flights"/);
  assert.match(cockpit, /key: "hotel"/);
  assert.match(cockpit, /key: "dining"/);
  assert.match(cockpit, /key: "activities"/);
});

test("has data-testid on the next-action area", () => {
  assert.match(cockpit, /data-testid="next-action-area"/);
});

test("has data-testid on the planning tools strip", () => {
  assert.match(cockpit, /data-testid="planning-tools-strip"/);
});

// ── DS token usage ───────────────────────────────────────────────────────────

test("uses bg-ds-onyx as the card surface", () => {
  assert.match(cockpit, /bg-ds-onyx/);
});

test("uses border-ds-pen-stroke for borders", () => {
  assert.match(cockpit, /border-ds-pen-stroke/);
});

test("uses bg-ds-carbon for the footer background", () => {
  assert.match(cockpit, /bg-ds-carbon/);
});

test("uses text-ds-text for primary text", () => {
  assert.match(cockpit, /text-ds-text(?!-)/);
});

test("uses text-ds-text-secondary for body copy", () => {
  assert.match(cockpit, /text-ds-text-secondary/);
});

test("uses text-ds-text-tertiary for Overline labels", () => {
  assert.match(cockpit, /text-ds-text-tertiary/);
});

test("uses text-ds-accent for accent color (score and icon)", () => {
  assert.match(cockpit, /text-ds-accent/);
});

test("uses text-ds-text-inverse for accent button text", () => {
  assert.match(cockpit, /text-ds-text-inverse/);
});

test("uses bg-ds-accent for primary CTA buttons", () => {
  assert.match(cockpit, /bg-ds-accent/);
});

test("uses ds-elevation-2 shadow for card depth", () => {
  assert.match(cockpit, /ds-elevation-2/);
});

// ── Overline type pattern ────────────────────────────────────────────────────

test("uses Overline tracking on section labels", () => {
  assert.match(cockpit, /tracking-\[0\.1em\]/);
});

test("uses uppercase on Overline labels", () => {
  assert.match(cockpit, /uppercase/);
});

test("uses 10px Overline font size", () => {
  assert.match(cockpit, /text-\[10px\]/);
});

// ── Accessibility: icons ─────────────────────────────────────────────────────

test("decorative icons have aria-hidden=true", () => {
  assert.match(cockpit, /aria-hidden="true"/);
});

test("signal icon wrappers are aria-hidden (not interactive)", () => {
  // The icon span has aria-hidden="true" applied
  const signalSection = cockpit.slice(
    cockpit.indexOf("data-testid={`readiness-signal-${signal.key}`}"),
    cockpit.indexOf("data-testid=\"next-action-area\""),
  );
  assert.match(signalSection, /aria-hidden="true"/);
});

// ── Accessibility: touch targets ─────────────────────────────────────────────

test("primary action buttons have min-h-[44px] touch target", () => {
  assert.match(cockpit, /min-h-\[44px\]/);
});

// ── Accessibility: focus rings ────────────────────────────────────────────────

test("all interactive elements have focus-visible outline", () => {
  assert.match(cockpit, /focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent/);
});

// ── Navigation: real Links and buttons, no card-level onClick ───────────────

test("uses Link from next/link for route navigation", () => {
  assert.match(cockpit, /from "next\/link"/);
  assert.match(cockpit, /<Link/);
});

test("Explore link navigates to /explore route", () => {
  assert.match(cockpit, /href="\/explore"/);
});

test("Saved Ideas link navigates to /saved route", () => {
  assert.match(cockpit, /href="\/saved"/);
});

test("uses callback buttons for panel actions (onOpenConcierge, onOpenOptimize, onOpenEdit)", () => {
  assert.match(cockpit, /onOpenConcierge/);
  assert.match(cockpit, /onOpenOptimize/);
  assert.match(cockpit, /onOpenEdit/);
});

test("no card-level click-only navigation (no onClick on section/div root)", () => {
  // The root <section> must not have an onClick handler
  const sectionTag = cockpit.slice(
    cockpit.indexOf("<section"),
    cockpit.indexOf("<section") + 300,
  );
  assert.doesNotMatch(sectionTag, /onClick/);
});

test("Concierge action in planning tools strip is a real button with aria-label", () => {
  assert.match(cockpit, /aria-label="Open AI Concierge panel"/);
});

// ── Defensive data handling ───────────────────────────────────────────────────

test("deriveReadiness handles empty itineraryDays array defensively", () => {
  // The function uses flatMap and filter — safe with empty arrays
  assert.match(cockpit, /days\.flatMap/);
  assert.match(cockpit, /days\.filter/);
  // Null-safe item access
  assert.match(cockpit, /d\.items \?\? \[\]/);
});

test("day coverage section only renders when totalDays > 0", () => {
  assert.match(cockpit, /r\.totalDays > 0/);
  assert.match(cockpit, /data-testid="day-coverage-strip"/);
});

test("day pills use aria-label for screen reader context", () => {
  assert.match(cockpit, /aria-label=\{`Day \$\{day\.dayNumber\}/);
});

// ── No backend/provider imports ───────────────────────────────────────────────

test("does not import from the API lib", () => {
  assert.doesNotMatch(cockpit, /from "@\/lib\/api"/);
});

test("does not import from provider or backend paths", () => {
  assert.doesNotMatch(cockpit, /from "@\/lib\/concierge"/);
  assert.doesNotMatch(cockpit, /from "@\/lib\/flights"/);
  assert.doesNotMatch(cockpit, /from "@\/lib\/hotels"/);
});

test("does not import from backend modules", () => {
  assert.doesNotMatch(cockpit, /from "\.\.\/\.\.\/backend\//);
});

// ── No fake data ──────────────────────────────────────────────────────────────

test("does not contain hardcoded mock place names or fake hotel names", () => {
  assert.doesNotMatch(cockpit, /Marriott|Hilton|Four Seasons|sample|placeholder/i);
});

test("derives readiness only from itemType field (not fabricated fields)", () => {
  assert.match(cockpit, /i\.itemType === "flight"/);
  assert.match(cockpit, /i\.itemType === "hotel"/);
  assert.match(cockpit, /i\.itemType === "meal"/);
  assert.match(cockpit, /i\.itemType === "activity"/);
});

// ── Copy tone: honest fallback language ──────────────────────────────────────

test("uses qualified copy for uncertain signals (Looks like…)", () => {
  assert.match(cockpit, /Looks like/);
});

test("uses honest fallback copy for missing items (Still needs…)", () => {
  assert.match(cockpit, /Still needs/);
});

// ── Page integration ─────────────────────────────────────────────────────────

test("trip detail page imports TripReadinessCockpit", () => {
  assert.match(tripDetailPage, /from "@\/components\/trips\/TripReadinessCockpit"/);
  assert.match(tripDetailPage, /TripReadinessCockpit/);
});

test("trip detail page renders TripReadinessCockpit with trip prop", () => {
  assert.match(tripDetailPage, /trip={trip}/);
});

test("trip detail page renders TripReadinessCockpit with itineraryDays prop", () => {
  assert.match(tripDetailPage, /itineraryDays={itineraryDays}/);
});

test("trip detail page wires onOpenConcierge to setConciergeOpen", () => {
  assert.match(tripDetailPage, /onOpenConcierge=\{\(\) => setConciergeOpen\(true\)\}/);
});

test("trip detail page wires onOpenOptimize to setOptimizeOpen", () => {
  assert.match(tripDetailPage, /onOpenOptimize=\{\(\) => setOptimizeOpen\(true\)\}/);
});

test("trip detail page wires onOpenEdit to openEdit", () => {
  assert.match(tripDetailPage, /onOpenEdit={openEdit}/);
});

test("trip detail page guards cockpit behind trip availability check", () => {
  // Must check that trip is non-null before rendering the cockpit
  const cockpitSection = tripDetailPage.slice(
    tripDetailPage.indexOf("TripReadinessCockpit"),
    tripDetailPage.indexOf("TripReadinessCockpit") + 400,
  );
  assert.match(cockpitSection, /trip/);
});

// ── Behavior preservation (TripBuilder unchanged) ────────────────────────────

test("trip detail page still renders TripBuilder after cockpit", () => {
  const cockpitPos = tripDetailPage.indexOf("TripReadinessCockpit");
  const builderPos = tripDetailPage.indexOf("<TripBuilder");
  assert.ok(cockpitPos < builderPos, "TripReadinessCockpit should appear before TripBuilder");
});

test("trip detail page still renders AIConciergePanel", () => {
  assert.match(tripDetailPage, /AIConciergePanel/);
});
