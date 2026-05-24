/**
 * Journey Desk v1C — Expanded Day + Decision Strip.
 *
 * Selecting a Dayboard day opens an expanded day panel in the Journey Desk area
 * that groups real placed items into Morning / Afternoon / Evening / Logistics
 * (+ honest "Anytime" for untimed items) using the durable classifier — no
 * fabricated slots. A calm brass-dot decision strip summarizes open decisions
 * honestly and opens the v1B Ideas Tray. Read-only except for tray placement.
 *
 * Source-scan contract tests (no DOM/browser in this environment).
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const panel = readFileSync(
  new URL("../src/components/trips/ExpandedDayPanel.tsx", import.meta.url),
  "utf8",
);
const dayParts = readFileSync(
  new URL("../src/lib/dayParts.ts", import.meta.url),
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

// ── Grouping logic — real signals only, honest Logistics + Anytime ────────────

test("classifier reads real signals only (dayPart, timeLabel, startTime) — never invents a time", () => {
  assert.match(dayParts, /d\.dayPart as string/);
  assert.match(dayParts, /d\.timeLabel as string/);
  assert.match(dayParts, /parseHour\(item\.startTime\)/);
  assert.match(dayParts, /return "unscheduled"/);
});

test("Logistics = flights / hotels / transit", () => {
  assert.match(dayParts, /LOGISTICS_TYPES = new Set\(\["flight", "hotel", "transit"\]\)/);
  assert.match(dayParts, /return "logistics"/);
});

test("untimed non-logistics items fall to an honest Anytime bucket (no fabricated slot)", () => {
  assert.match(dayParts, /part === "unscheduled" \? "anytime" : part/);
});

test("section order is Morning / Afternoon / Evening / Logistics / Anytime", () => {
  assert.match(
    dayParts,
    /label: "Morning"[\s\S]*label: "Afternoon"[\s\S]*label: "Evening"[\s\S]*label: "Logistics"[\s\S]*label: "Anytime"/,
  );
});

test("only non-empty sections are rendered (silent empties)", () => {
  assert.match(dayParts, /\.filter\(\(s\) => buckets\[s\.key\]\.length > 0\)/);
});

// ── Expanded day panel ────────────────────────────────────────────────────────

test("expanded day panel has a stable testid and groups via the shared classifier", () => {
  assert.match(panel, /data-testid="journey-desk-expanded-day"/);
  assert.match(panel, /groupJourneyDeskDay\(day\.items/);
});

test("header shows day number + real date + where-line only when present", () => {
  assert.match(panel, /Day \{day\.dayNumber\}/);
  assert.match(panel, /const whereLine = day\.title \|\| day\.summary \|\| ""/);
  assert.match(panel, /whereLine &&/);
});

test("no fabricated weather in the expanded day", () => {
  assert.doesNotMatch(panel, /weather|°|sunny|rain/i);
});

test("placed-item time is shown only from real startTime/timeLabel", () => {
  assert.match(panel, /item\.startTime/);
  assert.match(panel, /function timeLabelOf/);
});

// ── Decision strip ─────────────────────────────────────────────────────────────

test("decision strip renders with a calm brass dot and honest, trip-level summary", () => {
  assert.match(panel, /data-testid="jd-decision-strip"/);
  assert.match(panel, /jd-decide-dot/);
  assert.match(panel, /Nothing placed in this day yet/);
  // Idea count is trip-level (the whole tray) — copy says so, not a day filter.
  assert.match(panel, /trip idea\$\{ideasCount === 1 \? "" : "s"\} still in the tray/);
  assert.match(panel, /No open decisions/);
  // Must NOT imply day-specific filtering of unplaced ideas.
  assert.doesNotMatch(panel, /Still deciding: \$\{ideasCount\}/);
  assert.doesNotMatch(panel, /ideas? not placed/);
});

test("decision strip is calm paper, never a red/alert banner", () => {
  assert.doesNotMatch(panel, /ds-warning|bg-red|alert|urgent/i);
  const idx = css.indexOf(".jd-decision-strip {");
  assert.ok(idx !== -1, ".jd-decision-strip must be defined");
  assert.doesNotMatch(css.slice(idx, idx + 220), /--ds-warning|--ds-whisper-coral/);
});

test("decision strip 'Add from Ideas Tray' opens the tray (no day-specific filter faked)", () => {
  assert.match(panel, /data-testid="jd-decision-add-from-ideas"/);
  assert.match(panel, /Add from Ideas Tray/);
  assert.match(panel, /onAddFromIdeas/);
});

// ── Note hierarchy on placed cards (same keys as Ideas Tray / legacy tab) ─────

test("placed-item user note renders as private marginalia from the same note key", () => {
  assert.match(panel, /x\.userNote \?\? x\.user_note/);
  assert.match(panel, /data-testid="jd-day-item-note"/);
  assert.match(panel, /jd-note-private[\s\S]{0,80}font-serif italic/);
});

test("concierge reason is distinct and only shown when real and not equal to the note", () => {
  assert.match(panel, /reason && reason !== note/);
});

test("provider rating renders only from real numeric data", () => {
  assert.match(panel, /typeof r === "number" && r \? r\.toFixed\(1\) : null/);
});

test("contextual secondary links appear only where real (map, flight booking)", () => {
  assert.match(panel, /mapsUrl &&/);
  assert.match(panel, /item\.itemType === "flight" && bookingUrl/);
});

// ── Page integration ──────────────────────────────────────────────────────────

test("page selects a Dayboard day and renders the expanded panel for it", () => {
  assert.match(page, /const \[selectedDayId, setSelectedDayId\] = useState<string \| null>\(null\)/);
  assert.match(page, /onSelectDay=\{\(day\) => setSelectedDayId\(day\.id\)\}/);
  assert.match(page, /<ExpandedDayPanel/);
  // The expanded panel is now passed inline via Dayboard's inlineDayPanel prop
  // (renders directly under the selected day card, not after the full list).
  // The day is derived from expandedDay = itineraryDays.find(...)
  assert.match(page, /expandedDay = selectedDayId \? itineraryDays\.find\(\(d\) => d\.id === selectedDayId\)/);
  assert.match(page, /inlineDayPanel=\{expandedDay \?/);
});

test("expanded day decision strip opens the v1B Ideas Tray (assignments refresh via existing state)", () => {
  assert.match(page, /onAddFromIdeas=\{\(\) => setIdeasTrayOpen\(true\)\}/);
  assert.match(page, /ideasCount=\{tripIdeas\.length\}/);
});

test("Dayboard receives the selected day for highlight", () => {
  assert.match(page, /selectedDayId=\{selectedDayId\}/);
});

test("v1A/v1B surfaces are not regressed (cover, Brief, Dayboard, Ideas Tray present)", () => {
  assert.match(page, /data-testid="trip-chapter-cover"/);
  assert.match(page, /<TripBrief/);
  assert.match(page, /<Dayboard/);
  assert.match(page, /<IdeasTray/);
});

// ── CSS ─────────────────────────────────────────────────────────────────────

test("expanded day + item surfaces are token-built paper", () => {
  assert.match(css, /\.journey-desk-day \{/);
  assert.match(css, /\.jd-day-item \{/);
});
