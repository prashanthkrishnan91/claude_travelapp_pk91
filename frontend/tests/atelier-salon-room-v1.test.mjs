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
