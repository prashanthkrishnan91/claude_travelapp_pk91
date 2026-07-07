# Atmospheric Background System v1 — Asset Manifest

This folder holds the **curated, local, licensed** editorial photography for the
app's atmospheric background system. The system is wired and live today using
**premium gradient placeholders** — no photographic assets ship in the repo yet.

To activate real photography for a role:

1. Drop a licensed image file into this folder using the filename below.
2. Set that role's `image` (and optionally `mobileImage`) field in
   `frontend/src/lib/atmosphere/backgrounds.ts` to `/atmosphere/<file>`.
3. No other code changes are required — `<AtelierBackdrop>` picks it up and
   renders it through `next/image` with the role's blur / scrim / grain.

> **Do not** point a role's `image` at a remote/hotlinked URL. Assets must be
> local, licensed/allowed for this use, and listed here.

## Art direction (read before sourcing)

Premium editorial travel photography ONLY. Reference vibe: Condé Nast Traveller
editorial; Aman / Belmond / Six Senses calm; film photography; warm shadows,
soft highlights, restrained color.

**Allowed moods:** boutique hotel lobby at golden hour · quiet Mediterranean
courtyard · soft train-/airplane-window light · warm city street after rain ·
archival map / paper / passport texture · calm blurred coastal or desert light ·
luxury travel journal / private itinerary folio.

**Never:** stock-photo clichés · cartoons · vector illustrations · bright
postcard/tourism-board imagery · busy landmark hero shots behind dense UI ·
AI-looking fantasy scenes · readable text/logos/watermarks · close-up faces /
people-focused lifestyle shots.

**Palette:** keep the cream / paper / ink identity; introduce warm gold, muted
terracotta, olive, deep marine, dusk blue, soft rose, muted sand. Avoid neon,
bright cyan, cartoon blue, saturated tropical color, harsh gradients.

## Required files (one per role)

| Role            | Filename (desktop)     | Mobile crop (optional)        | Mood to source |
|-----------------|------------------------|-------------------------------|----------------|
| `auth-hero`     | `auth-hero.jpg`        | `auth-hero-mobile.jpg`        | Strongest cinematic full-bleed. Golden-hour over calm water / boutique terrace at dusk. The emotional hook. |
| `atelier-wash`  | `atelier-wash.jpg`     | `atelier-wash-mobile.jpg`     | Immersive boutique-lobby golden hour, blurred & atmospheric. For Concierge / Explore / Saved. |
| `library-wash`  | `library-wash.jpg`     | `library-wash-mobile.jpg`     | Calm warm editorial paper depth. For Home / My Trips. Must stay calm behind trip cards. |
| `desk-texture`  | `desk-texture.jpg`     | —                             | Subtle archival map / paper / blurred scenic wash. Behind the Journey Desk — restrained. |
| `brief-texture` | `brief-texture.jpg`    | —                             | Lightest paper/photo wash. Behind the read-only Brief. Maximum legibility. |

Prefer **4–6 reusable assets** total (a role per family), not a unique image
per page. Export desktop at ~2400px wide, mobile crop at ~1080px wide, quality
tuned for atmosphere (these sit under a blur + scrim, so they compress well).

## Format / performance

- Prefer `.jpg`/`.webp`. They render under blur + scrim, so heavy detail is
  wasted weight — optimize aggressively.
- Served from `/public` via `next/image` (`fill`, `sizes="100vw"`), so Next
  handles responsive sizing and lazy/priority loading. `auth-hero` is loaded
  with `priority`; all others lazy by default.
- The gradient color bed always renders first, so there is no flash and no
  layout shift while an image decodes.
