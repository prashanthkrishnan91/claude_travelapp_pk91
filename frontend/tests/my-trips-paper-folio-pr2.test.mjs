/**
 * My Journeys — "The Reading Room" implementation
 * Source-scan contract tests for trips/page.tsx and globals.css.
 *
 * What this file proves (the approved Reading Room prototype):
 *  - /trips renders a Reading Room / folio library room stage (floating stage)
 *  - The masthead uses editorial hierarchy (library line + serif title + caption)
 *  - The current trip renders as the open "current edition" (two-zone)
 *  - There is exactly ONE cinematic / monogram plate on the filled page
 *  - Trip cards render as bound-volume cards (spine + volume structure)
 *  - Active grouping is "On the table"; past grouping is "Bound" (quieter)
 *  - Status is rendered as small-caps text, NOT a colored pill badge
 *  - Planning tools render as a reference drawer ("Elsewhere in the house")
 *  - Empty state uses the empty-shelf concept
 *  - No fake mapline / poetic caption text is introduced (real data only)
 *  - Behavior preserved: edit/delete, Open Trip, AI Concierge, Plan Trip,
 *    grouping/filtering, data fetch
 *  - No Trip Detail / Journey Desk / TripBuilder files touched
 *  - No backend / provider / search / map imports introduced
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

// ── The room — floating paper shelf stage ─────────────────────────────────────

test("trips page uses trips-shelf-stage (the Reading Room stage)", () => {
  assert.ok(tripsPage.includes("trips-shelf-stage"));
});

test("trips-shelf-stage appears in both loading and loaded states", () => {
  const count = (tripsPage.match(/trips-shelf-stage/g) || []).length;
  assert.ok(count >= 2, "stage must wrap both the skeleton and the main render");
});

test("trips page uses trips-shelf-masthead and trips-shelf-body zones", () => {
  assert.ok(tripsPage.includes("trips-shelf-masthead"));
  assert.ok(tripsPage.includes("trips-shelf-body"));
});

test("globals.css trips-shelf-stage fills the canvas (not a narrow 52rem column)", () => {
  assert.ok(globalsCss.includes(".trips-shelf-stage"));
  const block = globalsCss.slice(
    globalsCss.indexOf(".trips-shelf-stage"),
    globalsCss.indexOf(".trips-shelf-stage") + 400,
  );
  assert.ok(block.includes("max-width"));
  assert.ok(!/max-width:\s*52rem/.test(block), "stage must not be capped at 52rem");
  assert.ok(/max-width:\s*100%/.test(block), "stage must fill available width");
});

test("globals.css defines trips-shelf-masthead with a bottom hairline", () => {
  const block = globalsCss.slice(
    globalsCss.indexOf(".trips-shelf-masthead"),
    globalsCss.indexOf(".trips-shelf-masthead") + 220,
  );
  assert.ok(block.includes("border-bottom"));
});

test("globals.css defines trips-shelf-body", () => {
  assert.ok(globalsCss.includes(".trips-shelf-body"));
});

// ── Masthead — editorial hierarchy ────────────────────────────────────────────

test("masthead uses the library line (folio-issue-eyebrow + 'The Folio Library')", () => {
  assert.ok(tripsPage.includes("folio-issue-eyebrow"));
  assert.ok(tripsPage.includes("The Folio Library"));
});

test("masthead title uses trips-shelf-heading editorial serif ('My Journeys')", () => {
  assert.ok(tripsPage.includes("trips-shelf-heading"));
  assert.ok(tripsPage.includes("My Journeys"));
});

test("masthead renders a room-sub caption from real trip counts (folio-caption)", () => {
  assert.ok(tripsPage.includes("roomSub"));
  // The caption is derived from real counts, not a poetic invented line.
  assert.match(tripsPage, /volumes? on the shelf/);
  assert.match(tripsPage, /trips\.length/);
});

test("globals.css trips-shelf-heading is editorial serif and italic", () => {
  const block = globalsCss.slice(
    globalsCss.indexOf(".trips-shelf-heading"),
    globalsCss.indexOf(".trips-shelf-heading") + 300,
  );
  assert.ok(block.includes("var(--ds-font-editorial)"));
  assert.ok(block.includes("italic"));
});

// ── Current edition — the open volume on the desk ─────────────────────────────

test("the current trip renders under 'The current edition' chapter", () => {
  assert.ok(tripsPage.includes("The current edition"));
});

test("ContinuePlanningHero is a two-zone current edition (spread + plate)", () => {
  const hero = tripsPage.slice(
    tripsPage.indexOf("function ContinuePlanningHero"),
    tripsPage.indexOf("function JourneyCard"),
  );
  assert.ok(hero.includes("trips-edition"), "hero must use the trips-edition page");
  assert.ok(hero.includes("trips-edition-spread"), "hero must have the editorial spread zone");
  assert.ok(hero.includes("lg:flex-row"), "hero must be a responsive two-zone layout");
  assert.ok(hero.includes("EditionPlate"), "hero must render the cinematic plate zone");
  assert.ok(hero.includes("folio-paper-panel"), "hero stays a paper panel (plate is the only dark zone)");
  assert.ok(!hero.includes("folio-serial"), "no serial-code labels on the hero");
});

test("ContinuePlanningHero uses trips-hero-destination editorial serif", () => {
  const hero = tripsPage.slice(
    tripsPage.indexOf("function ContinuePlanningHero"),
    tripsPage.indexOf("function JourneyCard"),
  );
  assert.ok(hero.includes("trips-volume-destination"));
  assert.ok(hero.includes("trips-hero-destination"));
});

test("ContinuePlanningHero uses folio-caption for the real metadata line", () => {
  const hero = tripsPage.slice(
    tripsPage.indexOf("function ContinuePlanningHero"),
    tripsPage.indexOf("function JourneyCard"),
  );
  assert.ok(hero.includes("folio-caption"));
  assert.ok(hero.includes("formatDateRange"));
});

// ── Exactly one cinematic / monogram plate on the filled page ─────────────────

test("there is exactly ONE cinematic monogram plate on the filled page", () => {
  const plateCount = (tripsPage.match(/data-testid="trips-edition-plate"/g) || []).length;
  assert.equal(plateCount, 1, "the current edition is the single cinematic plate");
});

test("the plate monogram is derived from the real trip destination (not a photo)", () => {
  const plate = tripsPage.slice(
    tripsPage.indexOf("function EditionPlate"),
    tripsPage.indexOf("function ContinuePlanningHero"),
  );
  assert.ok(plate.includes("trip.destination"));
  assert.ok(plate.includes("charAt(0)"));
  // No <img>, no background image URL, no stock photo.
  assert.ok(!plate.includes("<img"));
  assert.ok(!/url\(/.test(plate));
});

test("globals.css trips-edition-plate is a warm-dark cinema surface (ds tokens, pearl text)", () => {
  assert.ok(globalsCss.includes(".trips-edition-plate"));
  const block = globalsCss.slice(
    globalsCss.indexOf(".trips-edition-plate {"),
    globalsCss.indexOf(".trips-edition-plate {") + 600,
  );
  assert.ok(block.includes("var(--ds-cinema-deep)") || block.includes("var(--ds-carbon-mist)"));
  assert.ok(block.includes("var(--ds-pearl-cream)"));
});

// ── Trip volumes — bound-volume cards ─────────────────────────────────────────

test("JourneyCard is a bound volume (trips-volume + folio-journey-entry spine)", () => {
  const card = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.ok(card.includes("trips-volume"), "card uses the trips-volume class");
  assert.ok(card.includes("folio-journey-entry"), "card carries the brass binding spine");
  assert.ok(card.includes("trips-volume-cover"), "card body uses the warm cover zone");
  assert.ok(card.includes("border-ds-hairline"), "card has a quiet hairline footer rail");
});

test("JourneyCard leads with the destination as the editorial serif hero", () => {
  const card = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.ok(card.includes("trips-volume-destination"));
  assert.ok(!card.includes("folio-serial"), "no serial-code noise on volumes");
});

test("JourneyCard caption is a real date range (folio-caption), not poetic invention", () => {
  const card = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.ok(card.includes("folio-caption"));
  assert.ok(card.includes("formatDateRange"));
});

test("globals.css defines trips-volume-cover", () => {
  assert.ok(globalsCss.includes(".trips-volume-cover"));
});

// ── Chaptered grouping — On the table / Bound ─────────────────────────────────

test("active grouping uses the chapter 'On the table'", () => {
  assert.ok(tripsPage.includes('title="On the table"'));
});

test("past grouping uses the chapter 'Bound' and is rendered quieter", () => {
  assert.ok(tripsPage.includes('title="Bound"'));
  // The past section is flagged so volumes render quieter.
  assert.match(tripsPage, /title="Bound"[\s\S]{0,260}past/);
  assert.ok(globalsCss.includes(".trips-volume-past"));
});

test("globals.css defines the trips-chapter editorial section rule (serif title + hairline)", () => {
  assert.ok(globalsCss.includes(".trips-chapter"));
  assert.ok(globalsCss.includes(".trips-chapter-title"));
  const block = globalsCss.slice(
    globalsCss.indexOf(".trips-chapter-title"),
    globalsCss.indexOf(".trips-chapter-title") + 260,
  );
  assert.ok(block.includes("var(--ds-font-editorial)"));
});

// ── Status as text, not a colored pill ────────────────────────────────────────

test("status is rendered as small-caps text, not a colored pill badge", () => {
  // The colored pill component is gone; status is derived text.
  assert.ok(!tripsPage.includes("TripStatusBadge"), "TripStatusBadge pill must not be used");
  assert.ok(tripsPage.includes("StatusText"), "status renders via the StatusText text component");
  assert.ok(tripsPage.includes("trips-volume-status"), "status uses the small-caps text class");
  assert.ok(tripsPage.includes("getDisplayTripStatus"), "status value still derived via getDisplayTripStatus");
});

test("globals.css trips-volume-status is small-caps text (no pill background/border)", () => {
  const block = globalsCss.slice(
    globalsCss.indexOf(".trips-volume-status {"),
    globalsCss.indexOf(".trips-volume-status {") + 260,
  );
  assert.ok(block.includes("text-transform: uppercase") || block.includes("uppercase"));
  assert.ok(block.includes("letter-spacing"));
  assert.ok(!block.includes("border-radius"), "status text must not look like a pill");
});

// ── Reference drawer — Elsewhere in the house ─────────────────────────────────

test("planning tools render as the 'Elsewhere in the house' reference drawer", () => {
  assert.ok(tripsPage.includes("planning-tools-strip"));
  assert.ok(tripsPage.includes("Elsewhere in the house"));
  assert.ok(tripsPage.includes("trips-tools-shelf"));
  assert.ok(tripsPage.includes("trips-tool-panel"));
});

test("reference drawer preserves all three routes", () => {
  const strip = tripsPage.slice(
    tripsPage.indexOf("function PlanningToolsStrip"),
    tripsPage.indexOf("function EditModal"),
  );
  assert.match(strip, /href="\/concierge"/);
  assert.match(strip, /href="\/saved"/);
  assert.match(strip, /href="\/explore"/);
});

// ── Empty state — empty shelf concept ─────────────────────────────────────────

test("empty state uses the empty-shelf concept with the bound-spine motif", () => {
  assert.ok(tripsPage.includes('data-testid="trips-empty-state"'));
  assert.ok(tripsPage.includes("An empty shelf, waiting for its first volume."));
  assert.ok(tripsPage.includes("trips-empty-plate"));
});

test("empty state has one primary action and a quiet saved-ideas link", () => {
  const empty = tripsPage.slice(
    tripsPage.indexOf("function EmptyDashboard"),
    tripsPage.indexOf("function EditionPlate"),
  );
  assert.match(empty, /href="\/trips\/new"/);
  assert.match(empty, /href="\/saved"/);
});

test("empty state heading uses trips-shelf-heading editorial serif", () => {
  const empty = tripsPage.slice(
    tripsPage.indexOf("function EmptyDashboard"),
    tripsPage.indexOf("function EditionPlate"),
  );
  assert.ok(empty.includes("trips-shelf-heading"));
});

// ── No fake data — mapline / captions are real-data only ──────────────────────

test("no invented multi-city mapline or poetic caption text is introduced", () => {
  // The prototype's illustrative arrows / poetic lines must NOT ship.
  assert.ok(!tripsPage.includes("→"), "no fabricated city-sequence arrows");
  assert.ok(!/honey|maples turn|long lunch|rooftop/i.test(tripsPage), "no poetic sample captions");
});

test("no mock or sample data in trips page", () => {
  assert.doesNotMatch(tripsPage, /mock|fake|sample|dummy|placeholder/i);
});

// ── Behavior preserved ────────────────────────────────────────────────────────

test("ContinuePlanningHero preserves Open Trip, AI Concierge, edit/delete", () => {
  const hero = tripsPage.slice(
    tripsPage.indexOf("function ContinuePlanningHero"),
    tripsPage.indexOf("function JourneyCard"),
  );
  assert.match(hero, /href=\{`\/trips\/\$\{trip\.id\}`\}/);
  assert.match(hero, /href="\/concierge"/);
  assert.match(hero, /AI Concierge/);
  assert.match(hero, /onEdit\(trip\)/);
  assert.match(hero, /onDelete\(trip\.id\)/);
  assert.match(hero, /aria-label=\{`Edit \$\{trip\.title\}`\}/);
  assert.match(hero, /aria-label=\{`Delete \$\{trip\.title\}`\}/);
});

test("ContinuePlanningHero wired with onEdit/onDelete at call site", () => {
  assert.match(tripsPage, /ContinuePlanningHero[\s\S]{0,260}onEdit=\{openEdit\}/);
  assert.match(tripsPage, /ContinuePlanningHero[\s\S]{0,260}onDelete=\{/);
});

test("JourneyCard preserves Open link, edit/delete handlers, 44px targets, aria-labels", () => {
  const card = tripsPage.slice(
    tripsPage.indexOf("function JourneyCard"),
    tripsPage.indexOf("function TripSection"),
  );
  assert.match(card, /href=\{`\/trips\/\$\{trip\.id\}`\}/);
  assert.doesNotMatch(card, /onClick=\{\(\) => router\.push/);
  assert.match(card, /onEdit\(trip\)/);
  assert.match(card, /onDelete\(trip\.id\)/);
  assert.match(card, /aria-label=\{`Edit \$\{trip\.title\}`\}/);
  assert.match(card, /aria-label=\{`Delete \$\{trip\.title\}`\}/);
  assert.match(card, /min-h-\[44px\]/);
  assert.match(card, /min-w-\[44px\]/);
  assert.ok(card.includes("journey-card-edit-controls"));
});

test("selection + grouping logic unchanged", () => {
  assert.ok(tripsPage.includes("pickContinuePlanning"));
  assert.ok(tripsPage.includes("STATUS_PRIORITY"));
  assert.match(tripsPage, /researching.*0|0.*researching/);
  assert.ok(tripsPage.includes("getTripStatusGroup"));
  assert.match(tripsPage, /activeTrips.*getTripStatusGroup.*Active/s);
  assert.match(tripsPage, /continuePlanningId/);
  assert.match(tripsPage, /pastTrips.*getTripStatusGroup.*Past/s);
});

test("responsive volume grid uses the desktop canvas (sm:grid-cols-2 lg:grid-cols-3)", () => {
  const section = tripsPage.slice(
    tripsPage.indexOf("function TripSection"),
    tripsPage.indexOf("function PlanningToolsStrip"),
  );
  assert.ok(section.includes("journey-card-grid"));
  assert.ok(/sm:grid-cols-2/.test(section) && /lg:grid-cols-3/.test(section));
});

// ── Scope gates ───────────────────────────────────────────────────────────────

test("data fetching unchanged — only fetchTrips, updateTrip, deleteTrip used", () => {
  assert.ok(tripsPage.includes("fetchTrips"));
  assert.ok(tripsPage.includes("updateTrip"));
  assert.ok(tripsPage.includes("deleteTrip"));
  assert.ok(tripsPage.includes('from "@/lib/api"'));
  assert.doesNotMatch(tripsPage, /fetchItinerary|fetchIdeas|fetchDays|fetchBrief/);
});

test("no backend/provider/search/map imports introduced", () => {
  assert.doesNotMatch(tripsPage, /from ".*provider/i);
  assert.doesNotMatch(tripsPage, /from ".*search/i);
  assert.doesNotMatch(tripsPage, /from ".*map/i);
  assert.doesNotMatch(tripsPage, /from ".*backend/i);
});

test("no SQL, backend routes, or provider calls introduced", () => {
  assert.doesNotMatch(tripsPage, /supabase|postgres|sqlite|createClient/i);
  assert.doesNotMatch(tripsPage, /fetch\(.*\/api\//);
});

test("no Journey Desk / TripBuilder / Trip Detail imports in trips page", () => {
  assert.doesNotMatch(
    tripsPage,
    /TripBuilder|TripBrief|Dayboard|ExpandedDay|IdeasTray|MapFoldOut|AddToDayDrawer/,
  );
  assert.doesNotMatch(tripsPage, /journey-desk|journeyDesk/i);
});

// ── Reduced-motion gate ────────────────────────────────────────────────────────

test("MY TRIPS CSS section includes a prefers-reduced-motion guard", () => {
  const section = globalsCss.slice(
    globalsCss.indexOf("MY TRIPS"),
    globalsCss.indexOf("MY TRIPS") + 12000,
  );
  assert.ok(section.includes("prefers-reduced-motion"));
});

// ── HANDOFF truth-state ────────────────────────────────────────────────────────

test("HANDOFF references the My Journeys Reading Room as current direction", () => {
  assert.ok(handoff.includes("Reading Room"));
  assert.ok(handoff.includes("My Journeys") || handoff.includes("My Trips"));
});

test("HANDOFF does not reference a feature branch by name (merge-safe)", () => {
  assert.doesNotMatch(handoff, /claude\/[a-z]+-[a-z]+-[A-Za-z0-9]+/);
});
