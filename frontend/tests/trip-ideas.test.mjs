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
// 9. TripIdeasPanel does not hard-filter to concierge_idea only
// ---------------------------------------------------------------------------

test('TripIdeasPanel does not hard-filter to source_kind concierge_idea only', () => {
  assert.doesNotMatch(
    tripIdeasPanel,
    /source_kind\s*===\s*["']concierge_idea["']/,
    'Trip ideas visibility should not depend on a single source_kind value.',
  );
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

test('saveToTripIdeas persists optional google verification metadata into details', () => {
  const saveFnStart = apiTs.indexOf('export async function saveToTripIdeas');
  const saveFnEnd = apiTs.indexOf('\nexport async function', saveFnStart + 1);
  const fn = apiTs.slice(saveFnStart, saveFnEnd > 0 ? saveFnEnd : undefined);
  assert.match(fn, /normalizeGoogleVerificationDetails\(item\)/, 'saveToTripIdeas must merge normalized google verification metadata');
  assert.match(apiTs, /provider_place_id/, 'google provider_place_id must be persisted in details');
  assert.match(apiTs, /formatted_address/, 'google formatted_address must be persisted in details');
  assert.match(apiTs, /google_maps_uri/, 'google_maps_uri must be persisted in details');
});

test('addStructuredConciergeItemToTrip persists optional google verification metadata into details', () => {
  const addFnStart = apiTs.indexOf('export async function addStructuredConciergeItemToTrip');
  const addFnEnd = apiTs.indexOf('\nexport async function', addFnStart + 1);
  const fn = apiTs.slice(addFnStart, addFnEnd > 0 ? addFnEnd : undefined);
  assert.match(fn, /normalizeGoogleVerificationDetails\(item\)/, 'addStructuredConciergeItemToTrip must merge normalized google verification metadata');
  assert.match(apiTs, /if \(!gv \|\| typeof gv !== "object"\) return \{\}/, 'metadata helper must safely no-op when googleVerification is absent');
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

test('ItineraryItemCard invokes move-back handler exactly once from one action button', () => {
  const moveHandlerCallCount = (itineraryItemCard.match(/onMoveToIdeas\(item.id\)/g) ?? []).length;
  assert.equal(moveHandlerCallCount, 1, 'Move-back handler should be wired to exactly one UI action');
  assert.doesNotMatch(
    itineraryItemCard,
    /mt-1 rounded-md border border-amber-300\/35 bg-amber-300\/10 px-2 py-1 text-\[11px\]/,
    'Secondary inline/details Move to Ideas button must not be rendered'
  );
});

// ---------------------------------------------------------------------------
// Filter / Search / Sort v1 — tests 18–27
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// 18. Exported filter/search/sort functions exist
// ---------------------------------------------------------------------------

test('TripIdeasPanel exports filterByStatus, searchIdeas, and sortIdeas functions', () => {
  assert.match(tripIdeasPanel, /export function filterByStatus/, 'filterByStatus must be exported');
  assert.match(tripIdeasPanel, /export function searchIdeas/, 'searchIdeas must be exported');
  assert.match(tripIdeasPanel, /export function sortIdeas/, 'sortIdeas must be exported');
});

// ---------------------------------------------------------------------------
// 19. filterByStatus: "active" excludes skipped, specific value filters to that value
// ---------------------------------------------------------------------------

test('filterByStatus handles active, must_do, maybe, skipped filter values', () => {
  const fnStart = tripIdeasPanel.indexOf('export function filterByStatus');
  const fnEnd = tripIdeasPanel.indexOf('\nexport function', fnStart + 1);
  const fn = tripIdeasPanel.slice(fnStart, fnEnd > 0 ? fnEnd : undefined);
  assert.match(fn, /filter === "active"/, '"active" filter case must exist');
  assert.match(fn, /!== "skipped"/, '"active" must exclude skipped items');
  assert.match(fn, /=== filter/, 'specific status filter must use equality check');
});

// ---------------------------------------------------------------------------
// 20. searchIdeas: matches title, location, address, notes, category
// ---------------------------------------------------------------------------

test('searchIdeas searches title, location, address, note, and category fields', () => {
  const fnStart = tripIdeasPanel.indexOf('export function searchIdeas');
  const fnEnd = tripIdeasPanel.indexOf('\nexport function', fnStart + 1);
  const fn = tripIdeasPanel.slice(fnStart, fnEnd > 0 ? fnEnd : undefined);
  assert.match(fn, /idea\.title\.toLowerCase/, 'searchIdeas must search title');
  assert.match(fn, /idea\.location/, 'searchIdeas must search location');
  assert.match(fn, /address/, 'searchIdeas must search address from details');
  assert.match(fn, /userNote|user_note/, 'searchIdeas must search user note');
  assert.match(fn, /ideaCategory/, 'searchIdeas must search category');
  assert.match(fn, /if \(!q\) return ideas/, 'searchIdeas must short-circuit on empty query');
});

// ---------------------------------------------------------------------------
// 21. sortIdeas: all four sort options are handled
// ---------------------------------------------------------------------------

test('sortIdeas handles priority, recently_saved, name, and category sort options', () => {
  const fnStart = tripIdeasPanel.indexOf('export function sortIdeas');
  const fnEnd = tripIdeasPanel.indexOf('\nfunction IdeaCard', fnStart + 1);
  const fn = tripIdeasPanel.slice(fnStart, fnEnd > 0 ? fnEnd : undefined);
  assert.match(fn, /case "priority"/, 'priority sort must be handled');
  assert.match(fn, /case "recently_saved"/, 'recently_saved sort must be handled');
  assert.match(fn, /case "name"/, 'name sort must be handled');
  assert.match(fn, /case "category"/, 'category sort must be handled');
  assert.match(fn, /PRIORITY_ORDER/, 'priority sort must use PRIORITY_ORDER map');
  assert.match(fn, /createdAt/, 'recently_saved sort must use createdAt timestamp');
  assert.match(fn, /title\.localeCompare/, 'name sort must use localeCompare');
  assert.match(fn, /ideaCategory.*localeCompare|localeCompare.*ideaCategory/, 'category sort must use ideaCategory + localeCompare');
});

// ---------------------------------------------------------------------------
// 22. PRIORITY_ORDER: must_do < maybe < skipped
// ---------------------------------------------------------------------------

test('PRIORITY_ORDER ranks must_do first, then maybe, then skipped', () => {
  assert.match(tripIdeasPanel, /must_do:\s*0/, 'must_do must have priority 0 (highest)');
  assert.match(tripIdeasPanel, /maybe:\s*1/, 'maybe must have priority 1');
  assert.match(tripIdeasPanel, /skipped:\s*2/, 'skipped must have priority 2 (lowest)');
});

// ---------------------------------------------------------------------------
// 23. STATUS_FILTER_OPTIONS: all four status filter values present
// ---------------------------------------------------------------------------

test('STATUS_FILTER_OPTIONS includes active, must_do, maybe, and skipped values', () => {
  assert.match(tripIdeasPanel, /STATUS_FILTER_OPTIONS/, 'STATUS_FILTER_OPTIONS constant must exist');
  assert.match(tripIdeasPanel, /"active"/, '"active" status filter value must exist');
  assert.match(tripIdeasPanel, /"must_do"/, '"must_do" status filter value must exist');
  assert.match(tripIdeasPanel, /"maybe"/, '"maybe" status filter value must exist');
  assert.match(tripIdeasPanel, /"skipped"/, '"skipped" status filter value must exist');
});

// ---------------------------------------------------------------------------
// 24. SORT_OPTIONS: all four sort options present
// ---------------------------------------------------------------------------

test('SORT_OPTIONS includes priority, recently_saved, name, and category options', () => {
  assert.match(tripIdeasPanel, /SORT_OPTIONS/, 'SORT_OPTIONS constant must exist');
  assert.match(tripIdeasPanel, /"recently_saved"/, '"recently_saved" sort option must exist');
  assert.match(tripIdeasPanel, /"priority"/, '"priority" sort option must exist');
  assert.match(tripIdeasPanel, /"name"/, '"name" sort option must exist');
  assert.match(tripIdeasPanel, /"category"/, '"category" sort option must exist');
});

// ---------------------------------------------------------------------------
// 25. Search input and controls are present in the panel
// ---------------------------------------------------------------------------

test('TripIdeasPanel renders search input and filter/sort controls', () => {
  assert.match(tripIdeasPanel, /Search ideas/, 'Search placeholder text must appear');
  assert.match(tripIdeasPanel, /aria-label="Search trip ideas"/, 'Search input must have accessible label');
  assert.match(tripIdeasPanel, /aria-label="Sort ideas"/, 'Sort select must have accessible label');
  assert.match(tripIdeasPanel, /STATUS_FILTER_OPTIONS\.map/, 'Status filter pills must be rendered from STATUS_FILTER_OPTIONS');
  assert.match(tripIdeasPanel, /SORT_OPTIONS\.map/, 'Sort options must be rendered from SORT_OPTIONS');
});

// ---------------------------------------------------------------------------
// 26. hasActiveFilters gates the Clear button; handleReset resets all controls
// ---------------------------------------------------------------------------

test('TripIdeasPanel has hasActiveFilters guard and handleReset function for clear action', () => {
  assert.match(tripIdeasPanel, /hasActiveFilters/, 'hasActiveFilters derived value must exist');
  assert.match(tripIdeasPanel, /handleReset/, 'handleReset function must exist');
  assert.match(tripIdeasPanel, /Reset/, 'Reset/clear button label must appear in UI');
  assert.match(tripIdeasPanel, /setSearchQuery\(""\)/, 'handleReset must clear search query');
  assert.match(tripIdeasPanel, /setStatusFilter\("active"\)/, 'handleReset must reset status filter to active');
  assert.match(tripIdeasPanel, /setSortBy\("priority"\)/, 'handleReset must reset sort to priority');
});

// ---------------------------------------------------------------------------
// 27. Empty state differentiates: no ideas vs no filter match
// ---------------------------------------------------------------------------

test('TripIdeasPanel shows different empty states for no ideas and no filter match', () => {
  // No-ideas state: bookmark icon + helpful onboarding copy
  assert.match(
    tripIdeasPanel,
    /No ideas yet/,
    'Must show "No ideas yet" heading when no ideas exist',
  );
  assert.match(
    tripIdeasPanel,
    /Save recommendations from AI Concierge or Explore/,
    'Must show onboarding guidance mentioning real idea sources',
  );
  // No-results state: search icon + "No matching ideas" heading
  assert.match(
    tripIdeasPanel,
    /No matching ideas/,
    'Must show filter-empty state when ideas exist but none match current filters',
  );
  // The two empty states must be in different branches (ideas.length === 0 vs filteredAndSorted.length === 0)
  const noIdeasIdx = tripIdeasPanel.indexOf('No ideas yet');
  const noMatchIdx = tripIdeasPanel.indexOf('No matching ideas');
  assert.notEqual(noIdeasIdx, -1, 'Onboarding empty state must exist');
  assert.notEqual(noMatchIdx, -1, 'Filter-empty state must exist');
  assert.notEqual(noIdeasIdx, noMatchIdx, 'The two empty states must be at different locations in the source');
});
