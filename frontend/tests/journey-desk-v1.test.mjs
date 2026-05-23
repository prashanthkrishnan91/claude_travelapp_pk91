/**
 * Journey Desk v1A — trip detail planning shell.
 *
 * Source of truth: docs/ai/design/JOURNEY_DESK_V1_BLUEPRINT.md + the approved
 * v2 prototype. v1A ships the 10-second mobile read: one dark cinematic cover
 * hero, the calm Brief (where · what is fixed · what still needs choosing), and
 * the collapsed Dayboard. Ideas Tray, expanded day + decision strip, and the
 * desktop three-zone adaptation are sequenced in later slices (v1B–v1D); the
 * Map Fold-Out is v2.
 *
 * These are source-scan contract tests (no DOM/browser in this environment).
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const page = readFileSync(
  new URL("../src/app/trips/[id]/page.tsx", import.meta.url),
  "utf8",
);
const brief = readFileSync(
  new URL("../src/components/trips/TripBrief.tsx", import.meta.url),
  "utf8",
);
const dayboard = readFileSync(
  new URL("../src/components/trips/Dayboard.tsx", import.meta.url),
  "utf8",
);
const css = readFileSync(
  new URL("../src/app/globals.css", import.meta.url),
  "utf8",
);

// ── Page composition ──────────────────────────────────────────────────────────

test("page imports TripBrief, Dayboard and fetchTripIdeas", () => {
  assert.match(page, /import \{ TripBrief \} from "@\/components\/trips\/TripBrief"/);
  assert.match(page, /import \{ Dayboard \} from "@\/components\/trips\/Dayboard"/);
  assert.match(page, /fetchTripIdeas/);
});

test("page renders the Brief and the Dayboard", () => {
  assert.match(page, /<TripBrief/);
  assert.match(page, /<Dayboard/);
});

test("cover section is the one dark cinematic hero (journey-desk-cover)", () => {
  assert.match(page, /data-testid="trip-chapter-cover"[\s\S]{0,200}journey-desk-cover/);
});

test("page tracks real Trip Ideas state fed from fetchTripIdeas", () => {
  assert.match(page, /const \[tripIdeas,\s*setTripIdeas\]\s*=\s*useState<ItineraryItem\[\]>\(\[\]\)/);
  assert.match(page, /fetchTripIdeas\(id\)\.then\(setTripIdeas\)/);
});

test("Brief receives real trip, days and ideas (no fabricated props)", () => {
  assert.match(page, /<TripBrief[\s\S]{0,160}days=\{itineraryDays\}[\s\S]{0,80}ideas=\{tripIdeas\}/);
});

test("Brief review action opens the Ideas Tray (placement surface)", () => {
  assert.match(page, /onReview=\{\(\) => setIdeasTrayOpen\(true\)\}/);
});

test("Dayboard selecting a day selects it for the expanded day panel", () => {
  assert.match(page, /<Dayboard[\s\S]{0,200}onSelectDay=\{\(day\) => setSelectedDayId\(day\.id\)\}/);
});

test("ideas state refreshes when an idea is assigned or saved", () => {
  assert.match(page, /refreshIdeas\(\)/);
});

test("cover → Brief → Dayboard → cockpit order is preserved", () => {
  const cover = page.indexOf('data-testid="trip-chapter-cover"');
  const b = page.indexOf("<TripBrief");
  const d = page.indexOf("<Dayboard");
  const cockpit = page.indexOf("<TripReadinessCockpit");
  assert.ok(cover < b && b < d && d < cockpit, "expected cover < Brief < Dayboard < cockpit");
});

// ── Regression: existing trip-detail contracts preserved ──────────────────────

test("page preserves cover testid, section rule, cockpit, builder and cover tab", () => {
  assert.match(page, /data-testid="trip-chapter-cover"/);
  assert.match(page, /editorial-section-rule/);
  assert.match(page, /<TripReadinessCockpit/);
  assert.match(page, /<TripBuilder/);
  assert.match(page, /folio-cover-tab/);
});

// ── The Brief — honest derivation, no fabrication ─────────────────────────────

test("Brief has its own section testid", () => {
  assert.match(brief, /data-testid="journey-desk-brief"/);
});

test("Brief derives placed items from the real itinerary days", () => {
  assert.match(brief, /days\.flatMap\(\(d\) => d\.items \?\? \[\]\)/);
});

test("Brief 'still to decide' count comes from the real ideas array", () => {
  assert.match(brief, /const ideasCount = ideas\.length/);
  assert.match(brief, /still to decide/);
});

test("Brief detects flight / hotel anchors by itemType", () => {
  assert.match(brief, /i\.itemType === "flight"/);
  assert.match(brief, /i\.itemType === "hotel"/);
});

test("Brief shows a pending line for each missing essential anchor (flight + stay)", () => {
  assert.match(brief, /if \(!hasFlight\) pendingLines\.push/);
  assert.match(brief, /if \(!hasHotel\) pendingLines\.push/);
});

test("Brief shows fixed lines only for anchors that really exist (omit, never placeholder)", () => {
  assert.match(brief, /if \(hasFlight\) fixedLines\.push/);
  assert.match(brief, /if \(hasHotel\) fixedLines\.push/);
});

test("empty-trip Brief is honest and does not contradict the readiness notes", () => {
  // No fabricated "nothing to decide" when essentials are clearly missing.
  assert.doesNotMatch(brief, /Nothing to decide yet/);
  // Instead it nudges to real discovery surfaces.
  assert.match(brief, /No saved ideas yet/);
  assert.match(brief, /href="\/explore"/);
  assert.match(brief, /href="\/saved"/);
});

test("Brief shows real placed progress", () => {
  assert.match(brief, /\{placedCount\} of \{totalCandidates\} placed/);
});

test("Brief primary review action uses marine ink (paper-world primary)", () => {
  assert.match(brief, /data-testid="jd-brief-review-action"[\s\S]{0,200}bg-ds-marine-ink/);
});

test("Brief has exactly one marine-fill primary action (one primary per surface)", () => {
  const matches = brief.match(/bg-ds-marine-ink/g) ?? [];
  assert.equal(matches.length, 1, "Brief must carry exactly one bold marine primary action");
});

test("Brief contains no fabricated brands, weather or sample data", () => {
  assert.doesNotMatch(brief, /Marriott|Hilton|Four Seasons/i);
  assert.doesNotMatch(brief, /weather|°|sunny|rain/i);
  assert.doesNotMatch(brief, /"sample|placeholder"/i);
});

// ── Dayboard — collapsed day cards, timezone-safe, no fake data ───────────────

test("Dayboard and its day cards carry stable testids", () => {
  assert.match(dayboard, /data-testid="journey-desk-dayboard"/);
  assert.match(dayboard, /data-testid="journey-desk-day-card"/);
});

test("Dayboard renders the day numeral from real dayNumber", () => {
  assert.match(dayboard, /day\.dayNumber/);
});

test("Dayboard date formatting is timezone-safe (UTC, never local-shifted)", () => {
  assert.match(dayboard, /Date\.UTC\(year, month - 1, day\)/);
  assert.match(dayboard, /timeZone: "UTC"/);
});

test("Dayboard placed count comes from real item count", () => {
  assert.match(dayboard, /\(day\.items \?\? \[\]\)\.length/);
  assert.match(dayboard, /placed/);
});

test("Dayboard renders the calm brass still-deciding dot (not an alert)", () => {
  assert.match(dayboard, /jd-decide-dot/);
  assert.match(dayboard, /Still deciding/);
});

test("Dayboard day cards are real buttons", () => {
  assert.match(dayboard, /type="button"/);
});

test("Dayboard returns null when there are no days (no empty scaffold)", () => {
  assert.match(dayboard, /if \(days\.length === 0\) return null/);
});

test("Dayboard fabricates no weather", () => {
  assert.doesNotMatch(dayboard, /weather|°|sunny|rain/i);
});

// ── CSS — cinematic cover + paper Brief/Dayboard, reduced-motion guarded ──────

test("globals.css defines the dark cinematic cover on warm-dark (cinema-deep), not black", () => {
  const idx = css.indexOf(".journey-desk-cover {");
  assert.ok(idx !== -1, ".journey-desk-cover must be defined");
  const block = css.slice(idx, idx + 600);
  assert.match(block, /var\(--ds-cinema-deep\)/);
  assert.match(block, /rgba\(197, 148, 77/); // brass hairline border
});

test("cover has a cinematic corner vignette layer", () => {
  assert.match(css, /\.journey-desk-cover::after/);
});

test("globals.css defines the paper Brief and Dayboard primitives", () => {
  assert.match(css, /\.journey-desk-brief \{/);
  assert.match(css, /\.jd-day-card \{/);
});

test("still-deciding dot uses the brass token", () => {
  const idx = css.indexOf(".jd-decide-dot {");
  assert.ok(idx !== -1, ".jd-decide-dot must be defined");
  assert.match(css.slice(idx, idx + 300), /var\(--ds-ember-brass\)/);
});

test("Dayboard card motion is reduced-motion guarded", () => {
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)[\s\S]{0,200}\.jd-day-card \{ transition: none/);
});
