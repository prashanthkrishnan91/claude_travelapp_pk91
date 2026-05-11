/**
 * Trip Workspace Candidate Experience v1 — regression tests.
 *
 * Guards the specific invariants introduced in this slice:
 *
 *  1. Persisted candidates render even when the Explore snapshot is empty
 *     (mergePersistedWithSnapshot contract).
 *  2. An empty snapshot cannot zero out non-empty persisted attractions /
 *     restaurants (same contract — explicit null-snapshot case).
 *  3. Trip Ideas does not show creation-seed candidates (data-layer guard
 *     lives in backend list_unscheduled_items; this test confirms TripIdeasPanel
 *     calls fetchTripIdeas and not the raw items endpoint).
 *  4. Hotel cards do not duplicate address as primary filler when richer
 *     location metadata is available (location dedup guard in HotelCandidateCard).
 *  5. No AI Concierge fallback is triggered for initial post-create hydration
 *     (TripBuilder must not call concierge search functions).
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const tripBuilderSrc = readFileSync(
  new URL('../src/components/trips/TripBuilder.tsx', import.meta.url),
  'utf8',
);

const tripIdeasSrc = readFileSync(
  new URL('../src/components/trips/TripIdeasPanel.tsx', import.meta.url),
  'utf8',
);

const candidateSrc = readFileSync(
  new URL('../src/lib/tripCandidates.ts', import.meta.url),
  'utf8',
);

const apiSrc = readFileSync(
  new URL('../src/lib/api.ts', import.meta.url),
  'utf8',
);

// ── 1. Persisted candidates survive an empty snapshot ────────────────────────

test('mergePersistedWithSnapshot: persisted attractions survive when snapshot is empty', () => {
  // Source-level guard: non-empty persisted bucket takes precedence.
  assert.match(
    candidateSrc,
    /persisted\.attractions\.length > 0 \? persisted\.attractions : snapshot\.attractions/,
    'mergePersistedWithSnapshot must prefer persisted attractions over snapshot',
  );
});

test('mergePersistedWithSnapshot: persisted restaurants survive when snapshot is empty', () => {
  assert.match(
    candidateSrc,
    /persisted\.restaurants\.length > 0 \? persisted\.restaurants : snapshot\.restaurants/,
    'mergePersistedWithSnapshot must prefer persisted restaurants over snapshot',
  );
});

// ── 2. Null/empty snapshot cannot zero out non-empty persisted buckets ───────

test('mergePersistedWithSnapshot: null snapshot returns persisted buckets unchanged', () => {
  // Guard: the function exits early on null snapshot without touching buckets.
  assert.match(
    candidateSrc,
    /if \(!snapshot\) return persisted;/,
    'mergePersistedWithSnapshot must return persisted unchanged when snapshot is null',
  );
});

test('TripBuilder only fetches snapshot when at least one persisted bucket is empty', () => {
  // The snapshot fetch is guarded — it should not override non-empty persisted data.
  assert.match(
    tripBuilderSrc,
    /buckets\.attractions\.length === 0 \|\| buckets\.restaurants\.length === 0/,
    'TripBuilder must guard snapshot fetch with empty-bucket check',
  );
});

// ── 3. Trip Ideas shows only user-saved shortlist, not creation-seed rows ────

test('TripIdeasPanel fetches via fetchTripIdeas (concierge_idea scoped endpoint)', () => {
  // fetchTripIdeas hits GET /trips/{id}/ideas which is scoped to source_kind=concierge_idea
  // on the backend — ensuring creation-seed rows never appear in Trip Ideas.
  assert.match(
    tripIdeasSrc,
    /fetchTripIdeas/,
    'TripIdeasPanel must use fetchTripIdeas to load user-saved shortlist',
  );
  // Must NOT call fetchTripItems directly (which returns all candidate rows)
  assert.doesNotMatch(
    tripIdeasSrc,
    /fetchTripItems/,
    'TripIdeasPanel must not call fetchTripItems (all-candidates endpoint)',
  );
});

test('api.ts exports fetchTripIdeas distinct from fetchTripItems', () => {
  assert.match(apiSrc, /export async function fetchTripIdeas\(/, 'fetchTripIdeas must exist');
  assert.match(apiSrc, /export async function fetchTripItems\(/, 'fetchTripItems must exist');
});

// ── 4. Hotel cards do not duplicate address as primary filler ────────────────

test('HotelCandidateCard guards location display when it matches the hotel name', () => {
  // The guard prevents showing location when it equals name (e.g. item.location = hotel title).
  assert.match(
    tripBuilderSrc,
    /location\.trim\(\)\.toLowerCase\(\) !== name\.trim\(\)\.toLowerCase\(\)/,
    'HotelCandidateCard must skip rendering location when it equals hotel name',
  );
});

test('HotelCandidateCard suppresses redundant location when proximity AND area badges are both present', () => {
  // When both proximityLabel and areaLabel are available, raw location string is suppressed.
  assert.match(
    tripBuilderSrc,
    /!\(proximityLabel && areaLabel\)/,
    'HotelCandidateCard must suppress raw location when both area badges are available',
  );
});

// ── 5. No AI Concierge fallback for initial post-create hydration ────────────

test('TripBuilder does not call searchAttractionsViaConcierge for hydration', () => {
  assert.doesNotMatch(
    tripBuilderSrc,
    /searchAttractionsViaConcierge/,
    'TripBuilder must not use AI Concierge to hydrate attractions',
  );
});

test('TripBuilder does not call searchRestaurantsViaConcierge for hydration', () => {
  assert.doesNotMatch(
    tripBuilderSrc,
    /searchRestaurantsViaConcierge/,
    'TripBuilder must not use AI Concierge to hydrate restaurants',
  );
});

test('TripBuilder does not write an explore snapshot during hydration (saveExploreSnapshot absent)', () => {
  // Writing an empty snapshot back was the original source of the zero-state lock.
  assert.doesNotMatch(
    tripBuilderSrc,
    /saveExploreSnapshot\(/,
    'TripBuilder must not call saveExploreSnapshot during candidate hydration',
  );
});

// ── 6. CandidatePanel emptyMessage prop present (per-vertical clarity) ───────

test('CandidatePanel accepts an emptyMessage prop for per-vertical empty states', () => {
  assert.match(
    tripBuilderSrc,
    /emptyMessage\?:\s*string/,
    'CandidatePanel must declare emptyMessage as an optional string prop',
  );
});

test('each candidate panel passes a vertical-specific emptyMessage', () => {
  // Flights, Hotels, Attractions, Restaurants each supply a distinct message.
  assert.match(tripBuilderSrc, /No flight options seeded/,     'Flights panel needs specific empty message');
  assert.match(tripBuilderSrc, /No hotel options seeded/,      'Hotels panel needs specific empty message');
  assert.match(tripBuilderSrc, /No attractions seeded yet/,    'Attractions panel needs specific empty message');
  assert.match(tripBuilderSrc, /No restaurants seeded yet/,    'Restaurants panel needs specific empty message');
});

// ── 7. Round-trip / one-way flights rendered with clear section labels ────────

test('Flight panel renders One-way options and Round-trip pairs section labels when both types present', () => {
  assert.match(tripBuilderSrc, /One-way options/, 'One-way section label must be present in TripBuilder');
  assert.match(tripBuilderSrc, /Round-trip pairs/, 'Round-trip section label must be present in TripBuilder');
});
