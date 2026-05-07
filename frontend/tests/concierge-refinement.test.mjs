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
  dedupeCardsAgainstCurrentSet,
  hasGooglePriceSignals,
  getBaselinePriceLevel,
} from '../src/lib/concierge/refinementInterpreter.js';
import { formatDisplayPrice } from '../src/lib/concierge/priceFormatter.js';

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
  assert.ok('rating' in card, 'rating required');
  assert.ok('price' in card, 'price required');
  assert.ok('area' in card, 'area required');
  assert.ok('bestFor' in card, 'bestFor required');
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

test('COMPARE: card arrays contain top 2 canonical cards for action-capable rendering', () => {
  // Fix A: top 2 original cards returned so ConciergeCard renders them with
  // Add to Day, Save, map/source links, and Google verified badge.
  const msg = makeMsg(); // 3 restaurants: Sushi Nami, La Paloma, Trattoria Milano
  const result = applyRefinementToMessage({ type: ACTION.COMPARE_CURRENT_SET }, msg);
  assert.equal(result.restaurants.length, 2, 'top 2 canonical cards must be in restaurants array');
  assert.equal(result.restaurants[0].name, 'Sushi Nami');
  assert.equal(result.restaurants[1].name, 'La Paloma');
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
  // New structured shape: rating string and area string
  assert.match(comparisonCards[0].rating, /4\.7/);
  assert.match(comparisonCards[0].rating, /900/);
  assert.equal(comparisonCards[0].area, 'West Loop');
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

test('compareCards: bestFor is trimmed at word boundary to avoid mid-word truncation', () => {
  const longWhy = 'This is a great place for casual dining and special occasions. '.repeat(5); // >90 chars
  const cards = [
    { kind: 'restaurant', place: makePlace('A', { displayWhy: longWhy }) },
    { kind: 'restaurant', place: makePlace('B') },
  ];
  const { comparisonCards } = compareCards(cards);
  const bf = comparisonCards[0].bestFor ?? '';
  assert.ok(bf.length <= 93, `bestFor should be ≤93 chars (90 + ellipsis), got ${bf.length}`);
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

// ---------------------------------------------------------------------------
// False success message fix — addItem returns boolean; ADD_SELECTED_TO_DAY gates on it
// ---------------------------------------------------------------------------

test('AIConciergePanel: addItem return type is Promise<boolean>', () => {
  // addItem must declare a boolean return type so TypeScript enforces all paths return a value.
  assert.match(aiConciergePanel, /\): Promise<boolean> \{/);
});

test('AIConciergePanel: addItem returns false when no effectiveDayId', () => {
  assert.match(aiConciergePanel, /return false;\s*\n\s*\}/);
  // The no-day path explicitly returns false (not void/undefined).
  assert.match(aiConciergePanel, /setError\("Select a day before adding this item\."\);\s*\n\s*return false/);
});

test('AIConciergePanel: addItem returns true for duplicate', () => {
  // Duplicate detection is treated as success (item already on day).
  assert.match(aiConciergePanel, /setAddedItems\(.*new Set.*\);\s*\n\s*return true/s);
});

test('AIConciergePanel: addItem tracks success with local flag and returns it', () => {
  // success flag is set to true only after the API call completes without throwing.
  assert.match(aiConciergePanel, /let success = false/);
  assert.match(aiConciergePanel, /success = true/);
  assert.match(aiConciergePanel, /return success/);
});

test('AIConciergePanel: ADD_SELECTED_TO_DAY awaits boolean result from addItem', () => {
  // The branch must use the return value — not just fire-and-forget.
  assert.match(aiConciergePanel, /const didAdd = await addItem\(best\.place\.name/);
});

test('AIConciergePanel: ADD_SELECTED_TO_DAY success message gated on didAdd', () => {
  // "Added..." text must only appear when didAdd is truthy.
  assert.match(aiConciergePanel, /didAdd/);
  assert.match(aiConciergePanel, /Added.*to.*dayLabel/s);
  // Failure path must produce a distinct message — not the success text.
  assert.match(aiConciergePanel, /I couldn't add.*Please try again/);
});

test('AIConciergePanel: ADD_SELECTED_TO_DAY cannot emit "Added" when addItem fails', () => {
  // The text "Added" must always be conditional on didAdd, never unconditional.
  // Confirm the ternary structure: didAdd ? `Added...` : `I couldn't add...`
  assert.match(aiConciergePanel, /didAdd\s*\?\s*`Added/);
  assert.doesNotMatch(aiConciergePanel, /text:\s*`Added\s/);
});

// ---------------------------------------------------------------------------
// Fix A — Compare top 2 returns canonical cards for action-capable rendering
// ---------------------------------------------------------------------------

test('COMPARE: top 2 canonical cards are present in result for ConciergeCard rendering', () => {
  // The top 2 cards must be in restaurants/attractions/hotels so the existing
  // ConciergeCard renderer shows Add to Day, Save, map/source links, and badge.
  const msg = makeMsg();
  const result = applyRefinementToMessage({ type: ACTION.COMPARE_CURRENT_SET }, msg);
  assert.ok(result.restaurants.length >= 2, 'at least 2 canonical cards required for compare');
  // Canonical card objects retain googleVerification for addability
  for (const r of result.restaurants) {
    assert.ok(r.googleVerification, 'compare cards must retain googleVerification');
    assert.equal(r.type, 'verified_place', 'compare cards must remain verified_place');
  }
});

test('COMPARE: refinementComparison summary data still present alongside canonical cards', () => {
  // Both the text comparison summary AND the canonical cards must be in the result.
  const msg = makeMsg();
  const result = applyRefinementToMessage({ type: ACTION.COMPARE_CURRENT_SET }, msg);
  assert.ok(result.refinementComparison, 'comparison summary required');
  assert.equal(result.refinementComparison.length, 2, 'summary must cover top 2 cards');
  // Canonical cards are also present
  assert.ok(result.restaurants.length > 0, 'canonical cards must be non-empty');
});

test('AIConciergePanel: compare rendering uses text-based block, not card-shaped tiles', () => {
  // The comparison block must not use rounded-2xl with border on individual card divs
  // (which would look like place cards without actions). Instead it uses a plain text layout.
  assert.match(aiConciergePanel, /Quick comparison/);
  // The comparison block should not contain individual rounded-2xl card borders per item
  assert.doesNotMatch(
    aiConciergePanel,
    /refinementComparison\.map\([\s\S]{0,300}rounded-2xl border border-slate-700\/60/,
  );
});

// ---------------------------------------------------------------------------
// Fix B/D — dedupeCardsAgainstCurrentSet
// ---------------------------------------------------------------------------

test('dedupeCardsAgainstCurrentSet: de-dupes by Google place ID', () => {
  const current = [makePlace('Sushi Nami', { reviewCount: 1200 })];
  // current[0] has providerPlaceId: 'abc123' from makePlace fixture
  const newMsg = {
    restaurants: [makePlace('Sushi Nami', { reviewCount: 1200 })], // same place ID
    attractions: [],
    hotels: [],
  };
  const result = dedupeCardsAgainstCurrentSet(newMsg, current);
  assert.equal(result.restaurants.length, 0, 'duplicate by place ID must be removed');
  assert.equal(result.allDuplicates, true);
});

test('dedupeCardsAgainstCurrentSet: de-dupes by normalized name+address when no place ID', () => {
  const current = [{ name: 'Bar X', neighborhood: 'West Loop' }]; // no googleVerification
  const newMsg = {
    restaurants: [{ name: 'Bar X', neighborhood: 'West Loop' }], // same name+addr
    attractions: [],
    hotels: [],
  };
  const result = dedupeCardsAgainstCurrentSet(newMsg, current);
  assert.equal(result.restaurants.length, 0, 'duplicate by name+address must be removed');
  assert.equal(result.allDuplicates, true);
});

test('dedupeCardsAgainstCurrentSet: preserves cards not in current set', () => {
  const current = [makePlace('Sushi Nami')];
  const newMsg = {
    restaurants: [
      makePlace('Sushi Nami'),   // duplicate
      makePlace('La Paloma'),    // new — different providerPlaceId? No — makePlace always uses abc123
    ],
    attractions: [],
    hotels: [],
  };
  // Both have same providerPlaceId ('abc123') from makePlace, so both dedupe.
  // Use a card with a unique place ID instead.
  const unique = { name: 'New Bar', googleVerification: { providerPlaceId: 'xyz999', businessStatus: 'OPERATIONAL', confidence: 'high' } };
  const newMsg2 = {
    restaurants: [makePlace('Sushi Nami'), unique],
    attractions: [],
    hotels: [],
  };
  const result = dedupeCardsAgainstCurrentSet(newMsg2, current);
  assert.equal(result.restaurants.length, 1, 'non-duplicate must survive');
  assert.equal(result.restaurants[0].name, 'New Bar');
  assert.equal(result.allDuplicates, false);
});

test('dedupeCardsAgainstCurrentSet: allDuplicates false when no new cards had matches', () => {
  const current = [makePlace('Old Place', { reviewCount: 100 })];
  const newMsg = {
    restaurants: [{ name: 'Brand New', googleVerification: { providerPlaceId: 'zzz001', businessStatus: 'OPERATIONAL', confidence: 'high' } }],
    attractions: [],
    hotels: [],
  };
  const result = dedupeCardsAgainstCurrentSet(newMsg, current);
  assert.equal(result.allDuplicates, false);
  assert.equal(result.restaurants.length, 1);
});

test('dedupeCardsAgainstCurrentSet: empty currentCards returns all new cards unchanged', () => {
  const newMsg = { restaurants: [makePlace('A'), makePlace('B')], attractions: [], hotels: [] };
  const result = dedupeCardsAgainstCurrentSet(newMsg, []);
  assert.equal(result.restaurants.length, 2, 'all cards preserved when no current set');
  assert.equal(result.allDuplicates, false);
});

// ---------------------------------------------------------------------------
// Fix C (updated) — value-aware cheaper chip; honest when no price signals
// ---------------------------------------------------------------------------

test('AIConciergePanel: refinementChips contains "Find cheaper nearby"', () => {
  // The chip is restored as value-aware using Google price signals.
  assert.match(aiConciergePanel, /"Find cheaper nearby"/);
});

test('AIConciergePanel: refinementChips contains "Find more like these" as no-price-signal fallback', () => {
  // "Find more like these" is the honest fallback chip when cards have no Google price signals.
  assert.match(aiConciergePanel, /"Find more like these"/);
});

test('AIConciergePanel: cheaper guard uses isCheaperQuery regex covering cheaper/budget/affordable', () => {
  assert.match(aiConciergePanel, /isCheaperQuery/);
  assert.match(aiConciergePanel, /cheap\(er\)\?.*budget.*affordable/s);
});

test('AIConciergePanel: no-price-signal path shows honest message without claiming cheaper', () => {
  // Honest message when currentVisibleCards have no Google price signals.
  assert.match(aiConciergePanel, /Google price signals/);
});

test('AIConciergePanel: imports hasGooglePriceSignals from refinementInterpreter', () => {
  assert.match(aiConciergePanel, /hasGooglePriceSignals/);
});

// ---------------------------------------------------------------------------
// Fix D — de-dupe applied in SEARCH_MORE; honest message for all-duplicates
// ---------------------------------------------------------------------------

test('AIConciergePanel: imports dedupeCardsAgainstCurrentSet from refinementInterpreter', () => {
  assert.match(aiConciergePanel, /dedupeCardsAgainstCurrentSet/);
});

test('AIConciergePanel: SEARCH_MORE applies de-dupe before rendering results', () => {
  assert.match(aiConciergePanel, /dedupeCardsAgainstCurrentSet\(fromSearchResult\(result\)/);
});

test('AIConciergePanel: all-duplicate SEARCH_MORE shows honest "mostly found the same" message', () => {
  assert.match(aiConciergePanel, /mostly found the same top options/);
  assert.match(aiConciergePanel, /allDuplicates/);
});

// ---------------------------------------------------------------------------
// Fix G — existing card actions preserved after refinement (structural)
// ---------------------------------------------------------------------------

test('AIConciergePanel: ConciergeCard renders Add to Day, Save, map link, Google verified badge', () => {
  assert.match(aiConciergePanel, /Add to Day/);
  assert.match(aiConciergePanel, /Save to trip ideas/);
  assert.match(aiConciergePanel, /Google verified/);
  assert.match(aiConciergePanel, /MapPin/);
});

test('AIConciergePanel: canonical cards still rendered after refinement via isRenderableVerifiedPlace filter', () => {
  // The card renderer block uses isRenderableVerifiedPlace to filter — ensuring
  // only addable verified cards are shown.
  assert.match(aiConciergePanel, /isRenderableVerifiedPlace/);
  assert.match(aiConciergePanel, /addablePlaces/);
});

// ---------------------------------------------------------------------------
// Fix H — concierge note fields preserved when present; missing notes allowed
// ---------------------------------------------------------------------------

test('AIConciergePanel: pickCardDetail reads conciergeNote from supportingDetails', () => {
  // Note fields must be read from canonical card objects and passed to ConciergeCard.
  assert.match(aiConciergePanel, /pickCardDetail/);
  assert.match(aiConciergePanel, /conciergeNote/);
});

test('AIConciergePanel: missing concierge notes are allowed — pickCardDetail returns empty array', () => {
  // pickCardDetail must return an empty array (not throw) when no note is present.
  assert.match(aiConciergePanel, /return note \? \[note\] : \[\]/);
});

// ---------------------------------------------------------------------------
// Fix J — no internal labels exposed in rendered UI (structural)
// ---------------------------------------------------------------------------

test('AIConciergePanel: refinementAction values are not rendered as visible UI text', () => {
  // Internal refinementAction constants must be used only as data/conditions,
  // never rendered as visible JSX text content (e.g., not {msg.refinementAction}).
  assert.doesNotMatch(aiConciergePanel, /\{msg\.refinementAction\}/);
  // The comparison block label must be a user-visible label, not an internal class name
  assert.match(aiConciergePanel, /Quick comparison/);
  assert.doesNotMatch(aiConciergePanel, />COMPARE_CURRENT_SET</);
  assert.doesNotMatch(aiConciergePanel, />FILTER_CURRENT_SET</);
});

test('AIConciergePanel: no fallback_note_visible_count or deterministic_visible_count in JSX render', () => {
  assert.doesNotMatch(aiConciergePanel, /fallback_note_visible_count/);
  assert.doesNotMatch(aiConciergePanel, /deterministic_visible_count/);
});

// ---------------------------------------------------------------------------
// Fix I — mobile chip/input layout (structural)
// ---------------------------------------------------------------------------

test('AIConciergePanel: chip container uses overflow-x-auto to prevent cramping on narrow screens', () => {
  assert.match(aiConciergePanel, /overflow-x-auto/);
});

test('AIConciergePanel: chip buttons use shrink-0 to prevent compression and py-1.5 for tap target', () => {
  assert.match(aiConciergePanel, /shrink-0/);
  assert.match(aiConciergePanel, /py-1\.5/);
});

// ---------------------------------------------------------------------------
// Price signals — priceFormatter unit tests
// ---------------------------------------------------------------------------

test('priceFormatter: formatDisplayPrice returns $$ for PRICE_LEVEL_MODERATE', () => {
  assert.equal(formatDisplayPrice('PRICE_LEVEL_MODERATE', null), '$$');
});

test('priceFormatter: formatDisplayPrice returns $ for PRICE_LEVEL_INEXPENSIVE', () => {
  assert.equal(formatDisplayPrice('PRICE_LEVEL_INEXPENSIVE', null), '$');
});

test('priceFormatter: formatDisplayPrice returns $$$ for PRICE_LEVEL_EXPENSIVE', () => {
  assert.equal(formatDisplayPrice('PRICE_LEVEL_EXPENSIVE', null), '$$$');
});

test('priceFormatter: formatDisplayPrice returns $$$$ for PRICE_LEVEL_VERY_EXPENSIVE', () => {
  assert.equal(formatDisplayPrice('PRICE_LEVEL_VERY_EXPENSIVE', null), '$$$$');
});

test('priceFormatter: formatDisplayPrice returns Free for PRICE_LEVEL_FREE', () => {
  assert.equal(formatDisplayPrice('PRICE_LEVEL_FREE', null), 'Free');
});

test('priceFormatter: formatDisplayPrice returns null when no data', () => {
  assert.equal(formatDisplayPrice(null, null), null);
});

test('priceFormatter: formatDisplayPrice formats priceRange compact USD', () => {
  const pr = {
    startPrice: { currencyCode: 'USD', units: '10', nanos: 0 },
    endPrice: { currencyCode: 'USD', units: '25', nanos: 0 },
  };
  assert.equal(formatDisplayPrice(null, pr), '$10–25');
});

test('priceFormatter: formatDisplayPrice priceRange beats priceLevel', () => {
  const pr = {
    startPrice: { currencyCode: 'USD', units: '15', nanos: 0 },
    endPrice: { currencyCode: 'USD', units: '30', nanos: 0 },
  };
  assert.equal(formatDisplayPrice('PRICE_LEVEL_EXPENSIVE', pr), '$15–30');
});

test('priceFormatter: formatDisplayPrice never returns raw enum name', () => {
  const result = formatDisplayPrice('PRICE_LEVEL_MODERATE', null);
  assert.ok(!result?.includes('PRICE_LEVEL'), `Expected no raw enum, got: ${result}`);
});

test('priceFormatter: formatDisplayPrice returns null for zero-unit priceRange', () => {
  const pr = {
    startPrice: { currencyCode: 'USD', units: '0', nanos: 0 },
    endPrice: { currencyCode: 'USD', units: '0', nanos: 0 },
  };
  assert.equal(formatDisplayPrice(null, pr), null);
});

// ---------------------------------------------------------------------------
// Price signals — hasGooglePriceSignals
// ---------------------------------------------------------------------------

function makePriceCard(name, priceLevel = null, displayPrice = null) {
  return {
    type: 'verified_place',
    name,
    supportingDetails: { priceLevel },
    display: { displayCategory: 'Restaurant', displayWhy: 'Good place.', displayPrice },
    googleVerification: { businessStatus: 'OPERATIONAL', confidence: 'high', providerPlaceId: 'abc' },
  };
}

test('hasGooglePriceSignals: true when at least one card has priceLevel', () => {
  const cards = [
    makePriceCard('A', 'PRICE_LEVEL_MODERATE'),
    makePriceCard('B'),
  ];
  assert.equal(hasGooglePriceSignals(cards), true);
});

test('hasGooglePriceSignals: true when at least one card has displayPrice', () => {
  const cards = [
    makePriceCard('A', null, '$$'),
    makePriceCard('B'),
  ];
  assert.equal(hasGooglePriceSignals(cards), true);
});

test('hasGooglePriceSignals: false when no cards have price signals', () => {
  const cards = [makePriceCard('A'), makePriceCard('B')];
  assert.equal(hasGooglePriceSignals(cards), false);
});

test('hasGooglePriceSignals: false on empty array', () => {
  assert.equal(hasGooglePriceSignals([]), false);
});

test('hasGooglePriceSignals: false on null', () => {
  assert.equal(hasGooglePriceSignals(null), false);
});

// ---------------------------------------------------------------------------
// Price signals — getBaselinePriceLevel
// ---------------------------------------------------------------------------

test('getBaselinePriceLevel: returns median price order for 3 cards', () => {
  const cards = [
    makePriceCard('A', 'PRICE_LEVEL_INEXPENSIVE'), // order 1
    makePriceCard('B', 'PRICE_LEVEL_MODERATE'),    // order 2
    makePriceCard('C', 'PRICE_LEVEL_EXPENSIVE'),   // order 3
  ];
  assert.equal(getBaselinePriceLevel(cards), 2); // median = MODERATE
});

test('getBaselinePriceLevel: null when no cards have priceLevel', () => {
  const cards = [makePriceCard('A'), makePriceCard('B')];
  assert.equal(getBaselinePriceLevel(cards), null);
});

// ---------------------------------------------------------------------------
// Price signals — compareCards structured output
// ---------------------------------------------------------------------------

function makePriceCardWithDetails(name, priceLevel = null, displayPrice = null, rating = 4.5, reviewCount = 500) {
  return {
    type: 'verified_place',
    name,
    cuisine: 'Restaurant',
    rating,
    reviewCount,
    neighborhood: 'River North',
    supportingDetails: {
      priceLevel,
      categoryLabel: 'Restaurant',
      whyPick: `${name} is a great pick for casual dining.`,
    },
    display: {
      displayCategory: 'Restaurant',
      displayWhy: `${name} is a great pick for casual dining.`,
      displayWhyValidated: true,
      displayPrice,
    },
    googleVerification: { businessStatus: 'OPERATIONAL', confidence: 'high', providerPlaceId: 'abc' },
  };
}

test('compareCards: structured output has rating, price, area, bestFor fields', () => {
  const cards = [
    { kind: 'restaurant', place: makePriceCardWithDetails('Alpha', 'PRICE_LEVEL_MODERATE') },
    { kind: 'restaurant', place: makePriceCardWithDetails('Beta', 'PRICE_LEVEL_INEXPENSIVE') },
  ];
  const { comparisonCards } = compareCards(cards);
  assert.ok(comparisonCards, 'comparisonCards should be present');
  for (const card of comparisonCards) {
    assert.ok('rating' in card, 'card should have rating field');
    assert.ok('price' in card, 'card should have price field');
    assert.ok('area' in card, 'card should have area field');
    assert.ok('bestFor' in card, 'card should have bestFor field');
  }
});

test('compareCards: price field shows $$ for PRICE_LEVEL_MODERATE', () => {
  const cards = [
    { kind: 'restaurant', place: makePriceCardWithDetails('Alpha', 'PRICE_LEVEL_MODERATE') },
    { kind: 'restaurant', place: makePriceCardWithDetails('Beta') },
  ];
  const { comparisonCards } = compareCards(cards);
  assert.equal(comparisonCards[0].price, '$$');
});

test('compareCards: price field is null when no price signal', () => {
  const cards = [
    { kind: 'restaurant', place: makePriceCardWithDetails('Alpha') },
    { kind: 'restaurant', place: makePriceCardWithDetails('Beta') },
  ];
  const { comparisonCards } = compareCards(cards);
  assert.equal(comparisonCards[0].price, null);
  assert.equal(comparisonCards[1].price, null);
});

test('compareCards: prefers displayPrice over priceLevel for price field', () => {
  const place = makePriceCardWithDetails('Alpha', 'PRICE_LEVEL_EXPENSIVE', '$12–30');
  const cards = [
    { kind: 'restaurant', place },
    { kind: 'restaurant', place: makePriceCardWithDetails('Beta') },
  ];
  const { comparisonCards } = compareCards(cards);
  assert.equal(comparisonCards[0].price, '$12–30');
});

test('compareCards: bestFor does not truncate mid-word at 90 chars', () => {
  const longWhy = 'A ' + 'x'.repeat(100);
  const place = makePriceCardWithDetails('Alpha');
  place.display.displayWhy = longWhy;
  const cards = [
    { kind: 'restaurant', place },
    { kind: 'restaurant', place: makePriceCardWithDetails('Beta') },
  ];
  const { comparisonCards } = compareCards(cards);
  const bf = comparisonCards[0].bestFor ?? '';
  // Should not end mid-word abruptly without ellipsis
  assert.ok(bf.endsWith('…') || bf.length <= 90, `bestFor should be ≤90 chars or end with ellipsis: "${bf}"`);
});

test('compareCards: does not expose old meta/note fields', () => {
  const cards = [
    { kind: 'restaurant', place: makePriceCardWithDetails('Alpha') },
    { kind: 'restaurant', place: makePriceCardWithDetails('Beta') },
  ];
  const { comparisonCards } = compareCards(cards);
  for (const card of comparisonCards) {
    assert.ok(!('meta' in card), 'old meta field should not be present');
    assert.ok(!('note' in card), 'old note field should not be present');
  }
});

// ---------------------------------------------------------------------------
// Price signals — AIConciergePanel structural checks
// ---------------------------------------------------------------------------

test('AIConciergePanel: pickCardMeta includes price between rating and address', () => {
  // The price should appear in the meta line composition, after rating/reviews
  assert.match(aiConciergePanel, /price.*parts\.push|parts\.push.*price/s);
});

test('AIConciergePanel: comparison rendering uses structured table rows', () => {
  // The new comparison uses a table with row labels (Rating, Price, Area, Best for)
  assert.match(aiConciergePanel, /Rating/);
  assert.match(aiConciergePanel, /Price/);
  assert.match(aiConciergePanel, /Area/);
  assert.match(aiConciergePanel, /Best for/);
});

test('AIConciergePanel: comparison rendering does not clip notes mid-sentence', () => {
  // The old truncated note approach is gone
  assert.doesNotMatch(aiConciergePanel, /card\.note/);
});

test('AIConciergePanel: comparison rendering references card.price and card.rating', () => {
  assert.match(aiConciergePanel, /card\.price/);
  assert.match(aiConciergePanel, /card\.rating/);
});

test('AIConciergePanel: imports formatDisplayPrice from priceFormatter', () => {
  assert.match(aiConciergePanel, /formatDisplayPrice/);
  assert.match(aiConciergePanel, /priceFormatter/);
});

test('AIConciergePanel: keeps canonical actionable cards below comparison', () => {
  // The canonical ConciergeCard renderer still runs after comparison block
  assert.match(aiConciergePanel, /COMPARE_CURRENT_SET/);
  assert.match(aiConciergePanel, /ConciergeCard/);
});

// ---------------------------------------------------------------------------
// Follow-up fixes — pickCardMeta, hasGooglePriceSignals priceRange, baseline
// ---------------------------------------------------------------------------

test('hasGooglePriceSignals: true when at least one card has a usable priceRange', () => {
  const card = {
    type: 'verified_place',
    name: 'PriceRange Only',
    supportingDetails: {
      priceLevel: null,
      priceRange: {
        startPrice: { currencyCode: 'USD', units: '10', nanos: 0 },
        endPrice: { currencyCode: 'USD', units: '25', nanos: 0 },
      },
    },
    display: { displayCategory: 'Restaurant', displayPrice: null },
    googleVerification: { businessStatus: 'OPERATIONAL', confidence: 'high', providerPlaceId: 'pr1' },
  };
  assert.equal(hasGooglePriceSignals([card]), true);
});

test('hasGooglePriceSignals: false for priceRange with all zero units', () => {
  const card = {
    type: 'verified_place',
    name: 'Zero Range',
    supportingDetails: {
      priceLevel: null,
      priceRange: {
        startPrice: { currencyCode: 'USD', units: '0', nanos: 0 },
        endPrice: { currencyCode: 'USD', units: '0', nanos: 0 },
      },
    },
    display: { displayCategory: 'Restaurant', displayPrice: null },
    googleVerification: { businessStatus: 'OPERATIONAL', confidence: 'high', providerPlaceId: 'pr2' },
  };
  assert.equal(hasGooglePriceSignals([card]), false);
});

test('AIConciergePanel: pickCardMeta no longer early-returns displayMetaLine (price always appended)', () => {
  // The old early-return pattern "if displayMetaLine return [displayMetaLine]" is gone.
  // Instead ratingBase is used so price is always appended.
  assert.doesNotMatch(aiConciergePanel, /if \(card\.display\?\.displayMetaLine\) return \[card\.display\.displayMetaLine\]/);
  assert.match(aiConciergePanel, /ratingBase/);
});

test('AIConciergePanel: pickCardMeta guards against duplicate price in pre-formatted meta base', () => {
  assert.match(aiConciergePanel, /metaAlreadyHasPrice/);
});

test('AIConciergePanel: imports getBaselinePriceLevel from refinementInterpreter', () => {
  assert.match(aiConciergePanel, /getBaselinePriceLevel/);
});

test('AIConciergePanel: cheaper follow-up computes baseline and checks if results are cheaper', () => {
  assert.match(aiConciergePanel, /getBaselinePriceLevel\(currentVisibleCards\)/);
  assert.match(aiConciergePanel, /hasActuallyCheaper/);
});

test('AIConciergePanel: cheaper follow-up shows honest caveat when returned cards not lower than baseline', () => {
  assert.match(aiConciergePanel, /Google price data does not prove they.*re cheaper than the current picks/s);
});

test('AIConciergePanel: cheaper follow-up shows honest caveat when lacking price signals in results', () => {
  assert.match(aiConciergePanel, /not enough Google price data to prove they.*re cheaper/s);
});

// ---------------------------------------------------------------------------
// Sev1 regression — address deduplication in pickCardMeta
// ---------------------------------------------------------------------------

test('AIConciergePanel: pickCardMeta strips address from ratingBase before re-appending (no duplicate)', () => {
  // The strip logic must detect address in the pre-built meta string and remove it
  // before re-appending address in correct position (rating · price · address).
  assert.match(aiConciergePanel, /ratingBase\.includes\(addrTrimmed\)/);
  assert.match(aiConciergePanel, /ratingBase\.slice\(0, ratingBase\.indexOf\(addrTrimmed\)\)/);
});

test('AIConciergePanel: pickCardMeta calls formatDisplayPrice with priceLevel and priceRange as fallback', () => {
  // When display.displayPrice is absent, pickCardMeta must fall back to
  // formatDisplayPrice(priceLevel, priceRange) so priceRange data reaches the UI.
  assert.match(aiConciergePanel, /details\?\.priceRange/);
});

test('AIConciergePanel: pickCardMeta price always goes through formatDisplayPrice, never raw enum', () => {
  // In pickCardMeta, the `price` variable is sourced from display.displayPrice OR
  // formatDisplayPrice(), which maps enums to $ symbols.  The raw PRICE_LEVEL_ enum
  // strings are only used as keys in PRICE_ORD for numeric comparison, never as
  // displayable text.  Confirm the price derivation chain passes through formatDisplayPrice.
  assert.match(aiConciergePanel, /display\?\.displayPrice.*\?\?[\s\S]{0,60}formatDisplayPrice/);
});

// ---------------------------------------------------------------------------
// Sev1 regression — compare table mobile stacked layout
// ---------------------------------------------------------------------------

test('AIConciergePanel: compare table has sm:hidden stacked layout for narrow screens', () => {
  // The table must be hidden on mobile; a stacked-card layout must replace it.
  assert.match(aiConciergePanel, /hidden w-full border-collapse sm:table/);
  assert.match(aiConciergePanel, /flex flex-col gap-3 sm:hidden/);
});

test('AIConciergePanel: compare stacked cards use break-words to prevent text overflow', () => {
  // Each stacked card must use break-words so long venue names don't clip.
  assert.match(aiConciergePanel, /break-words/);
});

