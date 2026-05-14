import clsx from "clsx";
import type { HTMLAttributes, ReactNode } from "react";

// ── Tone ────────────────────────────────────────────────────────────────────
export type CardTone = "dark" | "paper";

const TONE_CLASSES: Record<CardTone, string> = {
  dark:  "bg-ds-onyx  border-ds-pen-stroke text-ds-text",
  paper: "bg-ds-paper border-ds-hairline   text-ds-text-inverse",
};

// ── Root ────────────────────────────────────────────────────────────────────
export interface CardProps extends HTMLAttributes<HTMLElement> {
  tone?:      CardTone;
  as?:        "article" | "div" | "li" | "section";
  children?:  ReactNode;
}

function CardRoot({
  tone = "dark",
  as: Tag = "div",
  className,
  children,
  ...rest
}: CardProps) {
  return (
    <Tag className={clsx("card", TONE_CLASSES[tone], className)} {...rest}>
      {children}
    </Tag>
  );
}

// ── Slot prop type (shared) ──────────────────────────────────────────────────
interface SlotProps extends HTMLAttributes<HTMLDivElement> {
  children?: ReactNode;
}

// ── Slots ────────────────────────────────────────────────────────────────────

/** Name, category, rating — primary identity of the place/offer. */
function CardIdentity({ className, children, ...rest }: SlotProps) {
  return (
    <div className={clsx("flex items-start gap-3", className)} {...rest}>
      {children}
    </div>
  );
}

/** Trust strip, source count, or verification badge slot. */
function CardTrust({ className, children, ...rest }: SlotProps) {
  return (
    <div
      role="region"
      aria-label="Trust signals"
      className={clsx(className)}
      {...rest}
    >
      {children}
    </div>
  );
}

/** Hero image or map preview. */
function CardMedia({ className, children, ...rest }: SlotProps) {
  return (
    <div className={clsx("overflow-hidden rounded-lg", className)} {...rest}>
      {children}
    </div>
  );
}

/** AI or editorial "why pick this" explanation. */
function CardWhy({ className, children, ...rest }: SlotProps) {
  return (
    <p className={clsx("text-sm leading-relaxed", className)} {...rest}>
      {children}
    </p>
  );
}

/** Tags, price tier, distance chips — secondary metadata. */
function CardMeta({ className, children, ...rest }: SlotProps) {
  return (
    <div
      className={clsx("flex flex-wrap items-center gap-2", className)}
      {...rest}
    >
      {children}
    </div>
  );
}

/** Primary and secondary action buttons. */
function CardActions({ className, children, ...rest }: SlotProps) {
  return (
    <div className={clsx("flex items-center gap-2", className)} {...rest}>
      {children}
    </div>
  );
}

/** Weak-evidence note, data-freshness caveat, or disclaimer. */
function CardCaveat({ className, children, ...rest }: SlotProps) {
  return (
    <p
      role="note"
      className={clsx("text-xs opacity-70 leading-snug italic", className)}
      {...rest}
    >
      {children}
    </p>
  );
}

// ── Compose ──────────────────────────────────────────────────────────────────
export const Card = Object.assign(CardRoot, {
  Identity: CardIdentity,
  Trust:    CardTrust,
  Media:    CardMedia,
  Why:      CardWhy,
  Meta:     CardMeta,
  Actions:  CardActions,
  Caveat:   CardCaveat,
});
