// Stage 3.5 Phase 4 — Trip Detail Planning Canvas / Itinerary Day System
//
// Static/contract tests verifying:
// - ds-token coverage in ItineraryDayColumn (no legacy slate/amber/sky/violet)
// - 44x44px touch targets on all interactive controls
// - ds-accent focus rings on all interactive elements
// - Chapter-style Overline typography (tracking, uppercase)
// - Editorial empty-day invitation state (no plain "No plans yet for Day N")
// - Selected-day chapter heading uses ds-accent
// - All behavior contracts preserved (DnD, timeline, ideas, flight link-out)
// - Trip detail page shell uses ds-tokens (no legacy brand, cream, slate classes)
// - TripBuilder no-days state uses ds-tokens (no legacy .card class)

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const dayColumnSrc  = readFileSync(new URL('../src/components/trips/ItineraryDayColumn.tsx', import.meta.url), 'utf8');
const tripDetailSrc = readFileSync(new URL('../src/app/trips/[id]/page.tsx', import.meta.url), 'utf8');
const tripBuilderSrc = readFileSync(new URL('../src/components/trips/TripBuilder.tsx', import.meta.url), 'utf8');

// ── ItineraryDayColumn: no legacy color classes ────────────────────────────────

test('ItineraryDayColumn: no legacy slate-NNN classes', () => {
  assert.ok(!/\bslate-\d+\b/.test(dayColumnSrc), 'found legacy slate-NNN class');
});

test('ItineraryDayColumn: no legacy amber-NNN classes', () => {
  assert.ok(!/\bamber-\d+\b/.test(dayColumnSrc), 'found legacy amber-NNN class');
});

test('ItineraryDayColumn: no legacy sky-NNN classes', () => {
  assert.ok(!/\bsky-\d+\b/.test(dayColumnSrc), 'found legacy sky-NNN class');
});

test('ItineraryDayColumn: no legacy violet-NNN classes', () => {
  assert.ok(!/\bviolet-\d+\b/.test(dayColumnSrc), 'found legacy violet-NNN class');
});

// ── ItineraryDayColumn: ds-token presence ─────────────────────────────────────

test('ItineraryDayColumn: uses text-ds-accent for morning day-part color', () => {
  assert.ok(dayColumnSrc.includes('text-ds-accent'), 'missing text-ds-accent');
});

test('ItineraryDayColumn: uses text-ds-accent-muted for evening day-part color', () => {
  assert.ok(dayColumnSrc.includes('text-ds-accent-muted'), 'missing text-ds-accent-muted');
});

test('ItineraryDayColumn: uses text-ds-text-secondary for afternoon day-part color', () => {
  assert.ok(dayColumnSrc.includes('text-ds-text-secondary'), 'missing text-ds-text-secondary');
});

test('ItineraryDayColumn: uses text-ds-text-tertiary for unscheduled and muted labels', () => {
  assert.ok(dayColumnSrc.includes('text-ds-text-tertiary'), 'missing text-ds-text-tertiary');
});

test('ItineraryDayColumn: uses border-ds-pen-stroke for all borders', () => {
  assert.ok(dayColumnSrc.includes('border-ds-pen-stroke'), 'missing border-ds-pen-stroke');
});

test('ItineraryDayColumn: uses bg-ds-carbon for secondary dark surface', () => {
  assert.ok(dayColumnSrc.includes('bg-ds-carbon'), 'missing bg-ds-carbon');
});

test('ItineraryDayColumn: uses bg-ds-onyx for card root surface', () => {
  assert.ok(dayColumnSrc.includes('bg-ds-onyx'), 'missing bg-ds-onyx');
});

test('ItineraryDayColumn: uses ds-midnight-ink inline style for expanded body (ink-ladder depth)', () => {
  assert.ok(dayColumnSrc.includes('var(--ds-midnight-ink)'), 'missing var(--ds-midnight-ink) inline style');
});

test('ItineraryDayColumn: uses ds-accent-subtle inline style for drag-over tint', () => {
  assert.ok(dayColumnSrc.includes('var(--ds-accent-subtle)'), 'missing var(--ds-accent-subtle) inline style');
});

test('ItineraryDayColumn: uses ds-elevation-2 shadow token for card depth', () => {
  assert.ok(dayColumnSrc.includes('ds-elevation-2'), 'missing ds-elevation-2 shadow token');
});

test('ItineraryDayColumn: uses text-ds-warning for far-apart travel hints', () => {
  assert.ok(dayColumnSrc.includes('text-ds-warning'), 'missing text-ds-warning for far-apart hints');
});

test('ItineraryDayColumn: uses to-ds-midnight for show-more gradient fade', () => {
  assert.ok(dayColumnSrc.includes('to-ds-midnight'), 'missing to-ds-midnight gradient fade');
});

// ── ItineraryDayColumn: 44×44px touch targets ─────────────────────────────────

test('ItineraryDayColumn: applies min-h-[44px] to interactive controls', () => {
  assert.ok(dayColumnSrc.includes('min-h-[44px]'), 'missing min-h-[44px] touch target');
});

test('ItineraryDayColumn: applies min-w-[44px] to icon-only header buttons', () => {
  assert.ok(dayColumnSrc.includes('min-w-[44px]'), 'missing min-w-[44px] touch target');
});

// ── ItineraryDayColumn: focus ring (ds-accent, 2px, offset-2) ─────────────────

test('ItineraryDayColumn: uses focus-visible:outline-ds-accent on interactive elements', () => {
  assert.ok(dayColumnSrc.includes('focus-visible:outline-ds-accent'), 'missing focus-visible:outline-ds-accent');
});

test('ItineraryDayColumn: uses focus-visible:outline-2 on interactive elements', () => {
  assert.ok(dayColumnSrc.includes('focus-visible:outline-2'), 'missing focus-visible:outline-2');
});

test('ItineraryDayColumn: uses focus-visible:outline-offset-2 on interactive elements', () => {
  assert.ok(dayColumnSrc.includes('focus-visible:outline-offset-2'), 'missing focus-visible:outline-offset-2');
});

// ── ItineraryDayColumn: chapter-style Overline typography ────────────────────

test('ItineraryDayColumn: uses tracking-[0.1em] for Overline section labels', () => {
  assert.ok(dayColumnSrc.includes('tracking-[0.1em]'), 'missing tracking-[0.1em] overline tracking');
});

test('ItineraryDayColumn: zero-pads chapter number via padStart(2)', () => {
  assert.ok(dayColumnSrc.includes('padStart(2'), 'missing padStart(2) for chapter number');
});

// ── ItineraryDayColumn: editorial empty-day invitation ───────────────────────

test('ItineraryDayColumn: no plain "No plans yet for Day N" text (replaced by editorial invitation)', () => {
  assert.ok(!dayColumnSrc.includes('No plans yet for Day'), 'legacy "No plans yet for Day N" text found');
});

test('ItineraryDayColumn: empty-state uses border-dashed drop zone', () => {
  assert.ok(dayColumnSrc.includes('border-dashed'), 'missing border-dashed on empty-state drop zone');
});

test('ItineraryDayColumn: empty-state uses border-ds-pen-stroke (normal) and border-ds-accent/60 (drag-over)', () => {
  assert.ok(dayColumnSrc.includes('border-ds-pen-stroke'), 'missing border-ds-pen-stroke on empty state');
  assert.ok(dayColumnSrc.includes('border-ds-accent/60'), 'missing border-ds-accent/60 on drag-over state');
});

test('ItineraryDayColumn: empty-state includes actionable "+ Add" inline link', () => {
  assert.ok(dayColumnSrc.includes('+ Add'), 'missing "+ Add" actionable link in empty state');
});

test('ItineraryDayColumn: no raw rgba() color values (must use ds-* tokens)', () => {
  assert.ok(!dayColumnSrc.includes('rgba('), 'found raw rgba() — replace with ds-* token');
});

test('ItineraryDayColumn: empty-state "+ Add" button has 44px hit-area (min-h-[44px] on the button containing onAddItem and + Add)', () => {
  // Find the button that contains both + Add text and onAddItem call — verify min-h-[44px] is on it
  const addBtnMatch = dayColumnSrc.match(/className="([^"]*min-h-\[44px\][^"]*)"[\s\S]{0,200}?\+\s*Add|className="([^"]*)"[\s\S]{0,100}?onAddItem[\s\S]{0,200}?min-h-\[44px\]/);
  // Simpler: confirm the inline-flex + min-h-[44px] pattern exists near the + Add text
  const emptyStateIdx = dayColumnSrc.indexOf('+ Add');
  assert.ok(emptyStateIdx !== -1, 'missing + Add text');
  const surroundingContext = dayColumnSrc.slice(Math.max(0, emptyStateIdx - 300), emptyStateIdx + 50);
  assert.ok(
    surroundingContext.includes('min-h-[44px]'),
    'empty-state "+ Add" button lacks min-h-[44px] touch-target within 300 chars before the text'
  );
});

// ── ItineraryDayColumn: selected-day uses ds-accent ──────────────────────────

test('ItineraryDayColumn: selected day number marker uses bg-ds-accent', () => {
  assert.ok(dayColumnSrc.includes('bg-ds-accent'), 'missing bg-ds-accent on selected chapter number');
});

test('ItineraryDayColumn: selected day border uses border-ds-accent/40', () => {
  assert.ok(dayColumnSrc.includes('border-ds-accent/40'), 'missing border-ds-accent/40 on selected day');
});

test('ItineraryDayColumn: selected ring uses ring-ds-accent/20', () => {
  assert.ok(dayColumnSrc.includes('ring-ds-accent/20'), 'missing ring-ds-accent/20 on selected day');
});

// ── ItineraryDayColumn: all behavior contracts preserved ─────────────────────

test('ItineraryDayColumn: exports ItineraryDayColumn function', () => {
  assert.ok(dayColumnSrc.includes('export function ItineraryDayColumn'), 'ItineraryDayColumn export missing');
});

test('ItineraryDayColumn: onPlanDay prop preserved', () => {
  assert.ok(dayColumnSrc.includes('onPlanDay'), 'onPlanDay prop missing');
});

test('ItineraryDayColumn: onUpdateTimeline prop preserved', () => {
  assert.ok(dayColumnSrc.includes('onUpdateTimeline'), 'onUpdateTimeline prop missing');
});

test('ItineraryDayColumn: onMoveItemToIdeas prop preserved', () => {
  assert.ok(dayColumnSrc.includes('onMoveItemToIdeas'), 'onMoveItemToIdeas prop missing');
});

test('ItineraryDayColumn: useDroppable DnD context preserved', () => {
  assert.ok(dayColumnSrc.includes('useDroppable'), 'useDroppable DnD hook missing');
});

test('ItineraryDayColumn: SortableContext for item reordering preserved', () => {
  assert.ok(dayColumnSrc.includes('SortableContext'), 'SortableContext missing');
});

test('ItineraryDayColumn: handleSuggestTimeline behavior preserved', () => {
  assert.ok(dayColumnSrc.includes('handleSuggestTimeline'), 'handleSuggestTimeline missing');
});

test('ItineraryDayColumn: handleApplyTimeline behavior preserved', () => {
  assert.ok(dayColumnSrc.includes('handleApplyTimeline'), 'handleApplyTimeline missing');
});

test('ItineraryDayColumn: isExpanded expand/collapse behavior preserved', () => {
  assert.ok(dayColumnSrc.includes('isExpanded'), 'isExpanded expand/collapse logic missing');
});

test('ItineraryDayColumn: PREVIEW_ITEM_LIMIT paging constant preserved', () => {
  assert.ok(dayColumnSrc.includes('PREVIEW_ITEM_LIMIT'), 'PREVIEW_ITEM_LIMIT missing');
});

test('ItineraryDayColumn: SuggestionsReviewPanel apply/dismiss preserved', () => {
  assert.ok(dayColumnSrc.includes('SuggestionsReviewPanel'), 'SuggestionsReviewPanel missing');
});

test('ItineraryDayColumn: DayTravelHintBar travel feasibility hints preserved', () => {
  assert.ok(dayColumnSrc.includes('DayTravelHintBar'), 'DayTravelHintBar missing');
});

test('ItineraryDayColumn: optimistic itemOverrides for timeline updates preserved', () => {
  assert.ok(dayColumnSrc.includes('itemOverrides'), 'itemOverrides state missing');
});

test('ItineraryDayColumn: CalendarDays icon for date field preserved', () => {
  assert.ok(dayColumnSrc.includes('CalendarDays'), 'CalendarDays icon missing');
});

// ── Trip detail page: ds-token coverage in shell ─────────────────────────────

test('TripDetailPage: no bg-brand-* legacy classes in context header', () => {
  assert.ok(!tripDetailSrc.includes('bg-brand-'), 'found bg-brand- in trip detail page');
});

test('TripDetailPage: no border-brand-* legacy classes in context header', () => {
  assert.ok(!tripDetailSrc.includes('border-brand-'), 'found border-brand- in trip detail page');
});

test('TripDetailPage: no text-brand-* legacy classes', () => {
  assert.ok(!tripDetailSrc.includes('text-brand-'), 'found text-brand- in trip detail page');
});

test('TripDetailPage: no legacy text-cream-300 class', () => {
  assert.ok(!tripDetailSrc.includes('text-cream-300'), 'found text-cream-300 in trip detail page');
});

test('TripDetailPage: toast does not use legacy bg-slate-800 text-white pattern', () => {
  assert.ok(!tripDetailSrc.includes('bg-slate-800 text-white'), 'found bg-slate-800 text-white in toast');
});

test('TripDetailPage: uses text-ds-text-tertiary for muted elements', () => {
  assert.ok(tripDetailSrc.includes('text-ds-text-tertiary'), 'missing text-ds-text-tertiary');
});

test('TripDetailPage: uses text-ds-accent for context compass icon', () => {
  assert.ok(tripDetailSrc.includes('text-ds-accent'), 'missing text-ds-accent in trip detail page');
});

test('TripDetailPage: toast uses bg-ds-onyx', () => {
  assert.ok(tripDetailSrc.includes('bg-ds-onyx'), 'missing bg-ds-onyx in trip detail page');
});

test('TripDetailPage: toast uses border-ds-pen-stroke', () => {
  assert.ok(tripDetailSrc.includes('border-ds-pen-stroke'), 'missing border-ds-pen-stroke in trip detail page');
});

test('TripDetailPage: toast uses ds-elevation-2 shadow', () => {
  assert.ok(tripDetailSrc.includes('ds-elevation-2'), 'missing ds-elevation-2 in trip detail page');
});

test('TripDetailPage: loading state does not use legacy .card class with slate-400', () => {
  assert.ok(!tripDetailSrc.includes('"card p-8 text-center text-slate-400'), 'found legacy card class in loading state');
});

// ── TripBuilder: no-days empty state uses ds-tokens ──────────────────────────

test('TripBuilder: no-days state does not use legacy "card p-8 text-center text-ds-text-tertiary" pattern', () => {
  assert.ok(!tripBuilderSrc.includes('"card p-8 text-center text-ds-text-tertiary"'), 'found legacy .card class in no-days state');
});

test('TripBuilder: no-days state uses rounded-lg border border-ds-pen-stroke bg-ds-onyx pattern', () => {
  assert.ok(
    tripBuilderSrc.includes('rounded-lg border border-ds-pen-stroke bg-ds-onyx'),
    'missing rounded-lg border border-ds-pen-stroke bg-ds-onyx in no-days state'
  );
});
