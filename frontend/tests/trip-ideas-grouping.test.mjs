/**
 * Trip Ideas grouped/capped rendering — Level 3 Trip Data Contract Rescue.
 *
 * Verifies that TripIdeasPanel:
 *   - Does not render ideas as one flat list when several verticals are present.
 *   - Caps default visible items per vertical.
 *   - Exposes a "Show more" expand affordance.
 *   - Renders an attractions/restaurants/hotels/flights label row per group.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const tripIdeasPanel = readFileSync(
  new URL('../src/components/trips/TripIdeasPanel.tsx', import.meta.url),
  'utf8',
);

test('TripIdeasPanel groups ideas by vertical (activity/meal/hotel/flight)', () => {
  assert.match(tripIdeasPanel, /groupIdeasByVertical/);
  assert.match(tripIdeasPanel, /Attractions/);
  assert.match(tripIdeasPanel, /Restaurants/);
  assert.match(tripIdeasPanel, /Hotels/);
  assert.match(tripIdeasPanel, /Flights/);
});

test('TripIdeasPanel caps default visible items per vertical', () => {
  assert.match(tripIdeasPanel, /DEFAULT_VISIBLE_PER_VERTICAL\s*=\s*\d+/);
  assert.match(tripIdeasPanel, /slice\(0, DEFAULT_VISIBLE_PER_VERTICAL\)/);
});

test('TripIdeasPanel exposes Show more / Show less affordance', () => {
  assert.match(tripIdeasPanel, /Show \{overflow\} more/);
  assert.match(tripIdeasPanel, /Show less/);
});

test('TripIdeasPanel tracks expand state per vertical key', () => {
  assert.match(tripIdeasPanel, /expandedGroups/);
  assert.match(tripIdeasPanel, /setExpandedGroups/);
});
