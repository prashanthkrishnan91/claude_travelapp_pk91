/**
 * My Trips — Paper Folio visual refresh (PR 2 + shelf composition patch)
 * Source-scan contract tests for trips/page.tsx and globals.css.
 *
 * What this file proves:
 *  - My Trips route adopts the Paper Folio shelf composition (floating stage, masthead, body)
 *  - Editorial serif primitives adopted on page, hero, and cards
 *  - Stage fills the desktop canvas (wide shelf, not a narrow 52rem column)
 *  - ContinuePlanningHero is a two-zone featured volume (content + actions rail)
 *  - JourneyCard leads with the destination; noisy serial-code labels removed
 *  - Cards sit in a responsive grid (sm:grid-cols-2 lg:grid-cols-3)
 *  - PlanningToolsStrip is the integrated shelf rail (trips-tools-shelf)
 *  - JourneyCard keeps edit/delete controls wired but visually demoted
 *  - ContinuePlanningHero still uses existing selection/action logic
 *  - Active/past grouping logic is not changed
 *  - Empty state remains available
 *  - No backend/provider/search/map imports introduced
 *  - No Journey Desk or TripBuilder files touched
 *  - HANDOFF no longer says #490 is open/in progress
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const tripsPage = readFileSync(
  new URL("../src/app/trips/page.tsx", import.meta.url),
  "utf8",
);

const globalsCss = readFileSync(
  new URL("../src/app/globals.css", import.meta.url),
  "utf8",
);

const handoff = readFileSync(
  new URL("../../docs/ai/HANDOFF.md", import.meta.url),
  "utf8",
);

// ── Shelf composition — floating paper stage ──────────────────────────────────

test("trips page uses trips-shelf-stage (floating shelf composition stage)", () => {
  assert.ok(
    tripsPage.includes("trips-shelf-stage"),
    "trips/page.tsx must use trips-shelf-stage to create the floating curated paper shelf",
  );
});

test("trips page uses trips-shelf-masthead (linen-tinted header zone)", () => {
  assert.ok(
    tripsPage.includes("trips-shelf-masthead"),
    "trips/page.tsx must use trips-shelf-masthead for the header zone inside the stage",
  );
});

test("trips page uses trips-shelf-body (content zone inside the stage)", () => {
  assert.ok(
    tripsPage.includes("trips-shelf-body"),
    "trips/page.tsx must use trips-shelf-body for the main content zone",
  );
});

test("trips-shelf-stage is present in both loading and loaded states", () => {
  const stageCount = (tripsPage.match(/trips-shelf-stage/g) || []).length;
  assert.ok(
    stageCount >= 2,
    "trips-shelf-stage must appear in both the loading skeleton and the main render",
  );
});

test("globals.css trips-shelf-stage fills the desktop canvas (not a narrow 52rem column)", () => {
  assert.ok(
    globalsCss.includes(".trips-shelf-stage"),
    "globals.css must define .trips-shelf-stage",
  );
  const block = globalsCss.slice(
    globalsCss.indexOf(".trips-shelf-stage"),
    globalsCss.indexOf(".trips-shelf-stage") + 400,
  );
  assert.ok(
    block.includes("max-width"),
    "trips-shelf-stage must declare a max-width",
  );
  // Composition correction: the stage must use the full AppShell width
  // (capped by the parent max-w-7xl), not the old narrow 52rem column that
  // left a large blank gap on desktop.
  assert.ok(
    !/max-width:\s*52rem/.test(block),
    "trips-shelf-stage must NOT be capped at the old narrow 52rem width",
  );
  assert.ok(
    /max-width:\s*100%/.test(block),
    "trips-shelf-stage must fill the available width (max-width: 100%)",
  );
});

test("globals.css defines trips-shelf-masthead with bottom border (masthead anchor)", () => {
  assert.ok(
    globalsCss.includes(".trips-shelf-masthead"),
    "globals.css must define .trips-shelf-masthead",
  );
  const block = globalsCss.slice(
    globalsCss.indexOf(".trips-shelf-masthead"),
    globalsCss.indexOf(".trips-shelf-masthead") + 200,
  );
  assert.ok(
    block.includes("border-bottom"),
    "trips-shelf-masthead must have a bottom border (hairline separator)",
  );
});

test("globals.css defines trips-shelf-body", () => {
  assert.ok(
    globalsCss.includes(".trips-shelf-body"),
    "globals.css must define .trips-shelf-body",
  );
});

// ── Featured volume — ContinuePlanningHero composition ───────────────────────

test("ContinuePlanningHero uses trips-featured-volume (featured volume gradient)", () => {
  const heroSection = tripsPage.slice(
    tripsPage.indexOf("function ContinuePlanningHero"),
    tripsPage.indexOf("function JourneyCard"),
  );
  assert.ok(
    heroSection.includes("trips-featured-volume"),
    "ContinuePlanningHero must use trips-featured-volume for the warm gradient cover zone",
  );
});

test("ContinuePlanningHero uses trips-hero-destination (larger editorial serif for featured title)", () => {
  const heroSection = tripsPage.slice(
    tripsPage.indexOf("function ContinuePlanningHero"),
    tripsPage.indexOf("function JourneyCard"),
  );
  assert.ok(
    heroSection.includes("trips-hero-destination"),
    "ContinuePlanningHero must use trips-hero-destination to make the destination a stronger editorial focal point",
  );
});

test("globals.css defines trips-featured-volume (hero gradient)", () => {
  assert.ok(
    globalsCss.includes(".trips-featured-volume"),
    "globals.css must define .trips-featured-volume",
  );
  const block = globalsCss.slice(
    globalsCss.indexOf(".trips-featured-volume"),
    globalsCss.indexOf(".trips-featured-volume") + 200,
  );
  assert.ok(
    block.includes("background"),
    "trips-featured-volume must define a background (gradient or color)",
  );
});

test("globals.css defines trips-hero-destination (larger editorial serif)", () => {
  assert.ok(
    globalsCss.includes(".trips-hero-destination"),
    "globals.css must define .trips-hero-destination",
  );
  const block = globalsCss.slice(
    globalsCss.indexOf(".trips-hero-destination"),
    globalsCss.indexOf(".trips-hero-destination") + 150,
  );
  assert.ok(
    block.includes("font-size"),
    "trips-hero-destination must define font-size larger than trips-volume-destination",
  );
});

// ── JourneyCard volume cover ──────────────────────────────────────────────────

test("JourneyCard uses trips-volume-cover (warm gradient body zone)", () => {
  const cardSection = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.ok(
    cardSection.includes("trips-volume-cover"),
    "JourneyCard body must use trips-volume-cover for the warm paper-to-bone gradient",
  );
});

test("globals.css defines trips-volume-cover (card body gradient)", () => {
  assert.ok(
    globalsCss.includes(".trips-volume-cover"),
    "globals.css must define .trips-volume-cover",
  );
  const block = globalsCss.slice(
    globalsCss.indexOf(".trips-volume-cover"),
    globalsCss.indexOf(".trips-volume-cover") + 200,
  );
  assert.ok(
    block.includes("background"),
    "trips-volume-cover must define a background gradient",
  );
});

test("globals.css defines trips-featured-aside (featured volume actions rail)", () => {
  assert.ok(
    globalsCss.includes(".trips-featured-aside"),
    "globals.css must define .trips-featured-aside",
  );
  const block = globalsCss.slice(
    globalsCss.indexOf(".trips-featured-aside"),
    globalsCss.indexOf(".trips-featured-aside") + 400,
  );
  assert.ok(
    block.includes("border-top") || block.includes("border-left"),
    "trips-featured-aside must use a hairline border to separate it as a distinct zone",
  );
});

// ── Responsive card shelf — desktop canvas use ────────────────────────────────

test("TripSection renders cards in a responsive grid that uses the desktop canvas", () => {
  const sectionScope = tripsPage.slice(
    tripsPage.indexOf("function TripSection"),
    tripsPage.indexOf("function PlanningToolsStrip"),
  );
  // Composition correction: cards must scale to 3 columns on wide screens so
  // they do not look like tiny boxes floating in a large blank stage.
  assert.ok(
    sectionScope.includes("journey-card-grid"),
    "TripSection must wrap cards in a grid (journey-card-grid)",
  );
  assert.ok(
    /sm:grid-cols-2/.test(sectionScope) && /lg:grid-cols-3/.test(sectionScope),
    "TripSection grid must be responsive (sm:grid-cols-2 lg:grid-cols-3)",
  );
});

test("trips page no longer derives or renders serial-code labels (noise removed)", () => {
  assert.ok(
    !tripsPage.includes("deriveSerialCode"),
    "deriveSerialCode helper must be removed — serial codes are no longer rendered",
  );
  assert.ok(
    !tripsPage.includes("Current Journey"),
    "the 'CHI · Current Journey' serial label must be removed",
  );
  assert.ok(
    !tripsPage.includes("folio-serial"),
    "no folio-serial code labels should remain on the trips page",
  );
});

// ── Planning tools shelf rail ─────────────────────────────────────────────────

test("PlanningToolsStrip uses trips-tools-shelf (integrated shelf rail)", () => {
  const stripSection = tripsPage.slice(
    tripsPage.indexOf("function PlanningToolsStrip"),
    tripsPage.indexOf("function EditModal"),
  );
  assert.ok(
    stripSection.includes("trips-tools-shelf"),
    "PlanningToolsStrip must use trips-tools-shelf to integrate into the shelf bottom rail",
  );
});

test("globals.css defines trips-tools-shelf (integrated shelf bottom rail)", () => {
  assert.ok(
    globalsCss.includes(".trips-tools-shelf"),
    "globals.css must define .trips-tools-shelf",
  );
  const block = globalsCss.slice(
    globalsCss.indexOf(".trips-tools-shelf"),
    globalsCss.indexOf(".trips-tools-shelf") + 200,
  );
  assert.ok(
    block.includes("border-top"),
    "trips-tools-shelf must have a border-top to anchor it as the shelf bottom rail",
  );
});

// ── Editorial serif primitives ────────────────────────────────────────────────

test("trips page uses trips-shelf-heading class (editorial serif masthead)", () => {
  assert.ok(
    tripsPage.includes("trips-shelf-heading"),
    "trips/page.tsx must use trips-shelf-heading for the editorial serif page heading",
  );
});

test("trips page uses trips-volume-destination class (editorial serif destination title)", () => {
  assert.ok(
    tripsPage.includes("trips-volume-destination"),
    "trips/page.tsx must use trips-volume-destination for the trip destination as volume title",
  );
});

test("globals.css defines trips-shelf-heading with editorial serif font", () => {
  assert.ok(
    globalsCss.includes(".trips-shelf-heading"),
    "globals.css must define .trips-shelf-heading",
  );
  const block = globalsCss.slice(
    globalsCss.indexOf(".trips-shelf-heading"),
    globalsCss.indexOf(".trips-shelf-heading") + 300,
  );
  assert.ok(
    block.includes("var(--ds-font-editorial)"),
    "trips-shelf-heading must use the editorial serif font token",
  );
  assert.ok(
    block.includes("font-style: italic") || block.includes("italic"),
    "trips-shelf-heading must be italic",
  );
});

test("globals.css defines trips-volume-destination with editorial serif font", () => {
  assert.ok(
    globalsCss.includes(".trips-volume-destination"),
    "globals.css must define .trips-volume-destination",
  );
  const block = globalsCss.slice(
    globalsCss.indexOf(".trips-volume-destination"),
    globalsCss.indexOf(".trips-volume-destination") + 300,
  );
  assert.ok(
    block.includes("var(--ds-font-editorial)"),
    "trips-volume-destination must use the editorial serif font token",
  );
  assert.ok(
    block.includes("font-style: italic") || block.includes("italic"),
    "trips-volume-destination must be italic",
  );
});

test("trips page uses folio-issue-eyebrow for section labels (Folio masthead treatment)", () => {
  assert.ok(
    tripsPage.includes("folio-issue-eyebrow"),
    "trips/page.tsx must use folio-issue-eyebrow for at least one section label",
  );
});

// ── Folio primitives adoption ─────────────────────────────────────────────────

test("JourneyCard uses folio-journey-entry class (binding-stripe enhancement)", () => {
  const cardSection = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.ok(
    cardSection.includes("folio-journey-entry"),
    "JourneyCard must use folio-journey-entry for the left binding stripe / enhanced shadow",
  );
});

test("JourneyCard leads with the destination as the visual hero, not a serial code", () => {
  const cardSection = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  // Composition correction: noisy CHI/NEW serial labels are removed; the
  // destination (trips-volume-destination) is the card's primary element.
  assert.ok(
    cardSection.includes("trips-volume-destination"),
    "JourneyCard must present the destination as the visual hero",
  );
  assert.ok(
    !cardSection.includes("folio-serial"),
    "JourneyCard must NOT use folio-serial code labels (removed as noise)",
  );
  // Status is still shown, but as a subtle badge rather than a serial prefix.
  assert.ok(
    cardSection.includes("TripStatusBadge"),
    "JourneyCard must show status via TripStatusBadge",
  );
});

test("JourneyCard uses folio-caption for italic date caption", () => {
  const cardSection = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.ok(
    cardSection.includes("folio-caption"),
    "JourneyCard must render a folio-caption element for the italic editorial date line",
  );
});

test("JourneyCard destination uses trips-volume-destination editorial serif", () => {
  const cardSection = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.ok(
    cardSection.includes("trips-volume-destination"),
    "JourneyCard destination must use trips-volume-destination for the editorial serif hero title",
  );
});

// ── JourneyCard — edit/delete behavior contract preserved ─────────────────────

test("JourneyCard edit button still wired (onEdit(trip) call preserved)", () => {
  const cardSection = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.ok(
    cardSection.includes("onEdit(trip)"),
    "JourneyCard must still call onEdit(trip) on edit button click",
  );
});

test("JourneyCard delete button still wired (onDelete(trip.id) call preserved)", () => {
  const cardSection = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.ok(
    cardSection.includes("onDelete(trip.id)"),
    "JourneyCard must still call onDelete(trip.id) on delete button click",
  );
});

test("JourneyCard edit button has aria-label (accessibility preserved)", () => {
  const cardSection = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.match(cardSection, /aria-label=\{`Edit \$\{trip\.title\}`\}/);
});

test("JourneyCard delete button has aria-label (accessibility preserved)", () => {
  const cardSection = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.match(cardSection, /aria-label=\{`Delete \$\{trip\.title\}`\}/);
});

test("JourneyCard edit/delete buttons have 44px touch targets (accessibility preserved)", () => {
  const cardSection = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.match(cardSection, /min-h-\[44px\]/);
  assert.match(cardSection, /min-w-\[44px\]/);
});

test("JourneyCard edit/delete controls are in the card footer (visually demoted)", () => {
  const cardSection = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.ok(
    cardSection.includes("journey-card-edit-controls"),
    "JourneyCard edit/delete must be inside the footer (journey-card-edit-controls container)",
  );
});

test("JourneyCard open link is a real Link (behavior unchanged)", () => {
  const cardSection = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.match(cardSection, /href=\{`\/trips\/\$\{trip\.id\}`\}/);
  assert.doesNotMatch(cardSection, /onClick=\{\(\) => router\.push/);
});

// ── ContinuePlanningHero — Paper Folio treatment ──────────────────────────────

test("ContinuePlanningHero uses folio-issue-eyebrow for section label", () => {
  const heroSection = tripsPage.slice(
    tripsPage.indexOf("function ContinuePlanningHero"),
    tripsPage.indexOf("function JourneyCard"),
  );
  assert.ok(
    heroSection.includes("folio-issue-eyebrow"),
    "ContinuePlanningHero section label must use folio-issue-eyebrow",
  );
});

test("ContinuePlanningHero uses trips-volume-destination editorial serif", () => {
  const heroSection = tripsPage.slice(
    tripsPage.indexOf("function ContinuePlanningHero"),
    tripsPage.indexOf("function JourneyCard"),
  );
  assert.ok(
    heroSection.includes("trips-volume-destination"),
    "ContinuePlanningHero must use trips-volume-destination for the editorial serif destination",
  );
});

test("ContinuePlanningHero uses a two-zone composition (editorial content + actions rail)", () => {
  const heroSection = tripsPage.slice(
    tripsPage.indexOf("function ContinuePlanningHero"),
    tripsPage.indexOf("function JourneyCard"),
  );
  // Composition correction: the featured volume is no longer one flat beige
  // column. It splits into a left content zone and a right actions/controls
  // rail (trips-featured-aside) that stacks on mobile and sits beside on desktop.
  assert.ok(
    heroSection.includes("trips-featured-aside"),
    "ContinuePlanningHero must use trips-featured-aside for the right actions rail",
  );
  assert.ok(
    heroSection.includes("lg:flex-row"),
    "ContinuePlanningHero must use a responsive lg:flex-row two-zone layout",
  );
  assert.ok(
    heroSection.includes("continue-planning-main") &&
      heroSection.includes("continue-planning-aside"),
    "ContinuePlanningHero must mark both the content zone and the actions rail",
  );
  // The noisy serial code marker is removed.
  assert.ok(
    !heroSection.includes("folio-serial"),
    "ContinuePlanningHero must NOT use folio-serial code labels (removed as noise)",
  );
});

test("ContinuePlanningHero uses folio-journey-entry (folio binding class)", () => {
  const heroSection = tripsPage.slice(
    tripsPage.indexOf("function ContinuePlanningHero"),
    tripsPage.indexOf("function JourneyCard"),
  );
  assert.ok(
    heroSection.includes("folio-journey-entry"),
    "ContinuePlanningHero must use folio-journey-entry",
  );
});

test("ContinuePlanningHero uses folio-caption for metadata line", () => {
  const heroSection = tripsPage.slice(
    tripsPage.indexOf("function ContinuePlanningHero"),
    tripsPage.indexOf("function JourneyCard"),
  );
  assert.ok(
    heroSection.includes("folio-caption"),
    "ContinuePlanningHero must use folio-caption for the italic metadata line",
  );
});

test("ContinuePlanningHero Open Trip link preserved (behavior unchanged)", () => {
  const heroSection = tripsPage.slice(
    tripsPage.indexOf("function ContinuePlanningHero"),
    tripsPage.indexOf("function JourneyCard"),
  );
  assert.match(heroSection, /href=\{`\/trips\/\$\{trip\.id\}`\}/);
});

test("ContinuePlanningHero AI Concierge link preserved (behavior unchanged)", () => {
  const heroSection = tripsPage.slice(
    tripsPage.indexOf("function ContinuePlanningHero"),
    tripsPage.indexOf("function JourneyCard"),
  );
  assert.match(heroSection, /href="\/concierge"/);
  assert.match(heroSection, /AI Concierge/);
});

test("ContinuePlanningHero edit/delete buttons preserved with aria-labels", () => {
  const heroSection = tripsPage.slice(
    tripsPage.indexOf("function ContinuePlanningHero"),
    tripsPage.indexOf("function JourneyCard"),
  );
  assert.match(heroSection, /aria-label=\{`Edit \$\{trip\.title\}`\}/);
  assert.match(heroSection, /aria-label=\{`Delete \$\{trip\.title\}`\}/);
  assert.match(heroSection, /onEdit\(trip\)/);
  assert.match(heroSection, /onDelete\(trip\.id\)/);
});

test("ContinuePlanningHero is wired with onEdit and onDelete at call site", () => {
  assert.match(tripsPage, /ContinuePlanningHero[\s\S]{0,200}onEdit=\{openEdit\}/);
  assert.match(tripsPage, /ContinuePlanningHero[\s\S]{0,200}onDelete=\{/);
});

// ── Grouping / selection logic — not changed ──────────────────────────────────

test("pickContinuePlanning and STATUS_PRIORITY are still present (selection logic unchanged)", () => {
  assert.ok(tripsPage.includes("pickContinuePlanning"));
  assert.ok(tripsPage.includes("STATUS_PRIORITY"));
  assert.match(tripsPage, /researching.*0|0.*researching/);
});

test("getTripStatusGroup still used for active/past grouping", () => {
  assert.ok(tripsPage.includes("getTripStatusGroup"));
});

test("active trips filter excludes continuePlanningId (unchanged)", () => {
  assert.match(tripsPage, /activeTrips.*getTripStatusGroup.*Active/s);
  assert.match(tripsPage, /continuePlanningId/);
});

test("past trips filter uses getTripStatusGroup Past (unchanged)", () => {
  assert.match(tripsPage, /pastTrips.*getTripStatusGroup.*Past/s);
});

// ── Page masthead ─────────────────────────────────────────────────────────────

test("page masthead uses folio-issue-eyebrow for the travel shelf eyebrow", () => {
  assert.ok(tripsPage.includes("trips-shelf-eyebrow"));
  assert.ok(tripsPage.includes("Your Travel Shelf"));
});

test("page masthead h1 uses trips-shelf-heading (editorial serif)", () => {
  assert.ok(tripsPage.includes("trips-shelf-heading"));
  assert.ok(tripsPage.includes("My Journeys"));
});

// ── Empty state ───────────────────────────────────────────────────────────────

test("empty state still renders (trips-empty-state testid present)", () => {
  assert.ok(tripsPage.includes('data-testid="trips-empty-state"'));
});

test("empty state heading uses trips-shelf-heading (editorial serif)", () => {
  const emptySection = tripsPage.slice(
    tripsPage.indexOf("function EmptyDashboard"),
    tripsPage.indexOf("function ContinuePlanningHero"),
  );
  assert.ok(
    emptySection.includes("trips-shelf-heading"),
    "empty state h2 must use trips-shelf-heading for editorial serif",
  );
});

test("empty state action cards and links preserved (behavior unchanged)", () => {
  assert.ok(tripsPage.includes("trips-empty-action-plan"));
  assert.ok(tripsPage.includes("trips-empty-action-concierge"));
  assert.match(tripsPage, /href="\/concierge"/);
  assert.match(tripsPage, /href="\/saved"/);
});

// ── Planning tools strip — present with all three links ───────────────────────

test("PlanningToolsStrip still present with all three tool links", () => {
  assert.ok(tripsPage.includes("planning-tools-strip"));
  assert.ok(tripsPage.includes("Planning tools"));
  assert.match(tripsPage, /href="\/explore"/);
  assert.match(tripsPage, /href="\/saved"/);
  assert.match(tripsPage, /href="\/concierge"/);
});

// ── No behavior changes — scope gates ─────────────────────────────────────────

test("no backend/provider/search/map imports introduced", () => {
  assert.doesNotMatch(tripsPage, /from ".*provider/i);
  assert.doesNotMatch(tripsPage, /from ".*search/i);
  assert.doesNotMatch(tripsPage, /from ".*map/i);
  assert.doesNotMatch(tripsPage, /from ".*backend/i);
  // Only expected API import
  assert.ok(tripsPage.includes('from "@/lib/api"'));
});

test("no mock or sample data in trips page", () => {
  assert.doesNotMatch(tripsPage, /mock|fake|sample|dummy|placeholder/i);
});

test("no Journey Desk or TripBuilder imports in trips page", () => {
  assert.doesNotMatch(tripsPage, /TripBuilder|TripBrief|Dayboard|ExpandedDay|IdeasTray|MapFoldOut/);
  assert.doesNotMatch(tripsPage, /journey-desk|journeyDesk/i);
});

test("data fetching unchanged — only fetchTrips, updateTrip, deleteTrip used", () => {
  assert.ok(tripsPage.includes("fetchTrips"));
  assert.ok(tripsPage.includes("updateTrip"));
  assert.ok(tripsPage.includes("deleteTrip"));
  assert.doesNotMatch(tripsPage, /fetchItinerary|fetchIdeas|fetchDays|fetchBrief/);
});

test("no SQL, backend routes, or provider calls introduced", () => {
  assert.doesNotMatch(tripsPage, /supabase|postgres|sqlite|createClient/i);
  assert.doesNotMatch(tripsPage, /fetch\(.*\/api\//);
});

// ── HANDOFF truth-state ────────────────────────────────────────────────────────

test("HANDOFF no longer says #490 is open or in progress", () => {
  assert.doesNotMatch(
    handoff,
    /Brief Fixed Scheduled Facts v1\s*[—-]\s*open PR/i,
    "HANDOFF must not use the old 'Brief Fixed Scheduled Facts v1 — open PR' wording",
  );
  assert.doesNotMatch(
    handoff,
    /Brief Fixed Scheduled Facts v1\s*\(\s*open PR/i,
    "HANDOFF must not use the old '(open PR, branch' wording for #490",
  );
  assert.ok(
    handoff.includes("Brief Fixed Scheduled Facts v1 merged (#490)") ||
      handoff.includes("Brief Fixed Scheduled Facts v1 (merged"),
    "HANDOFF must state Brief Fixed Scheduled Facts v1 as merged",
  );
});

test("HANDOFF references My Trips Paper Folio PR 2 as current direction", () => {
  assert.ok(
    handoff.includes("My Trips") || handoff.includes("Paper Folio"),
    "HANDOFF must reference the My Trips Paper Folio work as current direction",
  );
});

test("HANDOFF does not reference the feature branch by name (merge-safe wording)", () => {
  assert.doesNotMatch(
    handoff,
    /claude\/happy-heisenberg-AFcOV/,
    "HANDOFF must not reference the feature branch name — should be merge-safe",
  );
});

// ── Reduced-motion gate ────────────────────────────────────────────────────────

test("globals.css new trips primitives have a prefers-reduced-motion guard", () => {
  assert.ok(
    globalsCss.includes("trips-shelf-heading") &&
      globalsCss.includes("trips-volume-destination"),
    "Both editorial serif primitives must be defined in globals.css",
  );
  // Check the MY TRIPS section has a reduced-motion block (wide window — section grew)
  const myTripsSection = globalsCss.slice(
    globalsCss.indexOf("MY TRIPS"),
    globalsCss.indexOf("MY TRIPS") + 6000,
  );
  assert.ok(
    myTripsSection.includes("prefers-reduced-motion"),
    "MY TRIPS CSS section must include a prefers-reduced-motion guard",
  );
});
