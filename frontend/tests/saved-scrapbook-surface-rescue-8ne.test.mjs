/**
 * Stage 3.5 Phase 8N-E — Saved Ideas Scrapbook Surface Rescue
 *
 * Contract tests verifying:
 * 1.  SavedShell outer root uses saved-clipping-desk (not full-page cream slab).
 * 2.  SavedShell scrapbook-page is scoped to header zone, not full outer wrapper.
 * 3.  globals.css defines .saved-clipping-desk composition primitive.
 * 4.  globals.css defines .saved-clipping-card composition primitive.
 * 5.  saved-clipping-card defined after .clipping-card in source order.
 * 6.  SavedShell uses saved-clipping-card on individual cards.
 * 7.  SavedItemCard no longer uses boutique-folio (heavy dark shadow on light card).
 * 8.  Desktop layout uses lg:grid-cols-2 for two-column card layout.
 * 9.  Desktop layout uses lg:max-w-4xl for wider editorial desk on wide screens.
 * 10. Planning bridge idle state uses flex horizontal row (compact, not stacked).
 * 11. Planning bridge flex row contains create-trip-section and add-to-trip-section.
 * 12. Planning bridge create-trip-btn and add-to-trip-btn appear close together (horizontal).
 * 13. VerticalGroup section header uses vertical icon from config.
 * 14. Section count uses dark-background-compatible text (not dark text-ds-text-inverse).
 * 15. Loading state uses dark-background-compatible text.
 * 16. Empty state heading uses dark-background-compatible text (not text-ds-text-inverse).
 * 17. Empty state sub-text uses dark-background-compatible text.
 * 18. Error state text uses dark-background-compatible color.
 * 19. All key testids preserved (full list).
 * 20. All behavioral handlers preserved in SavedShell.
 * 21. CreateTripFromSavedModal behavioral hooks preserved.
 * 22. No backend/provider imports added.
 * 23. No new npm packages added.
 * 24. saved-clipping-desk outer wrapper has no scrapbook-page class on same element.
 * 25. saved-clipping-card defined in globals.css with position:relative.
 * 26. saved-clipping-card has ::before pseudo-element for warm top accent.
 * 27. saved-clipping-desk defined after .clipping-card in globals.css source order.
 * 28. Scrapbook header zone still uses scrapbook-page (8N-C preservation).
 * 29. Scrapbook header zone still uses editorial-section-rule (8N-C preservation).
 * 30. clipping-card still used on SavedItemCard (8N-C preservation).
 * 31. saved-scrapbook-header testid preserved (8G preservation).
 * 32. saved-planning-bridge testid preserved (8G preservation).
 * 33. create-trip-btn preserved with type="button" and onClick.
 * 34. add-to-trip-btn preserved with type="button" and onClick.
 * 35. trip-picker, trip-picker-option testids preserved.
 * 36. add-to-trip-success, add-to-trip-error testids preserved.
 * 37. remove-saved-btn testid preserved.
 * 38. saved-loading, saved-error, saved-empty testids preserved.
 * 39. saved-empty-explore-link testid preserved.
 * 40. create-trip-section, add-to-trip-section testids preserved.
 * 41. Hotel search context testid preserved.
 * 42. saved-card-rating testid preserved.
 * 43. No fake/hardcoded city data.
 * 44. No raw rgba() or raw hex in SavedShell.
 * 45. No legacy palette (cream-*, brand-*, dark-100) in SavedShell.
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

// ── 1. Outer root uses saved-clipping-desk ────────────────────────────────────

test('8N-E: SavedShell outer root uses folio-cinema-collection class (Slice 4B replaced saved-clipping-desk)', () => {
  assert.ok(savedShell.includes('folio-cinema-collection'), 'outer shell must use folio-cinema-collection class (Slice 4B replaced saved-clipping-desk)');
});

// ── 2. scrapbook-page scoped to header zone, not full outer wrapper ────────────

test('8N-E: scrapbook-page is NOT on the same element as saved-shell testid', () => {
  const shellIdx = savedShell.indexOf('data-testid="saved-shell"');
  assert.ok(shellIdx >= 0, 'saved-shell testid must exist');
  // The outer wrapper div extends from shellIdx backwards to find the opening tag
  // Look 400 chars back to find the div opening and its classes
  const outerDiv = savedShell.slice(Math.max(0, shellIdx - 400), shellIdx + 50);
  assert.ok(!outerDiv.includes('scrapbook-page'), 'saved-shell root element must NOT have scrapbook-page class (not a cream slab)');
});

test('8N-E: folio-cinema-collection and saved-shell testid are on the same element (Slice 4B)', () => {
  const shellIdx = savedShell.indexOf('data-testid="saved-shell"');
  const outerDiv = savedShell.slice(Math.max(0, shellIdx - 400), shellIdx + 50);
  assert.ok(outerDiv.includes('folio-cinema-collection'), 'folio-cinema-collection must be on the outer div with saved-shell testid (Slice 4B)');
});

// ── 3. CSS primitive: saved-clipping-desk ────────────────────────────────────

test('8N-E: globals.css defines .saved-clipping-desk', () => {
  assert.ok(globals.includes('.saved-clipping-desk'), '.saved-clipping-desk CSS class must be defined in globals.css');
});

// ── 4. CSS primitive: saved-clipping-card ────────────────────────────────────

test('8N-E: globals.css defines .saved-clipping-card', () => {
  assert.ok(globals.includes('.saved-clipping-card'), '.saved-clipping-card CSS class must be defined in globals.css');
});

// ── 5. Source order: saved-clipping-card after clipping-card ─────────────────

test('8N-E: .saved-clipping-card defined after .clipping-card in globals.css', () => {
  const clippingIdx = globals.indexOf('.clipping-card');
  const savedClippingIdx = globals.indexOf('.saved-clipping-card');
  assert.ok(savedClippingIdx > clippingIdx, '.saved-clipping-card must be defined after .clipping-card');
});

// ── 6. SavedItemCard uses dark folio card class (8N-F supersedes saved-clipping-card) ─────

test('8N-E/F: SavedItemCard uses folio-collection-card (Slice 4B replaced saved-folio-card)', () => {
  // saved-folio-card was replaced in Slice 4B by folio-collection-card.
  assert.ok(savedShell.includes('folio-collection-card'), 'SavedItemCard must use folio-collection-card (Slice 4B replaced saved-folio-card)');
});

// ── 8. Desktop: lg:grid-cols-2 for two-column card layout ────────────────────

test('8N-E: VerticalGroup uses lg:grid-cols-2 for two-column desktop layout', () => {
  assert.ok(savedShell.includes('lg:grid-cols-2'), 'card list must use lg:grid-cols-2 for editorial desk layout on desktop');
});

// ── 9. Desktop: lg:max-w-4xl for wider shell ──────────────────────────────────

test('8N-E: SavedShell uses lg:max-w-4xl for wider desktop editorial desk', () => {
  assert.ok(
    savedShell.includes('lg:max-w-4xl') || savedShell.includes('lg:max-w-5xl'),
    'SavedShell must use lg:max-w-4xl or lg:max-w-5xl for desktop width improvement'
  );
});

// ── 10. Planning bridge compact horizontal layout ─────────────────────────────

test('8N-E: planning bridge uses flex horizontal row for compact idle actions', () => {
  const bridgeIdx = savedShell.indexOf('saved-planning-bridge');
  assert.ok(bridgeIdx >= 0, 'saved-planning-bridge testid must exist');
  const bridgeSlice = savedShell.slice(bridgeIdx, bridgeIdx + 600);
  assert.ok(
    bridgeSlice.includes('flex') && bridgeSlice.includes('items-center'),
    'planning bridge must use flex items-center for compact horizontal action layout'
  );
});

// ── 11. Planning bridge create-trip-section and add-to-trip-section ───────────

test('8N-E: planning bridge contains both create-trip-section and add-to-trip-section', () => {
  const bridgeIdx = savedShell.indexOf('saved-planning-bridge');
  const bridgeSlice = savedShell.slice(bridgeIdx, bridgeIdx + 1500);
  assert.ok(bridgeSlice.includes('create-trip-section'), 'planning bridge must contain create-trip-section');
  assert.ok(bridgeSlice.includes('add-to-trip-section'), 'planning bridge must contain add-to-trip-section');
});

// ── 12. create-trip-section and add-to-trip-section are close (horizontal row) ─

test('8N-E: create-trip-section and add-to-trip-section are compact (not separated by 2000+ chars)', () => {
  const bridgeIdx = savedShell.indexOf('saved-planning-bridge');
  const bridgeSlice = savedShell.slice(bridgeIdx, bridgeIdx + 2000);
  const createIdx = bridgeSlice.indexOf('create-trip-section');
  const addIdx = bridgeSlice.indexOf('add-to-trip-section');
  assert.ok(createIdx >= 0 && addIdx >= 0, 'both section testids must appear in planning bridge');
  // In horizontal layout they're close; stacked layout would have them 1500+ chars apart
  assert.ok(
    Math.abs(addIdx - createIdx) < 1000,
    'create-trip-section and add-to-trip-section must be close together (compact horizontal layout)'
  );
});

// ── 13. VerticalGroup section header uses vertical icon ───────────────────────

test('8N-E: VerticalGroup section header includes vertical icon from config', () => {
  // SectionIcon should be used in the section header div (near saved-section-label)
  const labelIdx = savedShell.indexOf('saved-section-label-${key}');
  assert.ok(labelIdx >= 0, 'saved-section-label template must exist');
  const sectionSlice = savedShell.slice(Math.max(0, labelIdx - 500), labelIdx + 200);
  assert.ok(
    sectionSlice.includes('SectionIcon') || sectionSlice.includes('<Icon'),
    'VerticalGroup section header must use the vertical icon (SectionIcon or Icon)'
  );
});

// ── 14. Section count: dark-background-compatible text ───────────────────────

test('8N-E: section item count uses dark-background-compatible text color', () => {
  const labelIdx = savedShell.indexOf('saved-section-label-${key}');
  // The count is near the section label
  const sectionSlice = savedShell.slice(labelIdx, labelIdx + 400);
  const countIdx = sectionSlice.indexOf('items.length}');
  assert.ok(countIdx >= 0, 'items.length must appear in section header');
  const countCtx = sectionSlice.slice(Math.max(0, countIdx - 200), countIdx + 100);
  // Must NOT use text-ds-text-inverse (dark ink) or text-ds-slate (dark gray) on dark background
  assert.ok(
    !countCtx.includes('text-ds-text-inverse') && !countCtx.includes('text-ds-ink'),
    'section count must not use dark ink text on dark background'
  );
  assert.ok(
    countCtx.includes('text-ds-text-secondary') || countCtx.includes('text-ds-text') ||
    countCtx.includes('text-ds-accent') || countCtx.includes('text-ds-text-tertiary'),
    'section count must use a light-on-dark compatible text color'
  );
});

// ── 15. Loading state: dark-background-compatible text ───────────────────────

test('8N-E: loading state uses dark-background-compatible text', () => {
  const loadingIdx = savedShell.indexOf('data-testid="saved-loading"');
  const loadingSlice = savedShell.slice(loadingIdx, loadingIdx + 300);
  assert.ok(
    loadingSlice.includes('text-ds-text-secondary') || loadingSlice.includes('text-ds-text-tertiary') ||
    loadingSlice.includes('text-ds-text') || loadingSlice.includes('text-ds-accent'),
    'loading state must use text visible on dark background'
  );
  assert.ok(
    !loadingSlice.includes('text-ds-text-inverse'),
    'loading state must not use text-ds-text-inverse (dark ink) on dark background'
  );
});

// ── 16. Empty state heading: dark-background-compatible ──────────────────────

test('8N-E: empty state heading does not use text-ds-text-inverse on dark background', () => {
  const nothingIdx = savedShell.indexOf('Nothing saved yet');
  assert.ok(nothingIdx >= 0, '"Nothing saved yet" copy must exist');
  const emptySlice = savedShell.slice(Math.max(0, nothingIdx - 200), nothingIdx + 50);
  assert.ok(
    !emptySlice.includes('text-ds-text-inverse'),
    'empty state heading must not use text-ds-text-inverse (dark ink) on dark background'
  );
  assert.ok(
    emptySlice.includes('text-ds-text') || emptySlice.includes('text-ds-accent'),
    'empty state heading must use a light-on-dark compatible text color'
  );
});

// ── 17. Empty state sub-text: dark-background-compatible ─────────────────────

test('8N-E: empty state sub-text uses dark-background-compatible color', () => {
  const emptyIdx = savedShell.indexOf('data-testid="saved-empty"');
  const emptySlice = savedShell.slice(emptyIdx, emptyIdx + 600);
  assert.ok(
    emptySlice.includes('text-ds-text-secondary') || emptySlice.includes('text-ds-text-tertiary') ||
    emptySlice.includes('text-ds-text'),
    'empty state sub-text must use a light-on-dark compatible color'
  );
});

// ── 18. Error state: dark-background-compatible text ─────────────────────────

test('8N-E: error state text uses dark-background-compatible color', () => {
  const errorIdx = savedShell.indexOf('data-testid="saved-error"');
  const errorSlice = savedShell.slice(errorIdx, errorIdx + 400);
  // Check that a dark-background-compatible text color is present in the error state
  // Note: a "Try again" button with text-ds-text-inverse on bg-ds-bone is correct styling
  assert.ok(
    errorSlice.includes('text-ds-text-secondary') || errorSlice.includes('text-ds-warning') ||
    errorSlice.includes('text-ds-text'),
    'error state must use a dark-background-compatible text color'
  );
});

// ── 19. All key testids preserved ─────────────────────────────────────────────

test('8N-E: all key testids preserved in SavedShell', () => {
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
    const found = savedShell.includes(`data-testid="${id}"`) ||
      savedShell.includes(`data-testid={\`saved-section-`);
    assert.ok(
      savedShell.includes(`data-testid="${id}"`),
      `testid "${id}" must be preserved in SavedShell`
    );
  }
});

test('8N-E: section testid pattern preserved (saved-section-${key})', () => {
  assert.ok(
    savedShell.includes('data-testid={`saved-section-${key}`}'),
    'saved-section-${key} template testid must be preserved'
  );
});

test('8N-E: section label testid pattern preserved (saved-section-label-${key})', () => {
  assert.ok(
    savedShell.includes('data-testid={`saved-section-label-${key}`}') ||
    savedShell.includes("saved-section-label-${key}"),
    'saved-section-label-${key} template testid must be preserved'
  );
});

// ── 20. Behavioral handlers preserved ─────────────────────────────────────────

test('8N-E: all behavioral handlers preserved in SavedShell', () => {
  assert.ok(savedShell.includes('deleteSavedItem'), 'deleteSavedItem must be preserved');
  assert.ok(savedShell.includes('addSavedItemToTrip'), 'addSavedItemToTrip must be preserved');
  assert.ok(savedShell.includes('listSavedItems'), 'listSavedItems must be preserved');
  assert.ok(savedShell.includes('fetchTrips'), 'fetchTrips must be preserved');
  assert.ok(savedShell.includes('onCreateTrip(item)'), 'onCreateTrip handler must be preserved');
  assert.ok(savedShell.includes('onRemove(item.id)') || savedShell.includes('onRemove'), 'onRemove handler must be preserved');
});

test('8N-E: canAddToTrip flight exclusion preserved', () => {
  assert.ok(
    savedShell.includes('item.vertical !== "flight"') || savedShell.includes("item.vertical !== 'flight'"),
    'flight vertical must be excluded from canAddToTrip'
  );
});

test('8N-E: trip picker states preserved (picking/adding/added/error)', () => {
  assert.ok(savedShell.includes('"picking"'), 'picking state must be preserved');
  assert.ok(savedShell.includes('"adding"'), 'adding state must be preserved');
  assert.ok(savedShell.includes('"added"'), 'added state must be preserved');
  assert.ok(savedShell.includes('"error"'), 'error state must be preserved');
});

// ── 21. Modal behavioral hooks preserved ──────────────────────────────────────

test('8N-E: CreateTripFromSavedModal behavioral hooks preserved', () => {
  assert.ok(modal.includes('createTripFromSavedItem'), 'createTripFromSavedItem must be preserved');
  assert.ok(modal.includes('buildTripPrefillFromSavedItem'), 'buildTripPrefillFromSavedItem must be preserved');
  assert.ok(modal.includes('initFromPrefill'), 'initFromPrefill must be preserved');
  assert.ok(modal.includes('originSel'), 'origin selection state must be preserved');
  assert.ok(modal.includes('destSel'), 'destination selection state must be preserved');
  assert.ok(modal.includes('canSubmit'), 'canSubmit gate must be preserved');
});

test('8N-E: modal testids preserved', () => {
  assert.ok(modal.includes('data-testid="create-trip-modal"'), 'create-trip-modal testid must be preserved');
  assert.ok(modal.includes('data-testid="create-trip-form"'), 'create-trip-form testid must be preserved');
  assert.ok(modal.includes('data-testid="ct-submit"'), 'ct-submit testid must be preserved');
  assert.ok(modal.includes('data-testid="ct-error"'), 'ct-error testid must be preserved');
  assert.ok(modal.includes('data-testid="ct-unresolved-hint"'), 'ct-unresolved-hint testid must be preserved');
});

// ── 22. No backend/provider imports ───────────────────────────────────────────

test('8N-E: SavedShell has no new backend/provider imports', () => {
  assert.ok(!savedShell.includes('callConciergeSearch'), 'must not import callConciergeSearch');
  assert.ok(!savedShell.includes('/search/'), 'must not reference /search/ routes');
  assert.ok(!savedShell.includes('TripBuilder'), 'must not import TripBuilder');
  assert.ok(!savedShell.includes('searchRestaurants'), 'must not import searchRestaurants');
});

// ── 23. No new packages ────────────────────────────────────────────────────────

test('8N-E: no new packages added to package.json', () => {
  assert.ok(!pkgJson.includes('"axios"'), 'must not add axios');
  assert.ok(!pkgJson.includes('"@tanstack/react-query"'), 'must not add react-query');
  assert.ok(!pkgJson.includes('"framer-motion"'), 'must not add framer-motion');
});

// ── 24. saved-clipping-desk outer wrapper has no scrapbook-page ───────────────

test('8N-E: folio-cinema-collection wrapper does not contain scrapbook-page (Slice 4B)', () => {
  const deskIdx = savedShell.indexOf('folio-cinema-collection');
  const deskCtx = deskIdx !== -1 ? savedShell.slice(Math.max(0, deskIdx - 50), deskIdx + 200) : '';
  assert.ok(!deskCtx.includes('scrapbook-page'), 'folio-cinema-collection element must not have scrapbook-page class (Slice 4B)');
});

// ── 25. saved-clipping-card has position:relative in globals.css ─────────────

test('8N-E: .saved-clipping-card uses position:relative for pseudo-element', () => {
  const cardIdx = globals.indexOf('.saved-clipping-card');
  const cardSlice = globals.slice(cardIdx, cardIdx + 200);
  assert.ok(cardSlice.includes('position: relative') || cardSlice.includes('position:relative'), '.saved-clipping-card must use position:relative');
});

// ── 26. saved-clipping-card has ::before pseudo-element warm accent ────────────

test('8N-E: .saved-clipping-card::before defines warm top accent', () => {
  assert.ok(globals.includes('.saved-clipping-card::before'), '.saved-clipping-card::before must be defined for warm top accent');
  const pseudoIdx = globals.indexOf('.saved-clipping-card::before');
  const pseudoSlice = globals.slice(pseudoIdx, pseudoIdx + 400);
  assert.ok(
    pseudoSlice.includes('rgba(197, 148, 77') || pseudoSlice.includes('rgba(224, 184, 136'),
    '.saved-clipping-card::before must use warm brass tones for the top accent'
  );
});

// ── 27. saved-clipping-desk defined after .clipping-card in globals.css ────────

test('8N-E: .saved-clipping-desk defined after .clipping-card in globals.css', () => {
  const clippingIdx = globals.indexOf('.clipping-card {');
  const deskIdx = globals.indexOf('.saved-clipping-desk');
  assert.ok(deskIdx > clippingIdx, '.saved-clipping-desk must be defined after .clipping-card in source order');
});

// ── 28–30: stale cream-class preservation tests removed in Phase 8N-F.
// scrapbook-page, clipping-card, and boutique-folio are intentionally absent
// from Saved Ideas after the true visual correction (8N-F). These tests
// encoded the failed visual design and must not remain as acceptance criteria.

// ── editorial-section-rule still present (non-cream, structural) ─────────────

test('8N-E: editorial-section-rule still in SavedShell header', () => {
  assert.ok(savedShell.includes('editorial-section-rule'), 'editorial-section-rule must still be used in SavedShell header');
});

// ── 31. saved-scrapbook-header testid preserved ───────────────────────────────

test('8N-E: saved-scrapbook-header testid preserved (8G preservation)', () => {
  assert.ok(savedShell.includes('data-testid="saved-scrapbook-header"'), 'saved-scrapbook-header must be preserved');
});

// ── 32. saved-planning-bridge testid preserved ────────────────────────────────

test('8N-E: saved-planning-bridge testid preserved (8G preservation)', () => {
  assert.ok(savedShell.includes('data-testid="saved-planning-bridge"'), 'saved-planning-bridge must be preserved');
});

// ── 33. create-trip-btn preserved with type="button" and onClick ──────────────

test('8N-E: create-trip-btn preserved with type="button"', () => {
  const btnIdx = savedShell.indexOf('create-trip-btn');
  const slice = savedShell.slice(Math.max(0, btnIdx - 500), btnIdx + 50);
  assert.ok(slice.includes('type="button"'), 'create-trip-btn must have type="button"');
  assert.ok(slice.includes('onClick'), 'create-trip-btn must have onClick handler');
});

// ── 34. add-to-trip-btn preserved with type="button" and onClick ──────────────

test('8N-E: add-to-trip-btn preserved with type="button"', () => {
  const btnIdx = savedShell.indexOf('add-to-trip-btn');
  const slice = savedShell.slice(Math.max(0, btnIdx - 500), btnIdx + 50);
  assert.ok(slice.includes('type="button"'), 'add-to-trip-btn must have type="button"');
  assert.ok(slice.includes('onClick'), 'add-to-trip-btn must have onClick handler');
});

// ── 35. trip-picker and trip-picker-option testids preserved ─────────────────

test('8N-E: trip-picker testid preserved', () => {
  assert.ok(savedShell.includes('data-testid="trip-picker"'), 'trip-picker testid must be preserved');
});

test('8N-E: trip-picker-option testid preserved', () => {
  assert.ok(savedShell.includes('data-testid="trip-picker-option"'), 'trip-picker-option testid must be preserved');
});

// ── 36. add-to-trip-success and add-to-trip-error testids preserved ───────────

test('8N-E: add-to-trip-success testid preserved', () => {
  assert.ok(savedShell.includes('data-testid="add-to-trip-success"'), 'add-to-trip-success testid must be preserved');
});

test('8N-E: add-to-trip-error testid preserved', () => {
  assert.ok(savedShell.includes('data-testid="add-to-trip-error"'), 'add-to-trip-error testid must be preserved');
});

// ── 37. remove-saved-btn testid preserved ────────────────────────────────────

test('8N-E: remove-saved-btn testid preserved', () => {
  assert.ok(savedShell.includes('data-testid="remove-saved-btn"'), 'remove-saved-btn testid must be preserved');
});

// ── 38. loading/error/empty testids preserved ─────────────────────────────────

test('8N-E: saved-loading testid preserved', () => {
  assert.ok(savedShell.includes('data-testid="saved-loading"'), 'saved-loading testid must be preserved');
});

test('8N-E: saved-error testid preserved', () => {
  assert.ok(savedShell.includes('data-testid="saved-error"'), 'saved-error testid must be preserved');
});

test('8N-E: saved-empty testid preserved', () => {
  assert.ok(savedShell.includes('data-testid="saved-empty"'), 'saved-empty testid must be preserved');
});

// ── 39. saved-empty-explore-link testid preserved ─────────────────────────────

test('8N-E: saved-empty-explore-link testid preserved', () => {
  assert.ok(savedShell.includes('data-testid="saved-empty-explore-link"'), 'saved-empty-explore-link testid must be preserved');
});

// ── 40. create-trip-section and add-to-trip-section testids preserved ─────────

test('8N-E: create-trip-section testid preserved', () => {
  assert.ok(savedShell.includes('data-testid="create-trip-section"'), 'create-trip-section testid must be preserved');
});

test('8N-E: add-to-trip-section testid preserved', () => {
  assert.ok(savedShell.includes('data-testid="add-to-trip-section"'), 'add-to-trip-section testid must be preserved');
});

// ── 41. hotel-search-context testid preserved ────────────────────────────────

test('8N-E: hotel-search-context testid preserved', () => {
  assert.ok(savedShell.includes('data-testid="hotel-search-context"'), 'hotel-search-context testid must be preserved');
});

// ── 42. saved-card-rating testid preserved ────────────────────────────────────

test('8N-E: saved-card-rating testid preserved', () => {
  assert.ok(savedShell.includes('data-testid="saved-card-rating"'), 'saved-card-rating testid must be preserved');
});

// ── 43. No fake/hardcoded city data ───────────────────────────────────────────

test('8N-E: SavedShell has no hardcoded city Paris', () => {
  assert.ok(!savedShell.includes('"Paris"') && !savedShell.includes("'Paris'"), 'must not hardcode Paris');
});

test('8N-E: SavedShell has no hardcoded city Tokyo', () => {
  assert.ok(!savedShell.includes('"Tokyo"') && !savedShell.includes("'Tokyo'"), 'must not hardcode Tokyo');
});

// ── 44. No raw rgba() or raw hex in SavedShell ────────────────────────────────

test('8N-E: SavedShell has no raw rgba() in JSX', () => {
  const lines = savedShell.split('\n');
  const rgbaLines = lines.filter(l => l.includes('rgba(') && !l.includes('var(--'));
  assert.strictEqual(rgbaLines.length, 0, `raw rgba() found in SavedShell: ${rgbaLines.join(' | ')}`);
});

test('8N-E: SavedShell has no raw hex in className attributes', () => {
  assert.ok(
    !savedShell.match(/className[^>]*#[0-9A-Fa-f]{3,8}/),
    'must not have raw hex colors in className attributes'
  );
});

// ── 45. No legacy palette ─────────────────────────────────────────────────────

test('8N-E: SavedShell has no cream-* legacy classes', () => {
  assert.ok(!savedShell.includes('cream-1') && !savedShell.includes('cream-3') && !savedShell.includes('cream-5'), 'must not use cream-* legacy colors');
});

test('8N-E: SavedShell has no brand-* legacy classes', () => {
  assert.ok(!savedShell.includes('brand-4') && !savedShell.includes('brand-5') && !savedShell.includes('brand-6'), 'must not use brand-* legacy colors');
});

test('8N-E: SavedShell has no dark-100 legacy class', () => {
  assert.ok(!savedShell.includes('dark-100'), 'must not use bg-dark-100 legacy class');
});

// ── Touch targets preserved ───────────────────────────────────────────────────

test('8N-E: create-trip-btn has min-h-[44px] touch target', () => {
  const btnIdx = savedShell.indexOf('create-trip-btn');
  const slice = savedShell.slice(Math.max(0, btnIdx - 500), btnIdx + 50);
  assert.ok(slice.includes('min-h-[44px]'), 'create-trip-btn must have min-h-[44px]');
});

test('8N-E: add-to-trip-btn has min-h-[44px] touch target', () => {
  const btnIdx = savedShell.indexOf('add-to-trip-btn');
  const slice = savedShell.slice(Math.max(0, btnIdx - 500), btnIdx + 50);
  assert.ok(slice.includes('min-h-[44px]'), 'add-to-trip-btn must have min-h-[44px]');
});

test('8N-E: remove-saved-btn has min-h-[44px] touch target', () => {
  const removeIdx = savedShell.indexOf('remove-saved-btn');
  const slice = savedShell.slice(Math.max(0, removeIdx - 400), removeIdx + 50);
  assert.ok(slice.includes('min-h-[44px]'), 'remove-saved-btn must have min-h-[44px]');
});

test('8N-E: saved-empty-explore-link has min-h-[44px] touch target', () => {
  const exploreIdx = savedShell.indexOf('saved-empty-explore-link');
  const slice = savedShell.slice(Math.max(0, exploreIdx - 500), exploreIdx + 50);
  assert.ok(slice.includes('min-h-[44px]'), 'empty state explore link must have min-h-[44px]');
});

// ── Scrapbook composition: "Plan with this" label preserved ───────────────────

test('8N-E: planning bridge still has "Plan with this" editorial label', () => {
  assert.ok(savedShell.includes('Plan with this'), '"Plan with this" planning bridge label must be preserved');
});

// ── Hotel discovery-only preserved ───────────────────────────────────────────

test('8N-E: hotel discovery-only preserved (no per-night pricing)', () => {
  assert.ok(!savedShell.toLowerCase().includes('per night'), 'must not show per-night pricing');
});

test('8N-E: hotel checkIn and checkOut from searchContext preserved', () => {
  assert.ok(savedShell.includes('checkIn'), 'checkIn from searchContext must be preserved');
  assert.ok(savedShell.includes('checkOut'), 'checkOut from searchContext must be preserved');
});
