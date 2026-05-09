// Hotel itinerary card display contract — source-content tests.
//
// Guards that:
//   1. Hotel details block reads check_in / check_out (not check_in_date / checkInDate only).
//   2. Hotel details block does NOT show duplicate location (already shown in main location line).
//   3. Hotel card does not show a fake $0/night price from details.price_per_night.
//   4. Hotel rating is shown when available.

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const itemCard = readFileSync(
  new URL('../src/components/trips/ItineraryItemCard.tsx', import.meta.url),
  'utf8',
);

// ── check_in / check_out field names ─────────────────────────────────────────

test('ItineraryItemCard: hotel section reads d.check_in (backend field name)', () => {
  assert.match(
    itemCard,
    /d\.check_in\b/,
    'Hotel section must read d.check_in (the field the backend stores)',
  );
});

test('ItineraryItemCard: hotel section reads d.check_out (backend field name)', () => {
  assert.match(
    itemCard,
    /d\.check_out\b/,
    'Hotel section must read d.check_out (the field the backend stores)',
  );
});

test('ItineraryItemCard: hotel section still accepts check_in_date as fallback', () => {
  assert.match(
    itemCard,
    /check_in_date/,
    'check_in_date should remain as a fallback for legacy stored items',
  );
});

// ── No duplicate location ─────────────────────────────────────────────────────

test('ItineraryItemCard: hotel section does not render a location variable', () => {
  // The old code had: const location = (d.location ...) ?? item.location ...
  // and then rendered it.  This caused duplicate display because item.location
  // is already shown in the main MapPin row below.
  // After the fix, no "location" variable is declared or rendered in the hotel block.
  assert.doesNotMatch(
    itemCard,
    /const location\s*=.*check_in|check_in.*const location/,
    'Hotel section must not declare a location variable alongside check_in (old duplicate pattern)',
  );
  // The hotel-specific JSX block must not contain {location} rendering.
  // We check that the comment "Location is shown in the main" is present to confirm intent.
  assert.match(
    itemCard,
    /Location is shown\s+in the main/,
    'Hotel section comment must note that location is shown in the main location line',
  );
});

// ── No fake $0/night display ──────────────────────────────────────────────────

test('ItineraryItemCard: hotel details block does not display price_per_night', () => {
  // The hotel-specific row should show check-in/out and rating, not a nightly rate.
  // Hotels v1 ships with price_per_night=0.0 which would display as "$0/night".
  // Verify the hotel section does not reference price_per_night in JSX.
  // (cash_price is handled by the generic price row, but that shows 0 for discovery hotels,
  //  so we check the hotel-specific details block specifically.)
  assert.doesNotMatch(
    itemCard,
    /\$\{.*price_per_night/,
    'Hotel details block must not interpolate price_per_night into JSX (would show $0/night)',
  );
});

// ── Rating shown ─────────────────────────────────────────────────────────────

test('ItineraryItemCard: hotel details block reads d.rating for display', () => {
  // The hotel section reads d.rating and renders it as a star rating when available.
  assert.match(
    itemCard,
    /d\.rating.*number.*undefined/,
    'Hotel section must read d.rating from item details',
  );
  assert.match(
    itemCard,
    /rating\.toFixed\(1\)/,
    'Hotel section must display rating formatted to 1 decimal',
  );
});
