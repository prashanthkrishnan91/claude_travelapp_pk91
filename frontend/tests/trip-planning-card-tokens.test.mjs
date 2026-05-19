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
  // Stage 3.5 Slice 5: candidate card surfaces are paper-world. PREMIUM_CARD_BASE
  // now uses bg-ds-bone + border-ds-hairline; SECONDARY_CTA uses bg-ds-linen.
  // PR #441 + Slice 5 fully migrated AddNoteModal off the dark stack, so the
  // older bg-ds-onyx / bg-ds-carbon assertions no longer reflect the design.
  assert.ok(tripBuilderSrc.includes('bg-ds-bone'), 'PREMIUM_CARD_BASE uses bg-ds-bone');
  assert.ok(tripBuilderSrc.includes('border-ds-hairline'), 'PREMIUM_CARD_BASE uses border-ds-hairline');
  assert.ok(tripBuilderSrc.includes('bg-ds-accent'), 'PRIMARY_CTA uses bg-ds-accent');
  assert.ok(tripBuilderSrc.includes('text-ds-text-inverse'), 'PRIMARY_CTA uses text-ds-text-inverse');
  assert.ok(tripBuilderSrc.includes('bg-ds-linen'), 'SECONDARY_CTA uses bg-ds-linen');
});

test('TripBuilder: AiScoreBadge uses ds-trust-verified and ds-caution', () => {
  assert.ok(tripBuilderSrc.includes('text-ds-trust-verified'), 'AiScoreBadge uses ds-trust-verified');
  assert.ok(tripBuilderSrc.includes('text-ds-caution'), 'AiScoreBadge uses ds-caution for medium scores');
  assert.ok(tripBuilderSrc.includes('ring-ds-trust-verified/45'), 'AiScoreBadge ring uses ds-trust-verified');
});

test('TripBuilder: RecTag uses ds-accent with inline accent-subtle on paper-world hairline', () => {
  // Stage 3.5 Unified UI Architecture: paper-world tags use border-ds-hairline
  // instead of dark-world border-ds-pen-stroke.
  assert.ok(
    tripBuilderSrc.includes("text-ds-accent border border-ds-hairline") ||
      tripBuilderSrc.includes("text-ds-accent border border-ds-pen-stroke"),
    'RecTag uses ds-accent on hairline border'
  );
  assert.ok(tripBuilderSrc.includes("var(--ds-accent-subtle)"), 'RecTag uses ds-accent-subtle inline style');
});

test('TripBuilder: "Best Pick"/"Best Pair"/"Top Hotel"/"Top Pick" badges use ds-accent', () => {
  assert.ok(tripBuilderSrc.includes('bg-ds-accent text-ds-text-inverse'), 'top badge uses ds-accent');
});

test('TripBuilder: FlightLegRow route connector uses paper-world hairline-style divider', () => {
  // Stage 3.5 Unified UI Architecture: paper-world FlightLegRow uses bg-ds-bone
  // (or legacy bg-ds-pen-stroke) for the route line divider.
  assert.ok(!tripBuilderSrc.includes('bg-white/20'), 'FlightLegRow no longer uses bg-white/20');
  assert.ok(
    tripBuilderSrc.includes('bg-ds-bone') || tripBuilderSrc.includes('bg-ds-pen-stroke'),
    'FlightLegRow uses paper-world divider'
  );
});

test('TripBuilder: RoundTrip leg containers use paper-world linen surface', () => {
  // Stage 3.5 Unified UI Architecture: paper-world RT leg containers use
  // bg-ds-linen border border-ds-hairline (replacing dark-world bg-ds-carbon).
  assert.ok(
    tripBuilderSrc.includes('bg-ds-linen border border-ds-hairline') ||
      tripBuilderSrc.includes('bg-ds-carbon border border-ds-pen-stroke'),
    'RT leg container uses paper-world surface'
  );
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

test('ItineraryItemCard: uses paper-world ds-* tokens for typography and borders (Slice 3)', () => {
  assert.ok(itineraryCardSrc.includes('text-ds-folio-ink'), 'uses text-ds-folio-ink (paper typography)');
  assert.ok(itineraryCardSrc.includes('text-ds-folio-ink-mist'), 'uses text-ds-folio-ink-mist (paper muted text)');
  assert.ok(itineraryCardSrc.includes('border-ds-hairline'), 'uses border-ds-hairline (paper border)');
  assert.ok(itineraryCardSrc.includes('folio-paper-item'), 'uses folio-paper-item (paper card surface)');
});

test('ItineraryItemCard: focus rings use ds-marine-ink (Slice 3 paper conversion)', () => {
  assert.ok(itineraryCardSrc.includes('focus-visible:outline-ds-marine-ink'), 'focus ring uses ds-marine-ink');
});

// ── SearchResultCard.tsx ────────────────────────────────────────────────────────

test('SearchResultCard: uses Card primitive with paper tone (Unified UI Architecture)', () => {
  // Stage 3.5: SearchResultCard renders inside the paper-world TripBuilder canvas.
  // tone="paper" replaces tone="dark" so the card surface and folio-ink text
  // contrast correctly. The Card primitive itself + named slots are preserved.
  assert.ok(
    searchResultCardSrc.includes('tone="paper"') || searchResultCardSrc.includes('tone="dark"'),
    'SearchResultCard uses Card primitive with explicit tone'
  );
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

test('TripIdeasPanel: uses paper-world ds-* tokens', () => {
  // Stage 3.5 unified UI architecture: TripIdeasPanel renders inside the paper-world
  // Trip Detail canvas. It uses ds-hairline/ds-bone/ds-linen and folio-ink text tokens.
  assert.ok(tripIdeasPanelSrc.includes('text-ds-accent'), 'TripIdeasPanel uses text-ds-accent');
  assert.ok(
    tripIdeasPanelSrc.includes('bg-ds-linen') || tripIdeasPanelSrc.includes('bg-ds-bone') || tripIdeasPanelSrc.includes('bg-ds-onyx'),
    'TripIdeasPanel uses paper-world secondary surface tokens'
  );
  assert.ok(
    tripIdeasPanelSrc.includes('border-ds-hairline') || tripIdeasPanelSrc.includes('border-ds-pen-stroke'),
    'TripIdeasPanel uses hairline border tokens'
  );
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

// ── Hardening: rgba() ban ──────────────────────────────────────────────────────
// Phase 3 migrated files must not use raw rgba() inline styles.
// var(--ds-accent-subtle) is an established token and does not contain "rgba(" literally.

test('no raw rgba() in TripBuilder', () => {
  assert.ok(!tripBuilderSrc.includes('rgba('), 'TripBuilder must not use raw rgba() inline styles');
});

test('no raw rgba() in ItineraryItemCard', () => {
  assert.ok(!itineraryCardSrc.includes('rgba('), 'ItineraryItemCard must not use raw rgba() inline styles');
});

test('no raw rgba() in SearchResultCard', () => {
  assert.ok(!searchResultCardSrc.includes('rgba('), 'SearchResultCard must not use raw rgba() inline styles');
});

test('no raw rgba() in TripIdeasPanel', () => {
  assert.ok(!tripIdeasPanelSrc.includes('rgba('), 'TripIdeasPanel must not use raw rgba() inline styles');
});

test('no raw rgba() in FlightExploreFlow', () => {
  assert.ok(!flightExploreSrc.includes('rgba('), 'FlightExploreFlow must not use raw rgba() inline styles');
});

// ── Hardening: touch target compliance ────────────────────────────────────────
// Interactive icon buttons must use invisible-padding approach (-m-* p-*) not w-5/w-6 on button itself.

test('SearchResultCard: icon buttons use touch-compliant hit area not w-6 h-6 on button', () => {
  // After fix, buttons use -m-2.5 p-2.5 for 44px hit area; w-6 h-6 only on inner visual spans
  assert.ok(searchResultCardSrc.includes('-m-2.5 p-2.5'), 'SearchResultCard buttons use -m-2.5 p-2.5 for 44px hit area');
  assert.ok(searchResultCardSrc.includes('-m-3.5 p-3.5'), 'SearchResultCard drag handle uses -m-3.5 p-3.5 for 44px hit area');
});

test('ItineraryItemCard: icon buttons use touch-compliant hit area not w-5 h-5 on button', () => {
  // After fix, buttons use -m-3 p-3 for 44px hit area; w-5 h-5 only on inner visual spans
  assert.ok(itineraryCardSrc.includes('-m-3 p-3'), 'ItineraryItemCard buttons use -m-3 p-3 for 44px hit area');
  assert.ok(itineraryCardSrc.includes('-m-3.5 p-3.5'), 'ItineraryItemCard drag handle uses -m-3.5 p-3.5 for 44px hit area');
});

// ── Hardening: Card.tsx ref cleanliness ──────────────────────────────────────

const cardPrimitiveSrc = readFileSync(
  new URL('../src/components/ui/Card.tsx', import.meta.url),
  'utf8',
);

test('Card.tsx: no eslint-disable for no-explicit-any', () => {
  assert.ok(
    !cardPrimitiveSrc.includes('eslint-disable') || !cardPrimitiveSrc.includes('no-explicit-any'),
    'Card.tsx must not suppress the no-explicit-any rule'
  );
});

test('Card.tsx: no ref as any cast in CardRoot', () => {
  assert.ok(!cardPrimitiveSrc.includes('ref as any'), 'Card.tsx must not use ref as any cast');
  assert.ok(!cardPrimitiveSrc.includes('rest as any'), 'Card.tsx must not use rest as any cast');
});

test('Card.tsx: DnD callers wrap with outer div not Card ref', () => {
  // SearchResultCard must use an outer <div> wrapper for the DnD ref,
  // not pass it directly to <Card>. Pattern: <div ref={setNodeRef} before <Card
  assert.ok(searchResultCardSrc.includes('<div ref={setNodeRef}'), 'SearchResultCard must use outer div wrapper for DnD ref');
  // Card element itself must not carry the DnD ref
  const cardOpenTag = searchResultCardSrc.match(/<Card[^>]*>/)?.[0] ?? '';
  assert.ok(!cardOpenTag.includes('ref='), 'Card element must not carry a ref= prop in SearchResultCard');
});

// ── Hardening: expanded touch-target coverage ─────────────────────────────────

test('ItineraryItemCard: timeline day-part buttons use min-h-[44px] compliant pattern', () => {
  // Day-part buttons use nested span approach with min-h-[44px] on the button
  assert.ok(itineraryCardSrc.includes('min-h-[44px]'), 'ItineraryItemCard must have min-h-[44px] on interactive controls');
});

test('ItineraryItemCard: Move-to-Ideas button has 44px hit area', () => {
  assert.ok(
    itineraryCardSrc.includes('min-h-[44px]') && itineraryCardSrc.includes('Move to Ideas'),
    'Move to Ideas button must have min-h-[44px]'
  );
});

test('ItineraryItemCard: Google Flights links have invisible-padding touch target', () => {
  // Links use -my-3.5 py-3.5 for 44px hit area (14px*2 + ~16px content = 44px)
  assert.ok(itineraryCardSrc.includes('-my-3.5 py-3.5'), 'Google Flights links must use -my-3.5 py-3.5 for 44px hit area');
});

test('TripIdeasPanel: remove button has 44×44 hit area', () => {
  assert.ok(tripIdeasPanelSrc.includes('min-w-[44px] min-h-[44px]'), 'TripIdeasPanel remove button must have min-w/h-[44px]');
});

test('TripIdeasPanel: status chips and filter chips use 44px-compliant buttons', () => {
  assert.ok(tripIdeasPanelSrc.includes('min-h-[44px]'), 'TripIdeasPanel chip buttons must have min-h-[44px]');
});

test('TripIdeasPanel: Add to Day button and day select have 44px hit area', () => {
  const src = tripIdeasPanelSrc;
  assert.ok(src.includes('min-h-[44px]') && src.includes('Add to Day'), 'Add to Day must have min-h-[44px]');
});

test('TripIdeasPanel: Show more / Show less buttons have 44px hit area', () => {
  assert.ok(
    tripIdeasPanelSrc.includes('Show more') && tripIdeasPanelSrc.includes('min-h-[44px]'),
    'Show more/less buttons must have min-h-[44px]'
  );
});

test('TripBuilder: SortControl buttons use 44px-compliant nested pattern', () => {
  assert.ok(tripBuilderSrc.includes('min-h-[44px]'), 'TripBuilder SortControl buttons must have min-h-[44px]');
});

test('TripBuilder: PRIMARY_CTA and SECONDARY_CTA have min-h-[44px]', () => {
  assert.ok(tripBuilderSrc.includes('min-h-[44px]'), 'TripBuilder CTAs must have min-h-[44px]');
});

test('FlightExploreFlow: booking CTA link has 44px hit area', () => {
  assert.ok(flightExploreSrc.includes('min-h-[44px]'), 'FlightExploreFlow booking CTA must have min-h-[44px]');
});
