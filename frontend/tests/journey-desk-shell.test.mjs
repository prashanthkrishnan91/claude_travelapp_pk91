/**
 * Journey Desk PR 1 — Trip Detail immersive shell + mood + desktop plan-desk.
 *
 * Implements docs/ai/design/JOURNEY_DESK_PAGE_DIRECTION_AND_BLUEPRINT.md:
 *   - /trips/[id] joins the immersive floating-sidebar shell (data-atelier-shell
 *     "journey-desk"), distinct from My Journeys' Reading Room (/trips).
 *   - A marine-cool warm desk canvas hosts one WIDE floating paper folio.
 *   - The cinematic cover is a full-width band atop a two-zone planning desk:
 *     a sticky Plan Rail (read-only Brief + Dayboard) + a wide Working Surface.
 *   - The legacy Trip Readiness / "concierge notes" disclosure is removed.
 *   - Mobile tab IA (Brief · Itinerary · Ideas) and functional ownership preserved.
 *
 * Source-scan contract tests (no DOM/browser in this environment).
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const appShell = readFileSync(
  new URL("../src/components/layout/AppShell.tsx", import.meta.url),
  "utf8",
);
const css = readFileSync(
  new URL("../src/app/globals.css", import.meta.url),
  "utf8",
);
const page = readFileSync(
  new URL("../src/app/trips/[id]/page.tsx", import.meta.url),
  "utf8",
);

// ── AppShell — Trip Detail is an immersive floating-sidebar room ───────────────

test("AppShell matches /trips/[id] but not the /trips index", () => {
  assert.match(
    appShell,
    /const isTripDetailRoute = pathname\.startsWith\("\/trips\/"\) && pathname !== "\/trips"/,
  );
});

test("AppShell includes Trip Detail in the immersive-room set", () => {
  assert.match(appShell, /const isImmersiveRoom =[^;]*isTripDetailRoute/);
});

test("AppShell tags the Trip Detail shell as data-atelier-shell=journey-desk", () => {
  assert.match(appShell, /isTripDetailRoute \? "journey-desk"/);
});

test("AppShell renders the floating AtelierNavArtifact on Trip Detail", () => {
  assert.match(appShell, /\{isTripDetailRoute && <AtelierNavArtifact \/>\}/);
});

// ── globals.css — the Journey Desk shell primitives ───────────────────────────

test("CSS suppresses the SaaS sidebar on the journey-desk shell", () => {
  assert.match(
    css,
    /\.atelier-atmosphere-root\[data-atelier-shell="journey-desk"\] \.folio-sidebar \{\s*display: none !important;/,
  );
});

test("journey-desk-room-canvas exists and uses a marine-cool ambient (not Reading Room sandstone)", () => {
  const idx = css.indexOf(".journey-desk-room-canvas {");
  assert.ok(idx !== -1, ".journey-desk-room-canvas must be defined");
  const block = css.slice(idx, idx + 600);
  // The cool work-surface tint distinguishes it from .trips-room-canvas (sandstone).
  assert.match(block, /--ds-marine-ink/);
});

test("journey-desk-stage is a WIDE floating folio (max-width 94rem)", () => {
  const idx = css.indexOf(".journey-desk-stage {");
  assert.ok(idx !== -1, ".journey-desk-stage must be defined");
  const block = css.slice(idx, idx + 1100);
  assert.match(block, /max-width:\s*94rem/);
  assert.match(block, /overflow:\s*hidden/);
});

test("journey-desk-layout is a two-zone grid on desktop (21rem + 1fr)", () => {
  assert.match(css, /\.journey-desk-layout \{/);
  assert.match(css, /grid-template-columns:\s*21rem minmax\(0, 1fr\)/);
});

test("journey-desk-plan-rail is sticky on desktop", () => {
  const idx = css.indexOf(".journey-desk-plan-rail {");
  assert.ok(idx !== -1, ".journey-desk-plan-rail must be defined");
  const block = css.slice(idx, idx + 700);
  assert.match(block, /position:\s*sticky/);
});

test("journey-desk-surface and cover-band primitives exist", () => {
  assert.match(css, /\.journey-desk-surface \{/);
  assert.match(css, /\.journey-desk-cover-band \{/);
});

// ── page.tsx — composition ─────────────────────────────────────────────────────

test("page wraps the body in the room canvas → wide paper stage", () => {
  assert.match(page, /className="journey-desk-room-canvas"/);
  assert.match(page, /data-testid="trip-mobile-workspace" className="journey-desk-stage/);
});

test("cover is a full-width band atop the stage (no narrow max-w-4xl cap)", () => {
  assert.match(page, /data-testid="trip-chapter-cover"[\s\S]{0,200}journey-desk-cover journey-desk-cover-band/);
  assert.doesNotMatch(page, /lg:max-w-4xl/);
});

test("desktop two-zone layout: Plan Rail (Brief + Dayboard) | Working Surface (TripBuilder)", () => {
  assert.match(page, /className="journey-desk-layout"/);
  // Plan Rail hosts the read-only Brief + Dayboard.
  assert.match(page, /trip-mobile-panel-brief[\s\S]{0,160}journey-desk-plan-rail/);
  const rail = page.indexOf("journey-desk-plan-rail");
  const brief = page.indexOf("<TripBrief");
  const dayboard = page.indexOf("<Dayboard");
  const surface = page.indexOf("journey-desk-surface");
  const builder = page.indexOf("<TripBuilder");
  assert.ok(rail < brief && brief < dayboard, "Plan Rail wraps Brief then Dayboard");
  assert.ok(dayboard < surface && surface < builder, "Working Surface (TripBuilder) follows the Plan Rail");
});

// ── Trip Readiness / concierge-notes disclosure removed ───────────────────────

test("the Trip Readiness / concierge-notes disclosure is fully removed", () => {
  assert.doesNotMatch(page, /TripReadinessCockpit/);
  assert.doesNotMatch(page, /cockpitOpen/);
  assert.doesNotMatch(page, /trip-readiness-toggle/);
  assert.doesNotMatch(page, /Trip readiness · concierge notes/);
});

// ── Mobile tab IA preserved (Brief · Itinerary · Ideas) ───────────────────────

test("mobile 3-tab workspace IA is preserved", () => {
  assert.match(page, /data-testid="trip-mobile-workspace-switcher"/);
  assert.match(page, /trip-mobile-tab-brief/);
  assert.match(page, /trip-mobile-tab-itinerary/);
  assert.match(page, /trip-mobile-tab-ideas/);
  // The switcher is hidden on the desktop two-zone desk.
  assert.match(page, /lg:hidden[\s\S]{0,120}data-testid="trip-mobile-workspace-switcher"/);
});

// ── Desktop two-zone discipline (Plan Rail summary + Itinerary Working Surface) ─

const builder = readFileSync(
  new URL("../src/components/trips/TripBuilder.tsx", import.meta.url),
  "utf8",
);

test("Working Surface exposes Itinerary | Ideas tabs on desktop (Build is not a tab)", () => {
  assert.match(page, /data-testid="jd-surface-tabs"/);
  assert.match(page, /hidden lg:flex/);               // the tab strip is desktop-only
  assert.match(page, /jd-surface-tab-\$\{t\.id\}/);    // per-tab testid (templated)
  assert.match(page, /id: "itinerary"[\s\S]{0,40}label: "Itinerary"/);
  assert.match(page, /id: "ideas"[\s\S]{0,40}label: "Ideas"/);
  assert.doesNotMatch(page, /jd-surface-tab-build/);
});

test("the expanded selected-day detail is mobile-only in the Plan Rail (lg:hidden)", () => {
  // It duplicates the Itinerary Working Surface on desktop, so the rail hides it.
  assert.match(page, /lg:hidden">\s*<ExpandedDayPanel/);
});

test("the Add-to-Day return banner is available on desktop (no lg:hidden)", () => {
  assert.match(page, /data-testid="jd-build-return-banner"/);
  assert.doesNotMatch(page, /lg:hidden[^"]*"\s*\n?\s*>[\s\S]{0,40}jd-build-return-banner/);
});

test("Build is hidden unless its workspace is active — never a permanent desktop column", () => {
  assert.match(builder, /trip-mobile-panel-build[\s\S]{0,260}mobileWorkspace === "build" \? "" : "hidden"/);
  // No lg: desktop re-show that would force Build visible beside the itinerary.
  assert.doesNotMatch(builder, /trip-mobile-panel-build[\s\S]{0,260}hidden lg:flex/);
});

test("a clear 'Add to Day' entry opens the existing add/build flow (not Ideas-only)", () => {
  // The desktop Working Surface header has a prominent Add-to-Day button that
  // opens the existing AddToDayDrawer → 4-vertical → Build flow.
  assert.match(page, /data-testid="jd-surface-add-to-day"/);
  assert.match(page, /onClick=\{\(\) => handleOpenAddToDay\(targetDay\)\}/);
  // The per-day "Add to this day" entry in the itinerary is preserved too.
  assert.match(builder, /onAddToDay=\{onAddToDay\}/);
  // The 4-vertical add drawer is still wired (flights/stays/dining/things to do).
  assert.match(page, /<AddToDayDrawer/);
  assert.match(page, /onSelectVertical=\{handleAddToDaySelectVertical\}/);
});

test("there is ONE canonical active day — no competing dropdown selector", () => {
  // The redundant "Add to" target-day dropdown is removed; Dayboard + itinerary
  // own day selection and the single Add-to-Day button uses the active day.
  assert.doesNotMatch(builder, /focus-within:outline-ds-accent/);
});

test("active-day stays in sync across Dayboard, itinerary, and the Add-to-Day label", () => {
  // Parent → child: the canonical active day drives TripBuilder focus.
  assert.match(page, /focusDayId=\{buildFocusDayId \?\? selectedDayId\}/);
  // Child → parent: an itinerary day-header click reports the active day back so
  // the Dayboard highlight + "Add to Day X" label update.
  assert.match(page, /onActiveDayChange=\{\(dayId\) => setSelectedDayId\(dayId\)\}/);
  assert.match(builder, /onSelect=\{\(id\) => \{ setSelectedDayId\(id\); onActiveDayChange\?\.\(id\); \}\}/);
  // The active day also expands in the itinerary (focus), via the focusDayId effect.
  assert.match(builder, /if \(focusDayId && days\.some[\s\S]{0,160}setExpandedDayNumber\(dn\)/);
});

// ── Functional ownership preserved (no behavior change) ───────────────────────

test("all functional surfaces remain mounted (ownership unchanged)", () => {
  assert.match(page, /<TripBrief/);          // read-only summary
  assert.match(page, /<Dayboard/);            // day spine
  assert.match(page, /<TripBuilder/);         // Build + Itinerary working surface
  assert.match(page, /<IdeasTray/);           // quick placement
  assert.match(page, /<AddToDayDrawer/);      // day-scoped add
  assert.match(page, /<MapFoldOut/);          // trip map
  assert.match(page, /<AIConciergePanel/);    // concierge
  assert.match(page, /onReview=\{\(\) => setActiveMobileWorkspace\("ideas"\)\}/); // Brief → Ideas tab
});
