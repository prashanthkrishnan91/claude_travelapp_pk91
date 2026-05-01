/**
 * Trip Ideas / Saved Shortlist — renderer contract tests.
 *
 * Verifies that:
 * 1. AIConciergePanel has "Save to Ideas" action alongside "Add to Day".
 * 2. AIConciergePanel tracks savedIdea/savingIdea state separately from addedItems.
 * 3. saveToTripIdeas in api.ts marks items with source_kind: "concierge_idea".
 * 4. TripIdeasPanel renders ideas and exposes "Add to Day" assignment action.
 * 5. TripIdeasPanel does not expose debug/internal fields.
 * 6. Duplicate prevention: saved idea check uses normalizedName, not day-keyed key.
 * 7. onIdeaSaved callback prop exists on AIConciergePanel.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const aiConciergePanel = readFileSync(
  new URL('../src/components/trips/AIConciergePanel.tsx', import.meta.url),
  'utf8',
);

const tripIdeasPanel = readFileSync(
  new URL('../src/components/trips/TripIdeasPanel.tsx', import.meta.url),
  'utf8',
);

const apiTs = readFileSync(
  new URL('../src/lib/api.ts', import.meta.url),
  'utf8',
);

const itineraryItemCard = readFileSync(
  new URL('../src/components/trips/ItineraryItemCard.tsx', import.meta.url),
  'utf8',
);

// ---------------------------------------------------------------------------
// 1. AIConciergePanel: "Save" button exists alongside "Add to Day"
// ---------------------------------------------------------------------------

test('AIConciergePanel has Save button for saving to trip ideas', () => {
  // The "Save" / saved state button must appear in the ConciergeCard actions area
  assert.match(aiConciergePanel, /onSaveIdea/, 'onSaveIdea handler must be present in ConciergeCard');
  assert.match(aiConciergePanel, /savedIdea/, 'savedIdea prop must be declared');
  assert.match(aiConciergePanel, /savingIdea/, 'savingIdea prop must be declared');
});

// ---------------------------------------------------------------------------
// 2. AIConciergePanel: save idea state is separate from add-to-day state
// ---------------------------------------------------------------------------

test('AIConciergePanel tracks savedIdeaItems and savingIdeaItems independently', () => {
  assert.match(aiConciergePanel, /savedIdeaItems/, 'Must have savedIdeaItems state');
  assert.match(aiConciergePanel, /savingIdeaItems/, 'Must have savingIdeaItems state');
  // Must not conflate with addedItems
  assert.match(aiConciergePanel, /addedItems/, 'addedItems state must still exist for Add-to-Day');
});

// ---------------------------------------------------------------------------
// 3. AIConciergePanel: existing Add-to-Day behavior is preserved
// ---------------------------------------------------------------------------

test('AIConciergePanel preserves Add to Day button and selectedDayId logic', () => {
  assert.match(aiConciergePanel, /selectedDayId/, 'selectedDayId must still exist');
  assert.match(aiConciergePanel, /addItem\(/, 'addItem function for day assignment must remain');
  assert.match(aiConciergePanel, /Add to Day/, 'Add to Day label must appear in UI');
});

// ---------------------------------------------------------------------------
// 4. AIConciergePanel: onIdeaSaved callback prop wired up
// ---------------------------------------------------------------------------

test('AIConciergePanel accepts and calls onIdeaSaved callback', () => {
  assert.match(aiConciergePanel, /onIdeaSaved/, 'onIdeaSaved prop must be declared in Props interface');
  assert.match(aiConciergePanel, /onIdeaSaved\?\.\(\)/, 'onIdeaSaved must be called after successful save');
});

// ---------------------------------------------------------------------------
// 5. api.ts: saveToTripIdeas marks items with source_kind = "concierge_idea"
// ---------------------------------------------------------------------------

test('saveToTripIdeas sets source_kind to concierge_idea in item details', () => {
  assert.match(apiTs, /saveToTripIdeas/, 'saveToTripIdeas function must be exported');
  assert.match(apiTs, /source_kind.*concierge_idea|concierge_idea.*source_kind/, 'Must mark saved ideas with source_kind: concierge_idea');
});

// ---------------------------------------------------------------------------
// 6. api.ts: fetchTripIdeas and assignIdeaToDay exported
// ---------------------------------------------------------------------------

test('api.ts exports fetchTripIdeas and assignIdeaToDay', () => {
  assert.match(apiTs, /export async function fetchTripIdeas/, 'fetchTripIdeas must be exported');
  assert.match(apiTs, /export async function assignIdeaToDay/, 'assignIdeaToDay must be exported');
  assert.match(apiTs, /export async function moveIdeaToTripIdeas/, 'moveIdeaToTripIdeas must be exported');
});

// ---------------------------------------------------------------------------
// 7. api.ts: assignIdeaToDay sends day_id via PATCH
// ---------------------------------------------------------------------------

test('assignIdeaToDay uses PATCH on /itinerary/items/{itemId} with day_id', () => {
  const assignFnSection = apiTs.slice(apiTs.indexOf('export async function assignIdeaToDay'));
  const closingIdx = assignFnSection.indexOf('\n}');
  const fn = assignFnSection.slice(0, closingIdx + 2);
  assert.match(fn, /PATCH/, 'Must use PATCH method');
  assert.match(fn, /itinerary\/items/, 'Must target /itinerary/items endpoint');
  assert.match(fn, /day_id/, 'Must send day_id in the payload');
});

test('moveIdeaToTripIdeas uses PATCH with day_id set to null', () => {
  const fnSection = apiTs.slice(apiTs.indexOf('export async function moveIdeaToTripIdeas'));
  const closingIdx = fnSection.indexOf('\n}');
  const fn = fnSection.slice(0, closingIdx + 2);
  assert.match(fn, /PATCH/, 'Must use PATCH method');
  assert.match(fn, /day_id/, 'Must send day_id in payload');
  assert.match(fn, /null/, 'Must set day_id to null to move back to Trip Ideas');
});

// ---------------------------------------------------------------------------
// 8. TripIdeasPanel: renders ideas and exposes Add to Day assignment
// ---------------------------------------------------------------------------

test('TripIdeasPanel exists and has Add to Day assignment action', () => {
  assert.match(tripIdeasPanel, /Add to Day/, '"Add to Day" button must appear in TripIdeasPanel');
  assert.match(tripIdeasPanel, /onAssign/, 'onAssign handler for day assignment must be present');
  assert.match(tripIdeasPanel, /assignIdeaToDay/, 'Must call assignIdeaToDay API function');
});

// ---------------------------------------------------------------------------
// 9. TripIdeasPanel: filters for source_kind === "concierge_idea"
// ---------------------------------------------------------------------------

test('TripIdeasPanel filters items by source_kind === concierge_idea', () => {
  assert.match(tripIdeasPanel, /source_kind.*concierge_idea|concierge_idea.*source_kind/,
    'Must filter for concierge_idea source_kind to avoid mixing with flight/hotel candidates');
});

// ---------------------------------------------------------------------------
// 10. TripIdeasPanel: no debug or internal field leakage in rendered output
// ---------------------------------------------------------------------------

test('TripIdeasPanel does not expose internal debug fields in UI', () => {
  const forbiddenInUI = ['source_kind', 'evidence_count', 'provider_score', 'raw_snippet', 'debug_'];
  for (const field of forbiddenInUI) {
    // The field may appear in logic but must not be directly rendered in JSX text nodes
    const jsxTextPattern = new RegExp(`>\\s*\\{[^}]*${field}[^}]*\\}\\s*<`);
    assert.equal(
      jsxTextPattern.test(tripIdeasPanel),
      false,
      `Internal field "${field}" must not be directly rendered as visible JSX text`,
    );
  }
});

// ---------------------------------------------------------------------------
// 11. TripIdeasPanel: remove action exists
// ---------------------------------------------------------------------------

test('TripIdeasPanel has remove action to delete ideas', () => {
  assert.match(tripIdeasPanel, /onRemove/, 'onRemove prop must exist on IdeaCard');
  assert.match(tripIdeasPanel, /deleteItem/, 'Must call deleteItem to remove ideas');
});

// ---------------------------------------------------------------------------
// 12. AIConciergePanel: saveIdea uses name-keyed deduplication (trip-wide)
// ---------------------------------------------------------------------------

test('AIConciergePanel saveIdea deduplicates by normalizedName not day-keyed cardKey', () => {
  // saveIdea must NOT use `cardKey(name, selectedDayId)` — it uses the plain normalized name
  const saveIdeaSection = aiConciergePanel.slice(aiConciergePanel.indexOf('async function saveIdea'));
  const end = saveIdeaSection.indexOf('\n  }');
  const fn = saveIdeaSection.slice(0, end + 4);
  assert.doesNotMatch(fn, /cardKey\(/, 'saveIdea must NOT use day-keyed cardKey for deduplication');
  assert.match(fn, /normalizedName/, 'saveIdea must use normalizedName for trip-wide deduplication');
});

// ---------------------------------------------------------------------------
// 13. api.ts: updateIdeaMeta is exported
// ---------------------------------------------------------------------------

test('api.ts exports updateIdeaMeta for persisting triage status and notes', () => {
  assert.match(apiTs, /export async function updateIdeaMeta/, 'updateIdeaMeta must be exported from api.ts');
  assert.match(apiTs, /ideaStatus|idea_status/, 'updateIdeaMeta must reference ideaStatus field');
  assert.match(apiTs, /userNote|user_note/, 'updateIdeaMeta must reference userNote field');
});

// ---------------------------------------------------------------------------
// 14. api.ts: saveToTripIdeas sets a default idea_status of "maybe"
// ---------------------------------------------------------------------------

test('saveToTripIdeas sets idea_status to "maybe" by default', () => {
  const saveFnStart = apiTs.indexOf('export async function saveToTripIdeas');
  const saveFnEnd = apiTs.indexOf('\nexport async function', saveFnStart + 1);
  const fn = apiTs.slice(saveFnStart, saveFnEnd > 0 ? saveFnEnd : undefined);
  assert.match(fn, /idea_status.*maybe|maybe.*idea_status/, 'saveToTripIdeas must default idea_status to "maybe"');
});

// ---------------------------------------------------------------------------
// 15. TripIdeasPanel: has status buttons (Must-do, Maybe, Skip)
// ---------------------------------------------------------------------------

test('TripIdeasPanel has Must-do, Maybe, and Skip priority buttons', () => {
  assert.match(tripIdeasPanel, /Must-do/, '"Must-do" status label must appear in TripIdeasPanel');
  assert.match(tripIdeasPanel, /Maybe/, '"Maybe" status label must appear in TripIdeasPanel');
  assert.match(tripIdeasPanel, /Skip/, '"Skip" status label must appear in TripIdeasPanel');
  assert.match(tripIdeasPanel, /must_do/, 'must_do value must be present in STATUS_OPTIONS');
  assert.match(tripIdeasPanel, /skipped/, 'skipped value must be present for filtering');
});

test('ItineraryItemCard renders Move to Ideas action only for concierge ideas', () => {
  assert.match(itineraryItemCard, /isConciergeIdea/, 'Card must derive concierge marker from details');
  assert.match(itineraryItemCard, /Move to Ideas/, 'Card must render Move to Ideas action');
  assert.match(itineraryItemCard, /showMoveToIdeasAction/, 'Move action should be gated to concierge ideas only');
});

test('ItineraryItemCard contains exactly one Move to Ideas label and one concierge gate', () => {
  const moveLabelCount = (itineraryItemCard.match(/Move to Ideas/g) ?? []).length;
  const gateCount = (itineraryItemCard.match(/showMoveToIdeasAction/g) ?? []).length;
  assert.equal(moveLabelCount, 1, 'There must be exactly one visible Move to Ideas action label in the card renderer');
  assert.equal(gateCount, 2, 'Gate should be defined once and rendered once in one canonical location');
});
