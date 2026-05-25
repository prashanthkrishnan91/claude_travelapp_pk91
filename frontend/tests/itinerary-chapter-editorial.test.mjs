/**
 * Phase 8C — Itinerary Item Card Chapter-Style Editorial Polish
 *
 * Contract tests for the editorial transformation of ItineraryItemCard:
 *   1. Chapter-entry structure (overline label, promoted title, article element)
 *   2. ds-token usage (no raw hex, no rgba, no legacy palette classes)
 *   3. Semantic buttons and links (real actions, accessible labels)
 *   4. No card-level click-only navigation (root article has no onClick)
 *   5. No fake/mock/sample visible data
 *   6. No backend/provider imports
 *   7. Preserved item actions (remove, compare, move-to-ideas, booking, timeline, drag)
 *   8. Preserved round-trip one-card rendering (itinerary-roundtrip-flight testid, both legs)
 *   9. Preserved Google Flights link-out contract (canonical URL, testid, aria-label, touch target)
 *  10. Mobile-safe action layout (flex-shrink-0, min-h-[44px], -m-3 p-3)
 *  11. Day column frame unchanged (behavior preserved)
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const src = readFileSync(
  new URL('../src/components/trips/ItineraryItemCard.tsx', import.meta.url),
  'utf8',
);

const dayColSrc = readFileSync(
  new URL('../src/components/trips/ItineraryDayColumn.tsx', import.meta.url),
  'utf8',
);

// ── 1. Chapter-entry structure ────────────────────────────────────────────────

test('ItineraryItemCard: defines TYPE_LABELS map for editorial overline identity', () => {
  assert.match(src, /TYPE_LABELS/, 'must define TYPE_LABELS for editorial overline labels');
});

test('ItineraryItemCard: TYPE_LABELS entry for flight', () => {
  const labelsBlock = src.slice(src.indexOf('TYPE_LABELS'), src.indexOf('TYPE_LABELS') + 400);
  assert.match(labelsBlock, /flight/, 'TYPE_LABELS must have flight entry');
});

test('ItineraryItemCard: TYPE_LABELS entry for hotel mapped to Stay', () => {
  const labelsBlock = src.slice(src.indexOf('TYPE_LABELS'), src.indexOf('TYPE_LABELS') + 400);
  assert.match(labelsBlock, /hotel.*Stay|Stay.*hotel/, 'TYPE_LABELS must map hotel to Stay');
});

test('ItineraryItemCard: TYPE_LABELS entry for meal mapped to Dining', () => {
  const labelsBlock = src.slice(src.indexOf('TYPE_LABELS'), src.indexOf('TYPE_LABELS') + 400);
  assert.match(labelsBlock, /meal.*Dining|Dining.*meal/, 'TYPE_LABELS must map meal to Dining');
});

test('ItineraryItemCard: TYPE_LABELS covers activity, transit, note', () => {
  const labelsBlock = src.slice(src.indexOf('TYPE_LABELS'), src.indexOf('TYPE_LABELS') + 400);
  assert.match(labelsBlock, /activity/, 'TYPE_LABELS must have activity entry');
  assert.match(labelsBlock, /transit/, 'TYPE_LABELS must have transit entry');
  assert.match(labelsBlock, /note/, 'TYPE_LABELS must have note entry');
});

test('ItineraryItemCard: renders data-testid="item-type-overline" for type label', () => {
  assert.match(src, /data-testid="item-type-overline"/, 'must render item-type-overline testid');
});

test('ItineraryItemCard: type overline uses Overline tracking-[0.1em]', () => {
  assert.match(src, /tracking-\[0\.1em\]/, 'type overline must use tracking-[0.1em] (Overline role)');
});

test('ItineraryItemCard: type overline is uppercase', () => {
  assert.match(src, /uppercase/, 'type overline must use uppercase class');
});

test('ItineraryItemCard: type overline uses 10px/semibold (Overline role)', () => {
  assert.ok(
    src.includes('text-[10px]') && src.includes('font-semibold'),
    'type overline must be text-[10px] font-semibold per Overline role',
  );
});

test('ItineraryItemCard: title renders with editorial prominence (text-[13px] or text-sm)', () => {
  assert.ok(
    src.includes('text-[13px]') || src.includes('text-sm'),
    'title must be at least 13px for editorial prominence over old text-xs',
  );
});

test('ItineraryItemCard: title has data-testid="item-title"', () => {
  assert.match(src, /data-testid="item-title"/, 'title element must have item-title testid');
});

test('ItineraryItemCard: root element is <article> for semantic chapter-entry identity', () => {
  assert.match(src, /<article/, 'root element must be <article> for semantic chapter-entry identity');
});

test('ItineraryItemCard: root article has data-testid="itinerary-item-card"', () => {
  assert.match(src, /data-testid="itinerary-item-card"/, 'root article must have itinerary-item-card testid');
});

// ── 2. ds-token usage ─────────────────────────────────────────────────────────

test('ItineraryItemCard: no raw hex colors in component code', () => {
  const strippedSrc = src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*/g, '');
  assert.doesNotMatch(strippedSrc, /#[0-9a-fA-F]{3,6}\b/, 'no raw hex in ItineraryItemCard');
});

test('ItineraryItemCard: no raw rgba() inline styles', () => {
  assert.doesNotMatch(src, /rgba\(/, 'must use var(--ds-accent-subtle) not raw rgba()');
});

test('ItineraryItemCard: uses folio-paper-item for card surface (Slice 3 paper conversion)', () => {
  assert.match(src, /folio-paper-item/, 'must use folio-paper-item for paper card surface — converted from bg-ds-onyx in Slice 3');
});

test('ItineraryItemCard: uses border-ds-hairline for card border (Slice 3 paper conversion)', () => {
  assert.match(src, /border-ds-hairline/, 'must use border-ds-hairline for paper card border — converted from border-ds-pen-stroke in Slice 3');
});

test('ItineraryItemCard: uses text-ds-folio-ink for title (Slice 3 paper conversion)', () => {
  assert.match(src, /text-ds-folio-ink\b/, 'title must use text-ds-folio-ink — converted from text-ds-text in Slice 3');
});

test('ItineraryItemCard: uses text-ds-folio-ink-mist for secondary content (Slice 3 paper conversion)', () => {
  assert.match(src, /text-ds-folio-ink-mist/, 'secondary content must use text-ds-folio-ink-mist — converted from text-ds-text-tertiary in Slice 3');
});

test('ItineraryItemCard: no legacy cream color classes', () => {
  const strippedSrc = src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*/g, '');
  assert.doesNotMatch(strippedSrc, /text-cream-|bg-cream-/, 'no cream- classes in ItineraryItemCard');
});

test('ItineraryItemCard: no legacy slate color classes', () => {
  const strippedSrc = src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*/g, '');
  assert.doesNotMatch(strippedSrc, /text-slate-|bg-slate-/, 'no slate- classes in ItineraryItemCard');
});

test('ItineraryItemCard: no legacy amber color classes', () => {
  const strippedSrc = src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*/g, '');
  assert.doesNotMatch(strippedSrc, /text-amber-|bg-amber-/, 'no amber- classes in ItineraryItemCard');
});

// ── 3. Semantic buttons and links ─────────────────────────────────────────────

test('ItineraryItemCard: remove action is a real button with onClick', () => {
  assert.match(src, /onClick=\{[^}]*onRemove/, 'remove must be triggered by onClick on a real button');
});

test('ItineraryItemCard: remove button has accessible aria-label', () => {
  assert.match(src, /aria-label=\{`Remove/, 'remove button must have dynamic aria-label');
});

test('ItineraryItemCard: timeline trigger is a real button with aria-label', () => {
  assert.match(src, /aria-label="Set timeline"/, 'timeline button must have aria-label="Set timeline"');
});

test('ItineraryItemCard: booking button has accessible aria-label', () => {
  assert.match(src, /aria-label=\{`Book/, 'booking button must have dynamic aria-label for the item');
});

test('ItineraryItemCard: Google Flights link-out is a real <a> with target="_blank"', () => {
  assert.match(
    src,
    /<a[\s\S]{0,200}target="_blank"[\s\S]{0,500}itinerary-google-flights-cta/,
    'Google Flights must be a real <a> with target="_blank" and data-testid',
  );
});

test('ItineraryItemCard: focus rings use ds-marine-ink on all interactive elements (Slice 3 paper conversion)', () => {
  assert.match(src, /focus-visible:outline-ds-marine-ink/, 'focus rings must use ds-marine-ink — converted from ds-accent in Slice 3');
});

// ── 4. No card-level click-only navigation ────────────────────────────────────

test('ItineraryItemCard: root article element has no onClick handler', () => {
  const articleOpenTag = src.match(/<article[\s\S]*?>/)?.[0] ?? '';
  assert.doesNotMatch(articleOpenTag, /onClick/, 'root article must not have onClick — navigation via real links/buttons only');
});

// ── 5. No fake/mock/sample visible data ──────────────────────────────────────

test('ItineraryItemCard: does not hardcode fake destination place names', () => {
  assert.doesNotMatch(src, /"Paris"|"Tokyo"|"London"|"New York"/, 'no hardcoded fake destination names');
});

test('ItineraryItemCard: no sample/placeholder/mock data patterns', () => {
  assert.doesNotMatch(src, /placeholder.*destination|sample.*trip|mock.*data/i, 'no mock/sample data patterns');
});

// ── 6. No backend/provider imports ───────────────────────────────────────────

test('ItineraryItemCard: does not import from backend or provider modules', () => {
  assert.doesNotMatch(src, /from.*backend|from.*provider|from.*duffel|from.*tavily/i, 'no backend/provider imports');
});

test('ItineraryItemCard: does not import concierge search', () => {
  assert.doesNotMatch(src, /concierge.*search|searchViaConcierge/i, 'no concierge search import');
});

test('ItineraryItemCard: imports only from allowed local modules (lib/api, types, ui components)', () => {
  const importLines = src.split('\n').filter((l) => l.trim().startsWith('import'));
  for (const line of importLines) {
    assert.doesNotMatch(line, /from.*\/backend\/|from.*\/server\/|from.*supabase.*auth/, `unexpected backend import: ${line}`);
  }
});

// ── 7. Preserved item actions ─────────────────────────────────────────────────

test('ItineraryItemCard: onRemove prop preserved', () => {
  assert.match(src, /onRemove/, 'onRemove prop must be preserved');
});

test('ItineraryItemCard: compare action preserved with onToggleCompare and isComparing', () => {
  assert.match(src, /onToggleCompare/, 'onToggleCompare must be preserved');
  assert.match(src, /isComparing/, 'isComparing state must be preserved');
});

test('ItineraryItemCard: move-to-ideas action normalized to onUnplace in overflow menu', () => {
  assert.match(src, /Move to Ideas/, 'Move to Ideas label must be preserved');
  assert.match(src, /onUnplace/, 'onUnplace handler must replace onMoveToIdeas');
});

test('ItineraryItemCard: Move to Ideas is in the overflow action menu (not a standalone button)', () => {
  assert.doesNotMatch(src, /showMoveToIdeasAction/, 'showMoveToIdeasAction standalone gate must be removed');
  assert.match(src, /onUnplace\(item\.id/, 'onUnplace must be called with item.id in the overflow menu');
});

test('ItineraryItemCard: booking checklist action preserved', () => {
  assert.match(src, /setBookingOpen/, 'booking open state must be preserved');
  assert.match(src, /BookingChecklistModal/, 'BookingChecklistModal must be preserved');
});

test('ItineraryItemCard: timeline editor preserved with all state and handlers', () => {
  assert.match(src, /timelineOpen/, 'timelineOpen state must be preserved');
  assert.match(src, /handleSaveTimeline/, 'handleSaveTimeline must be preserved');
  assert.match(src, /updateItemTimeline/, 'updateItemTimeline API call must be preserved');
  assert.match(src, /timeLabelInput/, 'timeLabelInput state must be preserved');
});

test('ItineraryItemCard: drag handle preserved with DnD integration', () => {
  assert.match(src, /useSortable/, 'useSortable must be preserved');
  assert.match(src, /listeners/, 'DnD listeners must be preserved');
  assert.match(src, /GripVertical/, 'drag handle icon must be preserved');
  assert.match(src, /setNodeRef/, 'setNodeRef must be preserved for DnD');
});

test('ItineraryItemCard: onTimelineUpdated prop preserved', () => {
  assert.match(src, /onTimelineUpdated/, 'onTimelineUpdated prop must be preserved');
});

// ── 8. Round-trip one-card rendering preserved ───────────────────────────────

test('ItineraryItemCard: round-trip flight uses single card testid itinerary-roundtrip-flight', () => {
  assert.match(src, /data-testid="itinerary-roundtrip-flight"/, 'round-trip flight must use single-card testid');
});

test('ItineraryItemCard: round-trip renders outbound leg via renderLeg', () => {
  const flightIdx = src.indexOf('item.itemType === "flight"');
  const flightBlock = src.slice(flightIdx, flightIdx + 9000);
  assert.match(flightBlock, /renderLeg\(outboundLeg/, 'must render outbound leg via renderLeg function');
});

test('ItineraryItemCard: round-trip renders return leg via renderLeg', () => {
  const flightIdx = src.indexOf('item.itemType === "flight"');
  const flightBlock = src.slice(flightIdx, flightIdx + 9000);
  assert.match(flightBlock, /renderLeg\(returnLeg/, 'must render return leg via renderLeg function');
});

test('ItineraryItemCard: round-trip badge label preserved', () => {
  assert.match(src, /Round-trip/, 'Round-trip badge label must be preserved');
});

test('ItineraryItemCard: round-trip detection checks tripType/trip_type', () => {
  const flightIdx = src.indexOf('item.itemType === "flight"');
  const flightBlock = src.slice(flightIdx, flightIdx + 9000);
  assert.match(flightBlock, /tripType.*round_trip|trip_type.*round_trip/, 'must check tripType for round-trip detection');
});

test('ItineraryItemCard: round-trip detection checks isRoundTrip/is_round_trip legacy flags', () => {
  const flightIdx = src.indexOf('item.itemType === "flight"');
  const flightBlock = src.slice(flightIdx, flightIdx + 9000);
  assert.match(flightBlock, /isRoundTrip|is_round_trip/, 'must check legacy isRoundTrip/is_round_trip flags');
});

// ── 9. Google Flights link-out contract preserved ────────────────────────────

test('ItineraryItemCard: Google Flights link reads googleFlightsSearchUrl', () => {
  const flightIdx = src.indexOf('item.itemType === "flight"');
  const flightBlock = src.slice(flightIdx, flightIdx + 9000);
  assert.match(flightBlock, /googleFlightsSearchUrl/, 'must read googleFlightsSearchUrl (canonical camelCase field)');
});

test('ItineraryItemCard: Google Flights link reads google_flights_search_url snake_case fallback', () => {
  const flightIdx = src.indexOf('item.itemType === "flight"');
  const flightBlock = src.slice(flightIdx, flightIdx + 9000);
  assert.match(flightBlock, /google_flights_search_url/, 'must include snake_case fallback for Google Flights URL');
});

test('ItineraryItemCard: Google Flights CTA uses data-testid="itinerary-google-flights-cta"', () => {
  assert.match(src, /data-testid="itinerary-google-flights-cta"/, 'Google Flights CTA must have canonical testid');
});

test('ItineraryItemCard: Google Flights CTA has aria-label="Search on Google Flights"', () => {
  assert.match(src, /aria-label="Search on Google Flights"/, 'must have accessible aria-label for screen readers');
});

test('ItineraryItemCard: Google Flights CTA uses -my-3.5 py-3.5 for 44px touch target', () => {
  assert.match(src, /-my-3\.5 py-3\.5/, 'Google Flights link must use invisible-padding for 44px touch area');
});

test('ItineraryItemCard: Google Flights CTA uses rel="noopener noreferrer"', () => {
  assert.match(src, /rel="noopener noreferrer"/, 'external Google Flights link must have rel=noopener noreferrer');
});

// ── 10. Mobile-safe action layout ────────────────────────────────────────────

test('ItineraryItemCard: action buttons use flex-shrink-0 for mobile overflow safety', () => {
  assert.match(src, /flex-shrink-0/, 'action buttons must use flex-shrink-0 for mobile safety');
});

test('ItineraryItemCard: primary actions have min-h-[44px] touch targets', () => {
  assert.match(src, /min-h-\[44px\]/, 'primary action controls must have min-h-[44px]');
});

test('ItineraryItemCard: icon action buttons use -m-3 p-3 for 44px touch-compliant hit area', () => {
  assert.match(src, /-m-3 p-3/, 'icon buttons must use -m-3 p-3 for 44px touch area');
});

test('ItineraryItemCard: drag handle uses -m-3.5 p-3.5 for 44px touch-compliant hit area', () => {
  assert.match(src, /-m-3\.5 p-3\.5/, 'drag handle must use -m-3.5 p-3.5 for 44px touch area');
});

// ── 11. Day column frame: behavior preserved, no backend added ────────────────

test('ItineraryDayColumn: day-part grouping helpers preserved', () => {
  assert.match(dayColSrc, /DAY_PART_META/, 'DAY_PART_META must be preserved in day column');
  assert.match(dayColSrc, /groupByDayPart/, 'groupByDayPart helper must be preserved');
});

test('ItineraryDayColumn: DnD primitives preserved', () => {
  assert.match(dayColSrc, /SortableContext/, 'SortableContext must remain for drag/drop');
  assert.match(dayColSrc, /useDroppable/, 'useDroppable must remain for drop zones');
});

test('ItineraryDayColumn: no backend or provider imports added', () => {
  assert.doesNotMatch(dayColSrc, /from.*backend|from.*provider|from.*duffel/i, 'no backend/provider imports in day column');
});

test('ItineraryDayColumn: onMoveItemToIdeas threading preserved', () => {
  assert.match(dayColSrc, /onMoveItemToIdeas/, 'onMoveItemToIdeas must remain threaded through day column');
});

test('ItineraryDayColumn: paper-world surface tokens (Slice 2 converted from Phase 4 dark tokens)', () => {
  assert.ok(
    dayColSrc.includes('folio-paper-card') || dayColSrc.includes('ds-bone') || dayColSrc.includes('ds-warm-paper'),
    'day column must use paper-world surface (folio-paper-card, ds-bone, or ds-warm-paper)'
  );
});
