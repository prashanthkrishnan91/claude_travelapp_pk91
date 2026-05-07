import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  ACTION,
  parseRefinementAction,
  applyRefinementToMessage,
  buildContextualSearchQuery,
  compareCards,
  selectBestCard,
  looksLikeFreshSearch,
} from '../src/lib/concierge/refinementInterpreter.js';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makePlace(name, overrides = {}) {
  return {
    type: 'verified_place',
    name,
    cuisine: overrides.cuisine ?? 'Restaurant',
    rating: overrides.rating ?? 4.5,
    reviewCount: overrides.reviewCount ?? 500,
    neighborhood: overrides.neighborhood ?? 'River North',
    tags: overrides.tags ?? [],
    display: {
      displayCategory: overrides.displayCategory ?? overrides.cuisine ?? 'Restaurant',
      displayWhy: overrides.displayWhy ?? `${name} is a solid pick.`,
      displayWhyValidated: overrides.displayWhyValidated !== false,
    },
    googleVerification: { businessStatus: 'OPERATIONAL', confidence: 'high', providerPlaceId: 'abc123' },
    ...overrides,
  };
}

function makeMsg(overrides = {}) {
  return {
    role: 'assistant',
    text: 'Here are your options.',
    restaurants: overrides.restaurants ?? [
      makePlace('Sushi Nami', { cuisine: 'Sushi', rating: 4.8, reviewCount: 1200 }),
      makePlace('La Paloma', { cuisine: 'Mexican', rating: 4.5, reviewCount: 800 }),
      makePlace('Trattoria Milano', { cuisine: 'Italian', rating: 4.3, reviewCount: 600 }),
    ],
    attractions: overrides.attractions ?? [],
    hotels: overrides.hotels ?? [],
    researchSources: [],
    areaComparisons: [],
  };
}

const THREE_CARDS = [
  makePlace('Sushi Nami', { cuisine: 'Sushi', rating: 4.8, reviewCount: 1200 }),
  makePlace('La Paloma', { cuisine: 'Mexican', rating: 4.5, reviewCount: 800 }),
  makePlace('Trattoria Milano', { cuisine: 'Italian', rating: 4.3, reviewCount: 600 }),
];

// ---------------------------------------------------------------------------
// parseRefinementAction — action type routing
// ---------------------------------------------------------------------------

test('parseRefinementAction: compare top 2 → COMPARE_CURRENT_SET', () => {
  const action = parseRefinementAction('compare the first two', THREE_CARDS);
  assert.equal(action.type, ACTION.COMPARE_CURRENT_SET);
});

test('parseRefinementAction: compare them → COMPARE_CURRENT_SET', () => {
  const action = parseRefinementAction('compare them', THREE_CARDS);
  assert.equal(action.type, ACTION.COMPARE_CURRENT_SET);
});

test('parseRefinementAction: which is better → COMPARE_CURRENT_SET', () => {
  const action = parseRefinementAction('which is better', THREE_CARDS);
  assert.equal(action.type, ACTION.COMPARE_CURRENT_SET);
});

test('parseRefinementAction: show only casual → FILTER_CURRENT_SET with modifier', () => {
  const action = parseRefinementAction('show only casual', THREE_CARDS);
  assert.equal(action.type, ACTION.FILTER_CURRENT_SET);
  assert.ok(action.modifier, 'modifier should be set');
  assert.match(action.modifier, /casual/i);
});

test('parseRefinementAction: filter to cheap options → FILTER_CURRENT_SET', () => {
  const action = parseRefinementAction('filter to cheap options', THREE_CARDS);
  assert.equal(action.type, ACTION.FILTER_CURRENT_SET);
});

test('parseRefinementAction: remove sushi places → REMOVE_FROM_CURRENT_SET with modifier', () => {
  const action = parseRefinementAction('remove sushi places', THREE_CARDS);
  assert.equal(action.type, ACTION.REMOVE_FROM_CURRENT_SET);
  assert.match(action.modifier, /sushi/i);
});

test('parseRefinementAction: get rid of Italian → REMOVE_FROM_CURRENT_SET', () => {
  const action = parseRefinementAction('get rid of Italian restaurants', THREE_CARDS);
  assert.equal(action.type, ACTION.REMOVE_FROM_CURRENT_SET);
  assert.match(action.modifier, /italian/i);
});

test('parseRefinementAction: which one is best → RERANK_CURRENT_SET', () => {
  const action = parseRefinementAction('which one is best', THREE_CARDS);
  assert.equal(action.type, ACTION.RERANK_CURRENT_SET);
});

test('parseRefinementAction: best for a romantic dinner → RERANK_CURRENT_SET', () => {
  const action = parseRefinementAction('best for a romantic dinner', THREE_CARDS);
  assert.equal(action.type, ACTION.RERANK_CURRENT_SET);
});

test('parseRefinementAction: which is best after dinner → RERANK_CURRENT_SET with isTemporal', () => {
  const action = parseRefinementAction('which one is best after dinner', THREE_CARDS);
  assert.equal(action.type, ACTION.RERANK_CURRENT_SET);
  assert.equal(action.isTemporal, true);
});

test('parseRefinementAction: show only late-night → RERANK_CURRENT_SET with isTemporal', () => {
  // "late-night" triggers the temporal modifier check
  const action = parseRefinementAction('which one is best for late-night', THREE_CARDS);
  assert.equal(action.type, ACTION.RERANK_CURRENT_SET);
  assert.equal(action.isTemporal, true);
});

test('parseRefinementAction: add the best one to Day 1 → ADD_SELECTED_TO_DAY with dayNumber', () => {
  const action = parseRefinementAction('add the best one to Day 1', THREE_CARDS);
  assert.equal(action.type, ACTION.ADD_SELECTED_TO_DAY);
  assert.equal(action.dayNumber, 1);
});

test('parseRefinementAction: add the top one to my trip → ADD_SELECTED_TO_DAY', () => {
  const action = parseRefinementAction('add the top one to my trip', THREE_CARDS);
  assert.equal(action.type, ACTION.ADD_SELECTED_TO_DAY);
});

test('parseRefinementAction: find cheaper nearby → SEARCH_MORE_WITH_CONTEXT', () => {
  const action = parseRefinementAction('find cheaper nearby', THREE_CARDS);
  assert.equal(action.type, ACTION.SEARCH_MORE_WITH_CONTEXT);
});

test('parseRefinementAction: more options → SEARCH_MORE_WITH_CONTEXT', () => {
  const action = parseRefinementAction('show me more options', THREE_CARDS);
  assert.equal(action.type, ACTION.SEARCH_MORE_WITH_CONTEXT);
});

test('parseRefinementAction: alternatives → SEARCH_MORE_WITH_CONTEXT', () => {
  const action = parseRefinementAction('find alternatives', THREE_CARDS);
  assert.equal(action.type, ACTION.SEARCH_MORE_WITH_CONTEXT);
});

test('parseRefinementAction: empty message → CLARIFY_UNSUPPORTED', () => {
  const action = parseRefinementAction('', THREE_CARDS);
  assert.equal(action.type, ACTION.CLARIFY_UNSUPPORTED);
});

test('parseRefinementAction: no cards → SEARCH_MORE_WITH_CONTEXT', () => {
  const action = parseRefinementAction('show only casual', []);
  assert.equal(action.type, ACTION.SEARCH_MORE_WITH_CONTEXT);
});

// ---------------------------------------------------------------------------
// applyRefinementToMessage — FILTER
// ---------------------------------------------------------------------------

test('FILTER: matches visible field (cuisine) → filtered card set returned', () => {
  const msg = makeMsg();
  const action = { type: ACTION.FILTER_CURRENT_SET, modifier: 'sushi' };
  const result = applyRefinementToMessage(action, msg);
  assert.ok(result, 'should return a synthetic message');
  assert.equal(result.restaurants.length, 1);
  assert.equal(result.restaurants[0].name, 'Sushi Nami');
  assert.match(result.text, /Filtered to 1 pick/);
  assert.equal(result.isRefinement, true);
  assert.equal(result.refinementAction, ACTION.FILTER_CURRENT_SET);
});

test('FILTER: no matching cards → returns null (caller falls to SEARCH_MORE)', () => {
  const msg = makeMsg();
  const action = { type: ACTION.FILTER_CURRENT_SET, modifier: 'vegan' };
  const result = applyRefinementToMessage(action, msg);
  assert.equal(result, null);
});

test('FILTER: filtered result has same verified card structure (no new cards minted)', () => {
  const msg = makeMsg();
  const action = { type: ACTION.FILTER_CURRENT_SET, modifier: 'italian' };
  const result = applyRefinementToMessage(action, msg);
  assert.ok(result);
  assert.equal(result.restaurants.length, 1);
  // The returned card is the same object — not a newly minted card
  assert.equal(result.restaurants[0].name, 'Trattoria Milano');
  assert.equal(result.restaurants[0].type, 'verified_place');
  assert.equal(result.restaurants[0].googleVerification.businessStatus, 'OPERATIONAL');
});

test('FILTER: response text indicates count', () => {
  const msg = makeMsg({
    restaurants: [
      makePlace('A', { cuisine: 'Mexican' }),
      makePlace('B', { cuisine: 'Mexican' }),
      makePlace('C', { cuisine: 'Italian' }),
    ],
  });
  const result = applyRefinementToMessage({ type: ACTION.FILTER_CURRENT_SET, modifier: 'mexican' }, msg);
  assert.ok(result);
  assert.match(result.text, /2 picks/i);
});

// ---------------------------------------------------------------------------
// applyRefinementToMessage — REMOVE
// ---------------------------------------------------------------------------

test('REMOVE: removes matching cards, keeps rest', () => {
  const msg = makeMsg();
  const result = applyRefinementToMessage({ type: ACTION.REMOVE_FROM_CURRENT_SET, modifier: 'sushi' }, msg);
  assert.ok(result);
  assert.equal(result.restaurants.length, 2);
  assert.ok(!result.restaurants.find((r) => r.name === 'Sushi Nami'));
  assert.match(result.text, /Removed 1 card/i);
});

test('REMOVE: no match → message says no match, all cards preserved', () => {
  const msg = makeMsg();
  const result = applyRefinementToMessage({ type: ACTION.REMOVE_FROM_CURRENT_SET, modifier: 'thai' }, msg);
  assert.ok(result);
  assert.equal(result.restaurants.length, 3);
  assert.match(result.text, /No cards matching/i);
});

test('REMOVE: remaining count in response text', () => {
  const msg = makeMsg();
  const result = applyRefinementToMessage({ type: ACTION.REMOVE_FROM_CURRENT_SET, modifier: 'italian' }, msg);
  assert.ok(result);
  assert.match(result.text, /2 picks remaining/i);
});

test('REMOVE: returned cards are same verified objects (not re-minted)', () => {
  const msg = makeMsg();
  const result = applyRefinementToMessage({ type: ACTION.REMOVE_FROM_CURRENT_SET, modifier: 'italian' }, msg);
  assert.ok(result);
  const names = result.restaurants.map((r) => r.name);
  assert.ok(names.includes('Sushi Nami'));
  assert.ok(names.includes('La Paloma'));
  assert.ok(!names.includes('Trattoria Milano'));
});

// ---------------------------------------------------------------------------
// applyRefinementToMessage — RERANK
// ---------------------------------------------------------------------------

test('RERANK: returns cards sorted by rating desc', () => {
  const msg = makeMsg();
  const result = applyRefinementToMessage({ type: ACTION.RERANK_CURRENT_SET, modifier: 'best pick' }, msg);
  assert.ok(result);
  assert.equal(result.restaurants[0].name, 'Sushi Nami'); // highest rating 4.8
  assert.equal(result.restaurants[1].name, 'La Paloma');   // 4.5
  assert.equal(result.restaurants[2].name, 'Trattoria Milano'); // 4.3
  assert.match(result.text, /Sushi Nami/);
});

test('RERANK: temporal modifier → ask-to-search message, empty card arrays', () => {
  const msg = makeMsg();
  const result = applyRefinementToMessage({ type: ACTION.RERANK_CURRENT_SET, modifier: 'after dinner', isTemporal: true }, msg);
  assert.ok(result);
  assert.match(result.text, /late-night|after-hours/i);
  assert.equal(result.restaurants.length, 0);
  assert.equal(result.attractions.length, 0);
  assert.equal(result.hotels.length, 0);
});

// ---------------------------------------------------------------------------
// applyRefinementToMessage — COMPARE
// ---------------------------------------------------------------------------

test('COMPARE: returns comparison data for first two cards', () => {
  const msg = makeMsg();
  const result = applyRefinementToMessage({ type: ACTION.COMPARE_CURRENT_SET }, msg);
  assert.ok(result);
  assert.equal(result.refinementAction, ACTION.COMPARE_CURRENT_SET);
  assert.ok(result.refinementComparison, 'comparison data should be present');
  assert.equal(result.refinementComparison.length, 2);
  assert.equal(result.refinementComparison[0].name, 'Sushi Nami');
  assert.equal(result.refinementComparison[1].name, 'La Paloma');
});

test('COMPARE: comparison cards include visible fields only', () => {
  const msg = makeMsg();
  const result = applyRefinementToMessage({ type: ACTION.COMPARE_CURRENT_SET }, msg);
  const card = result.refinementComparison[0];
  assert.ok('name' in card, 'name required');
  assert.ok('category' in card, 'category required');
  assert.ok('meta' in card, 'meta required');
  assert.ok('note' in card, 'note required');
  // No internal fields
  assert.ok(!('evidence' in card), 'evidence must not be in comparison');
  assert.ok(!('dossier' in card), 'dossier must not be in comparison');
  assert.ok(!('reviewerLabel' in card), 'reviewer labels must not be in comparison');
});

test('COMPARE: response text names both cards', () => {
  const msg = makeMsg();
  const result = applyRefinementToMessage({ type: ACTION.COMPARE_CURRENT_SET }, msg);
  assert.match(result.text, /Sushi Nami/);
  assert.match(result.text, /La Paloma/);
});

test('COMPARE: card arrays are empty (comparison is displayed separately)', () => {
  const msg = makeMsg();
  const result = applyRefinementToMessage({ type: ACTION.COMPARE_CURRENT_SET }, msg);
  assert.equal(result.restaurants.length, 0);
  assert.equal(result.attractions.length, 0);
  assert.equal(result.hotels.length, 0);
});

// ---------------------------------------------------------------------------
// compareCards helper
// ---------------------------------------------------------------------------

test('compareCards: returns text and comparisonCards for two cards', () => {
  const cards = [
    { kind: 'restaurant', place: makePlace('Alpha', { rating: 4.7, reviewCount: 900, neighborhood: 'West Loop' }) },
    { kind: 'restaurant', place: makePlace('Beta', { rating: 4.3, reviewCount: 400 }) },
  ];
  const { text, comparisonCards } = compareCards(cards);
  assert.match(text, /Alpha.*Beta|Beta.*Alpha/);
  assert.equal(comparisonCards.length, 2);
  assert.match(comparisonCards[0].meta, /4\.7/);
  assert.match(comparisonCards[0].meta, /900/);
  assert.match(comparisonCards[0].meta, /West Loop/);
});

test('compareCards: single card → graceful message', () => {
  const cards = [{ kind: 'restaurant', place: makePlace('Lonely Place') }];
  const { text, comparisonCards } = compareCards(cards);
  assert.match(text, /Only one option/);
  assert.equal(comparisonCards, null);
});

test('compareCards: empty → graceful message', () => {
  const { text, comparisonCards } = compareCards([]);
  assert.match(text, /No cards/);
  assert.equal(comparisonCards, null);
});

test('compareCards: note is truncated at 130 chars', () => {
  const longNote = 'This is a great place. '.repeat(20); // >130 chars
  const cards = [
    { kind: 'restaurant', place: makePlace('A', { displayWhy: longNote }) },
    { kind: 'restaurant', place: makePlace('B') },
  ];
  const { comparisonCards } = compareCards(cards);
  assert.ok(comparisonCards[0].note.length <= 133, 'note should be truncated with ellipsis');
});

// ---------------------------------------------------------------------------
// selectBestCard helper
// ---------------------------------------------------------------------------

test('selectBestCard: returns highest-rated card', () => {
  const cards = [
    { kind: 'restaurant', place: makePlace('Low', { rating: 3.8 }) },
    { kind: 'restaurant', place: makePlace('High', { rating: 4.9 }) },
    { kind: 'restaurant', place: makePlace('Mid', { rating: 4.5 }) },
  ];
  const best = selectBestCard(cards);
  assert.equal(best.place.name, 'High');
});

test('selectBestCard: ties broken by review count', () => {
  const cards = [
    { kind: 'restaurant', place: makePlace('FewReviews', { rating: 4.8, reviewCount: 50 }) },
    { kind: 'restaurant', place: makePlace('ManyReviews', { rating: 4.8, reviewCount: 5000 }) },
  ];
  const best = selectBestCard(cards);
  assert.equal(best.place.name, 'ManyReviews');
});

test('selectBestCard: empty → null', () => {
  assert.equal(selectBestCard([]), null);
  assert.equal(selectBestCard(null), null);
});

// ---------------------------------------------------------------------------
// buildContextualSearchQuery
// ---------------------------------------------------------------------------

test('buildContextualSearchQuery: appends modifier to original query', () => {
  const q = buildContextualSearchQuery('best restaurants in Chicago', 'find cheaper nearby', { destination: 'Chicago' });
  assert.match(q, /best restaurants in Chicago/);
  assert.match(q, /find cheaper nearby/);
});

test('buildContextualSearchQuery: message containing destination used as-is', () => {
  // When follow-up already names the destination, use follow-up as-is (don't prepend original query)
  const q = buildContextualSearchQuery('restaurants Chicago', 'late night bars in Chicago', { destination: 'Chicago' });
  assert.equal(q, 'late night bars in Chicago');
});

test('buildContextualSearchQuery: fallback to destination when no original query', () => {
  const q = buildContextualSearchQuery('', 'find cheaper options', { destination: 'Tokyo' });
  assert.match(q, /Tokyo/);
  assert.match(q, /find cheaper options/);
});

// ---------------------------------------------------------------------------
// Contract regression tests
// ---------------------------------------------------------------------------

test('FILTER: refinement result contains zero researchSources (no editorial content promoted)', () => {
  const msg = {
    ...makeMsg(),
    researchSources: [{ type: 'research_source', title: 'Top 10 sushi', sourceUrl: 'http://example.com' }],
  };
  const result = applyRefinementToMessage({ type: ACTION.FILTER_CURRENT_SET, modifier: 'sushi' }, msg);
  assert.ok(result);
  assert.equal(result.researchSources.length, 0, 'research sources must not appear in refinement results');
});

test('REMOVE: cards dropped by remove are not re-minted from non-Google sources', () => {
  const msg = makeMsg();
  // All restaurants in makeMsg() are verified_place with googleVerification
  const result = applyRefinementToMessage({ type: ACTION.REMOVE_FROM_CURRENT_SET, modifier: 'sushi' }, msg);
  for (const r of result.restaurants) {
    assert.equal(r.type, 'verified_place', 'remaining cards must still be verified_place');
    assert.ok(r.googleVerification, 'remaining cards must retain googleVerification');
  }
});

test('RERANK: sorted cards retain original googleVerification objects', () => {
  const msg = makeMsg();
  const result = applyRefinementToMessage({ type: ACTION.RERANK_CURRENT_SET, modifier: 'best' }, msg);
  for (const r of result.restaurants) {
    assert.ok(r.googleVerification, 'sorted cards must retain googleVerification');
  }
});

test('COMPARE: no internal metadata exposed in comparison cards', () => {
  const place = {
    ...makePlace('Secret'),
    _dossier: 'internal dossier data',
    _evidence_count: 5,
    _reviewer_label: 'evidence_rich',
  };
  const cards = [
    { kind: 'restaurant', place },
    { kind: 'restaurant', place: makePlace('Other') },
  ];
  const { comparisonCards } = compareCards(cards);
  const keys = Object.keys(comparisonCards[0]);
  assert.ok(!keys.includes('_dossier'), 'dossier must not be in comparison');
  assert.ok(!keys.includes('_evidence_count'), 'evidence count must not be in comparison');
  assert.ok(!keys.includes('_reviewer_label'), 'reviewer label must not be in comparison');
});

test('invalid refinement action does not drop all cards unexpectedly', () => {
  const msg = makeMsg();
  // CLARIFY_UNSUPPORTED type → applyRefinementToMessage returns null (not an empty-card result)
  const result = applyRefinementToMessage({ type: ACTION.CLARIFY_UNSUPPORTED }, msg);
  assert.equal(result, null, 'CLARIFY_UNSUPPORTED must return null — caller handles it');
});

test('chips and typed follow-ups use the same action constants', () => {
  // Verify that the chip texts route to the expected action types
  const chipMappings = [
    ['Show only casual', ACTION.FILTER_CURRENT_SET],
    ['Compare top 2', ACTION.COMPARE_CURRENT_SET],
    ['Find cheaper nearby', ACTION.SEARCH_MORE_WITH_CONTEXT],
    ['Add best to Day 1', ACTION.ADD_SELECTED_TO_DAY],
  ];
  for (const [chip, expectedAction] of chipMappings) {
    const action = parseRefinementAction(chip, THREE_CARDS);
    assert.equal(action.type, expectedAction, `Chip "${chip}" should route to ${expectedAction}, got ${action.type}`);
  }
});

// ---------------------------------------------------------------------------
// AIConciergePanel structural contract tests
// ---------------------------------------------------------------------------

const aiConciergePanel = readFileSync(
  new URL('../src/components/trips/AIConciergePanel.tsx', import.meta.url),
  'utf8'
);

test('AIConciergePanel imports refinementInterpreter', () => {
  assert.match(aiConciergePanel, /refinementInterpreter/);
  assert.match(aiConciergePanel, /parseRefinementAction/);
  assert.match(aiConciergePanel, /applyRefinementToMessage/);
});

test('AIConciergePanel: handleUserInput routes through refinement when cards present', () => {
  assert.match(aiConciergePanel, /handleUserInput/);
  assert.match(aiConciergePanel, /getLatestCardMessage/);
  assert.match(aiConciergePanel, /handleRefinement/);
});

test('AIConciergePanel: refinement chips use same handleUserInput handler', () => {
  assert.match(aiConciergePanel, /refinementChips/);
  assert.match(aiConciergePanel, /handleUserInput\(prompt\)/);
});

test('AIConciergePanel: comparison rendering uses refinementComparison', () => {
  assert.match(aiConciergePanel, /refinementComparison/);
  assert.match(aiConciergePanel, /COMPARE_CURRENT_SET/);
});

test('AIConciergePanel: ADD_SELECTED_TO_DAY uses existing addItem flow', () => {
  assert.match(aiConciergePanel, /addItem\(best\.place\.name/);
  assert.match(aiConciergePanel, /ADD_SELECTED_TO_DAY/);
});

test('AIConciergePanel: SEARCH_MORE routes through callConciergeSearch', () => {
  assert.match(aiConciergePanel, /callConciergeSearch/);
  assert.match(aiConciergePanel, /buildContextualSearchQuery/);
});

test('AIConciergePanel: no fallback note or deterministic note fields exposed via refinement', () => {
  // Refinement messages must not carry fallback_note_visible_count or deterministic_visible_count
  assert.doesNotMatch(aiConciergePanel, /fallback_note_visible_count.*refinement/s);
  assert.doesNotMatch(aiConciergePanel, /deterministic_visible_count.*refinement/s);
});

// ---------------------------------------------------------------------------
// Blocker 1 — addItem targetDayId (async state safety)
// ---------------------------------------------------------------------------

test('looksLikeFreshSearch: destination-qualified queries return true', () => {
  assert.equal(looksLikeFreshSearch('Best restaurants in Tokyo'), true);
  assert.equal(looksLikeFreshSearch('Hotels near Paris'), true);
  assert.equal(looksLikeFreshSearch('Things to do around Osaka'), true);
  assert.equal(looksLikeFreshSearch('Cocktail bars in River North'), true);
});

test('looksLikeFreshSearch: "for Day N" pattern returns true', () => {
  assert.equal(looksLikeFreshSearch('Attractions for Day 2'), true);
  assert.equal(looksLikeFreshSearch('dinner for day 3'), true);
});

test('looksLikeFreshSearch: "compare neighborhoods/areas" returns true', () => {
  assert.equal(looksLikeFreshSearch('compare neighborhoods'), true);
  assert.equal(looksLikeFreshSearch('Compare areas'), true);
  assert.equal(looksLikeFreshSearch('compare districts'), true);
});

test('looksLikeFreshSearch: refinement commands return false', () => {
  assert.equal(looksLikeFreshSearch('Show only 4 star and above'), false);
  assert.equal(looksLikeFreshSearch('Remove the first one'), false);
  assert.equal(looksLikeFreshSearch('Sort by rating'), false);
  assert.equal(looksLikeFreshSearch('Compare them'), false);
  assert.equal(looksLikeFreshSearch('Add best to Day 2'), false);
  assert.equal(looksLikeFreshSearch('find more options'), false);
  assert.equal(looksLikeFreshSearch(''), false);
  assert.equal(looksLikeFreshSearch(null), false);
});

test('AIConciergePanel: addItem accepts targetDayId parameter', () => {
  // addItem must accept an explicit targetDayId so ADD_SELECTED_TO_DAY
  // does not rely on async selectedDayId state.
  assert.match(aiConciergePanel, /targetDayId\?:\s*string/);
  assert.match(aiConciergePanel, /effectiveDayId\s*=\s*targetDayId\s*\?\?\s*selectedDayId/);
});

test('AIConciergePanel: ADD_SELECTED_TO_DAY passes resolvedDayId to addItem, no setSelectedDayId', () => {
  // The branch must synchronously resolve the day and pass it to addItem
  // rather than calling setSelectedDayId and then reading async state.
  assert.match(aiConciergePanel, /resolvedDayId/);
  assert.match(aiConciergePanel, /addItem\(best\.place\.name,\s*best\.kind,\s*best\.place,\s*sanitized,\s*resolvedDayId\)/);
  // setSelectedDayId must not be called in the ADD_SELECTED_TO_DAY code path
  // (the only safe pattern is to pass the day id directly into addItem).
  assert.doesNotMatch(aiConciergePanel, /ADD_SELECTED_TO_DAY[\s\S]{0,400}setSelectedDayId\(dayId\)/);
});

test('AIConciergePanel: effectiveDayId is used throughout addItem, not selectedDayId directly', () => {
  assert.match(aiConciergePanel, /effectiveDayId/);
  // cardKey should use effectiveDayId inside addItem body
  assert.match(aiConciergePanel, /cardKey\(name,\s*effectiveDayId/);
});

// ---------------------------------------------------------------------------
// Blocker 2 — fresh-search pass-through after cards exist
// ---------------------------------------------------------------------------

test('AIConciergePanel: looksLikeFreshSearch is imported', () => {
  assert.match(aiConciergePanel, /looksLikeFreshSearch/);
});

test('AIConciergePanel: handleUserInput guards with looksLikeFreshSearch before routing to refinement', () => {
  // handleUserInput must bail out of the refinement path when query looks like a fresh search
  assert.match(aiConciergePanel, /looksLikeFreshSearch\(q\)/);
  assert.match(aiConciergePanel, /!looksLikeFreshSearch\(q\)/);
});

test('AIConciergePanel: handleRefinement returns false for CLARIFY_UNSUPPORTED', () => {
  // When refinement cannot handle the action it must signal the caller via false
  // so the caller can fall through to sendQuery without showing a confusing message.
  assert.match(aiConciergePanel, /CLARIFY_UNSUPPORTED/);
  assert.match(aiConciergePanel, /return false/);
});

test('AIConciergePanel: handleRefinement returns Promise<boolean>', () => {
  // The return type must be Promise<boolean> so handleUserInput can await it.
  assert.match(aiConciergePanel, /Promise<boolean>/);
});

test('AIConciergePanel: followUpActions chips call sendQuery directly, not handleUserInput', () => {
  // followUpActions are fresh-search prompts; they must bypass the refinement guard.
  assert.match(aiConciergePanel, /followUpActions/);
  // When refinementChips is false (followUpActions chip), onClick uses sendQuery.
  assert.match(aiConciergePanel, /refinementChips\s*\?\s*handleUserInput\(prompt\)\s*:\s*sendQuery\(prompt\)/);
});
