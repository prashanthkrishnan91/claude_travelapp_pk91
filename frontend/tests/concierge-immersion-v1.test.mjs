/**
 * Concierge Immersion Layer v1
 * Contract tests for the salon portal hero, destination-tuned state,
 * enriched loading copy, editorial result labels, and ambient motion.
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

// ── Section I: Salon Portal Hero CSS primitives ───────────────────────────────

describe("Concierge Immersion Layer v1: Portal Hero CSS", () => {
  test("I1. CONCIERGE IMMERSION LAYER v1 section header present in globals.css", () => {
    assert.ok(
      globalsCss.includes("CONCIERGE IMMERSION LAYER v1"),
      "globals.css must have a CONCIERGE IMMERSION LAYER v1 section comment",
    );
  });

  test("I2. atelier-salon-portal-frame defined in globals.css", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-portal-frame"),
      "globals.css must define .atelier-salon-portal-frame — the framed scenic centerpiece",
    );
  });

  test("I3. atelier-salon-portal-frame has brass hairline border", () => {
    const idx = globalsCss.indexOf(".atelier-salon-portal-frame");
    assert.ok(idx !== -1, ".atelier-salon-portal-frame must be defined");
    const block = globalsCss.slice(idx, idx + 400);
    assert.ok(
      block.includes("var(--ds-ember-brass)"),
      ".atelier-salon-portal-frame must use --ds-ember-brass for the brass hairline border",
    );
  });

  test("I4. atelier-salon-portal-frame has entrance animation", () => {
    const idx = globalsCss.indexOf(".atelier-salon-portal-frame");
    assert.ok(idx !== -1, ".atelier-salon-portal-frame must be defined");
    const block = globalsCss.slice(idx, idx + 400);
    assert.ok(
      block.includes("animation"),
      ".atelier-salon-portal-frame must define an entrance animation",
    );
  });

  test("I5. atelier-portal-enter keyframe defined in globals.css", () => {
    assert.ok(
      globalsCss.includes("atelier-portal-enter"),
      "globals.css must define the atelier-portal-enter keyframe for portal entrance",
    );
  });

  test("I6. atelier-salon-portal-hero defined with height for scenic stage", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-portal-hero"),
      "globals.css must define .atelier-salon-portal-hero — the scenic panel stage",
    );
    const idx = globalsCss.indexOf(".atelier-salon-portal-hero");
    const block = globalsCss.slice(idx, idx + 200);
    assert.ok(
      block.includes("height"),
      ".atelier-salon-portal-hero must define a height for the scenic stage",
    );
  });

  test("I7. portal painted layer reads --world-scenery CSS variable", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-portal-painted"),
      ".atelier-salon-portal-painted must be defined",
    );
    // Check the scenery variable exists anywhere after the painted class definition
    const idx = globalsCss.indexOf(".atelier-salon-portal-painted");
    const block = globalsCss.slice(idx, idx + 800);
    assert.ok(
      block.includes("var(--world-scenery"),
      ".atelier-salon-portal-painted must use var(--world-scenery) for destination DNA",
    );
  });

  test("I8. portal image layer reads --world-scenery-image CSS variable", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-portal-image"),
      ".atelier-salon-portal-image must be defined",
    );
    const idx = globalsCss.indexOf(".atelier-salon-portal-image");
    const block = globalsCss.slice(idx, idx + 800);
    assert.ok(
      block.includes("var(--world-scenery-image"),
      ".atelier-salon-portal-image must use var(--world-scenery-image) for photographic scenery",
    );
  });

  test("I9. portal overlay layer reads --world-scenery-overlay CSS variable", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-portal-overlay"),
      ".atelier-salon-portal-overlay must be defined",
    );
    const idx = globalsCss.indexOf(".atelier-salon-portal-overlay");
    const block = globalsCss.slice(idx, idx + 800);
    assert.ok(
      block.includes("var(--world-scenery-overlay"),
      ".atelier-salon-portal-overlay must use var(--world-scenery-overlay) for world palette",
    );
  });

  test("I10. portal veil uses --world-surface for seamless paper merge", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-portal-veil"),
      ".atelier-salon-portal-veil must be defined",
    );
    assert.ok(
      globalsCss.includes("var(--world-surface, var(--ds-warm-paper))"),
      ".atelier-salon-portal-veil must use --world-surface to fade into the paper room",
    );
  });

  test("I11. portal mood line uses Fraunces serif italic", () => {
    const idx = globalsCss.indexOf(".atelier-salon-portal-mood");
    assert.ok(idx !== -1, ".atelier-salon-portal-mood must be defined");
    const block = globalsCss.slice(idx, idx + 300);
    assert.ok(
      block.includes("font-fraunces"),
      ".atelier-salon-portal-mood must use var(--font-fraunces) for editorial serif voice",
    );
    assert.ok(
      block.includes("italic"),
      ".atelier-salon-portal-mood must use font-style: italic for the editorial tone",
    );
  });

  test("I12. portal entrance animation has reduced-motion guard", () => {
    const cssAfterPortal = globalsCss.slice(
      globalsCss.indexOf(".atelier-salon-portal-frame"),
    );
    assert.ok(
      cssAfterPortal.includes("prefers-reduced-motion: reduce"),
      "Portal animations must have a @media (prefers-reduced-motion: reduce) guard",
    );
    assert.ok(
      cssAfterPortal.includes("animation: none"),
      "Reduced-motion guard must set animation: none (portal entrance disabled)",
    );
  });
});

// ── Section J: Destination-tuned state ───────────────────────────────────────

describe("Concierge Immersion Layer v1: Destination-tuned state", () => {
  test("J1. data-destination-tuned CSS rule defined in globals.css", () => {
    assert.ok(
      globalsCss.includes("[data-destination-tuned"),
      "globals.css must define [data-destination-tuned] CSS rule for destination-aware portal",
    );
  });

  test("J2. destination-tuned state uses ember-brass for visual signal", () => {
    const idx = globalsCss.indexOf("[data-destination-tuned");
    assert.ok(idx !== -1, "[data-destination-tuned] rule must be defined");
    const block = globalsCss.slice(idx, idx + 400);
    assert.ok(
      block.includes("var(--ds-ember-brass)"),
      "destination-tuned state must use --ds-ember-brass for the brass portal glow",
    );
  });

  test("J3. destination-tuned transition has reduced-motion guard", () => {
    const cssAfterTuned = globalsCss.slice(
      globalsCss.indexOf("[data-destination-tuned"),
    );
    assert.ok(
      cssAfterTuned.indexOf("prefers-reduced-motion: reduce") !== -1,
      "[data-destination-tuned] transition must have a reduced-motion guard",
    );
  });

  test("J4. ConciergePage sets data-destination-tuned when destination is set", () => {
    assert.ok(
      conciergePage.includes("data-destination-tuned"),
      "ConciergePage must set data-destination-tuned attribute for destination-aware state",
    );
  });
});

// ── Section K: Portal hero in ConciergePage ───────────────────────────────────

describe("Concierge Immersion Layer v1: Portal hero adoption", () => {
  test("K1. ConciergePage renders atelier-salon-portal-wrapper", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-portal-wrapper"),
      "ConciergePage must render the portal wrapper element",
    );
  });

  test("K2. ConciergePage renders atelier-salon-portal-frame", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-portal-frame"),
      "ConciergePage must render the portal frame (framed cinema panel)",
    );
  });

  test("K3. ConciergePage renders portal scenic layers (painted, image, overlay, veil)", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-portal-painted") &&
      conciergePage.includes("atelier-salon-portal-image") &&
      conciergePage.includes("atelier-salon-portal-overlay") &&
      conciergePage.includes("atelier-salon-portal-veil"),
      "ConciergePage must render all four portal scenic layers",
    );
  });

  test("K4. ConciergePage renders portal editorial mood line", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-portal-editorial") &&
      conciergePage.includes("atelier-salon-portal-mood"),
      "ConciergePage must render the portal editorial mood line",
    );
  });

  test("K5. Portal wrapper has aria-hidden (decorative, no interactive content)", () => {
    const idx = conciergePage.indexOf("atelier-salon-portal-wrapper");
    assert.ok(idx !== -1, "atelier-salon-portal-wrapper must be rendered");
    const block = conciergePage.slice(Math.max(0, idx - 80), idx + 80);
    assert.ok(
      block.includes('aria-hidden="true"'),
      "The portal wrapper must have aria-hidden='true' — it is purely decorative",
    );
  });

  test("K6. Portal mood line reads salonWorld.mood", () => {
    assert.ok(
      conciergePage.includes("salonWorld.mood"),
      "ConciergePage portal must render salonWorld.mood as the editorial mood text",
    );
  });
});

// ── Section L: Loading state concierge tone ───────────────────────────────────

describe("Concierge Immersion Layer v1: Loading state tone", () => {
  test("L1. Loading state uses concierge-tone copy (Curating a shortlist)", () => {
    assert.ok(
      conciergePage.includes("Curating a shortlist"),
      "Loading state must use 'Curating a shortlist' for concierge tone",
    );
  });

  test("L2. Loading state uses dossier framing (Preparing your dossier)", () => {
    assert.ok(
      conciergePage.includes("Preparing your dossier"),
      "Loading state must use 'Preparing your dossier' for concierge dossier tone",
    );
  });

  test("L3. Loading state includes brass pulse dots", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-loading-dot"),
      "Loading state must use atelier-salon-loading-dot for brass pulse animation",
    );
  });

  test("L4. atelier-salon-loading-dot defined in globals.css", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-loading-dot"),
      "globals.css must define .atelier-salon-loading-dot for loading pulse animation",
    );
  });

  test("L5. loading dot animation has reduced-motion guard", () => {
    const cssAfterDot = globalsCss.slice(
      globalsCss.indexOf(".atelier-salon-loading-dot"),
    );
    assert.ok(
      cssAfterDot.indexOf("prefers-reduced-motion: reduce") !== -1,
      ".atelier-salon-loading-dot must have a reduced-motion guard",
    );
  });
});

// ── Section M: Result editorial label ────────────────────────────────────────

describe("Concierge Immersion Layer v1: Result editorial label", () => {
  test("M1. atelier-salon-result-label defined in globals.css", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-result-label"),
      "globals.css must define .atelier-salon-result-label — editorial result count annotation",
    );
  });

  test("M2. ConciergePage renders atelier-salon-result-label before card grids", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-result-label"),
      "ConciergePage must render atelier-salon-result-label before each card group",
    );
  });

  test("M3. Result label uses shortlisted framing", () => {
    assert.ok(
      conciergePage.includes("shortlisted"),
      "ConciergePage result label must use 'shortlisted' for concierge editorial tone",
    );
  });
});

// ── Section N: Preserved contracts (immersion layer must not regress) ─────────

describe("Concierge Immersion Layer v1: Preserved contracts", () => {
  test("N1. concierge-page testid preserved", () => {
    assert.ok(
      conciergePage.includes('data-testid="concierge-page"'),
      "data-testid='concierge-page' must remain unchanged",
    );
  });

  test("N2. concierge-instrument-header testid preserved", () => {
    assert.ok(
      conciergePage.includes('data-testid="concierge-instrument-header"'),
      "data-testid='concierge-instrument-header' must remain unchanged",
    );
  });

  test("N3. concierge-instrument-composer testid preserved", () => {
    assert.ok(
      conciergePage.includes('data-testid="concierge-instrument-composer"'),
      "data-testid='concierge-instrument-composer' must remain unchanged",
    );
  });

  test("N4. Starting points copy preserved in empty state", () => {
    assert.ok(
      conciergePage.includes("Starting points") || conciergePage.includes("starting points"),
      "'Starting points' framing must be preserved in the empty state",
    );
  });

  test("N5. WorldAtmosphere still rendered (ambient layer preserved)", () => {
    assert.ok(
      conciergePage.includes("<WorldAtmosphere"),
      "WorldAtmosphere must remain rendered for destination-aware ambient coloring",
    );
  });

  test("N6. folio-cinema-composer preserved on sticky composer", () => {
    assert.ok(
      conciergePage.includes("folio-cinema-composer"),
      "folio-cinema-composer must remain on the sticky bottom composer",
    );
  });

  test("N7. atelier-salon-briefing-rail still rendered", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-briefing-rail"),
      "atelier-salon-briefing-rail must remain rendered in ConciergePage",
    );
  });

  test("N8. No raw rgba() in ConciergePage (token rule preserved)", () => {
    assert.ok(
      !conciergePage.includes("rgba("),
      "ConciergePage must not use raw rgba() — use DS tokens or CSS classes",
    );
  });
});
