/**
 * Stage 3.5 Phase 8N-F — Saved Ideas True Visual Correction
 *
 * Contract tests verifying that the failed cream-slab design is fully removed
 * and replaced with a true dark atelier folio composition.
 *
 * Hard fail gates encoded as tests:
 * 1.  SavedShell does NOT use scrapbook-page anywhere (cream header slab removed).
 * 2.  SavedItemCard does NOT use clipping-card (cream card surface removed).
 * 3.  SavedItemCard does NOT use boutique-folio on the article element.
 * 4.  SavedShell uses saved-folio-card for item cards (dark atelier surface).
 * 5.  globals.css defines .saved-folio-header (dark integrated folio header).
 * 6.  globals.css defines .saved-folio-card (dark atelier clipping card).
 * 7.  saved-folio-card does NOT use warm-paper or bone background.
 * 8.  saved-folio-card uses dark surface (carbon-mist base).
 * 9.  saved-folio-card has ::before pseudo-element for warm brass accent.
 * 10. saved-folio-header has ::before pseudo-element for brass top rule.
 * 11. SavedShell outer root still uses saved-clipping-desk (8N-E preservation).
 * 12. All behavior testids preserved.
 * 13. Planning bridge compact horizontal layout preserved.
 * 14. All behavioral handlers preserved.
 * 15. No backend/provider imports added.
 * 16. No new packages added.
 * 17. Touch targets preserved (44px).
 * 18. item name uses dark-background text (not text-ds-text-inverse on dark).
 * 19. saved-folio-card defined in globals.css after saved-clipping-desk.
 * 20. saved-folio-header defined in globals.css.
 * 21. Trip picker states (picking/adding/added/error) preserved.
 * 22. CreateTripFromSavedModal behavioral hooks preserved.
 * 23. No raw rgba() in SavedShell JSX (no inline raw hex).
 * 24. No legacy palette (cream-*, brand-*, dark-100) in SavedShell.
 * 25. saved-folio-header used on the header zone div in SavedShell.
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

const savedShell = read('src/components/saved/SavedShell.tsx');
const modal = read('src/components/saved/CreateTripFromSavedModal.tsx');
const globals = read('src/app/globals.css');
const pkgJson = read('package.json');

// ── 1. scrapbook-page fully removed (cream header slab gate) ─────────────────

test('8N-F: SavedShell does NOT use scrapbook-page (cream header slab removed)', () => {
  assert.ok(
    !savedShell.includes('scrapbook-page'),
    'scrapbook-page must be fully removed from SavedShell — it was the large cream header slab'
  );
});

// ── 2. clipping-card removed from SavedItemCard (cream card gate) ─────────────

test('8N-F: SavedItemCard does NOT use clipping-card class', () => {
  assert.ok(
    !savedShell.includes('clipping-card'),
    'clipping-card must be removed from SavedShell — it was the full cream card surface'
  );
});

// ── 3. boutique-folio removed from card article ───────────────────────────────

test('8N-F: SavedItemCard article does NOT use boutique-folio', () => {
  const cardIdx = savedShell.indexOf('data-testid="saved-item-card"');
  assert.ok(cardIdx >= 0, 'saved-item-card testid must exist');
  const articleSlice = savedShell.slice(Math.max(0, cardIdx - 250), cardIdx + 50);
  assert.ok(
    !articleSlice.includes('boutique-folio'),
    'saved-item-card article must not use boutique-folio as card surface (dark folio replaces it)'
  );
});

// ── 4. saved-folio-card used for item cards (dark surface gate) ───────────────

test('8N-F: SavedShell uses folio-collection-card class for item cards (Slice 4B replaced saved-folio-card)', () => {
  assert.ok(
    savedShell.includes('folio-collection-card'),
    'SavedShell must use folio-collection-card class for the dark atelier card surface (Slice 4B)'
  );
});

test('8N-F: folio-collection-card is on the saved-item-card article element (Slice 4B)', () => {
  const cardIdx = savedShell.indexOf('data-testid="saved-item-card"');
  assert.ok(cardIdx >= 0, 'saved-item-card testid must exist');
  const articleSlice = savedShell.slice(Math.max(0, cardIdx - 250), cardIdx + 50);
  assert.ok(
    articleSlice.includes('folio-collection-card'),
    'folio-collection-card must be on the article element with saved-item-card testid (Slice 4B)'
  );
});

// ── 5. globals.css defines .saved-folio-header ────────────────────────────────

test('8N-F: globals.css defines .saved-folio-header', () => {
  assert.ok(
    globals.includes('.saved-folio-header'),
    '.saved-folio-header CSS class must be defined in globals.css'
  );
});

// ── 6. globals.css defines .saved-folio-card ─────────────────────────────────

test('8N-F: globals.css defines .saved-folio-card', () => {
  assert.ok(
    globals.includes('.saved-folio-card'),
    '.saved-folio-card CSS class must be defined in globals.css'
  );
});

// ── 7. saved-folio-card does NOT use warm-paper or bone background ─────────────

test('8N-F: .saved-folio-card CSS does not use warm-paper or bone background', () => {
  const cardCssIdx = globals.indexOf('.saved-folio-card {');
  assert.ok(cardCssIdx >= 0, '.saved-folio-card rule must exist');
  const cardCssSlice = globals.slice(cardCssIdx, cardCssIdx + 400);
  assert.ok(
    !cardCssSlice.includes('ds-warm-paper') && !cardCssSlice.includes('ds-bone') && !cardCssSlice.includes('ds-linen'),
    '.saved-folio-card must not use warm-paper/bone/linen as background — it must be a dark atelier surface'
  );
});

// ── 8. saved-folio-card uses dark carbon surface ──────────────────────────────

test('8N-F: .saved-folio-card uses ds-carbon-mist dark base', () => {
  const cardCssIdx = globals.indexOf('.saved-folio-card {');
  const cardCssSlice = globals.slice(cardCssIdx, cardCssIdx + 400);
  assert.ok(
    cardCssSlice.includes('ds-carbon-mist') || cardCssSlice.includes('var(--ds-carbon') || cardCssSlice.includes('var(--ds-onyx'),
    '.saved-folio-card must use a dark surface token (carbon-mist, carbon, or onyx)'
  );
});

// ── 9. saved-folio-card ::before pseudo-element for warm brass top accent ──────

test('8N-F: .saved-folio-card::before defines warm brass top accent', () => {
  assert.ok(
    globals.includes('.saved-folio-card::before'),
    '.saved-folio-card::before must be defined for the warm brass top accent'
  );
  const pseudoIdx = globals.indexOf('.saved-folio-card::before');
  const pseudoSlice = globals.slice(pseudoIdx, pseudoIdx + 400);
  assert.ok(
    pseudoSlice.includes('rgba(197, 148, 77') || pseudoSlice.includes('rgba(224, 184, 136'),
    '.saved-folio-card::before must use warm brass tones (rgba(197, 148, 77...) or rgba(224, 184, 136...))'
  );
});

// ── 10. saved-folio-header ::before for brass top rule ───────────────────────

test('8N-F: .saved-folio-header::before defines warm brass top rule', () => {
  assert.ok(
    globals.includes('.saved-folio-header::before'),
    '.saved-folio-header::before must be defined for the warm brass rule'
  );
  const pseudoIdx = globals.indexOf('.saved-folio-header::before');
  const pseudoSlice = globals.slice(pseudoIdx, pseudoIdx + 300);
  assert.ok(
    pseudoSlice.includes('rgba(197, 148, 77') || pseudoSlice.includes('rgba(224, 184, 136'),
    '.saved-folio-header::before must use warm brass tones'
  );
});

// ── 11. Outer shell still uses saved-clipping-desk (8N-E preservation) ────────

test('8N-F: SavedShell outer root uses folio-cinema-collection (Slice 4B replaced saved-clipping-desk)', () => {
  assert.ok(
    savedShell.includes('folio-cinema-collection'),
    'folio-cinema-collection must be on the outer shell (Slice 4B replaced saved-clipping-desk)'
  );
  const shellIdx = savedShell.indexOf('data-testid="saved-shell"');
  const outerSlice = savedShell.slice(Math.max(0, shellIdx - 400), shellIdx + 50);
  assert.ok(
    outerSlice.includes('folio-cinema-collection'),
    'folio-cinema-collection must be on the same element as saved-shell testid (Slice 4B)'
  );
});

// ── 12. All behavior testids preserved ────────────────────────────────────────

test('8N-F: all behavior testids preserved', () => {
  const required = [
    'saved-shell',
    'saved-scrapbook-header',
    'saved-scrapbook-overline',
    'saved-scrapbook-heading',
    'saved-scrapbook-count',
    'saved-item-card',
    'saved-item-type-overline',
    'saved-item-name',
    'saved-planning-bridge',
    'create-trip-btn',
    'add-to-trip-btn',
    'create-trip-section',
    'add-to-trip-section',
    'trip-picker',
    'trip-picker-option',
    'add-to-trip-success',
    'add-to-trip-error',
    'remove-saved-btn',
    'remove-error',
    'saved-card-rating',
    'hotel-search-context',
    'saved-loading',
    'saved-error',
    'saved-empty',
    'saved-empty-explore-link',
  ];
  for (const id of required) {
    assert.ok(
      savedShell.includes(`data-testid="${id}"`),
      `testid "${id}" must be preserved in SavedShell`
    );
  }
});

test('8N-F: section testid template preserved (saved-section-${key})', () => {
  assert.ok(
    savedShell.includes('data-testid={`saved-section-${key}`}'),
    'saved-section-${key} template testid must be preserved'
  );
});

// ── 13. Planning bridge compact layout preserved ──────────────────────────────

test('8N-F: planning bridge uses compact flex horizontal row', () => {
  const bridgeIdx = savedShell.indexOf('saved-planning-bridge');
  assert.ok(bridgeIdx >= 0, 'saved-planning-bridge must exist');
  const bridgeSlice = savedShell.slice(bridgeIdx, bridgeIdx + 600);
  assert.ok(
    bridgeSlice.includes('flex') && bridgeSlice.includes('items-center'),
    'planning bridge must use flex items-center for compact horizontal layout'
  );
});

test('8N-F: planning bridge create-trip-section and add-to-trip-section are compact', () => {
  const bridgeIdx = savedShell.indexOf('saved-planning-bridge');
  const bridgeSlice = savedShell.slice(bridgeIdx, bridgeIdx + 2000);
  const createIdx = bridgeSlice.indexOf('create-trip-section');
  const addIdx = bridgeSlice.indexOf('add-to-trip-section');
  assert.ok(createIdx >= 0 && addIdx >= 0, 'both section testids must appear in planning bridge');
  assert.ok(
    Math.abs(addIdx - createIdx) < 1000,
    'create-trip-section and add-to-trip-section must be close together (compact horizontal layout)'
  );
});

// ── 14. All behavioral handlers preserved ─────────────────────────────────────

test('8N-F: all behavioral handlers preserved', () => {
  assert.ok(savedShell.includes('deleteSavedItem'), 'deleteSavedItem must be preserved');
  assert.ok(savedShell.includes('addSavedItemToTrip'), 'addSavedItemToTrip must be preserved');
  assert.ok(savedShell.includes('listSavedItems'), 'listSavedItems must be preserved');
  assert.ok(savedShell.includes('fetchTrips'), 'fetchTrips must be preserved');
  assert.ok(savedShell.includes('onCreateTrip(item)'), 'onCreateTrip handler must be preserved');
  assert.ok(savedShell.includes('onRemove'), 'onRemove handler must be preserved');
});

test('8N-F: flight canAddToTrip exclusion preserved', () => {
  assert.ok(
    savedShell.includes('item.vertical !== "flight"') || savedShell.includes("item.vertical !== 'flight'"),
    'flight vertical must be excluded from canAddToTrip'
  );
});

// ── 15. No backend/provider imports ───────────────────────────────────────────

test('8N-F: SavedShell has no new backend/provider imports', () => {
  assert.ok(!savedShell.includes('callConciergeSearch'), 'must not import callConciergeSearch');
  assert.ok(!savedShell.includes('TripBuilder'), 'must not import TripBuilder');
  assert.ok(!savedShell.includes('searchRestaurants'), 'must not import searchRestaurants');
});

// ── 16. No new packages ────────────────────────────────────────────────────────

test('8N-F: no new packages added to package.json', () => {
  assert.ok(!pkgJson.includes('"framer-motion"'), 'must not add framer-motion');
  assert.ok(!pkgJson.includes('"@tanstack/react-query"'), 'must not add react-query');
});

// ── 17. Touch targets preserved ───────────────────────────────────────────────

test('8N-F: create-trip-btn has min-h-[44px] touch target', () => {
  const btnIdx = savedShell.indexOf('create-trip-btn');
  const slice = savedShell.slice(Math.max(0, btnIdx - 600), btnIdx + 50);
  assert.ok(slice.includes('min-h-[44px]'), 'create-trip-btn must have min-h-[44px]');
});

test('8N-F: add-to-trip-btn has min-h-[44px] touch target', () => {
  const btnIdx = savedShell.indexOf('add-to-trip-btn');
  const slice = savedShell.slice(Math.max(0, btnIdx - 600), btnIdx + 50);
  assert.ok(slice.includes('min-h-[44px]'), 'add-to-trip-btn must have min-h-[44px]');
});

test('8N-F: remove-saved-btn has min-h-[44px] touch target', () => {
  const removeIdx = savedShell.indexOf('remove-saved-btn');
  const slice = savedShell.slice(Math.max(0, removeIdx - 400), removeIdx + 50);
  assert.ok(slice.includes('min-h-[44px]'), 'remove-saved-btn must have min-h-[44px]');
});

test('8N-F: saved-empty-explore-link has min-h-[44px] touch target', () => {
  const exploreIdx = savedShell.indexOf('saved-empty-explore-link');
  const slice = savedShell.slice(Math.max(0, exploreIdx - 600), exploreIdx + 50);
  assert.ok(slice.includes('min-h-[44px]'), 'empty state explore link must have min-h-[44px]');
});

// ── 18. Item name uses dark-background text (not dark ink on dark card) ────────

test('8N-F: saved-item-name does not use text-ds-text-inverse on dark folio card', () => {
  const nameIdx = savedShell.indexOf('data-testid="saved-item-name"');
  assert.ok(nameIdx >= 0, 'saved-item-name testid must exist');
  const nameSlice = savedShell.slice(Math.max(0, nameIdx - 300), nameIdx + 50);
  assert.ok(
    !nameSlice.includes('text-ds-text-inverse'),
    'saved-item-name must not use text-ds-text-inverse (dark ink) on a dark folio card'
  );
});

// ── 19. saved-folio-card defined after saved-clipping-desk ───────────────────

test('8N-F: .saved-folio-card defined after .saved-clipping-desk in globals.css', () => {
  const deskIdx = globals.indexOf('.saved-clipping-desk');
  const folioIdx = globals.indexOf('.saved-folio-card');
  assert.ok(deskIdx >= 0, '.saved-clipping-desk must exist');
  assert.ok(folioIdx > deskIdx, '.saved-folio-card must be defined after .saved-clipping-desk');
});

// ── 20. saved-folio-header uses position:relative ────────────────────────────

test('8N-F: .saved-folio-header uses position:relative for pseudo-element', () => {
  const headerIdx = globals.indexOf('.saved-folio-header {');
  assert.ok(headerIdx >= 0, '.saved-folio-header rule must exist');
  const headerSlice = globals.slice(headerIdx, headerIdx + 200);
  assert.ok(
    headerSlice.includes('position: relative') || headerSlice.includes('position:relative'),
    '.saved-folio-header must use position:relative'
  );
});

// ── 21. Trip picker states preserved ─────────────────────────────────────────

test('8N-F: trip picker states preserved (picking/adding/added/error)', () => {
  assert.ok(savedShell.includes('"picking"'), 'picking state must be preserved');
  assert.ok(savedShell.includes('"adding"'), 'adding state must be preserved');
  assert.ok(savedShell.includes('"added"'), 'added state must be preserved');
  assert.ok(savedShell.includes('"error"'), 'error state must be preserved');
});

// ── 22. Modal behavioral hooks preserved ─────────────────────────────────────

test('8N-F: CreateTripFromSavedModal behavioral hooks preserved', () => {
  assert.ok(modal.includes('createTripFromSavedItem'), 'createTripFromSavedItem must be preserved');
  assert.ok(modal.includes('initFromPrefill'), 'initFromPrefill must be preserved');
  assert.ok(modal.includes('canSubmit'), 'canSubmit gate must be preserved');
});

test('8N-F: modal testids preserved', () => {
  assert.ok(modal.includes('data-testid="create-trip-modal"'), 'create-trip-modal testid must be preserved');
  assert.ok(modal.includes('data-testid="create-trip-form"'), 'create-trip-form testid must be preserved');
  assert.ok(modal.includes('data-testid="ct-submit"'), 'ct-submit testid must be preserved');
});

// ── 23. No raw rgba() in SavedShell JSX ──────────────────────────────────────

test('8N-F: SavedShell has no raw rgba() in JSX', () => {
  const lines = savedShell.split('\n');
  const rgbaLines = lines.filter(l => l.includes('rgba(') && !l.includes('var(--'));
  assert.strictEqual(rgbaLines.length, 0, `raw rgba() found in SavedShell: ${rgbaLines.join(' | ')}`);
});

// ── 24. No legacy palette ─────────────────────────────────────────────────────

test('8N-F: SavedShell has no cream-* legacy classes', () => {
  assert.ok(
    !savedShell.includes('cream-1') && !savedShell.includes('cream-3') && !savedShell.includes('cream-5'),
    'must not use cream-* legacy colors'
  );
});

test('8N-F: SavedShell has no brand-* legacy classes', () => {
  assert.ok(
    !savedShell.includes('brand-4') && !savedShell.includes('brand-5') && !savedShell.includes('brand-6'),
    'must not use brand-* legacy colors'
  );
});

test('8N-F: SavedShell has no dark-100 legacy class', () => {
  assert.ok(!savedShell.includes('dark-100'), 'must not use bg-dark-100 legacy class');
});

// ── 25. saved-folio-header used in SavedShell header zone ────────────────────

test('8N-F: saved-folio-header class used in SavedShell (header zone)', () => {
  assert.ok(
    savedShell.includes('saved-folio-header'),
    'saved-folio-header must be used in SavedShell for the dark integrated header zone'
  );
});

test('8N-F: saved-folio-header appears before saved-scrapbook-header (wraps the header)', () => {
  const folioIdx = savedShell.indexOf('saved-folio-header');
  const headerIdx = savedShell.indexOf('data-testid="saved-scrapbook-header"');
  assert.ok(folioIdx >= 0 && headerIdx > folioIdx, 'saved-folio-header div must wrap the saved-scrapbook-header element');
});

// ── No hotel per-night pricing (discovery-only preserved) ────────────────────

test('8N-F: hotel discovery-only preserved (no per-night pricing)', () => {
  assert.ok(!savedShell.toLowerCase().includes('per night'), 'must not show per-night pricing');
});
