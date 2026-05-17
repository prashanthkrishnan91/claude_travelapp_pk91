/**
 * Phase 8N-D — Old-Format Modal + Overlay Surface Rescue contract tests.
 *
 * Verifies:
 *  1.  OptimizeTripModal does not use bg-white as the modal shell class.
 *  2.  OptimizeTripModal uses advisor-desk-panel boutique shell.
 *  3.  OptimizeTripModal loading spinner uses text-ds-accent, not text-sky-*.
 *  4.  OptimizeTripModal loading state does not use old text-sky-4 class.
 *  5.  OptimizeTripModal error state uses text-ds-warning on AlertCircle.
 *  6.  OptimizeTripModal error state uses btn-primary for retry (not bg-sky-*).
 *  7.  OptimizeTripModal provider unavailable uses text-ds-caution (not text-amber-5).
 *  8.  OptimizeTripModal provider unavailable uses text-ds-text for title.
 *  9.  OptimizeTripModal provider unavailable uses btn-ghost (not bg-slate-900).
 * 10.  OptimizeTripModal result cards use bg-ds-onyx (not old bg-white/light surfaces).
 * 11.  OptimizeTripModal result cards use boutique-instrument/boutique-folio.
 * 12.  OptimizeTripModal rank badge uses bg-ds-carbon (not bg-emerald-100/bg-sky-100).
 * 13.  OptimizeTripModal RANK_BORDER uses border-ds-* tokens (not border-emerald-400).
 * 14.  OptimizeTripModal does not use RANK_BANNER light backgrounds (bg-emerald-50/bg-sky-50).
 * 15.  OptimizeTripModal scoreColor returns ds-trust/caution/tertiary (not emerald-6/amber-6).
 * 16.  OptimizeTripModal flight section uses text-ds-accent icon (not text-sky-5).
 * 17.  OptimizeTripModal hotel section uses text-ds-accent-muted (not text-violet-5).
 * 18.  OptimizeTripModal dividers use bg-ds-pen-stroke (not bg-slate-100).
 * 19.  OptimizeTripModal score breakdown cells use bg-ds-carbon (not bg-slate-50).
 * 20.  OptimizeTripModal select button uses btn-primary (not bg-sky-600).
 * 21.  OptimizeTripModal selected state uses bg-ds-carbon text-ds-trust (not bg-emerald-100).
 * 22.  OptimizeTripModal view details button uses btn-ghost (not border-slate-200).
 * 23.  OptimizeTripModal header uses concierge-desk-header zone.
 * 24.  OptimizeTripModal close button has min-h-[44px] touch target.
 * 25.  OptimizeTripModal close button has aria-label for accessibility.
 * 26.  OptimizeTripModal header uses text-ds-accent on Sparkles icon.
 * 27.  OptimizeTripModal optimize-provider-unavailable testid preserved.
 * 28.  DayPlanModal does not use bg-white as modal shell class.
 * 29.  DayPlanModal uses advisor-desk-panel boutique shell.
 * 30.  DayPlanModal uses concierge-desk-header for header zone.
 * 31.  DayPlanModal close button has min-h-[44px] touch target.
 * 32.  DayPlanModal close button has aria-label for accessibility.
 * 33.  DayPlanModal attraction cards use bg-ds-carbon (not bg-slate-50/40).
 * 34.  DayPlanModal attraction cards use border-ds-pen-stroke (not border-slate-100).
 * 35.  DayPlanModal add buttons use bg-ds-accent (not bg-emerald-600).
 * 36.  DayPlanModal add buttons do not use bg-rose-600.
 * 37.  DayPlanModal added state uses text-ds-trust (not text-emerald-700).
 * 38.  DayPlanModal added state does not use bg-emerald-100 or bg-rose-100.
 * 39.  DayPlanModal dining label uses text-ds-accent (not text-rose-5).
 * 40.  DayPlanModal dining section icon uses text-ds-accent-muted (not text-rose-5).
 * 41.  DayPlanModal rating star uses fill-ds-caution (not fill-amber-400).
 * 42.  DayPlanModal footer border uses border-ds-pen-stroke (not border-slate-100).
 * 43.  DayPlanModal header text uses text-ds-text (not text-slate-9).
 * 44.  DayPlanModal Sparkles icon uses text-ds-accent (not text-amber-5).
 * 45.  DayPlanModal description text uses text-ds-text-tertiary (not text-slate-4).
 * 46.  Behavior: OptimizeTripModal handleSelect function preserved.
 * 47.  Behavior: OptimizeTripModal run function preserved.
 * 48.  Behavior: DayPlanModal handleAcceptAll function preserved.
 * 49.  Behavior: DayPlanModal handleAdd function preserved.
 * 50.  Behavior: DayPlanModal onAddAttraction call preserved.
 * 51.  Behavior: DayPlanModal onAddRestaurant call preserved.
 * 52.  Behavior: OptimizeTripModal onClose preserved.
 * 53.  Behavior: OptimizeTripModal onPlanSelected preserved.
 * 54.  No backend/provider/API imports in OptimizeTripModal (existing list unchanged).
 * 55.  No new npm packages in package.json.
 * 56.  OptimizeTripModal optimize-trip-modal testid present.
 * 57.  DayPlanModal day-plan-modal testid present.
 * 58.  OptimizeTripModal optimize-loading-state testid present.
 * 59.  OptimizeTripModal optimize-error-state testid present.
 * 60.  OptimizeTripModal optimize-results testid present.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root      = resolve(__dirname, "..");
const srcRoot   = resolve(root, "src");

function readSrc(relPath) {
  return readFileSync(resolve(srcRoot, relPath), "utf8");
}
function readRoot(relPath) {
  return readFileSync(resolve(root, relPath), "utf8");
}

const optimizeModal = readSrc("components/trips/OptimizeTripModal.tsx");
const dayPlanModal  = readSrc("components/trips/DayPlanModal.tsx");
const packageJson   = readRoot("package.json");

// ── 1–27. OptimizeTripModal visual rescue ─────────────────────────────────────

describe("Phase 8N-D: OptimizeTripModal visual rescue", () => {
  it("1. OptimizeTripModal does not use bg-white as modal shell", () => {
    assert.ok(
      !optimizeModal.includes("bg-white"),
      "OptimizeTripModal must not use bg-white — modal shell must be boutique dark surface"
    );
  });

  it("2. OptimizeTripModal uses advisor-desk-panel boutique shell", () => {
    assert.ok(
      optimizeModal.includes("advisor-desk-panel"),
      "OptimizeTripModal must use advisor-desk-panel for the boutique modal shell"
    );
  });

  it("3. OptimizeTripModal loading spinner uses text-ds-accent (atelier gold)", () => {
    assert.ok(
      optimizeModal.includes("text-ds-accent animate-spin"),
      "OptimizeTripModal loading spinner must use text-ds-accent animate-spin"
    );
  });

  it("4. OptimizeTripModal loading state does not use old sky-blue spinner", () => {
    assert.ok(
      !optimizeModal.includes("text-sky-4"),
      "OptimizeTripModal must not use text-sky-4* for the loading spinner"
    );
  });

  it("5. OptimizeTripModal error state uses text-ds-warning on AlertCircle", () => {
    assert.ok(
      optimizeModal.includes("text-ds-warning"),
      "OptimizeTripModal error state must use text-ds-warning for AlertCircle"
    );
  });

  it("6. OptimizeTripModal error state uses btn-primary for retry (not bg-sky-*)", () => {
    assert.ok(
      !optimizeModal.includes("bg-sky-6"),
      "OptimizeTripModal must not use bg-sky-6* — use btn-primary for retry action"
    );
  });

  it("7. OptimizeTripModal provider unavailable uses text-ds-caution", () => {
    assert.ok(
      optimizeModal.includes("text-ds-caution"),
      "OptimizeTripModal provider unavailable must use text-ds-caution for warning icon"
    );
  });

  it("8. OptimizeTripModal provider unavailable title uses text-ds-text", () => {
    // text-ds-text appears in the provider unavailable section title
    assert.ok(
      optimizeModal.includes("text-ds-text"),
      "OptimizeTripModal must use text-ds-text for provider unavailable title"
    );
  });

  it("9. OptimizeTripModal provider unavailable uses btn-ghost (not bg-slate-900)", () => {
    assert.ok(
      !optimizeModal.includes("bg-slate-900"),
      "OptimizeTripModal provider unavailable must not use bg-slate-900 — use btn-ghost"
    );
    assert.ok(
      optimizeModal.includes("btn-ghost"),
      "OptimizeTripModal provider unavailable must use btn-ghost for the dismiss action"
    );
  });

  it("10. OptimizeTripModal result cards use bg-ds-onyx (not light surfaces)", () => {
    assert.ok(
      optimizeModal.includes("bg-ds-onyx"),
      "OptimizeTripModal result cards must use bg-ds-onyx (dark atelier surface)"
    );
  });

  it("11. OptimizeTripModal result cards use boutique shadow classes", () => {
    assert.ok(
      optimizeModal.includes("boutique-instrument"),
      "OptimizeTripModal result cards must include boutique-instrument shadow class"
    );
    assert.ok(
      optimizeModal.includes("boutique-folio"),
      "OptimizeTripModal result cards must include boutique-folio shadow class"
    );
  });

  it("12. OptimizeTripModal rank badge uses bg-ds-carbon (not bg-emerald-100/bg-sky-100)", () => {
    assert.ok(
      !optimizeModal.includes("bg-emerald-100"),
      "OptimizeTripModal RANK_BADGE must not use bg-emerald-100"
    );
    assert.ok(
      !optimizeModal.includes("bg-sky-100"),
      "OptimizeTripModal RANK_BADGE must not use bg-sky-100"
    );
    assert.ok(
      !optimizeModal.includes("bg-amber-100"),
      "OptimizeTripModal RANK_BADGE must not use bg-amber-100"
    );
    assert.ok(
      optimizeModal.includes("bg-ds-carbon"),
      "OptimizeTripModal rank badge must use bg-ds-carbon"
    );
  });

  it("13. OptimizeTripModal RANK_BORDER uses border-ds-* tokens (not border-emerald-400)", () => {
    assert.ok(
      !optimizeModal.includes("border-emerald-400"),
      "OptimizeTripModal must not use border-emerald-400"
    );
    assert.ok(
      !optimizeModal.includes("border-sky-300"),
      "OptimizeTripModal must not use border-sky-300"
    );
    assert.ok(
      !optimizeModal.includes("border-amber-300"),
      "OptimizeTripModal must not use border-amber-300"
    );
    assert.ok(
      optimizeModal.includes("border-ds-accent"),
      "OptimizeTripModal RANK_BORDER[0] must use border-ds-accent for primary card"
    );
  });

  it("14. OptimizeTripModal does not use old light rank banner backgrounds", () => {
    assert.ok(
      !optimizeModal.includes("bg-emerald-50"),
      "OptimizeTripModal must not use bg-emerald-50 for rank banners"
    );
    assert.ok(
      !optimizeModal.includes("bg-sky-50"),
      "OptimizeTripModal must not use bg-sky-50 for rank banners"
    );
    assert.ok(
      !optimizeModal.includes("bg-amber-50"),
      "OptimizeTripModal must not use bg-amber-50 for rank banners"
    );
  });

  it("15. OptimizeTripModal scoreColor returns ds tokens (not emerald-6/amber-6/slate-4)", () => {
    assert.ok(
      optimizeModal.includes("text-ds-trust"),
      "scoreColor must return text-ds-trust for high scores"
    );
    // text-ds-caution already verified in test 7, reuse here for scoreColor
    assert.ok(
      !optimizeModal.includes("text-emerald-6"),
      "scoreColor must not return text-emerald-6*"
    );
    assert.ok(
      !optimizeModal.includes("text-slate-400"),
      "scoreColor must not return text-slate-400"
    );
  });

  it("16. OptimizeTripModal flight section uses text-ds-accent icon (not text-sky-5)", () => {
    assert.ok(
      !optimizeModal.includes("text-sky-5"),
      "OptimizeTripModal flight Plane icon must not use text-sky-5*"
    );
  });

  it("17. OptimizeTripModal hotel section uses text-ds-accent-muted (not text-violet-5)", () => {
    assert.ok(
      !optimizeModal.includes("text-violet-5"),
      "OptimizeTripModal hotel Building2 icon must not use text-violet-5*"
    );
    assert.ok(
      optimizeModal.includes("text-ds-accent-muted"),
      "OptimizeTripModal hotel icon must use text-ds-accent-muted"
    );
  });

  it("18. OptimizeTripModal dividers use bg-ds-pen-stroke (not bg-slate-100)", () => {
    assert.ok(
      !optimizeModal.includes("bg-slate-100"),
      "OptimizeTripModal dividers must not use bg-slate-100"
    );
    assert.ok(
      optimizeModal.includes("bg-ds-pen-stroke"),
      "OptimizeTripModal dividers must use bg-ds-pen-stroke"
    );
  });

  it("19. OptimizeTripModal score breakdown cells use bg-ds-carbon (not bg-slate-50)", () => {
    assert.ok(
      !optimizeModal.includes("bg-slate-50"),
      "OptimizeTripModal score breakdown must not use bg-slate-50"
    );
    // bg-ds-carbon checked in test 12
  });

  it("20. OptimizeTripModal select button uses btn-primary (not bg-sky-600)", () => {
    assert.ok(
      !optimizeModal.includes("bg-sky-600"),
      "OptimizeTripModal select button must not use bg-sky-600"
    );
    assert.ok(
      optimizeModal.includes("btn-primary"),
      "OptimizeTripModal select button must use btn-primary"
    );
  });

  it("21. OptimizeTripModal selected state uses bg-ds-carbon text-ds-trust (not bg-emerald-100)", () => {
    assert.ok(
      optimizeModal.includes("text-ds-trust"),
      "OptimizeTripModal selected state must use text-ds-trust"
    );
  });

  it("22. OptimizeTripModal view details button uses btn-ghost (not border-slate-200)", () => {
    assert.ok(
      !optimizeModal.includes("border-slate-200"),
      "OptimizeTripModal view details button must not use border-slate-200"
    );
    // btn-ghost already checked in test 9
  });

  it("23. OptimizeTripModal header uses concierge-desk-header zone", () => {
    assert.ok(
      optimizeModal.includes("concierge-desk-header"),
      "OptimizeTripModal header must use concierge-desk-header for two-zone interior"
    );
  });

  it("24. OptimizeTripModal close button has min-h-[44px] touch target", () => {
    assert.ok(
      optimizeModal.includes("min-h-[44px]"),
      "OptimizeTripModal close button must have min-h-[44px] touch target"
    );
  });

  it("25. OptimizeTripModal close button has aria-label", () => {
    assert.ok(
      optimizeModal.includes('aria-label="Close optimize modal"'),
      "OptimizeTripModal close button must have aria-label for accessibility"
    );
  });

  it("26. OptimizeTripModal header Sparkles uses text-ds-accent", () => {
    assert.ok(
      optimizeModal.includes("text-ds-accent"),
      "OptimizeTripModal Sparkles icon must use text-ds-accent"
    );
  });

  it("27. OptimizeTripModal optimize-provider-unavailable testid preserved", () => {
    assert.ok(
      optimizeModal.includes('data-testid="optimize-provider-unavailable"'),
      "OptimizeTripModal must preserve optimize-provider-unavailable testid"
    );
  });
});

// ── 28–45. DayPlanModal visual rescue ─────────────────────────────────────────

describe("Phase 8N-D: DayPlanModal visual rescue", () => {
  it("28. DayPlanModal does not use bg-white as modal shell", () => {
    assert.ok(
      !dayPlanModal.includes("bg-white"),
      "DayPlanModal must not use bg-white — modal shell must be boutique dark surface"
    );
  });

  it("29. DayPlanModal uses advisor-desk-panel boutique shell", () => {
    assert.ok(
      dayPlanModal.includes("advisor-desk-panel"),
      "DayPlanModal must use advisor-desk-panel for the boutique modal shell"
    );
  });

  it("30. DayPlanModal uses concierge-desk-header for header zone", () => {
    assert.ok(
      dayPlanModal.includes("concierge-desk-header"),
      "DayPlanModal must use concierge-desk-header for two-zone header interior"
    );
  });

  it("31. DayPlanModal close button has min-h-[44px] touch target", () => {
    assert.ok(
      dayPlanModal.includes("min-h-[44px]"),
      "DayPlanModal close button must have min-h-[44px] touch target"
    );
  });

  it("32. DayPlanModal close button has aria-label", () => {
    assert.ok(
      dayPlanModal.includes('aria-label="Close day plan"'),
      "DayPlanModal close button must have aria-label for accessibility"
    );
  });

  it("33. DayPlanModal attraction cards use bg-ds-carbon (not bg-slate-50/40)", () => {
    assert.ok(
      !dayPlanModal.includes("bg-slate-50/40"),
      "DayPlanModal attraction cards must not use bg-slate-50/40"
    );
    assert.ok(
      dayPlanModal.includes("bg-ds-carbon"),
      "DayPlanModal attraction cards must use bg-ds-carbon for default state"
    );
  });

  it("34. DayPlanModal attraction cards use border-ds-pen-stroke (not border-slate-100)", () => {
    assert.ok(
      !dayPlanModal.includes("border-slate-100"),
      "DayPlanModal cards must not use border-slate-100"
    );
    assert.ok(
      dayPlanModal.includes("border-ds-pen-stroke"),
      "DayPlanModal cards must use border-ds-pen-stroke"
    );
  });

  it("35. DayPlanModal add buttons use bg-ds-accent (not bg-emerald-600)", () => {
    assert.ok(
      !dayPlanModal.includes("bg-emerald-600"),
      "DayPlanModal add buttons must not use bg-emerald-600"
    );
    assert.ok(
      dayPlanModal.includes("bg-ds-accent"),
      "DayPlanModal add buttons must use bg-ds-accent"
    );
  });

  it("36. DayPlanModal add buttons do not use bg-rose-600", () => {
    assert.ok(
      !dayPlanModal.includes("bg-rose-600"),
      "DayPlanModal dining add buttons must not use bg-rose-600"
    );
  });

  it("37. DayPlanModal added state uses text-ds-trust (not text-emerald-700)", () => {
    assert.ok(
      !dayPlanModal.includes("text-emerald-700"),
      "DayPlanModal added state must not use text-emerald-700"
    );
    assert.ok(
      dayPlanModal.includes("text-ds-trust"),
      "DayPlanModal added state must use text-ds-trust"
    );
  });

  it("38. DayPlanModal added state does not use bg-emerald-100 or bg-rose-100", () => {
    assert.ok(
      !dayPlanModal.includes("bg-emerald-100"),
      "DayPlanModal must not use bg-emerald-100 for added state"
    );
    assert.ok(
      !dayPlanModal.includes("bg-rose-100"),
      "DayPlanModal must not use bg-rose-100 for added state"
    );
  });

  it("39. DayPlanModal dining meal label uses text-ds-accent (not text-rose-5)", () => {
    assert.ok(
      !dayPlanModal.includes("text-rose-500"),
      "DayPlanModal dining label must not use text-rose-500"
    );
    assert.ok(
      dayPlanModal.includes("text-ds-accent"),
      "DayPlanModal dining label must use text-ds-accent"
    );
  });

  it("40. DayPlanModal dining section icon uses text-ds-accent-muted (not text-rose-5)", () => {
    assert.ok(
      dayPlanModal.includes("text-ds-accent-muted"),
      "DayPlanModal UtensilsCrossed icon must use text-ds-accent-muted"
    );
  });

  it("41. DayPlanModal rating star uses fill-ds-caution (not fill-amber-400)", () => {
    assert.ok(
      !dayPlanModal.includes("fill-amber-400"),
      "DayPlanModal star rating must not use fill-amber-400"
    );
    assert.ok(
      dayPlanModal.includes("fill-ds-caution"),
      "DayPlanModal star rating must use fill-ds-caution"
    );
  });

  it("42. DayPlanModal footer border uses border-ds-pen-stroke (not border-slate-100)", () => {
    // border-slate-100 absence already verified in test 34
    // confirm border-ds-pen-stroke in footer area
    assert.ok(
      dayPlanModal.includes("border-t border-ds-pen-stroke"),
      "DayPlanModal footer must use border-t border-ds-pen-stroke"
    );
  });

  it("43. DayPlanModal header title uses text-ds-text (not text-slate-9)", () => {
    assert.ok(
      !dayPlanModal.includes("text-slate-900"),
      "DayPlanModal header must not use text-slate-900"
    );
    assert.ok(
      dayPlanModal.includes("text-ds-text"),
      "DayPlanModal header must use text-ds-text for title"
    );
  });

  it("44. DayPlanModal Sparkles header icon uses text-ds-accent (not text-amber-5)", () => {
    assert.ok(
      !dayPlanModal.includes("text-amber-500"),
      "DayPlanModal Sparkles icon must not use text-amber-500"
    );
    // text-ds-accent already checked in test 39
  });

  it("45. DayPlanModal description text uses text-ds-text-tertiary (not text-slate-4)", () => {
    assert.ok(
      !dayPlanModal.includes("text-slate-400"),
      "DayPlanModal description must not use text-slate-400"
    );
    assert.ok(
      dayPlanModal.includes("text-ds-text-tertiary"),
      "DayPlanModal description must use text-ds-text-tertiary"
    );
  });
});

// ── 46–53. Behavior preservation ─────────────────────────────────────────────

describe("Phase 8N-D: Behavior preservation — OptimizeTripModal", () => {
  it("46. OptimizeTripModal handleSelect function preserved", () => {
    assert.ok(
      optimizeModal.includes("async function handleSelect"),
      "OptimizeTripModal must preserve handleSelect function"
    );
  });

  it("47. OptimizeTripModal run function preserved", () => {
    assert.ok(
      optimizeModal.includes("const run = useCallback"),
      "OptimizeTripModal must preserve run useCallback function"
    );
  });

  it("52. OptimizeTripModal onClose prop preserved", () => {
    assert.ok(
      optimizeModal.includes("onClose"),
      "OptimizeTripModal must preserve onClose prop usage"
    );
  });

  it("53. OptimizeTripModal onPlanSelected prop preserved", () => {
    assert.ok(
      optimizeModal.includes("onPlanSelected"),
      "OptimizeTripModal must preserve onPlanSelected prop usage"
    );
  });
});

describe("Phase 8N-D: Behavior preservation — DayPlanModal", () => {
  it("48. DayPlanModal handleAcceptAll function preserved", () => {
    assert.ok(
      dayPlanModal.includes("async function handleAcceptAll"),
      "DayPlanModal must preserve handleAcceptAll function"
    );
  });

  it("49. DayPlanModal handleAdd function preserved", () => {
    assert.ok(
      dayPlanModal.includes("async function handleAdd"),
      "DayPlanModal must preserve handleAdd function"
    );
  });

  it("50. DayPlanModal onAddAttraction call preserved", () => {
    assert.ok(
      dayPlanModal.includes("onAddAttraction"),
      "DayPlanModal must preserve onAddAttraction usage"
    );
  });

  it("51. DayPlanModal onAddRestaurant call preserved", () => {
    assert.ok(
      dayPlanModal.includes("onAddRestaurant"),
      "DayPlanModal must preserve onAddRestaurant usage"
    );
  });
});

// ── 54–60. Safety invariants ──────────────────────────────────────────────────

describe("Phase 8N-D: Safety invariants", () => {
  it("54. OptimizeTripModal has no new backend imports (only lib/api)", () => {
    assert.ok(
      optimizeModal.includes('from "@/lib/api"'),
      "OptimizeTripModal must keep existing lib/api imports"
    );
    assert.ok(
      !optimizeModal.includes('from "@/lib/concierge"'),
      "OptimizeTripModal must not add concierge imports"
    );
  });

  it("55. No new npm packages in package.json", () => {
    // Verify package.json doesn't have newly added unusual packages
    // (we cannot check an exhaustive list, but verify no Framer Motion etc.)
    assert.ok(
      !packageJson.includes('"framer-motion"'),
      "package.json must not add framer-motion"
    );
  });

  it("56. OptimizeTripModal has optimize-trip-modal testid", () => {
    assert.ok(
      optimizeModal.includes('data-testid="optimize-trip-modal"'),
      "OptimizeTripModal must have data-testid='optimize-trip-modal'"
    );
  });

  it("57. DayPlanModal has day-plan-modal testid", () => {
    assert.ok(
      dayPlanModal.includes('data-testid="day-plan-modal"'),
      "DayPlanModal must have data-testid='day-plan-modal'"
    );
  });

  it("58. OptimizeTripModal has optimize-loading-state testid", () => {
    assert.ok(
      optimizeModal.includes('data-testid="optimize-loading-state"'),
      "OptimizeTripModal must have data-testid='optimize-loading-state'"
    );
  });

  it("59. OptimizeTripModal has optimize-error-state testid", () => {
    assert.ok(
      optimizeModal.includes('data-testid="optimize-error-state"'),
      "OptimizeTripModal must have data-testid='optimize-error-state'"
    );
  });

  it("60. OptimizeTripModal has optimize-results testid", () => {
    assert.ok(
      optimizeModal.includes('data-testid="optimize-results"'),
      "OptimizeTripModal must have data-testid='optimize-results'"
    );
  });
});
