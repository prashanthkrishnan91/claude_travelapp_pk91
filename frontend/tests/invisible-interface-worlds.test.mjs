/**
 * Invisible Interface — World System
 *
 * Verifies that:
 *   A. The locationData / worldData library exposes the required shape and
 *      a curated set of canonical worlds.
 *   B. The World component family is exported and binds CSS variables
 *      from locationData (no hardcoded destination styling in components).
 *   C. globals.css ships the --world-* CSS-variable contract plus all
 *      reusable world-aware classes (world-canvas, world-atmosphere,
 *      world-portal, world-room-switcher, world-wayfinder).
 *   D. Reduced-motion + mobile budget guards exist.
 *   E. DashboardClient adopts the world system (binds variables, renders
 *      the room switcher, derives the world from the active trip).
 *   F. No hardcoded Portland-specific styling in components — must flow
 *      through worldData.
 */

import test, { describe } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

function readSrc(rel) {
  return readFileSync(new URL(`../src/${rel}`, import.meta.url), "utf8");
}

const worldData       = readSrc("lib/worldData.ts");
const worldTsx        = readSrc("components/ui/World.tsx");
const globalsCss      = readSrc("app/globals.css");
const dashboardClient = readSrc("components/dashboard/DashboardClient.tsx");

// ── A. locationData shape + canonical world library ─────────────────────────

describe("World System: locationData shape and curated worlds", () => {
  test("A1. worldData.ts exports LocationData interface", () => {
    assert.ok(
      worldData.includes("export interface LocationData"),
      "worldData.ts must export LocationData interface",
    );
  });

  test("A2. LocationData has the six core required fields per the brief", () => {
    const idx = worldData.indexOf("export interface LocationData");
    const block = worldData.slice(idx, worldData.indexOf("}", idx));
    for (const field of [
      "location",
      "mood",
      "primaryColor",
      "secondaryColor",
      "backgroundStyle",
      "typographyTheme",
    ]) {
      assert.ok(
        new RegExp(`\\b${field}\\b`).test(block),
        `LocationData must declare \`${field}\` field`,
      );
    }
  });

  test("A2b. LocationData declares the visualLayer scenery contract", () => {
    const idx = worldData.indexOf("export interface LocationData");
    const block = worldData.slice(idx, worldData.indexOf("}", idx));
    assert.ok(
      /\bvisualLayer\b/.test(block),
      "LocationData must declare `visualLayer` (scenery image + overlay)",
    );
    const v = worldData.indexOf("export interface WorldVisualLayer");
    assert.ok(v !== -1, "WorldVisualLayer interface must be exported");
    const vblock = worldData.slice(v, worldData.indexOf("}", v));
    for (const field of [
      "sceneryLayers",
      "overlay",
      "mistTint",
    ]) {
      assert.ok(
        new RegExp(`\\b${field}\\b`).test(vblock),
        `WorldVisualLayer must declare \`${field}\` field`,
      );
    }
  });

  test("A3. Curated WORLD_LIBRARY exists and is exported", () => {
    assert.ok(
      worldData.includes("export const WORLD_LIBRARY"),
      "worldData.ts must export WORLD_LIBRARY",
    );
  });

  test("A4. Curated worlds Portland / Santorini / Kyoto / Marrakech are present", () => {
    for (const city of ["Portland", "Santorini", "Kyoto", "Marrakech"]) {
      assert.ok(
        worldData.includes(`location: "${city}"`),
        `worldData.ts must include the ${city} world`,
      );
    }
  });

  test("A4b. Every curated world ships a visualLayer with painted scenery", () => {
    // All five curated worlds + the Atelier fallback must declare a visualLayer.
    // A simple proxy check: the file must include `visualLayer:` at least 6×.
    const count = (worldData.match(/visualLayer:\s*\{/g) ?? []).length;
    assert.ok(
      count >= 6,
      `worldData.ts must declare a visualLayer for every curated world (>= 6), got ${count}`,
    );
    // Portland in particular must declare its mist + forest scenery.
    const portlandIdx = worldData.indexOf('location: "Portland"');
    assert.ok(portlandIdx !== -1);
    const portlandBlock = worldData.slice(portlandIdx, portlandIdx + 2200);
    assert.ok(
      portlandBlock.includes("sceneryLayers"),
      "Portland world must declare a sceneryLayers stack",
    );
    assert.ok(
      portlandBlock.includes("overlay"),
      "Portland world must declare an overlay tint",
    );
  });

  test("A5. pickWorldFromDestination is exported and falls back to Atelier", () => {
    assert.ok(
      worldData.includes("export function pickWorldFromDestination"),
      "worldData.ts must export pickWorldFromDestination",
    );
    assert.ok(
      worldData.includes("ATELIER_WORLD"),
      "worldData.ts must define an ATELIER_WORLD fallback",
    );
  });

  test("A6. worldStyleVars binds the --world-* CSS variable contract", () => {
    assert.ok(
      worldData.includes("export function worldStyleVars"),
      "worldData.ts must export worldStyleVars",
    );
    for (const v of [
      "--world-primary",
      "--world-secondary",
      "--world-ink",
      "--world-mist",
      "--world-bg",
      "--world-surface",
      "--world-shadow",
      "--world-accent",
      "--world-type-display",
      "--world-scenery",
      "--world-scenery-overlay",
      "--world-scenery-image",
      "--world-mist-tint",
    ]) {
      assert.ok(
        worldData.includes(v),
        `worldStyleVars must bind the ${v} CSS variable`,
      );
    }
  });

  test("A7. ROOM_CATALOGUE exposes the four canonical rooms", () => {
    assert.ok(
      worldData.includes("export const ROOM_CATALOGUE"),
      "worldData.ts must export ROOM_CATALOGUE",
    );
    for (const id of ["concierge", "explore", "planning", "saved"]) {
      assert.ok(
        worldData.includes(`id: "${id}"`),
        `ROOM_CATALOGUE must include room "${id}"`,
      );
    }
  });

  test("A8. applyRoom extends a world with archetype atmosphere", () => {
    assert.ok(
      worldData.includes("export function applyRoom"),
      "worldData.ts must export applyRoom",
    );
  });
});

// ── B. World component family ───────────────────────────────────────────────

describe("World System: React component family", () => {
  test("B1. World.tsx exports WorldCanvas", () => {
    assert.ok(
      worldTsx.includes("export function WorldCanvas"),
      "World.tsx must export WorldCanvas",
    );
  });

  test("B2. WorldCanvas accepts a locationData prop", () => {
    const idx = worldTsx.indexOf("export function WorldCanvas");
    const block = worldTsx.slice(idx, idx + 800);
    assert.ok(
      block.includes("locationData"),
      "WorldCanvas must accept a locationData prop",
    );
  });

  test("B3. WorldCanvas binds --world-* variables via inline style", () => {
    const idx = worldTsx.indexOf("export function WorldCanvas");
    const block = worldTsx.slice(idx, idx + 800);
    assert.ok(
      block.includes("worldStyleVars"),
      "WorldCanvas must apply worldStyleVars to its root container",
    );
  });

  test("B4. WorldAtmosphere is exported and decorative-only (aria-hidden)", () => {
    assert.ok(
      worldTsx.includes("export function WorldAtmosphere"),
      "World.tsx must export WorldAtmosphere",
    );
    const idx = worldTsx.indexOf("export function WorldAtmosphere");
    const block = worldTsx.slice(idx, idx + 600);
    assert.ok(
      block.includes('aria-hidden="true"'),
      "WorldAtmosphere must be aria-hidden (decorative)",
    );
  });

  test("B5. World.tsx exports WorldPortal, WorldWayfinder, WorldRoomSwitcher, WorldSurface, WorldHero", () => {
    for (const name of [
      "WorldPortal",
      "WorldWayfinder",
      "WorldRoomSwitcher",
      "WorldSurface",
      "WorldHero",
    ]) {
      assert.ok(
        worldTsx.includes(`export function ${name}`),
        `World.tsx must export ${name}`,
      );
    }
  });

  test("B5b. World.tsx exports the new scenery primitives — WorldScenery, WorldMist, WorldGlassSurface", () => {
    for (const name of ["WorldScenery", "WorldMist", "WorldGlassSurface"]) {
      assert.ok(
        worldTsx.includes(`export function ${name}`),
        `World.tsx must export ${name}`,
      );
    }
  });

  test("B5c. WorldScenery layers painted scenery + image + overlay (decorative, aria-hidden)", () => {
    const idx = worldTsx.indexOf("export function WorldScenery");
    const block = worldTsx.slice(idx, idx + 1000);
    assert.ok(block.includes('aria-hidden="true"'),
      "WorldScenery must be decorative (aria-hidden)");
    for (const slotClass of [
      "world-scenery-painted",
      "world-scenery-image",
      "world-scenery-overlay",
    ]) {
      assert.ok(
        block.includes(slotClass),
        `WorldScenery must render the ${slotClass} layer`,
      );
    }
  });

  test("B6. WorldRoomSwitcher generates a portal per room in ROOM_CATALOGUE", () => {
    const idx = worldTsx.indexOf("export function WorldRoomSwitcher");
    const block = worldTsx.slice(idx, idx + 800);
    assert.ok(
      block.includes("ROOM_CATALOGUE"),
      "WorldRoomSwitcher must iterate ROOM_CATALOGUE",
    );
    assert.ok(
      block.includes("WorldPortal"),
      "WorldRoomSwitcher must render WorldPortal children",
    );
  });

  test("B7. Components are world-agnostic — no Portland-specific colors", () => {
    assert.doesNotMatch(
      worldTsx,
      /#667A68|#B68A5A|Portland/,
      "World.tsx must not hardcode Portland-specific colors or strings — drive via locationData",
    );
  });
});

// ── C. globals.css world contract ───────────────────────────────────────────

describe("World System: CSS variable + class contract", () => {
  test("C1. globals.css defines default :root values for all --world-* vars", () => {
    for (const v of [
      "--world-primary",
      "--world-secondary",
      "--world-tertiary",
      "--world-ink",
      "--world-ink-mist",
      "--world-surface",
      "--world-mist",
      "--world-shadow",
      "--world-accent",
      "--world-bg",
      "--world-type-display",
    ]) {
      assert.ok(
        globalsCss.includes(v),
        `globals.css must declare ${v}`,
      );
    }
  });

  test("C2. globals.css defines the .world-canvas root class", () => {
    assert.ok(
      globalsCss.includes(".world-canvas {"),
      ".world-canvas must be defined",
    );
    const idx = globalsCss.indexOf(".world-canvas {");
    const block = globalsCss.slice(idx, idx + 600);
    assert.ok(
      block.includes("isolation: isolate"),
      ".world-canvas must isolate its stacking context",
    );
    assert.ok(
      block.includes("var(--world-bg)"),
      ".world-canvas must read its background from var(--world-bg)",
    );
  });

  test("C3. globals.css defines .world-atmosphere with mesh + blob layers", () => {
    assert.ok(globalsCss.includes(".world-atmosphere {"));
    assert.ok(globalsCss.includes(".world-atmosphere-mesh"));
    assert.ok(globalsCss.includes(".world-atmosphere-blob-a"));
    assert.ok(globalsCss.includes(".world-atmosphere-blob-b"));
    assert.ok(globalsCss.includes(".world-atmosphere-blob-c"));
  });

  test("C4. World blobs animate with luxury easing", () => {
    const idx = globalsCss.indexOf(".world-atmosphere-blob-a");
    const block = globalsCss.slice(idx, idx + 500);
    assert.ok(
      block.includes("cubic-bezier(0.16, 1, 0.3, 1)"),
      "world-atmosphere blobs must use the luxury cubic-bezier(0.16, 1, 0.3, 1) easing",
    );
  });

  test("C5. .world-portal exists and animates with luxury easing", () => {
    assert.ok(globalsCss.includes(".world-portal {"));
    const idx = globalsCss.indexOf(".world-portal {");
    const block = globalsCss.slice(idx, idx + 800);
    assert.ok(
      block.includes("cubic-bezier(0.16, 1, 0.3, 1)"),
      ".world-portal must transition with luxury cubic-bezier(0.16, 1, 0.3, 1)",
    );
    assert.ok(
      block.includes("var(--world-surface)"),
      ".world-portal must read its base surface from var(--world-surface)",
    );
  });

  test("C6. .world-room-switcher exists and uses asymmetric desktop offsets", () => {
    assert.ok(globalsCss.includes(".world-room-switcher {"));
    const idx = globalsCss.indexOf(".world-room-switcher {");
    const block = globalsCss.slice(idx, idx + 1400);
    assert.ok(
      block.includes("translateY"),
      ".world-room-switcher must offset portals vertically on desktop for editorial asymmetry",
    );
  });

  test("C7. .world-wayfinder exists and uses --world-ink-mist", () => {
    assert.ok(globalsCss.includes(".world-wayfinder {"));
    const idx = globalsCss.indexOf(".world-wayfinder {");
    const block = globalsCss.slice(idx, idx + 500);
    assert.ok(
      block.includes("var(--world-ink-mist)"),
      ".world-wayfinder must read its color from var(--world-ink-mist)",
    );
  });

  test("C8. .world-surface ships paper / mineral / glass variants", () => {
    assert.ok(globalsCss.includes(".world-surface {"));
    assert.ok(globalsCss.includes(".world-surface-mineral"));
    assert.ok(globalsCss.includes(".world-surface-glass"));
  });

  test("C9. .world-scenery ships painted / image / overlay slots + size variants", () => {
    assert.ok(globalsCss.includes(".world-scenery {"));
    assert.ok(globalsCss.includes(".world-scenery-painted"));
    assert.ok(globalsCss.includes(".world-scenery-image"));
    assert.ok(globalsCss.includes(".world-scenery-overlay"));
    assert.ok(globalsCss.includes(".world-scenery-tall"));
  });

  test("C10. .world-scenery layers animate with luxury easing (drift + breathe)", () => {
    assert.ok(
      /@keyframes world-scenery-(?:drift|breathe)/.test(globalsCss),
      "world-scenery layers must define drift/breathe keyframes",
    );
    const re = /\.world-scenery-(?:painted|image)[^{]*\{[\s\S]*?cubic-bezier\(0\.16,\s*1,\s*0\.3,\s*1\)/;
    assert.ok(
      re.test(globalsCss),
      ".world-scenery painted/image must use luxury cubic-bezier(0.16, 1, 0.3, 1)",
    );
  });

  test("C11. .world-mist drifts with luxury easing and tinted veils", () => {
    assert.ok(globalsCss.includes(".world-mist {"));
    assert.ok(globalsCss.includes(".world-mist-veil-a"));
    assert.ok(
      /@keyframes world-mist-drift-a/.test(globalsCss),
      "world-mist must define a drift keyframes animation",
    );
    assert.ok(
      /\.world-mist-veil-a[^{]*\{[\s\S]*?cubic-bezier\(0\.16,\s*1,\s*0\.3,\s*1\)/.test(globalsCss),
      "world-mist veils must use luxury cubic-bezier(0.16, 1, 0.3, 1)",
    );
  });

  test("C12. .world-glass-surface is translucent (backdrop-filter blur)", () => {
    assert.ok(globalsCss.includes(".world-glass-surface {"));
    const idx = globalsCss.indexOf(".world-glass-surface {");
    const block = globalsCss.slice(idx, idx + 800);
    assert.ok(
      /backdrop-filter:\s*blur\(/.test(block),
      ".world-glass-surface must use backdrop-filter blur (paper-glass)",
    );
  });

  test("C13. world-portal carries a doorframe + interior light layer", () => {
    assert.ok(globalsCss.includes(".world-portal-doorframe"),
      ".world-portal must include a doorframe layer (jamb/lintel)");
    assert.ok(globalsCss.includes(".world-portal-light"),
      ".world-portal must include an interior warm-light layer");
    assert.ok(globalsCss.includes(".world-portal-scenery"),
      ".world-portal must include a scenery layer behind the label");
  });
});

// ── D. Reduced-motion / mobile guards ───────────────────────────────────────

describe("World System: reduced-motion and mobile guards", () => {
  test("D1. world-atmosphere blob animations disabled under prefers-reduced-motion", () => {
    // Find a reduced-motion block that mentions a world-atmosphere-blob class.
    const reIdx = globalsCss.indexOf("@media (prefers-reduced-motion: reduce)");
    assert.ok(reIdx !== -1);
    assert.ok(
      globalsCss.includes(".world-atmosphere-blob-a,") ||
        globalsCss.match(/world-atmosphere-blob-[abc][^{]*\{[^}]*animation: none/),
      "world-atmosphere blob animations must be suppressed under prefers-reduced-motion",
    );
  });

  test("D2. world-portal transitions disabled under prefers-reduced-motion", () => {
    const re = /\.world-portal,\s*[\s\S]*?transition: none/;
    assert.ok(
      re.test(globalsCss),
      ".world-portal hover transition must be disabled under prefers-reduced-motion",
    );
  });

  test("D3. world-room-switcher offsets disabled under prefers-reduced-motion", () => {
    assert.ok(
      /\.world-room-switcher > \*[^{]*\{[^}]*transform: none/.test(globalsCss),
      ".world-room-switcher offsets must reset to none under prefers-reduced-motion",
    );
  });

  test("D4. world-atmosphere-blob-c hidden on mobile (≤600px) for render budget", () => {
    const mqIdx = globalsCss.indexOf("@media (max-width: 600px)");
    assert.ok(mqIdx !== -1, "globals.css must include the mobile (≤600px) media query");
    // Scan all mobile blocks for the c-blob suppression.
    let cursor = mqIdx;
    let found = false;
    while (cursor !== -1) {
      const slice = globalsCss.slice(cursor, cursor + 500);
      if (slice.includes("world-atmosphere-blob-c")) {
        found = true;
        break;
      }
      cursor = globalsCss.indexOf("@media (max-width: 600px)", cursor + 1);
    }
    assert.ok(found, "world-atmosphere-blob-c must be suppressed on mobile (≤600px)");
  });

  test("D5. mobile keeps at least one atmosphere blob animating (motion-visible on phones)", () => {
    // The previous build set `animation: none` on both blob-a and blob-b at
    // ≤600px, which made the screen feel static on phones. The brief
    // explicitly requires perceivable motion on mobile, so the mobile block
    // must not set `animation: none` on both primary blobs.
    const mobileBlocks = [];
    let cursor = globalsCss.indexOf("@media (max-width: 600px)");
    while (cursor !== -1) {
      // grab the whole block
      const open = globalsCss.indexOf("{", cursor);
      let depth = 1;
      let end = open + 1;
      while (depth > 0 && end < globalsCss.length) {
        const ch = globalsCss[end];
        if (ch === "{") depth += 1;
        else if (ch === "}") depth -= 1;
        end += 1;
      }
      mobileBlocks.push(globalsCss.slice(cursor, end));
      cursor = globalsCss.indexOf("@media (max-width: 600px)", end);
    }
    const blob = mobileBlocks.join("\n");
    const killedBoth =
      /world-atmosphere-blob-a[\s\S]*?animation:\s*none[\s\S]*?world-atmosphere-blob-b[\s\S]*?animation:\s*none/.test(blob) ||
      /world-atmosphere-blob-a,\s*\.world-atmosphere-blob-b\s*\{[^}]*animation:\s*none/.test(blob);
    assert.ok(
      !killedBoth,
      "mobile (≤600px) must not set animation:none on BOTH world-atmosphere-blob-a and -b — keep one drift visible",
    );
  });

  test("D6. world-scenery painted/image animation suppressed under prefers-reduced-motion", () => {
    const re = /@media \(prefers-reduced-motion:\s*reduce\)\s*\{[\s\S]*?\.world-scenery-(?:painted|image)[\s\S]*?animation:\s*none/;
    assert.ok(
      re.test(globalsCss),
      "world-scenery must disable scenery drift under prefers-reduced-motion",
    );
  });

  test("D7. world-mist veil animation suppressed under prefers-reduced-motion", () => {
    const re = /@media \(prefers-reduced-motion:\s*reduce\)\s*\{[\s\S]*?\.world-mist-veil[\s\S]*?animation:\s*none/;
    assert.ok(
      re.test(globalsCss),
      "world-mist must disable veil drift under prefers-reduced-motion",
    );
  });
});

// ── E. DashboardClient adoption ─────────────────────────────────────────────

describe("World System: DashboardClient adoption", () => {
  test("E1. DashboardClient imports pickWorldFromDestination + worldStyleVars", () => {
    assert.ok(dashboardClient.includes("pickWorldFromDestination"));
    assert.ok(dashboardClient.includes("worldStyleVars"));
  });

  test("E2. DashboardClient imports the world scenery primitives + WorldRoomSwitcher", () => {
    for (const name of [
      "WorldAtmosphere",
      "WorldRoomSwitcher",
      "WorldScenery",
      "WorldMist",
      "WorldGlassSurface",
    ]) {
      assert.ok(
        dashboardClient.includes(name),
        `DashboardClient must import ${name}`,
      );
    }
  });

  test("E3. Root <FolioScene> receives world-canvas class + worldStyleVars style", () => {
    const ret = dashboardClient.slice(dashboardClient.indexOf("return ("));
    assert.match(ret, /<FolioScene[\s\S]*?world-canvas/);
    assert.match(ret, /style=\{worldStyleVars\(world\)\}/);
  });

  test("E4. Home renders the WorldScenery layer above content (scenery does orientation)", () => {
    const ret = dashboardClient.slice(dashboardClient.indexOf("return ("));
    assert.match(
      ret,
      /<WorldScenery[\s\S]*?\/>/,
      "DashboardClient must mount <WorldScenery /> as the top environmental layer",
    );
    // The greeting itself must no longer print the world description line
    // as a top-of-page WorldWayfinder. Scenery is the orientation now.
    const start = dashboardClient.indexOf("function AtelierGreeting");
    const end   = dashboardClient.indexOf("function ConciergeEntry");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      !block.includes("WorldWayfinder"),
      "AtelierGreeting must NOT render WorldWayfinder as the primary top line — scenery does the orientation",
    );
  });

  test("E4b. WorldMist drift layer is mounted on the home canvas", () => {
    const ret = dashboardClient.slice(dashboardClient.indexOf("return ("));
    assert.match(
      ret,
      /<WorldMist\s*\/>/,
      "DashboardClient must mount <WorldMist /> for perceivable atmosphere drift",
    );
  });

  test("E5. AtelierPlanningStrip renders the WorldRoomSwitcher", () => {
    const start = dashboardClient.indexOf("function AtelierPlanningStrip");
    const end   = dashboardClient.indexOf("// ── Main component");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("WorldRoomSwitcher"),
      "AtelierPlanningStrip must render WorldRoomSwitcher (4 room portals)",
    );
  });

  test("E5b. No hidden legacy artifact tiles remain (no sr-only legacy duplicate UI)", () => {
    assert.doesNotMatch(
      dashboardClient,
      /data-legacy-artifact|FolioArtifactTile/,
      "DashboardClient must not preserve legacy artifact tiles via sr-only — update tests instead",
    );
  });

  test("E6. Current world is derived from continuePlanning.destination", () => {
    assert.match(
      dashboardClient,
      /pickWorldFromDestination\(continuePlanning\?\.destination\)/,
      "DashboardClient must derive its world from the active trip destination",
    );
  });

  test("E7. WorldAtmosphere is mounted inside the canvas (not in flow)", () => {
    const ret = dashboardClient.slice(dashboardClient.indexOf("return ("));
    assert.match(ret, /<WorldAtmosphere\s*\/>/);
  });

  test("E8. Existing testids preserved alongside world adoption", () => {
    for (const id of [
      "atelier-home",
      "atelier-greeting",
      "concierge-entry",
      "atelier-continue-planning",
      "journey-shelf-teaser",
      "atelier-planning-strip",
      "home-new-trip-action",
    ]) {
      assert.match(
        dashboardClient,
        new RegExp(`data-testid="${id}"`),
        `data-testid="${id}" must remain in DashboardClient`,
      );
    }
  });

  test("E9. AtelierGreeting floats on the scenery via WorldGlassSurface", () => {
    const start = dashboardClient.indexOf("function AtelierGreeting");
    const end   = dashboardClient.indexOf("function ConciergeEntry");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("WorldGlassSurface"),
      "AtelierGreeting must wrap its content in WorldGlassSurface (paper-glass over scenery)",
    );
  });
});

// ── F. Anti-regression: no destination-specific hardcoding in components ────

describe("World System: components stay world-agnostic", () => {
  test("F1. DashboardClient does not hardcode a destination color", () => {
    // Components must drive everything through worldData / CSS vars.
    assert.doesNotMatch(
      dashboardClient,
      /background:\s*linear-gradient\([^)]*Portland|Santorini|Kyoto|Marrakech/i,
      "DashboardClient must not hardcode destination-specific gradients",
    );
  });

  test("F2. World.tsx renders no destination strings directly", () => {
    assert.doesNotMatch(
      worldTsx,
      /\bPortland\b|\bSantorini\b|\bKyoto\b|\bMarrakech\b/,
      "World.tsx must not mention specific destinations — they live in worldData",
    );
  });
});
