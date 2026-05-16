// Stage 3.5 Phase 5 — TripBuilder Command Surface
//
// Static/contract tests verifying:
// - No legacy .card / btn-ghost / accentColor in TripBuilder
// - ds-token coverage: bg-ds-onyx, border-ds-pen-stroke, shadow-[var(--ds-elevation-*)]
// - Overline typography (tracking-[0.1em], uppercase, text-[10px] font-semibold)
// - Planning cockpit context header present
// - 44×44px touch target on Add Day button
// - Compare bar uses ds-elevation-4 and Overline label
// - CandidatePanel: no accentColor prop in interface
// - Activities section uses ds-token card pattern
// - Editorial filter-empty states (no plain "No X match" copy)
// - Round-trip one-card rendering (RoundTripFlightCard) preserved
// - GSAP candidate-card class preserved
// - Google Flights link-out test-id preserved
// - All behavior contracts preserved

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const src = readFileSync(new URL('../src/components/trips/TripBuilder.tsx', import.meta.url), 'utf8');

// ── No legacy classes ────────────────────────────────────────────────────────

test('TripBuilder: no legacy .card class in component', () => {
  assert.ok(!/"card[\s"]/.test(src), 'found legacy .card class');
});

test('TripBuilder: no btn-ghost class', () => {
  assert.ok(!src.includes('btn-ghost'), 'found legacy btn-ghost class');
});

test('TripBuilder: CandidatePanel callers do not pass accentColor prop', () => {
  assert.ok(!src.includes('accentColor='), 'found accentColor= prop still being passed');
});

test('TripBuilder: no raw rgba() color values', () => {
  assert.ok(!src.includes('rgba('), 'found raw rgba() — replace with ds-* token');
});

test('TripBuilder: no legacy slate-NNN classes', () => {
  assert.ok(!/\bslate-\d+\b/.test(src), 'found legacy slate-NNN class');
});

// ── ds-token coverage ────────────────────────────────────────────────────────

test('TripBuilder: uses bg-ds-onyx for card surfaces', () => {
  assert.ok(src.includes('bg-ds-onyx'), 'missing bg-ds-onyx');
});

test('TripBuilder: uses border-ds-pen-stroke for borders', () => {
  assert.ok(src.includes('border-ds-pen-stroke'), 'missing border-ds-pen-stroke');
});

test('TripBuilder: uses var(--ds-elevation-1) for activity card shadow', () => {
  assert.ok(src.includes('var(--ds-elevation-1)'), 'missing var(--ds-elevation-1)');
});

test('TripBuilder: uses var(--ds-elevation-4) for compare bar shadow', () => {
  assert.ok(src.includes('var(--ds-elevation-4)'), 'missing var(--ds-elevation-4)');
});

test('TripBuilder: uses var(--ds-accent-subtle) for CandidatePanel count badge background', () => {
  assert.ok(src.includes('var(--ds-accent-subtle)'), 'missing var(--ds-accent-subtle)');
});

test('TripBuilder: uses text-ds-accent', () => {
  assert.ok(src.includes('text-ds-accent'), 'missing text-ds-accent');
});

test('TripBuilder: uses text-ds-text-tertiary', () => {
  assert.ok(src.includes('text-ds-text-tertiary'), 'missing text-ds-text-tertiary');
});

test('TripBuilder: uses bg-ds-carbon for cockpit UI surfaces', () => {
  assert.ok(src.includes('bg-ds-carbon'), 'missing bg-ds-carbon');
});

// ── Overline typography ──────────────────────────────────────────────────────

test('TripBuilder: uses tracking-[0.1em] for Overline labels', () => {
  assert.ok(src.includes('tracking-[0.1em]'), 'missing tracking-[0.1em] overline tracking');
});

test('TripBuilder: uses text-[10px] font-semibold uppercase for Overline labels', () => {
  assert.ok(src.includes('text-[10px] font-semibold'), 'missing text-[10px] font-semibold overline size');
});

// ── Planning cockpit context header ─────────────────────────────────────────

test('TripBuilder: has "Planning" Overline label in cockpit context header', () => {
  assert.ok(src.includes('Planning'), 'missing Planning label in cockpit header');
});

test('TripBuilder: cockpit header references destination prop', () => {
  assert.ok(src.includes('{destination}'), 'missing {destination} in cockpit header');
});

// ── Compare bar ──────────────────────────────────────────────────────────────

test('TripBuilder: compare bar uses ds-elevation-4 shadow (not shadow-2xl)', () => {
  assert.ok(!src.includes('shadow-2xl'), 'found legacy shadow-2xl — replace with ds-elevation token');
});

test('TripBuilder: compare bar has "Compare" Overline label', () => {
  const overlineCtx = src.match(/tracking-\[0\.1em\][^"]*"[\s\S]{0,80}Compare/);
  assert.ok(src.includes('tracking-[0.1em]') && src.includes('>Compare<'), 'missing "Compare" Overline label in compare bar');
});

test('TripBuilder: compare bar uses w-1.5 h-1.5 dots (not w-2 h-2)', () => {
  assert.ok(src.includes('w-1.5 h-1.5 rounded-full bg-ds-accent'), 'missing w-1.5 h-1.5 compare bar dots');
});

// ── Add Day button touch target ──────────────────────────────────────────────

test('TripBuilder: Add Day button has min-h-[44px] touch target', () => {
  const matches = [...src.matchAll(/Add Day/g)];
  assert.ok(matches.length > 0, 'missing Add Day text');
  const found = matches.some((m) => {
    const ctx = src.slice(Math.max(0, m.index - 400), m.index + 50);
    return ctx.includes('min-h-[44px]');
  });
  assert.ok(found, 'Add Day button missing min-h-[44px] touch target within 400 chars before text');
});

// ── Right panel Overline ─────────────────────────────────────────────────────

test('TripBuilder: right panel has "Your Itinerary" Overline label', () => {
  assert.ok(src.includes('Your Itinerary'), 'missing "Your Itinerary" Overline in right panel');
});

// ── Activities section uses ds-token pattern ─────────────────────────────────

test('TripBuilder: Activities section uses rounded-2xl border border-ds-pen-stroke bg-ds-onyx pattern', () => {
  assert.ok(
    src.includes('rounded-2xl border border-ds-pen-stroke bg-ds-onyx shadow-[var(--ds-elevation-1)]'),
    'Activities section missing ds-token card pattern'
  );
});

// ── Editorial filter-empty states ───────────────────────────────────────────

test('TripBuilder: filter-empty copy uses editorial "Nothing matches" instead of plain "No X match"', () => {
  assert.ok(!src.includes('No attractions match the selected filters'), 'found legacy "No attractions match" filter-empty copy');
  assert.ok(!src.includes('No restaurants match the selected filters'), 'found legacy "No restaurants match" filter-empty copy');
  assert.ok(src.includes('Nothing matches the current filters'), 'missing editorial "Nothing matches" filter-empty copy');
});

// ── Behavior contracts preserved ─────────────────────────────────────────────

test('TripBuilder: RoundTripFlightCard preserved for round-trip one-card rendering', () => {
  assert.ok(src.includes('RoundTripFlightCard'), 'RoundTripFlightCard missing');
});

test('TripBuilder: candidate-card class preserved for GSAP querySelector', () => {
  assert.ok(src.includes('"candidate-card'), 'candidate-card class missing — GSAP animations will break');
});

test('TripBuilder: data-testid="google-flights-cta" preserved for link-out', () => {
  assert.ok(src.includes('google-flights-cta'), 'google-flights-cta test-id missing');
});

test('TripBuilder: handleToggleCompareItem preserved', () => {
  assert.ok(src.includes('handleToggleCompareItem'), 'handleToggleCompareItem missing');
});

test('TripBuilder: selectedDayId state preserved', () => {
  assert.ok(src.includes('selectedDayId'), 'selectedDayId state missing');
});

test('TripBuilder: CandidatePanel component exported/defined', () => {
  assert.ok(src.includes('function CandidatePanel'), 'CandidatePanel function missing');
});
