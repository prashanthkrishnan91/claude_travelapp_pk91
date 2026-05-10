// Attraction score normalization — source-content + unit tests.
//
// Guards that:
//   1. mapUnifiedAttractionToResult normalizes concierge 0-8 score to 0-100 display.
//   2. When rating+numReviews are available, computeExploreAttractionScore is used.
//   3. Raw scores in [0, 10] range are scaled up (not displayed as-is).
//   4. computeExploreAttractionScore returns values in [0, 100].
//   5. AiScoreBadge thresholds in TripBuilder (>= 70 emerald, >= 50 amber) work
//      correctly with normalized 0-100 scores.

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const apiSrc = readFileSync(
  new URL('../src/lib/api.ts', import.meta.url),
  'utf8',
);
const tripBuilder = readFileSync(
  new URL('../src/components/trips/TripBuilder.tsx', import.meta.url),
  'utf8',
);

// ── mapUnifiedAttractionToResult score normalization ─────────────────────────

test('api.ts: mapUnifiedAttractionToResult normalizes raw score via computeExploreAttractionScore', () => {
  assert.match(
    apiSrc,
    /computeExploreAttractionScore\(rating,\s*numReviews,\s*category\)/,
    'mapUnifiedAttractionToResult must call computeExploreAttractionScore when rating+numReviews available',
  );
});

test('api.ts: mapUnifiedAttractionToResult scales raw 0-10 score to 0-100', () => {
  assert.match(
    apiSrc,
    /rawAiScore\s*\*\s*\(100\s*\/\s*8/,
    'Raw concierge score (max ~8) must be scaled to 0-100 as fallback',
  );
});

test('api.ts: mapUnifiedAttractionToResult caps scaled score at 100', () => {
  assert.match(
    apiSrc,
    /Math\.min\(100,\s*rawAiScore/,
    'Scaled score must be capped at 100',
  );
});

test('api.ts: computeExploreAttractionScore returns values in [0, 100]', () => {
  // Check formula uses Math.min(100, ...) and Math.max(0, ...)
  const fnMatch = apiSrc.match(
    /export function computeExploreAttractionScore[\s\S]*?^}/m,
  );
  assert.ok(fnMatch, 'computeExploreAttractionScore must be exported from api.ts');
  const fn = fnMatch[0];
  assert.match(fn, /Math\.min\(100/, 'Score must be capped at 100');
  assert.match(fn, /Math\.max\(0/, 'Score must be floored at 0');
});

// ── Inline score computation unit tests ──────────────────────────────────────

// Inline the formula to unit-test without importing TS
function computeExploreAttractionScore(rating, numReviews, category) {
  const ratingScore = (rating / 5.0) * 100;
  const reviewScore = Math.min(100.0, (Math.log1p(numReviews) / Math.log1p(500_000)) * 100);
  const popularity = ratingScore * 0.6 + reviewScore * 0.4;
  const uniquenessBonus = category === 'hidden_gems' || category === 'local_favorites' ? 8.0 : 0.0;
  const raw = popularity * 0.9 + uniquenessBonus * 0.1;
  return Math.round(Math.min(100.0, Math.max(0.0, raw)) * 10) / 10;
}

test('computeExploreAttractionScore: Eiffel Tower (4.7★, 200k reviews) → high score (>= 80)', () => {
  const score = computeExploreAttractionScore(4.7, 200_000, 'top_attractions');
  assert.ok(score >= 80, `Expected score >= 80 for Eiffel Tower, got ${score}`);
  assert.ok(score <= 100, `Expected score <= 100, got ${score}`);
});

test('computeExploreAttractionScore: mediocre place (3.0★, 20 reviews) → low score (< 60)', () => {
  const score = computeExploreAttractionScore(3.0, 20, 'attraction');
  assert.ok(score < 60, `Expected score < 60 for low-rated place, got ${score}`);
  assert.ok(score >= 0, `Expected score >= 0, got ${score}`);
});

test('computeExploreAttractionScore: perfect place (5.0★, 1M reviews) → near 100', () => {
  const score = computeExploreAttractionScore(5.0, 1_000_000, 'top_attractions');
  assert.ok(score >= 90, `Expected score >= 90 for perfect place, got ${score}`);
  assert.ok(score <= 100, `Expected score <= 100, got ${score}`);
});

test('raw score normalization: concierge score 7.0 → normalized ≈ 87.5 (0-100)', () => {
  const rawScore = 7.0;
  const normalized = Math.round(Math.min(100, rawScore * (100 / 8.0)) * 10) / 10;
  assert.ok(normalized >= 85 && normalized <= 90, `Expected 7.0 → ~87.5, got ${normalized}`);
});

test('raw score normalization: concierge score 5.0 → normalized ≈ 62.5 (amber range)', () => {
  const rawScore = 5.0;
  const normalized = Math.round(Math.min(100, rawScore * (100 / 8.0)) * 10) / 10;
  assert.ok(normalized >= 60 && normalized <= 65, `Expected 5.0 → ~62.5, got ${normalized}`);
});

// ── TripBuilder AiScoreBadge thresholds ──────────────────────────────────────

test('TripBuilder: AiScoreBadge threshold for emerald is >= 70 (0-100 scale)', () => {
  assert.match(
    tripBuilder,
    /score\s*>=\s*70/,
    'AiScoreBadge must use >= 70 threshold for emerald tier (0-100 scale)',
  );
});

test('TripBuilder: AiScoreBadge threshold for amber is >= 50 (0-100 scale)', () => {
  assert.match(
    tripBuilder,
    /score\s*>=\s*50/,
    'AiScoreBadge must use >= 50 threshold for amber tier (0-100 scale)',
  );
});
