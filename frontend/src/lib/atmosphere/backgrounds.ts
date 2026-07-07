/**
 * Atmospheric Background System v1 — central registry / manifest.
 *
 * This is the SINGLE source of truth for every cinematic background used
 * across the app. Surfaces never pick their own image or gradient ad-hoc;
 * they request a role from this registry and the <AtelierBackdrop> component
 * renders it with a consistent overlay/scrim/grain treatment.
 *
 * Art direction (premium editorial travel, not tourist-brochure):
 *   · boutique hotel lobby at golden hour, quiet Mediterranean courtyard,
 *     soft train/airplane-window light, warm city street after rain,
 *     archival map / passport texture, calm blurred coastal/desert light.
 *   · evolves the existing Paper Folio identity (cream / paper / ink) with
 *     warm gold, muted terracotta, olive, deep marine, dusk blue, soft rose,
 *     muted sand. No neon, no tropical/postcard saturation, no cartoons.
 *
 * ASSET POLICY (see public/atmosphere/MANIFEST.md):
 *   The repo currently ships NO curated photographic assets. Every role below
 *   therefore has `image: null` and renders a premium gradient/photo-wash
 *   PLACEHOLDER. When a licensed, local, documented image is dropped into
 *   /public/atmosphere/<file>, set the role's `image` field to that path to
 *   activate real editorial photography — no other code changes required.
 *   Never point `image` at a remote/hotlinked URL.
 */

export type BackdropTone = "cinema" | "paper";

export type BackdropRole =
  /** Strongest full-bleed cinematic image — login / auth. The emotional hook. */
  | "auth-hero"
  /** Warm immersive atelier mood — Concierge / Explore / Saved. */
  | "atelier-wash"
  /** Calmer editorial wash — Home / My Trips. */
  | "library-wash"
  /** Very subtle paper/map texture behind the planning desk — Journey Desk. */
  | "desk-texture"
  /** Lightest read-only itinerary atmosphere — Brief. */
  | "brief-texture";

export interface BackdropAsset {
  role: BackdropRole;
  /**
   * Local /public path to a curated editorial image, or null to render the
   * documented gradient placeholder. NEVER a remote/hotlinked URL.
   */
  image: string | null;
  /** Intended mobile crop (object-position) when an image is supplied. */
  mobileImage?: string | null;
  /** object-position used so the meaningful part of the photo survives crops. */
  focalPoint: string;
  /** Whether the base reads dark (cinema) or light (paper). Drives scrim color. */
  tone: BackdropTone;
  /**
   * Premium CSS gradient used when `image` is null, and as the always-present
   * color bed beneath any image (prevents flashes / layout shift, sets mood).
   */
  placeholder: string;
  /** Overlay scrim painted above the image/placeholder to protect contrast. */
  scrim: string;
  /** Soft gaussian blur applied to the image only (atmosphere, not detail). */
  blurPx: number;
  /** Whether to lay a faint film grain over the backdrop. */
  grain: boolean;
  /** Human description — also used by the manifest doc + reviewers. */
  brief: string;
}

/**
 * Approved palette anchors (kept in sync with globals.css --ds tokens):
 *   cream/paper  #FAF7F0 / #F1ECE0 / #E6DECB
 *   warm gold    #C5944D / #E0B888
 *   terracotta   #B5694B
 *   olive        #6E6A4A
 *   deep marine  #1F4256
 *   dusk blue    #2C3A4F
 *   soft rose    #C99A92
 *   muted sand   #CBB68F
 *   ink          #0D0C0A
 */

export const BACKDROP_REGISTRY: Record<BackdropRole, BackdropAsset> = {
  "auth-hero": {
    role: "auth-hero",
    image: null,
    mobileImage: null,
    focalPoint: "50% 38%",
    tone: "cinema",
    // Cinematic dusk-over-water golden-hour mood: deep marine → dusk blue
    // lifting to warm gold + muted sand at the horizon, with an ink vignette.
    placeholder: `
      radial-gradient(120% 80% at 50% 118%, rgba(197,148,77,0.42) 0%, rgba(197,148,77,0) 52%),
      radial-gradient(100% 70% at 18% -10%, rgba(44,58,79,0.55) 0%, rgba(44,58,79,0) 60%),
      linear-gradient(195deg,
        #14202c 0%,
        #1f3142 26%,
        #2c3a4f 46%,
        #5a5238 70%,
        #8a6a3f 86%,
        #c5944d 100%)
    `,
    scrim: `
      linear-gradient(to bottom,
        rgba(11,12,16,0.42) 0%,
        rgba(11,12,16,0.18) 38%,
        rgba(11,12,16,0.34) 72%,
        rgba(11,12,16,0.58) 100%)
    `,
    blurPx: 0,
    grain: true,
    brief:
      "Login / auth full-bleed hero. Cinematic golden-hour over calm water / boutique terrace at dusk.",
  },

  "atelier-wash": {
    role: "atelier-wash",
    image: null,
    mobileImage: null,
    focalPoint: "50% 42%",
    tone: "cinema",
    // Immersive warm atelier — ember-brass glow off a deep onyx room, with a
    // terracotta whisper. Richer than beige, still calm behind dense UI.
    placeholder: `
      radial-gradient(80% 55% at 24% -8%, rgba(197,148,77,0.20) 0%, rgba(197,148,77,0) 58%),
      radial-gradient(70% 60% at 92% 8%, rgba(181,105,75,0.12) 0%, rgba(181,105,75,0) 60%),
      linear-gradient(180deg, #100e0b 0%, #15120e 40%, #1b1712 100%)
    `,
    scrim: `
      linear-gradient(to bottom,
        rgba(11,10,8,0.30) 0%,
        rgba(11,10,8,0.12) 45%,
        rgba(11,10,8,0.40) 100%)
    `,
    blurPx: 14,
    grain: true,
    brief:
      "Concierge / Explore / Saved immersive mood. Boutique-lobby golden-hour, blurred and atmospheric.",
  },

  "library-wash": {
    role: "library-wash",
    image: null,
    mobileImage: null,
    focalPoint: "50% 35%",
    tone: "paper",
    // Calm editorial paper world with warm depth — linen lifting to a soft
    // gold dawn at the top and a muted-sand floor. Trip cards stay legible.
    placeholder: `
      radial-gradient(90% 45% at 50% -6%, rgba(197,148,77,0.10) 0%, rgba(197,148,77,0) 60%),
      radial-gradient(70% 50% at 88% 4%, rgba(110,106,74,0.07) 0%, rgba(110,106,74,0) 62%),
      linear-gradient(180deg, #faf7f0 0%, #f3eee2 52%, #ece4d2 100%)
    `,
    scrim: `
      linear-gradient(to bottom,
        rgba(250,247,240,0.30) 0%,
        rgba(250,247,240,0.05) 40%,
        rgba(236,228,210,0.22) 100%)
    `,
    blurPx: 18,
    grain: false,
    brief:
      "Home / My Trips editorial atmosphere. Warm paper depth, calm enough for trip cards.",
  },

  "desk-texture": {
    role: "desk-texture",
    image: null,
    mobileImage: null,
    focalPoint: "50% 50%",
    tone: "paper",
    // Journey Desk — restrained. Subtle map/paper wash + a faint scenic glow,
    // never a busy photo behind itinerary cards.
    placeholder: `
      radial-gradient(120% 70% at 50% -20%, rgba(44,58,79,0.06) 0%, rgba(44,58,79,0) 62%),
      radial-gradient(60% 50% at 6% 18%, rgba(197,148,77,0.06) 0%, rgba(197,148,77,0) 60%),
      linear-gradient(180deg, #f7f3ea 0%, #f1ebdd 60%, #ebe3d1 100%)
    `,
    scrim: `linear-gradient(to bottom, rgba(247,243,234,0.42) 0%, rgba(235,227,209,0.30) 100%)`,
    blurPx: 22,
    grain: false,
    brief:
      "Journey Desk / Trip Detail. Subtle scenic wash or archival-map texture behind the paper desk.",
  },

  "brief-texture": {
    role: "brief-texture",
    image: null,
    mobileImage: null,
    focalPoint: "50% 50%",
    tone: "paper",
    // Brief — lightest of all. Near-flat warm paper with the faintest gold
    // breath at the top. Read-only itinerary, not a hero page.
    placeholder: `
      radial-gradient(120% 40% at 50% -10%, rgba(197,148,77,0.06) 0%, rgba(197,148,77,0) 55%),
      linear-gradient(180deg, #faf7f0 0%, #f5efe4 100%)
    `,
    scrim: `linear-gradient(to bottom, rgba(250,247,240,0.30) 0%, rgba(245,239,228,0.20) 100%)`,
    blurPx: 0,
    grain: false,
    brief:
      "Brief read-only itinerary. Lightest texture/wash, maximum legibility.",
  },
};

/**
 * Route → role mapping. Centralised so surface backdrops are controlled in one
 * place. Trip detail (/trips/<id>) is the Journey Desk; the bare /trips index
 * is the library. Auth handles its own role directly on the page.
 */
export function backdropRoleForPath(pathname: string): BackdropRole | null {
  if (pathname.startsWith("/auth")) return "auth-hero";
  if (pathname === "/") return "library-wash";
  if (pathname === "/trips") return "library-wash";
  if (pathname.startsWith("/trips/")) return "desk-texture";
  if (pathname === "/concierge") return "atelier-wash";
  if (pathname === "/explore") return "atelier-wash";
  if (pathname === "/saved") return "atelier-wash";
  return null;
}

export function getBackdrop(role: BackdropRole): BackdropAsset {
  return BACKDROP_REGISTRY[role];
}
