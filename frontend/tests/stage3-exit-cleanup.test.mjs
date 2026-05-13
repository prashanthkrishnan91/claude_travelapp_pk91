/**
 * Stage 3 exit cleanup — honest Explore/Saved/ResultActionSheet state.
 *
 * Focused structural tests verifying:
 * 1. ExploreShell vertical cards no longer carry stale "Coming soon" badges
 *    for Flights / Hotels / Attractions (Restaurants never had one).
 * 2. Descriptions stay accurate: no hotel rate/availability/booking claims,
 *    no flight booking claims.
 * 3. ResultActionSheet no longer renders disabled "Coming soon" Add to Trip
 *    or Create Trip buttons.
 * 4. ResultActionSheet still renders save-action-btn (Save/Unsave unchanged).
 * 5. ResultActionSheet shows save-first guidance before save and a
 *    Manage-in-Saved link to /saved after save.
 * 6. No direct trip picker / create-trip modal wiring inside
 *    ResultActionSheet (trip lifecycle stays in SavedShell).
 * 7. HANDOFF and BUILD_QUEUE do not claim "Stage 3 complete" as active state.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, '..');

function read(rel) {
  return readFileSync(path.join(root, rel), 'utf8');
}

const exploreShell = read('src/components/explore/ExploreShell.tsx');
const actionSheet = read('src/components/explore/ResultActionSheet.tsx');
const handoff = read('../docs/ai/HANDOFF.md');
const buildQueue = read('../docs/product/BUILD_QUEUE.md');

// ── 1. ExploreShell badge cleanup ────────────────────────────────────────────

test('ExploreShell no longer renders any "Coming soon" badge string', () => {
  assert.ok(!exploreShell.includes('Coming soon'), 'ExploreShell must not include stale "Coming soon" copy');
});

test('ExploreShell does not assign badge: "Coming soon" on any vertical entry', () => {
  assert.ok(!/badge:\s*"Coming soon"/.test(exploreShell), 'no vertical may carry a Coming soon badge');
});

test('ExploreShell still renders all four vertical cards', () => {
  for (const id of ['flights', 'hotels', 'restaurants', 'attractions']) {
    assert.ok(exploreShell.includes(`id: "${id}"`), `vertical ${id} missing`);
  }
});

// ── 2. Honest descriptions ────────────────────────────────────────────────────

test('ExploreShell hotel description does not claim rates/availability/booking', () => {
  const hotelBlock = exploreShell.slice(
    exploreShell.indexOf('id: "hotels"'),
    exploreShell.indexOf('id: "restaurants"'),
  );
  assert.ok(!/rate|price|availability|book/i.test(hotelBlock),
    'hotel description must not imply rates/availability/booking');
});

test('ExploreShell flight description does not claim booking', () => {
  const flightBlock = exploreShell.slice(
    exploreShell.indexOf('id: "flights"'),
    exploreShell.indexOf('id: "hotels"'),
  );
  assert.ok(!/\bbook(ing)?\b/i.test(flightBlock),
    'flight description must not claim booking');
});

// ── 3. ResultActionSheet — stale deferred actions removed ────────────────────

test('ResultActionSheet does not render add-to-trip-btn (deferred copy gone)', () => {
  assert.ok(!actionSheet.includes('data-testid="add-to-trip-btn"'),
    'stale add-to-trip-btn must be removed');
});

test('ResultActionSheet does not render create-trip-btn (deferred copy gone)', () => {
  assert.ok(!actionSheet.includes('data-testid="create-trip-btn"'),
    'stale create-trip-btn must be removed');
});

test('ResultActionSheet contains no "Coming soon" copy', () => {
  assert.ok(!actionSheet.includes('Coming soon'),
    'stale "Coming soon" copy must be removed from ResultActionSheet');
});

// ── 4. Save/Unsave preserved ─────────────────────────────────────────────────

test('ResultActionSheet still renders save-action-btn', () => {
  assert.ok(actionSheet.includes('data-testid="save-action-btn"'),
    'save-action-btn must still be present');
});

test('ResultActionSheet retains handleSave and handleUnsave behavior', () => {
  assert.ok(actionSheet.includes('async function handleSave'), 'handleSave missing');
  assert.ok(actionSheet.includes('async function handleUnsave'), 'handleUnsave missing');
});

// ── 5. Honest guidance ───────────────────────────────────────────────────────

test('ResultActionSheet shows save-first-hint guidance when not yet saved', () => {
  assert.ok(actionSheet.includes('data-testid="save-first-hint"'),
    'save-first-hint missing');
  assert.ok(/Save first/.test(actionSheet),
    'save-first guidance copy missing');
});

test('ResultActionSheet exposes a Manage-in-Saved link to /saved when saved', () => {
  assert.ok(actionSheet.includes('data-testid="manage-in-saved-link"'),
    'manage-in-saved-link missing');
  assert.ok(actionSheet.includes('href="/saved"'),
    'Manage-in-Saved link must point to /saved');
});

// ── 6. No direct trip-picker / create-trip wiring in ResultActionSheet ──────

test('ResultActionSheet does not import trip-picker / create-trip modal pieces', () => {
  assert.ok(!actionSheet.includes('CreateTripFromSavedModal'),
    'ResultActionSheet must not wire CreateTripFromSavedModal');
  assert.ok(!actionSheet.includes('addSavedItemToTrip'),
    'ResultActionSheet must not call addSavedItemToTrip');
  assert.ok(!actionSheet.includes('createTripFromSavedItem'),
    'ResultActionSheet must not call createTripFromSavedItem');
  assert.ok(!actionSheet.includes('fetchTrips'),
    'ResultActionSheet must not load trips for an inline picker');
});

test('ResultActionSheet does not import TripBuilder or tripCandidates', () => {
  assert.ok(!actionSheet.includes('tripCandidates'),
    'ResultActionSheet must not import tripCandidates');
  assert.ok(!actionSheet.includes('TripBuilder'),
    'ResultActionSheet must not import TripBuilder');
});

// ── 7. Docs honesty ──────────────────────────────────────────────────────────

test('HANDOFF.md does not declare "Stage 3 complete" as active state', () => {
  assert.ok(!/Stage 3 complete/i.test(handoff),
    'HANDOFF must not declare Stage 3 complete');
});

test('HANDOFF.md flags Stage 3 exit/status decision as current work', () => {
  assert.ok(/Stage 3 exit/i.test(handoff),
    'HANDOFF must reference Stage 3 exit decision');
});

test('BUILD_QUEUE.md keeps Stage 3 exit/status decision under Now', () => {
  const nowIdx = buildQueue.indexOf('## Now');
  const nextIdx = buildQueue.indexOf('## Next');
  assert.ok(nowIdx >= 0 && nextIdx > nowIdx, 'Now/Next sections missing');
  const nowBlock = buildQueue.slice(nowIdx, nextIdx);
  assert.ok(/Stage 3 exit/i.test(nowBlock),
    'Stage 3 exit/status decision must remain the active item');
});

test('BUILD_QUEUE.md does not promote Stage 4 to a Now-bullet subject', () => {
  const nowIdx = buildQueue.indexOf('## Now');
  const nextIdx = buildQueue.indexOf('## Next');
  const nowBlock = buildQueue.slice(nowIdx, nextIdx);
  assert.ok(!/^-\s*\*\*Stage 4/im.test(nowBlock),
    'Stage 4 must not be a Now-bullet active item');
});
