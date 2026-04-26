import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const conciergeResponse = readFileSync(new URL('../src/components/concierge/ConciergeResponse.tsx', import.meta.url), 'utf8');
const tripAdviceView = readFileSync(new URL('../src/components/concierge/TripAdviceView.tsx', import.meta.url), 'utf8');
const placeRecommendationsView = readFileSync(new URL('../src/components/concierge/PlaceRecommendationsView.tsx', import.meta.url), 'utf8');

test('ConciergeResponse dispatches by response_type/responseType and has unsupported fallback', () => {
  assert.match(conciergeResponse, /response_type/);
  assert.match(conciergeResponse, /responseType/);
  assert.match(conciergeResponse, /PlaceRecommendationsView/);
  assert.match(conciergeResponse, /TripAdviceView/);
  assert.match(conciergeResponse, /UnsupportedView/);
});

test('TripAdviceView has no Add to Trip button rendering path', () => {
  assert.doesNotMatch(tripAdviceView, /Add to Trip/);
  assert.doesNotMatch(tripAdviceView, /ConciergeCard|SearchResultCard|addStructuredConciergeItemToTrip|AddToTrip/);
});

test('PlaceRecommendationsView does not import markdown renderers', () => {
  assert.doesNotMatch(placeRecommendationsView, /react-markdown|markdown renderer|Markdown/);
});

test('Snapshot markers for all three dedicated views are present', () => {
  assert.match(placeRecommendationsView, /aria-label="place recommendations"/);
  assert.match(tripAdviceView, /aria-label="trip advice"/);
  const unsupportedView = readFileSync(new URL('../src/components/concierge/UnsupportedView.tsx', import.meta.url), 'utf8');
  assert.match(unsupportedView, /aria-label="unsupported response"/);
});
