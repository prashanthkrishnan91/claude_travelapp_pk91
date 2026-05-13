/**
 * Trip workspace flight cards — canonical Duffel/Google Flights contract.
 *
 * Guards the display-layer changes introduced to make TripBuilder flight cards
 * render persisted canonical FlightItineraryOffer rows correctly:
 *
 *  1. FlightCandidateCard reads google_flights_search_url (→ googleFlightsSearchUrl)
 *  2. FlightCandidateCard reads booking_link.url (→ bookingLink.url)
 *  3. Canonical SEARCH_REDIRECT renders "Google Flights", NOT "Book"
 *  4. Google Flights CTA is an external <a> link (not a button)
 *  5. + Add button remains regardless of booking link type
 *  6. Canonical offer with outbound_leg uses airline/route/time from leg.segments[0]
 *  7. Round-trip canonical offer reads return_leg (→ returnLeg) when present
 *  8. Legacy flight rows (bookingUrl) still render without regression
 *  9. Price reads cashPrice (canonical) with fallback to price (legacy)
 * 10. bookingLink.kind === "search_redirect_only" also triggers Google Flights CTA
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const src = readFileSync(
  new URL('../src/components/trips/TripBuilder.tsx', import.meta.url),
  'utf8',
);

// ── 1. FlightCandidateCard reads googleFlightsSearchUrl ───────────────────────

test('FlightCandidateCard reads d.googleFlightsSearchUrl (canonical toCamel field)', () => {
  assert.match(
    src,
    /googleFlightsSearchUrl/,
    'FlightCandidateCard must read d.googleFlightsSearchUrl',
  );
});

test('FlightCandidateCard reads d.google_flights_search_url (snake_case fallback)', () => {
  assert.match(
    src,
    /google_flights_search_url/,
    'FlightCandidateCard must include snake_case fallback google_flights_search_url',
  );
});

// ── 2. FlightCandidateCard reads booking_link.url ────────────────────────────

test('FlightCandidateCard reads bookingLink.url (canonical booking link object)', () => {
  assert.match(
    src,
    /bookingLinkObj\.url/,
    'FlightCandidateCard must read url from bookingLinkObj',
  );
});

test('FlightCandidateCard reads d.bookingLink (toCamel canonical field)', () => {
  assert.match(
    src,
    /d\.bookingLink/,
    'FlightCandidateCard must read d.bookingLink',
  );
});

// ── 3. Canonical SEARCH_REDIRECT renders "Google Flights", not "Book" ─────────

test('FlightCandidateCard renders "Google Flights" label for SEARCH_REDIRECT', () => {
  assert.match(
    src,
    /Google Flights/,
    'FlightCandidateCard must show "Google Flights" label for canonical offers',
  );
});

test('FlightCandidateCard guards Google Flights CTA on isSearchRedirect', () => {
  assert.match(
    src,
    /isSearchRedirect/,
    'FlightCandidateCard must gate Google Flights CTA on isSearchRedirect flag',
  );
});

test('FlightCandidateCard detects link_type === "search_redirect"', () => {
  assert.match(
    src,
    /=== "search_redirect"/,
    'isSearchRedirect must check for "search_redirect" link_type',
  );
});

test('FlightCandidateCard detects kind === "search_redirect_only"', () => {
  assert.match(
    src,
    /=== "search_redirect_only"/,
    'isSearchRedirect must check for "search_redirect_only" booking_link.kind',
  );
});

// ── 4. Google Flights CTA is an external link ────────────────────────────────

test('Google Flights CTA uses target="_blank" (external link)', () => {
  // The CTA must open externally — source contains target="_blank" near Google Flights
  const ctaRegion = src.slice(src.indexOf('googleFlightsUrl && isSearchRedirect'));
  assert.match(
    ctaRegion,
    /target="_blank"/,
    'Google Flights CTA must use target="_blank"',
  );
});

test('Google Flights CTA title says "Search on Google Flights" (not booking)', () => {
  assert.match(
    src,
    /title="Search on Google Flights"/,
    'Google Flights CTA must have a clear search-only title attribute',
  );
});

// ── 5. Add button still present ───────────────────────────────────────────────

test('FlightCandidateCard still renders + Add button regardless of booking link', () => {
  assert.match(
    src,
    /data-testid="flight-add-btn"/,
    'FlightCandidateCard must include flight-add-btn for Add to itinerary',
  );
});

test('RoundTripFlightCard still renders Add Round Trip button', () => {
  assert.match(
    src,
    /Add Round Trip/,
    'RoundTripFlightCard must keep "Add Round Trip" button',
  );
});

// ── 6. Canonical outbound_leg → airline/flightNum from segments[0] ───────────

test('FlightLegRow derives airline from leg.segments[0] (canonical leg has no top-level airline)', () => {
  assert.match(
    src,
    /firstSeg\?\.airline/,
    'FlightLegRow must derive airline from segments[0] when not at leg level',
  );
});

test('FlightLegRow derives flightNum from segments[0].flightNumber', () => {
  assert.match(
    src,
    /firstSeg\?\.flightNumber/,
    'FlightLegRow must try segments[0].flightNumber for canonical legs',
  );
});

test('FlightLegRow derives flightNum from segments[0].flight_number (snake_case fallback)', () => {
  assert.match(
    src,
    /firstSeg\?\.flight_number/,
    'FlightLegRow must try segments[0].flight_number as fallback',
  );
});

// ── 7. Round-trip: returnLeg read from canonical return_leg ─────────────────

test('RoundTripFlightCard reads d.returnLeg (toCamel of return_leg)', () => {
  assert.match(
    src,
    /d\.returnLeg/,
    'RoundTripFlightCard must read d.returnLeg for canonical rows',
  );
});

test('RoundTripFlightCard reads d.outboundLeg (toCamel of outbound_leg)', () => {
  assert.match(
    src,
    /d\.outboundLeg/,
    'RoundTripFlightCard must read d.outboundLeg for canonical rows',
  );
});

test('RoundTripFlightCard also accepts d.outbound_leg (snake_case fallback)', () => {
  assert.match(
    src,
    /d\.outbound_leg/,
    'RoundTripFlightCard must include outbound_leg snake_case fallback',
  );
});

// ── 8. Legacy row compatibility ───────────────────────────────────────────────

test('FlightCandidateCard still falls back to d.bookingUrl for non-canonical legacy rows', () => {
  assert.match(
    src,
    /legacyBookingUrl/,
    'FlightCandidateCard must preserve legacyBookingUrl path for old rows',
  );
});

test('RoundTripFlightCard still falls back to d.outbound for legacy rows', () => {
  // d.outbound is the legacy key; canonical is d.outboundLeg
  assert.match(
    src,
    /d\.outbound as Record/,
    'RoundTripFlightCard must preserve d.outbound fallback for legacy rows',
  );
});

test('RoundTripFlightCard still falls back to d.returnFlight/d.return_flight', () => {
  assert.match(
    src,
    /d\.returnFlight/,
    'RoundTripFlightCard must preserve d.returnFlight legacy fallback',
  );
});

// ── 9. Price: cashPrice canonical, price legacy ───────────────────────────────

test('FlightCandidateCard reads d.cashPrice (canonical toCamel of cash_price)', () => {
  assert.match(
    src,
    /d\.cashPrice/,
    'FlightCandidateCard must read d.cashPrice (canonical)',
  );
});

test('RoundTripFlightCard reads d.cashPrice for canonical total price', () => {
  // The round-trip card now derives totalPrice from cashPrice first
  const rtSection = src.slice(src.indexOf('function RoundTripFlightCard('));
  assert.match(
    rtSection,
    /d\.cashPrice/,
    'RoundTripFlightCard must read d.cashPrice for canonical total price',
  );
});

test('FlightCandidateCard falls back to d.price for legacy rows', () => {
  assert.match(
    src,
    /d\.price as number/,
    'FlightCandidateCard must fall back to d.price for legacy rows',
  );
});

// ── 10. RoundTripFlightCard has Google Flights CTA ───────────────────────────

test('RoundTripFlightCard also renders Google Flights CTA for canonical offers', () => {
  const rtSection = src.slice(src.indexOf('function RoundTripFlightCard('));
  assert.match(
    rtSection,
    /rtGoogleFlightsUrl && rtIsSearchRedirect/,
    'RoundTripFlightCard must include Google Flights CTA for SEARCH_REDIRECT',
  );
});
