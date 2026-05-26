/**
 * Trip Workspace Finalized Itinerary Card Experience v1 — regression tests.
 *
 * Guards the invariants introduced in this slice:
 *
 *  1. Hotel day cards: no duplicated name/location/address filler (existing
 *     contract extended by area_label / stars / amenities enrichment).
 *  2. Hotel day cards: richer metadata (stars, area_label, proximity_label,
 *     amenities/tags) is rendered from stored details when present.
 *  3. One-way flight add preserves schedule display (origin→dest, times, leg).
 *  4. Round-trip flight display: outbound + return legs remain intact.
 *  5. Activity (attraction) day cards: vertical-specific section with rating,
 *     category, and tags — not a generic fallback only.
 *  6. Restaurant (meal) day cards: vertical-specific section with cuisine,
 *     rating, price level, and tags.
 *  7. Trip Ideas remains shortlist-only (fetchTripIdeas, not fetchTripItems).
 *  8. No AI Concierge fallback is used for finalized day display.
 *  9. addHotelToDay API function exists and passes item details to the backend.
 * 10. TripBuilder uses addHotelToDay for hotel candidates (not bare createItem).
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const itemCard = readFileSync(
  new URL('../src/components/trips/ItineraryItemCard.tsx', import.meta.url),
  'utf8',
);

const tripBuilderSrc = readFileSync(
  new URL('../src/components/trips/TripBuilder.tsx', import.meta.url),
  'utf8',
);

const apiSrc = readFileSync(
  new URL('../src/lib/api.ts', import.meta.url),
  'utf8',
);

const tripIdeasSrc = readFileSync(
  new URL('../src/components/trips/TripIdeasPanel.tsx', import.meta.url),
  'utf8',
);

// ── 1. Hotel: location comment preserved (no duplicate) ─────────────────────

test('ItineraryItemCard: hotel block preserves "Location is shown in the main" comment', () => {
  assert.match(
    itemCard,
    /Location is shown\s+in the main/,
    'Hotel block must note that location is shown in the main location line, not duplicated',
  );
});

test('ItineraryItemCard: hotel block does not render a standalone location variable', () => {
  assert.doesNotMatch(
    itemCard,
    /const location\s*=.*check_in|check_in.*const location/,
    'Hotel block must not declare location alongside check_in (old duplicate pattern)',
  );
});

// ── 2. Hotel: richer metadata now rendered ────────────────────────────────────

test('ItineraryItemCard: hotel block reads d.stars for display', () => {
  assert.match(
    itemCard,
    /d\.stars/,
    'Hotel block must read d.stars to display star rating',
  );
});

test('ItineraryItemCard: hotel block renders hotel stars using repeat pattern', () => {
  assert.match(
    itemCard,
    /★.*repeat/,
    'Hotel block must render stars with ★.repeat(...) for the star category',
  );
});

test('ItineraryItemCard: hotel block reads area_label (snake_case field)', () => {
  assert.match(
    itemCard,
    /area_label/,
    'Hotel block must read d.area_label (backend snake_case field)',
  );
});

test('ItineraryItemCard: hotel block reads areaLabel (camelCase field)', () => {
  assert.match(
    itemCard,
    /d\.areaLabel/,
    'Hotel block must read d.areaLabel (camelCase for toCamel-transformed items)',
  );
});

test('ItineraryItemCard: hotel block reads proximity_label', () => {
  assert.match(
    itemCard,
    /proximity_label/,
    'Hotel block must read d.proximity_label to show location context',
  );
});

test('ItineraryItemCard: hotel block renders area badge for In Best Area', () => {
  assert.match(
    itemCard,
    /In Best Area/,
    'Hotel block must render In Best Area badge when area_label matches',
  );
});

test('ItineraryItemCard: hotel block renders amenities and tags as pills', () => {
  assert.match(
    itemCard,
    /d\.amenities/,
    'Hotel block must read d.amenities to render as tag pills',
  );
});

test('ItineraryItemCard: hotel section still reads d.check_in and d.check_out', () => {
  assert.match(itemCard, /d\.check_in\b/, 'Hotel section must still read d.check_in');
  assert.match(itemCard, /d\.check_out\b/, 'Hotel section must still read d.check_out');
});

test('ItineraryItemCard: hotel section still renders rating.toFixed(1)', () => {
  assert.match(
    itemCard,
    /rating\.toFixed\(1\)/,
    'Hotel section must still display review rating formatted to 1 decimal',
  );
});

// ── 3. Activity (attraction): vertical-specific section exists ───────────────

test('ItineraryItemCard: activity block reads d.rating', () => {
  assert.match(
    itemCard,
    /item\.itemType === "activity"/,
    'ItineraryItemCard must have an activity-specific display block',
  );
});

test('ItineraryItemCard: activity block renders Star icon for rating', () => {
  // The activity section should use the Star lucide icon.
  // We check the file has Star in imports.
  assert.match(
    itemCard,
    /import\s*\{[^}]*\bStar\b/,
    'ItineraryItemCard must import Star from lucide-react for rating display',
  );
});

test('ItineraryItemCard: activity block reads d.category', () => {
  assert.match(
    itemCard,
    /d\.category/,
    'Activity block must read d.category from stored details',
  );
});

test('ItineraryItemCard: activity block reads d.tags for tag pills', () => {
  // The meal block also reads d.tags, so confirm item.itemType === "activity" block
  // contains a tags reference.
  const activityIdx = itemCard.indexOf('item.itemType === "activity" && (() => {');
  const mealIdx = itemCard.indexOf('item.itemType === "meal" && (() => {');
  assert.ok(activityIdx >= 0, 'activity block must exist');
  // Extract the activity block source up to the meal block
  const activityBlock = itemCard.slice(activityIdx, mealIdx > activityIdx ? mealIdx : undefined);
  assert.match(activityBlock, /d\.tags/, 'Activity block must read d.tags for pill display');
});

test('ItineraryItemCard: activity block shows maps link when google_maps_uri or placeId present', () => {
  const activityIdx = itemCard.indexOf('item.itemType === "activity" && (() => {');
  const mealIdx = itemCard.indexOf('item.itemType === "meal" && (() => {');
  const activityBlock = itemCard.slice(activityIdx, mealIdx > activityIdx ? mealIdx : undefined);
  assert.match(activityBlock, /google_maps_uri|placeId|place_id/, 'Activity block must use google_maps_uri or placeId to build map link');
  assert.match(activityBlock, /ExternalLink/, 'Activity block must use ExternalLink icon for the map action');
});

// ── 4. Restaurant (meal): vertical-specific section exists ──────────────────

test('ItineraryItemCard: meal block exists with item.itemType check', () => {
  assert.match(
    itemCard,
    /item\.itemType === "meal"/,
    'ItineraryItemCard must have a meal-specific display block',
  );
});

test('ItineraryItemCard: meal block reads d.cuisine', () => {
  const mealIdx = itemCard.indexOf('item.itemType === "meal" && (() => {');
  assert.ok(mealIdx >= 0, 'meal block must exist');
  const mealBlock = itemCard.slice(mealIdx, mealIdx + 2000);
  assert.match(mealBlock, /d\.cuisine/, 'Meal block must read d.cuisine from stored details');
});

test('ItineraryItemCard: meal block renders priceLevel as $ symbols', () => {
  const mealIdx = itemCard.indexOf('item.itemType === "meal" && (() => {');
  const mealBlock = itemCard.slice(mealIdx, mealIdx + 2000);
  assert.match(
    mealBlock,
    /price_level|priceLevel/,
    'Meal block must read price_level / priceLevel from stored details',
  );
  assert.match(
    mealBlock,
    /\$.*repeat/,
    'Meal block must render price level as "$".repeat(...)',
  );
});

test('ItineraryItemCard: meal block reads d.tags for pill display', () => {
  const mealIdx = itemCard.indexOf('item.itemType === "meal" && (() => {');
  const mealBlock = itemCard.slice(mealIdx, mealIdx + 2000);
  assert.match(mealBlock, /d\.tags/, 'Meal block must read d.tags for tag pills');
});

// ── 5. Flight schedule display intact ────────────────────────────────────────

test('ItineraryItemCard: flight block still reads origin and destination', () => {
  const flightIdx = itemCard.indexOf('item.itemType === "flight"');
  assert.ok(flightIdx >= 0, 'flight block must exist');
  const flightBlock = itemCard.slice(flightIdx, flightIdx + 8000);
  assert.match(flightBlock, /d\.origin/, 'Flight block must read d.origin (one-way path)');
  assert.match(flightBlock, /d\.destination/, 'Flight block must read d.destination (one-way path)');
});

test('ItineraryItemCard: flight block renders departure and arrival times', () => {
  const flightIdx = itemCard.indexOf('item.itemType === "flight"');
  const flightBlock = itemCard.slice(flightIdx, flightIdx + 8000);
  assert.match(flightBlock, /departure_time|departureTime/, 'Flight block must read departure time');
  assert.match(flightBlock, /arrival_time|arrivalTime/, 'Flight block must read arrival time');
});

test('ItineraryItemCard: flight block renders leg badge (outbound/return)', () => {
  const flightIdx = itemCard.indexOf('item.itemType === "flight"');
  const flightBlock = itemCard.slice(flightIdx, flightIdx + 8000);
  assert.match(flightBlock, /d\.leg/, 'Flight block must read d.leg for outbound/return badge');
  assert.match(flightBlock, /outbound/i, 'Flight block must have outbound badge styling');
});

test('ItineraryItemCard: round-trip flight renders both legs in one card', () => {
  const flightIdx = itemCard.indexOf('item.itemType === "flight"');
  const flightBlock = itemCard.slice(flightIdx, flightIdx + 8000);
  // Canonical round-trip detection + both-leg render in a single card.
  assert.match(flightBlock, /outboundLeg|outbound_leg/, 'must read canonical outbound leg');
  assert.match(flightBlock, /returnLeg|return_leg/, 'must read canonical return leg');
  assert.match(flightBlock, /trip_type|tripType/, 'must detect round_trip via trip_type');
  assert.match(flightBlock, /itinerary-roundtrip-flight/, 'round-trip render has a stable testid');
  // No bare placeholder-only rows — both legs render with route + airline.
  assert.match(flightBlock, /renderLeg/, 'must render each leg with full details');
});

test('ItineraryItemCard: scheduled canonical flight keeps Google Flights CTA', () => {
  const flightIdx = itemCard.indexOf('item.itemType === "flight"');
  const flightBlock = itemCard.slice(flightIdx, flightIdx + 8000);
  assert.match(flightBlock, /googleFlightsSearchUrl|google_flights_search_url/, 'must read canonical Google Flights URL');
  assert.match(flightBlock, /itinerary-google-flights-cta/, 'must render a Google Flights CTA');
});

// ── 6. Trip Ideas remains shortlist-only ─────────────────────────────────────

test('TripIdeasPanel uses fetchTripIdeas (concierge_idea scoped endpoint)', () => {
  assert.match(
    tripIdeasSrc,
    /fetchTripIdeas/,
    'TripIdeasPanel must use fetchTripIdeas for shortlist-only display',
  );
  assert.doesNotMatch(
    tripIdeasSrc,
    /fetchTripItems/,
    'TripIdeasPanel must not call fetchTripItems (all-candidates endpoint)',
  );
});

// ── 7. No AI Concierge for finalized day display ─────────────────────────────

test('ItineraryItemCard does not reference AI Concierge or concierge search', () => {
  assert.doesNotMatch(
    itemCard,
    /searchAttractionsViaConcierge|searchRestaurantsViaConcierge|concierge.*search/i,
    'ItineraryItemCard must not use AI Concierge for finalized day display',
  );
});

test('TripBuilder does not use AI Concierge for finalized itinerary display', () => {
  assert.doesNotMatch(
    tripBuilderSrc,
    /searchAttractionsViaConcierge|searchRestaurantsViaConcierge/,
    'TripBuilder must not call AI Concierge search for hydration',
  );
});

// ── 8. addHotelToDay: exists and preserves details ──────────────────────────

test('api.ts exports addHotelToDay function', () => {
  assert.match(
    apiSrc,
    /export async function addHotelToDay\(/,
    'api.ts must export addHotelToDay',
  );
});

test('addHotelToDay spreads item.details into the persisted payload', () => {
  const fnIdx = apiSrc.indexOf('export async function addHotelToDay(');
  assert.ok(fnIdx >= 0, 'addHotelToDay must exist');
  const fnBlock = apiSrc.slice(fnIdx, fnIdx + 600);
  assert.match(
    fnBlock,
    /\.\.\.\s*d\b|\.\.\.\s*item\.details/,
    'addHotelToDay must spread item details into the payload (not strip them)',
  );
});

test('addHotelToDay sends item_type: "hotel"', () => {
  const fnIdx = apiSrc.indexOf('export async function addHotelToDay(');
  const fnBlock = apiSrc.slice(fnIdx, fnIdx + 600);
  assert.match(fnBlock, /item_type.*hotel|"hotel"/, 'addHotelToDay must send item_type hotel');
});

// ── 9. TripBuilder uses addHotelToDay for hotel candidates ──────────────────

test('TripBuilder imports addHotelToDay from api', () => {
  assert.match(
    tripBuilderSrc,
    /addHotelToDay/,
    'TripBuilder must import addHotelToDay',
  );
});

test('TripBuilder calls addHotelToDay when item.itemType === "hotel"', () => {
  assert.match(
    tripBuilderSrc,
    /item\.itemType === "hotel"[\s\S]{0,600}addHotelToDay/,
    'TripBuilder must call addHotelToDay in the hotel branch of handleAddCandidateToItinerary',
  );
});

test('TripBuilder no longer falls through to createItem for hotel candidates', () => {
  // The hotel branch must come before the else createItem fallback.
  const hotelBranchIdx = tripBuilderSrc.indexOf('item.itemType === "hotel"');
  const createItemInHandlerIdx = tripBuilderSrc.indexOf(
    'createItem(tripId, targetDay.id',
    tripBuilderSrc.indexOf('handleAddCandidateToItinerary'),
  );
  assert.ok(hotelBranchIdx >= 0, 'hotel branch must exist');
  assert.ok(createItemInHandlerIdx >= 0, 'createItem fallback must exist');
  // The hotel-specific branch must appear before the createItem fallback line
  assert.ok(
    hotelBranchIdx < createItemInHandlerIdx,
    'Hotel branch must be evaluated before createItem fallback in handleAddCandidateToItinerary',
  );
});

// ── 10. Generic price row still guards cashPrice > 0 ────────────────────────

test('ItineraryItemCard: generic price row guards cashPrice > 0 (no $0 display)', () => {
  assert.match(
    itemCard,
    /cashPrice\s*!=\s*null\s*&&\s*item\.cashPrice\s*>\s*0/,
    'Generic price row must check cashPrice > 0 to prevent $0 display for discovery hotels',
  );
});

// ── 11. Payload-level detail preservation: addAttractionToDay ───────────────
// These check the actual field-by-field mapping in the API function body so
// that a future refactor cannot silently drop fields from the persisted payload.

test('addAttractionToDay payload maps attraction.rating into details', () => {
  const fnIdx = apiSrc.indexOf('export async function addAttractionToDay(');
  const fnEnd = apiSrc.indexOf('\nexport ', fnIdx + 1);
  const fn = apiSrc.slice(fnIdx, fnEnd > fnIdx ? fnEnd : fnIdx + 800);
  assert.match(fn, /rating:\s*attraction\.rating/, 'addAttractionToDay must map attraction.rating into details');
});

test('addAttractionToDay payload maps attraction.tags into details', () => {
  const fnIdx = apiSrc.indexOf('export async function addAttractionToDay(');
  const fnEnd = apiSrc.indexOf('\nexport ', fnIdx + 1);
  const fn = apiSrc.slice(fnIdx, fnEnd > fnIdx ? fnEnd : fnIdx + 800);
  assert.match(fn, /tags:\s*attraction\.tags/, 'addAttractionToDay must map attraction.tags into details');
});

test('addAttractionToDay payload maps attraction.category into details', () => {
  const fnIdx = apiSrc.indexOf('export async function addAttractionToDay(');
  const fnEnd = apiSrc.indexOf('\nexport ', fnIdx + 1);
  const fn = apiSrc.slice(fnIdx, fnEnd > fnIdx ? fnEnd : fnIdx + 800);
  assert.match(fn, /category:\s*attraction\.category/, 'addAttractionToDay must map attraction.category into details');
});

test('addAttractionToDay payload maps numReviews (num_reviews) into details', () => {
  const fnIdx = apiSrc.indexOf('export async function addAttractionToDay(');
  const fnEnd = apiSrc.indexOf('\nexport ', fnIdx + 1);
  const fn = apiSrc.slice(fnIdx, fnEnd > fnIdx ? fnEnd : fnIdx + 800);
  assert.match(fn, /num_reviews:\s*attraction\.numReviews/, 'addAttractionToDay must map numReviews into details');
});

test('addAttractionToDay payload maps attraction.address into details', () => {
  const fnIdx = apiSrc.indexOf('export async function addAttractionToDay(');
  const fnEnd = apiSrc.indexOf('\nexport ', fnIdx + 1);
  const fn = apiSrc.slice(fnIdx, fnEnd > fnIdx ? fnEnd : fnIdx + 800);
  assert.match(fn, /address:\s*attraction\.address/, 'addAttractionToDay must map attraction.address into details');
});

// ── 12. Payload-level detail preservation: addRestaurantToDay ───────────────

test('addRestaurantToDay payload maps restaurant.cuisine into details', () => {
  const fnIdx = apiSrc.indexOf('export async function addRestaurantToDay(');
  const fnEnd = apiSrc.indexOf('\nexport ', fnIdx + 1);
  const fn = apiSrc.slice(fnIdx, fnEnd > fnIdx ? fnEnd : fnIdx + 800);
  assert.match(fn, /cuisine:\s*restaurant\.cuisine/, 'addRestaurantToDay must map restaurant.cuisine into details');
});

test('addRestaurantToDay payload maps restaurant.rating into details', () => {
  const fnIdx = apiSrc.indexOf('export async function addRestaurantToDay(');
  const fnEnd = apiSrc.indexOf('\nexport ', fnIdx + 1);
  const fn = apiSrc.slice(fnIdx, fnEnd > fnIdx ? fnEnd : fnIdx + 800);
  assert.match(fn, /rating:\s*restaurant\.rating/, 'addRestaurantToDay must map restaurant.rating into details');
});

test('addRestaurantToDay payload maps priceLevel (price_level) into details', () => {
  const fnIdx = apiSrc.indexOf('export async function addRestaurantToDay(');
  const fnEnd = apiSrc.indexOf('\nexport ', fnIdx + 1);
  const fn = apiSrc.slice(fnIdx, fnEnd > fnIdx ? fnEnd : fnIdx + 800);
  assert.match(fn, /price_level:\s*restaurant\.priceLevel/, 'addRestaurantToDay must map priceLevel into details');
});

test('addRestaurantToDay payload maps restaurant.tags into details', () => {
  const fnIdx = apiSrc.indexOf('export async function addRestaurantToDay(');
  const fnEnd = apiSrc.indexOf('\nexport ', fnIdx + 1);
  const fn = apiSrc.slice(fnIdx, fnEnd > fnIdx ? fnEnd : fnIdx + 800);
  assert.match(fn, /tags:\s*restaurant\.tags/, 'addRestaurantToDay must map restaurant.tags into details');
});

// ── 13. Handler routing: attraction/restaurant panels use detail-preserving helpers ──

test('TripBuilder attraction candidate panel wires to handleAddAttractionToItinerary (not handleAddCandidateToItinerary)', () => {
  // The attraction panel passes onAddAttraction, which is wired to handleAddAttractionToItinerary.
  // This guarantees addAttractionToDay is called (detail-preserving), not createItem (stripping).
  assert.match(
    tripBuilderSrc,
    /onAddAttraction=\{handleAddAttractionToItinerary\}/,
    'Attraction candidate panel must wire onAddAttraction to handleAddAttractionToItinerary',
  );
});

test('TripBuilder restaurant candidate panel wires to handleAddRestaurantToItinerary (not handleAddCandidateToItinerary)', () => {
  assert.match(
    tripBuilderSrc,
    /onAddRestaurant=\{handleAddRestaurantToItinerary\}/,
    'Restaurant candidate panel must wire onAddRestaurant to handleAddRestaurantToItinerary',
  );
});

test('handleAddAttractionToItinerary calls addAttractionToDay (not createItem)', () => {
  const fnIdx = tripBuilderSrc.indexOf('const handleAddAttractionToItinerary');
  const fnEnd = tripBuilderSrc.indexOf('}, [days', fnIdx);
  const fn = tripBuilderSrc.slice(fnIdx, fnEnd > fnIdx ? fnEnd + 50 : fnIdx + 600);
  assert.match(fn, /addAttractionToDay/, 'handleAddAttractionToItinerary must call addAttractionToDay');
  assert.doesNotMatch(fn, /createItem/, 'handleAddAttractionToItinerary must not call createItem');
});

test('handleAddRestaurantToItinerary calls addRestaurantToDay (not createItem)', () => {
  const fnIdx = tripBuilderSrc.indexOf('const handleAddRestaurantToItinerary');
  const fnEnd = tripBuilderSrc.indexOf('}, [days', fnIdx);
  const fn = tripBuilderSrc.slice(fnIdx, fnEnd > fnIdx ? fnEnd + 50 : fnIdx + 600);
  assert.match(fn, /addRestaurantToDay/, 'handleAddRestaurantToItinerary must call addRestaurantToDay');
  assert.doesNotMatch(fn, /createItem/, 'handleAddRestaurantToItinerary must not call createItem');
});

// ── 14. Hotel proximity: both area badge and proximity label shown together ──

test('ItineraryItemCard: hotel proximity section shows proximityLabel even when areaLabel present (no !areaLabel guard)', () => {
  // Before this fix, the guard was `proximityLabel && !areaLabel`, which suppressed
  // the proximity label whenever an area badge was also available.  After the fix,
  // both are shown unless the text is the same.
  assert.doesNotMatch(
    itemCard,
    /proximityLabel && !areaLabel/,
    'Hotel proximity section must not suppress proximityLabel with !areaLabel guard',
  );
});

test('ItineraryItemCard: hotel proximity section guards against duplicate text (case-insensitive)', () => {
  assert.match(
    itemCard,
    /proximityLabel.*toLowerCase\(\).*areaLabel.*toLowerCase\(\)|areaLabel.*toLowerCase\(\).*proximityLabel.*toLowerCase\(\)/,
    'Hotel proximity section must skip rendering proximityLabel when it matches areaLabel text',
  );
});
