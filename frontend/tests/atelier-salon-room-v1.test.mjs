/**
 * Atelier Room System v1 — Private Salon (AI Concierge)
 * Contract tests for the salon room shell applied to ConciergePage.
 * All tests are static source-file assertions; no DOM rendering, no network.
 */

import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { test, describe } from "node:test";
import assert from "node:assert/strict";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");

const conciergePage = readFileSync(
  join(root, "src/components/concierge/ConciergePage.tsx"),
  "utf8",
);
const globalsCss = readFileSync(
  join(root, "src/app/globals.css"),
  "utf8",
);
const appShell = readFileSync(
  join(root, "src/components/layout/AppShell.tsx"),
  "utf8",
);

// ── Section A: CSS primitives defined in globals.css ────────────────────────

describe("Atelier Room System: CSS primitives", () => {
  test("A1. atelier-salon-room defined in globals.css", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-room"),
      "globals.css must define .atelier-salon-room — the salon room shell class",
    );
  });

  test("A2. atelier-salon-room has isolation: isolate for stacking context", () => {
    const salonRoomBlock = globalsCss.slice(
      globalsCss.indexOf(".atelier-salon-room"),
      globalsCss.indexOf(".atelier-salon-room") + 120,
    );
    assert.ok(
      salonRoomBlock.includes("isolation: isolate"),
      ".atelier-salon-room must set isolation: isolate to contain z-index:-1 ambient layers",
    );
  });

  test("A3. atelier-salon-room-header defined in globals.css", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-room-header"),
      "globals.css must define .atelier-salon-room-header — the salon entry header",
    );
  });

  test("A4. atelier-salon-room-header has brass separator ::before", () => {
    const idx = globalsCss.indexOf(".atelier-salon-room-header::before");
    assert.ok(
      idx !== -1,
      ".atelier-salon-room-header::before must be defined — the brass entry separator",
    );
    const block = globalsCss.slice(idx, idx + 300);
    assert.ok(
      block.includes("var(--ds-ember-brass)"),
      ".atelier-salon-room-header::before must use --ds-ember-brass for the brass separator",
    );
  });

  test("A5. atelier-salon-starter-chip defined in globals.css", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-starter-chip"),
      "globals.css must define .atelier-salon-starter-chip — premium prompt chip treatment",
    );
  });

  test("A6. atelier-salon-starter-chip uses DS tokens, no raw hex", () => {
    const idx = globalsCss.indexOf(".atelier-salon-starter-chip");
    const block = globalsCss.slice(idx, idx + 600);
    assert.ok(
      !block.includes("#") || block.includes("var(--"),
      ".atelier-salon-starter-chip must use --ds-* tokens, not raw hex colors",
    );
    assert.ok(
      block.includes("var(--ds-ember-brass)") || block.includes("var(--ds-accent"),
      ".atelier-salon-starter-chip must use ember-brass or accent tokens",
    );
  });

  test("A7. atelier-salon-starter-chip has reduced-motion guard", () => {
    const cssAfterChip = globalsCss.slice(
      globalsCss.indexOf(".atelier-salon-starter-chip"),
    );
    assert.ok(
      cssAfterChip.includes("prefers-reduced-motion: reduce"),
      ".atelier-salon-starter-chip must have a @media (prefers-reduced-motion: reduce) guard",
    );
  });

  test("A8. ATELIER ROOM SYSTEM section header present in globals.css", () => {
    assert.ok(
      globalsCss.includes("ATELIER ROOM SYSTEM"),
      "globals.css must have an ATELIER ROOM SYSTEM section comment",
    );
  });
});

// ── Section B: ConciergePage uses the salon room shell ──────────────────────

describe("Atelier Room System: ConciergePage salon room adoption", () => {
  test("B1. ConciergePage adds atelier-salon-room class to outer div", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-room"),
      "ConciergePage outer div must include atelier-salon-room class",
    );
  });

  test("B2. ConciergePage preserves folio-cinema-desk (not replaced)", () => {
    assert.ok(
      conciergePage.includes("folio-cinema-desk"),
      "ConciergePage must still use folio-cinema-desk — atelier-salon-room is additive",
    );
  });

  test("B3. ConciergePage imports WorldAtmosphere", () => {
    assert.ok(
      conciergePage.includes("WorldAtmosphere"),
      "ConciergePage must import WorldAtmosphere for destination-aware ambient layer",
    );
  });

  test("B4. ConciergePage renders WorldAtmosphere component", () => {
    assert.ok(
      conciergePage.includes("<WorldAtmosphere"),
      "ConciergePage must render <WorldAtmosphere /> for destination-aware ambient coloring",
    );
  });

  test("B5. ConciergePage imports pickWorldFromDestination", () => {
    assert.ok(
      conciergePage.includes("pickWorldFromDestination"),
      "ConciergePage must import pickWorldFromDestination for world DNA resolution",
    );
  });

  test("B6. ConciergePage imports worldStyleVars", () => {
    assert.ok(
      conciergePage.includes("worldStyleVars"),
      "ConciergePage must import worldStyleVars to inject --world-* CSS variables",
    );
  });

  test("B7. ConciergePage imports applyRoom for salon archetype tinting", () => {
    assert.ok(
      conciergePage.includes("applyRoom"),
      "ConciergePage must import applyRoom to apply the salon archetype tint",
    );
  });

  test("B8. ConciergePage uses applyRoom with salon archetype", () => {
    assert.ok(
      conciergePage.includes('applyRoom') && conciergePage.includes('"salon"'),
      'ConciergePage must call applyRoom(..., "salon") for the salon room world',
    );
  });

  test("B9. ConciergePage applies worldStyleVars to outer div style", () => {
    assert.ok(
      conciergePage.includes("worldStyleVars("),
      "ConciergePage must spread worldStyleVars() into the outer div style for world DNA",
    );
  });

  test("B10. ConciergePage applies data-world-location attribute", () => {
    assert.ok(
      conciergePage.includes("data-world-location"),
      "ConciergePage must set data-world-location on the room shell for world system integration",
    );
  });

  test("B11. ConciergePage header uses atelier-salon-room-header class", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-room-header"),
      "ConciergePage header must include atelier-salon-room-header class for the brass entry separator",
    );
  });

  test("B12. Prompt chips retain folio-concierge-chip (contract preserved)", () => {
    assert.ok(
      conciergePage.includes("folio-concierge-chip"),
      "ConciergePage must retain folio-concierge-chip on prompt chips — existing contract",
    );
  });

  test("B13. Prompt chips add atelier-salon-starter-chip for atelier treatment", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-starter-chip"),
      "ConciergePage prompt chips must include atelier-salon-starter-chip for premium chip styling",
    );
  });

  test("B14. ConciergePage has no raw rgba() — token rule preserved", () => {
    assert.ok(
      !conciergePage.includes("rgba("),
      "ConciergePage must not use raw rgba() — use DS tokens or CSS classes",
    );
  });
});

// ── Section C: Existing contracts preserved ──────────────────────────────────

describe("Atelier Room System: preservation of existing contracts", () => {
  test("C1. concierge-page testid preserved", () => {
    assert.ok(
      conciergePage.includes('data-testid="concierge-page"'),
      "data-testid='concierge-page' must remain on the ConciergePage root element",
    );
  });

  test("C2. concierge-instrument-header testid preserved", () => {
    assert.ok(
      conciergePage.includes('data-testid="concierge-instrument-header"'),
      "data-testid='concierge-instrument-header' must be preserved",
    );
  });

  test("C3. concierge-instrument-composer testid preserved", () => {
    assert.ok(
      conciergePage.includes('data-testid="concierge-instrument-composer"'),
      "data-testid='concierge-instrument-composer' must be preserved",
    );
  });

  test("C4. concierge-results-canvas testid preserved", () => {
    assert.ok(
      conciergePage.includes('data-testid="concierge-results-canvas"'),
      "data-testid='concierge-results-canvas' must be preserved",
    );
  });

  test("C5. concierge-empty-state testid preserved", () => {
    assert.ok(
      conciergePage.includes('data-testid="concierge-empty-state"'),
      "data-testid='concierge-empty-state' must be preserved",
    );
  });

  test("C6. concierge-prompt-chip testid preserved", () => {
    assert.ok(
      conciergePage.includes('data-testid="concierge-prompt-chip"'),
      "data-testid='concierge-prompt-chip' must be preserved on starter chips",
    );
  });

  test("C7. folio-cinema-composer preserved on sticky composer", () => {
    assert.ok(
      conciergePage.includes("folio-cinema-composer"),
      "folio-cinema-composer must remain on the sticky bottom composer",
    );
  });

  test("C8. Starting points copy preserved in empty state", () => {
    assert.ok(
      conciergePage.includes("Starting points") || conciergePage.includes("starting points"),
      "'Starting points' framing must be preserved in the empty state",
    );
  });

  test("C9. concierge-result-save-btn testid preserved", () => {
    assert.ok(
      conciergePage.includes('data-testid="concierge-result-save-btn"'),
      "data-testid='concierge-result-save-btn' must be preserved",
    );
  });

  test("C10. callConciergeSearch import preserved — backend contract unchanged", () => {
    assert.ok(
      conciergePage.includes("callConciergeSearch"),
      "callConciergeSearch must remain — no backend API contract changes",
    );
  });
});

// ── Section D: Patch-1 salon strengthening contracts ─────────────────────────

describe("Atelier Room System: salon strengthening (patch-1 primitives)", () => {
  test("D1. atelier-salon-invitation defined in globals.css", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-invitation"),
      "globals.css must define .atelier-salon-invitation — premium empty-state threshold",
    );
  });

  test("D2. atelier-salon-invitation has ::before brass rule", () => {
    const idx = globalsCss.indexOf(".atelier-salon-invitation::before");
    assert.ok(
      idx !== -1,
      ".atelier-salon-invitation::before must be defined — brass invitation separator",
    );
    const block = globalsCss.slice(idx, idx + 300);
    assert.ok(
      block.includes("var(--ds-ember-brass)"),
      ".atelier-salon-invitation::before must use --ds-ember-brass",
    );
  });

  test("D3. atelier-salon-composer-surface defined in globals.css", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-composer-surface"),
      "globals.css must define .atelier-salon-composer-surface — desk threshold hairline",
    );
  });

  test("D4. atelier-salon-composer-surface has ::before brass hairline", () => {
    const idx = globalsCss.indexOf(".atelier-salon-composer-surface::before");
    assert.ok(
      idx !== -1,
      ".atelier-salon-composer-surface::before must be defined — brass desk surface hairline",
    );
  });

  test("D5. atelier-salon-user-turn defined in globals.css", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-user-turn"),
      "globals.css must define .atelier-salon-user-turn — brass-tinted query annotation",
    );
  });

  test("D6. atelier-salon-user-turn uses ember-brass", () => {
    const idx = globalsCss.indexOf(".atelier-salon-user-turn");
    const block = globalsCss.slice(idx, idx + 120);
    assert.ok(
      block.includes("var(--ds-ember-brass)"),
      ".atelier-salon-user-turn must use --ds-ember-brass for the border tint",
    );
  });

  test("D7. ConciergePage empty-state uses atelier-salon-invitation", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-invitation"),
      "ConciergePage empty-state must use atelier-salon-invitation class",
    );
  });

  test("D8. ConciergePage composer uses atelier-salon-composer-surface", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-composer-surface"),
      "ConciergePage composer must use atelier-salon-composer-surface class",
    );
  });

  test("D9. ConciergePage user-turn uses atelier-salon-user-turn", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-user-turn"),
      "ConciergePage user-turn marker must use atelier-salon-user-turn class",
    );
  });

  test("D10. composer-surface reduced-motion guard present", () => {
    const cssAfterComposer = globalsCss.slice(
      globalsCss.indexOf(".atelier-salon-composer-surface"),
    );
    assert.ok(
      cssAfterComposer.includes("prefers-reduced-motion: reduce"),
      ".atelier-salon-composer-surface must have a reduced-motion guard",
    );
  });
});

// ── Section E: Salon room full-surface upgrade (patch-2 primitives) ───────────

describe("Atelier Room System: salon full-surface upgrade (patch-2)", () => {
  test("E1. atelier-salon-room.folio-cinema-desk combination rule strips card chrome", () => {
    const idx = globalsCss.indexOf(".atelier-salon-room.folio-cinema-desk");
    assert.ok(
      idx !== -1,
      "globals.css must define .atelier-salon-room.folio-cinema-desk combination rule",
    );
    const block = globalsCss.slice(idx, idx + 200);
    assert.ok(
      block.includes("border-radius: 0") && block.includes("border: none"),
      ".atelier-salon-room.folio-cinema-desk must set border-radius:0 and border:none",
    );
  });

  test("E2. atelier-salon-chip-grid defined in globals.css", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-chip-grid"),
      "globals.css must define .atelier-salon-chip-grid — 2-column starter chip grid",
    );
  });

  test("E3. atelier-salon-chip-grid uses grid layout", () => {
    const idx = globalsCss.indexOf(".atelier-salon-chip-grid");
    const block = globalsCss.slice(idx, idx + 200);
    assert.ok(
      block.includes("grid-template-columns"),
      ".atelier-salon-chip-grid must use grid-template-columns for 2-column layout",
    );
  });

  test("E4. ConciergePage chip container uses atelier-salon-chip-grid", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-chip-grid"),
      "ConciergePage chip container must use atelier-salon-chip-grid for 2-column desktop layout",
    );
  });

  test("E5. atelier-salon-header-landing defined in globals.css", () => {
    assert.ok(
      globalsCss.includes("atelier-salon-header-landing"),
      "globals.css must define atelier-salon-header-landing — salon cinematic vertical spacing",
    );
  });

  test("E6. ConciergePage header uses atelier-salon-header-landing", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-header-landing"),
      "ConciergePage header must use atelier-salon-header-landing for immersive vertical space",
    );
  });
});

// ── Section F: Salon route shell integration (AppShell + CSS) ───────────────

describe("Atelier Room System: salon route shell integration (patch-3)", () => {
  test("F1. AppShell defines isSalonRoute for /concierge path", () => {
    assert.ok(
      appShell.includes('pathname === "/concierge"'),
      "AppShell must define isSalonRoute checking pathname === '/concierge'",
    );
  });

  test("F2. AppShell sets data-atelier-shell='salon' for salon route", () => {
    assert.ok(
      appShell.includes('data-atelier-shell') && appShell.includes('"salon"'),
      "AppShell must set data-atelier-shell='salon' on the atmosphere root for salon route",
    );
  });

  test("F3. AppShell renders AtelierNavArtifact for salon route", () => {
    assert.ok(
      appShell.includes("isSalonRoute && <AtelierNavArtifact"),
      "AppShell must render AtelierNavArtifact for the salon route (floating nav)",
    );
  });

  test("F4. AppShell uses home-edge-bleed for salon route (immersive wrapper)", () => {
    assert.ok(
      appShell.includes("isSalonRoute") && appShell.includes("home-edge-bleed"),
      "AppShell must wrap salon route children in home-edge-bleed for edge-to-edge layout",
    );
  });

  test("F5. globals.css hides .folio-sidebar on salon route via data-atelier-shell", () => {
    assert.ok(
      globalsCss.includes('[data-atelier-shell="salon"] .folio-sidebar'),
      "globals.css must hide .folio-sidebar when data-atelier-shell='salon' is set",
    );
  });

  test("F6. globals.css defines atelier-salon-page with world-surface background", () => {
    const idx = globalsCss.indexOf(".atelier-salon-page");
    assert.ok(idx !== -1, "globals.css must define .atelier-salon-page");
    const block = globalsCss.slice(idx, idx + 200);
    assert.ok(
      block.includes("--world-surface"),
      ".atelier-salon-page must use --world-surface for light paper room background",
    );
  });

  test("F7. globals.css atelier-salon-page uses warm-paper fallback", () => {
    const idx = globalsCss.indexOf(".atelier-salon-page");
    const block = globalsCss.slice(idx, idx + 200);
    assert.ok(
      block.includes("--ds-warm-paper"),
      ".atelier-salon-page must fall back to --ds-warm-paper when --world-surface is unset",
    );
  });

  test("F8. ConciergePage outer div uses atelier-salon-page (light paper room shell)", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-page"),
      "ConciergePage outer div must use atelier-salon-page for the light paper room shell",
    );
  });
});

// ── Section G: Salon workbench layout (patch-4 constrained column) ───────────

describe("Atelier Room System: salon workbench layout (patch-4)", () => {
  test("G1. globals.css defines atelier-salon-workbench centered column", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-workbench"),
      "globals.css must define .atelier-salon-workbench — centered reading column",
    );
  });

  test("G2. ConciergePage uses atelier-salon-workbench to constrain content width", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-workbench"),
      "ConciergePage must use atelier-salon-workbench to prevent full-viewport composer",
    );
  });

  test("G3. atelier-salon-starter-chip uses world-ink for dark-on-light contrast", () => {
    const idx = globalsCss.indexOf(".atelier-salon-starter-chip");
    const block = globalsCss.slice(idx, idx + 600);
    assert.ok(
      block.includes("world-ink"),
      ".atelier-salon-starter-chip must use --world-ink for readable dark text on light paper",
    );
  });

  test("G4. folio-cinema-desk applied to result cards (dark objects on light salon room)", () => {
    assert.ok(
      conciergePage.includes("folio-cinema-desk folio-cinema-result-card") ||
      conciergePage.includes("folio-cinema-result-card"),
      "Result cards must use folio-cinema-desk treatment — dark cinema objects on the light salon room",
    );
  });
});

// ── Section H: Two-column workbench + briefing rail (patch-5) ────────────────

describe("Atelier Room System: two-column workbench + briefing rail (patch-5)", () => {
  test("H1. globals.css defines atelier-salon-main-panel for contained panel layout", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-main-panel"),
      "globals.css must define .atelier-salon-main-panel — the folio panel containing header, results, composer",
    );
  });

  test("H2. atelier-salon-main-panel has overflow: hidden to contain internal scroll", () => {
    const idx = globalsCss.indexOf(".atelier-salon-main-panel");
    assert.ok(idx !== -1, ".atelier-salon-main-panel must be defined");
    const block = globalsCss.slice(idx, idx + 300);
    assert.ok(
      block.includes("overflow: hidden"),
      ".atelier-salon-main-panel must set overflow: hidden so results scroll inside the panel",
    );
  });

  test("H3. globals.css defines atelier-salon-panel-body for scrollable results area", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-panel-body"),
      "globals.css must define .atelier-salon-panel-body — the scrollable results region inside the panel",
    );
  });

  test("H4. atelier-salon-panel-body has flex:1 and overflow-y:auto for internal scroll", () => {
    const idx = globalsCss.indexOf(".atelier-salon-panel-body");
    assert.ok(idx !== -1, ".atelier-salon-panel-body must be defined");
    const block = globalsCss.slice(idx, idx + 200);
    assert.ok(
      block.includes("flex: 1") && block.includes("overflow-y: auto"),
      ".atelier-salon-panel-body must set flex:1 and overflow-y:auto",
    );
  });

  test("H5. globals.css defines atelier-salon-briefing-rail for capability sidebar", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-briefing-rail"),
      "globals.css must define .atelier-salon-briefing-rail — static capability sidebar",
    );
  });

  test("H6. ConciergePage uses atelier-salon-main-panel to wrap panel content", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-main-panel"),
      "ConciergePage must use atelier-salon-main-panel to create the contained workbench panel",
    );
  });

  test("H7. ConciergePage uses atelier-salon-panel-body on the results canvas", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-panel-body"),
      "ConciergePage must use atelier-salon-panel-body on the results canvas for internal scroll",
    );
  });

  test("H8. ConciergePage renders atelier-salon-briefing-rail with static capability content", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-briefing-rail"),
      "ConciergePage must render atelier-salon-briefing-rail with static capability affordances",
    );
  });
});

// ── Section I: Portal composition (salon rebuild §11 contract tests) ───────────

describe("Atelier Room System: portal composition (salon rebuild)", () => {
  test("I1. globals.css defines .atelier-salon-portal", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-portal"),
      "globals.css must define .atelier-salon-portal — the cinematic portal frame",
    );
  });

  test("I2. globals.css defines .atelier-salon-portal-copy", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-portal-copy"),
      "globals.css must define .atelier-salon-portal-copy — readable content above depth layers",
    );
  });

  test("I3. globals.css defines the four portal depth-layer classes", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-portal-haze") &&
      globalsCss.includes(".atelier-salon-portal-bloom") &&
      globalsCss.includes(".atelier-salon-portal-grain") &&
      globalsCss.includes(".atelier-salon-portal-vignette"),
      "globals.css must define all four portal depth layers: haze, bloom, grain, vignette",
    );
  });

  test("I4. globals.css has [data-portal-state] open rule for .atelier-salon-portal", () => {
    assert.ok(
      globalsCss.includes('data-portal-state="open"') &&
      globalsCss.includes(".atelier-salon-portal"),
      "globals.css must have [data-portal-state=\"open\"] rule controlling portal flex/height",
    );
  });

  test("I5. globals.css has [data-portal-state] tuned rule for .atelier-salon-portal", () => {
    assert.ok(
      globalsCss.includes('data-portal-state="tuned"') &&
      globalsCss.includes(".atelier-salon-portal"),
      "globals.css must have [data-portal-state=\"tuned\"] rule collapsing portal to banner",
    );
  });

  test("I6. ConciergePage renders atelier-salon-portal", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-portal"),
      "ConciergePage must render the atelier-salon-portal section",
    );
  });

  test("I7. ConciergePage sets data-portal-state on the portal", () => {
    assert.ok(
      conciergePage.includes("data-portal-state"),
      "ConciergePage must set data-portal-state to drive portal open/tuned state",
    );
  });

  test("I8. ConciergePage uses portalMode derived from existing state (open/tuned)", () => {
    assert.ok(
      conciergePage.includes("portalMode") &&
      (conciergePage.includes('"open"') || conciergePage.includes("'open'")),
      "ConciergePage must derive portalMode from existing state (not new state)",
    );
  });

  test("I9. concierge-instrument-header is inside atelier-salon-portal (portal appears before canvas in source)", () => {
    const portalIdx = conciergePage.indexOf("atelier-salon-portal");
    const canvasIdx = conciergePage.indexOf('data-testid="concierge-results-canvas"');
    const headerIdx = conciergePage.indexOf('data-testid="concierge-instrument-header"');
    assert.ok(
      portalIdx !== -1 && headerIdx !== -1 && canvasIdx !== -1,
      "all three sections must be present",
    );
    assert.ok(
      headerIdx > portalIdx && headerIdx < canvasIdx,
      "concierge-instrument-header must appear after the portal section start and before the canvas",
    );
  });

  test("I10. concierge-empty-state is NOT inside concierge-results-canvas", () => {
    const canvasIdx = conciergePage.indexOf('data-testid="concierge-results-canvas"');
    const emptyStateIdx = conciergePage.indexOf('data-testid="concierge-empty-state"');
    assert.ok(
      emptyStateIdx !== -1 && canvasIdx !== -1,
      "both concierge-empty-state and concierge-results-canvas must be present",
    );
    // empty-state must appear BEFORE the canvas (it lives in the portal copy)
    assert.ok(
      emptyStateIdx < canvasIdx,
      "concierge-empty-state must appear before concierge-results-canvas — it lives in the portal, not the canvas",
    );
  });

  test("I11. ConciergePage imports WorldScenery for portal scene layer", () => {
    assert.ok(
      conciergePage.includes("WorldScenery"),
      "ConciergePage must import and render WorldScenery for the portal scene layer",
    );
  });

  test("I12. No fake data strings from prototype (no pickScene, no hardcoded demo places)", () => {
    // "data-scene=" checks for data-scene="value" (prototype demo attribute) without
    // matching production's data-scenery-tone which shares the prefix.
    const forbidden = ["pickScene", "Nanzen-ji", "Da Adolfo", "Pontocho", 'data-scene="', "SCENES =", "RESULTS ="];
    for (const s of forbidden) {
      assert.ok(
        !conciergePage.includes(s),
        `ConciergePage must not contain prototype demo string: "${s}"`,
      );
    }
  });

  test("I13. Portal bloom animation has prefers-reduced-motion guard", () => {
    const bloomIdx = globalsCss.indexOf("atelier-portal-bloom");
    assert.ok(bloomIdx !== -1, "atelier-portal-bloom keyframe must be defined");
    const cssAfterBloom = globalsCss.slice(bloomIdx);
    assert.ok(
      cssAfterBloom.includes("prefers-reduced-motion: reduce"),
      "atelier-portal-bloom animation must have a @media (prefers-reduced-motion: reduce) guard",
    );
  });

  test("I14. Canvas (atelier-salon-panel-body) pre-search: open state sets flex:0 to contribute 0 height", () => {
    assert.ok(
      globalsCss.includes('data-portal-state="open"] .atelier-salon-panel-body'),
      "globals.css must have open-state rule overriding canvas flex to prevent pre-search scroll",
    );
  });

  test("I15. Chip onClick populates input only — no setDestination or auto-submit", () => {
    // Find the chip onClick handler in the source
    const chipSection = conciergePage.slice(
      conciergePage.indexOf("EDITORIAL_PROMPTS.map"),
      conciergePage.indexOf("EDITORIAL_PROMPTS.map") + 600,
    );
    assert.ok(
      !chipSection.includes("setDestination") && !chipSection.includes("sendQuery") && !chipSection.includes("handleUserInput"),
      "Chip onClick must only call setInput + focus — no setDestination, sendQuery, or handleUserInput",
    );
  });

  test("I16. atelier-salon-portal-headline class defined in globals.css", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-portal-headline"),
      "globals.css must define .atelier-salon-portal-headline — light text on dark portal",
    );
  });

  test("I17. atelier-salon-portal-headline uses --ds-pearl-cream for light-on-dark contrast", () => {
    const idx = globalsCss.indexOf(".atelier-salon-portal-headline");
    assert.ok(idx !== -1, ".atelier-salon-portal-headline must be defined");
    const block = globalsCss.slice(idx, idx + 200);
    assert.ok(
      block.includes("--ds-pearl-cream"),
      ".atelier-salon-portal-headline must use --ds-pearl-cream — never world-ink (dark) on dark portal",
    );
  });
});
