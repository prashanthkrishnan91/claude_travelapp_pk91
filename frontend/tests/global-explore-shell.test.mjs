/**
 * Global Explore Shell v1 — Stage 2A Slice 1
 *
 * Focused structural tests verifying:
 * 1. /explore route exists as a Next.js page.
 * 2. ExploreShell exports and renders a 4-vertical grid.
 * 3. Sidebar and MobileNav both expose the Explore nav link.
 * 4. Restaurants vertical flow uses searchRestaurants (trip-optional, real Google Places).
 * 5. Attractions / Hotels verticals use live tripless Concierge discovery; Flights is deferred.
 * 6. Each result context carries action-ready fields for Slice 2 (vertical, destination,
 *    dates, origin, guests, passengers, providerIdentity, originalPayload).
 * 7. No trip creation gate in any Explore component.
 * 8. tripCandidates.ts and TripBuilder are untouched.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

// ── Source files ──────────────────────────────────────────────────────────────

const explorePage = readFileSync(
  new URL('../src/app/explore/page.tsx', import.meta.url), 'utf8');

const exploreShell = readFileSync(
  new URL('../src/components/explore/ExploreShell.tsx', import.meta.url), 'utf8');

const exploreTypes = readFileSync(
  new URL('../src/components/explore/types.ts', import.meta.url), 'utf8');

const restaurantFlow = readFileSync(
  new URL('../src/components/explore/RestaurantExploreFlow.tsx', import.meta.url), 'utf8');

const attractionFlow = readFileSync(
  new URL('../src/components/explore/AttractionExploreFlow.tsx', import.meta.url), 'utf8');

const hotelFlow = readFileSync(
  new URL('../src/components/explore/HotelExploreFlow.tsx', import.meta.url), 'utf8');

const flightFlow = readFileSync(
  new URL('../src/components/explore/FlightExploreFlow.tsx', import.meta.url), 'utf8');

const sidebar = readFileSync(
  new URL('../src/components/layout/Sidebar.tsx', import.meta.url), 'utf8');

const mobileNav = readFileSync(
  new URL('../src/components/layout/MobileNav.tsx', import.meta.url), 'utf8');

const tripCandidates = readFileSync(
  new URL('../src/lib/tripCandidates.ts', import.meta.url), 'utf8');

const tripBuilder = readFileSync(
  new URL('../src/components/trips/TripBuilder.tsx', import.meta.url), 'utf8');

const apiTs = readFileSync(
  new URL('../src/lib/api.ts', import.meta.url), 'utf8');

// ── 1. Route / navigation ──────────────────────────────────────────────────

test('explore page exists and imports ExploreShell', () => {
  assert.match(explorePage, /from "@\/components\/explore\/ExploreShell"/);
  assert.match(explorePage, /ExploreShell/);
});

test('explore page exports default page component', () => {
  assert.match(explorePage, /export default function ExplorePage/);
});

test('sidebar includes Explore link pointing to /explore', () => {
  assert.match(sidebar, /Explore/);
  assert.match(sidebar, /\/explore/);
  assert.match(sidebar, /Compass/);
});

test('mobile nav includes Explore link pointing to /explore', () => {
  assert.match(mobileNav, /Explore/);
  assert.match(mobileNav, /\/explore/);
  assert.match(mobileNav, /Compass/);
});

// ── 2. ExploreShell — four-vertical grid ──────────────────────────────────

test('ExploreShell exports named ExploreShell function', () => {
  assert.match(exploreShell, /export function ExploreShell/);
});

test('ExploreShell renders all four verticals', () => {
  assert.match(exploreShell, /flights/);
  assert.match(exploreShell, /hotels/);
  assert.match(exploreShell, /restaurants/);
  assert.match(exploreShell, /attractions/);
});

test('ExploreShell uses explore-home testid for the landing grid', () => {
  assert.match(exploreShell, /data-testid="explore-home"/);
});

test('ExploreShell uses explore-vertical-grid testid', () => {
  assert.match(exploreShell, /data-testid="explore-vertical-grid"/);
});

test('ExploreShell vertical cards have testids for each vertical', () => {
  assert.match(exploreShell, /data-testid=\{`vertical-card-\$\{/);
});

test('ExploreShell active vertical shows back/close path', () => {
  assert.match(exploreShell, /ArrowLeft/);
  assert.match(exploreShell, /Back to Explore|aria-label="Back to Explore"/);
});

test('ExploreShell only one vertical flow shown at a time (state-driven)', () => {
  assert.match(exploreShell, /const \[active, setActive\] = useState/);
  assert.match(exploreShell, /if \(active\)/);
});

test('ExploreShell does not reference tripId or TripBuilder', () => {
  assert.doesNotMatch(exploreShell, /tripId/);
  assert.doesNotMatch(exploreShell, /TripBuilder/);
});

test('ExploreShell hero uses plain browse copy (no internal trip-state language)', () => {
  assert.match(exploreShell, /Browse flights, hotels, restaurants, and attractions/i);
  assert.doesNotMatch(exploreShell, /no trip required/i);
});

// ── 3. ExploreResultContext types ──────────────────────────────────────────

test('ExploreResultContext carries all Slice-2 action-ready fields', () => {
  assert.match(exploreTypes, /vertical: ExploreVertical/);
  assert.match(exploreTypes, /destination: string/);
  assert.match(exploreTypes, /dates\?:/);
  assert.match(exploreTypes, /origin\?:/);
  assert.match(exploreTypes, /guests\?:/);
  assert.match(exploreTypes, /passengers\?:/);
  assert.match(exploreTypes, /providerIdentity\?:/);
  assert.match(exploreTypes, /originalPayload:/);
});

test('ExploreVertical type covers all four verticals', () => {
  assert.match(exploreTypes, /"flights"/);
  assert.match(exploreTypes, /"hotels"/);
  assert.match(exploreTypes, /"restaurants"/);
  assert.match(exploreTypes, /"attractions"/);
});

// ── 4. Restaurants — safe execution (real Google Places, no trip_id) ───────

test('RestaurantExploreFlow imports searchRestaurants from api', () => {
  assert.match(restaurantFlow, /import.*searchRestaurants.*from "@\/lib\/api"/);
});

test('RestaurantExploreFlow calls searchRestaurants with location only — no tripId, no cuisine param', () => {
  // searchRestaurants(location, date?) — cuisine is not a supported param in Slice 1
  assert.match(restaurantFlow, /searchRestaurants\(dest\)/);
  assert.doesNotMatch(restaurantFlow, /searchRestaurants\(.*tripId/);
  assert.doesNotMatch(restaurantFlow, /searchRestaurants\(.*cuisine/);
});

test('searchRestaurants in api.ts does not require tripId', () => {
  const fnMatch = apiTs.match(/export async function searchRestaurants\([^)]+\)/);
  assert.ok(fnMatch, 'searchRestaurants must be exported');
  assert.doesNotMatch(fnMatch[0], /tripId/);
});

test('RestaurantExploreFlow has no cuisine/vibe input field (not supported by searchRestaurants)', () => {
  // The cuisine field was removed because searchRestaurants(location, date?) does not accept it
  assert.doesNotMatch(restaurantFlow, /placeholder="Cuisine/);
  assert.doesNotMatch(restaurantFlow, /aria-label="Cuisine or vibe"/);
});

test('RestaurantExploreFlow wraps results in RestaurantSearchEnvelope (envelope.restaurants)', () => {
  assert.match(restaurantFlow, /envelope\.restaurants/);
});

test('RestaurantExploreFlow sets restaurant-results testid when results present', () => {
  assert.match(restaurantFlow, /data-testid="restaurant-results"/);
});

test('RestaurantExploreFlow builds ExploreResultContext with vertical=restaurants (Slice 2 ready)', () => {
  assert.match(restaurantFlow, /vertical: "restaurants"/);
  assert.match(restaurantFlow, /destination: lastDestination/);
  assert.match(restaurantFlow, /providerIdentity: r\.providerPlaceId/);
  assert.match(restaurantFlow, /originalPayload: r/);
});

test('RestaurantExploreFlow result cards do not expose a clickable Select action', () => {
  // Slice 1: no fake "Select" button that only logs to console
  assert.doesNotMatch(restaurantFlow, /aria-label=\{`Select /);
  assert.doesNotMatch(restaurantFlow, />Select<\/button>/);
});

test('RestaurantExploreFlow result cards expose ResultActionSheet (Slice 2)', () => {
  // Slice 1 stub replaced by live ResultActionSheet in Slice 2
  assert.ok(restaurantFlow.includes('ResultActionSheet'), 'ResultActionSheet missing from RestaurantExploreFlow');
  assert.ok(!restaurantFlow.includes('actions-pending-badge'), 'Slice-1 stub should be gone in Slice 2');
});

test('RestaurantExploreFlow does not call mock/sample data paths', () => {
  assert.doesNotMatch(restaurantFlow, /mock/i);
  assert.doesNotMatch(restaurantFlow, /sample/i);
  assert.doesNotMatch(restaurantFlow, /hardcoded/i);
});

// ── 5. Attractions — canonical /search/attractions vertical search ─────────

test('AttractionExploreFlow imports searchAttractionsExplore from api', () => {
  assert.match(attractionFlow, /searchAttractionsExplore/);
  assert.match(attractionFlow, /from "@\/lib\/api"/);
});

test('AttractionExploreFlow calls searchAttractionsExplore', () => {
  assert.match(attractionFlow, /searchAttractionsExplore\(/);
});

test('AttractionExploreFlow does not call the AI Concierge route', () => {
  assert.doesNotMatch(attractionFlow, /callConciergeSearch/);
  assert.doesNotMatch(attractionFlow, /\/ai\/concierge\/search/);
});

test('AttractionExploreFlow does not use Tavily / live research', () => {
  assert.doesNotMatch(attractionFlow, /allowLiveResearch/);
  assert.doesNotMatch(attractionFlow, /tavily/i);
  assert.doesNotMatch(attractionFlow, /live.?research/i);
});

test('AttractionExploreFlow renders attraction-results testid when results present', () => {
  assert.match(attractionFlow, /data-testid="attraction-results"/);
});

test('AttractionExploreFlow builds ExploreResultContext with attractions vertical', () => {
  assert.match(attractionFlow, /vertical: "attractions"/);
  assert.match(attractionFlow, /providerIdentity/);
});

test('AttractionExploreFlow uses ResultActionSheet on each card', () => {
  assert.match(attractionFlow, /ResultActionSheet/);
  assert.match(attractionFlow, /import.*ResultActionSheet/);
});

test('AttractionExploreFlow does not require a tripId', () => {
  assert.doesNotMatch(attractionFlow, /tripId(?!.*null)/);
});

// ── 6. Hotels — canonical /search/hotels vertical search ───────────────────

test('HotelExploreFlow calls searchHotelsExplore for hotel discovery', () => {
  assert.match(hotelFlow, /searchHotelsExplore\(/);
});

test('HotelExploreFlow does not call the AI Concierge route', () => {
  assert.doesNotMatch(hotelFlow, /callConciergeSearch/);
  assert.doesNotMatch(hotelFlow, /\/ai\/concierge\/search/);
});

test('HotelExploreFlow collects destination, checkIn, checkOut, guests', () => {
  assert.match(hotelFlow, /checkIn/);
  assert.match(hotelFlow, /checkOut/);
  assert.match(hotelFlow, /guests/);
  assert.match(hotelFlow, /destination/);
});

test('HotelExploreFlow builds ExploreResultContext with hotel vertical and dates', () => {
  assert.match(hotelFlow, /vertical: "hotels"/);
  assert.match(hotelFlow, /dates: \{ checkIn/);
  assert.match(hotelFlow, /guests: lastForm/);
});

test('HotelExploreFlow imports only the canonical searchHotelsExplore helper', () => {
  // The canonical helper is searchHotelsExplore; the legacy mock-era
  // wrapper must not be imported by Explore.
  assert.match(hotelFlow, /import \{ searchHotelsExplore \} from "@\/lib\/api"/);
});

test('HotelExploreFlow wires ResultActionSheet into hotel discovery cards', () => {
  assert.match(hotelFlow, /import.*ResultActionSheet/);
  assert.match(hotelFlow, /<ResultActionSheet/);
});

// ── 7. Flights — live CityAutocomplete form ────────────────────────────────

test('FlightExploreFlow renders live search button (not deferred)', () => {
  assert.match(flightFlow, /data-testid="flight-search-btn"/);
});

test('FlightExploreFlow collects origin, destination, departure, passengers, cabinClass', () => {
  assert.match(flightFlow, /origin/);
  assert.match(flightFlow, /destination/);
  assert.match(flightFlow, /departure/);
  assert.match(flightFlow, /passengers/);
  assert.match(flightFlow, /cabinClass/);
});

test('FlightExploreFlow uses CityAutocomplete for airport selection', () => {
  assert.match(flightFlow, /CityAutocomplete/);
  assert.match(flightFlow, /AirportSelection/);
});

test('FlightExploreFlow builds ExploreResultContext with flight vertical', () => {
  assert.match(flightFlow, /vertical: "flights"/);
  assert.match(flightFlow, /passengers: form\.passengers/);
  assert.match(flightFlow, /cabinClass: form\.cabinClass/);
});

test('FlightExploreFlow calls searchFlightsExplore (live provider, not the mock-backed legacy flight route)', () => {
  assert.match(flightFlow, /searchFlightsExplore/);
  assert.doesNotMatch(flightFlow, /\/search\/flights/);
});

// ── 8. No-trip gate verification ──────────────────────────────────────────

test('ExploreShell has no createTrip requirement or trip gate', () => {
  assert.doesNotMatch(exploreShell, /create.*trip.*first/i);
  assert.doesNotMatch(exploreShell, /need.*trip/i);
});

test('RestaurantExploreFlow does not check for or require a tripId', () => {
  assert.doesNotMatch(restaurantFlow, /tripId/);
  assert.doesNotMatch(restaurantFlow, /TripBuilder/);
});

test('AttractionExploreFlow deferred copy does not frame create-trip as the required Explore path', () => {
  assert.doesNotMatch(attractionFlow, /create a trip to search/i);
});

test('HotelExploreFlow does not frame create-trip as the required Explore path', () => {
  assert.doesNotMatch(hotelFlow, /create a trip to search/i);
});

test('FlightExploreFlow deferred copy does not frame create-trip as the required Explore path', () => {
  assert.doesNotMatch(flightFlow, /create a trip to search/i);
});

// ── 9. tripCandidates and TripBuilder are unchanged ───────────────────────

test('tripCandidates.ts still exports buildTripCandidateBuckets (not modified)', () => {
  assert.match(tripCandidates, /export function buildTripCandidateBuckets\(/);
});

test('TripBuilder does not import from explore component directory', () => {
  assert.doesNotMatch(tripBuilder, /from "@\/components\/explore/);
});

// ── 10. Safe execution rule documentation ─────────────────────────────────

test('AttractionExploreFlow source documents the canonical vertical-search path', () => {
  assert.match(attractionFlow, /searchAttractionsExplore/);
  assert.match(attractionFlow, /\/search\/attractions/);
});

test('HotelExploreFlow source documents the canonical vertical-search path', () => {
  assert.match(hotelFlow, /searchHotelsExplore/);
  assert.match(hotelFlow, /\/search\/hotels/);
  assert.match(hotelFlow, /discovery/i);
});

test('FlightExploreFlow source documents live provider safety invariants', () => {
  // Live FlightExploreFlow must document server-side key safety
  assert.match(flightFlow, /IGNAV_API_KEY.*server-side|server-side.*IGNAV_API_KEY/i);
});
