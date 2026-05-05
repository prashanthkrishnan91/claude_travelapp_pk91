export function splitReason(text) {
  const clean = String(text ?? "")
    .replace(/#{1,6}\s*/g, " ")
    .replace(/^\s*(?:\d{1,3}[.)]|[-*])\s+/g, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/[`*_>~]/g, " ")
    .replace(/^\s*why this pick:\s*/i, "")
    .replace(/\s+/g, " ")
    .trim();
  if (!clean) return { short: "" };
  const parts = clean.split(/(?<=[.!?])\s+/);
  const first = parts[0]?.slice(0, 220).trim() ?? "";
  return { short: first };
}

function containsAddressSignal(text) {
  return /\b\d{1,6}\s+[A-Za-z0-9.'-]+\s+(?:st|street|ave|avenue|rd|road|blvd|boulevard|dr|drive|ln|lane|way|pl|place|ct|court)\b/i.test(text);
}

export function normalizeTitle(value) {
  return String(value ?? "").trim().toLowerCase();
}

function pickWhyText(value) {
  if (!value) return undefined;
  if (typeof value === "string") return value;
  if (typeof value === "object" && typeof value.text === "string") return value.text;
  return undefined;
}

// Canonical display contract — check display.displayWhy first.
// For semantic cards (display object present): only render when displayWhyValidated===true.
// Do NOT fall back to legacy fields for semantic cards — an absent note beats a template.
// Falls back through legacy fields only for non-semantic (legacy) cards without display.
// Returns "" (empty string) when no meaningful note exists — callers must
// hide the Concierge Note block when this is empty.
export function pickCardReason(card) {
  if (card?.display !== undefined && card.display !== null) {
    // Semantic card path: only use the display.displayWhy when validated.
    if (card.display.displayWhyValidated === true
        && card.display.displayWhy
        && card.display.displayWhy.length >= 12) {
      return card.display.displayWhy;
    }
    // validated=false or empty note: return "" — do NOT fall through to legacy fields.
    return "";
  }
  // Legacy (non-semantic) card path: fall back through legacy fields.
  return pickWhyText(card?.supportingDetails?.whyPick)
    ?? pickWhyText(card?.whyPick)
    ?? card?.primaryReason
    ?? "";
}

// Display category from canonical display contract, or legacy fallback.
export function pickCardCategory(card, fallbackCategory) {
  return card?.display?.displayCategory || card?.supportingDetails?.categoryLabel || fallbackCategory || "Place";
}

const GENERIC_PHRASES_RE = /\b(a strong pick for well-reviewed|guest feedback, location, and relevance|polished night-out experience|viable option|great fit for this trip|trusted place signals|well-reviewed food|well-reviewed drinks|matches this dining request|matches this value-dinner request|fits this hotel request|fits this Michelin request|is a strong attraction match|well-rated|consistent guest ratings)\b/i;

// Patterns that indicate the old bad template output — must be filtered.
const BAD_TEMPLATE_RE = /^(?:[A-Z][^.!?]+\s+is\s+a\s+(?:restaurant|bar|hotel|attraction|place)\b[^.]*with\s+\d|[Aa]\s+(?:restaurant|bar|hotel|attraction|place)\s+with\s+\d|[Ww]ith\s+\d+[\.,]\d+\s+rating)/;

export function sanitizeWhyPick(rawReason, title, allPlaceTitles) {
  const reason = splitReason(rawReason).short;
  if (!reason || reason.length < 12) return "";
  const normalizedReason = reason.toLowerCase();
  if (containsAddressSignal(reason)) return "";
  if (/(backed by|available evidence|selected for this|verified restaurant details|verified drinks-focused|verified place details|with rated)/i.test(reason)) return "";
  if (GENERIC_PHRASES_RE.test(reason)) return "";
  if (BAD_TEMPLATE_RE.test(reason)) return "";
  const hasOtherVenueName = (allPlaceTitles || [])
    .filter((candidate) => normalizeTitle(candidate) !== normalizeTitle(title))
    .some((candidate) => normalizedReason.includes(normalizeTitle(candidate)));
  if (hasOtherVenueName) return "";
  return reason;
}

export function verifiedAddableCount(msg) {
  const restaurants = (msg?.restaurants ?? []).filter((r) => r?.type === "verified_place").length;
  const attractions = (msg?.attractions ?? []).filter((r) => r?.type === "verified_place").length;
  const hotels = (msg?.hotels ?? []).filter((r) => r?.type === "verified_place").length;
  return restaurants + attractions + hotels;
}

export function shouldShowCollapsedSources(msg) {
  const sourceCount = (msg?.researchSources ?? []).filter((s) => s?.type === "research_source").length;
  return sourceCount > 0 && verifiedAddableCount(msg) > 0;
}
