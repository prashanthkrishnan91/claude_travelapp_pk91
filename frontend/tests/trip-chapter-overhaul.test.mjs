/**
 * Stage 3.5 Phase 8B — Trip Detail Travel Chapter + Planning Canvas Overhaul
 * Contract tests for the TripChapterCover treatment in trips/[id]/page.tsx
 * and the advisor briefing in TripReadinessCockpit.tsx.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const tripDetailPage = readFileSync(
  new URL("../src/app/trips/[id]/page.tsx", import.meta.url),
  "utf8",
);

const cockpit = readFileSync(
  new URL("../src/components/trips/TripReadinessCockpit.tsx", import.meta.url),
  "utf8",
);

// ── Chapter cover structure ───────────────────────────────────────────────────

test("trip detail page has a chapter cover section with data-testid", () => {
  assert.match(tripDetailPage, /data-testid="trip-chapter-cover"/);
});

test("chapter cover uses a <section> element as root (data-testid on section tag)", () => {
  // The section element itself carries the data-testid attribute
  assert.match(tripDetailPage, /<section[^>]*data-testid="trip-chapter-cover"/);
});

test("chapter cover has aria-labelledby for accessibility", () => {
  assert.match(tripDetailPage, /aria-labelledby="chapter-destination-heading"/);
});

test("chapter cover has h1 with matching id", () => {
  assert.match(tripDetailPage, /id="chapter-destination-heading"/);
  assert.match(tripDetailPage, /<h1/);
});

test("chapter cover renders destination as the primary editorial heading", () => {
  assert.match(tripDetailPage, /trip\?\.destination \?\? trip\?\.title \?\? "Your Trip"/);
});

test("chapter cover includes an Overline 'Travel Chapter' label", () => {
  assert.match(tripDetailPage, /Travel Chapter/);
});

test("chapter cover Overline uses correct typography token pattern", () => {
  assert.match(tripDetailPage, /tracking-\[0\.1em\]/);
  assert.match(tripDetailPage, /uppercase/);
  assert.match(tripDetailPage, /text-\[10px\]/);
});

test("chapter cover renders trip title as subtitle when present", () => {
  assert.match(tripDetailPage, /trip\.title !== trip\.destination/);
});

test("chapter cover renders context vibe in italic editorial style", () => {
  assert.match(tripDetailPage, /italic/);
  assert.match(tripDetailPage, /tripContext/);
  assert.match(tripDetailPage, /tripContext\.vibe/);
});

test("chapter cover shows loading state for context while fetching", () => {
  assert.match(tripDetailPage, /contextLoading/);
  assert.match(tripDetailPage, /Composing destination context/);
});

test("chapter cover shows dates when trip has startDate or endDate", () => {
  assert.match(tripDetailPage, /trip\?\.startDate \|\| trip\?\.endDate/);
  assert.match(tripDetailPage, /trip\.startDate && trip\.endDate/);
});

test("chapter cover renders CalendarDays icon for dates", () => {
  assert.match(tripDetailPage, /CalendarDays/);
});

test("chapter cover shows day count from itineraryDays length", () => {
  assert.match(tripDetailPage, /itineraryDays\.length/);
});

// ── Chapter cover: back navigation ───────────────────────────────────────────

test("chapter cover has a 'My Journeys' back link", () => {
  assert.match(tripDetailPage, /My Journeys/);
  assert.match(tripDetailPage, /href="\/trips"/);
});

test("back link uses ChevronLeft icon", () => {
  assert.match(tripDetailPage, /ChevronLeft/);
});

// ── Chapter cover: action cluster ────────────────────────────────────────────

test("chapter cover actions section has data-testid", () => {
  assert.match(tripDetailPage, /data-testid="chapter-actions"/);
});

test("chapter cover has AI Concierge button with data-testid", () => {
  assert.match(tripDetailPage, /data-testid="chapter-action-concierge"/);
  assert.match(tripDetailPage, /AI Concierge/);
});

test("chapter cover has Optimize button with data-testid", () => {
  assert.match(tripDetailPage, /data-testid="chapter-action-optimize"/);
  assert.match(tripDetailPage, /Optimize/);
});

test("chapter cover has Edit Trip button with data-testid", () => {
  assert.match(tripDetailPage, /data-testid="chapter-action-edit"/);
  assert.match(tripDetailPage, /Edit Trip/);
});

test("chapter cover has Delete button with data-testid", () => {
  assert.match(tripDetailPage, /data-testid="chapter-action-delete"/);
  assert.match(tripDetailPage, /Delete/);
});

test("all action buttons are real <button> elements with onClick handlers", () => {
  assert.match(tripDetailPage, /onClick=\{\(\) => setConciergeOpen\(true\)\}/);
  assert.match(tripDetailPage, /onClick=\{\(\) => setOptimizeOpen\(true\)\}/);
  assert.match(tripDetailPage, /onClick={openEdit}/);
  assert.match(tripDetailPage, /onClick=\{\(\) => setConfirmDelete\(true\)\}/);
});

test("chapter cover action buttons have min-h-[44px] via COVER_BTN_BASE constant", () => {
  // Action buttons use COVER_PRIMARY/COVER_GHOST which extend COVER_BTN_BASE
  // COVER_BTN_BASE contains the min-h-[44px] touch target requirement
  assert.match(tripDetailPage, /COVER_BTN_BASE[\s\S]{0,200}min-h-\[44px\]/);
  // And chapter action buttons reference the constants
  assert.match(tripDetailPage, /className=\{COVER_PRIMARY\}/);
  assert.match(tripDetailPage, /className=\{COVER_GHOST\}/);
  assert.match(tripDetailPage, /className=\{COVER_DANGER\}/);
});

test("chapter cover action buttons have focus-visible outline", () => {
  assert.match(tripDetailPage, /focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent/);
});

// ── No card-level click-only navigation ──────────────────────────────────────

test("chapter cover section has no onClick (no card-level click navigation)", () => {
  const sectionTag = tripDetailPage.slice(
    tripDetailPage.indexOf('<section'),
    tripDetailPage.indexOf('<section') + 400,
  );
  assert.doesNotMatch(sectionTag, /onClick/);
});

// ── DS token usage ────────────────────────────────────────────────────────────

test("page uses bg-ds-onyx for chapter cover and modal surfaces", () => {
  assert.match(tripDetailPage, /bg-ds-onyx/);
});

test("page uses border-ds-pen-stroke for borders", () => {
  assert.match(tripDetailPage, /border-ds-pen-stroke/);
});

test("page uses text-ds-text for primary text", () => {
  assert.match(tripDetailPage, /text-ds-text(?!-)/);
});

test("page uses folio-ink-soft for secondary copy (Slice 2 paper conversion)", () => {
  assert.ok(
    tripDetailPage.includes("folio-ink-soft") || tripDetailPage.includes("text-ds-folio-ink-soft"),
    "trip detail page must use folio-ink-soft for secondary copy"
  );
});

test("page uses paper-world muted text token for metadata", () => {
  // Stage 3.5 UI architecture: trip detail page renders on paper canvas;
  // muted text uses folio-ink-mist instead of cream text-ds-text-tertiary.
  assert.match(tripDetailPage, /text-ds-folio-ink-mist/);
});

test("page uses marine-ink for primary CTA (Slice 2 paper conversion)", () => {
  assert.ok(
    tripDetailPage.includes("marine-ink") || tripDetailPage.includes("bg-ds-marine-ink"),
    "trip detail page must use marine-ink for primary CTA buttons"
  );
});

test("page uses text-ds-text-inverse on accent button", () => {
  assert.match(tripDetailPage, /text-ds-text-inverse/);
});

test("page uses text-ds-warning for destructive action", () => {
  assert.match(tripDetailPage, /text-ds-warning/);
});

test("page uses ds-elevation-2 shadow for chapter cover card", () => {
  assert.match(tripDetailPage, /ds-elevation-2/);
});

// ── No raw hex or legacy palette in chapter cover ────────────────────────────

test("page does not use raw hex color strings in chapter cover (no #hex patterns)", () => {
  // The page should not have gradient strings with raw hex
  assert.doesNotMatch(tripDetailPage, /DESTINATION_GRADIENTS/);
  assert.doesNotMatch(tripDetailPage, /getDestinationGradient/);
  assert.doesNotMatch(tripDetailPage, /DEFAULT_GRADIENT/);
});

test("page does not use destination-bg or destination-overlay (raw rgba gradients removed)", () => {
  assert.doesNotMatch(tripDetailPage, /destination-bg/);
  assert.doesNotMatch(tripDetailPage, /destination-overlay/);
});

test("page does not use bg-white in modal dialogs", () => {
  assert.doesNotMatch(tripDetailPage, /bg-white/);
});

test("page does not use text-slate-* in modal dialogs", () => {
  assert.doesNotMatch(tripDetailPage, /text-slate-/);
});

test("page does not use border-slate-* in modal dialogs", () => {
  assert.doesNotMatch(tripDetailPage, /border-slate-/);
});

test("page does not use sky-500 (legacy focus ring color) in modal dialogs", () => {
  assert.doesNotMatch(tripDetailPage, /sky-500/);
});

// ── No PageHeader import (replaced by chapter cover) ─────────────────────────

test("page does not import PageHeader (replaced by chapter cover composition)", () => {
  assert.doesNotMatch(tripDetailPage, /from "@\/components\/layout\/PageHeader"/);
  assert.doesNotMatch(tripDetailPage, /PageHeader/);
});

// ── No fake/mock/sample data ──────────────────────────────────────────────────

test("page does not contain hardcoded mock brand names or sample data", () => {
  // Check for fake hotel/brand names and sample data strings (exclude CSS class names like placeholder:)
  assert.doesNotMatch(tripDetailPage, /Marriott|Hilton|Four Seasons/i);
  assert.doesNotMatch(tripDetailPage, /"sample |sample data|sample_/i);
  // 'placeholder' as CSS utility (placeholder:text-...) is allowed; as a string value it is not
  assert.doesNotMatch(tripDetailPage, /"placeholder"/i);
});

test("page uses real trip data only (no fabricated strings)", () => {
  // Destination comes from real trip.destination, not a constant
  assert.match(tripDetailPage, /trip\?\.destination/);
});

// ── No backend/provider imports ───────────────────────────────────────────────

test("page does not import from provider or backend paths", () => {
  assert.doesNotMatch(tripDetailPage, /from "@\/lib\/concierge"/);
  assert.doesNotMatch(tripDetailPage, /from "@\/lib\/flights"/);
  assert.doesNotMatch(tripDetailPage, /from "@\/lib\/hotels"/);
  assert.doesNotMatch(tripDetailPage, /from "\.\.\/\.\.\/backend\//);
});

// ── Preserved behaviors ───────────────────────────────────────────────────────

// Journey Desk PR 1 removed the readiness cockpit from the page (the component
// file remains in the repo, unused). See blueprint §4.
test("page no longer imports or renders TripReadinessCockpit", () => {
  assert.doesNotMatch(tripDetailPage, /from "@\/components\/trips\/TripReadinessCockpit"/);
  assert.doesNotMatch(tripDetailPage, /TripReadinessCockpit/);
});

test("page still imports and renders TripBuilder", () => {
  assert.match(tripDetailPage, /from "@\/components\/trips\/TripBuilder"/);
  assert.match(tripDetailPage, /<TripBuilder/);
});

test("page still imports and renders AIConciergePanel", () => {
  assert.match(tripDetailPage, /from "@\/components\/trips\/AIConciergePanel"/);
  assert.match(tripDetailPage, /AIConciergePanel/);
});

test("page still imports and renders OptimizeTripModal", () => {
  assert.match(tripDetailPage, /from "@\/components\/trips\/OptimizeTripModal"/);
  assert.match(tripDetailPage, /OptimizeTripModal/);
});

test("page wires TripBrief with the trip prop", () => {
  assert.match(tripDetailPage, /trip={trip}/);
});

test("page still passes itineraryDays to a trip surface (OptimizeTripModal)", () => {
  assert.match(tripDetailPage, /itineraryDays={itineraryDays}/);
});

test("Concierge still opens from the cover action (not the removed cockpit)", () => {
  assert.match(tripDetailPage, /data-testid="chapter-action-concierge"/);
  assert.match(tripDetailPage, /setConciergeOpen\(true\)/);
});

test("TripBuilder has key prop for forced remount on update", () => {
  assert.match(tripDetailPage, /key={tripBuilderKey}/);
});

test("TripBuilder receives destination, startDate, endDate props from real trip data", () => {
  assert.match(tripDetailPage, /destination={trip\?\.destination \?\? ""}/);
  assert.match(tripDetailPage, /startDate={trip\?\.startDate}/);
  assert.match(tripDetailPage, /endDate={trip\?\.endDate}/);
});

test("chapter cover appears before the Brief JSX in page", () => {
  const coverPos = tripDetailPage.indexOf('data-testid="trip-chapter-cover"');
  const briefJsxPos = tripDetailPage.indexOf("<TripBrief");
  assert.ok(coverPos < briefJsxPos, "Chapter cover should appear before the Brief JSX element");
});

test("Brief (Plan Rail) appears before TripBuilder (Working Surface) in page", () => {
  const briefPos = tripDetailPage.indexOf("<TripBrief");
  const builderPos = tripDetailPage.indexOf("<TripBuilder");
  assert.ok(briefPos < builderPos, "Brief should appear before TripBuilder");
});

test("page preserves handleDelete → router.push to /trips", () => {
  assert.match(tripDetailPage, /router\.push\("\/trips"\)/);
});

test("page preserves handleUpdate flow with ensureTripDays", () => {
  assert.match(tripDetailPage, /ensureTripDays/);
  assert.match(tripDetailPage, /setTripBuilderKey/);
});

test("page preserves AIConciergePanel onItemAdded callback", () => {
  assert.match(tripDetailPage, /onItemAdded/);
});

test("page preserves AIConciergePanel onIdeaSaved callback", () => {
  assert.match(tripDetailPage, /onIdeaSaved/);
});

// ── No Google Flights URL changes ─────────────────────────────────────────────

test("page does not import or reference Duffel or Ignav providers", () => {
  assert.doesNotMatch(tripDetailPage, /duffel/i);
  assert.doesNotMatch(tripDetailPage, /ignav/i);
});

// ── Advisor briefing structure (TripReadinessCockpit) ────────────────────────

test("advisor briefing uses 'Concierge Notes' overline (not 'Trip Briefing')", () => {
  assert.match(cockpit, /Concierge Notes/);
  assert.doesNotMatch(cockpit, /Trip Briefing/);
});

test("advisor briefing has no score indicator (no X/4 coveredCount display)", () => {
  // The score display was: <span>{coveredCount}</span><span>/{signals.length}</span>
  // This pattern means we should NOT have the score fraction in a visual span
  assert.doesNotMatch(cockpit, /\{coveredCount\}.*\{signals\.length\}/s);
});

test("advisor briefing day coverage has no 'DAY COVERAGE' overline label", () => {
  assert.doesNotMatch(cockpit, /Day Coverage/);
  assert.doesNotMatch(cockpit, /DAY COVERAGE/);
});

test("advisor briefing next-step section has no 'NEXT STEP' overline label", () => {
  assert.doesNotMatch(cockpit, /Next Step/);
  assert.doesNotMatch(cockpit, /NEXT STEP/);
});

test("advisor briefing planning tools section has no 'ALSO TRY' label", () => {
  assert.doesNotMatch(cockpit, /Also try/);
  assert.doesNotMatch(cockpit, /ALSO TRY/);
});

test("advisor briefing next step description uses italic for advisor tone", () => {
  const nextActionBlock = cockpit.slice(
    cockpit.indexOf('data-testid="next-action-area"'),
    cockpit.indexOf('data-testid="planning-tools-strip"'),
  );
  assert.match(nextActionBlock, /italic/);
});

test("advisor briefing still derives signals from itemType (no fake data)", () => {
  assert.match(cockpit, /i\.itemType === "flight"/);
  assert.match(cockpit, /i\.itemType === "hotel"/);
  assert.match(cockpit, /i\.itemType === "meal"/);
  assert.match(cockpit, /i\.itemType === "activity"/);
});

test("advisor briefing preserves honest signal copy ('Looks like', 'Still needs')", () => {
  assert.match(cockpit, /Looks like/);
  assert.match(cockpit, /Still needs/);
});

test("advisor briefing day coverage uses 'days planned' phrase (not 'have plans')", () => {
  // New phrasing in the summary text
  assert.match(cockpit, /days planned/);
});
