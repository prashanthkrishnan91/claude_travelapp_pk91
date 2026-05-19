// Canonical Folio / Cinema UI primitives — Stage 3.5 Unified UI Architecture.
//
// Paper-world surfaces (Folio*) use warm bone/linen backgrounds with dark
// folio-ink text. Cinema-world surfaces (Cinema*) use warm dark velvet
// backgrounds with cream text. Feature files should compose these primitives
// instead of inventing local Tailwind class stacks — that's how we keep the
// app visually coherent across surfaces.
//
// Routing rule:
//   Paper world  → Home, My Trips, Trip Build, Trip Itinerary, Trip Ideas,
//                  New Trip form, planning modals.
//   Cinema world → Discover (Explore), Saved, AI Concierge.
//
// These primitives wrap the canonical CSS classes already defined in
// globals.css; they do not introduce new visual identity. The point is to
// give feature files a stable, intentional API.

import clsx from "clsx";
import type {
  ButtonHTMLAttributes,
  HTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
} from "react";

// ─── Folio (paper) primitives ───────────────────────────────────────────────

type DivProps = HTMLAttributes<HTMLDivElement>;

/** Paper-world page wrapper. Use as the outermost surface for paper screens. */
export function FolioPage({ className, children, ...rest }: DivProps) {
  return (
    <div
      data-folio-world="paper"
      className={clsx("folio-page space-y-6", className)}
      {...rest}
    >
      {children}
    </div>
  );
}

/** Paper-world panel — warm paper surface, hairline border, soft shadow. */
export function FolioPanel({ className, children, ...rest }: DivProps) {
  return (
    <div
      data-folio-world="paper"
      className={clsx("folio-paper-panel", className)}
      {...rest}
    >
      {children}
    </div>
  );
}

/** Paper-world card — bone surface, hairline border, soft warm shadow. */
export function FolioCard({ className, children, ...rest }: DivProps) {
  return (
    <div
      data-folio-world="paper"
      className={clsx("folio-paper-card text-ds-folio-ink", className)}
      {...rest}
    >
      {children}
    </div>
  );
}

/** Overline + heading combination for paper-world section headers. */
export function FolioSectionHeader({
  overline,
  title,
  className,
  children,
}: {
  overline?: ReactNode;
  title?: ReactNode;
  className?: string;
  children?: ReactNode;
}) {
  return (
    <header data-folio-world="paper" className={clsx("space-y-1", className)}>
      {overline && (
        <p className="folio-muted-label text-ds-folio-ink-mist">{overline}</p>
      )}
      {title && (
        <h2 className="text-base font-semibold text-ds-folio-ink leading-tight">
          {title}
        </h2>
      )}
      {children}
    </header>
  );
}

/** Paper-world form field — bone surface, hairline border, dark folio ink text. */
export function FolioInput({
  className,
  ...rest
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      data-folio-world="paper"
      className={clsx("folio-input", className)}
      {...rest}
    />
  );
}

/** Paper-world chip — hairline pill with optional active variant. */
export function FolioChip({
  active = false,
  className,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { active?: boolean }) {
  return (
    <button
      type="button"
      data-folio-world="paper"
      data-active={active ? "true" : undefined}
      className={clsx(
        "inline-flex items-center gap-1 min-h-[32px] px-3 rounded-full text-xs font-medium border transition-colors",
        active
          ? "bg-ds-accent text-ds-text-inverse border-ds-accent shadow-sm"
          : "bg-transparent text-ds-folio-ink-soft border-ds-hairline hover:bg-ds-bone hover:text-ds-folio-ink",
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}

/** Paper-world primary button — marine ink fill, paper-safe contrast. */
export function FolioButton({
  variant = "primary",
  className,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
}) {
  const base =
    "inline-flex items-center gap-1.5 min-h-[44px] transition-colors disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2";
  const variants: Record<string, string> = {
    primary:
      "px-4 rounded-xl bg-ds-accent hover:bg-ds-accent-muted text-ds-text-inverse text-sm font-semibold",
    secondary:
      "px-4 rounded-xl bg-ds-linen hover:bg-ds-bone text-ds-folio-ink-soft hover:text-ds-folio-ink border border-ds-hairline text-sm font-medium",
    ghost: "btn-folio-ghost",
  };
  return (
    <button
      type="button"
      data-folio-world="paper"
      className={clsx(base, variants[variant], className)}
      {...rest}
    >
      {children}
    </button>
  );
}

// ─── Cinema (dark) primitives ───────────────────────────────────────────────

/** Cinema-world page wrapper. Use for Discover, Saved, AI Concierge. */
export function CinemaPage({ className, children, ...rest }: DivProps) {
  return (
    <div
      data-folio-world="cinema"
      className={clsx("cinema-page space-y-6", className)}
      {...rest}
    >
      {children}
    </div>
  );
}

/** Cinema-world panel — warm dark velvet surface, brass hairline. */
export function CinemaPanel({ className, children, ...rest }: DivProps) {
  return (
    <div
      data-folio-world="cinema"
      className={clsx("folio-cinema-card text-ds-text", className)}
      {...rest}
    >
      {children}
    </div>
  );
}

/** Cinema-world card — warm dark carbon surface, brass hairline. */
export function CinemaCard({ className, children, ...rest }: DivProps) {
  return (
    <div
      data-folio-world="cinema"
      className={clsx("folio-cinema-card text-ds-text", className)}
      {...rest}
    >
      {children}
    </div>
  );
}

// ─── Folio Scene System — Stage 3.5 Atelier Scene ──────────────────────────
// Reusable scene, motion, layering, and route primitives for any paper-world
// screen (Home, Trip Builder, New Trip, Trip Ideas, planning modals, future
// paper-world surfaces). Not Home-specific.

/** Scene/stage wrapper for paper-world screens.
 *  Adds multi-point ambient warmth, a slow drifting glow, and isolation
 *  for correct stacking. Reusable on any paper-world screen. */
export function FolioScene({ className, children, ...rest }: DivProps) {
  return (
    <div
      data-folio-world="paper"
      className={clsx("folio-scene", className)}
      {...rest}
    >
      {children}
    </div>
  );
}

/** Entrance animation wrapper — fades up from 6px below on first render.
 *  stagger: 1–4 offsets the animation start by N × 80ms for sequential
 *  reveal rhythm. Reduced-motion: renders at full opacity immediately. */
export function FolioReveal({
  stagger,
  className,
  children,
  ...rest
}: DivProps & { stagger?: 1 | 2 | 3 | 4 }) {
  return (
    <div
      className={clsx(
        "folio-reveal",
        stagger != null && `folio-reveal-stagger-${stagger}`,
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  );
}

/** Decorative horizontal route thread — map/journey motif.
 *  Always aria-hidden; use between or within sections for editorial rhythm. */
export function FolioRouteThread({ className, ...rest }: DivProps) {
  return (
    <div
      aria-hidden="true"
      className={clsx("folio-route-thread", className)}
      {...rest}
    />
  );
}

// ─── Folio Living Atelier primitives — paper-world editorial surfaces ──────
// Reusable composition pieces for any paper-world screen that needs an
// immersive, editorial-magazine feeling (Home, future destination spreads,
// trip hero pages). Class names live in globals.css under FOLIO LIVING
// ATELIER — these components are thin React shells over those classes so
// callers don't reinvent the styling.

/** Living-canvas wrapper. Adds two slow-drifting warm sunlight blobs
 *  behind in-flow content. Compose with FolioScene for full atmosphere. */
export function FolioLivingCanvas({ className, children, ...rest }: DivProps) {
  return (
    <div
      data-folio-world="paper"
      className={clsx("folio-living-canvas", className)}
      {...rest}
    >
      {children}
    </div>
  );
}

/** Editorial hero spread — eyebrow + serif headline + italic subline.
 *  Pure composition (no surface). Place inside a FolioScene/Canvas. */
export function FolioAtelierHero({
  className,
  children,
  ...rest
}: DivProps) {
  return (
    <div
      data-folio-world="paper"
      className={clsx("folio-atelier-hero", className)}
      {...rest}
    >
      {children}
    </div>
  );
}

/** Atelier invitation panel — concierge entry as a private invitation.
 *  Layered paper depth, soft brass ring, brass corner glow. */
export function FolioAtelierInvitation({
  className,
  children,
  ...rest
}: DivProps) {
  return (
    <div
      data-folio-world="paper"
      className={clsx("folio-atelier-invitation", className)}
      {...rest}
    >
      {children}
    </div>
  );
}

/** CTA glide wrapper. Wraps a link/button; its child with class
 *  `folio-cta-arrow` translates 6px on hover/focus with luxury easing. */
export function FolioCtaGlide({ className, children, ...rest }: DivProps) {
  return (
    <span className={clsx("folio-cta-glide", className)} {...rest}>
      {children}
    </span>
  );
}

/** Active journey object — tactile dossier card with optional painted
 *  cover plate and a hover/focus-revealed micro-timeline slot.
 *  Pass `as` to render as a link or button when needed. */
export function FolioActiveJourneyObject({
  className,
  children,
  ...rest
}: DivProps) {
  return (
    <div
      data-folio-world="paper"
      className={clsx("folio-active-journey-object", className)}
      {...rest}
    >
      {children}
    </div>
  );
}

/** Painted atmospheric cover plate for a journey object.
 *  Pure CSS — no photo, no fabricated destination imagery. */
export function FolioJourneyCover({
  className,
  children,
  ...rest
}: DivProps) {
  return (
    <div
      aria-hidden="true"
      className={clsx("folio-journey-cover", className)}
      {...rest}
    >
      {children}
    </div>
  );
}

/** Reveal slot inside a FolioActiveJourneyObject — collapsed by default,
 *  unfurls on hover/focus-within with luxury easing. */
export function FolioJourneyUnfurl({
  className,
  children,
  ...rest
}: DivProps) {
  return (
    <div className={clsx("folio-journey-unfurl", className)} {...rest}>
      {children}
    </div>
  );
}

/** Editorial discovery artifact tile — small bespoke artifact, not a SaaS tile. */
export function FolioArtifactTile({
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      data-folio-world="paper"
      className={clsx("folio-artifact-tile", className)}
      {...rest}
    >
      {children}
    </div>
  );
}

/** Fanned scrapbook shelf preview — two paper edges visible behind the front sheet. */
export function FolioShelfSpread({
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      data-folio-world="paper"
      className={clsx("folio-shelf-spread", className)}
      {...rest}
    >
      {children}
    </div>
  );
}

/** Cinema-world chip — warm dark pill. Use for filters/prompts on dark surfaces. */
export function CinemaChip({
  active = false,
  className,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { active?: boolean }) {
  return (
    <button
      type="button"
      data-folio-world="cinema"
      data-active={active ? "true" : undefined}
      className={clsx(
        "inline-flex items-center gap-1 min-h-[32px] px-3 rounded-full text-xs font-medium border transition-colors",
        active
          ? "bg-ds-accent text-ds-text-inverse border-ds-accent shadow-sm"
          : "folio-concierge-chip text-ds-text hover:text-ds-text",
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}
