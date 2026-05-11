/**
 * Global Explore Shell v1 — Stage 2A Slice 1
 *
 * Focused structural tests verifying:
 * 1. /explore route exists as a Next.js page.
 * 2. ExploreShell exports and renders a 4-vertical grid.
 * 3. Sidebar and MobileNav both expose the Explore nav link.
 * 4. Restaurants vertical flow uses searchRestaurants (trip-optional, real Google Places).
 * 5. Attractions / Hotels / Flights verticals are deferred and carry polished deferred states.
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

test('ExploreShell heading says Explore with no-trip message', () => {
  assert.match(exploreShell, /no trip required/i);
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

test('RestaurantExploreFlow result cards show a non-clickable actions-pending badge', () => {
  assert.match(restaurantFlow, /data-testid="actions-pending-badge"/);
  assert.match(restaurantFlow, /Save & add/);
});

test('RestaurantExploreFlow does not call mock/sample data paths', () => {
  assert.doesNotMatch(restaurantFlow, /mock/i);
  assert.doesNotMatch(restaurantFlow, /sample/i);
  assert.doesNotMatch(restaurantFlow, /hardcoded/i);
});

// ── 5. Attractions — deferred state ────────────────────────────────────────

test('AttractionExploreFlow shows deferred state after form submission', () => {
  assert.match(attractionFlow, /data-testid="attraction-deferred-state"/);
});

test('AttractionExploreFlow does not import or call any live search function', () => {
  // Must not import from api or call any live route
  assert.doesNotMatch(attractionFlow, /import.*from "@\/lib\/api"/);
  assert.doesNotMatch(attractionFlow, /callConcierge/);
  assert.doesNotMatch(attractionFlow, /apiFetch/);
});

test('AttractionExploreFlow explains that attractions search is coming soon', () => {
  assert.match(attractionFlow, /coming soon/i);
});

test('AttractionExploreFlow deferred state has role=status for accessibility', () => {
  assert.match(attractionFlow, /role="status"/);
});

// ── 6. Hotels — structured form + deferred state ───────────────────────────

test('HotelExploreFlow shows hotel-deferred-state testid after submission', () => {
  assert.match(hotelFlow, /data-testid="hotel-deferred-state"/);
});

test('HotelExploreFlow collects destination, checkIn, checkOut, guests', () => {
  assert.match(hotelFlow, /checkIn/);
  assert.match(hotelFlow, /checkOut/);
  assert.match(hotelFlow, /guests/);
  assert.match(hotelFlow, /destination/);
});

test('HotelExploreFlow builds ExploreResultContext with hotel vertical', () => {
  assert.match(hotelFlow, /vertical: "hotels"/);
  assert.match(hotelFlow, /dates: \{ checkIn/);
  assert.match(hotelFlow, /guests: form\.guests/);
});

test('HotelExploreFlow does not call searchHotels (mock-backed, quarantined)', () => {
  assert.doesNotMatch(hotelFlow, /searchHotels/);
  assert.doesNotMatch(hotelFlow, /apiFetch/);
});

test('HotelExploreFlow deferred state explains live hotel search is coming soon', () => {
  assert.match(hotelFlow, /coming soon/i);
});

// ── 7. Flights — structured form + deferred state ──────────────────────────

test('FlightExploreFlow shows flight-deferred-state testid after submission', () => {
  assert.match(flightFlow, /data-testid="flight-deferred-state"/);
});

test('FlightExploreFlow collects origin, destination, departure, passengers, cabinClass', () => {
  assert.match(flightFlow, /origin/);
  assert.match(flightFlow, /destination/);
  assert.match(flightFlow, /departure/);
  assert.match(flightFlow, /passengers/);
  assert.match(flightFlow, /cabinClass/);
});

test('FlightExploreFlow validates IATA airport codes', () => {
  assert.match(flightFlow, /validateIata/);
  assert.match(flightFlow, /\[A-Za-z\]\{3\}/);
});

test('FlightExploreFlow builds ExploreResultContext with flight vertical', () => {
  assert.match(flightFlow, /vertical: "flights"/);
  assert.match(flightFlow, /origin: form\.origin/);
  assert.match(flightFlow, /passengers: form\.passengers/);
  assert.match(flightFlow, /cabinClass: form\.cabinClass/);
});

test('FlightExploreFlow does not call searchFlights (mock-backed)', () => {
  assert.doesNotMatch(flightFlow, /searchFlights/);
  assert.doesNotMatch(flightFlow, /apiFetch/);
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

test('HotelExploreFlow deferred copy does not frame create-trip as the required Explore path', () => {
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

test('AttractionExploreFlow source documents why it is deferred', () => {
  // The file must explain which route was removed and why it is deferred
  assert.match(attractionFlow, /\/search\/attractions/);
  assert.match(attractionFlow, /tripId/);
});

test('HotelExploreFlow source documents mock-backed quarantine reason', () => {
  assert.match(hotelFlow, /BLOCK_LEGACY_PRODUCT_MOCK/);
});

test('FlightExploreFlow source documents mock-backed quarantine reason', () => {
  assert.match(flightFlow, /BLOCK_LEGACY_PRODUCT_MOCK/);
});
