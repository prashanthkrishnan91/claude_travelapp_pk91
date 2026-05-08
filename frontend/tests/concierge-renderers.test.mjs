import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  pickCardReason,
  pickCardCategory,
  sanitizeWhyPick,
  shouldShowCollapsedSources,
  verifiedAddableCount,
  isAddableCanonicalCard,
} from '../src/lib/concierge/cardPresentation.js';

const aiConciergePanel = readFileSync(new URL('../src/components/trips/AIConciergePanel.tsx', import.meta.url), 'utf8');
const placeRecommendationsView = readFileSync(new URL('../src/components/concierge/PlaceRecommendationsView.tsx', import.meta.url), 'utf8');
const apiClient = readFileSync(new URL('../src/lib/api.ts', import.meta.url), 'utf8');

const blockedGenericPhrases = [
  'A strong pick for well-reviewed',
  'guest feedback, location, and relevance',
  'setting that fits this dining request',
  'polished night-out experience',
  'Great fit for this trip',
  'trusted place signals',
  'viable option',
  'matches this dining request',
  'fits this hotel request',
  'fits this Michelin request',
  'is a strong attraction match',
  'well-rated',
  'fits this request as a Google-verified',
];

// Checks that text contains at least one concrete data signal (number or known neighbourhood)
function hasConcreteSignal(text) {
  if (/\d+\.\d+/.test(text)) return true;  // rating like 4.3
  if (/\d{1,3}(,\d{3})?\s+reviews?/i.test(text)) return true;  // review count
  const locations = ['loop', 'market', 'park', 'square', 'river north', 'downtown', 'village', 'barber'];
  return locations.some((loc) => text.toLowerCase().includes(loc));
}

test('card reason prefers supportingDetails.whyPick.text over fallback', () => {
  const card = {
    name: 'Blind Barber',
    supportingDetails: {
      whyPick: {
        text: 'Blind Barber is a Fulton Market cocktail bar with a 4.3 rating across 970 reviews, making it a reliable nearby drinks option.',
        generationMethod: 'deterministic',
      },
    },
    primaryReason: 'fallback should not be used',
  };
  const reason = pickCardReason(card);
  assert.equal(
    reason,
    'Blind Barber is a Fulton Market cocktail bar with a 4.3 rating across 970 reviews, making it a reliable nearby drinks option.',
  );
});

test('card reason prefers supportingDetails over top-level whyPick when displayWhy is missing', () => {
  const card = {
    name: 'Scotch Lodge',
    whyPick: 'Top-level reason from canonical payload.',
    supportingDetails: { whyPick: 'Supporting-details reason.' },
  };
  assert.equal(pickCardReason(card), 'Supporting-details reason.');
});

test('sanitizeWhyPick blocks category+rating generic template', () => {
  const result = sanitizeWhyPick(
    'A restaurant with 4.8 rating across 15,764 reviews.',
    'Alinea',
    ['Alinea'],
  );
  assert.equal(result, '');
});

test('card reason does not render [object Object] when whyPick is string contract', () => {
  const card = { whyPick: 'String reason contract.' };
  assert.equal(pickCardReason(card), 'String reason contract.');
});

test('sanitizeWhyPick blocks awkward fragments and cross-venue leakage', () => {
  const fallback = sanitizeWhyPick('Alinea is backed by rated 4.8 and with rated praise.', 'Alinea', ['Alinea', 'Oriole']);
  assert.equal(fallback, '');

  const leaked = sanitizeWhyPick('Try Oriole first.', 'Alinea', ['Alinea', 'Oriole']);
  assert.equal(leaked, '');
});

test('sanitizeWhyPick blocks all listed generic phrases', () => {
  const genericInputs = [
    'A strong pick for well-reviewed food and polished service.',
    'This is a viable option for your stay.',
    'Great fit for this trip based on guest feedback, location, and relevance.',
    'Recommended for a polished night-out experience.',
    'Trusted place signals indicate a good choice.',
    'This matches this dining request with well-rated food.',
    'Fits this hotel request in the area.',
  ];
  for (const input of genericInputs) {
    const result = sanitizeWhyPick(input, 'Some Place', ['Some Place']);
    assert.equal(result, '',
      `Expected fallback for: "${input}", got: "${result}"`);
  }
});

test('sanitizeWhyPick replaces all newly banned fragments', () => {
  const bannedInputs = [
    'This place is backed by guest feedback.',
    'Selected for this request based on available evidence.',
    'Verified restaurant details are included here.',
    'Verified drinks-focused details indicate quality.',
    'Verified place details confirm this pick.',
  ];
  for (const input of bannedInputs) {
    const result = sanitizeWhyPick(input, 'Some Place', ['Some Place']);
    assert.equal(result, '');
  }
});

test('sanitizeWhyPick passes evidence-based text with rating and location', () => {
  const goodInputs = [
    'Blind Barber is a Fulton Market cocktail bar with a 4.3 rating across 970 reviews, making it a reliable nearby drinks option.',
    'Daisies is a lower-profile Logan Square Midwestern spot with a 4.7 rating across 612 reviews, making it a strong local favorite away from tourist-heavy areas.',
    'Alinea is a Michelin 3-star Lincoln Park tasting menu destination, making it the top splurge option for a Michelin-focused dinner.',
    'La Grande Boucherie is a River North French brasserie with a 4.6 rating across 2,300 reviews, offering a strong value alternative.',
  ];
  for (const input of goodInputs) {
    const result = sanitizeWhyPick(input, 'Test Place', ['Test Place']);
    assert.equal(
      /well-regarded local pick with verified listing details/i.test(result),
      false,
      `Expected good text to pass, got fallback for: "${input}"`,
    );
    assert.ok(hasConcreteSignal(result), `No concrete signal in: "${result}"`);
  }
});

test('renderer flow preserves valid backend whyPick text', () => {
  const card = {
    name: 'Punch House',
    supportingDetails: {
      whyPick: 'Punch House is a West Loop cocktail bar with a 4.6 rating across 1,200 reviews, making it a reliable nearby drinks option.',
      categoryLabel: 'Cocktail Bar',
    },
    primaryReason: 'Selected for this bar request based on verified drinks-focused details and available evidence.',
  };
  const picked = pickCardReason(card);
  const rendered = sanitizeWhyPick(picked, card.name, [card.name]);
  assert.equal(rendered, picked);
  assert.doesNotMatch(rendered, /Selected for this bar request based on verified drinks-focused details and available evidence\./i);
});

test('blocked generic phrases are absent from accepted visible reason text', () => {
  const reason = sanitizeWhyPick(
    'Kumiko is a West Loop cocktail bar with a 4.7 rating across 1,200 reviews, making it a reliable nearby drinks option.',
    'Kumiko',
    ['Kumiko'],
  );
  for (const blocked of blockedGenericPhrases) {
    assert.equal(reason.toLowerCase().includes(blocked.toLowerCase()), false,
      `Blocked phrase "${blocked}" found in output: "${reason}"`);
  }
});

test('collapsed sources disclosure appears only when research sources exist and addable cards exist', () => {
  const withAddable = {
    restaurants: [{ type: 'verified_place' }],
    attractions: [],
    hotels: [],
    researchSources: [{ type: 'research_source', title: 'Top bars' }],
  };
  assert.equal(verifiedAddableCount(withAddable), 1);
  assert.equal(shouldShowCollapsedSources(withAddable), true);

  const noAddable = {
    restaurants: [{ type: 'research_source' }],
    attractions: [],
    hotels: [],
    researchSources: [{ type: 'research_source', title: 'Top bars' }],
  };
  assert.equal(verifiedAddableCount(noAddable), 0);
  assert.equal(shouldShowCollapsedSources(noAddable), false);
});

test('AIConciergePanel keeps compact Sources used disclosure path', () => {
  assert.match(aiConciergePanel, /Sources used/);
  assert.match(aiConciergePanel, /<details/);
  assert.match(aiConciergePanel, /shouldShowCollapsedSources\(msg\)/);
});

test('PlaceRecommendationsView sanitizes reasons via shared cardPresentation helpers', () => {
  assert.match(placeRecommendationsView, /pickCardReason/);
  assert.match(placeRecommendationsView, /sanitizeWhyPick/);
  assert.match(placeRecommendationsView, /pickCardReason\(card\)/);
  assert.doesNotMatch(placeRecommendationsView, /Strong fit for this trip based on trusted place signals\./);
});

test('AIConciergePanel does not render research sources as ConciergeCard', () => {
  // Research sources must never be rendered as addable ConciergeCard components.
  // The old else-branch rendered them as cards — verify it is gone.
  assert.doesNotMatch(aiConciergePanel, /Research sources.*ConciergeCard/s,
    'Research sources should not be rendered as ConciergeCard components');
  // The canAdd={false} ConciergeCard for research_source must not exist
  assert.doesNotMatch(aiConciergePanel, /sourceType.*article_listicle_blog_directory/s,
    'Old research-source card branch should be removed');
});

test('callConciergeSearch normalizes snake_case typed responses before mapping cards', () => {
  assert.match(apiClient, /normalizeConciergeResponse\(raw\)/);
  assert.match(apiClient, /normalized\.responseType !== "place_recommendations"/);
});

test('AIConciergePanel does not hard-require type=verified_place for rendering addable cards', () => {
  assert.match(aiConciergePanel, /isRenderableVerifiedPlace/);
  assert.doesNotMatch(aiConciergePanel, /\.filter\(\(r\) => r\.type === "verified_place"\)/);
});

// ── Semantic card note-rendering contract (PR #277 regression tests) ──────────
// These tests exercise the pickCardReason semantic path that had no coverage.
// Root cause: set-writer notes were discarded when SLA timed out before Step 7,
// so display_why_validated arrived as false and pickCardReason returned "" for
// every card.  Tests here document the expected frontend contract.

test('pickCardReason returns displayWhy when displayWhyValidated is true', () => {
  const note = 'Hand-rolled pasta and a rotating natural wine list anchor this spot.';
  const card = {
    name: 'Test Osteria',
    display: {
      displayWhy: note,
      displayWhyValidated: true,
      displayCategory: 'Italian Restaurant',
      displayBadges: [],
      addability: 'addable',
    },
    supportingDetails: { whyPick: 'legacy note that must not be used' },
    primaryReason: 'legacy fallback that must not be used',
  };
  assert.equal(pickCardReason(card), note,
    'Semantic card with displayWhyValidated=true must return display.displayWhy');
});

test('pickCardReason returns empty string when displayWhyValidated is false', () => {
  const card = {
    name: 'Test Place',
    display: {
      displayWhy: 'Some note that should not be shown.',
      displayWhyValidated: false,
      displayCategory: 'Restaurant',
      displayBadges: [],
      addability: 'addable',
    },
    supportingDetails: { whyPick: 'legacy note' },
    primaryReason: 'legacy fallback',
  };
  assert.equal(pickCardReason(card), '',
    'Semantic card with displayWhyValidated=false must return "" — no legacy fallback allowed');
});

test('pickCardReason returns empty string when displayWhyValidated is absent', () => {
  // display object present but displayWhyValidated not set — treats as false.
  const card = {
    name: 'Test Place',
    display: {
      displayWhy: 'A note.',
      displayCategory: 'Restaurant',
      displayBadges: [],
      addability: 'addable',
    },
    supportingDetails: { whyPick: 'legacy note' },
  };
  assert.equal(pickCardReason(card), '',
    'display present but displayWhyValidated absent must return "" — not legacy fallback');
});

test('pickCardReason returns empty string when displayWhy is too short even with validated=true', () => {
  const card = {
    name: 'Test Place',
    display: { displayWhy: 'Short.', displayWhyValidated: true, displayBadges: [], addability: 'addable' },
  };
  assert.equal(pickCardReason(card), '',
    'Note shorter than 12 chars must be rejected even when displayWhyValidated=true');
});

test('pickCardReason falls back to legacy fields when display is absent', () => {
  const card = {
    name: 'Legacy Bar',
    supportingDetails: { whyPick: 'A fine cocktail bar in River North.' },
    primaryReason: 'fallback',
  };
  const reason = pickCardReason(card);
  assert.equal(reason, 'A fine cocktail bar in River North.',
    'No display object → must use legacy supportingDetails.whyPick');
});

test('sanitizeWhyPick passes a well-formed LLM evidence note', () => {
  const note = 'Hand-rolled pasta and a rotating natural wine list anchor this enoteca.';
  const result = sanitizeWhyPick(note, 'Enoteca Roma', ['Enoteca Roma', 'Bar Milano']);
  assert.equal(result, note,
    'A well-formed LLM note free of banned phrases must pass sanitization unchanged');
});

test('sanitizeWhyPick rejects a note containing a cross-venue name', () => {
  const result = sanitizeWhyPick(
    'Known for the same craft cocktails as Bar Milano next door.',
    'Enoteca Roma',
    ['Enoteca Roma', 'Bar Milano'],
  );
  assert.equal(result, '', 'Note containing another venue name must be rejected');
});

test('pickCardReason does not insert a deterministic fallback note for semantic cards', () => {
  // Semantic cards (display present) must never fall through to legacy fields.
  // This ensures no deterministic or template text reaches the rendered note.
  const card = {
    name: 'Test Bar',
    display: { displayWhy: '', displayWhyValidated: false, displayBadges: [], addability: 'addable' },
    supportingDetails: { whyPick: 'deterministic template: Test Bar is a strong bar option.' },
    primaryReason: 'Test Bar is a strong bar option with a 4.5 rating.',
    whyPick: 'Test Bar is a strong bar option with a 4.5 rating.',
  };
  assert.equal(pickCardReason(card), '',
    'Semantic card with validated=false must never fall back to supportingDetails or primaryReason');
});

test('api.ts ConciergeDisplayFields interface declares displayWhyValidated', () => {
  assert.match(apiClient, /displayWhyValidated/,
    'ConciergeDisplayFields must declare displayWhyValidated for the frontend contract');
});

test('toCamel correctly converts display_why_validated to displayWhyValidated', () => {
  // Verify the key transform used in apiFetch does the right thing.
  // The conversion is done by snakeToCamel which uses /_([a-z])/g → ch.toUpperCase()
  function snakeToCamel(str) {
    return str.replace(/_([a-z])/g, (_, ch) => ch.toUpperCase());
  }
  assert.equal(snakeToCamel('display_why_validated'), 'displayWhyValidated');
  assert.equal(snakeToCamel('display_why'), 'displayWhy');
  assert.equal(snakeToCamel('display_category'), 'displayCategory');
});

// ── End-to-end snake→camel normalization (PR #regression contract) ────────────
// Simulates the full apiFetch toCamel transform on a raw backend card object.
// Verifies that display_why_validated (snake_case from backend) becomes
// displayWhyValidated (camelCase) and that pickCardReason reads it correctly.

function transformKeys(obj, transform) {
  if (Array.isArray(obj)) return obj.map((item) => transformKeys(item, transform));
  if (obj !== null && typeof obj === 'object') {
    return Object.fromEntries(
      Object.entries(obj).map(([k, v]) => [transform(k), transformKeys(v, transform)]),
    );
  }
  return obj;
}

function snakeToCamelStr(str) {
  return str.replace(/_([a-z])/g, (_, ch) => ch.toUpperCase());
}

function toCamel(data) {
  return transformKeys(data, snakeToCamelStr);
}

test('end-to-end: snake_case backend card becomes camelCase and pickCardReason returns validated note', () => {
  const snakeCaseCard = {
    name: 'Izakaya Mita',
    type: 'verified_place',
    place_id: 'ChIJtest123',
    display: {
      display_why: 'Basement bar setting with Japanese street food and small bites in a casual West Loop space.',
      display_why_validated: true,
      display_category: 'Izakaya',
      display_badges: [],
      addability: 'addable',
    },
    supporting_details: { why_pick: 'legacy fallback — must not be used' },
    primary_reason: 'legacy fallback — must not be used',
  };
  const card = toCamel(snakeCaseCard);

  assert.equal(card.display.displayWhyValidated, true,
    'display_why_validated must become displayWhyValidated=true after toCamel');
  assert.equal(card.display.displayWhy,
    'Basement bar setting with Japanese street food and small bites in a casual West Loop space.',
    'display_why must become displayWhy unchanged after toCamel');
  assert.equal(card.placeId, 'ChIJtest123',
    'place_id must become placeId after toCamel — required for add-to-day identity');

  const reason = pickCardReason(card);
  assert.equal(reason,
    'Basement bar setting with Japanese street food and small bites in a casual West Loop space.',
    'pickCardReason must return displayWhy when displayWhyValidated=true');
});

test('end-to-end: snake_case card with display_why_validated=false yields no note', () => {
  const snakeCaseCard = {
    name: 'Test Place',
    type: 'verified_place',
    display: {
      display_why: 'A note that must not appear.',
      display_why_validated: false,
      display_category: 'Bar',
      display_badges: [],
      addability: 'addable',
    },
    supporting_details: { why_pick: 'legacy note — must not leak' },
    primary_reason: 'legacy fallback — must not leak',
  };
  const card = toCamel(snakeCaseCard);
  assert.equal(pickCardReason(card), '',
    'Semantic card with validated=false must produce empty reason — no legacy fallback');
});

test('production fixture: izakaya note with Chicago W Lake St address passes sanitizeWhyPick', () => {
  // Production log note from semantic_retrieval_v1 set_writer_primary accepted=4/8.
  // "820 W Lake St" has two words (W + Lake) between the number and "St", so
  // containsAddressSignal must NOT block it (regex only catches N WORD SUFFIX form).
  const note = 'Basement bar setting with Japanese street food and small bites in a Lower Level space at 820 W Lake St.';
  const result = sanitizeWhyPick(note, 'Izakaya Test', ['Izakaya Test']);
  assert.equal(result, note,
    'Production izakaya note must pass sanitizeWhyPick — Chicago W Lake St should not be treated as address signal');
});

test('production fixture: full semantic card render path for izakaya note', () => {
  const note = 'Basement bar setting with Japanese street food and small bites in a Lower Level space at 820 W Lake St.';
  const card = {
    name: 'Izakaya Mita',
    type: 'verified_place',
    display: {
      displayWhy: note,
      displayWhyValidated: true,
      displayCategory: 'Izakaya',
      displayBadges: [],
      addability: 'addable',
    },
  };
  const allTitles = ['Izakaya Mita', 'Yugen', 'Etta', 'Maple & Ash'];
  const picked = pickCardReason(card);
  const rendered = sanitizeWhyPick(picked, card.name, allTitles);
  assert.equal(rendered, note,
    'Full render path must preserve izakaya production note unchanged');
});

// ── Frontend Fallback Ladder Removal v1 (PR #287/#289 contract enforcement) ──
// AIConciergePanel must render a ConciergeCard only when the canonical display
// contract is present.  These tests pin the contract gate so backend drift can
// no longer be silently masked by reading top-level legacy fields.

function makeCanonicalCard(overrides = {}) {
  return {
    type: 'verified_place',
    name: 'Test Place',
    googleVerification: { providerPlaceId: 'ChIJtest123' },
    display: {
      displayName: 'Test Place',
      displayCategory: 'Restaurant',
      displayWhy: 'A canonical reason that is more than twelve chars.',
      displayWhyValidated: true,
      displayBadges: [],
      addability: 'addable',
    },
    supportingDetails: { metaLine: '★ 4.5 (200 reviews)' },
    ...overrides,
  };
}

test('isAddableCanonicalCard accepts a card with the full canonical contract', () => {
  assert.equal(isAddableCanonicalCard(makeCanonicalCard()), true);
});

test('isAddableCanonicalCard rejects a card missing display.displayName', () => {
  const card = makeCanonicalCard();
  card.display.displayName = '';
  assert.equal(isAddableCanonicalCard(card), false,
    'Empty displayName must fail the canonical gate — never fall back to top-level name');
});

test('isAddableCanonicalCard rejects a card missing display.displayCategory', () => {
  const card = makeCanonicalCard();
  card.display.displayCategory = null;
  assert.equal(isAddableCanonicalCard(card), false,
    'Missing displayCategory must fail closed — never fall back to cuisine/category');
});

test('isAddableCanonicalCard rejects a card whose addability is not "addable"', () => {
  for (const value of ['research_only', 'closed', null, undefined, 'unknown']) {
    const card = makeCanonicalCard();
    card.display.addability = value;
    assert.equal(isAddableCanonicalCard(card), false,
      `addability="${value}" must not render as a polished addable card`);
  }
});

test('isAddableCanonicalCard rejects a card without Google providerPlaceId', () => {
  const card = makeCanonicalCard();
  card.googleVerification = null;
  assert.equal(isAddableCanonicalCard(card), false,
    'No googleVerification → no Add to Day / Save / Maps as if Google-verified');

  const card2 = makeCanonicalCard();
  card2.googleVerification = { providerPlaceId: '' };
  assert.equal(isAddableCanonicalCard(card2), false,
    'Empty providerPlaceId must fail closed');
});

test('isAddableCanonicalCard rejects a card with only top-level legacy fields', () => {
  // The exact fallback ladder the v1 frontend contract enforcement removes.
  const legacyOnly = {
    type: 'verified_place',
    name: 'Top-level Only',
    cuisine: 'Italian',
    category: 'Restaurant',
    description: 'Legacy description',
    address: '123 Main St',
    rating: 4.6,
    reviewCount: 1200,
    mapsLink: 'https://maps.google.com/?q=foo',
    bookingUrl: 'https://example.com/book',
    verifiedPlace: true,
  };
  assert.equal(isAddableCanonicalCard(legacyOnly), false,
    'Top-level name/category/description/address/rating must NOT be sufficient — the canonical display contract is required');
});

test('isAddableCanonicalCard rejects null / non-object input safely', () => {
  assert.equal(isAddableCanonicalCard(null), false);
  assert.equal(isAddableCanonicalCard(undefined), false);
  assert.equal(isAddableCanonicalCard('string'), false);
  assert.equal(isAddableCanonicalCard(42), false);
});

test('pickCardCategory returns display.displayCategory only — no legacy fallback', () => {
  assert.equal(pickCardCategory(makeCanonicalCard()), 'Restaurant');

  const noDisplay = { name: 'X', cuisine: 'Italian', supportingDetails: { categoryLabel: 'Trattoria' } };
  assert.equal(pickCardCategory(noDisplay), '',
    'Missing display.displayCategory must yield "" — never fall back to cuisine/categoryLabel');

  const blankDisplayCategory = makeCanonicalCard();
  blankDisplayCategory.display.displayCategory = '   ';
  assert.equal(pickCardCategory(blankDisplayCategory), '',
    'Whitespace-only displayCategory must yield ""');
});

test('AIConciergePanel imports the canonical addable-card gate', () => {
  assert.match(aiConciergePanel, /isAddableCanonicalCard/,
    'AIConciergePanel must import isAddableCanonicalCard for the canonical gate');
});

test('AIConciergePanel does not derive card category from top-level cuisine/category strings', () => {
  // The legacy ladder built `category: place.cuisine || "Restaurant"` and passed
  // it through pickCardCategory as a fallback.  After v1 enforcement that path
  // must be gone — the rendered category comes only from display.displayCategory.
  assert.doesNotMatch(aiConciergePanel, /place\.cuisine\s*\|\|\s*"Restaurant"/,
    'Legacy `place.cuisine || "Restaurant"` ladder must be removed');
  assert.doesNotMatch(aiConciergePanel, /place\.category\s*\|\|\s*"Attraction"/,
    'Legacy `place.category || "Attraction"` ladder must be removed');
  assert.doesNotMatch(aiConciergePanel, /pickCardCategory\(place,\s*category\)/,
    'pickCardCategory must be called with the card alone (no legacy fallback arg)');
});

test('AIConciergePanel does not read top-level rating/reviewCount/neighborhood for meta', () => {
  // pickCardMeta used to reach into card.rating, card.reviewCount, card.address,
  // and card.neighborhood when the canonical meta_line was missing.  After v1
  // enforcement those reads must be gone so missing meta is visible (no meta
  // line) instead of silently rebuilt from raw fields.
  assert.doesNotMatch(aiConciergePanel, /card\.reviewCount/,
    'pickCardMeta must not read top-level reviewCount');
  assert.doesNotMatch(aiConciergePanel, /card\.neighborhood/,
    'pickCardMeta must not read top-level neighborhood');
  assert.doesNotMatch(aiConciergePanel, /typeof card\.rating === "number"/,
    'pickCardMeta must not derive rating from top-level numeric rating');
});

test('AIConciergePanel renders title from display.displayName, not place.name', () => {
  // The polished card title should come from the canonical display contract.
  assert.match(aiConciergePanel, /place\.display\?\.displayName/,
    'AIConciergePanel must read place.display.displayName for the rendered title');
});

test('AIConciergePanel does not reintroduce the v1A quarantined product surfaces', () => {
  // Guard against accidental regression that re-wires Concierge cards to the
  // legacy mock-backed search routes pruned in PR #288 / #289.
  assert.doesNotMatch(aiConciergePanel, /\/search\/attractions/);
  assert.doesNotMatch(aiConciergePanel, /\/search\/clusters/);
  assert.doesNotMatch(aiConciergePanel, /\/search\/best-area/);
});

test('cache version bump: AIConciergePanel declares CONCIERGE_CACHE_VERSION >= 5', () => {
  // Version must be >= 5 to evict pre-PR#277 cached messages that had
  // displayWhyValidated=false for all cards (set-writer notes were dropped on SLA timeout).
  const match = aiConciergePanel.match(/CONCIERGE_CACHE_VERSION\s*=\s*(\d+)/);
  assert.ok(match, 'CONCIERGE_CACHE_VERSION must be declared in AIConciergePanel');
  const version = parseInt(match[1], 10);
  assert.ok(version >= 5,
    `CONCIERGE_CACHE_VERSION must be >= 5 to evict stale pre-validation cache; found ${version}`);
});
