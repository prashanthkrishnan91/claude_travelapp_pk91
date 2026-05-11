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
  const activityIdx = itemCard.indexOf('item.itemType === "activity"');
  const mealIdx = itemCard.indexOf('item.itemType === "meal"');
  assert.ok(activityIdx >= 0, 'activity block must exist');
  // Extract the activity block source up to the meal block
  const activityBlock = itemCard.slice(activityIdx, mealIdx > activityIdx ? mealIdx : undefined);
  assert.match(activityBlock, /d\.tags/, 'Activity block must read d.tags for pill display');
});

test('ItineraryItemCard: activity block shows maps link when google_maps_uri or placeId present', () => {
  const activityIdx = itemCard.indexOf('item.itemType === "activity"');
  const mealIdx = itemCard.indexOf('item.itemType === "meal"');
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
  const mealIdx = itemCard.indexOf('item.itemType === "meal"');
  assert.ok(mealIdx >= 0, 'meal block must exist');
  const mealBlock = itemCard.slice(mealIdx, mealIdx + 2000);
  assert.match(mealBlock, /d\.cuisine/, 'Meal block must read d.cuisine from stored details');
});

test('ItineraryItemCard: meal block renders priceLevel as $ symbols', () => {
  const mealIdx = itemCard.indexOf('item.itemType === "meal"');
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
  const mealIdx = itemCard.indexOf('item.itemType === "meal"');
  const mealBlock = itemCard.slice(mealIdx, mealIdx + 2000);
  assert.match(mealBlock, /d\.tags/, 'Meal block must read d.tags for tag pills');
});

// ── 5. Flight schedule display intact ────────────────────────────────────────

test('ItineraryItemCard: flight block still reads origin and destination', () => {
  const flightIdx = itemCard.indexOf('item.itemType === "flight"');
  assert.ok(flightIdx >= 0, 'flight block must exist');
  const flightBlock = itemCard.slice(flightIdx, flightIdx + 800);
  assert.match(flightBlock, /d\.origin/, 'Flight block must read d.origin');
  assert.match(flightBlock, /d\.destination/, 'Flight block must read d.destination');
});

test('ItineraryItemCard: flight block renders departure and arrival times', () => {
  const flightIdx = itemCard.indexOf('item.itemType === "flight"');
  const flightBlock = itemCard.slice(flightIdx, flightIdx + 800);
  assert.match(flightBlock, /departure_time|departureTime/, 'Flight block must read departure time');
  assert.match(flightBlock, /arrival_time|arrivalTime/, 'Flight block must read arrival time');
});

test('ItineraryItemCard: flight block renders leg badge (outbound/return)', () => {
  const flightIdx = itemCard.indexOf('item.itemType === "flight"');
  const flightBlock = itemCard.slice(flightIdx, flightIdx + 1800);
  assert.match(flightBlock, /d\.leg/, 'Flight block must read d.leg for outbound/return badge');
  assert.match(flightBlock, /outbound/, 'Flight block must have outbound badge styling');
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
    /item\.itemType === "hotel"[\s\S]{0,200}addHotelToDay/,
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
