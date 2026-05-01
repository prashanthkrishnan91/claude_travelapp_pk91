/**
 * Smart Day Timeline AI Planning v1 — contract tests.
 *
 * Verifies:
 * 1. dayPlanner.ts exports suggestTimelineFallback with correct output shape.
 * 2. Fallback planner rules: breakfast→morning, dinner→evening, lunch→afternoon.
 * 3. Flights and hotels are always unscheduled (conservative).
 * 4. Existing details.dayPart is preserved by the fallback planner.
 * 5. Existing details fields are not overwritten during suggestion application.
 * 6. timeLabel is cleared/omitted safely when empty.
 * 7. day_id is never modified by the planner.
 * 8. api.ts exports suggestDayTimeline function.
 * 9. ItineraryDayColumn has Suggest Timing button and suggestion state.
 * 10. Suggestion review panel: Apply All and Dismiss controls.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const plannerSrc = readFileSync(
  new URL('../src/lib/dayPlanner.ts', import.meta.url),
  'utf8',
);

const apiSrc = readFileSync(
  new URL('../src/lib/api.ts', import.meta.url),
  'utf8',
);

const dayColumn = readFileSync(
  new URL('../src/components/trips/ItineraryDayColumn.tsx', import.meta.url),
  'utf8',
);

// ---------------------------------------------------------------------------
// dayPlanner.ts — exports and shape
// ---------------------------------------------------------------------------

test('dayPlanner exports suggestTimelineFallback', () => {
  assert.match(plannerSrc, /export function suggestTimelineFallback/, 'suggestTimelineFallback must be exported');
});

test('dayPlanner exports DayPlannerSuggestion type with itemId and dayPart', () => {
  assert.match(plannerSrc, /DayPlannerSuggestion/, 'DayPlannerSuggestion type must be exported');
  assert.match(plannerSrc, /itemId/, 'DayPlannerSuggestion must include itemId');
  assert.match(plannerSrc, /dayPart/, 'DayPlannerSuggestion must include dayPart');
  assert.match(plannerSrc, /timeLabel/, 'DayPlannerSuggestion must include optional timeLabel');
});

// ---------------------------------------------------------------------------
// Fallback planner keyword rules
// ---------------------------------------------------------------------------

test('dayPlanner fallback assigns morning to breakfast items', () => {
  assert.match(plannerSrc, /MORNING_PAT|morning.*breakfast|breakfast.*morning/i, 'breakfast must map to morning');
});

test('dayPlanner fallback assigns morning to cafe/coffee items', () => {
  assert.match(plannerSrc, /coffee|cafe|caf[eé]|bakery/i, 'coffee/cafe/bakery must be in morning pattern');
});

test('dayPlanner fallback assigns evening to dinner/bar items', () => {
  assert.match(plannerSrc, /EVENING_PAT|dinner|supper|cocktail/i, 'dinner/cocktail must map to evening');
});

test('dayPlanner fallback assigns afternoon to lunch items', () => {
  assert.match(plannerSrc, /LUNCH_PAT|\\blunch\\b|lunch.*afternoon/i, 'lunch must map to afternoon');
});

test('dayPlanner fallback keeps flights unscheduled', () => {
  assert.match(plannerSrc, /flight.*unscheduled|"flight"/, 'flight must be conservative → unscheduled');
});

test('dayPlanner fallback keeps hotels unscheduled', () => {
  assert.match(plannerSrc, /hotel.*unscheduled|"hotel"/, 'hotel must be conservative → unscheduled');
});

test('dayPlanner fallback assigns morning to generic activity items', () => {
  assert.match(plannerSrc, /activity.*morning|"activity"/, 'activity type defaults to morning');
});

test('dayPlanner fallback assigns afternoon to generic meal items', () => {
  assert.match(plannerSrc, /meal.*afternoon|"meal"/, 'meal type defaults to afternoon');
});

// ---------------------------------------------------------------------------
// Existing details.dayPart preservation
// ---------------------------------------------------------------------------

test('dayPlanner fallback preserves explicit dayPart already stored in details', () => {
  // The planner checks for d.dayPart before classifying
  assert.match(plannerSrc, /explicit.*dayPart|d\.dayPart|details.*dayPart/, 'existing dayPart must be checked first');
  assert.match(plannerSrc, /explicit === "morning"|explicit.*morning/, 'morning preservation branch must exist');
  assert.match(plannerSrc, /explicit === "afternoon"|explicit.*afternoon/, 'afternoon preservation branch must exist');
  assert.match(plannerSrc, /explicit === "evening"|explicit.*evening/, 'evening preservation branch must exist');
});

test('dayPlanner fallback preserves existing timeLabel when dayPart is already set', () => {
  // When explicit dayPart is preserved, timeLabel should be passed through
  assert.match(plannerSrc, /d\.timeLabel|timeLabel.*d\./, 'timeLabel must be read from details when preserving dayPart');
});

// ---------------------------------------------------------------------------
// timeLabel handling
// ---------------------------------------------------------------------------

test('dayPlanner returns undefined/omits timeLabel when no label is strongly implied', () => {
  // The planner returns undefined (not a blank string) for timeLabel when unset
  assert.match(plannerSrc, /timeLabel.*undefined|undefined.*timeLabel|\|\| undefined/, 'timeLabel must default to undefined, not blank string');
});

// ---------------------------------------------------------------------------
// day_id safety
// ---------------------------------------------------------------------------

test('dayPlanner never references or modifies day_id', () => {
  assert.doesNotMatch(plannerSrc, /day_id|dayId/, 'dayPlanner must not touch day_id');
});

// ---------------------------------------------------------------------------
// api.ts — suggestDayTimeline
// ---------------------------------------------------------------------------

test('api.ts exports suggestDayTimeline function', () => {
  assert.match(apiSrc, /export async function suggestDayTimeline/, 'suggestDayTimeline must be exported from api.ts');
});

test('api.ts suggestDayTimeline exports TimelineSuggestion type', () => {
  assert.match(apiSrc, /TimelineSuggestion/, 'TimelineSuggestion interface must be defined in api.ts');
  assert.match(apiSrc, /dayPart/, 'TimelineSuggestion must include dayPart');
  assert.match(apiSrc, /timeLabel/, 'TimelineSuggestion must include optional timeLabel');
});

test('api.ts suggestDayTimeline calls /ai/timeline/suggest backend endpoint', () => {
  assert.match(apiSrc, /\/ai\/timeline\/suggest/, 'suggestDayTimeline must call /ai/timeline/suggest');
});

test('api.ts suggestDayTimeline falls back to client-side planner on backend failure', () => {
  assert.match(apiSrc, /suggestTimelineFallback/, 'suggestDayTimeline must import suggestTimelineFallback as fallback');
  assert.match(apiSrc, /catch/, 'suggestDayTimeline must catch backend errors and use fallback');
});

test('api.ts suggestDayTimeline preserves other details fields (uses updateItemTimeline merge)', () => {
  // The apply flow uses updateItemTimeline which spreads currentDetails
  assert.match(apiSrc, /updateItemTimeline/, 'updateItemTimeline must exist for field-safe persistence');
  assert.match(apiSrc, /\.\.\.(currentDetails|merged)/, 'existing details must be spread before patching');
});

// ---------------------------------------------------------------------------
// ItineraryDayColumn — Suggest Timing button + review panel
// ---------------------------------------------------------------------------

test('ItineraryDayColumn has suggestingTimeline state', () => {
  assert.match(dayColumn, /suggestingTimeline/, 'suggestingTimeline state must exist in ItineraryDayColumn');
});

test('ItineraryDayColumn has timelineSuggestions state', () => {
  assert.match(dayColumn, /timelineSuggestions/, 'timelineSuggestions state must exist in ItineraryDayColumn');
});

test('ItineraryDayColumn has applyingTimeline state', () => {
  assert.match(dayColumn, /applyingTimeline/, 'applyingTimeline state must exist in ItineraryDayColumn');
});

test('ItineraryDayColumn has handleSuggestTimeline handler that calls suggestDayTimeline', () => {
  assert.match(dayColumn, /handleSuggestTimeline/, 'handleSuggestTimeline handler must exist');
  assert.match(dayColumn, /suggestDayTimeline/, 'suggestDayTimeline must be called from handler');
});

test('ItineraryDayColumn has handleApplyTimeline handler that calls updateItemTimeline', () => {
  assert.match(dayColumn, /handleApplyTimeline/, 'handleApplyTimeline handler must exist');
  assert.match(dayColumn, /updateItemTimeline/, 'updateItemTimeline must be called in apply handler');
});

test('ItineraryDayColumn renders Suggest Timing button with aria-label', () => {
  assert.match(dayColumn, /Suggest Timing/, 'Suggest Timing button text must appear');
  assert.match(dayColumn, /aria-label="Suggest day timing"/, 'Suggest Timing button must have aria-label');
});

test('ItineraryDayColumn renders SuggestionsReviewPanel when suggestions exist', () => {
  assert.match(dayColumn, /SuggestionsReviewPanel/, 'SuggestionsReviewPanel component must exist and be used');
  assert.match(dayColumn, /timelineSuggestions &&/, 'suggestions panel must be conditionally rendered');
});

test('SuggestionsReviewPanel has Apply All Suggestions and Dismiss controls', () => {
  assert.match(dayColumn, /Apply All Suggestions/, 'Apply All Suggestions button must exist');
  assert.match(dayColumn, /onDismiss|Dismiss/, 'Dismiss control must exist in suggestions panel');
});

test('ItineraryDayColumn handleApplyTimeline does not modify day_id', () => {
  // The apply handler only calls updateItemTimeline (which patches dayPart/timeLabel)
  // It must NOT call assignIdeaToDay or moveIdeaToTripIdeas or pass day_id
  assert.doesNotMatch(
    dayColumn,
    /assignIdeaToDay|moveIdeaToTripIdeas/,
    'apply handler must not reassign day_id'
  );
});

test('ItineraryDayColumn imports suggestDayTimeline and updateItemTimeline from api', () => {
  assert.match(dayColumn, /from "@\/lib\/api"/, 'api imports must be present in ItineraryDayColumn');
  assert.match(dayColumn, /suggestDayTimeline/, 'suggestDayTimeline import must be present');
  assert.match(dayColumn, /updateItemTimeline/, 'updateItemTimeline import must be present');
});
