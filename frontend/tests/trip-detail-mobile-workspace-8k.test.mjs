/**
 * Phase 8K — Trip Detail Mobile Workspace IA contract tests.
 *
 * Verifies:
 *  1. Four workspace tabs exist in the page source (Brief, Build, Itinerary, Ideas).
 *  2. Workspace tabs have stable data-testid values and type="button".
 *  3. Active workspace state drives mobile panel visibility (hidden/lg:block pattern).
 *  4. All four mobile panel testids exist in the correct source files.
 *  5. Desktop layout is NOT replaced — TripBuilder retains its multi-panel structure
 *     and uses lg: breakpoint overrides so panels are always visible at desktop width.
 *  6. Existing TripBuilder behaviour contracts are preserved (candidates, DnD, flights,
 *     hotels, compare, add-to-day, Google Flights CTA, TripIdeasPanel).
 *  7. AIConciergePanel contract is preserved (concierge panel testid, isOpen prop).
 *  8. Edit trip / delete trip modal contracts are preserved.
 *  9. No backend, provider, Supabase, or env files were changed.
 * 10. MobileWorkspace prop added to TripBuilder with correct type guard.
 * 11. Workspace switcher is mobile-only (lg:hidden) — desktop is unchanged.
 * 12. Touch-target minimums met on workspace tabs.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root      = resolve(__dirname, "..");
const srcRoot   = resolve(root, "src");
const backRoot  = resolve(root, "..", "backend");

function readSrc(relPath) {
  return readFileSync(resolve(srcRoot, relPath), "utf8");
}
function backExists(relPath) {
  return existsSync(resolve(backRoot, relPath));
}

const pageSrc          = readSrc("app/trips/[id]/page.tsx");
const tripBuilderSrc   = readSrc("components/trips/TripBuilder.tsx");
const tripIdeasSrc     = readSrc("components/trips/TripIdeasPanel.tsx");
const conciergePanelSrc = readSrc("components/trips/AIConciergePanel.tsx");

// ── 1. Four workspace tabs in page source ─────────────────────────────────────

describe("Phase 8K: workspace tabs exist in trip detail page", () => {
  it("Brief tab has data-testid trip-mobile-tab-brief", () => {
    assert.match(pageSrc, /trip-mobile-tab-brief/, "Brief tab testid must be present");
  });

  // Build is no longer a mobile tab — it was removed from the mobile nav in
  // #478 and is reached via the Add-to-Day handoff from the Itinerary tab.
  it("Build is not a mobile tab (reached via Add-to-Day handoff, PR #478)", () => {
    assert.doesNotMatch(pageSrc, /trip-mobile-tab-build/, "Build tab testid must not be present");
  });

  it("Itinerary tab has data-testid trip-mobile-tab-itinerary", () => {
    assert.match(pageSrc, /trip-mobile-tab-itinerary/, "Itinerary tab testid must be present");
  });

  it("Ideas tab has data-testid trip-mobile-tab-ideas", () => {
    assert.match(pageSrc, /trip-mobile-tab-ideas/, "Ideas tab testid must be present");
  });
});

// ── 2. Tab buttons have type="button" ────────────────────────────────────────

describe("Phase 8K: workspace tab buttons are type=button", () => {
  it("workspace tabs use type=button (not submit)", () => {
    // The switcher renders buttons with type="button"
    assert.match(pageSrc, /type="button"/, "Workspace tab buttons must have type=button");
  });

  it("WORKSPACE_TABS constant is defined with all four ids", () => {
    assert.match(pageSrc, /WORKSPACE_TABS/, "WORKSPACE_TABS constant must exist");
    assert.match(pageSrc, /"brief"/, "brief workspace id in WORKSPACE_TABS");
    assert.match(pageSrc, /"build"/, "build workspace id in WORKSPACE_TABS");
    assert.match(pageSrc, /"itinerary"/, "itinerary workspace id in WORKSPACE_TABS");
    assert.match(pageSrc, /"ideas"/, "ideas workspace id in WORKSPACE_TABS");
  });
});

// ── 3. Active workspace state controls mobile panel visibility ────────────────

describe("Phase 8K: active workspace state drives mobile panel visibility", () => {
  it("activeMobileWorkspace state is declared in the page", () => {
    assert.match(pageSrc, /activeMobileWorkspace/, "activeMobileWorkspace state must exist");
    assert.match(pageSrc, /setActiveMobileWorkspace/, "setActiveMobileWorkspace setter must exist");
  });

  it("brief panel uses hidden/lg:block conditional class", () => {
    // The brief panel wrapper should be hidden when non-brief is active on mobile
    assert.match(
      pageSrc,
      /activeMobileWorkspace !== "brief".*hidden lg:block|hidden lg:block.*activeMobileWorkspace !== "brief"/,
      "brief panel must use hidden lg:block when not in brief workspace",
    );
  });

  it("TripBuilder wrapper hides on mobile when brief workspace is active", () => {
    assert.match(
      pageSrc,
      /activeMobileWorkspace === "brief".*hidden lg:block|hidden lg:block.*activeMobileWorkspace === "brief"/,
      "TripBuilder wrapper must hide on mobile when brief is active",
    );
  });

  it("MobileWorkspace type alias is defined", () => {
    assert.match(pageSrc, /type MobileWorkspace\s*=/, "MobileWorkspace type must be defined");
    assert.match(pageSrc, /"brief" \| "build" \| "itinerary" \| "ideas"/, "MobileWorkspace includes all four values");
  });
});

// ── 4. All four mobile panel testids exist ────────────────────────────────────

describe("Phase 8K: all four workspace panel data-testids are present", () => {
  it("trip-mobile-panel-brief exists in page.tsx", () => {
    assert.match(pageSrc, /trip-mobile-panel-brief/, "brief panel testid must be in page.tsx");
  });

  it("trip-mobile-panel-build exists in TripBuilder.tsx", () => {
    assert.match(
      tripBuilderSrc,
      /trip-mobile-panel-build/,
      "build panel testid must be in TripBuilder.tsx",
    );
  });

  it("trip-mobile-panel-itinerary exists in TripBuilder.tsx", () => {
    assert.match(
      tripBuilderSrc,
      /trip-mobile-panel-itinerary/,
      "itinerary panel testid must be in TripBuilder.tsx",
    );
  });

  it("trip-mobile-panel-ideas exists in TripBuilder.tsx", () => {
    assert.match(
      tripBuilderSrc,
      /trip-mobile-panel-ideas/,
      "ideas panel testid must be in TripBuilder.tsx",
    );
  });

  it("trip-mobile-workspace outer shell testid exists in page.tsx", () => {
    assert.match(pageSrc, /trip-mobile-workspace/, "outer workspace shell testid must exist");
  });

  it("trip-mobile-workspace-switcher testid exists in page.tsx", () => {
    assert.match(pageSrc, /trip-mobile-workspace-switcher/, "workspace switcher testid must exist");
  });
});

// ── 5. Desktop layout is preserved — not replaced by mobile tab model ─────────

describe("Phase 8K: desktop layout preserved — lg: overrides keep all panels visible", () => {
  it("left (build) panel uses lg:flex to restore display on desktop", () => {
    assert.match(
      tripBuilderSrc,
      /hidden lg:flex/,
      "TripBuilder left panel must use hidden lg:flex for desktop visibility",
    );
  });

  it("right panel container uses lg:flex to restore on desktop when build is active", () => {
    assert.match(
      tripBuilderSrc,
      /hidden lg:flex/,
      "TripBuilder right panel must use hidden lg:flex for desktop visibility",
    );
  });

  it("ideas panel wrapper uses hidden lg:block for desktop override", () => {
    assert.match(
      tripBuilderSrc,
      /hidden lg:block/,
      "TripIdeasPanel wrapper must use hidden lg:block for desktop visibility",
    );
  });

  it("workspace switcher nav is lg:hidden (mobile-only)", () => {
    assert.match(
      pageSrc,
      /lg:hidden/,
      "workspace switcher nav must be lg:hidden so it does not appear on desktop",
    );
  });

  it("TripBuilder keeps its multi-panel flex layout (lg:flex-row) unchanged", () => {
    assert.match(
      tripBuilderSrc,
      /lg:flex-row/,
      "TripBuilder container must keep lg:flex-row for desktop side-by-side layout",
    );
  });
});

// ── 6. TripBuilder behaviour contracts preserved ──────────────────────────────

describe("Phase 8K: TripBuilder existing behaviour contracts preserved", () => {
  it("mobileWorkspace prop added to TripBuilderProps interface", () => {
    assert.match(
      tripBuilderSrc,
      /mobileWorkspace\?:\s*"build"\s*\|\s*"itinerary"\s*\|\s*"ideas"\s*\|\s*null/,
      "mobileWorkspace optional prop must be typed correctly in TripBuilderProps",
    );
  });

  it("TripBuilder still renders CandidatePanel for flights", () => {
    assert.match(tripBuilderSrc, /No flight options are available yet/, "flight empty message must remain");
  });

  it("TripBuilder still renders CandidatePanel for hotels", () => {
    assert.match(tripBuilderSrc, /No hotel options are available yet/, "hotel empty message must remain");
  });

  it("TripBuilder still renders CandidatePanel for attractions", () => {
    assert.match(tripBuilderSrc, /No attractions are available yet/, "attractions empty message must remain");
  });

  it("TripBuilder still renders CandidatePanel for restaurants", () => {
    assert.match(tripBuilderSrc, /No restaurants are available yet/, "restaurants empty message must remain");
  });

  it("Google Flights CTA testid preserved (google-flights-cta)", () => {
    assert.match(
      tripBuilderSrc,
      /google-flights-cta/,
      "google-flights-cta testid must remain in TripBuilder",
    );
  });

  it("flight-add-btn testid preserved", () => {
    assert.match(tripBuilderSrc, /flight-add-btn/, "flight-add-btn testid must remain");
  });

  it("Add Round Trip button preserved", () => {
    assert.match(tripBuilderSrc, /Add Round Trip/, "Add Round Trip button text must remain");
  });

  it("compareSet and compare modal preserved", () => {
    assert.match(tripBuilderSrc, /compareSet/, "compareSet state must remain in TripBuilder");
    assert.match(tripBuilderSrc, /CompareModal/, "CompareModal must remain in TripBuilder");
  });

  it("DnD context (DndContext, SortableContext) preserved", () => {
    assert.match(tripBuilderSrc, /DndContext/, "DndContext must remain in TripBuilder");
    assert.match(tripBuilderSrc, /SortableContext/, "SortableContext must remain in TripBuilder");
  });

  it("onIdeaAssigned callback preserved in TripBuilderProps", () => {
    assert.match(
      tripBuilderSrc,
      /onIdeaAssigned\?:\s*\(\)\s*=>/,
      "onIdeaAssigned must remain as optional callback in TripBuilderProps",
    );
  });

  it("TripIdeasPanel is still rendered inside TripBuilder", () => {
    assert.match(tripBuilderSrc, /TripIdeasPanel/, "TripIdeasPanel must remain in TripBuilder");
  });

  it("ItineraryDayColumn is still rendered inside TripBuilder", () => {
    assert.match(tripBuilderSrc, /ItineraryDayColumn/, "ItineraryDayColumn must remain in TripBuilder");
  });
});

// ── 7. AIConciergePanel contract preserved ────────────────────────────────────

describe("Phase 8K: AIConciergePanel contract preserved", () => {
  it("AIConciergePanel is imported in page.tsx", () => {
    assert.match(pageSrc, /AIConciergePanel/, "AIConciergePanel must remain imported");
  });

  it("AIConciergePanel receives isOpen and onClose props from page.tsx", () => {
    assert.match(pageSrc, /isOpen={conciergeOpen}/, "isOpen prop must remain on AIConciergePanel");
    assert.match(pageSrc, /onClose=/, "onClose prop must remain on AIConciergePanel");
  });

  it("conciergeOpen state is still managed in page.tsx", () => {
    assert.match(pageSrc, /conciergeOpen/, "conciergeOpen state must remain");
    assert.match(pageSrc, /setConciergeOpen/, "setConciergeOpen setter must remain");
  });

  it("chapter-action-concierge button preserved (opens concierge panel)", () => {
    assert.match(pageSrc, /chapter-action-concierge/, "concierge action button testid must remain");
  });
});

// ── 8. Edit trip / delete trip modal contracts preserved ─────────────────────

describe("Phase 8K: edit and delete modal contracts preserved", () => {
  it("chapter-action-edit button testid preserved", () => {
    assert.match(pageSrc, /chapter-action-edit/, "edit action button testid must remain");
  });

  it("chapter-action-delete button testid preserved", () => {
    assert.match(pageSrc, /chapter-action-delete/, "delete action button testid must remain");
  });

  it("editOpen state and handleUpdate preserved", () => {
    assert.match(pageSrc, /editOpen/, "editOpen state must remain");
    assert.match(pageSrc, /handleUpdate/, "handleUpdate function must remain");
  });

  it("confirmDelete state and handleDelete preserved", () => {
    assert.match(pageSrc, /confirmDelete/, "confirmDelete state must remain");
    assert.match(pageSrc, /handleDelete/, "handleDelete function must remain");
  });

  it("trip-chapter-cover section testid preserved", () => {
    assert.match(pageSrc, /trip-chapter-cover/, "trip-chapter-cover testid must remain in page.tsx");
  });
});

// ── 9. No backend / provider / Supabase / env files changed ──────────────────

describe("Phase 8K: no backend or provider files modified", () => {
  it("backend/app/main.py is not changed (backend route entrypoint)", () => {
    // Guard: this file should exist and not reference mobileWorkspace
    if (backExists("app/main.py")) {
      const mainSrc = readFileSync(resolve(backRoot, "app/main.py"), "utf8");
      assert.doesNotMatch(mainSrc, /mobileWorkspace/, "backend main.py must not reference mobileWorkspace");
    }
  });

  it("backend/app/services/provider_registry.py is unchanged", () => {
    if (backExists("app/services/provider_registry.py")) {
      const regSrc = readFileSync(resolve(backRoot, "app/services/provider_registry.py"), "utf8");
      assert.doesNotMatch(regSrc, /mobileWorkspace/, "provider_registry must not reference mobileWorkspace");
    }
  });

  it("no Supabase migration files were added for this phase", () => {
    // Phase 8K has no SQL requirement — guard that we didn't accidentally create one
    const migPath = resolve(backRoot, "db/migrations/007_trip_workspace.sql");
    assert.ok(!existsSync(migPath), "no SQL migration should exist for phase 8K (frontend-only change)");
  });
});

// ── 10. mobileWorkspace prop on TripBuilder ───────────────────────────────────

describe("Phase 8K: TripBuilder mobileWorkspace prop wired correctly in page.tsx", () => {
  it("page.tsx passes mobileWorkspace prop to TripBuilder", () => {
    assert.match(pageSrc, /mobileWorkspace=/, "mobileWorkspace prop must be passed to TripBuilder in page.tsx");
  });

  it("page.tsx passes null for mobileWorkspace when brief is active", () => {
    assert.match(
      pageSrc,
      /activeMobileWorkspace === "brief" \? null : activeMobileWorkspace/,
      "mobileWorkspace must be null when brief workspace is active",
    );
  });
});

// ── 11. Touch target minimums on workspace tabs ───────────────────────────────

describe("Phase 8K: workspace tab touch targets meet 44px minimum", () => {
  it("workspace tab buttons include min-h-[44px]", () => {
    assert.match(pageSrc, /min-h-\[44px\]/, "workspace tab buttons must have min-h-[44px] touch target");
  });
});

// ── 12. TripIdeasPanel contract unchanged ─────────────────────────────────────

describe("Phase 8K: TripIdeasPanel internal contracts unchanged", () => {
  it("TripIdeasPanel still uses fetchTripIdeas (not fetchTripItems)", () => {
    assert.match(tripIdeasSrc, /fetchTripIdeas/, "TripIdeasPanel must use fetchTripIdeas");
    assert.doesNotMatch(tripIdeasSrc, /fetchTripItems/, "TripIdeasPanel must not use fetchTripItems");
  });

  it("TripIdeasPanel still exports the component and accepts tripId/days props", () => {
    assert.match(tripIdeasSrc, /tripId/, "TripIdeasPanel must accept tripId prop");
    assert.match(tripIdeasSrc, /days:/, "TripIdeasPanel must accept days prop");
  });
});

// ── 13. Itinerary chrome isolation — Ideas workspace hides header on mobile ────

describe("Phase 8K: itinerary chrome hidden when Ideas workspace is active on mobile", () => {
  it("trip-mobile-itinerary-chrome testid exists in TripBuilder", () => {
    assert.match(
      tripBuilderSrc,
      /trip-mobile-itinerary-chrome/,
      "itinerary chrome wrapper must have data-testid trip-mobile-itinerary-chrome",
    );
  });

  it("itinerary chrome uses hidden lg:flex when mobileWorkspace is ideas", () => {
    assert.match(
      tripBuilderSrc,
      /mobileWorkspace === "ideas".*hidden lg:flex|hidden lg:flex.*mobileWorkspace === "ideas"/,
      "itinerary chrome must use hidden lg:flex when ideas workspace is active",
    );
  });

  it("itinerary chrome does NOT unconditionally hide when mobileWorkspace is itinerary", () => {
    // The condition must only apply to "ideas", so the chrome is visible for itinerary/null.
    // Verify the guard is specifically for "ideas" and not a blanket hide.
    assert.match(
      tripBuilderSrc,
      /mobileWorkspace === "ideas"/,
      "chrome hide condition must be specifically for ideas workspace",
    );
  });

  it("desktop always restores itinerary chrome via lg:flex override", () => {
    // hidden lg:flex pattern ensures desktop shows the chrome regardless of mobileWorkspace.
    assert.match(
      tripBuilderSrc,
      /hidden lg:flex/,
      "hidden lg:flex must be present to restore chrome on desktop",
    );
  });

  it("itinerary panel testid (trip-mobile-panel-itinerary) still exists after chrome fix", () => {
    assert.match(
      tripBuilderSrc,
      /trip-mobile-panel-itinerary/,
      "itinerary panel testid must remain after chrome isolation fix",
    );
  });

  it("ideas panel testid (trip-mobile-panel-ideas) still exists after chrome fix", () => {
    assert.match(
      tripBuilderSrc,
      /trip-mobile-panel-ideas/,
      "ideas panel testid must remain after chrome isolation fix",
    );
  });
});
