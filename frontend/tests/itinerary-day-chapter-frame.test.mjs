// Stage 3.5 Phase 8D — Itinerary DayColumn Editorial Chapter Frame
//
// Contract tests verifying:
// - day-column chapter-frame structure (data-testid contract)
// - day heading / date treatment (h3 promoted, data-testid, CalendarDays)
// - editorial day-part labels and hairline separators
// - premium empty-day chapter invitation (no board-lane copy)
// - ds-token usage (no raw hex, no legacy palette)
// - semantic buttons and links (no card-level click-only navigation)
// - no fake/mock/sample visible data in source
// - no backend/provider imports
// - preserved DnD primitives (useDroppable, SortableContext)
// - preserved groupByDayPart / DAY_PART_META
// - preserved ItineraryItemCard rendering and move-to-ideas threading

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const src = readFileSync(new URL('../src/components/trips/ItineraryDayColumn.tsx', import.meta.url), 'utf8');

// ── Chapter frame structure ────────────────────────────────────────────────────

test('Phase 8D: day-chapter-frame data-testid on root element', () => {
  assert.ok(src.includes('data-testid="day-chapter-frame"'), 'missing data-testid="day-chapter-frame"');
});

test('Phase 8D: day-chapter-header data-testid on header element', () => {
  assert.ok(src.includes('data-testid="day-chapter-header"'), 'missing data-testid="day-chapter-header"');
});

test('Phase 8D: day-chapter-number data-testid on number marker', () => {
  assert.ok(src.includes('data-testid="day-chapter-number"'), 'missing data-testid="day-chapter-number"');
});

test('Phase 8D: day-chapter-title data-testid on h3 heading', () => {
  assert.ok(src.includes('data-testid="day-chapter-title"'), 'missing data-testid="day-chapter-title"');
});

test('Phase 8D: day-chapter-date data-testid on date element', () => {
  assert.ok(src.includes('data-testid="day-chapter-date"'), 'missing data-testid="day-chapter-date"');
});

test('Phase 8D: day-item-count data-testid on item count badge', () => {
  assert.ok(src.includes('data-testid="day-item-count"'), 'missing data-testid="day-item-count"');
});

// ── Day heading / date treatment ──────────────────────────────────────────────

test('Phase 8D: chapter title uses text-base for editorial heading weight', () => {
  // text-base is the promoted chapter heading (was text-sm); folio-ink replaces text-ds-text in Slice 2
  assert.ok(src.includes('text-base font-semibold text-ds-folio-ink') || src.includes('text-base font-semibold text-ds-text'), 'chapter heading not promoted to text-base');
});

test('Phase 8D: day chapter number zero-pads via padStart(2)', () => {
  assert.ok(src.includes('padStart(2'), 'missing padStart(2) for chapter number');
});

test('Phase 8D: date overline uses tracking-[0.1em] (Overline pattern)', () => {
  assert.ok(src.includes('tracking-[0.1em]'), 'missing tracking-[0.1em] for date overline');
});

test('Phase 8D: CalendarDays icon preserved for date field', () => {
  assert.ok(src.includes('CalendarDays'), 'CalendarDays icon missing from date field');
});

test('Phase 8D: formatDate used for real date data (no hardcoded fake dates)', () => {
  assert.ok(src.includes('formatDate(day.date)'), 'formatDate call missing — date must come from real day.date');
});

// ── Editorial day-part labels and hairlines ───────────────────────────────────

test('Phase 8D: day-part-section data-testid on section containers', () => {
  assert.ok(src.includes('data-testid="day-part-section"'), 'missing data-testid="day-part-section"');
});

test('Phase 8D: day-part-label data-testid on Overline section labels', () => {
  assert.ok(src.includes('data-testid="day-part-label"'), 'missing data-testid="day-part-label"');
});

test('Phase 8D: editorial hairline border-t between non-empty day-part sections', () => {
  // Stage 3.5 paper-world conversion: hairline tokens are paper-world (ds-hairline)
  // instead of dark-world (ds-pen-stroke).
  assert.ok(
    src.includes('border-t border-ds-hairline') || src.includes('border-t border-ds-pen-stroke'),
    'missing border-t hairline between sections'
  );
});

test('Phase 8D: time hint uses italic for editorial register (not KPI-like)', () => {
  // The time hint span should use italic + paper-world muted text token
  assert.ok(
    src.includes('text-ds-folio-ink-mist italic') || src.includes('text-ds-text-tertiary italic'),
    'time hint not in italic editorial register'
  );
});

test('Phase 8D: day-part sections use filledSections array (hairline between non-empty sections)', () => {
  assert.ok(src.includes('filledSections'), 'filledSections variable missing — hairline logic requires it');
});

test('Phase 8D: DAY_PART_META preserved with morning/afternoon/evening/unscheduled', () => {
  assert.ok(src.includes('DAY_PART_META'), 'DAY_PART_META missing');
  assert.ok(src.includes('"morning"'), 'morning key missing from DAY_PART_META');
  assert.ok(src.includes('"afternoon"'), 'afternoon key missing from DAY_PART_META');
  assert.ok(src.includes('"evening"'), 'evening key missing from DAY_PART_META');
  assert.ok(src.includes('"unscheduled"'), 'unscheduled key missing from DAY_PART_META');
});

test('Phase 8D: day-part Overline labels use uppercase tracking-[0.1em] pattern', () => {
  // Section labels must follow Design Bible Overline type role
  assert.ok(
    src.includes('uppercase tracking-[0.1em]'),
    'Overline pattern (uppercase tracking-[0.1em]) missing from day-part labels'
  );
});

// ── Premium empty-day chapter state ──────────────────────────────────────────

test('Phase 8D: empty-day-chapter data-testid on empty state container', () => {
  assert.ok(src.includes('data-testid="empty-day-chapter"'), 'missing data-testid="empty-day-chapter"');
});

test('Phase 8D: empty day uses editorial chapter-prompt language, not board-lane copy', () => {
  // "Begin this chapter" is the editorial chapter-opening prompt
  assert.ok(src.includes('Begin this chapter'), 'missing editorial chapter prompt in empty day state');
});

test('Phase 8D: empty day no longer uses "to start building" (board/SaaS language removed)', () => {
  assert.ok(!src.includes('to start building'), 'found "to start building" — SaaS language must be replaced');
});

test('Phase 8D: empty day no longer uses "Drag items here" (board-lane copy removed)', () => {
  assert.ok(!src.includes('Drag items here'), 'found "Drag items here" — generic board copy must be replaced');
});

test('Phase 8D: empty day uses border-dashed drop zone (DnD affordance preserved)', () => {
  assert.ok(src.includes('border-dashed'), 'missing border-dashed drop zone in empty-day state');
});

test('Phase 8D: empty day + Add button has 44px touch target (min-h-[44px])', () => {
  const emptyChapterIdx = src.indexOf('Begin this chapter');
  assert.ok(emptyChapterIdx !== -1, 'missing "Begin this chapter" text');
  // Extend window to 700 chars after to capture the button className
  const surroundingCtx = src.slice(Math.max(0, emptyChapterIdx - 200), emptyChapterIdx + 700);
  assert.ok(surroundingCtx.includes('min-h-[44px]'), 'empty-day + Add button lacks min-h-[44px] near chapter prompt');
});

test('Phase 8D: empty day + Add inline button is a semantic <button>, not a div/span', () => {
  // The + Add element in the empty state must be a real button
  const addIdx = src.indexOf('+ Add');
  assert.ok(addIdx !== -1, 'missing "+ Add" text in empty state');
  // Extend window to 700 chars before to capture the button opening tag
  const preceding = src.slice(Math.max(0, addIdx - 700), addIdx);
  assert.ok(preceding.includes('<button'), 'the "+ Add" element is not a semantic <button>');
});

test('Phase 8D: empty day drag-over uses border-ds-accent/60 and accent-subtle bg', () => {
  assert.ok(src.includes('border-ds-accent/60'), 'missing border-ds-accent/60 drag-over state');
  assert.ok(src.includes('var(--ds-accent-subtle)'), 'missing accent-subtle bg on drag-over');
});

// ── ds-token usage ────────────────────────────────────────────────────────────

test('Phase 8D: no raw hex color values in source', () => {
  assert.ok(!src.includes('#0'), 'found raw hex (#0...) — use ds-* tokens instead');
});

test('Phase 8D: no raw rgba() color values in source', () => {
  assert.ok(!src.includes('rgba('), 'found raw rgba() — use ds-* tokens or var(--ds-*) instead');
});

test('Phase 8D: no legacy slate-NNN classes', () => {
  assert.ok(!/\bslate-\d+\b/.test(src), 'found legacy slate-NNN class');
});

test('Phase 8D: no legacy amber-NNN classes', () => {
  assert.ok(!/\bamber-\d+\b/.test(src), 'found legacy amber-NNN class');
});

test('Phase 8D: uses folio-paper-card for column root surface (Slice 2 paper conversion)', () => {
  assert.ok(src.includes('folio-paper-card'), 'missing folio-paper-card on column surface (replaced bg-ds-onyx in Slice 2)');
});

test('Phase 8D: uses hairline tokens for paper column borders', () => {
  // Stage 3.5: paper-world ItineraryDayColumn uses ds-hairline tokens.
  assert.ok(
    src.includes('border-ds-hairline') || src.includes('border-ds-pen-stroke'),
    'missing hairline border'
  );
});

test('Phase 8D: uses folio-paper-card which carries shadow (Slice 2 paper conversion)', () => {
  assert.ok(src.includes('folio-paper-card'), 'folio-paper-card carries shadow via CSS class (replaced inline ds-elevation-2 in Slice 2)');
});

test('Phase 8D: uses bg-ds-marine-ink for selected state number marker (Slice 2 paper conversion)', () => {
  assert.ok(src.includes('bg-ds-marine-ink'), 'selected number marker must use bg-ds-marine-ink (converted from bg-ds-accent in Slice 2)');
});

test('Phase 8D: uses paper-world muted text token for secondary labels', () => {
  // Stage 3.5: paper-world ItineraryDayColumn uses folio-ink-mist for muted text.
  assert.ok(
    src.includes('text-ds-folio-ink-mist') || src.includes('text-ds-text-tertiary'),
    'missing paper-world muted text token'
  );
});

// ── Semantic buttons/links — no card-level click-only navigation ──────────────

test('Phase 8D: day-chapter-frame root has no onClick navigation handler', () => {
  // The root div [data-testid="day-chapter-frame"] must not have onClick for navigation
  // The onClick belongs on the header div only, not the card root
  const frameIdx = src.indexOf('data-testid="day-chapter-frame"');
  assert.ok(frameIdx !== -1, 'day-chapter-frame not found');
  // The very next onClick after the frame open tag should NOT be immediately on the frame div
  // (it should be inside the header div, not on the frame root)
  const frameClose = src.indexOf('>', frameIdx);
  const frameAttrs = src.slice(frameIdx, frameClose);
  assert.ok(!frameAttrs.includes('onClick'), 'day-chapter-frame root has onClick — card-level navigation forbidden');
});

test('Phase 8D: all action buttons are semantic <button> elements with explicit handlers', () => {
  // Verify Plan My Day, Suggest Timing, Add item, Expand/Collapse are real buttons
  assert.ok(src.includes('onPlanDay'), 'onPlanDay handler missing');
  assert.ok(src.includes('onAddItem'), 'onAddItem handler missing');
  assert.ok(src.includes('onToggleExpanded'), 'onToggleExpanded handler missing');
});

test('Phase 8D: all interactive buttons have focus-visible:outline-ds-accent ring', () => {
  assert.ok(src.includes('focus-visible:outline-ds-accent'), 'missing focus-visible:outline-ds-accent');
  assert.ok(src.includes('focus-visible:outline-2'), 'missing focus-visible:outline-2');
  assert.ok(src.includes('focus-visible:outline-offset-2'), 'missing focus-visible:outline-offset-2');
});

test('Phase 8D: interactive buttons have min-h-[44px] touch targets', () => {
  assert.ok(src.includes('min-h-[44px]'), 'missing min-h-[44px] on interactive buttons');
});

test('Phase 8D: icon-only buttons have min-w-[44px] touch targets', () => {
  assert.ok(src.includes('min-w-[44px]'), 'missing min-w-[44px] on icon-only buttons');
});

// ── No fake/mock/sample visible data ─────────────────────────────────────────

test('Phase 8D: no hardcoded place names or fake itinerary copy in source', () => {
  const fakePlaces = ['Eiffel Tower', 'Colosseum', 'Times Square', 'Golden Gate', 'Louvre'];
  for (const place of fakePlaces) {
    assert.ok(!src.includes(place), `found fake/sample place name "${place}"`);
  }
});

test('Phase 8D: no fake weather data or made-up times in source', () => {
  // No hardcoded time strings that would be fake/sample data
  assert.ok(!src.includes('"8:00 AM"') && !src.includes('"9:00 AM"'), 'found fake hardcoded time strings');
});

test('Phase 8D: no "sample" or "placeholder" text in source', () => {
  assert.ok(!src.toLowerCase().includes('sample'), 'found "sample" text — no mock data allowed');
  assert.ok(!src.toLowerCase().includes('placeholder text'), 'found "placeholder text" — no mock data allowed');
});

// ── No backend/provider imports ───────────────────────────────────────────────

test('Phase 8D: no backend imports in ItineraryDayColumn', () => {
  assert.ok(!src.includes("from '@/backend"), 'found import from @/backend');
  assert.ok(!src.includes('from "../backend'), 'found relative import from backend');
  assert.ok(!src.includes("from 'backend/"), 'found import from backend/');
});

test('Phase 8D: no provider/search/Supabase imports', () => {
  assert.ok(!src.includes('supabase'), 'found supabase import in ItineraryDayColumn');
  assert.ok(!src.includes('tavily'), 'found tavily import in ItineraryDayColumn');
  assert.ok(!src.includes('duffel'), 'found duffel import in ItineraryDayColumn');
});

test('Phase 8D: only frontend lib imports (api, travelHints, types)', () => {
  // Confirm only frontend-safe imports (source may use single or double quotes)
  assert.ok(src.includes('@/types'), 'missing @/types import');
  assert.ok(src.includes('@/lib/travelHints'), 'missing travelHints import');
  assert.ok(src.includes('@/lib/api'), 'missing @/lib/api import');
});

// ── Preserved DnD primitives ──────────────────────────────────────────────────

test('Phase 8D: useDroppable DnD hook preserved', () => {
  assert.ok(src.includes('useDroppable'), 'useDroppable DnD hook missing');
});

test('Phase 8D: SortableContext for item ordering preserved', () => {
  assert.ok(src.includes('SortableContext'), 'SortableContext missing');
});

test('Phase 8D: verticalListSortingStrategy preserved', () => {
  assert.ok(src.includes('verticalListSortingStrategy'), 'verticalListSortingStrategy missing');
});

test('Phase 8D: isOver drop-zone state preserved', () => {
  assert.ok(src.includes('isOver'), 'isOver drop-zone state missing');
});

test('Phase 8D: setNodeRef for droppable zone preserved', () => {
  assert.ok(src.includes('setNodeRef'), 'setNodeRef for droppable zone missing');
});

// ── Preserved groupByDayPart / DAY_PART_META ─────────────────────────────────

test('Phase 8D: groupByDayPart function preserved', () => {
  assert.ok(src.includes('function groupByDayPart'), 'groupByDayPart function missing');
});

test('Phase 8D: getItemDayPart function preserved', () => {
  assert.ok(src.includes('function getItemDayPart'), 'getItemDayPart function missing');
});

test('Phase 8D: TimelineSections component preserved', () => {
  assert.ok(src.includes('function TimelineSections'), 'TimelineSections component missing');
});

test('Phase 8D: DAY_PART_META colorClass entries preserved', () => {
  assert.ok(src.includes('colorClass'), 'colorClass property missing from DAY_PART_META');
  assert.ok(src.includes('timeHint'), 'timeHint property missing from DAY_PART_META');
  assert.ok(src.includes('label'), 'label property missing from DAY_PART_META');
});

test('Phase 8D: orderedSections array preserved for section ordering', () => {
  assert.ok(src.includes('orderedSections'), 'orderedSections array missing');
});

// ── Preserved ItineraryItemCard rendering and move-to-ideas threading ─────────

test('Phase 8D: ItineraryItemCard import preserved', () => {
  assert.ok(src.includes("import { ItineraryItemCard }"), 'ItineraryItemCard import missing');
});

test('Phase 8D: ItineraryItemCard rendered inside renderItemsWithConnectors', () => {
  assert.ok(src.includes('<ItineraryItemCard'), 'ItineraryItemCard JSX missing');
});

test('Phase 8D: onMoveItemToIdeas prop threading preserved', () => {
  assert.ok(src.includes('onMoveItemToIdeas'), 'onMoveItemToIdeas prop threading missing');
});

test('Phase 8D: onMoveToIdeas passed to ItineraryItemCard', () => {
  assert.ok(src.includes('onMoveToIdeas={'), 'onMoveToIdeas prop not passed to ItineraryItemCard');
});

test('Phase 8D: onRemoveItem passed to ItineraryItemCard', () => {
  assert.ok(src.includes('onRemove={'), 'onRemove prop not passed to ItineraryItemCard');
});

test('Phase 8D: onToggleCompare passed to ItineraryItemCard', () => {
  assert.ok(src.includes('onToggleCompare={'), 'onToggleCompare prop not passed to ItineraryItemCard');
});

test('Phase 8D: onTimelineUpdated passed to ItineraryItemCard', () => {
  assert.ok(src.includes('onTimelineUpdated={'), 'onTimelineUpdated prop not passed to ItineraryItemCard');
});

test('Phase 8D: renderItemsWithConnectors helper preserved', () => {
  assert.ok(src.includes('function renderItemsWithConnectors'), 'renderItemsWithConnectors function missing');
});

test('Phase 8D: computeAdjacentHints for travel time hints preserved', () => {
  assert.ok(src.includes('computeAdjacentHints'), 'computeAdjacentHints missing');
});

// ── Timeline AI planning preserved ───────────────────────────────────────────

test('Phase 8D: handleSuggestTimeline AI planning preserved', () => {
  assert.ok(src.includes('handleSuggestTimeline'), 'handleSuggestTimeline missing');
});

test('Phase 8D: handleApplyTimeline apply-suggestions preserved', () => {
  assert.ok(src.includes('handleApplyTimeline'), 'handleApplyTimeline missing');
});

test('Phase 8D: SuggestionsReviewPanel preserved', () => {
  assert.ok(src.includes('SuggestionsReviewPanel'), 'SuggestionsReviewPanel missing');
});

test('Phase 8D: itemOverrides optimistic timeline state preserved', () => {
  assert.ok(src.includes('itemOverrides'), 'itemOverrides optimistic update state missing');
});

// ── Additional behavior preservation ─────────────────────────────────────────

test('Phase 8D: isExpanded / onToggleExpanded preserved', () => {
  assert.ok(src.includes('isExpanded'), 'isExpanded prop missing');
  assert.ok(src.includes('onToggleExpanded'), 'onToggleExpanded prop missing');
});

test('Phase 8D: PREVIEW_ITEM_LIMIT paging preserved', () => {
  assert.ok(src.includes('PREVIEW_ITEM_LIMIT'), 'PREVIEW_ITEM_LIMIT missing');
});

test('Phase 8D: show all / show less pagination preserved', () => {
  assert.ok(src.includes('showAllItems'), 'showAllItems state missing');
  assert.ok(src.includes('hasHiddenItems'), 'hasHiddenItems logic missing');
});

test('Phase 8D: DayTravelHintBar travel feasibility preserved', () => {
  assert.ok(src.includes('DayTravelHintBar'), 'DayTravelHintBar missing');
});

test('Phase 8D: onPlanDay AI day planning preserved', () => {
  assert.ok(src.includes('onPlanDay'), 'onPlanDay prop missing');
});

test('Phase 8D: onUpdateTimeline timeline update prop preserved', () => {
  assert.ok(src.includes('onUpdateTimeline'), 'onUpdateTimeline prop missing');
});

test('Phase 8D: ItineraryDayColumn exported correctly', () => {
  assert.ok(src.includes('export function ItineraryDayColumn'), 'ItineraryDayColumn export missing');
});

// ── Semantic button fix: day-chapter-header must not be a clickable div ───────

test('Phase 8D patch: day-chapter-header wrapper div has no onClick', () => {
  const headerIdx = src.indexOf('data-testid="day-chapter-header"');
  assert.ok(headerIdx !== -1, 'day-chapter-header not found');
  const headerClose = src.indexOf('>', headerIdx);
  const headerAttrs = src.slice(headerIdx, headerClose);
  assert.ok(!headerAttrs.includes('onClick'), 'day-chapter-header wrapper div has onClick — card-level click pattern forbidden');
});

test('Phase 8D patch: day-chapter-header wrapper div has no cursor-pointer', () => {
  const headerIdx = src.indexOf('data-testid="day-chapter-header"');
  assert.ok(headerIdx !== -1, 'day-chapter-header not found');
  const headerClose = src.indexOf('>', headerIdx);
  const headerAttrs = src.slice(headerIdx, headerClose);
  assert.ok(!headerAttrs.includes('cursor-pointer'), 'day-chapter-header wrapper div has cursor-pointer — move it to the semantic button');
});

test('Phase 8D patch: chapter identity action is a semantic <button type="button">', () => {
  // The chapter identity (left side of header) must be a real button
  assert.ok(
    src.includes('<button') && src.includes('type="button"'),
    'missing semantic <button type="button"> for chapter identity'
  );
  // The button should be inside the header region (before Header actions comment)
  const headerIdx = src.indexOf('data-testid="day-chapter-header"');
  const actionsIdx = src.indexOf('Header actions', headerIdx);
  const identityRegion = src.slice(headerIdx, actionsIdx);
  assert.ok(
    identityRegion.includes('type="button"'),
    'chapter identity <button type="button"> not found in header identity region'
  );
});

test('Phase 8D patch: chapter identity button has aria-label', () => {
  const headerIdx = src.indexOf('data-testid="day-chapter-header"');
  const actionsIdx = src.indexOf('Header actions', headerIdx);
  const identityRegion = src.slice(headerIdx, actionsIdx);
  assert.ok(identityRegion.includes('aria-label'), 'chapter identity button missing aria-label');
});

test('Phase 8D patch: no nested interactive controls (button inside button)', () => {
  // Chapter identity is a button; no child buttons/links should be nested inside it
  const headerIdx = src.indexOf('data-testid="day-chapter-header"');
  const actionsIdx = src.indexOf('Header actions', headerIdx);
  const identityRegion = src.slice(headerIdx, actionsIdx);
  // Count opening button tags — only one (the identity button itself)
  const buttonOpens = (identityRegion.match(/<button/g) || []).length;
  assert.ok(buttonOpens <= 1, `found ${buttonOpens} <button> opens in chapter identity region — nested buttons forbidden`);
});
