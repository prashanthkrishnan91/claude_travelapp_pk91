import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  pickCardReason,
  sanitizeWhyPick,
  shouldShowCollapsedSources,
  verifiedAddableCount,
} from '../src/lib/concierge/cardPresentation.js';

const aiConciergePanel = readFileSync(new URL('../src/components/trips/AIConciergePanel.tsx', import.meta.url), 'utf8');

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

test('sanitizeWhyPick blocks awkward fragments and cross-venue leakage', () => {
  const fallback = sanitizeWhyPick('Alinea is backed by rated 4.8 and with rated praise.', 'Alinea', ['Alinea', 'Oriole']);
  assert.match(fallback, /Selected because available place details/i);

  const leaked = sanitizeWhyPick('Try Oriole first.', 'Alinea', ['Alinea', 'Oriole']);
  assert.match(leaked, /Selected because available place details/i);
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
    assert.match(result, /Selected because available place details/i,
      `Expected fallback for: "${input}", got: "${result}"`);
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
      /Selected because available place details/i.test(result),
      false,
      `Expected good text to pass, got fallback for: "${input}"`,
    );
    assert.ok(hasConcreteSignal(result), `No concrete signal in: "${result}"`);
  }
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

test('AIConciergePanel does not render research sources as ConciergeCard', () => {
  // Research sources must never be rendered as addable ConciergeCard components.
  // The old else-branch rendered them as cards — verify it is gone.
  assert.doesNotMatch(aiConciergePanel, /Research sources.*ConciergeCard/s,
    'Research sources should not be rendered as ConciergeCard components');
  // The canAdd={false} ConciergeCard for research_source must not exist
  assert.doesNotMatch(aiConciergePanel, /sourceType.*article_listicle_blog_directory/s,
    'Old research-source card branch should be removed');
});
