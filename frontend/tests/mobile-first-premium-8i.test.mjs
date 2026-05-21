/**
 * Stage 3.5 Phase 8I — Mobile-First Premium Pass
 *
 * Contract tests verifying:
 * 1.  TripBuilder uses responsive flex-col → lg:flex-row stacking (not bare horizontal flex).
 * 2.  TripBuilder candidate panel uses lg:w-80 (full-width on mobile, 320px on lg+).
 * 3.  TripBuilder candidate panel uses lg:flex-shrink-0 (not bare flex-shrink-0).
 * 4.  TripBuilder compare bar has max-w constraint preventing mobile overflow.
 * 5.  HotelExploreFlow date/guests row uses sm:grid-cols-3 (not bare grid-cols-3).
 * 6.  HotelExploreFlow form uses grid grid-cols-1 sm:grid-cols-3.
 * 7.  AttractionExploreFlow form row uses flex flex-col sm:flex-row (not bare flex gap-3 only).
 * 8.  AttractionExploreFlow interest input uses sm:w-44 (not bare w-44 without breakpoint).
 * 9.  AttractionExploreFlow search button has w-full sm:w-auto for mobile full-width.
 * 10. TripDetail edit modal close button has min-h-[44px] touch target.
 * 11. TripDetail edit modal close button has min-w-[44px] touch target.
 * 12. TripDetail edit modal inputs use focus-visible:outline pattern (not focus:ring-*).
 * 13. TripDetail chapter cover uses responsive horizontal padding (sm:px-6).
 * 14. ConciergePage header uses responsive padding classes (not inline paddingBottom only).
 * 15. ConciergePage header uses pb-5 mobile padding.
 * 16. ConciergePage header uses sm:pb-8 desktop padding.
 * 17. AIConciergePanel Clear button has min-h-[44px] touch target.
 * 18. ExploreShell active section uses responsive padding (p-4 sm:p-6) not inline only.
 * 19. TripBuilder preserves google-flights-cta testid (behavior unchanged).
 * 20. TripBuilder preserves flight-add-btn testid (behavior unchanged).
 * 21. TripBuilder preserves handleAddCandidateToItinerary handler.
 * 22. AIConciergePanel preserves concierge-panel-clear testid.
 * 23. AIConciergePanel preserves concierge-panel-close testid.
 * 24. AIConciergePanel preserves concierge-panel-submit testid.
 * 25. TripDetail preserves chapter-actions testid.
 * 26. TripDetail preserves chapter-action-concierge testid.
 * 27. TripDetail preserves chapter-action-edit testid.
 * 28. No backend/provider imports in TripBuilder.
 * 29. No backend/provider imports in HotelExploreFlow.
 * 30. No backend/provider imports in AttractionExploreFlow.
 * 31. No fake/hardcoded city examples in HotelExploreFlow.
 * 32. No fake/hardcoded city examples in AttractionExploreFlow.
 * 33. TripBuilder does not use bare w-80 flex-shrink-0 (mobile-unsafe pattern).
 * 34. TripDetail edit modal inputs do not use focus:ring-* (legacy pattern).
 * 35. AttractionExploreFlow search form has type="submit" (semantic button).
 * 36. HotelExploreFlow search form has type="submit" (semantic button).
 * 37. ConciergePage preserves concierge-query-input testid.
 * 38. ConciergePage preserves concierge-submit-button testid.
 * 39. ConciergePage preserves concierge-destination-field testid.
 * 40. No nested interactive controls in TripBuilder candidate panel.
 * 41. AIConciergePanel has no bare focus:ring-* pattern on clear/close buttons.
 * 42. TripBuilder does not use bare flex items-start gap-4 without mobile stacking.
 * 43. HotelExploreFlow no hardcoded city placeholder text (Paris, Tokyo, etc.).
 * 44. ExploreShell preserves explore-lounge-header testid.
 * 45. ExploreShell preserves explore-lounge-breadcrumb testid.
 * 46. ExploreShell active flow section has no inline padding style (converted to class).
 * 47. TripDetail chapter cover section has responsive px-4 sm:px-6.
 * 48. TripBuilder preserves DnD behavior (DndContext import).
 * 49. ConciergePage preserves callConciergeSearch handler.
 * 50. AIConciergePanel preserves addStructuredConciergeItemToTrip handler.
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

const tripBuilder       = read('src/components/trips/TripBuilder.tsx');
const hotelFlow         = read('src/components/explore/HotelExploreFlow.tsx');
const attractionFlow    = read('src/components/explore/AttractionExploreFlow.tsx');
const tripDetailPage    = read('src/app/trips/[id]/page.tsx');
const conciergePage     = read('src/components/concierge/ConciergePage.tsx');
const conciergePanel    = read('src/components/trips/AIConciergePanel.tsx');
const exploreShell      = read('src/components/explore/ExploreShell.tsx');

// ── 1–4. TripBuilder mobile layout ───────────────────────────────────────────

test('TripBuilder uses lg:flex-row for responsive layout (mobile stacks vertically)', () => {
  assert.ok(tripBuilder.includes('lg:flex-row'), 'TripBuilder main container must use lg:flex-row for mobile-first stacking');
});

test('TripBuilder uses flex flex-col for base mobile layout', () => {
  assert.ok(tripBuilder.includes('flex flex-col') && tripBuilder.includes('lg:flex-row'),
    'TripBuilder must start as flex-col and switch to flex-row at lg breakpoint');
});

test('TripBuilder candidate panel uses lg:w-80 (full-width on mobile)', () => {
  assert.ok(tripBuilder.includes('lg:w-80'), 'Candidate panel must use lg:w-80 so it is full-width on mobile');
});

test('TripBuilder candidate panel uses lg:flex-shrink-0 (not bare flex-shrink-0)', () => {
  assert.ok(tripBuilder.includes('lg:flex-shrink-0'), 'Candidate panel must use lg:flex-shrink-0');
  assert.ok(!tripBuilder.includes('"w-80 flex-shrink-0'), 'Must not use bare w-80 flex-shrink-0 without lg prefix');
});

test('TripBuilder compare bar has max-w constraint preventing mobile overflow', () => {
  assert.ok(tripBuilder.includes('max-w-[calc(100vw-2rem)]'),
    'Compare bar must be constrained by max-w-[calc(100vw-2rem)] to prevent mobile horizontal overflow');
});

// ── 5–6. HotelExploreFlow mobile form ────────────────────────────────────────

test('HotelExploreFlow date/guests row uses sm:grid-cols-3 (not bare grid-cols-3)', () => {
  assert.ok(hotelFlow.includes('sm:grid-cols-3'),
    'Hotel form date/guests row must use sm:grid-cols-3 to stack on mobile');
  assert.ok(!hotelFlow.match(/"grid grid-cols-3/),
    'Must not use bare grid-cols-3 without breakpoint — cramped on mobile');
});

test('HotelExploreFlow form uses grid grid-cols-1 sm:grid-cols-3', () => {
  assert.ok(hotelFlow.includes('grid grid-cols-1 sm:grid-cols-3'),
    'Hotel date/guests row must stack to single column on mobile (grid-cols-1)');
});

// ── 7–9. AttractionExploreFlow mobile form ───────────────────────────────────

test('AttractionExploreFlow search row uses flex flex-col sm:flex-row', () => {
  assert.ok(attractionFlow.includes('flex flex-col gap-3 sm:flex-row') || attractionFlow.includes('flex flex-col sm:flex-row'),
    'Attraction search form row must stack vertically on mobile (flex-col)');
});

test('AttractionExploreFlow does not have bare w-44 shrink-0 without breakpoint', () => {
  assert.ok(!attractionFlow.match(/"relative w-44 shrink-0"/),
    'Interest input must not use bare w-44 shrink-0 — causes cramped horizontal layout on mobile');
});

test('AttractionExploreFlow interest input uses sm:w-44 sm:shrink-0', () => {
  assert.ok(attractionFlow.includes('sm:w-44 sm:shrink-0'),
    'Interest input must use sm:w-44 sm:shrink-0 so it is full-width on mobile');
});

test('AttractionExploreFlow search button has w-full sm:w-auto for mobile', () => {
  assert.ok(attractionFlow.includes('w-full sm:w-auto'),
    'Search button must stretch to full width on mobile (w-full sm:w-auto)');
});

// ── 10–13. TripDetail page touch targets and focus patterns ──────────────────

test('TripDetail edit modal close button has min-h-[44px] touch target', () => {
  assert.ok(tripDetailPage.includes('min-h-[44px]'),
    'Edit modal close button must have min-h-[44px] touch target');
});

test('TripDetail edit modal close button has min-w-[44px] touch target', () => {
  assert.ok(tripDetailPage.includes('min-w-[44px]'),
    'Edit modal close button must have min-w-[44px] touch target');
});

test('TripDetail edit modal inputs use focus-visible:outline (not focus:ring-*)', () => {
  assert.ok(!tripDetailPage.includes('focus:ring-ds-accent'),
    'Edit modal inputs must not use legacy focus:ring-ds-accent — use focus-visible:outline instead');
  assert.ok(!tripDetailPage.includes('focus:ring-2'),
    'Edit modal inputs must not use legacy focus:ring-2 — use focus-visible:outline instead');
});

test('TripDetail edit modal inputs use focus-visible:outline pattern', () => {
  assert.ok(tripDetailPage.includes('focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent'),
    'Edit modal inputs must use the standard focus-visible:outline pattern');
});

test('TripDetail chapter cover uses responsive px-4 sm:px-6 (mobile-first padding)', () => {
  assert.ok(tripDetailPage.includes('px-4') && tripDetailPage.includes('sm:px-6'),
    'Chapter cover must use responsive padding (px-4 on mobile, sm:px-6 on larger screens)');
});

// ── 14–16. ConciergePage header mobile optimization ──────────────────────────

test('ConciergePage header uses responsive pb-5 sm:pb-8 classes', () => {
  assert.ok(conciergePage.includes('pb-5') && conciergePage.includes('sm:pb-8'),
    'Concierge header must use responsive padding (pb-5 mobile, sm:pb-8 desktop)');
});

test('ConciergePage header does not have inline paddingBottom style blocking mobile override', () => {
  const headerBlock = conciergePage.match(/<header[^>]*concierge-instrument-header[^>]*>/);
  if (headerBlock) {
    assert.ok(!headerBlock[0].includes('paddingBottom'),
      'Header must not use inline paddingBottom — use responsive Tailwind classes instead');
  }
});

// ── 17. AIConciergePanel clear button touch target ───────────────────────────

test('AIConciergePanel clear button has min-h-[44px] touch target', () => {
  const clearSection = conciergePanel.slice(
    conciergePanel.indexOf('concierge-panel-clear'),
    conciergePanel.indexOf('concierge-panel-clear') + 400
  );
  assert.ok(clearSection.includes('min-h-[44px]'),
    'Clear button in AIConciergePanel must have min-h-[44px] for mobile touch target');
});

// ── 18. ExploreShell responsive section padding ──────────────────────────────

test('ExploreShell active section uses responsive padding classes (p-4 sm:p-6)', () => {
  assert.ok(exploreShell.includes('p-4 sm:p-6'),
    'ExploreShell active section must use responsive padding (p-4 on mobile, sm:p-6 on larger screens)');
});

test('ExploreShell active section does not rely solely on inline padding style', () => {
  const hasInlinePaddingOnly = exploreShell.match(/style=\{\{[^}]*padding:[^}]*var\(--ds-space-6\)[^}]*\}\}[^>]*data-testid=.*flow/);
  assert.ok(!hasInlinePaddingOnly,
    'Explore active section must use className for padding, not inline style only');
});

// ── 19–28. Preserved testids and handlers ─────────────────────────────────────

test('TripBuilder preserves google-flights-cta testid', () => {
  assert.ok(tripBuilder.includes('data-testid="google-flights-cta"'),
    'google-flights-cta testid must be preserved');
});

test('TripBuilder preserves flight-add-btn testid', () => {
  assert.ok(tripBuilder.includes('data-testid="flight-add-btn"'),
    'flight-add-btn testid must be preserved');
});

test('TripBuilder preserves handleAddCandidateToItinerary handler', () => {
  assert.ok(tripBuilder.includes('handleAddCandidateToItinerary'),
    'handleAddCandidateToItinerary handler must be preserved');
});

test('AIConciergePanel preserves concierge-panel-clear testid', () => {
  assert.ok(conciergePanel.includes('data-testid="concierge-panel-clear"'),
    'concierge-panel-clear testid must be preserved');
});

test('AIConciergePanel preserves concierge-panel-close testid', () => {
  assert.ok(conciergePanel.includes('data-testid="concierge-panel-close"'),
    'concierge-panel-close testid must be preserved');
});

test('AIConciergePanel preserves concierge-panel-submit testid', () => {
  assert.ok(conciergePanel.includes('data-testid="concierge-panel-submit"'),
    'concierge-panel-submit testid must be preserved');
});

test('TripDetail preserves chapter-actions testid', () => {
  assert.ok(tripDetailPage.includes('data-testid="chapter-actions"'),
    'chapter-actions testid must be preserved');
});

test('TripDetail preserves chapter-action-concierge testid', () => {
  assert.ok(tripDetailPage.includes('data-testid="chapter-action-concierge"'),
    'chapter-action-concierge testid must be preserved');
});

test('TripDetail preserves chapter-action-edit testid', () => {
  assert.ok(tripDetailPage.includes('data-testid="chapter-action-edit"'),
    'chapter-action-edit testid must be preserved');
});

// ── 28–31. No backend/provider imports ───────────────────────────────────────

test('TripBuilder no raw backend/provider imports from backend module', () => {
  assert.ok(!tripBuilder.includes('from "@/backend"') && !tripBuilder.includes('from "../backend"'),
    'TripBuilder must not import from backend modules directly');
});

test('HotelExploreFlow no raw backend/provider imports', () => {
  assert.ok(!hotelFlow.includes('from "@/backend"') && !hotelFlow.includes('from "../backend"'),
    'HotelExploreFlow must not import from backend modules');
});

test('AttractionExploreFlow no raw backend/provider imports', () => {
  assert.ok(!attractionFlow.includes('from "@/backend"') && !attractionFlow.includes('from "../backend"'),
    'AttractionExploreFlow must not import from backend modules');
});

// ── 32–33. No fake/hardcoded city data ───────────────────────────────────────

test('HotelExploreFlow no hardcoded city examples in placeholders', () => {
  assert.ok(!hotelFlow.includes('Paris') && !hotelFlow.includes('Tokyo') && !hotelFlow.includes('Barcelona'),
    'HotelExploreFlow must not contain hardcoded city examples in visible text/placeholders');
});

test('AttractionExploreFlow no hardcoded city examples in placeholders', () => {
  assert.ok(!attractionFlow.includes('"Paris"') && !attractionFlow.includes('"Tokyo"') && !attractionFlow.includes('"Barcelona"'),
    'AttractionExploreFlow must not contain hardcoded city examples in visible text/placeholders');
});

// ── 34. No bare horizontal-only control rows (already validated above) ────────

test('TripBuilder does not use bare flex items-start without lg breakpoint on main container', () => {
  assert.ok(!tripBuilder.includes('"flex items-start gap-4 min-h-[500px]"'),
    'Main container must not be bare horizontal flex — mobile stacking is required');
});

// ── 35–36. Semantic form controls ─────────────────────────────────────────────

test('AttractionExploreFlow search button is type="submit" (semantic)', () => {
  assert.ok(attractionFlow.includes('type="submit"'),
    'Attraction search button must be type="submit"');
});

test('HotelExploreFlow search button is type="submit" (semantic)', () => {
  assert.ok(hotelFlow.includes('type="submit"'),
    'Hotel search button must be type="submit"');
});

// ── 37–39. ConciergePage preserved testids ────────────────────────────────────

test('ConciergePage preserves concierge-query-input testid', () => {
  assert.ok(conciergePage.includes('data-testid="concierge-query-input"'),
    'concierge-query-input testid must be preserved');
});

test('ConciergePage preserves concierge-submit-button testid', () => {
  assert.ok(conciergePage.includes('data-testid="concierge-submit-button"'),
    'concierge-submit-button testid must be preserved');
});

test('ConciergePage preserves concierge-destination-field testid', () => {
  assert.ok(conciergePage.includes('data-testid="concierge-destination-field"'),
    'concierge-destination-field testid must be preserved');
});

// ── 40. No nested interactive controls in TripBuilder ────────────────────────

test('TripBuilder candidate panel has no button-inside-button nesting', () => {
  const buttonOpens = (tripBuilder.match(/<button/g) || []).length;
  const buttonCloses = (tripBuilder.match(/<\/button>/g) || []).length;
  assert.strictEqual(buttonOpens, buttonCloses, 'Button open/close tags must be balanced (no accidental nesting)');
});

// ── 41. AIConciergePanel no legacy focus:ring on header buttons ──────────────

test('AIConciergePanel clear/close buttons use focus-visible:outline (not focus:ring-*)', () => {
  const headerSection = conciergePanel.slice(
    conciergePanel.indexOf('concierge-panel-header'),
    conciergePanel.indexOf('concierge-panel-transcript')
  );
  assert.ok(!headerSection.includes('focus:ring-'),
    'Panel header buttons must use focus-visible:outline, not legacy focus:ring-*');
});

// ── 42. ExploreShell preserved testids ───────────────────────────────────────

test('ExploreShell preserves explore-lounge-header testid', () => {
  assert.ok(exploreShell.includes('data-testid="explore-lounge-header"'),
    'explore-lounge-header testid must be preserved');
});

test('ExploreShell preserves explore-lounge-breadcrumb testid', () => {
  assert.ok(exploreShell.includes('data-testid="explore-lounge-breadcrumb"'),
    'explore-lounge-breadcrumb testid must be preserved');
});

// ── 48–50. Preserved core behaviors ──────────────────────────────────────────

test('TripBuilder preserves DndContext import (DnD behavior)', () => {
  assert.ok(tripBuilder.includes('DndContext'),
    'TripBuilder must preserve DndContext for drag-and-drop behavior');
});

test('ConciergePage preserves callConciergeSearch handler', () => {
  assert.ok(conciergePage.includes('callConciergeSearch'),
    'callConciergeSearch handler must be preserved in ConciergePage');
});

test('AIConciergePanel preserves addStructuredConciergeItemToTrip handler', () => {
  assert.ok(conciergePanel.includes('addStructuredConciergeItemToTrip'),
    'addStructuredConciergeItemToTrip handler must be preserved in AIConciergePanel');
});

// ── Additional: Mobile-safe layout class invariants ───────────────────────────

test('HotelExploreFlow search button uses w-full for full-width mobile layout', () => {
  assert.ok(hotelFlow.includes('w-full'),
    'Hotel search button must be full-width (w-full) for easy mobile tap');
});

test('AttractionExploreFlow form does not use bare flex gap-3 without col on search row', () => {
  const formSection = attractionFlow.slice(
    attractionFlow.indexOf('<form'),
    attractionFlow.indexOf('</form>')
  );
  assert.ok(!formSection.match(/"flex gap-3"/),
    'Attraction form row must not use bare flex gap-3 — must include flex-col for mobile');
});

test('TripBuilder lg:items-start used for lg-breakpoint alignment', () => {
  assert.ok(tripBuilder.includes('lg:items-start'),
    'TripBuilder must use lg:items-start so candidate panel and itinerary align at top on desktop');
});

// ── Phase 8I patch: semantic type="button" and 44px touch targets ────────────

// ExploreShell
test('ExploreShell Back breadcrumb button has type="button"', () => {
  const breadcrumb = exploreShell.slice(
    exploreShell.indexOf('explore-lounge-breadcrumb'),
    exploreShell.indexOf('explore-lounge-breadcrumb') + 600
  );
  assert.ok(breadcrumb.includes('type="button"'),
    'Breadcrumb Back button must have type="button"');
});

test('ExploreShell Back breadcrumb button has min-h-[44px] touch target', () => {
  const breadcrumb = exploreShell.slice(
    exploreShell.indexOf('explore-lounge-breadcrumb'),
    exploreShell.indexOf('explore-lounge-breadcrumb') + 600
  );
  assert.ok(breadcrumb.includes('min-h-[44px]'),
    'Breadcrumb Back button must have min-h-[44px] touch target');
});

test('ExploreShell VerticalCard button has type="button"', () => {
  const cardFn = exploreShell.slice(exploreShell.indexOf('function VerticalCard'));
  assert.ok(cardFn.includes('type="button"'),
    'VerticalCard button must have type="button"');
});

test('ExploreShell VerticalCard button has min-h-[44px] touch target', () => {
  const cardFn = exploreShell.slice(exploreShell.indexOf('function VerticalCard'));
  assert.ok(cardFn.includes('min-h-[44px]'),
    'VerticalCard button must have min-h-[44px] touch target');
});

// HotelExploreFlow
test('HotelExploreFlow hotel-compare-cta has min-h-[44px] touch target', () => {
  const ctaSection = hotelFlow.slice(
    hotelFlow.indexOf('hotel-compare-cta') - 500,
    hotelFlow.indexOf('hotel-compare-cta') + 200
  );
  assert.ok(ctaSection.includes('min-h-[44px]'),
    'hotel-compare-cta link must have min-h-[44px] touch target');
});

test('HotelExploreFlow hotel-compare-cta preserves href and target="_blank"', () => {
  const ctaSection = hotelFlow.slice(
    hotelFlow.indexOf('hotel-compare-cta') - 600,
    hotelFlow.indexOf('hotel-compare-cta') + 100
  );
  assert.ok(ctaSection.includes('href={compareLink}') || ctaSection.includes('href='),
    'hotel-compare-cta must preserve its href');
  assert.ok(ctaSection.includes('target="_blank"'),
    'hotel-compare-cta must preserve target="_blank"');
});

// ConciergePage starter prompt chips
test('ConciergePage starter prompt chips have min-h-[44px] touch target', () => {
  // Search from the JSX map call (not the const definition which is far above)
  const mapIdx = conciergePage.indexOf('EDITORIAL_PROMPTS.map');
  const emptyState = conciergePage.slice(mapIdx, mapIdx + 600);
  assert.ok(emptyState.includes('min-h-[44px]'),
    'Starter prompt chips must have min-h-[44px] touch target');
});

test('ConciergePage starter prompt chips remain type="button"', () => {
  // Window extended to 1400 chars: the invitations block is now nested inside
  // the portal copy (salon rebuild), so there is more JSX before the buttons.
  const emptyState = conciergePage.slice(
    conciergePage.indexOf('concierge-empty-state'),
    conciergePage.indexOf('concierge-empty-state') + 1400
  );
  assert.ok(emptyState.includes('type="button"'),
    'Starter prompt chips must remain type="button"');
});

test('ConciergePage starter prompt chips only populate input, do not auto-submit', () => {
  const chipOnClick = conciergePage.slice(
    conciergePage.indexOf('EDITORIAL_PROMPTS.map'),
    conciergePage.indexOf('EDITORIAL_PROMPTS.map') + 400
  );
  assert.ok(chipOnClick.includes('setInput(prompt)'),
    'Chip onClick must call setInput to populate input');
  assert.ok(chipOnClick.includes("inputRef.current?.focus()"),
    'Chip onClick must focus the input');
  assert.ok(!chipOnClick.includes('handleUserInput') && !chipOnClick.includes('sendQuery'),
    'Chip onClick must NOT call handleUserInput or sendQuery — chips only populate input');
});

test('ConciergePage starter prompt chips do not set hardcoded destination', () => {
  const chipOnClick = conciergePage.slice(
    conciergePage.indexOf('EDITORIAL_PROMPTS.map'),
    conciergePage.indexOf('EDITORIAL_PROMPTS.map') + 400
  );
  assert.ok(!chipOnClick.includes('setDestination('),
    'Chip onClick must not call setDestination — chips only populate query input, not destination');
});

// TripDetail chapter action buttons
test('TripDetail chapter-action-concierge button has type="button"', () => {
  const conciergeBtn = tripDetailPage.slice(
    tripDetailPage.indexOf('chapter-action-concierge') - 200,
    tripDetailPage.indexOf('chapter-action-concierge') + 50
  );
  assert.ok(conciergeBtn.includes('type="button"'),
    'chapter-action-concierge must have type="button"');
});

test('TripDetail chapter-action-edit button has type="button"', () => {
  const editBtn = tripDetailPage.slice(
    tripDetailPage.indexOf('chapter-action-edit') - 200,
    tripDetailPage.indexOf('chapter-action-edit') + 50
  );
  assert.ok(editBtn.includes('type="button"'),
    'chapter-action-edit must have type="button"');
});

test('TripDetail edit modal close button has type="button"', () => {
  const closeBtn = tripDetailPage.slice(
    tripDetailPage.indexOf('Close edit dialog') - 100,
    tripDetailPage.indexOf('Close edit dialog') + 50
  );
  assert.ok(closeBtn.includes('type="button"'),
    'Edit modal close button must have type="button"');
});

test('TripDetail modal Cancel buttons have type="button"', () => {
  assert.ok(tripDetailPage.includes('type="button"'),
    'TripDetail must have type="button" on non-submit buttons');
});

// TripBuilder control surface type="button"
test('TripBuilder SortControl option buttons have type="button"', () => {
  const sortSection = tripBuilder.slice(
    tripBuilder.indexOf('function SortControl'),
    tripBuilder.indexOf('function SortControl') + 600
  );
  assert.ok(sortSection.includes('type="button"'),
    'SortControl option buttons must have type="button"');
});

test('TripBuilder CandidatePanel toggle button has type="button"', () => {
  const panelSection = tripBuilder.slice(
    tripBuilder.indexOf('function CandidatePanel'),
    tripBuilder.indexOf('function CandidatePanel') + 1200
  );
  assert.ok(panelSection.includes('type="button"'),
    'CandidatePanel toggle button must have type="button"');
});

test('TripBuilder List/Map view toggle buttons have type="button"', () => {
  const viewSection = tripBuilder.slice(
    tripBuilder.indexOf('setViewMode("list")') - 50,
    tripBuilder.indexOf('setViewMode("map")') + 200
  );
  assert.ok(viewSection.includes('type="button"'),
    'List/Map view toggle buttons must have type="button"');
});

test('TripBuilder Add Day button has type="button"', () => {
  // Use JSX onClick usage, not the callback definition
  const jsxIdx = tripBuilder.indexOf('onClick={handleAddDay}');
  const addDaySection = tripBuilder.slice(jsxIdx - 200, jsxIdx + 100);
  assert.ok(addDaySection.includes('type="button"'),
    'Add Day button must have type="button"');
});

test('TripBuilder Compare bar buttons have type="button"', () => {
  // Use JSX onClick usage to find the compare button
  const jsxIdx = tripBuilder.indexOf('onClick={handleCompare}');
  const compareSection = tripBuilder.slice(jsxIdx - 200, jsxIdx + 300);
  assert.ok(compareSection.includes('type="button"'),
    'Compare bar buttons must have type="button"');
});
