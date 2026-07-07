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
    // Cinematic warm-dusk travel-film opening: deep warm ink descends into
    // rich amber-bronze shadow, then opens into a luminous golden horizon
    // (#c5944d → #e0b888). The base is entirely warm — no cold blues.
    // Two amber blooms push warmth up from the horizon; a faint ink veil
    // at the top gives depth without cooling the palette.
    placeholder: `
      radial-gradient(160% 110% at 50% 130%, rgba(224,184,136,0.92) 0%, rgba(197,148,77,0.62) 30%, rgba(197,148,77,0) 58%),
      radial-gradient( 80%  56% at 22%  0%,  rgba(16,10,4,0.70)     0%, rgba(16,10,4,0)      48%),
      radial-gradient( 60%  44% at 82%  2%,  rgba(26,16,6,0.45)     0%, rgba(26,16,6,0)      50%),
      linear-gradient(185deg,
        #0c0906 0%,
        #1a1208 18%,
        #2e1e0c 34%,
        #4a3218 48%,
        #6a4c22 64%,
        #9a7238 80%,
        #c5944d 92%,
        #e0b888 100%)
    `,
    scrim: `
      linear-gradient(to bottom,
        rgba(6,8,12,0.62) 0%,
        rgba(6,8,12,0.26) 32%,
        rgba(6,8,12,0.18) 58%,
        rgba(6,8,12,0.70) 100%)
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
    // Private travel atelier — the boutique salon at golden hour.
    // Stronger brass bloom (52%) at upper-left: a warm amber window of light
    // from outside. Terracotta at lower-right (26%) warms the far wall.
    // Central amber uplighting (32%) lifts the floor. Base is warm near-black
    // (#120e08), warm-tinted so the room never reads as cold charcoal.
    // Blur reduced (8px) so the blooms read as distinct warm sources, not haze.
    placeholder: `
      radial-gradient(88% 60% at 18% -4%, rgba(197,148,77,0.52) 0%, rgba(197,148,77,0) 55%),
      radial-gradient(68% 56% at 92%  6%, rgba(181,105,75,0.26) 0%, rgba(181,105,75,0) 54%),
      radial-gradient(55% 48% at 50% 108%, rgba(160,108,54,0.32) 0%, rgba(160,108,54,0) 52%),
      radial-gradient(40% 36% at 72% 78%, rgba(197,148,77,0.14) 0%, rgba(197,148,77,0) 58%),
      linear-gradient(180deg, #120e08 0%, #160e08 32%, #1c1208 62%, #221610 100%)
    `,
    scrim: `
      linear-gradient(to bottom,
        rgba(10,7,4,0.30) 0%,
        rgba(10,7,4,0.06) 40%,
        rgba(10,7,4,0.32) 100%)
    `,
    blurPx: 8,
    grain: true,
    brief:
      "Concierge / Explore / Saved immersive mood. Boutique-lobby at golden hour, blurred and atmospheric.",
  },

  "library-wash": {
    role: "library-wash",
    image: null,
    mobileImage: null,
    focalPoint: "50% 35%",
    tone: "paper",
    // Editorial paper library with clearly warm depth — a visible gold-dawn
    // bloom at the top (~22% opacity vs the old 10%), a terracotta whisper at
    // the lower corner, and a base that shifts from warm honey (#ede0c4) up to
    // burnished cream (#f5edd8). The gradient reads as "warm and editorial"
    // rather than "flat beige" when seen against white page chrome.
    placeholder: `
      radial-gradient(92% 52% at 50% -4%,  rgba(197,148,77,0.28) 0%, rgba(197,148,77,0) 56%),
      radial-gradient(72% 54% at 88%  3%,  rgba(110,106,74,0.18) 0%, rgba(110,106,74,0) 60%),
      radial-gradient(80% 60% at  6% 98%,  rgba(181,105,75,0.12) 0%, rgba(181,105,75,0) 65%),
      linear-gradient(180deg, #f5edd8 0%, #ede0c6 48%, #e6d8b8 100%)
    `,
    scrim: `
      linear-gradient(to bottom,
        rgba(245,237,216,0.18) 0%,
        rgba(245,237,216,0)    28%,
        rgba(230,216,184,0.15) 100%)
    `,
    blurPx: 18,
    grain: false,
    brief:
      "Home / My Trips editorial atmosphere. Warm honey-paper depth, calm enough for trip cards.",
  },

  "desk-texture": {
    role: "desk-texture",
    image: null,
    mobileImage: null,
    focalPoint: "50% 50%",
    tone: "paper",
    // Journey Desk — restrained but detectable. A marine-cool bloom at the top
    // (14% opacity) gives the work surface a map/cartographic quality distinct
    // from the library-wash's gold-warm reading room. A softer amber corner
    // adds warmth so the desk doesn't feel sterile. Base is a cool-tinted
    // parchment (#eee8da) so the atmosphere is perceptible at a glance.
    placeholder: `
      radial-gradient(120% 72% at 50% -16%, rgba(44,58,79,0.14) 0%, rgba(44,58,79,0) 60%),
      radial-gradient( 60% 52% at  6% 18%, rgba(197,148,77,0.11) 0%, rgba(197,148,77,0) 58%),
      radial-gradient( 50% 42% at 96% 82%, rgba(110,106,74,0.08) 0%, rgba(110,106,74,0) 55%),
      linear-gradient(180deg, #eee8da 0%, #e8e0ce 55%, #e2d8c4 100%)
    `,
    scrim: `linear-gradient(to bottom, rgba(238,232,218,0.38) 0%, rgba(226,216,196,0.25) 100%)`,
    blurPx: 22,
    grain: false,
    brief:
      "Journey Desk / Trip Detail. Subtle map/cartographic wash behind the paper planning desk.",
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
