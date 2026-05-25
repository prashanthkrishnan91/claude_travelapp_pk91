/**
 * Itinerary card action normalization — source-scan contract tests.
 *
 * Guards the invariants from the action normalization slice:
 *
 *  1. ItineraryItemCard uses onUnplace (not onMoveToIdeas) for Move to Ideas.
 *  2. No standalone Move to Ideas button — it lives in the overflow/action menu.
 *  3. No source_kind / isConciergeIdea gate — all placed cards can expose the action.
 *  4. onUnplace is called with item.id AND current details (details preserved).
 *  5. TripBuilder no longer imports or calls moveIdeaToTripIdeas for this path.
 *  6. TripBuilder accepts onUnplace prop and passes it to ItineraryDayColumn.
 *  7. page.tsx wires handleItemUnplace into TripBuilder as onUnplace.
 *  8. Remove from trip requires two-step confirmation in ItineraryItemCard.
 *  9. Brief remains read-only (no onUnplace/onRemoveItem added to TripBrief).
 * 10. IdeasTray placement-only IA remains untouched (no jd-item-action-toggle).
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const itemCard = readFileSync(
  new URL("../src/components/trips/ItineraryItemCard.tsx", import.meta.url),
  "utf8",
);
const dayColumn = readFileSync(
  new URL("../src/components/trips/ItineraryDayColumn.tsx", import.meta.url),
  "utf8",
);
const tripBuilder = readFileSync(
  new URL("../src/components/trips/TripBuilder.tsx", import.meta.url),
  "utf8",
);
const page = readFileSync(
  new URL("../src/app/trips/[id]/page.tsx", import.meta.url),
  "utf8",
);
const brief = readFileSync(
  new URL("../src/components/trips/TripBrief.tsx", import.meta.url),
  "utf8",
);
const tray = readFileSync(
  new URL("../src/components/trips/IdeasTray.tsx", import.meta.url),
  "utf8",
);

// ── 1. onUnplace prop — new normalized interface ──────────────────────────────

test("ItineraryItemCard declares onUnplace prop (not onMoveToIdeas)", () => {
  assert.match(itemCard, /onUnplace\?/, "onUnplace prop must be declared");
  assert.doesNotMatch(
    itemCard,
    /onMoveToIdeas/,
    "onMoveToIdeas must not appear in ItineraryItemCard",
  );
});

// ── 2. No standalone Move to Ideas button ─────────────────────────────────────

test("ItineraryItemCard has no standalone always-visible Move to Ideas button", () => {
  assert.doesNotMatch(
    itemCard,
    /showMoveToIdeasAction/,
    "showMoveToIdeasAction standalone-button gate must be removed",
  );
  assert.doesNotMatch(
    itemCard,
    /isConciergeIdea/,
    "isConciergeIdea source_kind gate must be removed",
  );
});

test("Move to Ideas label exists in ItineraryItemCard action menu", () => {
  assert.match(itemCard, /Move to Ideas/, "Move to Ideas label must exist");
});

// ── 3. No source_kind gate — all placed cards can expose Move to Ideas ─────────

test("ItineraryItemCard does not gate Move to Ideas on source_kind", () => {
  assert.doesNotMatch(
    itemCard,
    /source_kind.*concierge_idea|concierge_idea.*source_kind/,
    "source_kind gate must not restrict Move to Ideas action",
  );
  assert.doesNotMatch(
    itemCard,
    /sourceKind.*concierge_idea|concierge_idea.*sourceKind/,
    "sourceKind gate must not restrict Move to Ideas action",
  );
});

// ── 4. onUnplace receives item.id and current details ────────────────────────

test("ItineraryItemCard calls onUnplace with item.id and details (details preserved)", () => {
  assert.match(
    itemCard,
    /onUnplace\(item\.id,\s*details\)/,
    "onUnplace must be called with item.id and details",
  );
});

// ── 5. TripBuilder no longer uses moveIdeaToTripIdeas for this action path ───

test("TripBuilder does not import moveIdeaToTripIdeas", () => {
  assert.doesNotMatch(
    tripBuilder,
    /moveIdeaToTripIdeas/,
    "TripBuilder must not import or call moveIdeaToTripIdeas for the itinerary-card action path",
  );
});

// ── 6. TripBuilder accepts onUnplace and passes it through ────────────────────

test("TripBuilder declares onUnplace prop in TripBuilderProps", () => {
  assert.match(
    tripBuilder,
    /onUnplace\?/,
    "TripBuilder must declare onUnplace prop",
  );
});

test("TripBuilder passes onUnplace to ItineraryDayColumn via handleMoveItemToIdeas", () => {
  assert.match(
    tripBuilder,
    /onMoveItemToIdeas=\{handleMoveItemToIdeas\}/,
    "TripBuilder must wire onMoveItemToIdeas to ItineraryDayColumn",
  );
  assert.match(
    tripBuilder,
    /onUnplace\b/,
    "TripBuilder handleMoveItemToIdeas must delegate to onUnplace",
  );
});

// ── 7. page.tsx wires handleItemUnplace into TripBuilder ──────────────────────

test("page.tsx passes handleItemUnplace to TripBuilder as onUnplace", () => {
  assert.match(
    page,
    /onUnplace=\{handleItemUnplace\}/,
    "page.tsx must wire handleItemUnplace as onUnplace to TripBuilder",
  );
});

// ── 8. Remove from trip is confirm-gated in ItineraryItemCard ─────────────────

test("ItineraryItemCard has confirmRemove state for two-step Remove confirm", () => {
  assert.match(
    itemCard,
    /confirmRemove/,
    "confirmRemove state must exist for confirm-gating Remove",
  );
});

test("ItineraryItemCard desktop Remove requires confirmation (itinerary-item-remove-confirm testid)", () => {
  assert.match(
    itemCard,
    /data-testid="itinerary-item-remove-confirm"/,
    "desktop confirm block must have data-testid",
  );
  assert.match(
    itemCard,
    /data-testid="itinerary-item-remove-confirm-yes"/,
    "desktop confirm-yes button must have data-testid",
  );
});

test("ItineraryItemCard mobile Remove requires confirmation (itinerary-item-mobile-remove-confirm testid)", () => {
  assert.match(
    itemCard,
    /data-testid="itinerary-item-mobile-remove-confirm"/,
    "mobile confirm block must have data-testid",
  );
  assert.match(
    itemCard,
    /data-testid="itinerary-item-mobile-remove-confirm-yes"/,
    "mobile confirm-yes button must have data-testid",
  );
});

test("ItineraryItemCard desktop Remove does not call onRemove directly on first click", () => {
  // Remove from trip in the desktop dropdown sets confirmRemove=true first, not onRemove
  assert.match(
    itemCard,
    /data-testid="itinerary-item-remove"[\s\S]*?setConfirmRemove\(true\)/,
    "desktop Remove must set confirmRemove=true, not call onRemove directly",
  );
});

// ── 9. Brief remains read-only ────────────────────────────────────────────────

test("TripBrief has no onUnplace or onRemoveItem handler (read-only)", () => {
  assert.doesNotMatch(
    brief,
    /onUnplace|onRemoveItem/,
    "TripBrief must remain read-only — no unplace or remove handlers",
  );
});

// ── 10. IdeasTray placement-only IA untouched ─────────────────────────────────

test("IdeasTray has no itinerary-card action-menu patterns (placement-only IA preserved)", () => {
  assert.doesNotMatch(
    tray,
    /jd-item-action-toggle|itinerary-item-desktop-overflow/,
    "IdeasTray must not have itinerary-card overflow toggle",
  );
  assert.doesNotMatch(
    tray,
    /itinerary-item-remove-confirm/,
    "IdeasTray must not have itinerary-card remove-confirm pattern",
  );
});

// ── ItineraryDayColumn signature update ──────────────────────────────────────

test("ItineraryDayColumn onMoveItemToIdeas uses currentDetails signature (not dayId)", () => {
  assert.match(
    dayColumn,
    /onMoveItemToIdeas\?.*currentDetails/,
    "onMoveItemToIdeas must carry currentDetails in the signature",
  );
  assert.match(
    dayColumn,
    /onUnplace=\{onMoveItemToIdeas\}/,
    "ItineraryItemCard must receive onUnplace mapped from onMoveItemToIdeas",
  );
});

test("ItineraryDayColumn does not call moveIdeaToTripIdeas (it was only in TripBuilder)", () => {
  assert.doesNotMatch(
    dayColumn,
    /moveIdeaToTripIdeas/,
    "ItineraryDayColumn must never call moveIdeaToTripIdeas",
  );
});
