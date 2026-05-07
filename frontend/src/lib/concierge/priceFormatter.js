/**
 * Google-backed price display formatter for AI Concierge cards.
 *
 * Rules:
 *  - priceRange first: compact "$10–20" using Google's Money fields.
 *  - priceLevel fallback: Google-style symbols ("$", "$$", "$$$", "$$$$").
 *  - Returns null when no usable price signal — never returns raw enum names.
 *  - Never invents prices; only uses what Google explicitly provided.
 */

const PRICE_LEVEL_SYMBOL = {
  PRICE_LEVEL_FREE: 'Free',
  PRICE_LEVEL_INEXPENSIVE: '$',
  PRICE_LEVEL_MODERATE: '$$',
  PRICE_LEVEL_EXPENSIVE: '$$$',
  PRICE_LEVEL_VERY_EXPENSIVE: '$$$$',
};

/**
 * Format a Google priceRange object into a compact string.
 * @param {{ startPrice?: object, endPrice?: object } | null} priceRange
 * @returns {string|null}
 */
function formatPriceRange(priceRange) {
  if (!priceRange || typeof priceRange !== 'object') return null;
  const start = priceRange.startPrice;
  const end = priceRange.endPrice;
  if (!start || !end || typeof start !== 'object' || typeof end !== 'object') return null;
  const startUnits = parseInt(start.units ?? '0', 10);
  const endUnits = parseInt(end.units ?? '0', 10);
  if (isNaN(startUnits) || isNaN(endUnits)) return null;
  if (startUnits === 0 && endUnits === 0) return null;
  const currency = start.currencyCode ?? end.currencyCode ?? 'USD';
  const symbol = currency === 'USD' ? '$' : currency;
  return `${symbol}${startUnits}–${endUnits}`;
}

/**
 * Return a compact UI price string from Google price fields, or null.
 *
 * @param {string|null} priceLevel - Google priceLevel enum string
 * @param {object|null} priceRange - Google PriceRange {startPrice, endPrice}
 * @returns {string|null}
 */
export function formatDisplayPrice(priceLevel, priceRange) {
  const fromRange = formatPriceRange(priceRange ?? null);
  if (fromRange) return fromRange;
  if (priceLevel) return PRICE_LEVEL_SYMBOL[priceLevel] ?? null;
  return null;
}
