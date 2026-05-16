import { formatDisplayPrice } from "./priceFormatter";

// ── Closed-signal detection ───────────────────────────────────────────────────
// Shared between standalone ConciergePage and trip-context AIConciergePanel.

export const CLOSED_SIGNAL_PATTERNS = [
  "permanently closed",
  "closed permanently",
  "closed for good",
  "closed for the final time",
  "has closed",
  "is closed",
  "shut down",
  "no longer open",
  "won't reopen",
  "will not reopen",
] as const;

export type ClosedSignalSource = Partial<{
  name: unknown;
  title: unknown;
  summary: unknown;
  description: unknown;
  reason: unknown;
  source: unknown;
  sourceText: unknown;
  rawText: unknown;
  url: unknown;
  sourceUrl: unknown;
  snippet: unknown;
  raw: unknown;
}>;

export function hasClosedSignal(card: ClosedSignalSource): boolean {
  const textBlob = [
    card.name,
    card.title,
    card.summary,
    card.description,
    card.reason,
    card.source,
    card.sourceText,
    card.rawText,
    card.url,
    card.sourceUrl,
    card.snippet,
  ]
    .map((v) => String(v ?? "").toLowerCase())
    .join("\n");
  return CLOSED_SIGNAL_PATTERNS.some((signal) => textBlob.includes(signal));
}

// ── Operational badge helper ──────────────────────────────────────────────────
// Only Google-verified OPERATIONAL venues with high/medium confidence qualify.

export type OperationalBadgeCard = {
  googleVerification?: {
    businessStatus?: string | null;
    confidence?: string | null;
    providerPlaceId?: string | null;
  } | null;
};

export function canShowGoogleVerifiedBadge(card: OperationalBadgeCard): boolean {
  if (hasClosedSignal(card as ClosedSignalSource)) return false;
  const gv = card.googleVerification;
  if (!gv) return false;
  if (gv.businessStatus !== "OPERATIONAL") return false;
  const c = (gv.confidence ?? "").toLowerCase();
  if (c !== "high" && c !== "medium") return false;
  if (!gv.providerPlaceId) return false;
  return true;
}

// ── Card meta line composer ───────────────────────────────────────────────────
// Reads only the canonical display contract for the subheader meta line.
// Never falls back to top-level rating, reviewCount, or neighborhood.

export type DisplayCard = {
  display?: {
    displayMetaLine?: string | null;
    displayPrice?: string | null;
  } | null;
  supportingDetails?: {
    metaLine?: string | null;
    address?: string | null;
    priceLevel?: string | null;
    priceRange?: Record<string, unknown> | null;
  } | null;
};

export function pickCardMeta(card: DisplayCard): string[] {
  const details = card.supportingDetails;
  const price =
    card.display?.displayPrice ??
    formatDisplayPrice(
      (details?.priceLevel as string | null) ?? null,
      (details?.priceRange as Record<string, unknown> | null) ?? null,
    ) ??
    undefined;
  const address = details?.address ?? undefined;
  const ratingBase = card.display?.displayMetaLine ?? details?.metaLine;
  if (!ratingBase && !price && !address) return [];
  if (ratingBase) {
    const addrTrimmed = address?.trim() ?? "";
    let stem = ratingBase;
    if (addrTrimmed && ratingBase.includes(addrTrimmed)) {
      const stripped = ratingBase.slice(0, ratingBase.indexOf(addrTrimmed)).replace(/\s*·\s*$/, "").trim();
      if (stripped) stem = stripped;
    }
    const parts: string[] = [stem];
    const metaAlreadyHasPrice = /\$|Free\b|EUR/.test(stem);
    if (price && !metaAlreadyHasPrice) parts.push(price);
    if (address) parts.push(address);
    return [parts.join(" · ")];
  }
  const parts: string[] = [];
  if (price) parts.push(price);
  if (address) parts.push(address);
  return parts.length > 0 ? [parts.join(" · ")] : [];
}
