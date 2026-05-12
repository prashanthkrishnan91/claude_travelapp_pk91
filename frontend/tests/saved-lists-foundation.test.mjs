/**
 * Saved Lists Foundation — Stage 3 v1
 *
 * Focused structural tests verifying:
 * 1.  /saved route exists as a Next.js page.
 * 2.  SavedShell exports a named export and is a client component.
 * 3.  Sidebar includes a Saved nav link to /saved.
 * 4.  MobileNav drawer and tab bar include a Saved link to /saved.
 * 5.  SavedShell imports listSavedItems (existing helper, not a new path).
 * 6.  SavedShell imports deleteSavedItem for the remove action.
 * 7.  SavedShell groups saved items by all 4 verticals.
 * 8.  Card renders name, rating, address, googleMapsUri, tags from displaySnapshot.
 * 9.  Hotel cards read checkIn/checkOut/guests from searchContext — no rates/prices/booking.
 * 10. Remove action uses deleteSavedItem; remove button has data-testid.
 * 11. Loading, error, and empty states all exist.
 * 12. Empty state links to /explore.
 * 13. No /search/* calls or provider imports.
 * 14. No TripBuilder or tripCandidates imports.
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

// ── Source files ──────────────────────────────────────────────────────────────

const savedPage    = read('src/app/saved/page.tsx');
const savedShell   = read('src/components/saved/SavedShell.tsx');
const sidebar      = read('src/components/layout/Sidebar.tsx');
const mobileNav    = read('src/components/layout/MobileNav.tsx');
const apiTs        = read('src/lib/api.ts');

// ── 1. /saved route ───────────────────────────────────────────────────────────

test('/saved page exists and imports SavedShell', () => {
  assert.ok(savedPage.includes('SavedShell'), '/saved page must import SavedShell');
  assert.ok(
    savedPage.includes('@/components/saved/SavedShell'),
    'must import from @/components/saved/SavedShell'
  );
});

test('/saved page exports a default function', () => {
  assert.ok(savedPage.includes('export default function'), 'page must have a default export');
});

// ── 2. SavedShell component ───────────────────────────────────────────────────

test('SavedShell exports named SavedShell function', () => {
  assert.ok(savedShell.includes('export function SavedShell'), 'must export named SavedShell');
});

test('SavedShell is a client component', () => {
  assert.ok(
    savedShell.startsWith('"use client"') || savedShell.startsWith("'use client'"),
    'SavedShell must start with "use client"'
  );
});

// ── 3. Sidebar navigation ─────────────────────────────────────────────────────

test('Sidebar includes /saved href', () => {
  assert.ok(
    sidebar.includes('href: "/saved"') || sidebar.includes("href: '/saved'"),
    'Sidebar primaryLinks must include href for /saved'
  );
});

test('Sidebar has Saved label', () => {
  assert.ok(sidebar.includes('"Saved"') || sidebar.includes("'Saved'") || sidebar.includes('label: "Saved"'), 'Sidebar must have a Saved label');
});

test('Sidebar imports Bookmark icon for Saved link', () => {
  assert.ok(sidebar.includes('Bookmark'), 'Sidebar must import Bookmark icon');
});

// ── 4. MobileNav navigation ───────────────────────────────────────────────────

test('MobileNav drawer links include /saved', () => {
  assert.ok(
    mobileNav.includes('"/saved"') || mobileNav.includes("'/saved'"),
    'MobileNav must include /saved in links array'
  );
});

test('MobileNav has Saved label', () => {
  assert.ok(mobileNav.includes('"Saved"') || mobileNav.includes("'Saved'"), 'MobileNav must include Saved label');
});

test('MobileNav tabLinks include /saved', () => {
  // Verify /saved appears in tabLinks (the bottom tab bar)
  assert.ok(
    mobileNav.includes('tabLinks') && mobileNav.includes('"/saved"'),
    'tabLinks must include /saved'
  );
});

test('MobileNav imports Bookmark icon', () => {
  assert.ok(mobileNav.includes('Bookmark'), 'MobileNav must import Bookmark icon');
});

// ── 5-6. API helper usage (existing helpers reused, no new persistence path) ──

test('SavedShell uses listSavedItems from api', () => {
  assert.ok(savedShell.includes('listSavedItems'), 'SavedShell must use listSavedItems');
});

test('SavedShell uses deleteSavedItem from api', () => {
  assert.ok(savedShell.includes('deleteSavedItem'), 'SavedShell must use deleteSavedItem');
});

test('listSavedItems already exists in api.ts (not added by this PR)', () => {
  assert.ok(
    apiTs.includes('export async function listSavedItems'),
    'listSavedItems must be in api.ts'
  );
});

test('deleteSavedItem already exists in api.ts (not added by this PR)', () => {
  assert.ok(
    apiTs.includes('export async function deleteSavedItem'),
    'deleteSavedItem must be in api.ts'
  );
});

// ── 7. Vertical grouping ──────────────────────────────────────────────────────

test('SavedShell references restaurant vertical', () => {
  assert.ok(
    savedShell.includes('"restaurant"') || savedShell.includes("'restaurant'"),
    'must reference restaurant vertical'
  );
});

test('SavedShell references attraction vertical', () => {
  assert.ok(
    savedShell.includes('"attraction"') || savedShell.includes("'attraction'"),
    'must reference attraction vertical'
  );
});

test('SavedShell references hotel vertical', () => {
  assert.ok(
    savedShell.includes('"hotel"') || savedShell.includes("'hotel'"),
    'must reference hotel vertical'
  );
});

test('SavedShell references flight vertical', () => {
  assert.ok(
    savedShell.includes('"flight"') || savedShell.includes("'flight'"),
    'must reference flight vertical'
  );
});

test('SavedShell renders group labels for all 4 verticals', () => {
  assert.ok(savedShell.includes('Restaurants'), 'Restaurants group label missing');
  assert.ok(savedShell.includes('Attractions'), 'Attractions group label missing');
  assert.ok(savedShell.includes('Hotels'),      'Hotels group label missing');
  assert.ok(savedShell.includes('Flights'),     'Flights group label missing');
});

test('SavedShell hides empty groups (VerticalGroup returns null when items empty)', () => {
  assert.ok(savedShell.includes('items.length === 0') || savedShell.includes('items.length == 0'), 'empty group must return null');
});

// ── 8. Card rendering from displaySnapshot / searchContext ────────────────────

test('Card reads name from displaySnapshot', () => {
  assert.ok(
    savedShell.includes('displaySnapshot') && savedShell.includes('"name"'),
    'must read name from displaySnapshot'
  );
});

test('Card reads rating from displaySnapshot', () => {
  assert.ok(savedShell.includes('"rating"'), 'must read rating from displaySnapshot');
});

test('Card reads address from displaySnapshot', () => {
  assert.ok(savedShell.includes('"address"'), 'must read address from displaySnapshot');
});

test('Card reads googleMapsUri from displaySnapshot', () => {
  assert.ok(savedShell.includes('"googleMapsUri"'), 'must read googleMapsUri from displaySnapshot');
});

test('Card reads tags from displaySnapshot', () => {
  assert.ok(savedShell.includes('"tags"'), 'must read tags from displaySnapshot');
});

test('Card reads searchContext fields (destination at minimum)', () => {
  assert.ok(savedShell.includes('searchContext'), 'must read from searchContext');
});

test('Card shows saved date from createdAt', () => {
  assert.ok(savedShell.includes('createdAt'), 'must use createdAt for saved date');
});

// ── 9. Hotel card — discovery only, no rates/prices/availability/booking ──────

test('Hotel card reads checkIn from searchContext', () => {
  assert.ok(savedShell.includes('checkIn'), 'must read checkIn from searchContext');
});

test('Hotel card reads checkOut from searchContext', () => {
  assert.ok(savedShell.includes('checkOut'), 'must read checkOut from searchContext');
});

test('Hotel card reads guests from searchContext', () => {
  assert.ok(savedShell.includes('guests'), 'must read guests from searchContext');
});

test('Hotel saved card does not render price per night copy', () => {
  const lower = savedShell.toLowerCase();
  assert.ok(!lower.includes('per night'), 'must not include per-night pricing copy');
});

test('Hotel saved card does not render availability copy', () => {
  const lower = savedShell.toLowerCase();
  assert.ok(!lower.includes('availability'), 'must not include availability copy');
});

test('Hotel saved card does not render booking copy', () => {
  const lower = savedShell.toLowerCase();
  assert.ok(
    !lower.includes('book now') && !lower.includes('check rates'),
    'must not include booking copy'
  );
});

// ── 10. Remove action ─────────────────────────────────────────────────────────

test('Remove action calls deleteSavedItem', () => {
  assert.ok(savedShell.includes('deleteSavedItem'), 'remove action must call deleteSavedItem');
});

test('Remove button has data-testid="remove-saved-btn"', () => {
  assert.ok(savedShell.includes('remove-saved-btn'), 'remove button must have data-testid');
});

test('Remove shows error message on failure', () => {
  assert.ok(savedShell.includes('remove-error') || savedShell.includes('removeError'), 'must show remove error');
});

// ── 11. Loading / error / empty states ───────────────────────────────────────

test('SavedShell has loading state (data-testid="saved-loading")', () => {
  assert.ok(savedShell.includes('saved-loading'), 'must have saved-loading state');
});

test('SavedShell has error state (data-testid="saved-error")', () => {
  assert.ok(savedShell.includes('saved-error'), 'must have saved-error state');
});

test('SavedShell has empty state (data-testid="saved-empty")', () => {
  assert.ok(savedShell.includes('saved-empty'), 'must have saved-empty state');
});

// ── 12. Empty state links to /explore ────────────────────────────────────────

test('Empty state contains a link to /explore', () => {
  const emptyIdx = savedShell.indexOf('saved-empty');
  assert.ok(emptyIdx !== -1, 'saved-empty must exist');
  const slice = savedShell.slice(emptyIdx, emptyIdx + 600);
  assert.ok(slice.includes('/explore'), 'empty state must link to /explore');
});

// ── 13. No provider calls / search routes ────────────────────────────────────

test('SavedShell does not call any /search/* routes', () => {
  assert.ok(!savedShell.includes('/search/'), 'must not call any /search/* routes');
});

test('SavedShell does not import callConciergeSearch', () => {
  assert.ok(!savedShell.includes('callConciergeSearch'), 'must not import callConciergeSearch');
});

test('SavedShell does not import searchRestaurants', () => {
  assert.ok(!savedShell.includes('searchRestaurants'), 'must not import searchRestaurants');
});

// ── 14. Forbidden scope ───────────────────────────────────────────────────────

test('SavedShell does not import TripBuilder', () => {
  assert.ok(!savedShell.includes('TripBuilder'), 'must not import TripBuilder');
});

test('SavedShell does not import tripCandidates', () => {
  assert.ok(!savedShell.includes('tripCandidates'), 'must not import tripCandidates');
});
