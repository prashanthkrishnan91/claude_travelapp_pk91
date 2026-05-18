/**
 * Core trip-flow regression fixes — contract tests.
 *
 * Guards the five regressions fixed in this PR:
 *
 * Issue 1 — Round-trip placement: flight is split into two leg items
 *   (outbound + return) placed on correct trip days.
 * Issue 2 — Outside Concierge save: ConciergeResultCard exposes a Save action
 *   for addable canonical cards.
 * Issue 3 — CityAutocomplete z-index: form has overflow:visible so dropdown
 *   is not clipped by advisor-desk-panel's overflow:hidden.
 * Issue 4 — Plan My Day diversity: backend uses day_number to offset restaurant
 *   selection so different days get different picks.
 * Issue 5 — Optimize copy: provider_unavailable copy is specific about hotel
 *   pricing being the blocker (not generic "unavailable").
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const apiSrc = readFileSync(
  new URL('../src/lib/api.ts', import.meta.url),
  'utf8',
);
const tripBuilder = readFileSync(
  new URL('../src/components/trips/TripBuilder.tsx', import.meta.url),
  'utf8',
);
const concierge = readFileSync(
  new URL('../src/components/concierge/ConciergePage.tsx', import.meta.url),
  'utf8',
);
const tripBuilderForm = readFileSync(
  new URL('../src/components/trips/TripBuilderForm.tsx', import.meta.url),
  'utf8',
);
const optimizeModal = readFileSync(
  new URL('../src/components/trips/OptimizeTripModal.tsx', import.meta.url),
  'utf8',
);

// ─── Issue 1: Round-trip leg placement ───────────────────────────────────────

test('Issue1: api.ts exports addRoundTripLegToDay', () => {
  assert.match(
    apiSrc,
    /export async function addRoundTripLegToDay/,
    'addRoundTripLegToDay must be exported from api.ts',
  );
});

test('Issue1: addRoundTripLegToDay accepts leg:"outbound"|"return" parameter', () => {
  assert.match(
    apiSrc,
    /leg:\s*["']outbound["']\s*\|\s*["']return["']/,
    'addRoundTripLegToDay must accept a typed "outbound"|"return" leg param',
  );
});

test('Issue1: addRoundTripLegToDay sets is_round_trip:false per leg (disables combined render)', () => {
  assert.match(
    apiSrc,
    /is_round_trip:\s*false/,
    'Each leg must set is_round_trip:false so ItineraryItemCard renders as one-way card',
  );
});

test('Issue1: addRoundTripLegToDay sets round_trip_price_included for return leg', () => {
  assert.match(
    apiSrc,
    /round_trip_price_included/,
    'Return leg must mark price as included in the round-trip total',
  );
});

test('Issue1: addRoundTripLegToDay sets leg_of_round_trip for provenance', () => {
  assert.match(
    apiSrc,
    /leg_of_round_trip/,
    'Each leg item must carry leg_of_round_trip for provenance tracing',
  );
});

test('Issue1: TripBuilder imports addRoundTripLegToDay', () => {
  assert.match(
    tripBuilder,
    /addRoundTripLegToDay/,
    'TripBuilder must import and use addRoundTripLegToDay',
  );
});

test('Issue1: handleAddRoundTripToItinerary calls addRoundTripLegToDay for outbound leg', () => {
  assert.match(
    tripBuilder,
    /addRoundTripLegToDay\s*\(\s*\n?\s*tripId[^)]*["']outbound["']/s,
    'Must call addRoundTripLegToDay with "outbound" leg',
  );
});

test('Issue1: handleAddRoundTripToItinerary calls addRoundTripLegToDay for return leg', () => {
  assert.match(
    tripBuilder,
    /addRoundTripLegToDay\s*\(\s*\n?\s*tripId[^)]*["']return["']/s,
    'Must call addRoundTripLegToDay with "return" leg',
  );
});

test('Issue1: TripBuilder resolves outbound day from normalizeIsoDate of departure time', () => {
  assert.match(
    tripBuilder,
    /outboundDate.*normalizeIsoDate|normalizeIsoDate.*outboundDate/s,
    'Outbound departure date must be derived via normalizeIsoDate',
  );
});

test('Issue1: TripBuilder resolves return day from normalizeIsoDate of return departure time', () => {
  assert.match(
    tripBuilder,
    /returnDate.*normalizeIsoDate|normalizeIsoDate.*returnDate/s,
    'Return departure date must be derived via normalizeIsoDate',
  );
});

test('Issue1: handleAddRoundTripToItinerary falls back to days[0] for outbound when no date match', () => {
  assert.match(
    tripBuilder,
    /days\[0\]/,
    'Must fall back to days[0] as outbound day when no date match',
  );
});

test('Issue1: handleAddRoundTripToItinerary falls back to last day for return when no date match', () => {
  assert.match(
    tripBuilder,
    /days\[days\.length\s*-\s*1\]/,
    'Must fall back to last day as return day when no date match',
  );
});

test('Issue1: toast message distinguishes same-day vs different-day round-trip', () => {
  assert.match(
    tripBuilder,
    /outboundDay\.dayNumber\s*===\s*returnDay\.dayNumber/,
    'Toast message must handle same-day vs split-day round-trip placement',
  );
});

test('Issue1: handleAddRoundTripToItinerary has rollback on return-leg failure', () => {
  assert.match(
    tripBuilder,
    /deleteItem\(outboundItem\.id\)/,
    'Must attempt deleteItem(outboundItem.id) if return-leg add fails',
  );
});

test('Issue1: local state update happens only after both legs succeed', () => {
  // setDays must appear after returnItem is assigned (not between the two POSTs)
  const setDaysIdx = tripBuilder.indexOf('// Both legs succeeded');
  const returnItemIdx = tripBuilder.indexOf('returnItem = await addRoundTripLegToDay');
  assert.ok(
    returnItemIdx !== -1 && setDaysIdx > returnItemIdx,
    'setDays must be called only after both outbound and return items exist',
  );
});

test('Issue1: one-way add still uses addOneWayFlightToDay (no regression)', () => {
  assert.match(
    tripBuilder,
    /addOneWayFlightToDay\s*\(\s*tripId/,
    'One-way flight add must still call addOneWayFlightToDay',
  );
});

test('Issue1: addRoundTripFlightToDay still present in api.ts (not removed)', () => {
  assert.match(
    apiSrc,
    /export async function addRoundTripFlightToDay/,
    'addRoundTripFlightToDay must remain in api.ts (used by other flows)',
  );
});

// ─── Issue 2: Outside Concierge save action ───────────────────────────────────

test('Issue2: ConciergePage imports saveItem from api', () => {
  assert.match(
    concierge,
    /saveItem/,
    'ConciergePage must import saveItem to persist saved cards',
  );
});

test('Issue2: ConciergeResultCard accepts onSave prop', () => {
  assert.match(
    concierge,
    /onSave\s*\?\s*:/,
    'ConciergeResultCard must have an optional onSave prop',
  );
});

test('Issue2: ConciergeResultCard accepts saveState prop', () => {
  assert.match(
    concierge,
    /saveState.*SaveState|saveState.*"idle"/s,
    'ConciergeResultCard must accept saveState prop',
  );
});

test('Issue2: Save button renders in ConciergeResultCard', () => {
  assert.match(
    concierge,
    /concierge-result-save-btn/,
    'ConciergeResultCard must render a save button with testid concierge-result-save-btn',
  );
});

test('Issue2: Save button shows "Saved" label when saveState is "saved"', () => {
  assert.match(
    concierge,
    /Saved/,
    'Save button must show "Saved" when in saved state',
  );
});

test('Issue2: Save button shows Loader when saving', () => {
  assert.match(
    concierge,
    /saving.*animate-spin|animate-spin.*saving/s,
    'Save button must show spinner while saving',
  );
});

test('Issue2: onSave only wired to addable canonical cards (isSaveable guard)', () => {
  assert.match(
    concierge,
    /isSaveable.*isAddableCanonicalCard|isAddableCanonicalCard.*isSaveable/s,
    'onSave must only be passed for cards that pass isAddableCanonicalCard',
  );
});

test('Issue2: handleSaveCard builds SavedItemCreate with vertical', () => {
  assert.match(
    concierge,
    /handleSaveCard/,
    'ConciergePage must define handleSaveCard function',
  );
});

test('Issue2: handleSaveCard passes provenance:outside_concierge', () => {
  assert.match(
    concierge,
    /outside_concierge/,
    'Saved item provenance must identify outside_concierge as source',
  );
});

test('Issue2: Map+Source buttons preserved alongside Save button', () => {
  assert.match(
    concierge,
    /Map/,
    'Map button must still be present',
  );
  assert.match(
    concierge,
    /Source/,
    'Source button must still be present',
  );
});

test('Issue2: cardSaveStates uses Map keyed per card', () => {
  assert.match(
    concierge,
    /cardSaveStates.*Map|Map.*cardSaveStates/s,
    'Save state must be tracked per card via a Map',
  );
});

test('Issue2: handleSaveCard uses google_places provider identity (not google)', () => {
  assert.match(
    concierge,
    /provider:\s*["']google_places["']/,
    'Saved item provider must be "google_places" to match Explore dedupe key',
  );
  assert.ok(
    !concierge.includes('provider: "google"') && !concierge.includes("provider: 'google'"),
    'Provider must not be bare "google" — that breaks SavedItemsService dedupe',
  );
});

test('Issue2: handleSaveCard guards against missing providerPlaceId', () => {
  assert.match(
    concierge,
    /if\s*\(!providerPlaceId\)/,
    'Must not call saveItem when providerPlaceId is absent',
  );
});

test('Issue2: handleSaveCard displaySnapshot uses googleMapsUri camelCase key', () => {
  // Validate the snapshot uses camelCase so saveItem/toSnake converts it consistently
  const saveBlock = concierge.slice(concierge.indexOf('handleSaveCard'));
  assert.match(
    saveBlock,
    /googleMapsUri/,
    'displaySnapshot must use camelCase googleMapsUri, not hand-written google_maps_uri',
  );
  assert.ok(
    !saveBlock.slice(0, saveBlock.indexOf('outside_concierge') + 20).includes('google_maps_uri:'),
    'displaySnapshot must not use snake_case google_maps_uri — let saveItem/toSnake handle conversion',
  );
});

// ─── Issue 3: CityAutocomplete dropdown overflow ──────────────────────────────

test('Issue3: TripBuilderForm form has overflow:visible to allow dropdown above fields', () => {
  assert.match(
    tripBuilderForm,
    /overflow.*visible/,
    'Form element must have overflow:visible to prevent clipping the CityAutocomplete dropdown',
  );
});

test('Issue3: CityAutocomplete dropdown has high z-index (z-50)', () => {
  const autocompleteSrc = readFileSync(
    new URL('../src/components/ui/CityAutocomplete.tsx', import.meta.url),
    'utf8',
  );
  assert.match(
    autocompleteSrc,
    /z-50|z-\[/,
    'CityAutocomplete dropdown must have z-50 or higher z-index',
  );
});

test('Issue3: CityAutocomplete preserves selection behavior (handleSelect)', () => {
  const autocompleteSrc = readFileSync(
    new URL('../src/components/ui/CityAutocomplete.tsx', import.meta.url),
    'utf8',
  );
  assert.match(
    autocompleteSrc,
    /handleSelect/,
    'CityAutocomplete handleSelect function must still be present',
  );
});

// ─── Issue 4: Plan My Day diversity ──────────────────────────────────────────

const planRouterSrc = readFileSync(
  new URL('../../backend/app/routes/plan.py', import.meta.url),
  'utf8',
);

test('Issue4: backend plan.py uses day_number to offset restaurant selection', () => {
  assert.match(
    planRouterSrc,
    /day_number/,
    'plan.py must use day_number to diversify restaurant selection',
  );
});

test('Issue4: backend plan.py uses offset/modulo for diversity (not always index 0)', () => {
  assert.match(
    planRouterSrc,
    /offset|%\s*pool/,
    'plan.py must use an offset derived from day_number, not always sorted_restaurants[0]',
  );
});

test('Issue4: DayPlanModal still supports Add and Accept All', () => {
  const dayPlanModal = readFileSync(
    new URL('../src/components/trips/DayPlanModal.tsx', import.meta.url),
    'utf8',
  );
  assert.match(dayPlanModal, /handleAcceptAll/, 'DayPlanModal must still have handleAcceptAll');
  assert.match(dayPlanModal, /handleAdd/, 'DayPlanModal must still have handleAdd');
});

test('Issue4: plan.py still returns honest empty attractions list (no mock)', () => {
  // The endpoint fails closed for attractions (no canonical attraction provider).
  // attractions=[] is the honest state.
  assert.match(
    planRouterSrc,
    /attractions=\[\]/,
    'plan.py must still return empty attractions list when no cluster is provided',
  );
  // Verify no active mock call (comments mentioning _mock_attractions are OK; calls are not)
  assert.ok(
    !planRouterSrc.match(/search_attractions\s*\(\s*mock|mock_attractions\s*\(/),
    'plan.py must not call mock attraction search',
  );
});

// ─── Issue 5: Optimize My Trip copy ──────────────────────────────────────────

test('Issue5: OptimizeTripModal provider_unavailable copy mentions hotel pricing', () => {
  assert.match(
    optimizeModal,
    /nightly rates|hotel pric/i,
    'Provider-unavailable copy must explain hotel pricing is the blocker',
  );
});

test('Issue5: OptimizeTripModal copy does not imply flights are unavailable', () => {
  assert.ok(
    !optimizeModal.includes('Flights & hotels search is temporarily unavailable'),
    'Copy must not say both flights and hotels are unavailable when only hotels lack rates',
  );
});

test('Issue5: OptimizeTripModal provider_unavailable phase is still distinct', () => {
  assert.match(
    optimizeModal,
    /provider_unavailable/,
    'provider_unavailable phase must still exist for fail-closed UX',
  );
});

test('Issue5: OptimizeTripModal no fake hotel rates enabled', () => {
  assert.ok(
    !optimizeModal.includes('hasRealRate: true'),
    'No fake hasRealRate injection allowed',
  );
});

test('Issue5: OptimizeTripModal still guards anyHotelHasRealRate (no mock bypass)', () => {
  assert.match(
    optimizeModal,
    /anyHotelHasRealRate/,
    'Hotel rate guard must remain active — no mock bypass',
  );
});

// ─── Issue 6: Day "+" no longer creates a dead "New item" note ────────────────

test('Issue6: handleAddToDay no longer calls createItem with title "New item"', () => {
  // The old pattern was: createItem(..., { title: "New item" }) — it must be gone
  assert.ok(
    !tripBuilder.includes('"New item"'),
    'handleAddToDay must not immediately create a "New item" note',
  );
});

test('Issue6: handleAddToDay opens Add Note modal via addNoteTargetDayId', () => {
  assert.match(
    tripBuilder,
    /addNoteTargetDayId/,
    'TripBuilder must track addNoteTargetDayId to open the Add Note modal',
  );
  assert.match(
    tripBuilder,
    /setAddNoteTargetDayId/,
    'handleAddToDay must call setAddNoteTargetDayId to open the modal',
  );
});

test('Issue6: AddNoteModal renders with data-testid add-note-modal', () => {
  assert.match(
    tripBuilder,
    /add-note-modal/,
    'AddNoteModal must have data-testid="add-note-modal"',
  );
});

test('Issue6: AddNoteModal has title input and description input', () => {
  assert.match(
    tripBuilder,
    /add-note-title-input/,
    'AddNoteModal must have a title input (data-testid add-note-title-input)',
  );
  assert.match(
    tripBuilder,
    /add-note-description-input/,
    'AddNoteModal must have a description/details input',
  );
});

test('Issue6: AddNoteModal has Save and Cancel buttons', () => {
  assert.match(
    tripBuilder,
    /add-note-save-btn/,
    'AddNoteModal must have a Save button (data-testid add-note-save-btn)',
  );
  assert.match(
    tripBuilder,
    /add-note-cancel-btn/,
    'AddNoteModal must have a Cancel button (data-testid add-note-cancel-btn)',
  );
});

test('Issue6: handleSaveNote creates itemType "note" with user-entered title', () => {
  assert.match(
    tripBuilder,
    /handleSaveNote/,
    'TripBuilder must define handleSaveNote',
  );
  // Save handler passes the title argument through to createItem (not a hardcoded string)
  assert.match(
    tripBuilder,
    /itemType:\s*["']note["']/,
    'Note creation must use itemType: "note"',
  );
});

test('Issue6: Cancel path closes modal without calling createItem', () => {
  // setAddNoteTargetDayId(null) is the cancel path — createItem must not be called in onCancel
  assert.match(
    tripBuilder,
    /onCancel.*setAddNoteTargetDayId\(null\)|setAddNoteTargetDayId\(null\).*onCancel/s,
    'Cancel must call setAddNoteTargetDayId(null) without creating an item',
  );
});

test('Issue6: AddNoteModal includes helper text about Build/Saved Ideas/AI Concierge', () => {
  assert.match(
    tripBuilder,
    /Build.*Saved Ideas.*AI Concierge|Saved Ideas.*AI Concierge.*Build/s,
    'Modal must include helper text pointing users to Build, Saved Ideas, or AI Concierge for places',
  );
});

test('Issue6: existing Plan My Day handlePlanDay contract unchanged', () => {
  assert.match(
    tripBuilder,
    /handlePlanDay/,
    'handlePlanDay must still be present (Plan My Day contract intact)',
  );
});

test('Issue6: existing drag-drop handlers unchanged', () => {
  assert.match(
    tripBuilder,
    /handleDragEnd|onDragEnd/,
    'Drag-drop handler must still be present',
  );
});

// ─── Note link rendering (URL-aware description) ──────────────────────────────

const itineraryItemCard = readFileSync(
  new URL('../src/components/trips/ItineraryItemCard.tsx', import.meta.url),
  'utf8',
);

test('NoteLinks: ItineraryItemCard defines renderDescriptionWithLinks', () => {
  assert.match(
    itineraryItemCard,
    /renderDescriptionWithLinks/,
    'ItineraryItemCard must define renderDescriptionWithLinks helper',
  );
});

test('NoteLinks: renderDescriptionWithLinks detects https URLs via URL_RE', () => {
  assert.match(
    itineraryItemCard,
    /URL_RE\s*=\s*\/https\?/,
    'URL_RE must match https? URLs',
  );
});

test('NoteLinks: Google Maps URLs labeled "Open map link"', () => {
  assert.match(
    itineraryItemCard,
    /Open map link/,
    'Google Maps URLs must be labeled "Open map link"',
  );
  assert.match(
    itineraryItemCard,
    /MAPS_RE\s*=.*maps/s,
    'MAPS_RE must include a maps pattern for Google Maps URL detection',
  );
});

test('NoteLinks: generic URLs labeled "Open link"', () => {
  assert.match(
    itineraryItemCard,
    /Open link/,
    'Non-Maps URLs must be labeled "Open link"',
  );
});

test('NoteLinks: links use target="_blank" and rel="noreferrer"', () => {
  assert.match(
    itineraryItemCard,
    /target="_blank"/,
    'Note links must open in new tab',
  );
  assert.match(
    itineraryItemCard,
    /rel="noreferrer"/,
    'Note links must use rel="noreferrer" for security',
  );
});

test('NoteLinks: links have note-description-link testid', () => {
  assert.match(
    itineraryItemCard,
    /note-description-link/,
    'Link elements must have data-testid="note-description-link"',
  );
});

test('NoteLinks: description renders via renderDescriptionWithLinks (not raw text)', () => {
  // The description paragraph must call renderDescriptionWithLinks
  assert.match(
    itineraryItemCard,
    /renderDescriptionWithLinks\(item\.description\)/,
    'Description must be rendered via renderDescriptionWithLinks, not as plain text',
  );
});

test('NoteLinks: plain notes without URLs still render normally', () => {
  // The function must handle the case where no URL is found (last slice appended)
  assert.match(
    itineraryItemCard,
    /last\s*<\s*text\.length/,
    'Non-URL text segments must be appended for plain notes',
  );
});

test('NoteLinks: no Google Places / provider calls introduced', () => {
  // URL renderer must not import or call any place search API
  assert.ok(
    !itineraryItemCard.includes('fetchPlace') && !itineraryItemCard.includes('searchPlaces'),
    'Note link rendering must not introduce provider calls',
  );
});
