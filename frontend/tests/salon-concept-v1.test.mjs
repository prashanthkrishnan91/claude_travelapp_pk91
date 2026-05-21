/**
 * Section I — Salon Concept v1 implementation tests
 *
 * Verifies that the portal, invitation cards, results header, and dossier
 * briefing rail CSS primitives and ConciergePage wiring are correct.
 * Companion to atelier-salon-room-v1.test.mjs (Sections A–H).
 */

import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "..");

const globalsCss = readFileSync(
  resolve(root, "src/app/globals.css"),
  "utf8",
);
const conciergePage = readFileSync(
  resolve(root, "src/components/concierge/ConciergePage.tsx"),
  "utf8",
);

describe("Section I — Salon Concept v1", () => {
  // ── I-A: Portal CSS primitives ───────────────────────────────────────────

  it("I-A1 — .atelier-salon-portal is defined in globals.css", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-portal {"),
      "Missing .atelier-salon-portal CSS class",
    );
  });

  it("I-A2 — .atelier-salon-portal-scene uses --world-scenery", () => {
    assert.ok(
      globalsCss.includes("var(--world-scenery"),
      ".atelier-salon-portal-scene must use --world-scenery for destination tuning",
    );
  });

  it("I-A3 — portal bloom uses --world-secondary for destination hue", () => {
    assert.ok(
      globalsCss.includes("var(--world-secondary"),
      ".atelier-salon-portal-bloom must use --world-secondary for destination tint",
    );
  });

  it("I-A4 — .atelier-salon-portal-headline uses Fraunces font", () => {
    const startIdx = globalsCss.indexOf(".atelier-salon-portal-headline {");
    assert.ok(startIdx !== -1, "Missing .atelier-salon-portal-headline");
    const blockEnd = globalsCss.indexOf("}", startIdx);
    const block = globalsCss.slice(startIdx, blockEnd + 1);
    assert.ok(
      block.includes("var(--font-fraunces)"),
      ".atelier-salon-portal-headline must use var(--font-fraunces)",
    );
  });

  it("I-A5 — portal has reduced-motion guard on animations", () => {
    assert.ok(
      globalsCss.includes("prefers-reduced-motion: reduce"),
      "Portal animations must have @media (prefers-reduced-motion: reduce) guard",
    );
    assert.ok(
      globalsCss.includes("salonPortalDrift"),
      "Portal scene drift animation must be defined",
    );
  });

  it("I-A6 — portal uses no raw rgba() — only color-mix()", () => {
    const portalSection = globalsCss.slice(
      globalsCss.indexOf(".atelier-salon-portal {"),
      globalsCss.indexOf(".atelier-salon-invitation-card {"),
    );
    assert.ok(
      !portalSection.includes("rgba("),
      "Portal CSS must not use raw rgba() — use color-mix() instead",
    );
  });

  // ── I-B: Invitation card CSS primitives ──────────────────────────────────

  it("I-B1 — .atelier-salon-invitation-card is defined", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-invitation-card {"),
      "Missing .atelier-salon-invitation-card",
    );
  });

  it("I-B2 — .atelier-salon-invitation-lead uses Fraunces font", () => {
    const hasClass = globalsCss.includes(".atelier-salon-invitation-lead {");
    const hasFraunces =
      globalsCss.includes("var(--font-fraunces)") &&
      globalsCss.indexOf(".atelier-salon-invitation-lead") <
        globalsCss.lastIndexOf("var(--font-fraunces)");
    assert.ok(hasClass, "Missing .atelier-salon-invitation-lead");
    assert.ok(hasFraunces, ".atelier-salon-invitation-lead must use var(--font-fraunces)");
  });

  it("I-B3 — .atelier-salon-invitation-hint uses uppercase letter-spacing", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-invitation-hint"),
      "Missing .atelier-salon-invitation-hint",
    );
    const hintSection = globalsCss.slice(
      globalsCss.indexOf(".atelier-salon-invitation-hint"),
      globalsCss.indexOf(".atelier-salon-invitation-hint") + 300,
    );
    assert.ok(
      hintSection.includes("text-transform: uppercase"),
      ".atelier-salon-invitation-hint must use text-transform: uppercase",
    );
  });

  it("I-B4 — invitation card has reduced-motion guard on transform", () => {
    const afterInvitation = globalsCss.slice(
      globalsCss.indexOf(".atelier-salon-invitation-card {"),
    );
    assert.ok(
      afterInvitation.includes("transform: none"),
      "Invitation card must suppress translateY(-1px) under prefers-reduced-motion",
    );
  });

  // ── I-C: Results header CSS ───────────────────────────────────────────────

  it("I-C1 — .atelier-salon-results-header is defined", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-results-header {"),
      "Missing .atelier-salon-results-header",
    );
  });

  it("I-C2 — .atelier-salon-results-count uses Fraunces font", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-results-count"),
      "Missing .atelier-salon-results-count",
    );
  });

  it("I-C3 — results header animation has reduced-motion guard", () => {
    const afterResults = globalsCss.slice(
      globalsCss.indexOf(".atelier-salon-results-header {"),
    );
    assert.ok(
      afterResults.includes("salonRevealUp"),
      "Missing salonRevealUp animation",
    );
    assert.ok(
      afterResults.slice(0, afterResults.indexOf(".atelier-salon-results-count")).includes(
        "prefers-reduced-motion: reduce",
      ) || globalsCss.includes("prefers-reduced-motion: reduce"),
      "Results header animation must have reduced-motion guard",
    );
  });

  // ── I-D: Briefing rail dossier CSS ────────────────────────────────────────

  it("I-D1 — .atelier-salon-briefing-title is defined", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-briefing-title {"),
      "Missing .atelier-salon-briefing-title",
    );
  });

  it("I-D2 — .atelier-salon-briefing-no is defined for roman numerals", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-briefing-no {"),
      "Missing .atelier-salon-briefing-no",
    );
  });

  it("I-D3 — .atelier-salon-briefing-badge is defined", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-briefing-badge {"),
      "Missing .atelier-salon-briefing-badge",
    );
  });

  it("I-D4 — .atelier-salon-briefing-rule is defined", () => {
    assert.ok(
      globalsCss.includes(".atelier-salon-briefing-rule {"),
      "Missing .atelier-salon-briefing-rule",
    );
  });

  // ── I-E: ConciergePage wiring ─────────────────────────────────────────────

  it("I-E1 — ConciergePage renders concierge-portal testid", () => {
    assert.ok(
      conciergePage.includes('data-testid="concierge-portal"'),
      "ConciergePage must render data-testid=\"concierge-portal\"",
    );
  });

  it("I-E2 — ConciergePage invitation buttons use atelier-salon-invitation-card", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-invitation-card"),
      "ConciergePage invitation chip buttons must include atelier-salon-invitation-card class",
    );
  });

  it("I-E3 — ConciergePage invitation buttons render lead span", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-invitation-lead"),
      "ConciergePage must render atelier-salon-invitation-lead spans inside chips",
    );
  });

  it("I-E4 — ConciergePage invitation buttons render hint span", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-invitation-hint"),
      "ConciergePage must render atelier-salon-invitation-hint spans inside chips",
    );
  });

  it("I-E5 — ConciergePage renders atelier-salon-results-header on results", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-results-header"),
      "ConciergePage must render atelier-salon-results-header for result sections",
    );
  });

  it("I-E6 — ConciergePage briefing rail uses atelier-salon-briefing-title", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-briefing-title"),
      "Briefing rail must use atelier-salon-briefing-title (dossier upgrade)",
    );
  });

  it("I-E7 — ConciergePage briefing rail uses DOSSIER_ITEMS", () => {
    assert.ok(
      conciergePage.includes("DOSSIER_ITEMS"),
      "Briefing rail must render from DOSSIER_ITEMS constant",
    );
  });

  it("I-E8 — ConciergePage briefing rail renders roman numeral no class", () => {
    assert.ok(
      conciergePage.includes("atelier-salon-briefing-no"),
      "Briefing rail items must use atelier-salon-briefing-no for roman numerals",
    );
  });

  it("I-E9 — ConciergePage has no raw rgba() (test B14 compatibility)", () => {
    assert.ok(
      !conciergePage.includes("rgba("),
      "ConciergePage.tsx must not contain raw rgba() — use color-mix() or CSS vars",
    );
  });

  it("I-E10 — SALON_INVITATIONS constant is defined", () => {
    assert.ok(
      conciergePage.includes("SALON_INVITATIONS"),
      "ConciergePage must define and use SALON_INVITATIONS constant",
    );
  });
});
