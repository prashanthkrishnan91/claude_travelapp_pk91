import clsx from "clsx";

export type TrustConfidence = "high" | "medium" | "low";

export interface TrustStripProps {
  /** When true, renders "Verified by Google". Must be explicitly set — never inferred. */
  verified?:     boolean;
  /** Number of distinct sources backing this result. Omitted when unknown. */
  sourceCount?:  number;
  /** Qualitative confidence level. Omitted when unknown. */
  confidence?:   TrustConfidence;
  /** Short caveat text shown when evidence is weak or incomplete. */
  caveat?:       string;
  className?:    string;
}

const CONFIDENCE_LABEL: Record<TrustConfidence, string> = {
  high:   "High confidence",
  medium: "Moderate confidence",
  low:    "Low confidence",
};

const CONFIDENCE_CLASS: Record<TrustConfidence, string> = {
  high:   "text-emerald-400",
  medium: "text-amber-400",
  low:    "text-cream-400 opacity-70",
};

export function TrustStrip({
  verified,
  sourceCount,
  confidence,
  caveat,
  className,
}: TrustStripProps) {
  const hasContent = verified || sourceCount != null || confidence || caveat;
  if (!hasContent) return null;

  return (
    <div
      role="region"
      aria-label="Source trust signals"
      className={clsx(
        "flex flex-wrap items-center gap-x-3 gap-y-1 text-xs",
        className,
      )}
    >
      {/* "Verified by Google" only when explicitly confirmed — no inference */}
      {verified && (
        <span className="flex items-center gap-1 font-medium text-emerald-400">
          <svg
            aria-hidden="true"
            width="12"
            height="12"
            viewBox="0 0 12 12"
            fill="none"
          >
            <path
              d="M2 6.5L4.5 9L10 3"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          Verified by Google
        </span>
      )}

      {typeof sourceCount === "number" && sourceCount > 0 && (
        <span className="text-cream-400">
          <span className="sr-only">Based on </span>
          {sourceCount}&nbsp;source{sourceCount !== 1 ? "s" : ""}
        </span>
      )}

      {confidence && (
        <span
          aria-label={CONFIDENCE_LABEL[confidence]}
          className={clsx("font-medium", CONFIDENCE_CLASS[confidence])}
        >
          {CONFIDENCE_LABEL[confidence]}
        </span>
      )}

      {caveat && (
        <span role="note" className="text-cream-500 italic">
          {caveat}
        </span>
      )}
    </div>
  );
}
