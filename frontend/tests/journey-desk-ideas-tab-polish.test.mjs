/**
 * Journey Desk — Ideas tab polish contract tests.
 *
 * Verifies that after the polish PR:
 *   1. Ideas tab (TripIdeasPanel) reads as the canonical "manage ideas" workspace:
 *      serif heading, labeled filters, status management, note editing.
 *   2. IdeasTray is placement-first only — no note editor testid, no status chips testid.
 *   3. IA contract: Brief "Review ideas" opens Ideas tab; ExpandedDayPanel "Add from Ideas"
 *      opens IdeasTray.
 *   4. Empty/no-results states are polished and honest (no fabricated data).
 *
 * Source-scan only — no DOM/browser in this environment.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const ideasPanel = readFileSync(
  new URL("../src/components/trips/TripIdeasPanel.tsx", import.meta.url),
  "utf8",
);
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

// ── Ideas tab workspace identity ──────────────────────────────────────────────

test("Ideas tab has a serif 'Ideas' heading — reads as a named workspace", () => {
  assert.match(ideasPanel, /font-serif[\s\S]{0,60}>Ideas<\/h2>/);
});

test("Ideas tab heading is an h2 for correct document hierarchy", () => {
  assert.match(ideasPanel, /<h2[\s\S]{0,120}>Ideas<\/h2>/);
});

test("Ideas tab has a subtitle that adapts to empty and non-empty state", () => {
  assert.match(ideasPanel, /Save ideas from AI Concierge or Explore/);
  assert.match(ideasPanel, /Set priority.*add notes.*schedule to a day/);
});

test("Ideas tab workspace header applies the jd-ideas-workspace-header class", () => {
  assert.match(ideasPanel, /jd-ideas-workspace-header/);
});

test("jd-ideas-workspace-header is defined in globals.css with a hairline bottom border", () => {
  assert.match(css, /\.jd-ideas-workspace-header \{[\s\S]{0,120}border-bottom/);
});

// ── Status management (Must-do/Maybe/Skip) ────────────────────────────────────

test("Ideas tab has a 'Priority' label above status chips", () => {
  assert.match(ideasPanel, /Priority/);
});

test("Ideas tab status chip row has data-testid='ideas-tab-status-chips'", () => {
  assert.match(ideasPanel, /data-testid="ideas-tab-status-chips"/);
});

test("Ideas tab status chips use aria-pressed for active state", () => {
  assert.match(ideasPanel, /aria-pressed=\{status === opt\.value\}/);
});

test("IdeasTray does NOT have ideas-tab-status-chips testid (management stays in Ideas tab)", () => {
  assert.doesNotMatch(tray, /data-testid="ideas-tab-status-chips"/);
});

// ── Note editing ──────────────────────────────────────────────────────────────

test("Ideas tab note textarea has data-testid='ideas-tab-note-textarea'", () => {
  assert.match(ideasPanel, /data-testid="ideas-tab-note-textarea"/);
});

test("Ideas tab note toggle uses Pencil icon (no emoji)", () => {
  assert.match(ideasPanel, /Pencil/);
  assert.doesNotMatch(ideasPanel, /✎/);
});

test("Ideas tab note toggle offers 'Edit note' when note exists, 'Add note' when absent", () => {
  assert.match(ideasPanel, /note \? "Edit note" : "Add note"/);
});

test("Ideas tab note placeholder says 'Add a private note' (private = margin note tone)", () => {
  assert.match(ideasPanel, /Add a private note/);
});

test("IdeasTray does NOT have ideas-tab-note-textarea testid (editing stays in Ideas tab)", () => {
  assert.doesNotMatch(tray, /data-testid="ideas-tab-note-textarea"/);
});

// ── Search / filter / sort controls ──────────────────────────────────────────

test("Ideas tab filter chips have 'Show' label for clarity", () => {
  assert.match(ideasPanel, /Show/);
});

test("Ideas tab filter chips are direct single-element buttons (no nested span wrapper)", () => {
  // The old pattern was button > span. New pattern is button directly styled.
  // Verify the filter button class contains 'inline-flex' and 'rounded-full' on the button.
  assert.match(ideasPanel, /setStatusFilter\(opt\.value\)[\s\S]{0,400}inline-flex items-center rounded-full border/);
});

test("Ideas tab sort dropdown still has aria-label for accessibility", () => {
  assert.match(ideasPanel, /aria-label="Sort ideas"/);
});

test("Ideas tab has a Reset button for clearing active filters", () => {
  assert.match(ideasPanel, /onClick=\{handleReset\}/);
  assert.match(ideasPanel, /Reset/);
});

// ── Empty and no-results states ───────────────────────────────────────────────

test("No-ideas empty state has 'No ideas yet' heading", () => {
  assert.match(ideasPanel, /No ideas yet/);
});

test("No-ideas empty state copy mentions AI Concierge and Explore (real sources)", () => {
  assert.match(ideasPanel, /AI Concierge or Explore/);
});

test("No-ideas empty state uses the Bookmark icon", () => {
  // Both Bookmark (import) and 'No ideas yet' (empty state copy) must be present
  assert.match(ideasPanel, /Bookmark/);
  assert.match(ideasPanel, /No ideas yet/);
  // The empty state is inside the ideas.length === 0 branch
  assert.match(ideasPanel, /ideas\.length === 0 \? \([\s\S]{0,400}Bookmark[\s\S]{0,400}No ideas yet/);
});

test("No-results empty state has 'No matching ideas' heading", () => {
  assert.match(ideasPanel, /No matching ideas/);
});

test("No-results empty state has its own Reset filters button", () => {
  assert.match(ideasPanel, /Reset filters/);
});

test("Loading state has italic editorial copy (not a bare spinner)", () => {
  assert.match(ideasPanel, /Preparing your ideas/);
});

test("Ideas tab empty states fabricate no prices, weather, or ratings", () => {
  // Empty state sections must not invent data
  const noIdeasSection = ideasPanel.slice(
    ideasPanel.indexOf("No ideas yet"),
    ideasPanel.indexOf("No ideas yet") + 500,
  );
  assert.doesNotMatch(noIdeasSection, /\$\d|weather|°|★|\d+\.\d+\s*stars/i);
});

// ── IA contract: Brief → Ideas tab; ExpandedDayPanel → IdeasTray ─────────────

test("Brief 'Review ideas' routes to the Ideas tab workspace (not the placement tray)", () => {
  assert.match(page, /onReview=\{\(\) => setActiveMobileWorkspace\("ideas"\)\}/);
});

test("Brief 'Review ideas' does NOT open IdeasTray directly", () => {
  assert.doesNotMatch(page, /onReview=\{\(\) => setIdeasTrayOpen\(true\)\}/);
});

test("ExpandedDayPanel 'Add from Ideas' opens IdeasTray for quick day-specific placement", () => {
  assert.match(page, /onAddFromIdeas=\{\(\) => setIdeasTrayOpen\(true\)\}/);
});

// ── CSS primitive ─────────────────────────────────────────────────────────────

test("globals.css defines jd-ideas-workspace-header under @layer components", () => {
  const layerIdx = css.indexOf("@layer components");
  const classIdx = css.indexOf(".jd-ideas-workspace-header", layerIdx);
  assert.ok(classIdx !== -1, ".jd-ideas-workspace-header must be defined in globals.css");
});
