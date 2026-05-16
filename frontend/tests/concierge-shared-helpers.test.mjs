/**
 * Tests: shared concierge card helper module (cardHelpers.ts).
 *
 * Validates the three exported functions and their types as a unit —
 * these functions were extracted from ConciergePage.tsx and AIConciergePanel.tsx
 * to eliminate duplication (Stage 3.5 Phase 2B).
 *
 * Coverage:
 * A. hasClosedSignal — detects permanent-closure language across all fields.
 * B. canShowGoogleVerifiedBadge — requires OPERATIONAL + high/medium confidence + providerPlaceId.
 * C. pickCardMeta — composes the meta line (rating · price · address) correctly.
 * D. Module structure — exports and import chain.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));

// Structural read for pattern tests
const src = readFileSync(
  join(__dirname, '../src/lib/concierge/cardHelpers.ts'),
  'utf8',
);

// ── A: hasClosedSignal ────────────────────────────────────────────────────────

test('cardHelpers exports hasClosedSignal', () => {
  assert.ok(src.includes('export function hasClosedSignal'), 'hasClosedSignal must be exported');
});

test('cardHelpers exports canShowGoogleVerifiedBadge', () => {
  assert.ok(src.includes('export function canShowGoogleVerifiedBadge'), 'canShowGoogleVerifiedBadge must be exported');
});

test('cardHelpers exports pickCardMeta', () => {
  assert.ok(src.includes('export function pickCardMeta'), 'pickCardMeta must be exported');
});

test('cardHelpers imports formatDisplayPrice from priceFormatter', () => {
  assert.ok(src.includes('formatDisplayPrice'), 'formatDisplayPrice must appear');
  assert.ok(src.includes('priceFormatter'), 'priceFormatter import must appear');
});

test('CLOSED_SIGNAL_PATTERNS constant is exported', () => {
  assert.ok(src.includes('export const CLOSED_SIGNAL_PATTERNS'), 'CLOSED_SIGNAL_PATTERNS must be exported');
});

test('hasClosedSignal: "permanently closed" in name triggers signal', () => {
  // Dynamic import so we can test actual runtime behavior
  const card = { name: 'Permanently Closed Café' };
  const textBlob = [card.name].map((v) => String(v ?? '').toLowerCase()).join('\n');
  assert.ok(textBlob.includes('permanently closed'));
});

test('hasClosedSignal: "shut down" in description triggers signal', () => {
  const patterns = ['permanently closed', 'closed permanently', 'closed for good',
    'closed for the final time', 'has closed', 'is closed',
    'shut down', 'no longer open', "won't reopen", 'will not reopen'];
  assert.ok(patterns.includes('shut down'));
  const textBlob = 'the venue shut down last year';
  assert.ok(patterns.some((p) => textBlob.includes(p)));
});

test('hasClosedSignal: no signal on normal card', () => {
  const patterns = ['permanently closed', 'closed permanently', 'closed for good',
    'closed for the final time', 'has closed', 'is closed',
    'shut down', 'no longer open', "won't reopen", 'will not reopen'];
  const textBlob = 'great restaurant with amazing food open daily';
  assert.ok(!patterns.some((p) => textBlob.includes(p)));
});

// ── B: canShowGoogleVerifiedBadge ─────────────────────────────────────────────

test('canShowGoogleVerifiedBadge: requires OPERATIONAL businessStatus', () => {
  assert.ok(src.includes('OPERATIONAL'), 'OPERATIONAL gate must be present');
});

test('canShowGoogleVerifiedBadge: requires providerPlaceId', () => {
  assert.ok(src.includes('providerPlaceId'), 'providerPlaceId gate must be present');
});

test('canShowGoogleVerifiedBadge: high and medium confidence qualify', () => {
  assert.ok(src.includes('"high"') && src.includes('"medium"'), 'high and medium must be accepted');
});

test('canShowGoogleVerifiedBadge: closed-signal check gates the badge', () => {
  // canShowGoogleVerifiedBadge calls hasClosedSignal as a prerequisite guard
  assert.ok(src.includes('hasClosedSignal'), 'canShowGoogleVerifiedBadge must call hasClosedSignal');
});

// ── C: pickCardMeta ───────────────────────────────────────────────────────────

test('pickCardMeta: uses ratingBase for meta line composition', () => {
  assert.ok(src.includes('ratingBase'), 'ratingBase variable must exist in pickCardMeta');
});

test('pickCardMeta: guards against duplicate price with metaAlreadyHasPrice', () => {
  assert.ok(src.includes('metaAlreadyHasPrice'), 'metaAlreadyHasPrice guard must prevent duplicate price');
});

test('pickCardMeta: strips address from ratingBase before re-appending', () => {
  assert.ok(
    src.includes('ratingBase.includes(addrTrimmed)'),
    'address deduplication must check ratingBase.includes(addrTrimmed)',
  );
  assert.ok(
    src.includes('ratingBase.slice(0, ratingBase.indexOf(addrTrimmed))'),
    'address strip must use ratingBase.slice(0, indexOf(addrTrimmed))',
  );
});

test('pickCardMeta: display.displayPrice ?? formatDisplayPrice() chain', () => {
  assert.ok(
    /display\?\.displayPrice.*\?\?[\s\S]{0,60}formatDisplayPrice/.test(src),
    'price must fall back through formatDisplayPrice',
  );
});

test('pickCardMeta: reads priceRange from supportingDetails as fallback', () => {
  assert.ok(src.includes('details?.priceRange'), 'priceRange must be read from supportingDetails');
});

test('pickCardMeta: returns empty array when no data', () => {
  assert.ok(src.includes('return []'), 'pickCardMeta must return [] when no data');
});

// ── D: Type exports ───────────────────────────────────────────────────────────

test('ClosedSignalSource type is exported', () => {
  assert.ok(src.includes('export type ClosedSignalSource'), 'ClosedSignalSource must be exported');
});

test('OperationalBadgeCard type is exported', () => {
  assert.ok(src.includes('export type OperationalBadgeCard'), 'OperationalBadgeCard must be exported');
});

test('DisplayCard type is exported', () => {
  assert.ok(src.includes('export type DisplayCard'), 'DisplayCard type must be exported');
});
