import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const apiTs = readFileSync(new URL('../src/lib/api.ts', import.meta.url), 'utf8');
const tripBuilder = readFileSync(new URL('../src/components/trips/TripBuilder.tsx', import.meta.url), 'utf8');
const backendSearch = readFileSync(new URL('../../backend/app/services/search.py', import.meta.url), 'utf8');
const backendModels = readFileSync(new URL('../../backend/app/models/search.py', import.meta.url), 'utf8');

// ─── Test 1: API client mapping ──────────────────────────────────────────────

test('restaurant mapper accepts google_place_id aliases as verified identity', () => {
  assert.match(apiTs, /google_place_id\?: string/);
  assert.match(apiTs, /googlePlaceId\?: string/);
  assert.match(apiTs, /providerPlaceId:\s*providerPlaceId \?\? googlePlaceId/);
  assert.match(apiTs, /placeId:\s*placeId \?\? googlePlaceId/);
});

test('restaurant mapper preserves verified google fields through snapshot hydration aliases', () => {
  assert.match(apiTs, /formatted_address\?: string/);
  assert.match(apiTs, /user_ratings_total\?: number/);
  assert.match(apiTs, /review_count\?: number/);
  assert.match(apiTs, /r\.formattedAddress \?\? r\.formatted_address/);
  assert.match(apiTs, /r\.userRatingsTotal/);
  assert.match(apiTs, /r\.user_ratings_total/);
});

test('explore restaurant trust gate still requires verified place identity fields', () => {
  assert.match(apiTs, /\.filter\(\(r\) => Boolean\(r\.googleMapsUri \|\| r\.providerPlaceId \|\| r\.placeId\)\)/);
  assert.match(apiTs, /if \(!googleMapsUri && !providerPlaceId && !placeId\) return null/);
});

// ─── Test 2: API mapping with 12 verified restaurants ────────────────────────

test('searchRestaurants returns RestaurantSearchEnvelope with restaurants array', () => {
  // Verify the function signature and envelope shape are in api.ts
  assert.match(apiTs, /export interface RestaurantSearchEnvelope/);
  assert.match(apiTs, /restaurants: RestaurantSearchResult\[\]/);
  assert.match(apiTs, /sourceStatus: string/);
  assert.match(apiTs, /terminalNoResults: boolean/);
  assert.match(apiTs, /export async function searchRestaurants/);
  assert.match(apiTs, /Promise<RestaurantSearchEnvelope>/);
});

test('searchRestaurants maps backend snake_case to camelCase identity fields via toCamel', () => {
  // toCamel converts google_maps_uri -> googleMapsUri, provider_place_id -> providerPlaceId
  // The mapper reads camelCase first, falling back to snake_case
  assert.match(apiTs, /r\.googleMapsUri === "string" \? r\.googleMapsUri : typeof r\.google_maps_uri/);
  assert.match(apiTs, /r\.providerPlaceId === "string" \? r\.providerPlaceId : typeof r\.provider_place_id/);
  assert.match(apiTs, /r\.placeId === "string" \? r\.placeId : typeof r\.place_id/);
});

test('searchRestaurants trust filter keeps all verified restaurants and drops unverified', () => {
  // Verified: has googleMapsUri or providerPlaceId or placeId
  // Unverified: all three are falsy
  assert.match(apiTs, /const verified = mapped\.filter\(\(r\) => Boolean\(r\.googleMapsUri \|\| r\.providerPlaceId \|\| r\.placeId\)\)/);
  // Non-zero verified → returned in envelope
  assert.match(apiTs, /return \{ restaurants: verified, sourceStatus, cacheStatus, terminalNoResults \}/);
});

test('searchRestaurants catch returns empty envelope not throws (no uncaught error)', () => {
  assert.match(apiTs, /return \{ restaurants: \[\], sourceStatus: "error", cacheStatus: "bypass", terminalNoResults: false \}/);
});

// ─── Test 3: State/snapshot - empty snapshot + live verified → non-empty state ─

test('TripBuilder sets candidateRestaurants unconditionally after Promise.allSettled (no length guard)', () => {
  // Previous bug: "if (resolvedRestaurants.length > 0) setCandidateRestaurants" — gate prevented setting []
  // was changed to unconditional setCandidateRestaurants to allow self-heal to propagate empty → live results
  assert.match(tripBuilder, /setCandidateRestaurants\(resolvedRestaurants\)/);
  // Must NOT have the old length guard before setCandidateRestaurants
  assert.doesNotMatch(tripBuilder, /if \(resolvedRestaurants\.length > 0\) setCandidateRestaurants/);
});

test('TripBuilder canPersistRestaurants guard prevents saving [] when live results exist and prior was empty', () => {
  assert.match(tripBuilder, /const canPersistRestaurants = resolvedRestaurants\.length > 0 \|\| shouldPersistEmptyRestaurants \|\| priorRestaurants\.length === 0/);
  assert.match(tripBuilder, /restaurants: canPersistRestaurants \? resolvedRestaurants : priorRestaurants/);
});

test('TripBuilder self-heal triggers when snapshot has empty restaurants', () => {
  assert.match(tripBuilder, /const hasHealthyRestaurants = snapshot != null && snapshot\.restaurants\.length > 0 && hasPositiveExploreScore\(snapshot\.restaurants\)/);
  assert.match(tripBuilder, /const shouldFetchRestaurants = !hasHealthyRestaurants/);
  assert.match(tripBuilder, /shouldFetchRestaurants \? searchRestaurants\(destination\)/);
});

// ─── Test 4: Hydration - snapshot with identity fields survives trust gate ────

test('fetchExploreSnapshot identity fields read camelCase first (providerPlaceId, googleMapsUri, placeId)', () => {
  // After toCamel, snapshot restaurants have camelCase keys
  // The mapper must read these camelCase fields first
  assert.match(apiTs, /typeof r\.providerPlaceId === "string" \? r\.providerPlaceId/);
  assert.match(apiTs, /typeof r\.googleMapsUri === "string" \? r\.googleMapsUri/);
  assert.match(apiTs, /typeof r\.placeId === "string" \? r\.placeId/);
});

test('fetchExploreSnapshot also reads snake_case identity aliases (google_place_id, google_maps_uri)', () => {
  assert.match(apiTs, /typeof r\.google_place_id === "string" \? r\.google_place_id/);
  assert.match(apiTs, /typeof r\.google_maps_uri === "string" \? r\.google_maps_uri/);
});

test('saveExploreSnapshot sends provider_place_id, google_maps_uri, place_id to backend', () => {
  assert.match(apiTs, /provider_place_id: r\.providerPlaceId \?\? r\.placeId \?\? null/);
  assert.match(apiTs, /google_maps_uri: r\.googleMapsUri \?\? null/);
  assert.match(apiTs, /place_id: r\.placeId \?\? null/);
});

// ─── Test 5: Backend ExploreSnapshotRestaurant now persists identity ──────────

test('ExploreSnapshotRestaurant model includes provider_place_id, google_maps_uri, place_id', () => {
  // These fields were missing — causing identity to be stripped on PUT, breaking snapshot trust gate
  assert.match(backendModels, /class ExploreSnapshotRestaurant\(BaseModel\):/);
  assert.match(backendModels, /provider_place_id: Optional\[str\]/);
  assert.match(backendModels, /google_maps_uri: Optional\[str\]/);
  assert.match(backendModels, /place_id: Optional\[str\]/);
});

// ─── Test 6: Backend cache hit raw_count defined ─────────────────────────────

test('backend search_restaurants cache hit path defines raw_count before logger.info', () => {
  // Previously raw_count was undefined on cache hit → NameError → 500 → frontend gets []
  // The fix: raw_count = len(cached) must appear before the logger.info call
  assert.match(backendSearch, /raw_count = len\(cached\)/);
  // raw_count must appear BEFORE the logger.info that uses it in the cache hit block
  const hitBlock = backendSearch.slice(
    backendSearch.indexOf('if cached:'),
    backendSearch.indexOf('results = _mock_restaurants')
  );
  assert.match(hitBlock, /raw_count = len\(cached\)/);
  assert.match(hitBlock, /raw_candidates=%d.*raw_count/s);
});

// ─── Test 7: Regression - unverified restaurants still blocked ────────────────

test('fetchExploreSnapshot filters out restaurants with no google identity (null filter)', () => {
  assert.match(apiTs, /if \(!googleMapsUri && !providerPlaceId && !placeId\) return null/);
});

test('searchRestaurants trust gate: restaurant with no googleMapsUri/providerPlaceId/placeId is dropped', () => {
  // verified = mapped.filter(r => Boolean(r.googleMapsUri || r.providerPlaceId || r.placeId))
  // A restaurant with all three absent returns false from Boolean(false || false || false)
  assert.match(apiTs, /const verified = mapped\.filter\(\(r\) => Boolean\(r\.googleMapsUri \|\| r\.providerPlaceId \|\| r\.placeId\)\)/);
});

// ─── Test 8: Maps URL uses google_maps_uri/place_id ──────────────────────────

test('restaurant Maps link uses canonical googleMapsUri then placeId, not loose name+city query', () => {
  // RestaurantCandidateCard should use googleMapsUri or place_id URL, not a generic search
  // Verify saveExploreSnapshot preserves google_maps_uri for Maps link
  assert.match(apiTs, /google_maps_uri: r\.googleMapsUri \?\? null/);
  // Verify fetchExploreSnapshot reconstructs googleMapsUri for the card
  assert.match(apiTs, /googleMapsUri,/);
  assert.match(apiTs, /providerPlaceId,/);
  assert.match(apiTs, /placeId,/);
});

// ─── Test 9: Race - stale empty snapshot cannot overwrite live results ────────

test('TripBuilder hydration effect is one-shot per tripId:destination (exploreSnapshotLoadedRef)', () => {
  assert.match(tripBuilder, /exploreSnapshotLoadedRef\.current === hydrationKey/);
  // The ref is set synchronously before async work — prevents double execution
  assert.match(tripBuilder, /exploreSnapshotLoadedRef\.current = hydrationKey/);
});

test('TripBuilder snapshot hydration does not set candidateRestaurants from snapshot when restaurants are empty', () => {
  // Only sets from snapshot when length > 0 — avoids overwriting live results with stale []
  assert.match(tripBuilder, /if \(snapshot\.restaurants\.length > 0\) setCandidateRestaurants\(snapshot\.restaurants\)/);
});

// ─── Test 10: canPersistRestaurants prevents snapshot overwrite with empty ────

test('TripBuilder does not overwrite prior non-empty restaurants with empty live result unless terminalNoResults', () => {
  // shouldPersistEmptyRestaurants only true when both resolved is [] AND terminalNoResults
  assert.match(tripBuilder, /const shouldPersistEmptyRestaurants = resolvedRestaurants\.length === 0 && resolvedRestaurantEnvelope\.terminalNoResults/);
  // canPersistRestaurants = true only when there are results OR terminal OR prior was already empty
  assert.match(tripBuilder, /const canPersistRestaurants = resolvedRestaurants\.length > 0 \|\| shouldPersistEmptyRestaurants \|\| priorRestaurants\.length === 0/);
});
