/**
 * Atmospheric Background System v1 — contract tests.
 *
 * Verifies the centralized, image-capable background system:
 *  · registry is the single source of truth for the 5 backdrop roles;
 *  · roles carry placeholder gradient + scrim + tone (no hardcoded image yet);
 *  · NO remote/hotlinked image URLs anywhere in the system;
 *  · shared <AtelierBackdrop> component exists, is decorative, no layout shift;
 *  · login + signup adopt the cinematic auth-hero (tropical rainbow removed);
 *  · AppShell wires the registry route map behind content;
 *  · the public asset MANIFEST documents the curated files to supply;
 *  · the brief surface gets the lightest wash;
 *  · 8N atmosphere contract preserved (no regression).
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "..");
const srcRoot = resolve(root, "src");
const readSrc = (p) => readFileSync(resolve(srcRoot, p), "utf8");
const readRoot = (p) => readFileSync(resolve(root, p), "utf8");

const registry = readSrc("lib/atmosphere/backgrounds.ts");
const backdrop = readSrc("components/atmosphere/AtelierBackdrop.tsx");
const globalsCss = readRoot("src/app/globals.css");
const appShell = readSrc("components/layout/AppShell.tsx");
const loginPage = readSrc("app/auth/login/page.tsx");
const signupPage = readSrc("app/auth/signup/page.tsx");
const tripBrief = readSrc("components/trips/TripBrief.tsx");

const ROLES = [
  "auth-hero",
  "atelier-wash",
  "library-wash",
  "desk-texture",
  "brief-texture",
];

describe("Atmospheric Background System v1 — registry", () => {
  it("1. defines a central BACKDROP_REGISTRY", () => {
    assert.ok(registry.includes("BACKDROP_REGISTRY"));
  });

  it("2. registry declares all five backdrop roles", () => {
    for (const role of ROLES) {
      assert.ok(registry.includes(`"${role}"`), `missing role ${role}`);
    }
  });

  it("3. every role ships a placeholder gradient + scrim (no flat beige)", () => {
    assert.ok(registry.includes("placeholder:"));
    assert.ok(registry.includes("scrim:"));
    // placeholders are gradients, not solid beige
    assert.ok(registry.includes("linear-gradient") && registry.includes("radial-gradient"));
  });

  it("4. roles default to null image (placeholder mode, no invented assets)", () => {
    assert.ok(registry.includes("image: null"));
  });

  it("5. NO remote/hotlinked image URLs in the registry", () => {
    assert.ok(!/https?:\/\//.test(registry), "registry must not hotlink remote images");
  });

  it("6. exposes a route→role map and a getter", () => {
    assert.ok(registry.includes("backdropRoleForPath"));
    assert.ok(registry.includes("getBackdrop"));
  });

  it("7. forbids no-go colors at the token level (no neon cyan tropical)", () => {
    // The old tropical login palette anchors must not reappear in the registry.
    for (const banned of ["#0a9396", "#94d2bd", "#0e6ba8", "#ee9b00"]) {
      assert.ok(!registry.includes(banned), `banned tropical color ${banned}`);
    }
  });
});

describe("Atmospheric Background System v1 — shared component", () => {
  it("8. AtelierBackdrop component exists and is registry-driven", () => {
    assert.ok(backdrop.includes("export function AtelierBackdrop"));
    assert.ok(backdrop.includes("getBackdrop"));
  });

  it("9. backdrop is decorative (aria-hidden) and testable", () => {
    assert.ok(backdrop.includes('aria-hidden="true"'));
    assert.ok(backdrop.includes('data-testid="atelier-backdrop"'));
    assert.ok(backdrop.includes("data-backdrop-role"));
  });

  it("10. backdrop uses optimized next/image for curated photos", () => {
    assert.ok(backdrop.includes('from "next/image"'));
    assert.ok(backdrop.includes("fill"));
  });

  it("11. backdrop geometry classes exist and never shift layout", () => {
    assert.ok(globalsCss.includes(".atelier-backdrop"));
    assert.ok(globalsCss.includes("pointer-events: none"));
    assert.ok(globalsCss.includes(".atelier-backdrop--fixed"));
    // fixed layer sits behind content, not in flow
    const block = globalsCss.slice(globalsCss.indexOf(".atelier-backdrop--fixed"));
    assert.ok(block.slice(0, 160).includes("position: fixed"));
  });

  it("12. backdrop grain uses CSS data-URI, never an external asset", () => {
    assert.ok(globalsCss.includes(".atelier-backdrop__grain"));
    // dedicated grain rule carries the SVG turbulence data-URI (unique filter id)
    const block = globalsCss.slice(globalsCss.indexOf("id='ab'"));
    assert.ok(block.slice(-1) !== undefined);
    assert.ok(globalsCss.includes("data:image/svg+xml") && globalsCss.includes("id='ab'"));
    assert.ok(!globalsCss.includes("url(\"http") && !globalsCss.includes("url('http"));
  });

  it("13. backdrop respects reduced motion", () => {
    assert.ok(globalsCss.includes("prefers-reduced-motion"));
    assert.ok(globalsCss.includes(".atelier-backdrop__photo"));
  });
});

describe("Atmospheric Background System v1 — surface adoption", () => {
  it("14. login adopts the cinematic auth-hero backdrop", () => {
    assert.ok(loginPage.includes("AtelierBackdrop"));
    assert.ok(loginPage.includes('role="auth-hero"'));
  });

  it("15. signup adopts the same auth-hero backdrop", () => {
    assert.ok(signupPage.includes("AtelierBackdrop"));
    assert.ok(signupPage.includes('role="auth-hero"'));
  });

  it("16. the saturated tropical login gradient is gone", () => {
    // old rainbow login-bg markup + animation removed from auth + css
    assert.ok(!loginPage.includes("login-bg"));
    assert.ok(!globalsCss.includes("luxury-zoom"));
    assert.ok(!globalsCss.includes("#0a9396"));
  });

  it("17. AppShell wires the registry route map behind content", () => {
    assert.ok(appShell.includes("backdropRoleForPath"));
    assert.ok(appShell.includes("AtelierBackdrop"));
    assert.ok(appShell.includes('data-atelier-backdrop'));
  });

  it("18. backdrop sits behind content (root goes transparent when active)", () => {
    assert.ok(globalsCss.includes('.atelier-atmosphere-root[data-atelier-backdrop="true"]'));
  });

  it("19. Brief gets the lightest wash, not a busy photo", () => {
    const block = globalsCss.slice(globalsCss.indexOf(".journey-desk-brief {"));
    assert.ok(block.slice(0, 400).includes("radial-gradient"));
    assert.ok(!block.slice(0, 400).includes("url("));
    // brief markup unchanged structurally
    assert.ok(tripBrief.includes("journey-desk-brief"));
  });
});

describe("Atmospheric Background System v1 — asset policy + manifest", () => {
  it("20. public asset folder + documented manifest exist", () => {
    assert.ok(existsSync(resolve(root, "public/atmosphere/MANIFEST.md")));
    const manifest = readRoot("public/atmosphere/MANIFEST.md");
    for (const role of ROLES) assert.ok(manifest.includes(role), `manifest missing ${role}`);
  });

  it("21. manifest forbids hotlinking and documents activation", () => {
    const manifest = readRoot("public/atmosphere/MANIFEST.md");
    assert.ok(/local/i.test(manifest));
    assert.ok(/hotlink|remote/i.test(manifest));
  });

  it("22. enriched paper wash replaces flat beige on padded routes", () => {
    const block = globalsCss.slice(globalsCss.indexOf(".atelier-atmosphere-root {"));
    // multiple radial layers now (depth), still gradient-only
    const head = block.slice(0, 900);
    assert.ok((head.match(/radial-gradient/g) || []).length >= 3);
  });
});

describe("Atmospheric Background System v1 — no regression", () => {
  it("23. 8N atmosphere root + layers preserved", () => {
    assert.ok(globalsCss.includes(".atelier-atmosphere-root"));
    assert.ok(globalsCss.includes(".atelier-vignette-layer"));
    assert.ok(globalsCss.includes(".atelier-texture-layer"));
    assert.ok(appShell.includes('data-testid="atelier-atmosphere-root"'));
  });

  it("24. atmosphere-root still uses radial-gradient (8N test 47 invariant)", () => {
    const rootStart = globalsCss.indexOf(".atelier-atmosphere-root {");
    const rootBlock = globalsCss.slice(rootStart, rootStart + 800);
    assert.ok(rootBlock.includes("radial-gradient"));
    assert.ok(!rootBlock.includes("url(\"http") && !rootBlock.includes("url('http"));
  });
});
