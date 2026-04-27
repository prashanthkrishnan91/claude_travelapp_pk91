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
];

test('card reason prefers supportingDetails.whyPick.text over fallback', () => {
  const card = {
    name: 'Blind Barber',
    supportingDetails: {
      whyPick: {
        text: 'Blind Barber fits the nearby cocktail request because it is a Google-verified Fulton Market cocktail bar with a 4.3 rating across 970 reviews.',
        generationMethod: 'deterministic',
      },
    },
    primaryReason: 'fallback should not be used',
  };
  const reason = pickCardReason(card);
  assert.equal(
    reason,
    'Blind Barber fits the nearby cocktail request because it is a Google-verified Fulton Market cocktail bar with a 4.3 rating across 970 reviews.',
  );
});

test('sanitizeWhyPick blocks awkward fragments and cross-venue leakage', () => {
  const fallback = sanitizeWhyPick('Alinea is backed by rated 4.8 and with rated praise.', 'Alinea', ['Alinea', 'Oriole']);
  assert.match(fallback, /Selected because available place details/i);

  const leaked = sanitizeWhyPick('Try Oriole first.', 'Alinea', ['Alinea', 'Oriole']);
  assert.match(leaked, /Selected because available place details/i);
});

test('blocked generic phrases are absent from accepted visible reason text', () => {
  const reason = sanitizeWhyPick(
    'Kumiko fits this cocktail request in West Loop with 4.7 rating across 1,200 reviews.',
    'Kumiko',
    ['Kumiko'],
  );
  for (const blocked of blockedGenericPhrases) {
    assert.equal(reason.toLowerCase().includes(blocked.toLowerCase()), false);
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
