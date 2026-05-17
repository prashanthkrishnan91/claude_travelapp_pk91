/**
 * Stage 3.5 Phase 6 — Premium My Trips / Journey Dashboard
 * Contract tests for the redesigned trips page and dashboard components.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const tripsPage = readFileSync(
  new URL("../src/app/trips/page.tsx", import.meta.url),
  "utf8",
);
const recentTrips = readFileSync(
  new URL("../src/components/dashboard/RecentTrips.tsx", import.meta.url),
  "utf8",
);
const quickActions = readFileSync(
  new URL("../src/components/dashboard/QuickActions.tsx", import.meta.url),
  "utf8",
);
const dashboardClient = readFileSync(
  new URL("../src/components/dashboard/DashboardClient.tsx", import.meta.url),
  "utf8",
);

// ── trips/page.tsx — ds-* token contract ─────────────────────────────────────

test("trips page uses Card primitive (not bare .card class for trip content)", () => {
  assert.match(tripsPage, /from "@\/components\/ui\/Card"/);
  assert.match(tripsPage, /<Card/);
});

test("trips page uses Skeleton for loading state", () => {
  assert.match(tripsPage, /from "@\/components\/ui\/Skeleton"/);
  assert.match(tripsPage, /<Skeleton/);
});

test("trips page loading state has aria-busy for accessibility", () => {
  assert.match(tripsPage, /aria-busy="true"/);
});

test("trips page uses ds-* surface tokens (not raw dark-/cream- colors for structure)", () => {
  assert.match(tripsPage, /bg-ds-carbon|bg-ds-onyx|border-ds-pen-stroke/);
  assert.match(tripsPage, /text-ds-text/);
  assert.match(tripsPage, /text-ds-text-tertiary/);
});

test("trips page uses ds-accent tokens for icon backgrounds", () => {
  assert.match(tripsPage, /bg-ds-accent-subtle/);
  assert.match(tripsPage, /text-ds-accent/);
});

test("trips page has Overline section labels", () => {
  assert.match(tripsPage, /tracking-\[0\.1em\]/);
  assert.match(tripsPage, /uppercase/);
});

test("trips page has Continue Planning section", () => {
  assert.match(tripsPage, /Continue planning/i);
  assert.match(tripsPage, /ContinuePlanningHero/);
});

test("trips page ContinuePlanningHero uses elevation or boutique surface token", () => {
  assert.ok(
    tripsPage.includes("ds-elevation-2") || tripsPage.includes("boutique-instrument"),
    "ContinuePlanningHero must use ds-elevation-2 or boutique-instrument surface class"
  );
});

test("ContinuePlanningHero accepts onEdit and onDelete props", () => {
  assert.match(tripsPage, /ContinuePlanningHeroProps/);
  assert.match(tripsPage, /onEdit: \(trip: Trip\) => void/);
  assert.match(tripsPage, /onDelete: \(id: string\) => void/);
});

test("ContinuePlanningHero exposes an edit button with aria-label", () => {
  const heroSection = tripsPage.slice(
    tripsPage.indexOf("function ContinuePlanningHero"),
    tripsPage.indexOf("function JourneyCard"),
  );
  assert.match(heroSection, /onEdit\(trip\)/);
  assert.match(heroSection, /aria-label=\{`Edit \$\{trip\.title\}`\}/);
});

test("ContinuePlanningHero exposes a delete button with aria-label", () => {
  const heroSection = tripsPage.slice(
    tripsPage.indexOf("function ContinuePlanningHero"),
    tripsPage.indexOf("function JourneyCard"),
  );
  assert.match(heroSection, /onDelete\(trip\.id\)/);
  assert.match(heroSection, /aria-label=\{`Delete \$\{trip\.title\}`\}/);
});

test("ContinuePlanningHero edit/delete buttons have 44px touch targets", () => {
  const heroSection = tripsPage.slice(
    tripsPage.indexOf("function ContinuePlanningHero"),
    tripsPage.indexOf("function JourneyCard"),
  );
  assert.match(heroSection, /min-h-\[44px\]/);
  assert.match(heroSection, /min-w-\[44px\]/);
});

test("ContinuePlanningHero edit button uses ds-text-tertiary token", () => {
  const heroSection = tripsPage.slice(
    tripsPage.indexOf("function ContinuePlanningHero"),
    tripsPage.indexOf("function JourneyCard"),
  );
  assert.match(heroSection, /text-ds-text-tertiary/);
});

test("ContinuePlanningHero delete button uses ds-warning token", () => {
  const heroSection = tripsPage.slice(
    tripsPage.indexOf("function ContinuePlanningHero"),
    tripsPage.indexOf("function JourneyCard"),
  );
  assert.match(heroSection, /ds-warning/);
});

test("ContinuePlanningHero open action is a real Link (not only article onClick)", () => {
  const heroSection = tripsPage.slice(
    tripsPage.indexOf("function ContinuePlanningHero"),
    tripsPage.indexOf("function JourneyCard"),
  );
  assert.match(heroSection, /href=\{`\/trips\/\$\{trip\.id\}`\}/);
  assert.doesNotMatch(heroSection, /onClick=\{\(\) => router\.push/);
});

test("ContinuePlanningHero is wired with onEdit and onDelete at call site", () => {
  assert.match(tripsPage, /ContinuePlanningHero[\s\S]{0,200}onEdit=\{openEdit\}/);
  assert.match(tripsPage, /ContinuePlanningHero[\s\S]{0,200}onDelete=\{/);
});

test("trips page has pickContinuePlanning helper that sorts by status priority", () => {
  assert.match(tripsPage, /pickContinuePlanning/);
  assert.match(tripsPage, /STATUS_PRIORITY/);
  assert.match(tripsPage, /researching.*0|0.*researching/);
});

test("trips page has premium empty state with editorial copy", () => {
  assert.match(tripsPage, /EmptyDashboard/);
  assert.match(tripsPage, /Your journey starts here/);
});

test("trips page empty state has Plan a Trip and AI Concierge action cards", () => {
  assert.match(tripsPage, /Plan a Trip/);
  assert.match(tripsPage, /Ask the AI Concierge/);
});

test("trips page empty state links to /concierge and /saved", () => {
  assert.match(tripsPage, /href="\/concierge"/);
  assert.match(tripsPage, /href="\/saved"/);
});

test("trips page has Planning Tools strip with Concierge, Saved Ideas, Explore links", () => {
  assert.match(tripsPage, /PlanningToolsStrip/);
  assert.match(tripsPage, /Planning tools/i);
  assert.match(tripsPage, /href="\/explore"/);
});

test("trips page journey cards have 44px min touch targets on action buttons", () => {
  assert.match(tripsPage, /min-h-\[44px\]/);
  assert.match(tripsPage, /min-w-\[44px\]/);
});

test("JourneyCard has a real Link to open the trip (not router.push)", () => {
  const cardSection = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.match(cardSection, /href=\{`\/trips\/\$\{trip\.id\}`\}/);
  assert.doesNotMatch(cardSection, /onClick=\{\(\) => router\.push/);
});

test("JourneyCard edit and delete buttons have aria-labels", () => {
  const cardSection = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.match(cardSection, /aria-label=\{`Edit \$\{trip\.title\}`\}/);
  assert.match(cardSection, /aria-label=\{`Delete \$\{trip\.title\}`\}/);
});

test("JourneyCard edit and delete buttons have 44px touch targets", () => {
  const cardSection = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.match(cardSection, /min-h-\[44px\]/);
  assert.match(cardSection, /min-w-\[44px\]/);
});

test("trips page groups trips with getTripStatusGroup", () => {
  assert.match(tripsPage, /getTripStatusGroup/);
});

test("trips page TripStatusBadge uses getDisplayTripStatus", () => {
  assert.match(tripsPage, /TripStatusBadge status=\{getDisplayTripStatus\(trip\)\}/);
});

test("trips page edit modal uses Card primitive and ds-elevation-4", () => {
  assert.match(tripsPage, /EditModal/);
  assert.match(tripsPage, /ds-elevation-4/);
});

test("trips page delete modal uses ds-warning token (not hardcoded rose colors)", () => {
  assert.match(tripsPage, /DeleteModal/);
  assert.match(tripsPage, /ds-warning/);
});

test("trips page toast uses ds-onyx and ds-pen-stroke tokens", () => {
  assert.match(tripsPage, /bg-ds-onyx/);
  assert.match(tripsPage, /border-ds-pen-stroke/);
});

test("trips page toast has role=status and aria-live for accessibility", () => {
  assert.match(tripsPage, /role="status"/);
  assert.match(tripsPage, /aria-live="polite"/);
});

test("trips page has no console.log statements", () => {
  assert.doesNotMatch(tripsPage, /console\.log/);
});

test("trips page page title changed to My Journeys", () => {
  assert.match(tripsPage, /My Journeys/);
});

test("trips page CTA button has Plan a Trip label", () => {
  assert.match(tripsPage, /Plan a Trip/);
});

// ── RecentTrips.tsx — ds-* token contract ────────────────────────────────────

test("RecentTrips uses Card primitive", () => {
  assert.match(recentTrips, /from "@\/components\/ui\/Card"/);
  assert.match(recentTrips, /<Card/);
});

test("RecentTrips uses ds-pen-stroke for dividers", () => {
  assert.match(recentTrips, /divide-ds-pen-stroke|border-ds-pen-stroke/);
});

test("RecentTrips uses ds-accent for icon and link colors", () => {
  assert.match(recentTrips, /text-ds-accent/);
  assert.match(recentTrips, /bg-ds-accent-subtle/);
});

test("RecentTrips uses ds-carbon for hover state", () => {
  assert.match(recentTrips, /hover:bg-ds-carbon|hover:border-ds-accent/);
});

test("RecentTrips uses getDisplayTripStatus for badge status", () => {
  assert.match(recentTrips, /getDisplayTripStatus\(trip\)/);
});

test("RecentTrips uses ds-text tokens for text hierarchy", () => {
  assert.match(recentTrips, /text-ds-text/);
  assert.match(recentTrips, /text-ds-text-secondary/);
  assert.match(recentTrips, /text-ds-text-tertiary/);
});

// ── QuickActions.tsx — ds-* token contract ───────────────────────────────────

test("QuickActions uses Card primitive", () => {
  assert.match(quickActions, /from "@\/components\/ui\/Card"/);
  assert.match(quickActions, /<Card/);
});

test("QuickActions uses ds-pen-stroke and ds-carbon tokens", () => {
  assert.match(quickActions, /border-ds-pen-stroke/);
  assert.match(quickActions, /bg-ds-carbon/);
});

test("QuickActions uses ds-accent-subtle for icon backgrounds", () => {
  assert.match(quickActions, /bg-ds-accent-subtle/);
  assert.match(quickActions, /text-ds-accent/);
});

test("QuickActions uses ds-text tokens", () => {
  assert.match(quickActions, /text-ds-text/);
  assert.match(quickActions, /text-ds-text-tertiary/);
});

// ── DashboardClient.tsx — ds-* token contract ────────────────────────────────

test("DashboardClient header uses ds-text tokens", () => {
  assert.match(dashboardClient, /text-ds-text/);
  assert.match(dashboardClient, /text-ds-text-tertiary/);
});

test("DashboardClient primary trip stat uses ds-accent-subtle and ds-accent", () => {
  assert.match(dashboardClient, /bg-ds-accent-subtle/);
  assert.match(dashboardClient, /text-ds-accent/);
});

test("DashboardClient new trip button has min-h-[44px] touch target", () => {
  assert.match(dashboardClient, /min-h-\[44px\]/);
});

test("DashboardClient has no console.log statements", () => {
  assert.doesNotMatch(dashboardClient, /console\.log/);
});

// ── Behavioral safety — no fake data or provider changes ─────────────────────

test("trips page imports only from lib/api (no new providers)", () => {
  assert.match(tripsPage, /from "@\/lib\/api"/);
  assert.doesNotMatch(tripsPage, /fetch.*provider|new.*Provider/i);
});

test("trips page does not import mock or sample data", () => {
  assert.doesNotMatch(tripsPage, /mock|fake|sample|dummy|placeholder/i);
});

test("trips page budget formatting is defensive (Number() wrap)", () => {
  assert.match(tripsPage, /Number\(trip\.budgetCash\)/);
});

test("trips page handles missing dates with fallback copy", () => {
  assert.match(tripsPage, /Dates TBD/);
});
