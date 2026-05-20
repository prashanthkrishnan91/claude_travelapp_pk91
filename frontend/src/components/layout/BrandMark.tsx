import { Plane } from "lucide-react";
import clsx from "clsx";

// ════════════════════════════════════════════════════════════════
// BrandMark — the Travel Concierge / Atelier wordmark glyph.
//
// A single reusable brand icon (navy marine-ink chip + cream/paper
// airplane). Used by the desktop Sidebar brand lockup AND the Home
// AtelierNavArtifact floating dock so the brand glyph is pixel-
// identical everywhere — no per-surface drift, no dark-on-dark icon.
// ════════════════════════════════════════════════════════════════

export function BrandMark({
  size = "md",
  className,
}: {
  size?: "sm" | "md";
  className?: string;
}) {
  return (
    <span
      aria-hidden="true"
      className={clsx(
        "inline-flex items-center justify-center rounded-lg bg-ds-marine-ink text-ds-paper shrink-0",
        size === "sm" ? "w-7 h-7" : "w-8 h-8",
        className,
      )}
    >
      <Plane className={size === "sm" ? "w-3.5 h-3.5" : "w-4 h-4"} />
    </span>
  );
}
