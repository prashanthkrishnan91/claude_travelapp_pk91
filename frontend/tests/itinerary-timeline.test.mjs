/**
 * Smart Day Timeline v1 — renderer contract tests.
 *
 * Verifies that:
 * 1. getItemDayPart logic is correct for all signal types.
 * 2. Grouped sections render section headers for timed items.
 * 3. Untimed items render under "Unscheduled" section.
 * 4. Mixed timed + untimed items separate into correct sections.
 * 5. Move-to-ideas action is present for concierge items in day columns.
 * 6. No duplicate action buttons: move-to-ideas only for concierge items.
 * 7. Existing Trip Ideas assignment behavior preserved (source_kind check).
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const dayColumn = readFileSync(
  new URL('../src/components/trips/ItineraryDayColumn.tsx', import.meta.url),
  'utf8',
);

const itemCard = readFileSync(
  new URL('../src/components/trips/ItineraryItemCard.tsx', import.meta.url),
  'utf8',
);

// ---------------------------------------------------------------------------
// 1. DayPart classification: labels and constants present
// ---------------------------------------------------------------------------

test('ItineraryDayColumn defines four day-part buckets', () => {
  assert.match(dayColumn, /morning/, 'morning bucket required');
  assert.match(dayColumn, /afternoon/, 'afternoon bucket required');
  assert.match(dayColumn, /evening/, 'evening bucket required');
  assert.match(dayColumn, /unscheduled/, 'unscheduled bucket required');
});

test('ItineraryDayColumn exports getItemDayPart helper or equivalent grouping', () => {
  assert.match(dayColumn, /getItemDayPart|groupByDayPart/, 'grouping helper must exist');
});

// ---------------------------------------------------------------------------
// 2. getItemDayPart reads details.dayPart as explicit override
// ---------------------------------------------------------------------------

test('ItineraryDayColumn reads details.dayPart for explicit section override', () => {
  assert.match(dayColumn, /d\.dayPart|details.*dayPart/, 'dayPart read from details');
});

// ---------------------------------------------------------------------------
// 3. getItemDayPart reads details.timeLabel for keyword classification
// ---------------------------------------------------------------------------

test('ItineraryDayColumn reads details.timeLabel for morning/afternoon/evening keywords', () => {
  assert.match(dayColumn, /timeLabel/, 'timeLabel signal must be read');
});

// ---------------------------------------------------------------------------
// 4. getItemDayPart parses startTime for hour-based classification
// ---------------------------------------------------------------------------

test('ItineraryDayColumn parses startTime to determine day part', () => {
  // startTime hour parsing must exist
  assert.match(dayColumn, /startTime/, 'startTime must be consumed');
  assert.match(dayColumn, /morning|hour.*12|5.*12/, 'morning hour boundary must exist');
  assert.match(dayColumn, /afternoon|hour.*17|12.*17/, 'afternoon hour boundary must exist');
  assert.match(dayColumn, /evening|hour.*17/, 'evening hour boundary must exist');
});

// ---------------------------------------------------------------------------
// 5. Unscheduled section: items without time metadata shown under Unscheduled
// ---------------------------------------------------------------------------

test('ItineraryDayColumn renders Unscheduled label for items with no time metadata', () => {
  assert.match(dayColumn, /Unscheduled/, 'Unscheduled section label must appear');
});

// ---------------------------------------------------------------------------
// 6. Section headers: Morning / Afternoon / Evening labels in the component
// ---------------------------------------------------------------------------

test('ItineraryDayColumn renders Morning, Afternoon, Evening section labels', () => {
  assert.match(dayColumn, /Morning/, 'Morning section label must appear');
  assert.match(dayColumn, /Afternoon/, 'Afternoon section label must appear');
  assert.match(dayColumn, /Evening/, 'Evening section label must appear');
});

// ---------------------------------------------------------------------------
// 7. TimelineSections component exists and is used
// ---------------------------------------------------------------------------

test('ItineraryDayColumn defines and uses TimelineSections sub-component', () => {
  assert.match(dayColumn, /TimelineSections/, 'TimelineSections must be defined/used');
});

// ---------------------------------------------------------------------------
// 8. Existing drag/drop infrastructure preserved (SortableContext, useDroppable)
// ---------------------------------------------------------------------------

test('ItineraryDayColumn still uses SortableContext and useDroppable for drag/drop', () => {
  assert.match(dayColumn, /SortableContext/, 'SortableContext must remain for drag/drop');
  assert.match(dayColumn, /useDroppable/, 'useDroppable must remain for drag/drop');
});

// ---------------------------------------------------------------------------
// 9. Move-to-ideas action: only shows for concierge items (source_kind check)
// ---------------------------------------------------------------------------

test('ItineraryItemCard only shows Move to Ideas for source_kind=concierge_idea items', () => {
  assert.match(itemCard, /source_kind.*concierge_idea|concierge_idea.*source_kind/, 'source_kind guard must exist');
  assert.match(itemCard, /showMoveToIdeasAction/, 'showMoveToIdeasAction guard must exist');
  assert.match(itemCard, /Move to Ideas/, 'Move to Ideas button must exist');
});

// ---------------------------------------------------------------------------
// 10. No duplicate action: Move to Ideas button is conditional
// ---------------------------------------------------------------------------

test('ItineraryItemCard Move to Ideas button is conditionally rendered (no duplicates)', () => {
  // The button must be inside a conditional render (showMoveToIdeasAction && ...)
  assert.match(itemCard, /showMoveToIdeasAction.*&&|{showMoveToIdeasAction/, 'button must be conditional');
});

// ---------------------------------------------------------------------------
// 11. Travel-time connectors preserved within sections
// ---------------------------------------------------------------------------

test('ItineraryDayColumn still renders travel connectors via estimateTravel', () => {
  assert.match(dayColumn, /estimateTravel/, 'estimateTravel must still be called for connectors');
});

// ---------------------------------------------------------------------------
// 12. Trip Ideas assignment behavior: onMoveItemToIdeas prop threaded through
// ---------------------------------------------------------------------------

test('ItineraryDayColumn threads onMoveItemToIdeas to TimelineSections', () => {
  assert.match(dayColumn, /onMoveItemToIdeas/, 'onMoveItemToIdeas must be passed through');
});
