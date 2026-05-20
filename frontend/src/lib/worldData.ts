// ════════════════════════════════════════════════════════════════
// Invisible Interface — Location DNA / World Data
//
// A "world" is the sensory identity of a destination expressed as
// design tokens. Components do not know what Portland looks like —
// they only know the shape of a `LocationData` object. The world
// drives the environment: ambient colors, background mesh, surface
// tinting, type voice. Components stay world-agnostic.
//
// Add a new destination by adding a new entry to `WORLD_LIBRARY` —
// no component edits required.
// ════════════════════════════════════════════════════════════════

import type { CSSProperties } from "react";

/** The shape every world-aware component reads from. */
export interface LocationData {
  /** Canonical city/place name shown in the wayfinder. */
  location: string;
  /** One-line sensory mood — quiet, editorial, place-specific. */
  mood: string;
  /** Primary world hue (deep, surface-friendly). */
  primaryColor: string;
  /** Secondary hue (accent / brass / sun / sea / lantern). */
  secondaryColor: string;
  /** Tertiary atmospheric hue used in mesh gradient layers. */
  tertiaryColor: string;
  /** Ink color for body type on this world's paper. */
  inkColor: string;
  /** Quieter ink — labels, meta. */
  inkMistColor: string;
  /** Surface base — the paper/sand/stone the room sits on. */
  surfaceColor: string;
  /** Mist/haze color used for soft horizon washes. */
  mistColor: string;
  /** Shadow warmth — added behind floating surfaces. */
  shadowColor: string;
  /** Full background style string — mesh + linear washes. */
  backgroundStyle: string;
  /** Typography theme — drives type-display family selection. */
  typographyTheme: "serif-editorial" | "serif-warm" | "serif-spare" | "serif-lantern";
  /** Optional: a short room archetype this world reads like. */
  archetype?: "atelier" | "salon" | "observatory" | "gallery" | "scrapbook" | "residence";
  /**
   * Environment / scenery layer — drives the cinematic top-fold image the
   * user feels before they read a label. Curated worlds ship one. Generic
   * destinations fall back to the Atelier visualLayer.
   *
   * The shape is intentionally generic so a curator can swap a CSS-only
   * painted scene for a photographic asset without component edits.
   */
  visualLayer: WorldVisualLayer;
}

export interface WorldVisualLayer {
  /**
   * Optional full-bleed environmental photograph URL. When absent, the
   * `sceneryLayers` field stands alone as image-like CSS scenery. When
   * present, sceneryLayers paint behind/over the image to keep the
   * destination feeling intact if the network is slow.
   *
   * This is a *mood* asset, not a factual itinerary image — it sits in
   * the environment, never inside a card that asserts a place exists.
   */
  imageUrl?: string;
  /** Alt label for the environmental image (decorative, but useful). */
  imageAlt?: string;
  /** CSS object-position for image framing (e.g. "center 40%"). */
  imagePosition?: string;
  /** CSS filter applied to the image (e.g. "saturate(0.85) brightness(0.95)"). */
  imageFilter?: string;
  /**
   * Painted scenic background stack — CSS image-like gradients that
   * compose forest / sea / paper-shadow / textile scenery. Works as the
   * standalone scenery when no photo is supplied, and as the
   * tone/atmosphere layer over the photo when one is supplied.
   */
  sceneryLayers: string;
  /**
   * Top overlay tinted to the world's palette — keeps content readable
   * over the scenery while still letting the destination breathe.
   */
  overlay: string;
  /** Soft mist tint used by the WorldMist drifting layer. */
  mistTint: string;
  /**
   * Luminance-aware contrast hint for text rendered ON the scenery.
   * `light` = scenery is dark, text should be cream/paper.
   * `dark`  = scenery is light, text should be charcoal/ink.
   * Drives the `--world-on-scenery`, `--world-on-scenery-muted`,
   * and `--world-scenery-scrim` CSS variables consumed by any
   * scenic-overlay surface (dossier covers, portals, glass scrims).
   */
  contrastTone?: "light" | "dark";
}

// ─── Curated worlds — sensory DNA per destination ──────────────────────────────
//
// These were composed as palettes, not photo-grabs. Every color has been
// checked for legibility against `surfaceColor`. Add new worlds as needed.

// Painted "cedar grove + Pacific mist" scenery — used standalone or as the
// atmospheric layer over a photographic image. Composes:
//  · deep evergreen body / forest floor
//  · stacked cedar silhouettes (radial cones + ellipses)
//  · soft drift mist near the horizon
const PORTLAND_SCENERY = [
  // distant tree-line silhouette, low and soft
  "radial-gradient(ellipse 38% 14% at 12% 64%, rgba(31, 42, 34, 0.55), transparent 70%)",
  "radial-gradient(ellipse 28% 10% at 32% 60%, rgba(31, 42, 34, 0.5), transparent 72%)",
  "radial-gradient(ellipse 42% 16% at 60% 66%, rgba(31, 42, 34, 0.55), transparent 70%)",
  "radial-gradient(ellipse 34% 12% at 84% 62%, rgba(31, 42, 34, 0.5), transparent 72%)",
  // tall cedars — narrow, deep evergreens
  "radial-gradient(ellipse 6% 28% at 18% 70%, rgba(20, 32, 25, 0.6), transparent 65%)",
  "radial-gradient(ellipse 5% 24% at 42% 68%, rgba(20, 32, 25, 0.55), transparent 65%)",
  "radial-gradient(ellipse 7% 32% at 72% 72%, rgba(20, 32, 25, 0.6), transparent 65%)",
  "radial-gradient(ellipse 5% 26% at 88% 70%, rgba(20, 32, 25, 0.55), transparent 65%)",
  // valley mist drifting through the trees
  "linear-gradient(180deg, transparent 0%, transparent 42%, rgba(232, 236, 229, 0.55) 56%, rgba(232, 236, 229, 0.32) 72%, transparent 88%)",
  // canopy haze / Pacific drizzle in the air
  "radial-gradient(ellipse 90% 50% at 50% 18%, rgba(186, 198, 188, 0.5), transparent 70%)",
  // deep forest body
  "linear-gradient(178deg, #C8D2C2 0%, #9CB0A1 40%, #5E6E5F 78%, #2E3A30 100%)",
].join(", ");

const PORTLAND: LocationData = {
  location: "Portland",
  mood: "Misty forest, quiet streets, cedar warmth",
  primaryColor: "#3F5546",
  secondaryColor: "#B68A5A",
  tertiaryColor: "#8AA092",
  inkColor: "#1F2A22",
  inkMistColor: "#5A6A5D",
  surfaceColor: "#F2EEE4",
  mistColor: "rgba(138, 160, 146, 0.45)",
  shadowColor: "rgba(31, 42, 34, 0.18)",
  backgroundStyle: [
    "radial-gradient(ellipse 80% 50% at 18% 12%, rgba(138, 160, 146, 0.32), transparent 65%)",
    "radial-gradient(ellipse 70% 40% at 88% 78%, rgba(182, 138, 90, 0.20), transparent 70%)",
    "radial-gradient(ellipse 60% 50% at 50% 100%, rgba(63, 85, 70, 0.18), transparent 75%)",
    "linear-gradient(178deg, #F4F1E8 0%, #E9E5D6 100%)",
  ].join(", "),
  typographyTheme: "serif-editorial",
  archetype: "atelier",
  visualLayer: {
    imageUrl:
      "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=1600&q=80",
    imageAlt: "Mist drifting between tall evergreen trees",
    imagePosition: "center 55%",
    imageFilter: "saturate(0.78) brightness(0.92) contrast(1.02)",
    sceneryLayers: PORTLAND_SCENERY,
    overlay: [
      "linear-gradient(180deg, rgba(31, 42, 34, 0.12) 0%, rgba(242, 238, 228, 0.0) 38%, rgba(242, 238, 228, 0.55) 72%, rgba(242, 238, 228, 0.86) 100%)",
      "radial-gradient(ellipse 90% 55% at 50% 100%, rgba(242, 238, 228, 0.72), transparent 70%)",
    ].join(", "),
    mistTint: "rgba(186, 198, 188, 0.55)",
    contrastTone: "light",
  },
};

const SANTORINI_SCENERY = [
  // sun-bleached cubic village silhouette near horizon
  "linear-gradient(180deg, transparent 50%, rgba(250, 247, 240, 0.7) 58%, rgba(250, 247, 240, 0.4) 68%, transparent 78%)",
  // soft caldera haze
  "radial-gradient(ellipse 70% 28% at 50% 62%, rgba(123, 168, 194, 0.35), transparent 70%)",
  // sun bloom
  "radial-gradient(ellipse 55% 30% at 75% 18%, rgba(255, 232, 196, 0.6), transparent 70%)",
  // sea
  "linear-gradient(180deg, #DDE5EA 0%, #A8C2D2 40%, #5B8DA8 72%, #2E587A 100%)",
].join(", ");

const SANTORINI: LocationData = {
  location: "Santorini",
  mood: "Sun-drenched mineral white, salt and sea haze",
  primaryColor: "#1F4256",
  secondaryColor: "#E0B888",
  tertiaryColor: "#7BA8C2",
  inkColor: "#152E3E",
  inkMistColor: "#4A6680",
  surfaceColor: "#FAF7F0",
  mistColor: "rgba(123, 168, 194, 0.40)",
  shadowColor: "rgba(21, 46, 62, 0.16)",
  backgroundStyle: [
    "radial-gradient(ellipse 90% 55% at 50% 0%, rgba(224, 184, 136, 0.28), transparent 70%)",
    "radial-gradient(ellipse 70% 50% at 12% 88%, rgba(123, 168, 194, 0.30), transparent 70%)",
    "radial-gradient(ellipse 60% 50% at 92% 60%, rgba(31, 66, 86, 0.18), transparent 75%)",
    "linear-gradient(180deg, #FBF8F1 0%, #EDE6D7 100%)",
  ].join(", "),
  typographyTheme: "serif-spare",
  archetype: "gallery",
  visualLayer: {
    imageUrl:
      "https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=1600&q=80",
    imageAlt: "Sunlit blue horizon over the sea",
    imagePosition: "center 45%",
    imageFilter: "saturate(0.88) brightness(1.02)",
    sceneryLayers: SANTORINI_SCENERY,
    overlay: [
      "linear-gradient(180deg, rgba(21, 46, 62, 0.12) 0%, transparent 32%, rgba(250, 247, 240, 0.5) 70%, rgba(250, 247, 240, 0.86) 100%)",
    ].join(", "),
    mistTint: "rgba(212, 224, 232, 0.5)",
    contrastTone: "dark",
  },
};

const KYOTO_SCENERY = [
  // shoji paper grid pattern hint — vertical paper panels
  "repeating-linear-gradient(90deg, rgba(60, 42, 24, 0.06) 0px, rgba(60, 42, 24, 0.06) 1px, transparent 1px, transparent 96px)",
  "repeating-linear-gradient(0deg, rgba(60, 42, 24, 0.05) 0px, rgba(60, 42, 24, 0.05) 1px, transparent 1px, transparent 140px)",
  // lantern warmth low-right
  "radial-gradient(ellipse 28% 22% at 78% 78%, rgba(232, 168, 90, 0.55), transparent 70%)",
  // bamboo shadow cluster on the left
  "radial-gradient(ellipse 6% 36% at 12% 60%, rgba(34, 21, 13, 0.4), transparent 65%)",
  "radial-gradient(ellipse 5% 30% at 22% 64%, rgba(34, 21, 13, 0.35), transparent 65%)",
  // dusk paper wash
  "linear-gradient(176deg, #F1DDB6 0%, #D8B57F 45%, #8E6A45 88%, #3D2F26 100%)",
].join(", ");

const KYOTO: LocationData = {
  location: "Kyoto",
  mood: "Paper and shadow, stillness, lantern warmth",
  primaryColor: "#3D2F26",
  secondaryColor: "#C5944D",
  tertiaryColor: "#8E6A45",
  inkColor: "#22150D",
  inkMistColor: "#5A4632",
  surfaceColor: "#EFE7D2",
  mistColor: "rgba(142, 106, 69, 0.32)",
  shadowColor: "rgba(34, 21, 13, 0.22)",
  backgroundStyle: [
    "radial-gradient(ellipse 65% 50% at 22% 18%, rgba(197, 148, 77, 0.28), transparent 65%)",
    "radial-gradient(ellipse 70% 50% at 82% 82%, rgba(61, 47, 38, 0.22), transparent 70%)",
    "radial-gradient(ellipse 55% 45% at 50% 50%, rgba(142, 106, 69, 0.14), transparent 75%)",
    "linear-gradient(176deg, #F3ECD6 0%, #E2D7B5 100%)",
  ].join(", "),
  typographyTheme: "serif-lantern",
  archetype: "salon",
  visualLayer: {
    imageUrl:
      "https://images.unsplash.com/photo-1493997181344-712f2f19d87a?auto=format&fit=crop&w=1600&q=80",
    imageAlt: "Soft light filtering through bamboo",
    imagePosition: "center 55%",
    imageFilter: "saturate(0.85) brightness(0.94)",
    sceneryLayers: KYOTO_SCENERY,
    overlay: [
      "linear-gradient(180deg, rgba(34, 21, 13, 0.18) 0%, transparent 30%, rgba(239, 231, 210, 0.45) 70%, rgba(239, 231, 210, 0.88) 100%)",
    ].join(", "),
    mistTint: "rgba(232, 168, 90, 0.35)",
    contrastTone: "light",
  },
};

const MARRAKECH_SCENERY = [
  // textile pattern stripe hint
  "repeating-linear-gradient(45deg, rgba(58, 26, 17, 0.06) 0px, rgba(58, 26, 17, 0.06) 2px, transparent 2px, transparent 22px)",
  // dusk sun
  "radial-gradient(ellipse 70% 35% at 78% 22%, rgba(255, 192, 132, 0.65), transparent 70%)",
  // terracotta walls silhouette
  "linear-gradient(180deg, transparent 55%, rgba(155, 74, 46, 0.5) 70%, rgba(94, 47, 42, 0.65) 100%)",
  // body
  "linear-gradient(176deg, #F9DDA8 0%, #E8A867 35%, #B26836 70%, #5E2F2A 100%)",
].join(", ");

const MARRAKECH: LocationData = {
  location: "Marrakech",
  mood: "Terracotta, brass, dusk heat, textile glow",
  primaryColor: "#9B4A2E",
  secondaryColor: "#D49A4A",
  tertiaryColor: "#5E2F2A",
  inkColor: "#3A1A11",
  inkMistColor: "#7A4530",
  surfaceColor: "#F5E5CB",
  mistColor: "rgba(212, 154, 74, 0.34)",
  shadowColor: "rgba(58, 26, 17, 0.22)",
  backgroundStyle: [
    "radial-gradient(ellipse 80% 55% at 80% 12%, rgba(212, 154, 74, 0.38), transparent 65%)",
    "radial-gradient(ellipse 70% 50% at 15% 85%, rgba(155, 74, 46, 0.30), transparent 70%)",
    "radial-gradient(ellipse 55% 45% at 50% 100%, rgba(94, 47, 42, 0.22), transparent 75%)",
    "linear-gradient(176deg, #F8EAD0 0%, #EAC994 100%)",
  ].join(", "),
  typographyTheme: "serif-warm",
  archetype: "residence",
  visualLayer: {
    imageUrl:
      "https://images.unsplash.com/photo-1538970272646-f61fabb3a8a2?auto=format&fit=crop&w=1600&q=80",
    imageAlt: "Warm terracotta walls in late sun",
    imagePosition: "center 50%",
    imageFilter: "saturate(0.94) brightness(0.96)",
    sceneryLayers: MARRAKECH_SCENERY,
    overlay: [
      "linear-gradient(180deg, rgba(58, 26, 17, 0.16) 0%, transparent 36%, rgba(245, 229, 203, 0.55) 72%, rgba(245, 229, 203, 0.9) 100%)",
    ].join(", "),
    mistTint: "rgba(232, 168, 90, 0.42)",
    contrastTone: "light",
  },
};

const LISBON_SCENERY = [
  // azulejo tile grid
  "repeating-linear-gradient(0deg, rgba(47, 111, 136, 0.07) 0px, rgba(47, 111, 136, 0.07) 1px, transparent 1px, transparent 48px)",
  "repeating-linear-gradient(90deg, rgba(47, 111, 136, 0.07) 0px, rgba(47, 111, 136, 0.07) 1px, transparent 1px, transparent 48px)",
  // river light
  "radial-gradient(ellipse 60% 30% at 50% 22%, rgba(255, 226, 168, 0.5), transparent 70%)",
  // terra rooftops near horizon
  "linear-gradient(180deg, transparent 50%, rgba(216, 122, 91, 0.45) 64%, rgba(216, 122, 91, 0.25) 78%, transparent 90%)",
  // tile body
  "linear-gradient(178deg, #E4D9C0 0%, #B4C7CC 38%, #6E9EAE 72%, #2F6F88 100%)",
].join(", ");

const LISBON: LocationData = {
  location: "Lisbon",
  mood: "Tile glaze, terra rooftops, river light",
  primaryColor: "#2F6F88",
  secondaryColor: "#D87A5B",
  tertiaryColor: "#E8D38B",
  inkColor: "#172F3D",
  inkMistColor: "#4F6C7C",
  surfaceColor: "#F7F1E4",
  mistColor: "rgba(232, 211, 139, 0.38)",
  shadowColor: "rgba(23, 47, 61, 0.16)",
  backgroundStyle: [
    "radial-gradient(ellipse 80% 50% at 18% 10%, rgba(47, 111, 136, 0.24), transparent 65%)",
    "radial-gradient(ellipse 75% 50% at 85% 82%, rgba(216, 122, 91, 0.28), transparent 70%)",
    "radial-gradient(ellipse 60% 45% at 50% 50%, rgba(232, 211, 139, 0.20), transparent 75%)",
    "linear-gradient(178deg, #F9F3E8 0%, #ECE2C9 100%)",
  ].join(", "),
  typographyTheme: "serif-editorial",
  archetype: "gallery",
  visualLayer: {
    imageUrl:
      "https://images.unsplash.com/photo-1513735492246-483525079686?auto=format&fit=crop&w=1600&q=80",
    imageAlt: "River light over tile-faced city",
    imagePosition: "center 50%",
    imageFilter: "saturate(0.9) brightness(0.98)",
    sceneryLayers: LISBON_SCENERY,
    overlay: [
      "linear-gradient(180deg, rgba(23, 47, 61, 0.12) 0%, transparent 32%, rgba(247, 241, 228, 0.55) 70%, rgba(247, 241, 228, 0.88) 100%)",
    ].join(", "),
    mistTint: "rgba(232, 211, 139, 0.4)",
    contrastTone: "dark",
  },
};

// ─── Atelier — the default house world (used when no destination) ──────────────
//
// Warm bone paper. Brass accents. Sandstone secondary. This is the foyer of the
// boutique hotel — readable, neutral, but still place-feeling, not SaaS.

// Atelier — the default foyer. Warmer, quieter, still scenic but neutral
// enough to host any destination not in the curated set.
const ATELIER_SCENERY = [
  // brass lamp warmth from corner
  "radial-gradient(ellipse 38% 40% at 86% 24%, rgba(220, 170, 100, 0.55), transparent 70%)",
  // soft brass-hairline horizon
  "linear-gradient(180deg, transparent 55%, rgba(197, 148, 77, 0.18) 62%, transparent 66%)",
  // distant warm light pool
  "radial-gradient(ellipse 60% 40% at 22% 78%, rgba(224, 184, 136, 0.4), transparent 70%)",
  // paper body
  "linear-gradient(178deg, #FBF7EC 0%, #F1E6CB 45%, #E0CCA6 78%, #B89461 100%)",
].join(", ");

const ATELIER: LocationData = {
  location: "Atelier",
  mood: "Warm paper, brass hairlines, quiet sandstone glow",
  primaryColor: "#1F4256",
  secondaryColor: "#C5944D",
  tertiaryColor: "#E0B888",
  inkColor: "#1E1A14",
  inkMistColor: "#7A6E5C",
  surfaceColor: "#FAF7F0",
  mistColor: "rgba(197, 148, 77, 0.28)",
  shadowColor: "rgba(30, 26, 20, 0.14)",
  backgroundStyle: [
    "radial-gradient(ellipse 70% 40% at 50% 0%, rgba(197, 148, 77, 0.16), transparent 70%)",
    "radial-gradient(ellipse 55% 45% at 12% 88%, rgba(224, 184, 136, 0.22), transparent 70%)",
    "radial-gradient(ellipse 50% 40% at 88% 78%, rgba(184, 130, 60, 0.16), transparent 75%)",
    "linear-gradient(180deg, #FBF8F1 0%, #F1EBDA 100%)",
  ].join(", "),
  typographyTheme: "serif-editorial",
  archetype: "atelier",
  visualLayer: {
    // No photographic asset on the house world — keep the foyer neutral.
    sceneryLayers: ATELIER_SCENERY,
    overlay: [
      "linear-gradient(180deg, rgba(30, 26, 20, 0.08) 0%, transparent 32%, rgba(250, 247, 240, 0.58) 70%, rgba(250, 247, 240, 0.92) 100%)",
    ].join(", "),
    mistTint: "rgba(224, 184, 136, 0.4)",
    contrastTone: "dark",
  },
};

// ─── Room archetypes — same hotel, different rooms ─────────────────────────────
//
// These are world-skins that override the *archetype-feel* of a portal regardless
// of the active city. A concierge room always feels intimate; an explore room
// always feels open. They share `inkColor`/`surfaceColor` with the active world
// at call time, but bring their own atmospheric tilt.

// Each room archetype gets its own *interior* — a painted preview of what the
// room feels like behind the door. The portal uses these layers behind the
// label so the four portals read as four different rooms in the same hotel.
const ROOM_SCENERY: Record<NonNullable<LocationData["archetype"]>, string> = {
  // Drafting atelier — paper, brass lamp pool, drafting horizon
  atelier: [
    "radial-gradient(ellipse 55% 38% at 78% 22%, rgba(220, 170, 100, 0.65), transparent 70%)",
    "linear-gradient(180deg, transparent 60%, rgba(197, 148, 77, 0.28) 70%, transparent 78%)",
    "radial-gradient(ellipse 40% 30% at 18% 78%, rgba(224, 184, 136, 0.45), transparent 70%)",
    "linear-gradient(178deg, #F2E6CB 0%, #E0CCA6 50%, #B89461 100%)",
  ].join(", "),
  // Private salon — intimate dim, lantern warmth, deep velvet horizon
  salon: [
    "radial-gradient(ellipse 38% 30% at 70% 30%, rgba(232, 168, 90, 0.55), transparent 70%)",
    "radial-gradient(ellipse 60% 40% at 30% 80%, rgba(40, 24, 18, 0.6), transparent 70%)",
    "linear-gradient(180deg, transparent 50%, rgba(30, 20, 14, 0.35) 75%, rgba(30, 20, 14, 0.6) 100%)",
    "linear-gradient(178deg, #5A3B28 0%, #3D2418 60%, #1E120A 100%)",
  ].join(", "),
  // Observatory — open sky, soft horizon, distant terrain
  observatory: [
    "radial-gradient(ellipse 80% 30% at 50% 18%, rgba(186, 218, 232, 0.55), transparent 70%)",
    "linear-gradient(180deg, transparent 56%, rgba(78, 110, 132, 0.5) 70%, rgba(38, 58, 78, 0.65) 100%)",
    "radial-gradient(ellipse 20% 12% at 28% 64%, rgba(38, 58, 78, 0.4), transparent 70%)",
    "radial-gradient(ellipse 24% 14% at 70% 66%, rgba(38, 58, 78, 0.5), transparent 70%)",
    "linear-gradient(178deg, #CCE0EE 0%, #7BA3C2 55%, #2F587A 100%)",
  ].join(", "),
  // Gallery — soft museum light, parquet floor implied, neutral palette
  gallery: [
    "radial-gradient(ellipse 70% 35% at 50% 20%, rgba(250, 244, 232, 0.7), transparent 70%)",
    "linear-gradient(180deg, transparent 65%, rgba(170, 138, 96, 0.4) 78%, rgba(120, 92, 60, 0.55) 100%)",
    "linear-gradient(178deg, #EFE5D2 0%, #C9B58E 70%, #8E6E48 100%)",
  ].join(", "),
  // Scrapbook library — warm shelves, bookbinder reds and brass
  scrapbook: [
    "radial-gradient(ellipse 60% 38% at 50% 22%, rgba(232, 178, 107, 0.45), transparent 70%)",
    // shelf line
    "linear-gradient(180deg, transparent 64%, rgba(80, 38, 30, 0.55) 70%, transparent 74%)",
    // book stacks
    "radial-gradient(ellipse 8% 22% at 18% 82%, rgba(120, 50, 42, 0.6), transparent 65%)",
    "radial-gradient(ellipse 8% 22% at 36% 80%, rgba(140, 90, 60, 0.55), transparent 65%)",
    "radial-gradient(ellipse 8% 22% at 64% 82%, rgba(80, 38, 30, 0.6), transparent 65%)",
    "radial-gradient(ellipse 8% 22% at 82% 80%, rgba(120, 50, 42, 0.55), transparent 65%)",
    "linear-gradient(178deg, #E6CFA8 0%, #B27A48 60%, #5C2C20 100%)",
  ].join(", "),
  // Residence — textile glow, dusk warmth
  residence: [
    "repeating-linear-gradient(45deg, rgba(58, 26, 17, 0.08) 0px, rgba(58, 26, 17, 0.08) 2px, transparent 2px, transparent 14px)",
    "radial-gradient(ellipse 70% 35% at 50% 24%, rgba(255, 192, 132, 0.55), transparent 70%)",
    "linear-gradient(178deg, #F8D5A8 0%, #C97A48 55%, #5E2F2A 100%)",
  ].join(", "),
};

const ROOM_TINTS: Record<NonNullable<LocationData["archetype"]>, {
  primaryShift: string;
  secondaryShift: string;
  mistShift: string;
  archetype: NonNullable<LocationData["archetype"]>;
  archetypeLine: string;
}> = {
  atelier: {
    primaryShift: "rgba(197, 148, 77, 0.35)",
    secondaryShift: "rgba(184, 130, 60, 0.22)",
    mistShift: "rgba(197, 148, 77, 0.20)",
    archetype: "atelier",
    archetypeLine: "the atelier",
  },
  salon: {
    primaryShift: "rgba(61, 47, 38, 0.40)",
    secondaryShift: "rgba(197, 148, 77, 0.30)",
    mistShift: "rgba(142, 106, 69, 0.22)",
    archetype: "salon",
    archetypeLine: "the private salon",
  },
  observatory: {
    primaryShift: "rgba(31, 66, 86, 0.34)",
    secondaryShift: "rgba(123, 168, 194, 0.26)",
    mistShift: "rgba(138, 160, 146, 0.22)",
    archetype: "observatory",
    archetypeLine: "the observatory",
  },
  gallery: {
    primaryShift: "rgba(31, 66, 86, 0.30)",
    secondaryShift: "rgba(224, 184, 136, 0.30)",
    mistShift: "rgba(218, 198, 172, 0.26)",
    archetype: "gallery",
    archetypeLine: "the gallery",
  },
  scrapbook: {
    primaryShift: "rgba(216, 132, 120, 0.32)",
    secondaryShift: "rgba(232, 178, 107, 0.28)",
    mistShift: "rgba(218, 198, 172, 0.22)",
    archetype: "scrapbook",
    archetypeLine: "the scrapbook library",
  },
  residence: {
    primaryShift: "rgba(155, 74, 46, 0.34)",
    secondaryShift: "rgba(212, 154, 74, 0.32)",
    mistShift: "rgba(212, 154, 74, 0.22)",
    archetype: "residence",
    archetypeLine: "the residence",
  },
};

/**
 * Painted room interior preview for a given archetype. Used by `WorldPortal`
 * to give each portal a distinct atmosphere behind the label so the four
 * portals feel like four different rooms in the same hotel.
 */
export function roomSceneryFor(
  archetype: NonNullable<LocationData["archetype"]>,
): string {
  return ROOM_SCENERY[archetype] ?? ROOM_SCENERY.atelier;
}

/** Stable lookup library — add new destinations here. */
export const WORLD_LIBRARY: Readonly<Record<string, LocationData>> = Object.freeze({
  portland: PORTLAND,
  santorini: SANTORINI,
  kyoto: KYOTO,
  marrakech: MARRAKECH,
  lisbon: LISBON,
  atelier: ATELIER,
});

export const ATELIER_WORLD: LocationData = ATELIER;

// ─── Destination → world resolution ────────────────────────────────────────────

/** Lowercase, strip non-letters, split on comma/space, take the first token. */
function normalizeDestination(raw: string | null | undefined): string {
  if (!raw) return "";
  return raw
    .toLowerCase()
    .split(/[,/·•|]/)[0]
    .trim()
    .replace(/[^a-z\s-]/g, "")
    .replace(/\s+/g, " ");
}

// ─── Archetype fallback worlds ─────────────────────────────────────────────────
//
// When a destination is not in the curated `WORLD_LIBRARY`, the resolver maps
// the destination keyword to a generic travel archetype world so the dossier
// cover + shelf spine still paint a recognizable archetype mood rather than a
// pale gradient. This keeps the World-DNA system working for arbitrary
// destinations without scattering image URLs through components.
//
// Imagery strategy:
//   · Where a photographic Unsplash mood URL is *verified* to depict the
//     archetype (coast = the tropical beach used by Miami; forest = the misty
//     forest used by Portland), we reuse that exact verified URL.
//   · For archetypes whose photographic content could not be verified in this
//     environment (city / mountain / desert), we ship a self-contained
//     SVG-data-URI scene so the content is GUARANTEED correct (a city skyline
//     is always a city skyline) with zero network dependency. SVG scales
//     cleanly to any cover size.

/** Wrap a raw SVG string into a CSS-ready data-URI image URL value
 *  (the raw `data:` URL — worldStyleVars adds the `url("…")` wrapper). */
function svgScene(svg: string): string {
  return `data:image/svg+xml,${encodeURIComponent(svg.replace(/\s+/g, " ").trim())}`;
}

// Verified photographic mood URLs (confirmed correct in preview screenshots).
const VERIFIED_COAST_PHOTO =
  "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1600&q=80";
const VERIFIED_FOREST_PHOTO =
  "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=1600&q=80";

// City skyline — dusk sky + layered building silhouettes + warm window
// lights. Guaranteed to read as a city.
const CITY_SCENE = svgScene(`
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1600 900' preserveAspectRatio='xMidYMid slice'>
  <defs>
    <linearGradient id='sky' x1='0' y1='0' x2='0' y2='1'>
      <stop offset='0' stop-color='#1b2742'/>
      <stop offset='0.5' stop-color='#3a4a6e'/>
      <stop offset='0.82' stop-color='#c98a4e'/>
      <stop offset='1' stop-color='#e6ad5e'/>
    </linearGradient>
  </defs>
  <rect width='1600' height='900' fill='url(#sky)'/>
  <circle cx='1180' cy='250' r='90' fill='#ffe6b0' opacity='0.55'/>
  <g fill='#16243f' opacity='0.92'>
    <rect x='0' y='470' width='150' height='430'/>
    <rect x='150' y='560' width='110' height='340'/>
    <rect x='260' y='400' width='130' height='500'/>
    <rect x='390' y='520' width='95' height='380'/>
    <rect x='485' y='340' width='150' height='560'/>
    <rect x='635' y='480' width='120' height='420'/>
    <rect x='755' y='300' width='140' height='600'/>
    <rect x='895' y='520' width='110' height='380'/>
    <rect x='1005' y='420' width='135' height='480'/>
    <rect x='1140' y='540' width='100' height='360'/>
    <rect x='1240' y='360' width='150' height='540'/>
    <rect x='1390' y='500' width='120' height='400'/>
    <rect x='1510' y='580' width='90' height='320'/>
  </g>
  <g fill='#0b1426' opacity='0.95'>
    <rect x='0' y='640' width='200' height='260'/>
    <rect x='320' y='670' width='240' height='230'/>
    <rect x='720' y='650' width='260' height='250'/>
    <rect x='1120' y='680' width='280' height='220'/>
  </g>
  <g fill='#ffd28a' opacity='0.85'>
    <rect x='40' y='510' width='14' height='18'/><rect x='80' y='540' width='14' height='18'/><rect x='40' y='580' width='14' height='18'/>
    <rect x='300' y='440' width='14' height='18'/><rect x='340' y='480' width='14' height='18'/><rect x='300' y='520' width='14' height='18'/>
    <rect x='520' y='380' width='14' height='18'/><rect x='560' y='420' width='14' height='18'/><rect x='520' y='460' width='14' height='18'/><rect x='560' y='500' width='14' height='18'/>
    <rect x='790' y='340' width='14' height='18'/><rect x='830' y='380' width='14' height='18'/><rect x='790' y='420' width='14' height='18'/><rect x='830' y='460' width='14' height='18'/>
    <rect x='1040' y='460' width='14' height='18'/><rect x='1080' y='500' width='14' height='18'/>
    <rect x='1280' y='400' width='14' height='18'/><rect x='1320' y='440' width='14' height='18'/><rect x='1280' y='480' width='14' height='18'/>
  </g>
</svg>`);

// Mountain range — layered peaks + snow line + alpine haze.
const MOUNTAIN_SCENE = svgScene(`
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1600 900' preserveAspectRatio='xMidYMid slice'>
  <defs>
    <linearGradient id='msky' x1='0' y1='0' x2='0' y2='1'>
      <stop offset='0' stop-color='#cdd8da'/>
      <stop offset='0.5' stop-color='#9fb0b4'/>
      <stop offset='1' stop-color='#6f8084'/>
    </linearGradient>
  </defs>
  <rect width='1600' height='900' fill='url(#msky)'/>
  <circle cx='400' cy='220' r='80' fill='#fdf6e6' opacity='0.5'/>
  <polygon points='0,640 280,360 520,640' fill='#7d8e93' opacity='0.85'/>
  <polygon points='360,660 720,300 1040,660' fill='#5c6d72' opacity='0.9'/>
  <polygon points='900,660 1240,340 1600,660' fill='#6b7c80' opacity='0.88'/>
  <polygon points='620,700 980,420 1320,700' fill='#3f4d52'/>
  <polygon points='720,300 760,360 700,360' fill='#f3f6f5'/>
  <polygon points='980,420 1030,500 930,500' fill='#eef2f1'/>
  <polygon points='280,360 320,430 240,430' fill='#eef2f1'/>
  <rect x='0' y='655' width='1600' height='245' fill='#2a3539'/>
  <rect x='0' y='600' width='1600' height='90' fill='#384449' opacity='0.6'/>
</svg>`);

// Desert dunes — dusk sun + layered dune ridges + mineral haze.
const DESERT_SCENE = svgScene(`
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1600 900' preserveAspectRatio='xMidYMid slice'>
  <defs>
    <linearGradient id='dsky' x1='0' y1='0' x2='0' y2='1'>
      <stop offset='0' stop-color='#f4d8a0'/>
      <stop offset='0.5' stop-color='#e9b873'/>
      <stop offset='1' stop-color='#d99a55'/>
    </linearGradient>
  </defs>
  <rect width='1600' height='900' fill='url(#dsky)'/>
  <circle cx='1080' cy='280' r='120' fill='#fff0d0' opacity='0.7'/>
  <path d='M0,560 C400,500 700,600 1000,540 C1300,490 1500,560 1600,540 L1600,900 L0,900 Z' fill='#c97f44' opacity='0.9'/>
  <path d='M0,660 C350,600 650,700 980,640 C1280,590 1500,660 1600,650 L1600,900 L0,900 Z' fill='#a85b2f'/>
  <path d='M0,760 C300,720 700,800 1050,750 C1350,710 1500,760 1600,755 L1600,900 L0,900 Z' fill='#7c3f25'/>
</svg>`);

const CITY_WORLD: LocationData = {
  location: "Urban",
  mood: "City rooftops, night windows, neon avenue",
  primaryColor: "#1F2A3E",
  secondaryColor: "#D8A055",
  tertiaryColor: "#6E7E9A",
  inkColor: "#0E1422",
  inkMistColor: "#4A5366",
  surfaceColor: "#F2EFE6",
  mistColor: "rgba(110, 126, 154, 0.34)",
  shadowColor: "rgba(14, 20, 34, 0.22)",
  backgroundStyle: [
    "radial-gradient(ellipse 80% 50% at 50% 0%, rgba(216, 160, 85, 0.22), transparent 70%)",
    "radial-gradient(ellipse 70% 50% at 12% 88%, rgba(31, 42, 62, 0.28), transparent 70%)",
    "linear-gradient(180deg, #F4F1E8 0%, #E9E5D6 100%)",
  ].join(", "),
  typographyTheme: "serif-editorial",
  archetype: "gallery",
  visualLayer: {
    imageUrl: CITY_SCENE,
    imageAlt: "City skyline at dusk with warm window light",
    imagePosition: "center 60%",
    imageFilter: "saturate(1) brightness(0.96) contrast(1.02)",
    sceneryLayers: [
      "radial-gradient(ellipse 70% 30% at 50% 18%, rgba(255, 222, 168, 0.4), transparent 70%)",
      "linear-gradient(180deg, transparent 50%, rgba(216, 160, 85, 0.35) 70%, rgba(31, 42, 62, 0.55) 100%)",
      "linear-gradient(180deg, #2A3858 0%, #131C30 100%)",
    ].join(", "),
    overlay: [
      "linear-gradient(180deg, rgba(14, 20, 34, 0.34) 0%, transparent 32%, rgba(242, 239, 230, 0.45) 78%, rgba(242, 239, 230, 0.85) 100%)",
    ].join(", "),
    mistTint: "rgba(216, 160, 85, 0.35)",
    contrastTone: "light",
  },
};

const COAST_WORLD: LocationData = {
  location: "Coastal",
  mood: "Salt, glare, linen, slow heat",
  primaryColor: "#1F4A66",
  secondaryColor: "#E0B888",
  tertiaryColor: "#86B2C8",
  inkColor: "#102434",
  inkMistColor: "#476275",
  surfaceColor: "#F8F5EC",
  mistColor: "rgba(134, 178, 200, 0.4)",
  shadowColor: "rgba(16, 36, 52, 0.18)",
  backgroundStyle: [
    "radial-gradient(ellipse 90% 50% at 50% 0%, rgba(224, 184, 136, 0.24), transparent 70%)",
    "radial-gradient(ellipse 70% 50% at 18% 88%, rgba(134, 178, 200, 0.30), transparent 70%)",
    "linear-gradient(180deg, #F9F5EA 0%, #ECE3D0 100%)",
  ].join(", "),
  typographyTheme: "serif-spare",
  archetype: "gallery",
  visualLayer: {
    imageUrl: VERIFIED_COAST_PHOTO,
    imageAlt: "Quiet coastline with horizon glow",
    imagePosition: "center 50%",
    imageFilter: "saturate(0.9) brightness(0.96)",
    sceneryLayers: [
      "linear-gradient(180deg, transparent 50%, rgba(248, 245, 236, 0.5) 64%, transparent 78%)",
      "radial-gradient(ellipse 70% 28% at 50% 64%, rgba(134, 178, 200, 0.35), transparent 70%)",
      "linear-gradient(180deg, #DDE7EA 0%, #8FB3C4 38%, #466F8A 72%, #1F4A66 100%)",
    ].join(", "),
    overlay: [
      "linear-gradient(180deg, rgba(16, 36, 52, 0.14) 0%, transparent 30%, rgba(248, 245, 236, 0.5) 72%, rgba(248, 245, 236, 0.88) 100%)",
    ].join(", "),
    mistTint: "rgba(212, 224, 232, 0.5)",
    contrastTone: "dark",
  },
};

const MOUNTAIN_WORLD: LocationData = {
  location: "Mountain",
  mood: "Pine, stone, mist, altitude",
  primaryColor: "#2D3A40",
  secondaryColor: "#9B7A4E",
  tertiaryColor: "#6B7E80",
  inkColor: "#11161A",
  inkMistColor: "#4A5560",
  surfaceColor: "#F1EEE5",
  mistColor: "rgba(107, 126, 128, 0.45)",
  shadowColor: "rgba(17, 22, 26, 0.22)",
  backgroundStyle: [
    "radial-gradient(ellipse 80% 50% at 50% 0%, rgba(155, 122, 78, 0.20), transparent 70%)",
    "radial-gradient(ellipse 70% 50% at 88% 88%, rgba(45, 58, 64, 0.22), transparent 70%)",
    "linear-gradient(178deg, #F2EFE6 0%, #E6E1D4 100%)",
  ].join(", "),
  typographyTheme: "serif-editorial",
  archetype: "observatory",
  visualLayer: {
    imageUrl: MOUNTAIN_SCENE,
    imageAlt: "Mountain ridge wrapped in alpine mist",
    imagePosition: "center 50%",
    imageFilter: "saturate(0.92) brightness(0.98) contrast(1.02)",
    sceneryLayers: [
      "linear-gradient(180deg, transparent 45%, rgba(232, 236, 229, 0.55) 60%, rgba(232, 236, 229, 0.3) 76%, transparent 88%)",
      "radial-gradient(ellipse 75% 28% at 50% 16%, rgba(212, 224, 232, 0.55), transparent 70%)",
      "linear-gradient(178deg, #C5D0D2 0%, #7E8E94 38%, #404C55 72%, #1F262C 100%)",
    ].join(", "),
    overlay: [
      "linear-gradient(180deg, rgba(17, 22, 26, 0.18) 0%, transparent 32%, rgba(241, 238, 229, 0.5) 72%, rgba(241, 238, 229, 0.9) 100%)",
    ].join(", "),
    mistTint: "rgba(186, 198, 200, 0.55)",
    contrastTone: "light",
  },
};

const DESERT_WORLD: LocationData = {
  location: "Desert",
  mood: "Heat, mineral dust, brass, dusk",
  primaryColor: "#A85B2F",
  secondaryColor: "#E2B370",
  tertiaryColor: "#6E3725",
  inkColor: "#3B1A11",
  inkMistColor: "#7C4A30",
  surfaceColor: "#F6E7CB",
  mistColor: "rgba(212, 154, 74, 0.38)",
  shadowColor: "rgba(59, 26, 17, 0.22)",
  backgroundStyle: [
    "radial-gradient(ellipse 80% 55% at 80% 10%, rgba(226, 179, 112, 0.36), transparent 65%)",
    "radial-gradient(ellipse 70% 50% at 18% 88%, rgba(168, 91, 47, 0.30), transparent 70%)",
    "linear-gradient(176deg, #F8E9CE 0%, #EBC994 100%)",
  ].join(", "),
  typographyTheme: "serif-warm",
  archetype: "residence",
  visualLayer: {
    imageUrl: DESERT_SCENE,
    imageAlt: "Late-day light over desert dunes",
    imagePosition: "center 55%",
    imageFilter: "saturate(0.98) brightness(1) contrast(1.02)",
    sceneryLayers: [
      "radial-gradient(ellipse 70% 35% at 75% 22%, rgba(255, 200, 138, 0.6), transparent 70%)",
      "linear-gradient(180deg, transparent 55%, rgba(168, 91, 47, 0.4) 75%, rgba(110, 55, 37, 0.55) 100%)",
      "linear-gradient(176deg, #F4D29E 0%, #DD9B58 40%, #A85B2F 75%, #5E2A1A 100%)",
    ].join(", "),
    overlay: [
      "linear-gradient(180deg, rgba(59, 26, 17, 0.18) 0%, transparent 36%, rgba(246, 231, 203, 0.55) 72%, rgba(246, 231, 203, 0.9) 100%)",
    ].join(", "),
    mistTint: "rgba(232, 168, 90, 0.42)",
    contrastTone: "light",
  },
};

const FOREST_WORLD: LocationData = {
  location: "Forest",
  mood: "Cedar, mist, deep green stillness",
  primaryColor: "#2F4A38",
  secondaryColor: "#B68A5A",
  tertiaryColor: "#7B907F",
  inkColor: "#15201A",
  inkMistColor: "#4A5C50",
  surfaceColor: "#F1EEE3",
  mistColor: "rgba(138, 160, 146, 0.45)",
  shadowColor: "rgba(21, 32, 26, 0.22)",
  backgroundStyle: [
    "radial-gradient(ellipse 80% 50% at 18% 12%, rgba(123, 144, 127, 0.32), transparent 65%)",
    "radial-gradient(ellipse 70% 40% at 88% 78%, rgba(182, 138, 90, 0.20), transparent 70%)",
    "linear-gradient(178deg, #F2EFE5 0%, #E6E1D0 100%)",
  ].join(", "),
  typographyTheme: "serif-editorial",
  archetype: "observatory",
  visualLayer: {
    imageUrl: VERIFIED_FOREST_PHOTO,
    imageAlt: "Tall forest with morning light filtering through",
    imagePosition: "center 50%",
    imageFilter: "saturate(0.84) brightness(0.92)",
    sceneryLayers: [
      "linear-gradient(180deg, transparent 42%, rgba(232, 236, 229, 0.5) 56%, rgba(232, 236, 229, 0.3) 72%, transparent 88%)",
      "radial-gradient(ellipse 90% 50% at 50% 18%, rgba(186, 198, 188, 0.48), transparent 70%)",
      "linear-gradient(178deg, #BFC9BA 0%, #8FA292 40%, #4B5C4F 78%, #1F2A22 100%)",
    ].join(", "),
    overlay: [
      "linear-gradient(180deg, rgba(21, 32, 26, 0.16) 0%, transparent 36%, rgba(241, 238, 227, 0.55) 72%, rgba(241, 238, 227, 0.88) 100%)",
    ].join(", "),
    mistTint: "rgba(186, 198, 188, 0.55)",
    contrastTone: "light",
  },
};

/** Reusable archetype world catalogue — keyword → curated archetype world. */
const ARCHETYPE_WORLDS: Readonly<Record<string, LocationData>> = Object.freeze({
  city: CITY_WORLD,
  coast: COAST_WORLD,
  mountain: MOUNTAIN_WORLD,
  desert: DESERT_WORLD,
  forest: FOREST_WORLD,
});

/** Keyword → archetype map. A short curated list of city + coast + mountain
 *  + desert + forest hints so a destination like "Chicago" resolves to the
 *  CITY archetype and gets a real urban skyline mood image (not a gradient).
 *  Keep this list compact and ordered; longer phrases win first. */
const ARCHETYPE_KEYWORDS: ReadonlyArray<readonly [string, keyof typeof ARCHETYPE_WORLDS]> = [
  // City / urban / metropolitan
  ["new york", "city"],
  ["york", "city"],
  ["chicago", "city"],
  ["tokyo", "city"],
  ["london", "city"],
  ["paris", "city"],
  ["rome", "city"],
  ["berlin", "city"],
  ["barcelona", "city"],
  ["madrid", "city"],
  ["seoul", "city"],
  ["singapore", "city"],
  ["dubai", "city"],
  ["hong kong", "city"],
  ["bangkok", "city"],
  ["mumbai", "city"],
  ["delhi", "city"],
  ["istanbul", "city"],
  ["los angeles", "city"],
  ["san francisco", "city"],
  ["boston", "city"],
  ["seattle", "city"],
  ["amsterdam", "city"],
  ["vienna", "city"],
  ["prague", "city"],
  ["sydney", "city"],
  ["melbourne", "city"],
  ["mexico city", "city"],
  ["city", "city"],
  // Coast / island / beach
  ["beach", "coast"],
  ["coast", "coast"],
  ["seaside", "coast"],
  ["island", "coast"],
  ["maui", "coast"],
  ["hawaii", "coast"],
  ["bali", "coast"],
  ["amalfi", "coast"],
  ["mykonos", "coast"],
  ["positano", "coast"],
  ["malibu", "coast"],
  ["nice", "coast"],
  ["miami", "coast"],
  ["cancun", "coast"],
  ["phuket", "coast"],
  ["tulum", "coast"],
  ["maldives", "coast"],
  // Mountain
  ["mountain", "mountain"],
  ["alps", "mountain"],
  ["aspen", "mountain"],
  ["zermatt", "mountain"],
  ["chamonix", "mountain"],
  ["whistler", "mountain"],
  ["banff", "mountain"],
  ["andes", "mountain"],
  ["denver", "mountain"],
  ["telluride", "mountain"],
  ["jackson", "mountain"],
  // Desert
  ["desert", "desert"],
  ["sahara", "desert"],
  ["sedona", "desert"],
  ["scottsdale", "desert"],
  ["palm springs", "desert"],
  ["santa fe", "desert"],
  ["tucson", "desert"],
  // Forest / woodland (catches "forest of dean", etc.)
  ["forest", "forest"],
  ["redwood", "forest"],
];

function pickArchetypeWorld(normalized: string): LocationData | null {
  for (const [keyword, archetype] of ARCHETYPE_KEYWORDS) {
    if (normalized.includes(keyword)) {
      return ARCHETYPE_WORLDS[archetype];
    }
  }
  return null;
}

export const WORLD_ARCHETYPE_LIBRARY: typeof ARCHETYPE_WORLDS = ARCHETYPE_WORLDS;

/**
 * Resolve a `LocationData` from a free-text destination string. Falls back
 * through (1) curated WORLD_LIBRARY, (2) substring match in WORLD_LIBRARY,
 * (3) keyword → archetype world (city / coast / mountain / desert / forest),
 * and finally (4) the Atelier (house) world. The result always carries a
 * photographic mood image so the dossier cover never paints a pale gradient
 * for unknown destinations like Chicago.
 */
export function pickWorldFromDestination(
  destination: string | null | undefined,
): LocationData {
  const normalized = normalizeDestination(destination);
  if (!normalized) return ATELIER_WORLD;
  // Match by direct lookup first, then by "starts with" / "contains" for
  // multi-word place names like "Portland, OR" or "Kyoto Prefecture".
  if (WORLD_LIBRARY[normalized]) return WORLD_LIBRARY[normalized];
  for (const key of Object.keys(WORLD_LIBRARY)) {
    if (key === "atelier") continue;
    if (normalized.startsWith(key) || normalized.includes(key)) {
      return WORLD_LIBRARY[key];
    }
  }
  // Archetype fallback — Chicago → city, Tahiti → coast, Aspen → mountain, etc.
  const archetypeWorld = pickArchetypeWorld(normalized);
  if (archetypeWorld) return archetypeWorld;
  return ATELIER_WORLD;
}

/**
 * Apply a `room` archetype on top of a base world. The result keeps the
 * destination's ink/surface but shifts the atmosphere toward the room's
 * archetype (concierge → salon, explore → observatory, etc).
 */
export function applyRoom(
  world: LocationData,
  room: NonNullable<LocationData["archetype"]>,
): LocationData {
  const tint = ROOM_TINTS[room];
  if (!tint) return world;
  return {
    ...world,
    archetype: tint.archetype,
    primaryColor: world.primaryColor,
    secondaryColor: world.secondaryColor,
    mistColor: tint.mistShift,
    backgroundStyle: [
      `radial-gradient(ellipse 75% 45% at 18% 14%, ${tint.primaryShift}, transparent 65%)`,
      `radial-gradient(ellipse 70% 50% at 86% 82%, ${tint.secondaryShift}, transparent 70%)`,
      `radial-gradient(ellipse 55% 45% at 50% 100%, ${tint.mistShift}, transparent 75%)`,
      world.backgroundStyle,
    ].join(", "),
    // For portals the scenery shows the room interior, not the destination
    // exterior — that's what gives Concierge/Explore/Planning/Saved their
    // boutique-room feel.
    visualLayer: {
      ...world.visualLayer,
      imageUrl: undefined,
      sceneryLayers: ROOM_SCENERY[room] ?? world.visualLayer.sceneryLayers,
      overlay: [
        `linear-gradient(180deg, transparent 0%, ${tint.mistShift} 65%, color-mix(in srgb, ${world.surfaceColor} 92%, transparent) 100%)`,
      ].join(", "),
      mistTint: tint.mistShift,
    },
  };
}

// ─── CSS variable binding — locationData → inline style ────────────────────────

/**
 * Build the inline `style` object that injects `--world-*` CSS variables on a
 * container. Every world-aware surface reads from these variables; no component
 * hardcodes Portland-specific values.
 */
export function worldStyleVars(world: LocationData): CSSProperties {
  const typeDisplay =
    world.typographyTheme === "serif-warm"
      ? "var(--font-fraunces), 'Cormorant Garamond', Georgia, serif"
      : world.typographyTheme === "serif-spare"
      ? "var(--font-fraunces), 'Times New Roman', Georgia, serif"
      : world.typographyTheme === "serif-lantern"
      ? "var(--font-fraunces), 'Cormorant Garamond', 'Times New Roman', serif"
      : "var(--font-fraunces), Georgia, 'Times New Roman', serif";
  const visual = world.visualLayer;
  // Luminance-aware contrast — scenic overlay text always uses
  // --world-on-scenery / --world-on-scenery-muted / --world-scenery-scrim
  // so the dossier title, scrim metadata, and portal label can never go
  // dark-on-dark or light-on-light on any curated world.
  const tone = visual.contrastTone ?? "dark";
  const onScenery =
    tone === "light"
      ? "rgba(255, 248, 235, 0.96)"
      : "rgba(24, 22, 18, 0.94)";
  const onSceneryMuted =
    tone === "light"
      ? "rgba(255, 248, 235, 0.78)"
      : "rgba(24, 22, 18, 0.74)";
  const sceneryScrim =
    tone === "light"
      ? "rgba(12, 14, 12, 0.55)"
      : "rgba(252, 248, 238, 0.62)";
  return {
    // Primary world tokens — every component reads these.
    ["--world-primary" as string]: world.primaryColor,
    ["--world-secondary" as string]: world.secondaryColor,
    ["--world-tertiary" as string]: world.tertiaryColor,
    ["--world-ink" as string]: world.inkColor,
    ["--world-ink-mist" as string]: world.inkMistColor,
    ["--world-surface" as string]: world.surfaceColor,
    ["--world-mist" as string]: world.mistColor,
    ["--world-shadow" as string]: world.shadowColor,
    ["--world-bg" as string]: world.backgroundStyle,
    ["--world-accent" as string]: world.secondaryColor,
    ["--world-type-display" as string]: typeDisplay,
    ["--world-type-ui" as string]:
      "var(--font-fraunces), Georgia, 'Times New Roman', serif",
    // Visual-layer tokens — scenery image + painted layers + overlay tints.
    ["--world-scenery" as string]: visual.sceneryLayers,
    ["--world-scenery-overlay" as string]: visual.overlay,
    ["--world-scenery-image" as string]: visual.imageUrl
      ? `url("${visual.imageUrl}")`
      : "none",
    ["--world-scenery-position" as string]: visual.imagePosition ?? "center 50%",
    ["--world-scenery-filter" as string]:
      visual.imageFilter ?? "saturate(0.9) brightness(0.98)",
    ["--world-mist-tint" as string]: visual.mistTint,
    // Luminance-aware text + scrim — auto-contrast for any scenic overlay.
    ["--world-on-scenery" as string]: onScenery,
    ["--world-on-scenery-muted" as string]: onSceneryMuted,
    ["--world-scenery-scrim" as string]: sceneryScrim,
    ["--world-contrast-tone" as string]: tone,
  };
}

/** Quiet wayfinder line — "Portland · Misty forest, quiet streets, cedar warmth" */
export function worldWayfinderLine(world: LocationData): string {
  return `${world.location} · ${world.mood}`;
}

// ─── Curated room catalogue — used by the portal/room switcher ─────────────────

export interface RoomDefinition {
  /** Internal id; stable. */
  id: "concierge" | "explore" | "planning" | "saved";
  /** Quiet label shown beside the room. */
  label: string;
  /** Quiet sublabel — emotional, not feature-list. */
  whisper: string;
  /** Where the doorway opens. */
  href: string;
  /** Archetype applied on top of the active world. */
  archetype: NonNullable<LocationData["archetype"]>;
}

export const ROOM_CATALOGUE: ReadonlyArray<RoomDefinition> = [
  {
    id: "concierge",
    label: "Concierge",
    whisper: "Private dining, stays, and local intelligence.",
    href: "/concierge",
    archetype: "salon",
  },
  {
    id: "explore",
    label: "Explore",
    whisper: "Landscapes, neighborhoods, and hidden doors.",
    href: "/explore",
    archetype: "observatory",
  },
  {
    id: "planning",
    label: "Planning",
    whisper: "Shape the journey.",
    href: "/trips/new",
    archetype: "atelier",
  },
  {
    id: "saved",
    label: "Saved",
    whisper: "Your private archive.",
    href: "/saved",
    archetype: "scrapbook",
  },
];
