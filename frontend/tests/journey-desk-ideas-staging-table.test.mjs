/**
 * Journey Desk — Ideas tab staging-table polish contract tests.
 *
 * Verifies the visual hierarchy improvements made in the Ideas tab polish PR:
 *   1. Idea cards carry a type-specific left accent border (.jd-idea-card + modifier).
 *   2. The placement zone (.jd-idea-place-zone) is distinct from the card content.
 *   3. Note preview (.jd-idea-note-preview) displays when note is set and editor is closed.
 *   4. The "Add to Day" CTA uses marine-ink primary styling.
 *   5. Group headers have a top separator for non-first groups.
 *   6. New CSS primitives are defined in globals.css.
 *   7. All existing behavior (testids, aria, handlers) is preserved.
 *
 * Source-scan only — no DOM/browser.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const ideasPanel = readFileSync(
  new URL("../src/components/trips/TripIdeasPanel.tsx", import.meta.url),
  "utf8",
);
const css = readFileSync(
  new URL("../src/app/globals.css", import.meta.url),
  "utf8",
);

// ── Left accent border CSS primitives ─────────────────────────────────────────

test("globals.css defines .jd-idea-card with border-left-width", () => {
  assert.match(css, /\.jd-idea-card \{[^}]*border-left-width/);
});

test("globals.css defines .jd-idea-card--activity with marine-ink left border", () => {
  assert.match(css, /\.jd-idea-card--activity \{[^}]*var\(--ds-marine-ink\)/);
});

test("globals.css defines .jd-idea-card--meal with ember-brass left border", () => {
  assert.match(css, /\.jd-idea-card--meal\s*\{[^}]*var\(--ds-ember-brass\)/);
});

test("globals.css defines .jd-idea-card--hotel with verified-sage left border", () => {
  assert.match(css, /\.jd-idea-card--hotel\s*\{[^}]*var\(--ds-verified-sage\)/);
});

test("globals.css defines .jd-idea-card--flight with caution-amber left border", () => {
  assert.match(css, /\.jd-idea-card--flight\s*\{[^}]*caution-amber/);
});

// ── Left accent border applied in JSX ─────────────────────────────────────────

test("IdeaCard applies jd-idea-card class to the card element", () => {
  assert.match(ideasPanel, /jd-idea-card/);
});

test("IdeaCard applies a type-specific jd-idea-card--{itemType} modifier", () => {
  assert.match(ideasPanel, /jd-idea-card--\$\{item\.itemType\}/);
});

// ── Placement zone CSS primitive ──────────────────────────────────────────────

test("globals.css defines .jd-idea-place-zone with linen background", () => {
  assert.match(css, /\.jd-idea-place-zone \{[\s\S]{0,200}var\(--ds-linen\)/);
});

test("globals.css defines .jd-idea-place-zone with a top border", () => {
  assert.match(css, /\.jd-idea-place-zone \{[\s\S]{0,200}border-top/);
});

test("globals.css .jd-idea-place-zone uses negative margins to extend to card edges", () => {
  assert.match(css, /\.jd-idea-place-zone \{[\s\S]{0,100}margin:[\s\S]{0,60}-12px/);
});

test("IdeaCard wraps the day select + Add to Day in jd-idea-place-zone", () => {
  assert.match(ideasPanel, /jd-idea-place-zone/);
});

// ── Note preview CSS primitive and JSX ────────────────────────────────────────

test("globals.css defines .jd-idea-note-preview with italic style", () => {
  assert.match(css, /\.jd-idea-note-preview \{[\s\S]{0,500}font-style:\s*italic/);
});

test("globals.css .jd-idea-note-preview has a brass left hairline", () => {
  assert.match(css, /\.jd-idea-note-preview \{[\s\S]{0,300}border-left/);
});

test("IdeaCard renders jd-idea-note-preview when note is set and editor is closed", () => {
  assert.match(ideasPanel, /jd-idea-note-preview/);
  assert.match(ideasPanel, /!noteOpen && note/);
});

// ── Marine-ink primary Add to Day button ─────────────────────────────────────

test("IdeaCard Add to Day button uses bg-ds-marine-ink primary fill", () => {
  assert.match(ideasPanel, /bg-ds-marine-ink[\s\S]{0,300}Add to Day/);
});

test("IdeaCard Add to Day button uses text-ds-paper for contrast on marine bg", () => {
  assert.match(ideasPanel, /bg-ds-marine-ink[\s\S]{0,60}text-ds-paper/);
});

// ── Group header separator ────────────────────────────────────────────────────

test("Group headers receive a top border separator for non-first groups via groupIdx", () => {
  assert.match(ideasPanel, /groupIdx/);
  assert.match(ideasPanel, /groupIdx > 0/);
});

test("Group header top separator uses border-ds-hairline token", () => {
  assert.match(ideasPanel, /groupIdx > 0[\s\S]{0,80}border-ds-hairline/);
});

// ── Preserved behavior invariants ─────────────────────────────────────────────

test("ideas-tab-status-chips testid is preserved", () => {
  assert.match(ideasPanel, /data-testid="ideas-tab-status-chips"/);
});

test("ideas-tab-note-textarea testid is preserved", () => {
  assert.match(ideasPanel, /data-testid="ideas-tab-note-textarea"/);
});

test("trip-idea-card testid is preserved", () => {
  assert.match(ideasPanel, /data-testid="trip-idea-card"/);
});

test("trip-ideas-panel-root testid is preserved", () => {
  assert.match(ideasPanel, /data-testid="trip-ideas-panel-root"/);
});

test("aria-pressed is still used for priority chips", () => {
  assert.match(ideasPanel, /aria-pressed=\{status === opt\.value\}/);
});

test("note toggle still shows 'Edit note' when note exists, 'Add note' when not", () => {
  assert.match(ideasPanel, /note \? "Edit note" : "Add note"/);
});

test("Pencil icon still used for note toggle", () => {
  assert.match(ideasPanel, /Pencil/);
});
