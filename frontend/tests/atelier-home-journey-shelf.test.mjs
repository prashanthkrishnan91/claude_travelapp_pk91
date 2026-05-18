/**
 * Stage 3.5 Phase 8A — Private Atelier Home + Journey Shelf
 * Contract tests for the redesigned DashboardClient (atelier home)
 * and the upgraded trips/page.tsx (travel-volume journey shelf).
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const dashboardClient = readFileSync(
  new URL("../src/components/dashboard/DashboardClient.tsx", import.meta.url),
  "utf8",
);
const tripsPage = readFileSync(
  new URL("../src/app/trips/page.tsx", import.meta.url),
  "utf8",
);
const homePage = readFileSync(
  new URL("../src/app/page.tsx", import.meta.url),
  "utf8",
);

// ── DashboardClient — Atelier home structure ──────────────────────────────────

test("DashboardClient has atelier-greeting data-testid", () => {
  assert.match(dashboardClient, /data-testid="atelier-greeting"/);
});

test("DashboardClient has concierge-entry data-testid", () => {
  assert.match(dashboardClient, /data-testid="concierge-entry"/);
});

test("DashboardClient has atelier-home data-testid on root", () => {
  assert.match(dashboardClient, /data-testid="atelier-home"/);
});

test("DashboardClient greeting uses time-based function (not hardcoded text)", () => {
  assert.match(dashboardClient, /getTimeGreeting/);
});

test("DashboardClient greeting uses real tripCount from summary (not hardcoded number)", () => {
  assert.match(dashboardClient, /summary\.tripCount/);
});

test("DashboardClient has 'Private Travel Concierge' overline label", () => {
  assert.match(dashboardClient, /Private Travel Concierge/);
});

test("DashboardClient has editorial Overline function with tracking-[0.1em] and uppercase", () => {
  assert.match(dashboardClient, /tracking-\[0\.1em\]/);
  assert.match(dashboardClient, /uppercase/);
});

// ── DashboardClient — Concierge as primary instrument ────────────────────────

test("DashboardClient ConciergeEntry has a semantic Link to /concierge", () => {
  const section = dashboardClient.slice(
    dashboardClient.indexOf("function ConciergeEntry"),
    dashboardClient.indexOf("function ContinuePlanningStrip"),
  );
  assert.match(section, /href="\/concierge"/);
  assert.doesNotMatch(section, /onClick=\{\(\) => router\.push/);
});

test("DashboardClient ConciergeEntry open link has 44px touch target", () => {
  const section = dashboardClient.slice(
    dashboardClient.indexOf("function ConciergeEntry"),
    dashboardClient.indexOf("function ContinuePlanningStrip"),
  );
  assert.match(section, /min-h-\[44px\]/);
});

test("DashboardClient has elevated Concierge section (boutique-instrument or ds-elevation-2 token)", () => {
  assert.ok(
    dashboardClient.includes("boutique-instrument") || dashboardClient.includes("ds-elevation-2"),
    "DashboardClient must elevate the Concierge section via boutique-instrument or ds-elevation-2"
  );
});

test("DashboardClient ConciergeEntry is a client-side section element with aria-label", () => {
  const section = dashboardClient.slice(
    dashboardClient.indexOf("function ConciergeEntry"),
    dashboardClient.indexOf("function ContinuePlanningStrip"),
  );
  assert.match(section, /aria-label="AI Concierge"/);
});

// ── DashboardClient — No KPI dashboard energy ────────────────────────────────

test("DashboardClient does not import StatCard (no KPI dashboard widgets)", () => {
  assert.doesNotMatch(dashboardClient, /StatCard/);
});

test("DashboardClient does not import DealsFeed (removed from atelier home)", () => {
  assert.doesNotMatch(dashboardClient, /DealsFeed/);
});

test("DashboardClient does not import PointsSummary (removed from atelier home)", () => {
  assert.doesNotMatch(dashboardClient, /PointsSummary/);
});

test("DashboardClient does not import QuickActions (replaced by atelier layout)", () => {
  assert.doesNotMatch(dashboardClient, /QuickActions/);
});

test("DashboardClient does not import RecentTrips (replaced by atelier journey view)", () => {
  assert.doesNotMatch(dashboardClient, /RecentTrips/);
});

// ── DashboardClient — ds-* token contract ────────────────────────────────────

test("DashboardClient uses ds-* surface tokens (no raw violet/emerald/amber)", () => {
  assert.match(dashboardClient, /bg-ds-carbon|bg-ds-onyx|border-ds-pen-stroke/);
  assert.doesNotMatch(dashboardClient, /violet-\d+|emerald-\d+|amber-\d+/);
});

test("DashboardClient uses bg-ds-accent-subtle for icon backgrounds", () => {
  assert.match(dashboardClient, /bg-ds-accent-subtle/);
});

test("DashboardClient uses text-ds-accent for accent elements", () => {
  assert.match(dashboardClient, /text-ds-accent/);
});

test("DashboardClient uses ds-text tokens for text hierarchy", () => {
  assert.match(dashboardClient, /text-ds-text\b/);
  assert.match(dashboardClient, /text-ds-text-secondary/);
  assert.match(dashboardClient, /text-ds-text-tertiary/);
});

test("DashboardClient uses focus-visible outline tokens for keyboard accessibility", () => {
  assert.match(dashboardClient, /focus-visible:outline-ds-accent/);
});

// ── DashboardClient — No fake data / no card-level onClick nav ───────────────

test("DashboardClient does not import mock or sample data", () => {
  assert.doesNotMatch(dashboardClient, /mock|fake|sample|dummy/i);
});

test("DashboardClient has no card-level onClick navigation", () => {
  assert.doesNotMatch(dashboardClient, /onClick=\{\(\) => router\.push/);
});

test("DashboardClient does not import backend or provider modules", () => {
  assert.doesNotMatch(dashboardClient, /from "@\/backend/);
  assert.doesNotMatch(dashboardClient, /from "@\/services/);
});

// ── DashboardClient — Continue planning with real trip data ──────────────────

test("DashboardClient has atelier-continue-planning data-testid", () => {
  assert.match(dashboardClient, /data-testid="atelier-continue-planning"/);
});

test("DashboardClient ContinuePlanningStrip has semantic Link to trip by real id", () => {
  assert.match(dashboardClient, /href=\{`\/trips\/\$\{trip\.id\}`\}/);
});

test("DashboardClient ContinuePlanningStrip open link has 44px touch target", () => {
  const section = dashboardClient.slice(
    dashboardClient.indexOf("function ContinuePlanningStrip"),
    dashboardClient.indexOf("function JourneyShelfTeaser"),
  );
  assert.match(section, /min-h-\[44px\]/);
});

test("DashboardClient ContinuePlanningStrip shows real trip title and destination", () => {
  const section = dashboardClient.slice(
    dashboardClient.indexOf("function ContinuePlanningStrip"),
    dashboardClient.indexOf("function JourneyShelfTeaser"),
  );
  assert.match(section, /trip\.title/);
  assert.match(section, /trip\.destination/);
});

// ── DashboardClient — Journey shelf teaser ────────────────────────────────────

test("DashboardClient has journey-shelf-teaser data-testid", () => {
  assert.match(dashboardClient, /data-testid="journey-shelf-teaser"/);
});

test("DashboardClient JourneyShelfTeaser has a Link to /trips", () => {
  const section = dashboardClient.slice(
    dashboardClient.indexOf("function JourneyShelfTeaser"),
    dashboardClient.indexOf("function EmptyAtelierHome"),
  );
  assert.match(section, /href="\/trips"/);
});

test("DashboardClient JourneyShelfTeaser uses real count (tripCount from summary)", () => {
  assert.match(dashboardClient, /summary\.tripCount/);
});

// ── DashboardClient — Discovery tools ────────────────────────────────────────

test("DashboardClient has atelier-planning-strip data-testid", () => {
  assert.match(dashboardClient, /data-testid="atelier-planning-strip"/);
});

test("DashboardClient has Link to /explore in discovery strip", () => {
  assert.match(dashboardClient, /href="\/explore"/);
});

test("DashboardClient has Link to /saved in discovery strip", () => {
  assert.match(dashboardClient, /href="\/saved"/);
});

// ── DashboardClient — Loading state accessibility ────────────────────────────

test("DashboardClient loading state has aria-busy", () => {
  assert.match(dashboardClient, /aria-busy="true"/);
});

test("DashboardClient has no console.log statements", () => {
  assert.doesNotMatch(dashboardClient, /console\.log/);
});

// ── trips/page.tsx — Journey shelf / travel-volume upgrades ──────────────────

test("trips page JourneyCard shows destination as large editorial hero text", () => {
  const cardSection = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.match(cardSection, /trip\.destination/);
  assert.match(cardSection, /text-lg|text-xl/);
});

test("trips page JourneyCard trip title is a semantic Link (not only div with onClick)", () => {
  const cardSection = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.match(cardSection, /href=\{`\/trips\/\$\{trip\.id\}`\}/);
  assert.doesNotMatch(cardSection, /onClick=\{\(\) => router\.push/);
});

test("trips page JourneyCard has Open link in footer with min-h-[44px]", () => {
  const cardSection = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.match(cardSection, /Open/);
  assert.match(cardSection, /min-h-\[44px\]/);
});

test("trips page JourneyCard has no card root onClick navigation", () => {
  const cardSection = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.doesNotMatch(cardSection, /onClick=\{\(\) => router\.push/);
});

test("trips page ContinuePlanningHero uses destination as editorial overline", () => {
  const heroSection = tripsPage.slice(
    tripsPage.indexOf("function ContinuePlanningHero"),
    tripsPage.indexOf("function JourneyCard"),
  );
  assert.match(heroSection, /trip\.destination/);
  assert.ok(
    /tracking-\[0\.1em\]/.test(heroSection) || heroSection.includes("folio-muted-label") || heroSection.includes("Overline"),
    "hero section must use Overline tracking (direct class, folio-muted-label, or Overline component)"
  );
});

test("trips page has editorial 'Your Travel Shelf' overline in page header", () => {
  assert.match(tripsPage, /Your Travel Shelf/);
});

test("trips page h1 still reads My Journeys (semantic heading preserved)", () => {
  assert.match(tripsPage, /My Journeys/);
});

test("trips page JourneyCard displays trip.destination (no icon replacing it as identity)", () => {
  const cardSection = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.match(cardSection, /trip\.destination/);
});

test("trips page JourneyCard footer has date and travelers from real data", () => {
  const cardSection = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.match(cardSection, /formatDateRange/);
  assert.match(cardSection, /trip\.travelers/);
});

// ── trips/page.tsx — preserved affordances (no regression) ───────────────────

test("trips page preserves create trip action (Plan a Trip link to /trips/new)", () => {
  assert.match(tripsPage, /href="\/trips\/new"/);
  assert.match(tripsPage, /Plan a Trip/);
});

test("trips page preserves edit action via EditModal and handleUpdate", () => {
  assert.match(tripsPage, /EditModal/);
  assert.match(tripsPage, /handleUpdate/);
});

test("trips page preserves delete action via DeleteModal and handleDelete", () => {
  assert.match(tripsPage, /DeleteModal/);
  assert.match(tripsPage, /handleDelete/);
});

test("trips page preserves open-trip navigation via real Link (no router.push)", () => {
  assert.match(tripsPage, /href=\{`\/trips\/\$\{trip\.id\}`\}/);
  assert.doesNotMatch(tripsPage, /onClick=\{\(\) => router\.push/);
});

test("trips page preserves ContinuePlanningHero with onEdit and onDelete wired", () => {
  assert.match(tripsPage, /ContinuePlanningHero[\s\S]{0,200}onEdit=\{openEdit\}/);
  assert.match(tripsPage, /ContinuePlanningHero[\s\S]{0,200}onDelete=\{/);
});

test("trips page preserves PlanningToolsStrip with planning tools", () => {
  assert.match(tripsPage, /PlanningToolsStrip/);
});

// ── No fake data ──────────────────────────────────────────────────────────────

test("DashboardClient has no fake data patterns", () => {
  assert.doesNotMatch(dashboardClient, /mock|fake|sample|dummy|placeholder/i);
});

test("trips page has no fake data or mock imports", () => {
  assert.doesNotMatch(tripsPage, /mock|fake|sample|dummy|placeholder/i);
});

// ── Home page metadata ────────────────────────────────────────────────────────

test("home page title is not the generic 'Dashboard' string", () => {
  assert.doesNotMatch(homePage, /title: "Dashboard"/);
});

// ── DashboardClient — is a client component ──────────────────────────────────

test("DashboardClient is a client component", () => {
  assert.match(dashboardClient, /"use client"/);
});

// ── DashboardClient — lib/api imports (no new providers) ─────────────────────

test("DashboardClient imports only from lib/api and lib/tripStatus (no new providers)", () => {
  assert.match(dashboardClient, /from "@\/lib\/api"/);
  assert.doesNotMatch(dashboardClient, /fetch.*[Pp]rovider|new.*Provider/);
});
