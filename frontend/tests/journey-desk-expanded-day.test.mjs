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
  // Check only the decision-strip JSX region (not the whole panel, which now has a
  // legitimate text-ds-warning on the Remove confirm button for the destructive action).
  const stripRegion = panel.match(/data-testid="jd-decision-strip"[\s\S]{0,500}/)?.[0] ?? "";
  assert.ok(stripRegion.length > 0, "jd-decision-strip must be present");
  assert.doesNotMatch(stripRegion, /ds-warning|bg-red|alert|urgent/i);
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

// ── Slice 1: per-item actions — Back to Ideas + Remove from trip ──────────────

test("ExpandedDayPanel renders a per-item action toggle (MoreHorizontal kebab)", () => {
  assert.match(panel, /data-testid="jd-item-action-toggle"/);
  assert.match(panel, /MoreHorizontal/);
  assert.match(panel, /aria-label="Item actions"/);
  assert.match(panel, /aria-haspopup="menu"/);
});

test("item action menu has Back to Ideas and Remove from trip labels", () => {
  assert.match(panel, /data-testid="jd-item-back-to-ideas"/);
  assert.match(panel, /Back to Ideas/);
  assert.match(panel, /data-testid="jd-item-remove"/);
  assert.match(panel, /Remove from trip/);
});

test("Back to Ideas calls onUnplace with item.id and current details — never moveIdeaToTripIdeas", () => {
  // Must invoke the corrected unplace prop
  assert.match(panel, /onUnplace\?\.\(item\.id/);
  // Must never import or invoke the legacy orphan-gap path
  assert.doesNotMatch(panel, /moveIdeaToTripIdeas/);
});

test("Back to Ideas is non-destructive — never calls onRemoveItem", () => {
  // handleBackToIdeas calls onUnplace, not onRemoveItem
  assert.match(panel, /function handleBackToIdeas/);
  assert.doesNotMatch(panel, /onRemoveItem\?\.\([\s\S]{0,40}handleBackToIdeas/);
});

test("Remove from trip requires confirm before calling onRemoveItem (two-step)", () => {
  // First click arms the confirm step; only onConfirmRemove calls onRemoveItem
  assert.match(panel, /confirmItemId/);
  assert.match(panel, /handleRequestRemove/);
  assert.match(panel, /handleConfirmRemove/);
  assert.match(panel, /data-testid="jd-item-remove-confirm"/);
  assert.match(panel, /data-testid="jd-item-remove-confirm-yes"/);
  assert.match(panel, /data-testid="jd-item-remove-cancel"/);
});

test("onRemoveItem is not called without the confirm step", () => {
  // onRequestRemove only sets confirmItemId; onRemoveItem is called in handleConfirmRemove only
  assert.match(panel, /function handleRequestRemove\(itemId: string\) \{[\s\S]{0,60}setConfirmItemId\(itemId\)/);
  assert.match(panel, /function handleConfirmRemove\(itemId: string\) \{[\s\S]{0,80}onRemoveItem\?\.\(itemId\)/);
});

test("ExpandedDayPanel never imports or calls deleteItem directly", () => {
  assert.doesNotMatch(panel, /deleteItem/);
});

test("page wires onUnplace to handleItemUnplace for ExpandedDayPanel", () => {
  assert.match(page, /onUnplace=\{handleItemUnplace\}/);
});

test("page wires onRemoveItem to handleIdeaRemove for ExpandedDayPanel", () => {
  assert.match(page, /onRemoveItem=\{handleIdeaRemove\}/);
});

test("Brief (TripBrief) stays read-only — no unplace or remove handlers", () => {
  const brief = readFileSync(
    new URL("../src/components/trips/TripBrief.tsx", import.meta.url),
    "utf8",
  );
  assert.doesNotMatch(brief, /onUnplace|onRemoveItem|deleteItem/);
});

test("IdeasTray is untouched — no unplace or remove-item wiring added", () => {
  const tray = readFileSync(
    new URL("../src/components/trips/IdeasTray.tsx", import.meta.url),
    "utf8",
  );
  // IdeasTray should not have been modified: no onUnplace prop, no jd-item-action-toggle
  assert.doesNotMatch(tray, /jd-item-action-toggle/);
  assert.doesNotMatch(tray, /jd-item-remove-confirm/);
});
