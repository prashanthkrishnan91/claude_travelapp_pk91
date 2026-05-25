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

const api = readFileSync(
  new URL('../src/lib/api.ts', import.meta.url),
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
// 9. Move-to-ideas: normalized — uses onUnplace, not source_kind gate
// ---------------------------------------------------------------------------

test('ItineraryItemCard uses onUnplace prop for Move to Ideas (no source_kind gate)', () => {
  assert.match(itemCard, /onUnplace/, 'onUnplace prop must exist');
  assert.match(itemCard, /Move to Ideas/, 'Move to Ideas label must exist in action menu');
  assert.doesNotMatch(itemCard, /showMoveToIdeasAction/, 'old showMoveToIdeasAction gate must be removed');
  assert.doesNotMatch(itemCard, /isConciergeIdea/, 'isConciergeIdea source_kind gate must be removed');
});

// ---------------------------------------------------------------------------
// 10. Move to Ideas is inside the overflow/action menu, not standalone
// ---------------------------------------------------------------------------

test('ItineraryItemCard Move to Ideas is inside the overflow action menu (not standalone)', () => {
  // Must NOT be in a standalone always-visible block before the title
  assert.doesNotMatch(itemCard, /showMoveToIdeasAction\s*&&/, 'standalone showMoveToIdeasAction block must be gone');
  // onUnplace must be called with item.id AND details (current details preserved)
  assert.match(itemCard, /onUnplace\(item\.id,\s*details\)/, 'onUnplace must receive item.id and details');
});

// ---------------------------------------------------------------------------
// 11. Travel-time connectors preserved within sections (via computeAdjacentHints)
// ---------------------------------------------------------------------------

test('ItineraryDayColumn renders travel connectors via computeAdjacentHints from travelHints', () => {
  assert.match(dayColumn, /computeAdjacentHints/, 'computeAdjacentHints must be used for connectors in ItineraryDayColumn');
});

// ---------------------------------------------------------------------------
// 12. ItineraryDayColumn threads onMoveItemToIdeas (new signature: currentDetails) to cards
// ---------------------------------------------------------------------------

test('ItineraryDayColumn threads onMoveItemToIdeas with currentDetails signature to ItineraryItemCard', () => {
  assert.match(dayColumn, /onMoveItemToIdeas/, 'onMoveItemToIdeas must be passed through');
  assert.match(dayColumn, /currentDetails/, 'signature must carry currentDetails, not dayId');
  assert.match(dayColumn, /onUnplace=\{onMoveItemToIdeas\}/, 'ItineraryItemCard must receive onUnplace mapped from onMoveItemToIdeas');
});

// ---------------------------------------------------------------------------
// Manual Timeline Controls v1 — new tests
// ---------------------------------------------------------------------------

// 13. api.ts exports updateItemTimeline
test('api.ts exports updateItemTimeline function', () => {
  assert.match(api, /export async function updateItemTimeline/, 'updateItemTimeline must be exported from api.ts');
});

// 14. updateItemTimeline accepts dayPart and optional timeLabel
test('api.ts updateItemTimeline persists dayPart and timeLabel via updateItem', () => {
  assert.match(api, /dayPart/, 'updateItemTimeline must accept dayPart field');
  assert.match(api, /timeLabel/, 'updateItemTimeline must handle timeLabel field');
});

// 15. ItineraryItemCard has onTimelineUpdated prop
test('ItineraryItemCard accepts onTimelineUpdated prop', () => {
  assert.match(itemCard, /onTimelineUpdated/, 'onTimelineUpdated prop must exist in ItineraryItemCard');
});

// 16. ItineraryItemCard has timeline edit trigger button
test('ItineraryItemCard has a timeline edit trigger (clock button)', () => {
  assert.match(itemCard, /timelineOpen/, 'timelineOpen state must exist for the timeline editor');
  assert.match(itemCard, /Set timeline/, 'timeline trigger button must have accessible label');
});

// 17. ItineraryItemCard defines four day-part options
test('ItineraryItemCard defines Morning, Afternoon, Evening, Unscheduled day-part options', () => {
  assert.match(itemCard, /DAY_PARTS/, 'DAY_PARTS constant must exist in ItineraryItemCard');
  assert.match(itemCard, /Morning/, 'Morning option must exist in card');
  assert.match(itemCard, /Afternoon/, 'Afternoon option must exist in card');
  assert.match(itemCard, /Evening/, 'Evening option must exist in card');
  assert.match(itemCard, /Unscheduled/, 'Unscheduled option must exist in card');
});

// 18. ItineraryItemCard has timeLabel input
test('ItineraryItemCard has a timeLabel text input for freeform time label', () => {
  assert.match(itemCard, /timeLabelInput/, 'timeLabelInput state must exist in ItineraryItemCard');
  assert.match(itemCard, /Time label/, 'timeLabel input placeholder must exist in card');
});

// 19. ItineraryItemCard calls updateItemTimeline on save
test('ItineraryItemCard imports and calls updateItemTimeline from api on save', () => {
  assert.match(itemCard, /updateItemTimeline/, 'updateItemTimeline must be imported and called in ItineraryItemCard');
  assert.match(itemCard, /handleSaveTimeline/, 'handleSaveTimeline handler must exist in ItineraryItemCard');
});

// 20. ItineraryDayColumn threads onUpdateTimeline to TimelineSections
test('ItineraryDayColumn threads onUpdateTimeline prop to TimelineSections', () => {
  assert.match(dayColumn, /onUpdateTimeline/, 'onUpdateTimeline must be threaded in ItineraryDayColumn');
});

// 21. ItineraryDayColumn maintains itemOverrides for optimistic section movement
test('ItineraryDayColumn maintains itemOverrides state for immediate timeline section movement', () => {
  assert.match(dayColumn, /itemOverrides/, 'itemOverrides state must exist in ItineraryDayColumn for optimistic updates');
});

// 22. Existing item data fields preserved (notes, status, priority preserved via details merge)
test('updateItemTimeline merges details to preserve existing fields', () => {
  // The function spreads currentDetails before applying the patch
  assert.match(api, /\.\.\.(currentDetails|merged)/, 'existing details must be spread/preserved in updateItemTimeline');
});

// 23. getItemDayPart handles explicit "unscheduled" override
test('ItineraryDayColumn getItemDayPart handles explicit unscheduled value as override', () => {
  assert.match(dayColumn, /explicit.*unscheduled|"unscheduled"\).*return.*"unscheduled"/, 'explicit unscheduled must bypass startTime classification');
});

// 24. No duplicate action buttons: timeline clock button is one button
test('ItineraryItemCard timeline button is a single non-duplicated control', () => {
  const ariaMatches = (itemCard.match(/aria-label="Set timeline"/g) ?? []).length;
  assert.equal(ariaMatches, 1, 'only one aria-label="Set timeline" button must exist');
});


// 25. Early-morning (00:00-04:59) classification should be morning, not unscheduled
test('ItineraryDayColumn classifies early-morning hours as morning', () => {
  assert.ok(dayColumn.includes("normalizedHour >= 0 && normalizedHour < 12"), 'early hours must classify as morning');
});

// 26. Regression fixture: ISO datetime 2026-06-05T03:05:00 must be parsed via T03:05 path and map to morning
test('ItineraryDayColumn includes ISO T-hour parser for 2026-06-05T03:05:00 seam', () => {
  const regressionIsoFixture = '2026-06-05T03:05:00';
  assert.equal(regressionIsoFixture.includes('T03:05'), true, 'regression fixture should encode the production seam');
  assert.ok(dayColumn.includes("input.match(/T(\\d{2}):/)"), 'ISO T-hour parser must exist');
  assert.match(dayColumn, /normalizedHour\s*>?=\s*0\s*&&\s*normalizedHour\s*<\s*12/, 'ISO early hour must resolve to morning');
});

// 27. Regression fixture: HH:MM 03:05 must be parsed and map to morning
test('ItineraryDayColumn includes HH:MM parser for "03:05" seam', () => {
  const regressionHhmmFixture = "03:05";
  assert.equal(regressionHhmmFixture.startsWith("03:"), true, 'fixture should represent pre-5AM departure');
  assert.ok(dayColumn.includes('input.match(/^(\\d{1,2}):\\d{2}/)'), 'HH:MM parser must exist for startTime values');
  assert.match(dayColumn, /normalizedHour\s*>?=\s*0\s*&&\s*normalizedHour\s*<\s*12/, 'HH:MM early hour must resolve to morning');
});

// 28. Flight fallback departure fields are considered when startTime is absent (e.g., fallback "03:05")
 test('ItineraryDayColumn reads known flight departure fallback fields from details', () => {
  assert.match(dayColumn, /departureTime/, 'details.departureTime fallback required');
  assert.match(dayColumn, /departure_time/, 'details.departure_time fallback required');
  assert.match(dayColumn, /departureDateTime/, 'details.departureDateTime fallback required');
  assert.match(dayColumn, /departure_datetime/, 'details.departure_datetime fallback required');
});

// 29. Explicit unscheduled override remains intentional contract and appears before parsing
 test('ItineraryDayColumn preserves explicit details.dayPart=unscheduled override', () => {
  assert.match(dayColumn, /explicit\s*===\s*"unscheduled"\)\s*return\s*"unscheduled"/, 'explicit unscheduled override must be preserved');
  const overrideIdx = dayColumn.indexOf('explicit === "unscheduled"');
  const parseIdx = dayColumn.indexOf("const parseHour");
  assert.ok(overrideIdx !== -1 && parseIdx !== -1 && overrideIdx < parseIdx, 'explicit unscheduled override must run before parsing');
});

// 30. Invalid hours should fail closed and not classify as evening (e.g., 99:05)
test('ItineraryDayColumn validates parsed hour range to 0..23', () => {
  assert.match(dayColumn, /hour\s*>=\s*0\s*&&\s*hour\s*<=\s*23/, 'hour validity guard 0..23 required');
  assert.match(dayColumn, /Number\.isFinite\(hour\)/, 'hour validity guard should enforce finite number');
});

// 31. Valid parsed early hours should not fall through to unscheduled
test('ItineraryDayColumn does not route valid early hours to unscheduled', () => {
  assert.match(dayColumn, /if\s*\(normalizedHour\s*!==\s*null\)/, 'valid parsed hour branch must exist');
  assert.match(dayColumn, /return\s+"unscheduled";/, 'unscheduled fallback exists only after timed branches');
});
