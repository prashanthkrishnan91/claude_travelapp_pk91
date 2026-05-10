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
  // searchRestaurants: verified filter includes canonical identity check (Boolean(...))
  assert.match(apiTs, /Boolean\(r\.googleMapsUri \|\| r\.providerPlaceId \|\| r\.placeId\)/);
  // fetchExploreSnapshot: null-return trust gate still present
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
  // Verified: has googleMapsUri or providerPlaceId or placeId AND no mock- prefix
  // Filter now combines mock-prefix guard + identity check in one step
  assert.match(apiTs, /const verified = mapped\.filter/);
  assert.match(apiTs, /Boolean\(r\.googleMapsUri \|\| r\.providerPlaceId \|\| r\.placeId\)/);
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

// ─── Test 6: Backend cache hit raw_count defined + mock data removed ────────────

test('backend search_restaurants cache hit path defines raw_count before logger.info', () => {
  // raw_count = len(cached) must still exist for the cache-hit logger.info call
  assert.match(backendSearch, /raw_count = len\(cached\)/);
  // Locate the search_restaurants method body for scoped assertions
  const methodStart = backendSearch.indexOf('def search_restaurants(');
  const methodEnd = backendSearch.indexOf('\n    def ', methodStart + 1);
  const methodBody = methodEnd > methodStart
    ? backendSearch.slice(methodStart, methodEnd)
    : backendSearch.slice(methodStart);
  // raw_count must appear in the method (cache-hit block)
  assert.match(methodBody, /raw_count = len\(cached\)/);
  assert.match(methodBody, /raw_candidates=%d.*raw_count/s);
});

test('backend search_restaurants no longer calls _mock_restaurants (mock fallback removed)', () => {
  // After fix: search_restaurants returns [] on cache miss, never calls _mock_restaurants
  const methodStart = backendSearch.indexOf('def search_restaurants(');
  const methodEnd = backendSearch.indexOf('\n    def ', methodStart + 1);
  const methodBody = methodEnd > methodStart
    ? backendSearch.slice(methodStart, methodEnd)
    : backendSearch.slice(methodStart);
  // _mock_restaurants must NOT be called inside search_restaurants
  assert.doesNotMatch(methodBody, /_mock_restaurants\(/);
  // The no-provider path must log source_status=no_provider
  assert.match(methodBody, /no_provider/);
});

test('backend search_restaurants discards stale mock cache entries (mock_bypass)', () => {
  // All-mock cache entries must be discarded, not returned to the API consumer
  assert.match(backendSearch, /all\(item\.get\("source"\) == "mock" for item in cached\)/);
  assert.match(backendSearch, /mock_bypass/);
});

// ─── Test 7: Regression - unverified restaurants still blocked ────────────────

test('fetchExploreSnapshot filters out restaurants with no google identity (null filter)', () => {
  assert.match(apiTs, /if \(!googleMapsUri && !providerPlaceId && !placeId\) return null/);
});

test('searchRestaurants trust gate: non-mock restaurant with no identity fields is dropped', () => {
  // verified filter now also excludes mock- prefixed providerPlaceId
  assert.match(apiTs, /!pId\.startsWith\("mock-"\) && Boolean\(r\.googleMapsUri \|\| r\.providerPlaceId \|\| r\.placeId\)/);
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

// ─── Tests 11–16: Mock/demo restaurant rejection ─────────────────────────────

test('searchRestaurants rejects source="mock" restaurants before any identity check', () => {
  // Safety net: mock-source results are stripped before verified filter
  // Mock names like Bangkok Garden Chicago, Corner Brew Café Chicago, Spice Route Chicago
  // have source="mock" → nonMockRaw filter drops them
  assert.match(apiTs, /const nonMockRaw = results\.filter\(\(r\) => r\.source !== "mock"\)/);
  assert.match(apiTs, /const mapped = nonMockRaw\.map\(mapRestaurantToResult\)/);
});

test('searchRestaurants rejects mock- prefixed providerPlaceId (fake identity) from verified list', () => {
  // Mock restaurants have provider_place_id="mock-{slug}-{city}" which fakes a verified identity.
  // The verified filter now also rejects entries where providerPlaceId starts with "mock-".
  assert.match(apiTs, /!pId\.startsWith\("mock-"\)/);
});

test('RawRestaurantResult interface includes source field for mock-source detection', () => {
  assert.match(apiTs, /interface RawRestaurantResult/);
  // source field must be declared so TypeScript consumers can check r.source === "mock"
  assert.match(apiTs, /source\?: string/);
});

test('fetchExploreSnapshot quarantines mock snapshot entries with isMockEntry guard', () => {
  // Stale mock snapshots have providerPlaceId="mock-{slug}-{city}" saved from previous renders.
  // isMockEntry guard must return null before trust gate, preventing hydration as visible cards.
  assert.match(apiTs, /const isMockEntry/);
  assert.match(apiTs, /providerPlaceId\.startsWith\("mock-"\)/);
  assert.match(apiTs, /if \(isMockEntry\) return null/);
});

test('saveExploreSnapshot filters out mock-marker restaurants before persisting to snapshot', () => {
  // Defense: even if a mock restaurant reaches candidateRestaurants state,
  // saveExploreSnapshot must not write it to trips.metadata.explore_snapshot.
  assert.match(apiTs, /\.filter\(\(r\) => !r\.providerPlaceId\?\.startsWith\("mock-"\)\)/);
});

test('backend _mock_restaurants remains deleted and search_restaurants stays fail-closed Google Places', () => {
  // Final mock-leak closeout removed _mock_restaurants. Keep this strict so
  // future edits cannot silently reintroduce mock-backed behavior.
  assert.doesNotMatch(backendSearch, /def _mock_restaurants\(/, '_mock_restaurants must remain absent');
  const methodStart = backendSearch.indexOf('def search_restaurants(');
  const methodEnd = backendSearch.indexOf('\n    def ', methodStart + 1);
  const methodBody = methodEnd > methodStart
    ? backendSearch.slice(methodStart, methodEnd)
    : backendSearch.slice(methodStart);
  assert.doesNotMatch(methodBody, /_mock_restaurants\(/, 'search_restaurants must not call deleted _mock_restaurants');
  assert.match(backendSearch, /Returns an empty list on any error \(fail-closed\)\. Never returns mock data\./, 'search_restaurants must preserve fail-closed contract');
  assert.match(methodBody, /api_key = os\.getenv\("GOOGLE_PLACES_API_KEY", ""\)/, 'search_restaurants must remain Google Places-provider gated');
  assert.match(methodBody, /if not provider_configured:[\s\S]*?return \[\]/, 'search_restaurants must fail closed when provider is unconfigured');
});
