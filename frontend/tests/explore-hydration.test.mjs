import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const tripBuilder = readFileSync(
  new URL('../src/components/trips/TripBuilder.tsx', import.meta.url),
  'utf8',
);
const apiClient = readFileSync(
  new URL('../src/lib/api.ts', import.meta.url),
  'utf8',
);

const searchModels = readFileSync(
  new URL('../../backend/app/models/search.py', import.meta.url),
  'utf8',
);

const tripsRoutes = readFileSync(
  new URL('../../backend/app/routes/trips.py', import.meta.url),
  'utf8',
);

const tripsService = readFileSync(
  new URL('../../backend/app/services/trips.py', import.meta.url),
  'utf8',
);


test('Existing-trip hydration API contract only exposes ai_score (not rank/top-pick/value score aliases)', () => {
  assert.match(searchModels, /class AttractionResult\(SearchResult\):[\s\S]*?ai_score: Optional\[float\]/, 'Attraction response model should expose ai_score');
  assert.match(searchModels, /class RestaurantResult\(SearchResult\):[\s\S]*?ai_score: Optional\[float\]/, 'Restaurant response model should expose ai_score');
  assert.doesNotMatch(searchModels, /recommendation_score|recommendationScore|value_score|valueScore|rank(?:ing)?|top_pick|is_top_pick|isTopPick/, 'Search response model should not define additional score/rank/top-pick fields');
});

test('Hydration mappers do not currently accept recommendation/value/rank/top-pick score aliases', () => {
  assert.doesNotMatch(tripBuilder, /details\.(?:valueScore|value_score|recommendationScore|recommendation_score|ranking|rank|topPick|top_pick|isTopPick|is_top_pick)/, 'Trip item hydration score mapper is limited to aiScore/ai_score/score');
  assert.doesNotMatch(apiClient, /(?:valueScore|value_score|recommendationScore|recommendation_score|ranking|rank|topPick|top_pick|isTopPick|is_top_pick)/, 'API search mapper is limited to aiScore/ai_score/score');
});

test('TripBuilder waits for auth session before loading attractions/restaurants', () => {
  assert.match(tripBuilder, /authSessionReady/, 'authSessionReady state must exist to gate hydration');
  assert.match(tripBuilder, /supabase\.auth\.getSession\(\)/, 'TripBuilder must check current session on mount');
  assert.match(tripBuilder, /onAuthStateChange/, 'TripBuilder must subscribe to auth changes');
  assert.match(tripBuilder, /if \(!destination \|\| !authSessionReady\) return;/, 'Explore loaders must bail when auth is not ready');
});

test('TripBuilder hydration mapper preserves attraction and restaurant score fields from persisted snake_case/camelCase details', () => {
  assert.match(tripBuilder, /function normalizeExploreScore\(details: Record<string, unknown>\)/, 'TripBuilder should centralize explore score normalization');
  assert.match(tripBuilder, /if \(typeof details\.ai_score === "number"\) return details\.ai_score;/, 'Persisted ai_score should map into aiScore');
  assert.match(tripBuilder, /if \(typeof details\.score === "number"\) return details\.score;/, 'Persisted fallback score should map into aiScore');
  assert.match(tripBuilder, /typeof details\.num_reviews === "number" \? details\.num_reviews/, 'Persisted num_reviews should map for card details');
});

test('API search mappers preserve attraction and restaurant score fields from snake_case/camelCase/score payloads', () => {
  assert.match(apiClient, /typeof a\.ai_score === "number"/, 'Attractions mapper should support ai_score from backend payload');
  assert.match(apiClient, /typeof a\.score === "number"/, 'Attractions mapper should support legacy score field');
  assert.match(apiClient, /typeof r\.ai_score === "number"/, 'Restaurants mapper should support ai_score from backend payload');
  assert.match(apiClient, /typeof r\.score === "number"/, 'Restaurants mapper should support legacy score field');
});

test('TripBuilder calls provider-backed search as fallback when no snapshot exists', () => {
  assert.match(tripBuilder, /searchAttractions\(destination\)/, 'Attractions provider search must be present as fallback path');
  assert.match(tripBuilder, /searchRestaurants\(destination\)/, 'Restaurants provider search must be present as fallback path');
  assert.doesNotMatch(tripBuilder, /if \(candidateAttractions\.length > 0\) return;/, 'In-memory candidate count must not short-circuit snapshot-first hydration');
  assert.doesNotMatch(tripBuilder, /if \(candidateRestaurants\.length > 0\) return;/, 'In-memory candidate count must not short-circuit snapshot-first hydration');
});

test('TripBuilder does not render misleading score or Top Pick for zero/absent score', () => {
  assert.match(tripBuilder, /if \(typeof score !== "number" \|\| !Number\.isFinite\(score\) \|\| score <= 0\) return null;/, 'Score badge must be hidden for missing or zero score');
  assert.match(tripBuilder, /isTopPick=\{attractionSort === "ai" && idx < top20 && \(attraction\.aiScore \?\? 0\) > 0\}/, 'Attraction Top Pick requires positive score');
  assert.match(tripBuilder, /isTopPick=\{restaurantSort === "ai" && idx < top20 && \(restaurant\.aiScore \?\? 0\) > 0\}/, 'Restaurant Top Pick requires positive score');
});

// ─── Persisted Explore Candidate Snapshots v1 ────────────────────────────────

test('TripBuilder imports fetchExploreSnapshot and saveExploreSnapshot from api', () => {
  assert.match(tripBuilder, /fetchExploreSnapshot/, 'TripBuilder must import fetchExploreSnapshot');
  assert.match(tripBuilder, /saveExploreSnapshot/, 'TripBuilder must import saveExploreSnapshot');
});

test('TripBuilder has exploreSnapshotLoadedRef to gate one-shot snapshot fetch', () => {
  assert.match(tripBuilder, /exploreSnapshotLoadedRef/, 'TripBuilder must track snapshot load state via ref to prevent duplicate fetches');
  assert.match(tripBuilder, /exploreSnapshotLoadedRef\.current === hydrationKey/, 'Snapshot load must be idempotent per tripId:destination key');
});

test('TripBuilder snapshot-first hydration: fetches snapshot before calling provider search', () => {
  assert.match(tripBuilder, /const snapshot = await fetchExploreSnapshot\(tripId\)/, 'TripBuilder must await fetchExploreSnapshot before provider search');
  assert.match(tripBuilder, /snapshot\.attractions\.length > 0 \|\| snapshot\.restaurants\.length > 0/, 'Snapshot usability check must cover both attractions and restaurants');
});

test('TripBuilder skips provider search and returns early when usable snapshot exists', () => {
  assert.match(tripBuilder, /if \(snapshot && \(snapshot\.attractions\.length > 0 \|\| snapshot\.restaurants\.length > 0\)\)/, 'Must short-circuit provider search when snapshot is present and non-empty');
  assert.match(tripBuilder, /if \(snapshot\.attractions\.length > 0\) setCandidateAttractions\(snapshot\.attractions\)/, 'Must hydrate attractions from snapshot');
  assert.match(tripBuilder, /if \(snapshot\.restaurants\.length > 0\) setCandidateRestaurants\(snapshot\.restaurants\)/, 'Must hydrate restaurants from snapshot');
});

test('TripBuilder persists snapshot after successful provider search', () => {
  assert.match(tripBuilder, /saveExploreSnapshot\(tripId, \{ destination, attractions: resolvedAttractions, restaurants: resolvedRestaurants \}\)/, 'Provider search results must be persisted as snapshot');
  assert.match(tripBuilder, /if \(resolvedAttractions\.length > 0 \|\| resolvedRestaurants\.length > 0\)/, 'Snapshot save must be gated on non-empty results');
});

test('api.ts exports fetchExploreSnapshot and saveExploreSnapshot', () => {
  assert.match(apiClient, /export async function fetchExploreSnapshot/, 'fetchExploreSnapshot must be exported from api.ts');
  assert.match(apiClient, /export async function saveExploreSnapshot/, 'saveExploreSnapshot must be exported from api.ts');
});

test('api.ts ExploreSnapshot interface is exported and includes required fields', () => {
  assert.match(apiClient, /export interface ExploreSnapshot/, 'ExploreSnapshot interface must be exported');
  assert.match(apiClient, /attractions: AttractionSearchResult\[\]/, 'ExploreSnapshot must include attractions array');
  assert.match(apiClient, /restaurants: RestaurantSearchResult\[\]/, 'ExploreSnapshot must include restaurants array');
  assert.match(apiClient, /destination: string/, 'ExploreSnapshot must include destination');
  assert.match(apiClient, /createdAt: string/, 'ExploreSnapshot must include createdAt timestamp');
});

test('api.ts snapshot mapper gates aiScore on positive value only (no fake 0 scores)', () => {
  // Mapper uses storedScore (positive guard) and falls back to computedScore enrichment
  assert.match(apiClient, /a\.aiScore > 0/, 'Snapshot attraction mapper must guard against zero/negative aiScore');
  assert.match(apiClient, /r\.aiScore > 0/, 'Snapshot restaurant mapper must guard against zero/negative aiScore');
  assert.match(apiClient, /r\.ai_score === "number" && r\.ai_score > 0/, 'Snapshot restaurant mapper must read persisted snake_case ai_score');
  assert.match(apiClient, /a\.ai_score === "number" && a\.ai_score > 0/, 'Snapshot attraction mapper must read persisted snake_case ai_score');
  // computeExploreAttractionScore and computeExploreRestaurantScore exported for enrichment
  assert.match(apiClient, /computeExploreAttractionScore/, 'api.ts must export computeExploreAttractionScore');
  assert.match(apiClient, /computeExploreRestaurantScore/, 'api.ts must export computeExploreRestaurantScore');
});

test('api.ts fetchExploreSnapshot supports score aliases and snake_case metadata fields', () => {
  assert.match(apiClient, /typeof a\.score === "number" && a\.score > 0/, 'Attraction snapshot mapper must support legacy score field');
  assert.match(apiClient, /typeof r\.score === "number" && r\.score > 0/, 'Restaurant snapshot mapper must support legacy score field');
  assert.match(apiClient, /typeof a\.num_reviews === "number" \? a\.num_reviews/, 'Attraction snapshot mapper must map num_reviews');
  assert.match(apiClient, /typeof r\.num_reviews === "number" \? r\.num_reviews/, 'Restaurant snapshot mapper must map num_reviews');
});

test('TripBuilder re-runs provider search exactly once for stale unscored snapshot', () => {
  assert.match(tripBuilder, /hasPositiveExploreScore/, 'TripBuilder must detect whether snapshot already has positive explore scores');
  assert.match(tripBuilder, /if \(hasPositiveExploreScore\(snapshot\.attractions, snapshot\.restaurants\)\) return;/, 'TripBuilder should only short-circuit when snapshot has valid scores');
  assert.match(tripBuilder, /exploreSnapshotLoadedRef\.current === hydrationKey/, 'Hydration key guard avoids repeated provider calls on rerenders');
});

test('api.ts saveExploreSnapshot sends snake_case ai_score field to backend', () => {
  assert.match(apiClient, /ai_score: aiScore/, 'saveExploreSnapshot must serialize enriched aiScore as ai_score for backend');
});

test('api.ts computeExploreAttractionScore mirrors backend formula (rating, numReviews, category)', () => {
  // Function must be exported
  assert.match(apiClient, /export function computeExploreAttractionScore/, 'computeExploreAttractionScore must be exported');
  // Must use log1p for review volume (matches backend math.log1p)
  assert.match(apiClient, /Math\.log1p\(numReviews\)/, 'attraction scorer must use log1p for review volume');
  // Must include uniqueness bonus for hidden_gems and local_favorites
  assert.match(apiClient, /hidden_gems.*local_favorites|local_favorites.*hidden_gems/, 'attraction scorer must apply uniqueness bonus for hidden_gems/local_favorites');
  // Must clamp to 0-100
  assert.match(apiClient, /Math\.min\(100\.0,\s*Math\.max\(0\.0,/, 'attraction scorer must clamp result to 0-100');
});

test('api.ts computeExploreRestaurantScore mirrors backend formula (rating, numReviews, priceLevel, sentiment)', () => {
  assert.match(apiClient, /export function computeExploreRestaurantScore/, 'computeExploreRestaurantScore must be exported');
  assert.match(apiClient, /Math\.log1p\(numReviews\)/, 'restaurant scorer must use log1p for review volume');
  // Must handle sentiment branch
  assert.match(apiClient, /sentiment != null/, 'restaurant scorer must have sentiment branch');
  // Must include price_value calculation
  assert.match(apiClient, /4 - priceLevel/, 'restaurant scorer must compute price value from priceLevel');
});

test('api.ts fetchExploreSnapshot enriches stale candidates (aiScore=null) using computed score fallback', () => {
  // Enrichment path: compute score when storedScore is null but rating+numReviews present
  assert.match(apiClient, /computeExploreAttractionScore\(a\.rating/, 'fetchExploreSnapshot must enrich attractions via computeExploreAttractionScore');
  assert.match(apiClient, /computeExploreRestaurantScore\(/, 'fetchExploreSnapshot must enrich restaurants via computeExploreRestaurantScore');
  // Computed score must still be gated (no zero scores)
  assert.match(apiClient, /computedScore != null && computedScore > 0/, 'Enrichment must still gate on positive computed score');
});

test('api.ts saveExploreSnapshot enriches candidates with computed score before persisting', () => {
  // saveExploreSnapshot must apply enrichment before serializing
  assert.match(apiClient, /computeExploreAttractionScore\(a\.rating/, 'saveExploreSnapshot must compute score for attractions missing aiScore');
  assert.match(apiClient, /computeExploreRestaurantScore\(/, 'saveExploreSnapshot must compute score for restaurants missing aiScore');
  // Final serialization uses local aiScore variable, not raw a.aiScore
  assert.match(apiClient, /ai_score: aiScore/, 'saveExploreSnapshot must serialize enriched aiScore as ai_score');
});

test('Backend search_attractions re-scores stale cache hits with null ai_score', () => {
  const searchService = readFileSync(
    new URL('../../backend/app/services/search.py', import.meta.url),
    'utf8',
  );
  assert.match(searchService, /if r\.ai_score is None and r\.rating is not None and r\.num_reviews is not None/, 'search_attractions must re-score stale cache hits where ai_score is None');
  assert.match(searchService, /_compute_attraction_ai_score\(r\.rating, r\.num_reviews, r\.category/, 'search_attractions must call _compute_attraction_ai_score for re-scoring');
});

test('Backend search_restaurants re-scores stale cache hits with null ai_score', () => {
  const searchService = readFileSync(
    new URL('../../backend/app/services/search.py', import.meta.url),
    'utf8',
  );
  assert.match(searchService, /if r\.ai_score is None and r\.rating is not None and r\.num_reviews is not None/, 'search_restaurants must re-score stale cache hits where ai_score is None');
  assert.match(searchService, /_compute_restaurant_ai_score\(r\.rating, r\.num_reviews, price_level, r\.sentiment\)/, 'search_restaurants must call _compute_restaurant_ai_score for re-scoring');
});

test('Backend trips routes include explore-snapshot GET and PUT endpoints', () => {
  assert.match(tripsRoutes, /\/explore-snapshot/, 'trips.py routes must include explore-snapshot path');
  assert.match(tripsRoutes, /get_explore_snapshot/, 'GET explore-snapshot handler must be defined');
  assert.match(tripsRoutes, /save_explore_snapshot/, 'PUT explore-snapshot handler must be defined');
  assert.match(tripsRoutes, /ExploreSnapshot/, 'trips.py must import ExploreSnapshot model');
});

test('Backend trips routes enforce trip ownership via CurrentUserID for snapshot endpoints', () => {
  assert.match(tripsRoutes, /def get_explore_snapshot\(trip_id: UUID, db: DB, user_id: CurrentUserID\)/, 'GET snapshot must require authenticated user');
  assert.match(tripsRoutes, /def save_explore_snapshot\(trip_id: UUID, payload: ExploreSnapshot, db: DB, user_id: CurrentUserID\)/, 'PUT snapshot must require authenticated user');
});

test('Backend TripsService implements get_explore_snapshot and save_explore_snapshot', () => {
  assert.match(tripsService, /def get_explore_snapshot\(self, trip_id: UUID, user_id: UUID\)/, 'TripsService must have get_explore_snapshot method');
  assert.match(tripsService, /def save_explore_snapshot\(self, trip_id: UUID, user_id: UUID, snapshot: Dict\[str, Any\]\)/, 'TripsService must have save_explore_snapshot method');
  assert.match(tripsService, /explore_snapshot/, 'Service must use explore_snapshot key in trips.metadata');
});

test('Backend ExploreSnapshot model is defined in search.py with required fields', () => {
  assert.match(searchModels, /class ExploreSnapshot\(BaseModel\)/, 'ExploreSnapshot model must be defined');
  assert.match(searchModels, /class ExploreSnapshotAttraction\(BaseModel\)/, 'ExploreSnapshotAttraction model must be defined');
  assert.match(searchModels, /class ExploreSnapshotRestaurant\(BaseModel\)/, 'ExploreSnapshotRestaurant model must be defined');
  assert.match(searchModels, /ai_score: Optional\[float\] = None/, 'Snapshot models must include ai_score field');
});
