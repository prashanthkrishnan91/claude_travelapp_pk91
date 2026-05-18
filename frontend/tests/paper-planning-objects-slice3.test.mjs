/**
 * Stage 3.5 Slice 3 — Paper Planning Objects contract tests.
 *
 * Verifies:
 *  1.  ItineraryItemCard uses folio-paper-item for card surface.
 *  2.  ItineraryItemCard uses border-ds-hairline for card border.
 *  3.  ItineraryItemCard uses text-ds-folio-ink for title typography.
 *  4.  ItineraryItemCard uses text-ds-folio-ink-mist for secondary content.
 *  5.  ItineraryItemCard focus rings use focus-visible:outline-ds-marine-ink.
 *  6.  ItineraryItemCard does NOT use bg-ds-onyx (dark surface removed).
 *  7.  ItineraryItemCard does NOT use border-ds-pen-stroke (dark border removed).
 *  8.  ItineraryItemCard does NOT use text-ds-accent (gold accent removed from card).
 *  9.  ItineraryItemCard protected round-trip markers remain (data-testid="itinerary-roundtrip-flight").
 * 10.  ItineraryItemCard protected leg_of_round_trip logic remains.
 * 11.  ItineraryItemCard protected addRoundTripLegToDay reference remains.
 * 12.  TripBuilderForm uses folio-paper-panel on form element.
 * 13.  TripBuilderForm uses folio-paper-card on loading state card.
 * 14.  TripBuilderForm uses atelier-transition on outer wrappers.
 * 15.  TripBuilderForm uses btn-marine for primary submit button.
 * 16.  TripBuilderForm uses text-ds-folio-ink-mist for muted text.
 * 17.  TripBuilderForm does NOT use bg-ds-onyx (dark surface removed).
 * 18.  TripBuilderForm does NOT use boutique-folio (dark panel removed).
 * 19.  TripBuilderForm does NOT use editorial-scene (dark wrapper removed).
 * 20.  OptimizeTripModal uses folio-paper-panel for modal shell.
 * 21.  OptimizeTripModal uses folio-paper-header for header zone.
 * 22.  OptimizeTripModal uses bg-ds-bone for result cards.
 * 23.  OptimizeTripModal uses border-ds-marine-ink for primary rank border.
 * 24.  OptimizeTripModal uses btn-marine for select button.
 * 25.  OptimizeTripModal uses btn-folio-ghost for secondary actions.
 * 26.  OptimizeTripModal uses text-ds-marine-ink for accent elements.
 * 27.  OptimizeTripModal does NOT use advisor-desk-panel (dark shell removed).
 * 28.  OptimizeTripModal does NOT use concierge-desk-header (dark header removed).
 * 29.  OptimizeTripModal does NOT use bg-ds-onyx (dark surface removed).
 * 30.  OptimizeTripModal does NOT use boutique-instrument or boutique-folio.
 * 31.  DayPlanModal uses folio-paper-panel for modal shell.
 * 32.  DayPlanModal uses folio-paper-header for header zone.
 * 33.  DayPlanModal uses border-ds-hairline for card borders.
 * 34.  DayPlanModal uses bg-ds-marine-ink for add buttons.
 * 35.  DayPlanModal uses btn-marine for Accept All CTA.
 * 36.  DayPlanModal uses btn-folio-ghost for close button.
 * 37.  DayPlanModal uses text-ds-marine-ink for dining meal labels.
 * 38.  DayPlanModal does NOT use advisor-desk-panel (dark shell removed).
 * 39.  DayPlanModal does NOT use concierge-desk-header (dark header removed).
 * 40.  DayPlanModal does NOT use border-ds-pen-stroke (dark border removed).
 * 41.  No text-ds-warm-paper appears in any touched file (invalid token).
 * 42.  No text-ds-accent appears in ItineraryItemCard (removed from paper card).
 * 43.  DayPlanModal handleAcceptAll behavior preserved.
 * 44.  DayPlanModal handleAdd behavior preserved.
 * 45.  OptimizeTripModal handleSelect behavior preserved.
 * 46.  ItineraryItemCard round-trip section testid preserved.
 */

import { describe, it, test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root    = resolve(__dirname, "..");
const srcRoot = resolve(root, "src");

function readSrc(relPath) {
  return readFileSync(resolve(srcRoot, relPath), "utf8");
}

const itineraryCard  = readSrc("components/trips/ItineraryItemCard.tsx");
const tripBuilder    = readSrc("components/trips/TripBuilderForm.tsx");
const optimizeModal  = readSrc("components/trips/OptimizeTripModal.tsx");
const dayPlanModal   = readSrc("components/trips/DayPlanModal.tsx");

// ── ItineraryItemCard — paper surface ─────────────────────────────────────────

describe("Slice 3: ItineraryItemCard paper surface", () => {
  it("1. uses folio-paper-item for card surface", () => {
    assert.ok(itineraryCard.includes("folio-paper-item"), "ItineraryItemCard must use folio-paper-item paper card class");
  });

  it("2. uses border-ds-hairline for card border", () => {
    assert.ok(itineraryCard.includes("border-ds-hairline"), "ItineraryItemCard must use border-ds-hairline paper border");
  });

  it("3. uses text-ds-folio-ink for title typography", () => {
    assert.ok(itineraryCard.includes("text-ds-folio-ink"), "ItineraryItemCard must use text-ds-folio-ink for title text");
  });

  it("4. uses text-ds-folio-ink-mist for secondary content", () => {
    assert.ok(itineraryCard.includes("text-ds-folio-ink-mist"), "ItineraryItemCard must use text-ds-folio-ink-mist for muted content");
  });

  it("5. focus rings use focus-visible:outline-ds-marine-ink", () => {
    assert.ok(itineraryCard.includes("focus-visible:outline-ds-marine-ink"), "ItineraryItemCard focus rings must use ds-marine-ink");
  });

  it("6. does NOT use bg-ds-onyx (dark surface removed)", () => {
    assert.ok(!itineraryCard.includes("bg-ds-onyx"), "ItineraryItemCard must not use bg-ds-onyx after Slice 3 conversion");
  });

  it("7. does NOT use border-ds-pen-stroke (dark border removed)", () => {
    assert.ok(!itineraryCard.includes("border-ds-pen-stroke"), "ItineraryItemCard must not use border-ds-pen-stroke after Slice 3 conversion");
  });

  it("8. does NOT use text-ds-accent on card elements (removed)", () => {
    assert.ok(!itineraryCard.includes("text-ds-accent"), "ItineraryItemCard must not use text-ds-accent after Slice 3 conversion");
  });
});

// ── ItineraryItemCard — protected round-trip logic ────────────────────────────

describe("Slice 3: ItineraryItemCard protected round-trip logic preserved", () => {
  it("9. round-trip section testid preserved", () => {
    assert.ok(itineraryCard.includes('data-testid="itinerary-roundtrip-flight"'), "round-trip testid must be preserved — protected from modification");
  });

  it("10. leg_of_round_trip logic preserved", () => {
    assert.ok(itineraryCard.includes("leg_of_round_trip"), "leg_of_round_trip logic must be preserved — protected from modification");
  });

  it("11. isExplicitlyOneWay detection logic preserved", () => {
    assert.ok(itineraryCard.includes("isExplicitlyOneWay"), "isExplicitlyOneWay detection must be preserved — protected from modification");
  });
});

// ── TripBuilderForm — paper surface ──────────────────────────────────────────

describe("Slice 3: TripBuilderForm paper surface", () => {
  it("12. uses folio-paper-panel on form element", () => {
    assert.ok(tripBuilder.includes("folio-paper-panel"), "TripBuilderForm form must use folio-paper-panel paper panel class");
  });

  it("13. uses folio-paper-card on loading state card", () => {
    assert.ok(tripBuilder.includes("folio-paper-card"), "TripBuilderForm loading state must use folio-paper-card");
  });

  it("14. uses atelier-transition on outer wrappers", () => {
    assert.ok(tripBuilder.includes("atelier-transition"), "TripBuilderForm outer wrappers must use atelier-transition");
  });

  it("15. uses btn-marine for primary submit button", () => {
    assert.ok(tripBuilder.includes("btn-marine"), "TripBuilderForm submit must use btn-marine paper-world CTA");
  });

  it("16. uses text-ds-folio-ink-mist for muted text", () => {
    assert.ok(tripBuilder.includes("text-ds-folio-ink-mist"), "TripBuilderForm muted text must use text-ds-folio-ink-mist");
  });

  it("17. does NOT use bg-ds-onyx (dark surface removed)", () => {
    assert.ok(!tripBuilder.includes("bg-ds-onyx"), "TripBuilderForm must not use bg-ds-onyx after Slice 3 conversion");
  });

  it("18. does NOT use boutique-folio (dark panel removed)", () => {
    assert.ok(!tripBuilder.includes("boutique-folio"), "TripBuilderForm must not use boutique-folio after Slice 3 conversion");
  });

  it("19. does NOT use editorial-scene (dark wrapper removed)", () => {
    assert.ok(!tripBuilder.includes("editorial-scene"), "TripBuilderForm must not use editorial-scene after Slice 3 conversion");
  });
});

// ── OptimizeTripModal — paper planning sheet ──────────────────────────────────

describe("Slice 3: OptimizeTripModal paper planning sheet", () => {
  it("20. uses folio-paper-panel for modal shell", () => {
    assert.ok(optimizeModal.includes("folio-paper-panel"), "OptimizeTripModal shell must use folio-paper-panel");
  });

  it("21. uses folio-paper-header for header zone", () => {
    assert.ok(optimizeModal.includes("folio-paper-header"), "OptimizeTripModal header must use folio-paper-header");
  });

  it("22. uses bg-ds-bone for result cards", () => {
    assert.ok(optimizeModal.includes("bg-ds-bone"), "OptimizeTripModal result cards must use bg-ds-bone paper surface");
  });

  it("23. uses border-ds-marine-ink for primary rank border", () => {
    assert.ok(optimizeModal.includes("border-ds-marine-ink"), "OptimizeTripModal RANK_BORDER[0] must use border-ds-marine-ink");
  });

  it("24. uses btn-marine for select button", () => {
    assert.ok(optimizeModal.includes("btn-marine"), "OptimizeTripModal select button must use btn-marine paper CTA");
  });

  it("25. uses btn-folio-ghost for secondary actions", () => {
    assert.ok(optimizeModal.includes("btn-folio-ghost"), "OptimizeTripModal secondary buttons must use btn-folio-ghost");
  });

  it("26. uses text-ds-marine-ink for accent elements", () => {
    assert.ok(optimizeModal.includes("text-ds-marine-ink"), "OptimizeTripModal accent elements must use text-ds-marine-ink");
  });

  it("27. does NOT use advisor-desk-panel (dark shell removed)", () => {
    assert.ok(!optimizeModal.includes("advisor-desk-panel"), "OptimizeTripModal must not use advisor-desk-panel after Slice 3");
  });

  it("28. does NOT use concierge-desk-header (dark header removed)", () => {
    assert.ok(!optimizeModal.includes("concierge-desk-header"), "OptimizeTripModal must not use concierge-desk-header after Slice 3");
  });

  it("29. does NOT use bg-ds-onyx (dark surface removed)", () => {
    assert.ok(!optimizeModal.includes("bg-ds-onyx"), "OptimizeTripModal must not use bg-ds-onyx after Slice 3");
  });

  it("30. does NOT use boutique-instrument or boutique-folio (dark shadows removed)", () => {
    assert.ok(!optimizeModal.includes("boutique-instrument"), "OptimizeTripModal must not use boutique-instrument after Slice 3");
    assert.ok(!optimizeModal.includes("boutique-folio"), "OptimizeTripModal must not use boutique-folio after Slice 3");
  });
});

// ── DayPlanModal — paper planning sheet ──────────────────────────────────────

describe("Slice 3: DayPlanModal paper planning sheet", () => {
  it("31. uses folio-paper-panel for modal shell", () => {
    assert.ok(dayPlanModal.includes("folio-paper-panel"), "DayPlanModal shell must use folio-paper-panel");
  });

  it("32. uses folio-paper-header for header zone", () => {
    assert.ok(dayPlanModal.includes("folio-paper-header"), "DayPlanModal header must use folio-paper-header");
  });

  it("33. uses border-ds-hairline for card borders", () => {
    assert.ok(dayPlanModal.includes("border-ds-hairline"), "DayPlanModal cards must use border-ds-hairline paper borders");
  });

  it("34. uses bg-ds-marine-ink for add buttons", () => {
    assert.ok(dayPlanModal.includes("bg-ds-marine-ink"), "DayPlanModal add buttons must use bg-ds-marine-ink");
  });

  it("35. uses btn-marine for Accept All CTA", () => {
    assert.ok(dayPlanModal.includes("btn-marine"), "DayPlanModal Accept All must use btn-marine paper CTA");
  });

  it("36. uses btn-folio-ghost for close button", () => {
    assert.ok(dayPlanModal.includes("btn-folio-ghost"), "DayPlanModal close/done must use btn-folio-ghost");
  });

  it("37. uses text-ds-marine-ink for dining meal labels", () => {
    assert.ok(dayPlanModal.includes("text-ds-marine-ink"), "DayPlanModal dining labels must use text-ds-marine-ink");
  });

  it("38. does NOT use advisor-desk-panel (dark shell removed)", () => {
    assert.ok(!dayPlanModal.includes("advisor-desk-panel"), "DayPlanModal must not use advisor-desk-panel after Slice 3");
  });

  it("39. does NOT use concierge-desk-header (dark header removed)", () => {
    assert.ok(!dayPlanModal.includes("concierge-desk-header"), "DayPlanModal must not use concierge-desk-header after Slice 3");
  });

  it("40. does NOT use border-ds-pen-stroke (dark border removed)", () => {
    assert.ok(!dayPlanModal.includes("border-ds-pen-stroke"), "DayPlanModal must not use border-ds-pen-stroke after Slice 3");
  });
});

// ── Cross-file invariants ─────────────────────────────────────────────────────

describe("Slice 3: Cross-file invariants", () => {
  it("41. no text-ds-warm-paper in any touched file (invalid token)", () => {
    assert.ok(!itineraryCard.includes("text-ds-warm-paper"), "ItineraryItemCard must not use invalid text-ds-warm-paper token");
    assert.ok(!tripBuilder.includes("text-ds-warm-paper"), "TripBuilderForm must not use invalid text-ds-warm-paper token");
    assert.ok(!optimizeModal.includes("text-ds-warm-paper"), "OptimizeTripModal must not use invalid text-ds-warm-paper token");
    assert.ok(!dayPlanModal.includes("text-ds-warm-paper"), "DayPlanModal must not use invalid text-ds-warm-paper token");
  });

  it("42. no text-ds-accent in ItineraryItemCard (paper card uses marine-ink)", () => {
    assert.ok(!itineraryCard.includes("text-ds-accent"), "ItineraryItemCard must not use text-ds-accent — paper world uses marine-ink");
  });
});

// ── Behavior preservation ─────────────────────────────────────────────────────

describe("Slice 3: Behavior preservation", () => {
  it("43. DayPlanModal handleAcceptAll behavior preserved", () => {
    assert.ok(dayPlanModal.includes("async function handleAcceptAll"), "DayPlanModal handleAcceptAll must be preserved");
  });

  it("44. DayPlanModal handleAdd behavior preserved", () => {
    assert.ok(dayPlanModal.includes("async function handleAdd"), "DayPlanModal handleAdd must be preserved");
  });

  it("45. OptimizeTripModal handleSelect behavior preserved", () => {
    assert.ok(optimizeModal.includes("async function handleSelect"), "OptimizeTripModal handleSelect must be preserved");
  });

  it("46. ItineraryItemCard round-trip section testid preserved", () => {
    assert.ok(itineraryCard.includes('data-testid="itinerary-roundtrip-flight"'), "round-trip testid must survive the paper conversion");
  });
});
