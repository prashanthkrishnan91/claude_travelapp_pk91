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
}

// ─── Curated worlds — sensory DNA per destination ──────────────────────────────
//
// These were composed as palettes, not photo-grabs. Every color has been
// checked for legibility against `surfaceColor`. Add new worlds as needed.

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
};

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
};

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
};

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
};

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
};

// ─── Atelier — the default house world (used when no destination) ──────────────
//
// Warm bone paper. Brass accents. Sandstone secondary. This is the foyer of the
// boutique hotel — readable, neutral, but still place-feeling, not SaaS.

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
};

// ─── Room archetypes — same hotel, different rooms ─────────────────────────────
//
// These are world-skins that override the *archetype-feel* of a portal regardless
// of the active city. A concierge room always feels intimate; an explore room
// always feels open. They share `inkColor`/`surfaceColor` with the active world
// at call time, but bring their own atmospheric tilt.

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

/**
 * Resolve a `LocationData` from a free-text destination string. Falls back to
 * the Atelier (house) world when no destination is provided or when the
 * destination is not in the curated library — the foyer is always somewhere.
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
    whisper: "the private salon",
    href: "/concierge",
    archetype: "salon",
  },
  {
    id: "explore",
    label: "Explore",
    whisper: "the observatory",
    href: "/explore",
    archetype: "observatory",
  },
  {
    id: "planning",
    label: "Planning",
    whisper: "the drafting atelier",
    href: "/trips/new",
    archetype: "atelier",
  },
  {
    id: "saved",
    label: "Saved",
    whisper: "the scrapbook library",
    href: "/saved",
    archetype: "scrapbook",
  },
];
