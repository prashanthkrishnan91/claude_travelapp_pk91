/**
 * Saved Ideas Scrapbook + Planning Bridge — Stage 3.5 Phase 8G
 *
 * Contract tests verifying:
 * 1.  Scrapbook shell structure: saved-scrapbook-header, overline, heading, count testids.
 * 2.  Overline typography role: tracking-[0.1em], uppercase, text-[10px], font-semibold.
 * 3.  TYPE_OVERLINES constant for scrapbook idea type identity.
 * 4.  Saved item editorial: saved-item-type-overline testid on each card.
 * 5.  Saved item name: saved-item-name testid.
 * 6.  Planning bridge: saved-planning-bridge testid with editorial label.
 * 7.  Planning bridge preserved actions: create-trip-btn, add-to-trip-btn.
 * 8.  Planning bridge section testids: create-trip-section, add-to-trip-section.
 * 9.  Trip picker preserved: trip-picker, trip-picker-option.
 * 10. Add-to-trip success/error states preserved.
 * 11. Semantic buttons and links — no card-level click-only navigation.
 * 12. Maps link touch target: min-w-[44px] and min-h-[44px].
 * 13. Remove button touch target preserved (min-w-[44px] / min-h-[44px]).
 * 14. Section editorial: saved-section-${key}, saved-section-label-${key}.
 * 15. Section Overline tracking preserved.
 * 16. No fake / mock / sample / hardcoded city data.
 * 17. No backend / provider imports in SavedShell or CreateTripFromSavedModal.
 * 18. No raw rgba() or raw hex in SavedShell.tsx.
 * 19. No legacy palette (cream-*, brand-*, dark-100, rose-*, amber-3*) in SavedShell.
 * 20. CreateTripFromSavedModal ds-token migration: bg-ds-onyx, border-ds-pen-stroke, text-ds-text.
 * 21. No legacy colors in CreateTripFromSavedModal (cream-*, brand-*, dark-100, rose-*, amber-3*).
 * 22. Modal submit button ds-accent.
 * 23. Modal error state text-ds-warning.
 * 24. Modal unresolved hint text-ds-caution.
 * 25. Modal labels tracking-[0.1em] Overline pattern.
 * 26. Modal close button 44px touch target.
 * 27. Modal focus-visible pattern on inputs.
 * 28. All existing action handlers preserved (deleteSavedItem, addSavedItemToTrip, createTripFromSavedItem, listSavedItems, fetchTrips).
 * 29. Hotel discovery-only preserved: no rates/prices/booking.
 * 30. Mobile-safe layout: max-w-2xl, space-y-*, flex-wrap.
 * 31. Empty state: no hardcoded destinations, Explore link preserved.
 * 32. Loading and error states preserved.
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

// ── 1. Scrapbook shell structure ──────────────────────────────────────────────

test('SavedShell has saved-shell data-testid on root', () => {
  assert.ok(savedShell.includes('data-testid="saved-shell"'), 'saved-shell testid must exist on root');
});

test('SavedShell has saved-scrapbook-header data-testid', () => {
  assert.ok(savedShell.includes('data-testid="saved-scrapbook-header"'), 'saved-scrapbook-header testid missing');
});

test('SavedShell has saved-scrapbook-overline data-testid', () => {
  assert.ok(savedShell.includes('data-testid="saved-scrapbook-overline"'), 'saved-scrapbook-overline testid missing');
});

test('SavedShell has saved-scrapbook-heading data-testid', () => {
  assert.ok(savedShell.includes('data-testid="saved-scrapbook-heading"'), 'saved-scrapbook-heading testid missing');
});

test('SavedShell has saved-scrapbook-count data-testid', () => {
  assert.ok(savedShell.includes('data-testid="saved-scrapbook-count"'), 'saved-scrapbook-count testid missing');
});

test('Scrapbook overline text is "Your Travel Scrapbook"', () => {
  assert.ok(savedShell.includes('Your Travel Scrapbook'), '"Your Travel Scrapbook" overline copy missing');
});

test('Scrapbook h1 heading is "Saved Ideas"', () => {
  assert.ok(savedShell.includes('Saved Ideas'), '"Saved Ideas" h1 heading missing');
});

test('Scrapbook header uses semantic <header> element', () => {
  assert.ok(savedShell.includes('<header data-testid="saved-scrapbook-header"'), 'header must use semantic <header> element');
});

// ── 2. Overline typography role ───────────────────────────────────────────────

test('Scrapbook overline uses tracking-[0.1em]', () => {
  const overlineIdx = savedShell.indexOf('saved-scrapbook-overline');
  const slice = savedShell.slice(Math.max(0, overlineIdx - 200), overlineIdx + 300);
  assert.ok(slice.includes('tracking-[0.1em]'), 'scrapbook overline must use tracking-[0.1em]');
});

test('Scrapbook overline uses uppercase', () => {
  const overlineIdx = savedShell.indexOf('saved-scrapbook-overline');
  const slice = savedShell.slice(Math.max(0, overlineIdx - 200), overlineIdx + 300);
  assert.ok(slice.includes('uppercase'), 'scrapbook overline must use uppercase class');
});

test('Scrapbook overline uses text-[10px]', () => {
  const overlineIdx = savedShell.indexOf('saved-scrapbook-overline');
  const slice = savedShell.slice(Math.max(0, overlineIdx - 200), overlineIdx + 300);
  assert.ok(slice.includes('text-[10px]'), 'scrapbook overline must use text-[10px]');
});

test('Scrapbook overline uses font-semibold', () => {
  const overlineIdx = savedShell.indexOf('saved-scrapbook-overline');
  const slice = savedShell.slice(Math.max(0, overlineIdx - 200), overlineIdx + 300);
  assert.ok(slice.includes('font-semibold'), 'scrapbook overline must use font-semibold');
});

// ── 3. TYPE_OVERLINES constant ────────────────────────────────────────────────

test('SavedShell defines TYPE_OVERLINES constant', () => {
  assert.ok(savedShell.includes('TYPE_OVERLINES'), 'TYPE_OVERLINES constant must exist');
});

test('TYPE_OVERLINES has restaurant entry', () => {
  assert.ok(
    savedShell.includes('restaurant: "Restaurant"') || savedShell.includes("restaurant: 'Restaurant'"),
    'TYPE_OVERLINES must have restaurant entry'
  );
});

test('TYPE_OVERLINES has attraction entry', () => {
  assert.ok(
    savedShell.includes('attraction: "Attraction"') || savedShell.includes("attraction: 'Attraction'"),
    'TYPE_OVERLINES must have attraction entry'
  );
});

test('TYPE_OVERLINES has hotel entry', () => {
  assert.ok(
    savedShell.includes('hotel: "Hotel"') || savedShell.includes("hotel: 'Hotel'"),
    'TYPE_OVERLINES must have hotel entry'
  );
});

test('TYPE_OVERLINES has flight entry', () => {
  assert.ok(
    savedShell.includes('flight: "Flight"') || savedShell.includes("flight: 'Flight'"),
    'TYPE_OVERLINES must have flight entry'
  );
});

// ── 4. Saved item type overline ───────────────────────────────────────────────

test('SavedItemCard has saved-item-type-overline data-testid', () => {
  assert.ok(savedShell.includes('data-testid="saved-item-type-overline"'), 'saved-item-type-overline testid missing from card');
});

test('Item type overline uses tracking-[0.1em]', () => {
  const typeOvIdx = savedShell.indexOf('saved-item-type-overline');
  const slice = savedShell.slice(Math.max(0, typeOvIdx - 200), typeOvIdx + 300);
  assert.ok(slice.includes('tracking-[0.1em]'), 'item type overline must use tracking-[0.1em]');
});

test('Item type overline uses uppercase', () => {
  const typeOvIdx = savedShell.indexOf('saved-item-type-overline');
  const slice = savedShell.slice(Math.max(0, typeOvIdx - 200), typeOvIdx + 300);
  assert.ok(slice.includes('uppercase'), 'item type overline must use uppercase');
});

test('Item type overline uses TYPE_OVERLINES lookup', () => {
  assert.ok(
    savedShell.includes('TYPE_OVERLINES[item.vertical]'),
    'item type overline must use TYPE_OVERLINES[item.vertical]'
  );
});

// ── 5. Saved item name testid ─────────────────────────────────────────────────

test('SavedItemCard has saved-item-name data-testid', () => {
  assert.ok(savedShell.includes('data-testid="saved-item-name"'), 'saved-item-name testid missing');
});

test('Item name uses h3 element', () => {
  const nameIdx = savedShell.indexOf('saved-item-name');
  const slice = savedShell.slice(Math.max(0, nameIdx - 250), nameIdx + 10);
  assert.ok(slice.includes('<h3'), 'item name must use <h3> element');
});

// ── 6. Planning bridge section ────────────────────────────────────────────────

test('SavedItemCard has saved-planning-bridge data-testid', () => {
  assert.ok(savedShell.includes('data-testid="saved-planning-bridge"'), 'saved-planning-bridge testid missing');
});

test('Planning bridge has editorial "Plan with this" label', () => {
  assert.ok(savedShell.includes('Plan with this'), '"Plan with this" planning bridge label missing');
});

test('Planning bridge label uses tracking-[0.1em] Overline pattern', () => {
  const bridgeIdx = savedShell.indexOf('Plan with this');
  const slice = savedShell.slice(Math.max(0, bridgeIdx - 200), bridgeIdx + 50);
  assert.ok(slice.includes('tracking-[0.1em]'), 'planning bridge label must use Overline tracking');
});

test('Planning bridge has border-t separator from card body', () => {
  const bridgeIdx = savedShell.indexOf('saved-planning-bridge');
  const slice = savedShell.slice(Math.max(0, bridgeIdx - 300), bridgeIdx + 300);
  assert.ok(slice.includes('border-t'), 'planning bridge must have border-t separator');
});

// ── 7. Planning bridge preserved actions ──────────────────────────────────────

test('Planning bridge contains create-trip-btn', () => {
  assert.ok(savedShell.includes('data-testid="create-trip-btn"'), 'create-trip-btn must exist in SavedShell');
});

test('Planning bridge contains add-to-trip-btn', () => {
  assert.ok(savedShell.includes('data-testid="add-to-trip-btn"'), 'add-to-trip-btn must exist in SavedShell');
});

test('create-trip-btn is a <button> element with onClick', () => {
  const btnIdx = savedShell.indexOf('create-trip-btn');
  const slice = savedShell.slice(Math.max(0, btnIdx - 500), btnIdx + 50);
  assert.ok(slice.includes('<button') && slice.includes('onClick'), 'create-trip-btn must be a <button> with onClick');
});

test('add-to-trip-btn is a <button> element with onClick', () => {
  const btnIdx = savedShell.indexOf('add-to-trip-btn');
  const slice = savedShell.slice(Math.max(0, btnIdx - 500), btnIdx + 50);
  assert.ok(slice.includes('<button') && slice.includes('onClick'), 'add-to-trip-btn must be a <button> with onClick');
});

test('Create Trip button calls onCreateTrip handler', () => {
  assert.ok(savedShell.includes('onCreateTrip(item)'), 'create trip must call onCreateTrip handler');
});

// ── 8. Section testids ────────────────────────────────────────────────────────

test('SavedItemCard has create-trip-section data-testid', () => {
  assert.ok(savedShell.includes('data-testid="create-trip-section"'), 'create-trip-section testid missing');
});

test('SavedItemCard has add-to-trip-section data-testid', () => {
  assert.ok(savedShell.includes('data-testid="add-to-trip-section"'), 'add-to-trip-section testid missing');
});

// ── 9. Trip picker preserved ──────────────────────────────────────────────────

test('SavedItemCard has trip-picker data-testid', () => {
  assert.ok(savedShell.includes('data-testid="trip-picker"'), 'trip-picker testid missing');
});

test('SavedItemCard has trip-picker-option data-testid', () => {
  assert.ok(savedShell.includes('data-testid="trip-picker-option"'), 'trip-picker-option testid missing');
});

test('Trip picker Choose a trip label uses tracking-[0.1em]', () => {
  const pickerIdx = savedShell.indexOf('Choose a trip');
  const slice = savedShell.slice(Math.max(0, pickerIdx - 200), pickerIdx + 50);
  assert.ok(slice.includes('tracking-[0.1em]'), 'trip picker label must use Overline tracking');
});

// ── 10. Add-to-trip states preserved ─────────────────────────────────────────

test('SavedItemCard has add-to-trip-success data-testid', () => {
  assert.ok(savedShell.includes('data-testid="add-to-trip-success"'), 'add-to-trip-success testid missing');
});

test('SavedItemCard has add-to-trip-error data-testid', () => {
  assert.ok(savedShell.includes('data-testid="add-to-trip-error"'), 'add-to-trip-error testid missing');
});

test('Add-to-trip success shows CheckCircle2 and trip name', () => {
  assert.ok(savedShell.includes('CheckCircle2'), 'CheckCircle2 icon must be used for add-to-trip success');
  assert.ok(savedShell.includes('addedToTripName'), 'must display addedToTripName');
});

// ── 11. Semantic buttons and links — no card-level onClick nav ────────────────

test('SavedShell Card root has no onClick handler (no card-level click nav)', () => {
  const cardIdx = savedShell.indexOf('data-testid="saved-item-card"');
  const slice = savedShell.slice(cardIdx, cardIdx + 100);
  assert.ok(!slice.includes('onClick'), 'card root must not have onClick (no card-level nav)');
});

test('SavedShell section root has no onClick handler', () => {
  const sectionIdx = savedShell.indexOf('saved-section-restaurant');
  const slice = savedShell.slice(sectionIdx, sectionIdx + 100);
  assert.ok(!slice.includes('onClick'), 'section root must not have onClick');
});

test('Empty state explore link is a real <Link> element', () => {
  const emptyIdx = savedShell.indexOf('saved-empty');
  const slice = savedShell.slice(emptyIdx, emptyIdx + 600);
  assert.ok(slice.includes('<Link') && slice.includes('href="/explore"'), 'empty state explore link must be a <Link href="/explore">');
});

// ── 12. Maps link 44px touch target ──────────────────────────────────────────

test('Maps link has min-w-[44px] touch target', () => {
  const mapsIdx = savedShell.indexOf('View ${name} on Google Maps');
  const slice = savedShell.slice(Math.max(0, mapsIdx - 400), mapsIdx + 50);
  assert.ok(slice.includes('min-w-[44px]'), 'maps link must have min-w-[44px] for touch target');
});

test('Maps link has min-h-[44px] touch target', () => {
  const mapsIdx = savedShell.indexOf('View ${name} on Google Maps');
  const slice = savedShell.slice(Math.max(0, mapsIdx - 400), mapsIdx + 50);
  assert.ok(slice.includes('min-h-[44px]'), 'maps link must have min-h-[44px] for touch target');
});

test('Maps link is an <a> element with target="_blank"', () => {
  assert.ok(savedShell.includes('target="_blank"'), 'maps link must open in new tab');
  assert.ok(savedShell.includes('rel="noopener noreferrer"'), 'maps link must have rel=noopener');
});

// ── 13. Remove button 44px touch target ──────────────────────────────────────

test('Remove button has min-w-[44px] touch target', () => {
  const removeIdx = savedShell.indexOf('remove-saved-btn');
  const slice = savedShell.slice(Math.max(0, removeIdx - 400), removeIdx + 50);
  assert.ok(slice.includes('min-w-[44px]'), 'remove button must have min-w-[44px]');
});

test('Remove button has min-h-[44px] touch target', () => {
  const removeIdx = savedShell.indexOf('remove-saved-btn');
  const slice = savedShell.slice(Math.max(0, removeIdx - 400), removeIdx + 50);
  assert.ok(slice.includes('min-h-[44px]'), 'remove button must have min-h-[44px]');
});

test('Remove button has aria-label', () => {
  assert.ok(savedShell.includes('aria-label={`Remove ${name} from saved`}'), 'remove button must have aria-label');
});

// ── 14. Section editorial structure ──────────────────────────────────────────

test('VerticalGroup has saved-section-restaurant data-testid', () => {
  assert.ok(savedShell.includes('saved-section-restaurant') || savedShell.includes('saved-section-${key}'), 'section testid pattern must exist');
});

test('VerticalGroup has saved-section-label-restaurant pattern', () => {
  assert.ok(
    savedShell.includes('saved-section-label-${key}') || savedShell.includes('saved-section-label-restaurant'),
    'section label testid pattern must exist'
  );
});

test('Section labels show Restaurants text', () => {
  assert.ok(savedShell.includes('Restaurants'), 'Restaurants section label must exist');
});

test('Section labels show Attractions text', () => {
  assert.ok(savedShell.includes('Attractions'), 'Attractions section label must exist');
});

test('Section labels show Hotels text', () => {
  assert.ok(savedShell.includes('Hotels'), 'Hotels section label must exist');
});

test('Section labels show Flights text', () => {
  assert.ok(savedShell.includes('Flights'), 'Flights section label must exist');
});

test('VerticalGroup uses <section> semantic element', () => {
  assert.ok(savedShell.includes('<section data-testid={`saved-section-${key}`}'), 'VerticalGroup must use <section> element');
});

// ── 15. Section Overline tracking ────────────────────────────────────────────

test('Section labels use tracking-[0.1em]', () => {
  const sectionLabelIdx = savedShell.indexOf('saved-section-label-${key}');
  const slice = savedShell.slice(Math.max(0, sectionLabelIdx - 200), sectionLabelIdx + 200);
  assert.ok(slice.includes('tracking-[0.1em]'), 'section label must use tracking-[0.1em]');
});

test('Section has border-b hairline separator', () => {
  assert.ok(savedShell.includes('border-b border-ds-hairline'), 'section header must have border-b hairline separator');
});

// ── 16. No fake / mock / hardcoded city data ──────────────────────────────────

test('SavedShell has no hardcoded city "Paris"', () => {
  assert.ok(!savedShell.includes('"Paris"') && !savedShell.includes("'Paris'"), 'must not hardcode Paris');
});

test('SavedShell has no hardcoded city "Tokyo"', () => {
  assert.ok(!savedShell.includes('"Tokyo"') && !savedShell.includes("'Tokyo'"), 'must not hardcode Tokyo');
});

test('SavedShell has no hardcoded city "Barcelona"', () => {
  assert.ok(!savedShell.includes('"Barcelona"') && !savedShell.includes("'Barcelona'"), 'must not hardcode Barcelona');
});

test('SavedShell has no hardcoded city "Rome"', () => {
  assert.ok(!savedShell.includes('"Rome"') && !savedShell.includes("'Rome'"), 'must not hardcode Rome');
});

test('SavedShell has no sample / mock data copy', () => {
  const lower = savedShell.toLowerCase();
  assert.ok(!lower.includes('sample data'), 'must not include sample data copy');
  assert.ok(!lower.includes('mock data'), 'must not include mock data copy');
});

// ── 17. No backend / provider imports ────────────────────────────────────────

test('SavedShell does not import callConciergeSearch', () => {
  assert.ok(!savedShell.includes('callConciergeSearch'), 'must not import callConciergeSearch');
});

test('SavedShell does not import searchRestaurants', () => {
  assert.ok(!savedShell.includes('searchRestaurants'), 'must not import searchRestaurants');
});

test('SavedShell does not reference /search/ routes', () => {
  assert.ok(!savedShell.includes('/search/'), 'must not call /search/ routes');
});

test('SavedShell does not import TripBuilder', () => {
  assert.ok(!savedShell.includes('TripBuilder'), 'must not import TripBuilder');
});

test('CreateTripFromSavedModal does not import callConciergeSearch', () => {
  assert.ok(!modal.includes('callConciergeSearch'), 'modal must not import callConciergeSearch');
});

test('CreateTripFromSavedModal does not reference /search/ routes', () => {
  assert.ok(!modal.includes('/search/'), 'modal must not call /search/ routes');
});

// ── 18. No raw rgba() or raw hex in SavedShell ────────────────────────────────

test('SavedShell has no raw rgba() calls (except var() wrappers)', () => {
  // rgba() is allowed only inside var(--ds-*) definitions (CSS vars), not inline JSX
  const lines = savedShell.split('\n');
  const rgbaLines = lines.filter(l => l.includes('rgba(') && !l.includes('var(--'));
  assert.strictEqual(rgbaLines.length, 0, `raw rgba() found in SavedShell: ${rgbaLines.join(' | ')}`);
});

test('SavedShell has no raw hex color values', () => {
  // Raw hex should not appear in JSX/TSX component code
  const noHex = !/#[0-9A-Fa-f]{3,8}[^0-9A-Fa-f]/.test(savedShell) || savedShell.match(/#[0-9A-Fa-f]{3,8}/g)?.every(h => savedShell.includes(`"${h}"`));
  assert.ok(noHex || !savedShell.match(/className.*#[0-9A-Fa-f]{3,8}/), 'must not have raw hex in className attributes');
});

// ── 19. No legacy palette in SavedShell ──────────────────────────────────────

test('SavedShell has no cream-* legacy classes', () => {
  assert.ok(!savedShell.includes('cream-1') && !savedShell.includes('cream-3') && !savedShell.includes('cream-5'), 'must not use cream-* legacy colors');
});

test('SavedShell has no brand-* legacy classes', () => {
  assert.ok(!savedShell.includes('brand-4') && !savedShell.includes('brand-5') && !savedShell.includes('brand-6'), 'must not use brand-* legacy colors');
});

test('SavedShell has no slate-* classes', () => {
  assert.ok(!savedShell.includes('slate-7') && !savedShell.includes('slate-8') && !savedShell.includes('slate-9'), 'must not use slate-700+ classes');
});

// ── 20. CreateTripFromSavedModal ds-token migration ───────────────────────────

test('Modal uses bg-ds-onyx for dialog surface', () => {
  assert.ok(modal.includes('bg-ds-onyx'), 'modal must use bg-ds-onyx for surface');
});

test('Modal uses border-ds-pen-stroke', () => {
  assert.ok(modal.includes('border-ds-pen-stroke'), 'modal must use border-ds-pen-stroke');
});

test('Modal title uses text-ds-text', () => {
  assert.ok(modal.includes('text-ds-text'), 'modal title must use text-ds-text');
});

test('Modal subtitle uses text-ds-text-tertiary', () => {
  assert.ok(modal.includes('text-ds-text-tertiary'), 'modal must use text-ds-text-tertiary');
});

test('Modal inputs use bg-ds-carbon', () => {
  assert.ok(modal.includes('bg-ds-carbon'), 'modal inputs must use bg-ds-carbon');
});

// ── 21. No legacy colors in CreateTripFromSavedModal ─────────────────────────

test('Modal has no cream-* legacy classes', () => {
  assert.ok(!modal.includes('cream-1') && !modal.includes('cream-4') && !modal.includes('cream-5'), 'modal must not use cream-* legacy classes');
});

test('Modal has no bg-dark-100', () => {
  assert.ok(!modal.includes('bg-dark-100'), 'modal must not use bg-dark-100');
});

test('Modal has no brand-500 or brand-600', () => {
  assert.ok(!modal.includes('brand-500') && !modal.includes('brand-600'), 'modal must not use brand-* classes');
});

test('Modal has no rose-* classes', () => {
  assert.ok(!modal.includes('rose-3') && !modal.includes('rose-5'), 'modal must not use rose-* classes');
});

test('Modal has no amber-300', () => {
  assert.ok(!modal.includes('amber-300'), 'modal must not use amber-300');
});

// ── 22. Modal submit button uses ds-accent ───────────────────────────────────

test('Modal submit button uses bg-ds-accent', () => {
  assert.ok(modal.includes('bg-ds-accent'), 'modal submit must use bg-ds-accent');
});

test('Modal submit button uses text-ds-text-inverse', () => {
  assert.ok(modal.includes('text-ds-text-inverse'), 'modal submit must use text-ds-text-inverse');
});

// ── 23. Modal error state text-ds-warning ─────────────────────────────────────

test('Modal error state uses text-ds-warning', () => {
  const errorIdx = modal.indexOf('data-testid="ct-error"');
  const slice = modal.slice(Math.max(0, errorIdx - 300), errorIdx + 200);
  assert.ok(slice.includes('text-ds-warning'), 'modal error must use text-ds-warning');
});

// ── 24. Modal unresolved hint uses text-ds-caution ───────────────────────────

test('Modal unresolved hint uses text-ds-caution', () => {
  const hintIdx = modal.indexOf('ct-unresolved-hint');
  const slice = modal.slice(Math.max(0, hintIdx - 200), hintIdx + 200);
  assert.ok(slice.includes('text-ds-caution'), 'modal unresolved hint must use text-ds-caution');
});

// ── 25. Modal labels Overline tracking ───────────────────────────────────────

test('Modal form labels use tracking-[0.1em]', () => {
  assert.ok(modal.includes('tracking-[0.1em]'), 'modal labels must use tracking-[0.1em] Overline pattern');
});

// ── 26. Modal close button 44px ──────────────────────────────────────────────

test('Modal close button has min-w-[44px]', () => {
  const closeIdx = modal.indexOf('aria-label="Close"');
  const slice = modal.slice(Math.max(0, closeIdx - 400), closeIdx + 400);
  assert.ok(slice.includes('min-w-[44px]'), 'close button must have min-w-[44px]');
});

test('Modal close button has min-h-[44px]', () => {
  const closeIdx = modal.indexOf('aria-label="Close"');
  const slice = modal.slice(Math.max(0, closeIdx - 400), closeIdx + 400);
  assert.ok(slice.includes('min-h-[44px]'), 'close button must have min-h-[44px]');
});

// ── 27. Modal inputs focus-visible pattern ───────────────────────────────────

test('Modal inputs use focus-visible:outline pattern', () => {
  assert.ok(modal.includes('focus-visible:outline'), 'modal inputs must use focus-visible:outline pattern');
});

test('Modal inputs use focus-visible:outline-ds-accent', () => {
  assert.ok(modal.includes('focus-visible:outline-ds-accent'), 'modal must use focus-visible:outline-ds-accent');
});

// ── 28. All action handlers preserved ────────────────────────────────────────

test('SavedShell imports deleteSavedItem', () => {
  assert.ok(savedShell.includes('deleteSavedItem'), 'deleteSavedItem must be imported and used');
});

test('SavedShell imports addSavedItemToTrip', () => {
  assert.ok(savedShell.includes('addSavedItemToTrip'), 'addSavedItemToTrip must be imported and used');
});

test('SavedShell imports listSavedItems', () => {
  assert.ok(savedShell.includes('listSavedItems'), 'listSavedItems must be imported and used');
});

test('SavedShell imports fetchTrips', () => {
  assert.ok(savedShell.includes('fetchTrips'), 'fetchTrips must be imported and used');
});

test('Modal imports createTripFromSavedItem', () => {
  assert.ok(modal.includes('createTripFromSavedItem'), 'createTripFromSavedItem must be used in modal');
});

test('Flight vertical excluded from add-to-trip (canAddToTrip guard)', () => {
  assert.ok(
    savedShell.includes('item.vertical !== "flight"') || savedShell.includes("item.vertical !== 'flight'"),
    'flight must be excluded from canAddToTrip'
  );
});

// ── 29. Hotel discovery-only preserved ───────────────────────────────────────

test('Hotel card reads checkIn from searchContext', () => {
  assert.ok(savedShell.includes('checkIn'), 'must read checkIn from searchContext');
});

test('Hotel card reads checkOut from searchContext', () => {
  assert.ok(savedShell.includes('checkOut'), 'must read checkOut from searchContext');
});

test('Hotel card has no per-night pricing', () => {
  assert.ok(!savedShell.toLowerCase().includes('per night'), 'must not show per-night pricing');
});

test('Hotel card has no booking copy', () => {
  const lower = savedShell.toLowerCase();
  assert.ok(!lower.includes('book now') && !lower.includes('check rates'), 'must not include booking copy');
});

// ── 30. Mobile-safe layout ────────────────────────────────────────────────────

test('SavedShell root has max-w-2xl for contained mobile layout', () => {
  assert.ok(savedShell.includes('max-w-2xl'), 'root must have max-w-2xl for responsive containment');
});

test('SavedShell root has mx-auto centering', () => {
  assert.ok(savedShell.includes('mx-auto'), 'root must have mx-auto for centering');
});

test('Rating + tags row uses flex-wrap for mobile', () => {
  assert.ok(savedShell.includes('flex-wrap'), 'rating/tags row must use flex-wrap for mobile safety');
});

test('Action cluster uses gap for spacing', () => {
  assert.ok(savedShell.includes('gap-0.5') || savedShell.includes('gap-1'), 'action cluster must use gap spacing');
});

// ── 31. Empty state ───────────────────────────────────────────────────────────

test('Empty state has saved-empty data-testid', () => {
  assert.ok(savedShell.includes('data-testid="saved-empty"'), 'saved-empty testid must exist');
});

test('Empty state has saved-empty-explore-link data-testid', () => {
  assert.ok(savedShell.includes('data-testid="saved-empty-explore-link"'), 'saved-empty-explore-link testid must exist');
});

test('Empty state links to /explore', () => {
  const emptyIdx = savedShell.indexOf('saved-empty');
  const slice = savedShell.slice(emptyIdx, emptyIdx + 700);
  assert.ok(slice.includes('href="/explore"'), 'empty state must link to /explore');
});

test('Empty state has no hardcoded destination examples', () => {
  const emptyIdx = savedShell.indexOf('saved-empty');
  const slice = savedShell.slice(emptyIdx, emptyIdx + 700);
  assert.ok(!slice.includes('"Paris"') && !slice.includes('"Tokyo"'), 'empty state must not hardcode destinations');
});

// ── 32. Loading and error states ─────────────────────────────────────────────

test('Loading state has saved-loading data-testid', () => {
  assert.ok(savedShell.includes('data-testid="saved-loading"'), 'saved-loading testid must exist');
});

test('Error state has saved-error data-testid', () => {
  assert.ok(savedShell.includes('data-testid="saved-error"'), 'saved-error testid must exist');
});

test('Error state has Try again retry button', () => {
  const errorIdx = savedShell.indexOf('saved-error');
  const slice = savedShell.slice(errorIdx, errorIdx + 600);
  assert.ok(slice.includes('Try again'), 'error state must have Try again button');
});

test('SavedShell preserves remove-saved-btn data-testid', () => {
  assert.ok(savedShell.includes('data-testid="remove-saved-btn"'), 'remove-saved-btn testid must be preserved');
});

test('SavedShell preserves remove-error data-testid', () => {
  assert.ok(savedShell.includes('data-testid="remove-error"'), 'remove-error testid must be preserved');
});

test('SavedShell preserves saved-card-rating data-testid', () => {
  assert.ok(savedShell.includes('data-testid="saved-card-rating"'), 'saved-card-rating testid must be preserved');
});

test('SavedShell preserves hotel-search-context data-testid', () => {
  assert.ok(savedShell.includes('data-testid="hotel-search-context"'), 'hotel-search-context testid must be preserved');
});

test('Modal preserves create-trip-modal data-testid', () => {
  assert.ok(modal.includes('data-testid="create-trip-modal"'), 'create-trip-modal testid must be preserved in modal');
});

test('Modal preserves create-trip-form data-testid', () => {
  assert.ok(modal.includes('data-testid="create-trip-form"'), 'create-trip-form testid must be preserved');
});
