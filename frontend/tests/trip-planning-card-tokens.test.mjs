/**
 * Stage 3.5 Phase 3 — Trip Planning Card Token Coverage
 *
 * Verifies that trip-planning card surfaces use ds-* design tokens
 * and have removed legacy cream/brand/dark/sky/violet/emerald/rose color classes.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const tripBuilderSrc = readFileSync(
  new URL('../src/components/trips/TripBuilder.tsx', import.meta.url),
  'utf8',
);

const itineraryCardSrc = readFileSync(
  new URL('../src/components/trips/ItineraryItemCard.tsx', import.meta.url),
  'utf8',
);

const searchResultCardSrc = readFileSync(
  new URL('../src/components/trips/SearchResultCard.tsx', import.meta.url),
  'utf8',
);

const tripIdeasPanelSrc = readFileSync(
  new URL('../src/components/trips/TripIdeasPanel.tsx', import.meta.url),
  'utf8',
);

const flightExploreSrc = readFileSync(
  new URL('../src/components/explore/FlightExploreFlow.tsx', import.meta.url),
  'utf8',
);

// ── TripBuilder.tsx ────────────────────────────────────────────────────────────

test('TripBuilder: no legacy cream color classes in JSX', () => {
  // Strip JS comments before checking
  const src = tripBuilderSrc.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*/g, '');
  assert.ok(!src.includes('text-cream-'), 'found text-cream- in TripBuilder');
  assert.ok(!src.includes('bg-cream-'), 'found bg-cream- in TripBuilder');
});

test('TripBuilder: no legacy brand color classes in JSX', () => {
  const src = tripBuilderSrc.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*/g, '');
  // bg-brand-* and text-brand-* should be replaced with ds-accent
  assert.ok(!src.includes('bg-brand-'), 'found bg-brand- in TripBuilder');
  assert.ok(!src.includes('text-brand-'), 'found text-brand- in TripBuilder');
  assert.ok(!src.includes('border-brand-'), 'found border-brand- in TripBuilder');
});

test('TripBuilder: no legacy dark color classes in JSX', () => {
  const src = tripBuilderSrc.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*/g, '');
  assert.ok(!src.includes('bg-dark-'), 'found bg-dark- in TripBuilder');
  assert.ok(!src.includes('text-dark-'), 'found text-dark- in TripBuilder');
});

test('TripBuilder: candidate card uses ds-* tokens', () => {
  assert.ok(tripBuilderSrc.includes('bg-ds-onyx'), 'PREMIUM_CARD_BASE uses bg-ds-onyx');
  assert.ok(tripBuilderSrc.includes('border-ds-pen-stroke'), 'PREMIUM_CARD_BASE uses border-ds-pen-stroke');
  assert.ok(tripBuilderSrc.includes('bg-ds-accent'), 'PRIMARY_CTA uses bg-ds-accent');
  assert.ok(tripBuilderSrc.includes('text-ds-text-inverse'), 'PRIMARY_CTA uses text-ds-text-inverse');
  assert.ok(tripBuilderSrc.includes('bg-ds-carbon'), 'SECONDARY_CTA uses bg-ds-carbon');
});

test('TripBuilder: AiScoreBadge uses ds-trust-verified and ds-caution', () => {
  assert.ok(tripBuilderSrc.includes('text-ds-trust-verified'), 'AiScoreBadge uses ds-trust-verified');
  assert.ok(tripBuilderSrc.includes('text-ds-caution'), 'AiScoreBadge uses ds-caution for medium scores');
  assert.ok(tripBuilderSrc.includes('ring-ds-trust-verified/45'), 'AiScoreBadge ring uses ds-trust-verified');
});

test('TripBuilder: RecTag uses ds-accent with inline accent-subtle', () => {
  assert.ok(tripBuilderSrc.includes("text-ds-accent border border-ds-pen-stroke"), 'RecTag uses ds-accent');
  assert.ok(tripBuilderSrc.includes("var(--ds-accent-subtle)"), 'RecTag uses ds-accent-subtle inline style');
});

test('TripBuilder: "Best Pick"/"Best Pair"/"Top Hotel"/"Top Pick" badges use ds-accent', () => {
  assert.ok(tripBuilderSrc.includes('bg-ds-accent text-ds-text-inverse'), 'top badge uses ds-accent');
});

test('TripBuilder: FlightLegRow route connector uses bg-ds-pen-stroke', () => {
  // Should no longer use bg-white/20
  assert.ok(!tripBuilderSrc.includes('bg-white/20'), 'FlightLegRow no longer uses bg-white/20');
  assert.ok(tripBuilderSrc.includes('bg-ds-pen-stroke'), 'FlightLegRow uses bg-ds-pen-stroke for route line');
});

test('TripBuilder: RoundTrip leg containers use ds-carbon', () => {
  assert.ok(tripBuilderSrc.includes('bg-ds-carbon border border-ds-pen-stroke'), 'RT leg container uses ds-carbon');
});

test('TripBuilder: HotelCandidateCard location badges use ds-trust-verified', () => {
  assert.ok(tripBuilderSrc.includes('text-ds-trust-verified'), 'hotel proximity badge uses trust-verified');
});

test('TripBuilder: SortControl active state uses bg-ds-accent', () => {
  assert.ok(tripBuilderSrc.includes('"bg-ds-accent text-ds-text-inverse border-ds-accent shadow-sm"'),
    'SortControl active uses bg-ds-accent');
});

test('TripBuilder: FilterPills active state uses bg-ds-accent', () => {
  assert.ok(tripBuilderSrc.includes('"bg-ds-accent text-ds-text-inverse border-ds-accent"'),
    'FilterPills active uses bg-ds-accent');
});

test('TripBuilder: compare bar uses ds-* tokens', () => {
  assert.ok(tripBuilderSrc.includes('bg-ds-onyx border border-ds-pen-stroke'), 'compare bar uses bg-ds-onyx');
  assert.ok(!tripBuilderSrc.includes('bg-slate-900'), 'compare bar no longer uses bg-slate-900');
});

test('TripBuilder: candidate-card class preserved for GSAP targeting', () => {
  assert.ok(tripBuilderSrc.includes('"candidate-card'), 'PREMIUM_CARD_BASE still includes candidate-card');
});

// ── ItineraryItemCard.tsx ──────────────────────────────────────────────────────

test('ItineraryItemCard: no legacy color classes', () => {
  const src = itineraryCardSrc.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*/g, '');
  assert.ok(!src.includes('text-cream-'), 'no text-cream- in ItineraryItemCard');
  assert.ok(!src.includes('text-slate-'), 'no text-slate- in ItineraryItemCard');
  assert.ok(!src.includes('bg-slate-'), 'no bg-slate- in ItineraryItemCard');
  assert.ok(!src.includes('text-amber-'), 'no text-amber- in ItineraryItemCard');
  assert.ok(!src.includes('text-sky-'), 'no text-sky- in ItineraryItemCard');
});

test('ItineraryItemCard: uses ds-* tokens for typography and borders', () => {
  assert.ok(itineraryCardSrc.includes('text-ds-text'), 'uses text-ds-text');
  assert.ok(itineraryCardSrc.includes('text-ds-text-tertiary'), 'uses text-ds-text-tertiary');
  assert.ok(itineraryCardSrc.includes('border-ds-pen-stroke'), 'uses border-ds-pen-stroke');
  assert.ok(itineraryCardSrc.includes('bg-ds-onyx'), 'uses bg-ds-onyx');
});

test('ItineraryItemCard: focus rings use ds-accent', () => {
  assert.ok(itineraryCardSrc.includes('focus-visible:outline-ds-accent'), 'focus ring uses ds-accent');
});

// ── SearchResultCard.tsx ────────────────────────────────────────────────────────

test('SearchResultCard: uses Card primitive with tone="dark"', () => {
  assert.ok(searchResultCardSrc.includes('tone="dark"'), 'SearchResultCard uses Card tone="dark"');
  assert.ok(searchResultCardSrc.includes('Card.Identity'), 'SearchResultCard uses Card.Identity slot');
  assert.ok(searchResultCardSrc.includes('Card.Meta'), 'SearchResultCard uses Card.Meta slot');
});

test('SearchResultCard: category icon uses ds-accent', () => {
  assert.ok(searchResultCardSrc.includes('text-ds-accent'), 'category icon uses text-ds-accent');
  assert.ok(searchResultCardSrc.includes("var(--ds-accent-subtle)"), 'uses ds-accent-subtle inline style');
});

test('SearchResultCard: add button uses bg-ds-accent', () => {
  assert.ok(searchResultCardSrc.includes('bg-ds-accent'), 'add button uses bg-ds-accent');
  assert.ok(searchResultCardSrc.includes('text-ds-text-inverse'), 'add button uses text-ds-text-inverse');
});

// ── TripIdeasPanel.tsx ─────────────────────────────────────────────────────────

test('TripIdeasPanel: no legacy color classes', () => {
  const src = tripIdeasPanelSrc.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*/g, '');
  assert.ok(!src.includes('text-cream-'), 'no text-cream- in TripIdeasPanel');
  assert.ok(!src.includes('bg-amber-'), 'no bg-amber- in TripIdeasPanel');
  assert.ok(!src.includes('text-emerald-'), 'no text-emerald- in TripIdeasPanel');
});

test('TripIdeasPanel: uses ds-* tokens', () => {
  assert.ok(tripIdeasPanelSrc.includes('text-ds-accent'), 'TripIdeasPanel uses text-ds-accent');
  assert.ok(tripIdeasPanelSrc.includes('bg-ds-onyx'), 'TripIdeasPanel uses bg-ds-onyx');
  assert.ok(tripIdeasPanelSrc.includes('border-ds-pen-stroke'), 'TripIdeasPanel uses border-ds-pen-stroke');
});

// ── FlightExploreFlow.tsx ──────────────────────────────────────────────────────

test('FlightExploreFlow: FlightCard uses Card primitive', () => {
  assert.ok(flightExploreSrc.includes('tone="dark"'), 'FlightCard uses Card with tone="dark"');
  assert.ok(flightExploreSrc.includes('Card.Identity'), 'FlightCard uses Card.Identity slot');
});

test('FlightExploreFlow: no legacy cream/dark/brand colors', () => {
  const src = flightExploreSrc.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*/g, '');
  assert.ok(!src.includes('text-cream-'), 'no text-cream- in FlightExploreFlow');
  assert.ok(!src.includes('bg-dark-'), 'no bg-dark- in FlightExploreFlow');
  assert.ok(!src.includes('text-brand-'), 'no text-brand- in FlightExploreFlow');
});
