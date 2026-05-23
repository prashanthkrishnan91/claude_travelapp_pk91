/**
 * Journey Desk v1B — Ideas Tray + Notes.
 *
 * Turns Trip Ideas into the placement-first tray from the approved v2 prototype:
 * mobile bottom sheet / desktop right drawer, one bold primary action per card,
 * the typed note hierarchy, and contextual secondary actions — all wired only to
 * real durable writes (day-level assignIdeaToDay, status/note updateIdeaMeta,
 * deleteItem). No slot-level persistence exists, so placement is honestly
 * day-level ("Add to Day…") and never labels a fabricated slot.
 *
 * Source-scan contract tests (no DOM/browser in this environment).
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const tray = readFileSync(
  new URL("../src/components/trips/IdeasTray.tsx", import.meta.url),
  "utf8",
);
const page = readFileSync(
  new URL("../src/app/trips/[id]/page.tsx", import.meta.url),
  "utf8",
);
const css = readFileSync(
  new URL("../src/app/globals.css", import.meta.url),
  "utf8",
);

// ── Tray shell ────────────────────────────────────────────────────────────────

test("tray has a stable testid and is a modal dialog", () => {
  assert.match(tray, /data-testid="journey-desk-ideas-tray"/);
  assert.match(tray, /role="dialog"/);
  assert.match(tray, /aria-modal="true"/);
});

test("tray header communicates purpose (place one in / from your Private Folio)", () => {
  assert.match(tray, /Place one in\./);
  assert.match(tray, /From your Private Folio\./);
});

test("tray shows the real candidate count from the ideas array", () => {
  assert.match(tray, /\{ideas\.length\}\s*\{ideas\.length === 1 \? "candidate" : "candidates"\}/);
});

test("tray is a bottom sheet on mobile and a right drawer on desktop", () => {
  assert.match(tray, /bottom-0/);
  assert.match(tray, /lg:right-0/);
});

test("tray filter chips cover All/Hotels/Flights/Dining/Places with real counts", () => {
  assert.match(tray, /label: "All"/);
  assert.match(tray, /label: "Hotels"/);
  assert.match(tray, /label: "Flights"/);
  assert.match(tray, /label: "Dining"/);
  assert.match(tray, /label: "Places"/);
  // counts derive from real itemType, never fabricated
  assert.match(tray, /ideas\.filter\(\(i\) => i\.itemType === key\)\.length/);
});

// ── Placement-first card, honest writes ───────────────────────────────────────

test("card primary action is placement-first and day-level (Add to Day… / Keep as Maybe)", () => {
  assert.match(tray, /Add to Day…/);
  assert.match(tray, /Keep as Maybe/);
  assert.match(tray, /Add to which day/);
});

test("placement is wired to the real day-level write via onAssign(day.id)", () => {
  assert.match(tray, /onAssign\(day\.id\)/);
  assert.match(tray, /const dayAssignable = days\.length > 0/);
});

test("no fabricated slot label — placement never claims a Dinner/Morning/etc. slot", () => {
  assert.doesNotMatch(tray, /Dinner/i);
  assert.doesNotMatch(tray, /·\s*(Morning|Afternoon|Evening)/i);
  assert.doesNotMatch(tray, /Add to Day \d+ ·/);
});

test("status fallback uses the durable updateIdeaMeta path (ideaStatus maybe)", () => {
  assert.match(tray, /ideaStatus: "maybe"/);
});

test("primary action uses marine ink; it is the one bold action per card", () => {
  assert.match(tray, /data-testid="ideas-tray-primary-action"[\s\S]{0,400}bg-ds-marine-ink/);
});

// ── Note hierarchy ─────────────────────────────────────────────────────────────

test("private marginalia reads the saved user note (carryover preserved)", () => {
  assert.match(tray, /x\.userNote \?\? x\.user_note/);
  assert.match(tray, /data-testid="ideas-tray-note-private"/);
  assert.match(tray, /jd-note-private/);
});

test("private note is italic serif (distinct from concierge reason)", () => {
  assert.match(tray, /jd-note-private[\s\S]{0,80}font-serif italic/);
});

test("concierge reason is a distinct muted helper, shown only when real and not equal to the user note", () => {
  assert.match(tray, /data-testid="ideas-tray-note-concierge"/);
  assert.match(tray, /reason && reason !== note/);
});

test("provider facts (rating) render only from real data", () => {
  assert.match(tray, /const r = x\.rating as number/);
  assert.match(tray, /if \(!r \|\| typeof r !== "number"\) return null/);
});

test("tray fabricates no prices/weather", () => {
  assert.doesNotMatch(tray, /\$\d|weather|°|sunny|rain/i);
});

// ── Contextual secondary actions (quiet links) ────────────────────────────────

test("secondary actions are contextual to real data (map link, flight booking)", () => {
  assert.match(tray, /mapsUrl &&/);
  assert.match(tray, /item\.itemType === "flight" && bookingUrl/);
  assert.match(tray, /Google Flights/);
});

test("tray closes on Escape and on scrim/close click", () => {
  assert.match(tray, /e\.key === "Escape"/);
  assert.match(tray, /aria-label="Close ideas tray"/);
});

// ── Page integration with v1A ─────────────────────────────────────────────────

test("page imports and renders the Ideas Tray", () => {
  assert.match(page, /import \{ IdeasTray \} from "@\/components\/trips\/IdeasTray"/);
  assert.match(page, /<IdeasTray/);
});

test("the v1A Brief 'Review ideas' opens the tray (not a legacy tab)", () => {
  assert.match(page, /onReview=\{\(\) => setIdeasTrayOpen\(true\)\}/);
  assert.match(page, /const \[ideasTrayOpen, setIdeasTrayOpen\] = useState\(false\)/);
});

test("a discoverable Ideas Tray launcher exists in the Journey Desk area", () => {
  assert.match(page, /data-testid="journey-desk-ideas-launcher"/);
});

test("tray actions are wired to real durable writes only", () => {
  assert.match(page, /await assignIdeaToDay\(itemId, dayId\)/);
  assert.match(page, /await updateIdeaMeta\(itemId, currentDetails, patch\)/);
  assert.match(page, /await deleteItem\(itemId\)/);
  assert.match(page, /onAssign=\{handleIdeaAssign\}/);
  assert.match(page, /onUpdateMeta=\{handleIdeaMeta\}/);
  assert.match(page, /onRemove=\{handleIdeaRemove\}/);
});

test("v1A surfaces are not regressed (cover, Brief, Dayboard still present)", () => {
  assert.match(page, /data-testid="trip-chapter-cover"/);
  assert.match(page, /<TripBrief/);
  assert.match(page, /<Dayboard/);
});

// ── CSS primitives, reduced-motion guarded ────────────────────────────────────

test("tray paper surfaces and brass note hairline are defined with tokens", () => {
  assert.match(css, /\.journey-desk-tray \{/);
  assert.match(css, /\.jd-tray-card \{/);
  const idx = css.indexOf(".jd-note-private {");
  assert.ok(idx !== -1, ".jd-note-private must be defined");
  assert.match(css.slice(idx, idx + 200), /var\(--ds-ember-brass\)/);
});

test("tray entrance animation is reduced-motion guarded", () => {
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)[\s\S]{0,120}\.jd-tray-enter \{ animation: none/);
});
