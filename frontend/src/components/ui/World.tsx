// ════════════════════════════════════════════════════════════════
// Invisible Interface — World Component Family
//
// These primitives turn a `LocationData` object into an environment
// the user can feel before they read a label. They never hardcode a
// destination — only the CSS variables exposed by `worldStyleVars`.
//
// Composition model (top → bottom):
//
//   <WorldCanvas locationData={world}>          ← injects CSS vars + scene
//     <WorldAtmosphere />                       ← mesh + drifting blobs
//     <WorldWayfinder world={world} />          ← quiet location overline
//     <WorldSurface>…</WorldSurface>            ← floating paper/glass card
//     <WorldRoomSwitcher world={world} />       ← portals to other rooms
//   </WorldCanvas>
//
// Every layer participates in environmental orientation. None of them
// re-introduces SaaS chrome.
// ════════════════════════════════════════════════════════════════

"use client";

import clsx from "clsx";
import Link from "next/link";
import type {
  AnchorHTMLAttributes,
  HTMLAttributes,
} from "react";

import {
  applyRoom,
  ROOM_CATALOGUE,
  worldStyleVars,
  worldWayfinderLine,
  type LocationData,
} from "@/lib/worldData";

type DivProps = HTMLAttributes<HTMLDivElement>;

// ─── WorldCanvas ────────────────────────────────────────────────────────────
//
// Root environment wrapper. Renders nothing visual on its own beyond binding
// CSS variables and providing the layered stage. Compose `WorldAtmosphere`
// and `WorldSurface` children to fill it.

export function WorldCanvas({
  locationData,
  className,
  style,
  children,
  ...rest
}: DivProps & { locationData: LocationData }) {
  return (
    <div
      data-world-canvas="true"
      data-world-location={locationData.location}
      data-world-archetype={locationData.archetype ?? "atelier"}
      className={clsx("world-canvas", className)}
      style={{ ...worldStyleVars(locationData), ...style }}
      {...rest}
    >
      {children}
    </div>
  );
}

// ─── WorldAtmosphere ────────────────────────────────────────────────────────
//
// Environment layer. Three slow-drifting blobs + a mesh wash, all reading from
// the world's CSS variables. Decorative only — `aria-hidden`.

export function WorldAtmosphere({ className, ...rest }: DivProps) {
  return (
    <div
      aria-hidden="true"
      className={clsx("world-atmosphere", className)}
      {...rest}
    >
      <span className="world-atmosphere-mesh" />
      <span className="world-atmosphere-blob world-atmosphere-blob-a" />
      <span className="world-atmosphere-blob world-atmosphere-blob-b" />
      <span className="world-atmosphere-blob world-atmosphere-blob-c" />
      <span className="world-atmosphere-grain" />
    </div>
  );
}

// ─── WorldScenery ───────────────────────────────────────────────────────────
//
// Full-bleed environment layer. Paints the destination's `visualLayer` —
// a curated photograph (if any) plus an image-like CSS scenic stack —
// behind the top of the page so the user *feels* the destination
// (mist, light, textile) before they read a single label. Decorative only.
//
// Tunables (driven by --world-* CSS variables on the surrounding canvas):
//   --world-scenery          painted CSS scenery (image-like gradient stack)
//   --world-scenery-image    optional url(...) photograph
//   --world-scenery-overlay  text-legibility overlay
//   --world-scenery-position image object-position
//   --world-scenery-filter   tone applied to the photograph
//
// The component layers them as:
//   [painted scenery]  →  [photograph]  →  [overlay tinted to world]
// so the painted scenery shows through if the photo never loads.

export function WorldScenery({
  height = "tall",
  className,
  imageAlt,
  ...rest
}: DivProps & {
  /** Height of the scenery stage. */
  height?: "tall" | "medium" | "short";
  /** Decorative-only, but the curator may supply an alt for the image. */
  imageAlt?: string;
}) {
  return (
    <div
      aria-hidden="true"
      data-world-scenery="true"
      data-world-scenery-height={height}
      data-world-scenery-alt={imageAlt}
      className={clsx("world-scenery", `world-scenery-${height}`, className)}
      {...rest}
    >
      <span className="world-scenery-painted" />
      <span className="world-scenery-image" />
      <span className="world-scenery-overlay" />
      <span className="world-scenery-edge" />
    </div>
  );
}

// ─── WorldMist ──────────────────────────────────────────────────────────────
//
// A slow drifting mist/light/air layer. Lives over the scenery, below
// content. Performance-safe: transform + opacity only. Stays visible on
// mobile (one layer) — only `prefers-reduced-motion` disables the drift.

export function WorldMist({ className, ...rest }: DivProps) {
  return (
    <div
      aria-hidden="true"
      className={clsx("world-mist", className)}
      {...rest}
    >
      <span className="world-mist-veil world-mist-veil-a" />
      <span className="world-mist-veil world-mist-veil-b" />
    </div>
  );
}

// ─── WorldGlassSurface ──────────────────────────────────────────────────────
//
// A floating panel made of paper-glass that lives *over* the scenery. Unlike
// WorldSurface (which is opaque paper), this one is translucent so the
// destination's mist/light reads through the panel edge. Use for the hero
// greeting card, the concierge invitation, and the active journey card.

export function WorldGlassSurface({
  tone = "paper",
  className,
  children,
  ...rest
}: DivProps & { tone?: "paper" | "smoke" | "deep" }) {
  return (
    <div
      data-world-glass="true"
      data-world-glass-tone={tone}
      className={clsx("world-glass-surface", `world-glass-${tone}`, className)}
      {...rest}
    >
      {children}
    </div>
  );
}

// ─── WorldWayfinder ─────────────────────────────────────────────────────────
//
// Quiet textual locator. Not navigation — labelling. The scenery should already
// have oriented the user; this just confirms in editorial language.

export function WorldWayfinder({
  world,
  className,
  ...rest
}: HTMLAttributes<HTMLParagraphElement> & { world: LocationData }) {
  return (
    <p
      className={clsx("world-wayfinder", className)}
      data-world-wayfinder="true"
      {...rest}
    >
      <span className="world-wayfinder-dot" aria-hidden="true" />
      {worldWayfinderLine(world)}
    </p>
  );
}

// ─── WorldSurface ───────────────────────────────────────────────────────────
//
// A floating object in the world's space. Uses paper-glass treatment that
// inherits from `--world-surface`/`--world-shadow`/`--world-mist`.

export function WorldSurface({
  variant = "paper",
  className,
  children,
  ...rest
}: DivProps & { variant?: "paper" | "mineral" | "glass" }) {
  return (
    <div
      className={clsx(
        "world-surface",
        `world-surface-${variant}`,
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  );
}

// ─── WorldPortal ────────────────────────────────────────────────────────────
//
// A doorway into another room. Renders an `<a>` (Next Link) with the
// "doorway opens" hover/focus animation. The `world` prop drives the portal's
// own atmosphere preview — so you see where the door leads before you walk
// through it.

export function WorldPortal({
  href,
  world,
  label,
  whisper,
  archetypeLine,
  className,
  children,
  ...rest
}: Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href"> & {
  href: string;
  world: LocationData;
  label: string;
  whisper: string;
  archetypeLine?: string;
}) {
  return (
    <Link
      href={href}
      className={clsx("world-portal", className)}
      data-world-portal="true"
      data-world-doorway="true"
      data-world-archetype={world.archetype ?? "atelier"}
      style={worldStyleVars(world)}
      {...rest}
    >
      <span className="world-portal-scenery" aria-hidden="true" />
      <span className="world-portal-atmosphere" aria-hidden="true" />
      <span className="world-portal-doorframe" aria-hidden="true">
        <span className="world-portal-doorframe-jamb world-portal-doorframe-jamb-left" />
        <span className="world-portal-doorframe-jamb world-portal-doorframe-jamb-right" />
        <span className="world-portal-doorframe-lintel" />
      </span>
      <span className="world-portal-doorline" aria-hidden="true" />
      <span className="world-portal-light" aria-hidden="true" />
      <span className="world-portal-body">
        <span className="world-portal-eyebrow">
          {archetypeLine ?? whisper}
        </span>
        <span className="world-portal-label">{label}</span>
        <span className="world-portal-whisper">{whisper}</span>
      </span>
      <span className="world-portal-threshold" aria-hidden="true" />
      {children}
    </Link>
  );
}

/**
 * `WorldDoorway` — semantic alias for `WorldPortal`. Some surfaces benefit
 * from reading "doorway" at the call-site. Same DOM/behaviour as WorldPortal.
 */
export const WorldDoorway = WorldPortal;

// ─── WorldRoomSwitcher ──────────────────────────────────────────────────────
//
// A horizontal row of portals to the four canonical rooms (Concierge, Explore,
// Planning, Saved). Each room inherits the active world's ink/surface but
// applies its own archetype atmosphere — so the four portals feel like four
// different rooms in the same hotel.

export function WorldRoomSwitcher({
  world,
  active,
  className,
  ...rest
}: DivProps & { world: LocationData; active?: string }) {
  return (
    <nav
      aria-label="Rooms"
      data-world-room-switcher="true"
      className={clsx("world-room-switcher", className)}
      {...rest}
    >
      {ROOM_CATALOGUE.map((room) => {
        const roomWorld = applyRoom(world, room.archetype);
        const isActive = active === room.id;
        return (
          <WorldPortal
            key={room.id}
            href={room.href}
            world={roomWorld}
            label={room.label}
            whisper={room.whisper}
            data-active={isActive ? "true" : undefined}
            aria-current={isActive ? "page" : undefined}
          />
        );
      })}
    </nav>
  );
}

// ─── WorldHero ──────────────────────────────────────────────────────────────
//
// Composition slot for the page's editorial hero. Pure layout — the surface
// underneath should already feel world-bound. Renders as a flexible spread
// with the wayfinder always present.

export function WorldHero({
  world,
  className,
  children,
  ...rest
}: DivProps & { world: LocationData }) {
  return (
    <header
      data-world-hero="true"
      className={clsx("world-hero", className)}
      {...rest}
    >
      <WorldWayfinder world={world} className="world-hero-wayfinder" />
      {children}
    </header>
  );
}

// ─── WorldLayer ─────────────────────────────────────────────────────────────
//
// Generic depth layer for arbitrary atmospheric content (a photograph, an
// SVG horizon, a slow scroll element). Reserved for future slices — exposed
// now so consumers can adopt without churning components.

export function WorldLayer({
  depth = 0,
  className,
  children,
  ...rest
}: DivProps & { depth?: -2 | -1 | 0 | 1 | 2 }) {
  return (
    <div
      data-world-layer="true"
      data-depth={depth}
      className={clsx("world-layer", `world-layer-depth-${depth}`, className)}
      {...rest}
    >
      {children}
    </div>
  );
}

// ─── Re-export typing helpers for consumers ────────────────────────────────

export type { LocationData };

export function withRoom(
  world: LocationData,
  archetype: NonNullable<LocationData["archetype"]>,
): LocationData {
  return applyRoom(world, archetype);
}
