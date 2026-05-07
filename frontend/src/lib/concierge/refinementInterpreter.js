/**
 * Conversational refinement interpreter for AI Concierge.
 *
 * Parses a user follow-up message into one of seven action classes, then
 * applies the action to the current verified card set without calling the
 * backend (except SEARCH_MORE_WITH_CONTEXT which routes through the
 * existing callConciergeSearch path).
 *
 * Contracts:
 *  - Only reads visible card fields: name, category, rating, note, tags, area.
 *  - Never mints new cards; filtered results are subsets of the original set.
 *  - Never accesses internal metadata (dossiers, evidence, reviewer labels).
 *  - All returned card arrays remain Google-verified and addable.
 */

export const ACTION = {
  FILTER_CURRENT_SET: 'FILTER_CURRENT_SET',
  REMOVE_FROM_CURRENT_SET: 'REMOVE_FROM_CURRENT_SET',
  RERANK_CURRENT_SET: 'RERANK_CURRENT_SET',
  COMPARE_CURRENT_SET: 'COMPARE_CURRENT_SET',
  ADD_SELECTED_TO_DAY: 'ADD_SELECTED_TO_DAY',
  SEARCH_MORE_WITH_CONTEXT: 'SEARCH_MORE_WITH_CONTEXT',
  CLARIFY_UNSUPPORTED: 'CLARIFY_UNSUPPORTED',
};

// Ordered by specificity — first match wins.
const ACTION_MATCHERS = [
  {
    action: ACTION.COMPARE_CURRENT_SET,
    patterns: [
      /compare\s+(?:the\s+)?(?:first\s+(?:two|2)|top\s+(?:two|2)|two|2|them|these|both)/i,
      /how\s+do\s+(?:the\s+)?(?:first\s+(?:two|2)|top\s+(?:two|2)|they|these)\s+(?:compare|differ|stack\s+up)/i,
      /difference\s+between\s+(?:the\s+)?(?:first\s+(?:two|2)|top\s+(?:two|2))/i,
      /which\s+is\s+(?:better|the\s+better)\b/i,
    ],
  },
  {
    action: ACTION.ADD_SELECTED_TO_DAY,
    patterns: [
      /add\s+(?:the\s+)?(?:best|first|top)\s+(?:one\s+)?to\s+(?:day|my\s+trip|itinerary)/i,
      /put\s+(?:the\s+)?(?:best|first|top)\s+(?:one\s+)?(?:on|in)\s+(?:day|my\s+itinerary)/i,
      /book\s+(?:the\s+)?(?:best|first|top)\s+one/i,
    ],
  },
  {
    action: ACTION.REMOVE_FROM_CURRENT_SET,
    patterns: [
      /^(?:remove|hide|exclude|drop)\b/i,
      /^get\s+rid\s+of\b/i,
      /^(?:no|without)\s+(?:more\s+)?[a-z]/i,
      /\bremove\s+(?:any|all|the)\b/i,
    ],
  },
  {
    action: ACTION.FILTER_CURRENT_SET,
    patterns: [
      /^show\s+(?:me\s+)?(?:only|just)\b/i,
      /^(?:only|just)\s+(?:show|display|the)\b/i,
      /^filter\s+(?:to|by|for|down)\b/i,
      /^narrow\s+(?:down|to|it)\b/i,
      /^(?:more\s+)?casual\s+(?:ones?|options?|picks?)?\s*$/i,
      /^(?:more\s+)?(?:cheap|budget|affordable)\s+(?:ones?|options?|picks?)?\s*$/i,
    ],
  },
  {
    action: ACTION.RERANK_CURRENT_SET,
    patterns: [
      /which\s+(?:one\s+)?(?:is|would\s+be)\s+best\b/i,
      /(?:best|top)\s+(?:pick|choice|option)\s+(?:for|after|if)\b/i,
      /most\s+(?:suitable|appropriate|romantic|casual|upscale)\s+(?:for|one)\b/i,
      /(?:for\s+)?(?:a\s+)?(?:romantic|anniversary|birthday|business|solo|family|group)\s+(?:dinner|meal|night|trip)\b/i,
      /recommend\s+(?:the\s+)?(?:best|one)\b/i,
      /which\s+(?:should|would)\s+(?:I|we)\s+(?:go|visit|try)/i,
    ],
  },
  {
    action: ACTION.SEARCH_MORE_WITH_CONTEXT,
    patterns: [
      /\b(?:find|show|get)\s+(?:me\s+)?(?:more|other|different|alternative|similar)\b/i,
      /\bmore\s+(?:options?|choices?|results?|places?)\b/i,
      /\balternatives?\b/i,
      /\bnearby\s+alternatives?\b/i,
      /\b(?:cheaper|budget|affordable)\s+(?:options?|alternatives?|nearby|places?)\b/i,
      /\bfind\s+(?:cheaper|budget|nearby|more\s+casual|more\s+upscale)\b/i,
      /\b(?:something|anything)\s+(?:cheaper|nearby|more\s+casual)\b/i,
    ],
  },
];

const TEMPORAL_MODIFIER_RE = /\b(?:late[- ]?night|after[- ](?:dinner|hours?|midnight)|open\s+late|night\s+owl|early\s+(?:morning|bird)|midnight|2am|brunch|breakfast)\b/i;

/**
 * Parse a follow-up message into a refinement action descriptor.
 *
 * @param {string} message
 * @param {Array} currentCards - flat array of card objects (any mix of types)
 * @returns {{ type: string, modifier?: string, dayNumber?: number|null }}
 */
export function parseRefinementAction(message, currentCards) {
  const msg = (message ?? '').trim();
  if (!msg) {
    return { type: ACTION.CLARIFY_UNSUPPORTED, clarificationText: "Could you be more specific about what you're looking for?" };
  }
  if (!currentCards || currentCards.length === 0) {
    return { type: ACTION.SEARCH_MORE_WITH_CONTEXT, modifier: msg };
  }

  for (const { action, patterns } of ACTION_MATCHERS) {
    if (patterns.some((re) => re.test(msg))) {
      const result = { type: action };
      if (action === ACTION.FILTER_CURRENT_SET) {
        result.modifier = extractFilterModifier(msg);
      } else if (action === ACTION.REMOVE_FROM_CURRENT_SET) {
        result.modifier = extractRemoveModifier(msg);
      } else if (action === ACTION.RERANK_CURRENT_SET) {
        result.modifier = msg;
        result.isTemporal = TEMPORAL_MODIFIER_RE.test(msg);
      } else if (action === ACTION.ADD_SELECTED_TO_DAY) {
        result.dayNumber = extractDayNumber(msg);
      } else if (action === ACTION.SEARCH_MORE_WITH_CONTEXT) {
        result.modifier = msg;
      }
      return result;
    }
  }

  // Unrecognized but sounds like a search intent → try SEARCH_MORE
  if (/\b(?:find|show|get|want|need|looking for|suggest)\b/i.test(msg)) {
    return { type: ACTION.SEARCH_MORE_WITH_CONTEXT, modifier: msg };
  }

  return {
    type: ACTION.CLARIFY_UNSUPPORTED,
    clarificationText: "I'm not sure what you'd like. You can filter the current options, compare them, remove specific types, or ask me to find more.",
  };
}

function extractFilterModifier(msg) {
  const m = msg.match(
    /(?:show\s+(?:me\s+)?(?:only|just)|only|just|filter\s+(?:to|by|for)|narrow\s+(?:down\s+)?to)\s+(?:the\s+)?(?:more\s+)?([a-z][\w\s-]*?)(?:\s+(?:ones?|options?|picks?|places?|restaurants?|bars?))?\s*$/i
  );
  if (m?.[1]) return m[1].trim();
  const m2 = msg.match(/^(?:more\s+)?([a-z][\w\s-]+?)(?:\s+(?:ones?|options?|picks?|places?))?\s*$/i);
  if (m2?.[1]) return m2[1].trim();
  return msg;
}

function extractRemoveModifier(msg) {
  const m = msg.match(
    /^(?:remove|hide|exclude|drop|get\s+rid\s+of)\s+(?:the\s+|all\s+|any\s+)?([a-z][\w\s-]+?)(?:\s+(?:places?|restaurants?|bars?|options?|ones?))?\s*$/i
  );
  if (m?.[1]) return m[1].trim();
  const m2 = msg.match(/^(?:no|without)\s+(?:more\s+)?([a-z][\w\s-]+?)(?:\s+(?:places?|restaurants?|bars?|options?|ones?))?\s*$/i);
  if (m2?.[1]) return m2[1].trim();
  return msg;
}

function extractDayNumber(msg) {
  const m = msg.match(/day\s+(\d+)/i);
  return m ? parseInt(m[1], 10) : null;
}

// ---------------------------------------------------------------------------
// Card field helpers — only visible, safe fields
// ---------------------------------------------------------------------------

function cardSearchText(place) {
  const wp = place?.supportingDetails?.whyPick;
  const wpText = typeof wp === 'string' ? wp : (wp?.text ?? '');
  return [
    place?.name ?? '',
    place?.display?.displayCategory ?? '',
    place?.display?.displayWhy ?? '',
    place?.cuisine ?? '',
    place?.category ?? '',
    place?.supportingDetails?.categoryLabel ?? '',
    wpText,
    place?.primaryReason ?? '',
    place?.neighborhood ?? '',
    place?.address ?? '',
    ...(place?.tags ?? []),
  ].join(' ').toLowerCase();
}

function getNumericRating(place) {
  const r = place?.rating ?? place?.supportingDetails?.rating;
  if (typeof r === 'number') return r;
  if (typeof r === 'string') return parseFloat(r) || 0;
  return 0;
}

function getReviewCount(place) {
  const c = place?.reviewCount ?? place?.supportingDetails?.reviewCount;
  if (typeof c === 'number') return c;
  if (typeof c === 'string') return parseInt(c, 10) || 0;
  return 0;
}

function sortByRating(places) {
  return [...places].sort((a, b) => {
    const ratingDiff = getNumericRating(b) - getNumericRating(a);
    if (ratingDiff !== 0) return ratingDiff;
    return getReviewCount(b) - getReviewCount(a);
  });
}

// ---------------------------------------------------------------------------
// Public helpers
// ---------------------------------------------------------------------------

/**
 * Select the best card from a flat array of { kind, place } objects.
 * "Best" = highest rating, then highest review count.
 */
export function selectBestCard(cardsWithKind) {
  if (!cardsWithKind?.length) return null;
  return [...cardsWithKind].sort((a, b) => {
    const ratingDiff = getNumericRating(b.place) - getNumericRating(a.place);
    if (ratingDiff !== 0) return ratingDiff;
    return getReviewCount(b.place) - getReviewCount(a.place);
  })[0];
}

/**
 * Build a comparison summary for the first two cards.
 * Returns { text, comparisonCards } using only visible, safe fields.
 */
export function compareCards(cardsWithKind) {
  const cards = (cardsWithKind ?? []).slice(0, 2);
  if (cards.length === 0) return { text: 'No cards to compare.', comparisonCards: null };
  if (cards.length === 1) {
    return { text: `Only one option available: ${cards[0].place.name}.`, comparisonCards: null };
  }

  const summaries = cards.map(({ place, kind }) => {
    const rating = getNumericRating(place);
    const reviewCount = getReviewCount(place);
    const metaParts = [];
    if (rating > 0) {
      metaParts.push(reviewCount > 0
        ? `★ ${rating.toFixed(1)} (${reviewCount.toLocaleString()} reviews)`
        : `★ ${rating.toFixed(1)}`);
    }
    const area = place?.neighborhood ?? place?.address ?? place?.supportingDetails?.address ?? '';
    if (area) metaParts.push(area);

    const category = place?.display?.displayCategory
      ?? place?.cuisine
      ?? place?.category
      ?? place?.supportingDetails?.categoryLabel
      ?? (kind === 'hotel' ? 'Hotel' : kind === 'attraction' ? 'Attraction' : 'Restaurant');

    const rawNote = (place?.display?.displayWhyValidated === true && place?.display?.displayWhy)
      ? place.display.displayWhy
      : (typeof place?.supportingDetails?.whyPick === 'string'
        ? place.supportingDetails.whyPick
        : (place?.supportingDetails?.whyPick?.text ?? ''));
    const note = rawNote ? rawNote.slice(0, 130) + (rawNote.length > 130 ? '…' : '') : '';

    return { name: place.name, category, meta: metaParts.join(' · '), note };
  });

  const [a, b] = summaries;
  return {
    text: `Here's a quick comparison of ${a.name} vs. ${b.name}.`,
    comparisonCards: summaries,
  };
}

/**
 * Returns true when a follow-up query looks like a fresh category/destination
 * search rather than a refinement of the current card set.
 *
 * Criteria (generic / action-oriented, no venue keyword patching):
 *  1. Explicit destination qualifier: "in Tokyo", "near Paris", "around Kyoto"
 *  2. "for Day N" concierge starter: "Attractions for Day 2"
 *  3. Neighborhood/area comparison: "Compare neighborhoods", "Compare areas"
 *
 * If this returns false but the action parser returns CLARIFY_UNSUPPORTED, the
 * caller (handleUserInput) falls through to sendQuery as a safety net.
 */
export function looksLikeFreshSearch(query) {
  const q = (query ?? '').trim();
  // Destination qualifier: "in Tokyo", "near Paris", "around Osaka"
  if (/\b(?:in|near|around)\s+[A-Z][a-z]/.test(q)) return true;
  // "for Day X" pattern: "Attractions for Day 2", "Restaurants for Day 3"
  if (/\bfor\s+day\s+\d+\b/i.test(q)) return true;
  // Neighborhood/area comparison (not a card-set comparison)
  if (/^compare\s+(?:neighborhoods?|areas?|districts?)\b/i.test(q)) return true;
  return false;
}

/**
 * Build a contextual search query for SEARCH_MORE_WITH_CONTEXT.
 * Combines the original query context with the user's new modifier.
 */
export function buildContextualSearchQuery(originalQuery, followUpMessage, context) {
  const dest = (context?.destination ?? '').trim();
  const base = originalQuery || dest;
  const msg = (followUpMessage ?? '').trim();

  // If the message already names the destination, use it as-is.
  if (dest && msg.toLowerCase().includes(dest.toLowerCase())) return msg;
  if (base) return `${base} — ${msg}`;
  return msg;
}

// ---------------------------------------------------------------------------
// Apply refinement to the latest card message
// ---------------------------------------------------------------------------

/**
 * Apply an action to the latest card message and return a synthetic assistant
 * Message to append. Returns null for ADD and SEARCH_MORE (caller handles
 * those) and for FILTER when no cards match (fall through to SEARCH_MORE).
 *
 * @param {{ type: string, modifier?: string, isTemporal?: boolean }} action
 * @param {{ restaurants?: any[], attractions?: any[], hotels?: any[] }} latestCardMsg
 * @returns {object|null} Synthetic assistant message or null
 */
export function applyRefinementToMessage(action, latestCardMsg) {
  const restaurants = latestCardMsg?.restaurants ?? [];
  const attractions = latestCardMsg?.attractions ?? [];
  const hotels = latestCardMsg?.hotels ?? [];

  if (action.type === ACTION.FILTER_CURRENT_SET) {
    const modLower = (action.modifier ?? '').toLowerCase();
    if (!modLower) return null;

    const filtered = {
      restaurants: restaurants.filter((p) => cardSearchText(p).includes(modLower)),
      attractions: attractions.filter((p) => cardSearchText(p).includes(modLower)),
      hotels: hotels.filter((p) => cardSearchText(p).includes(modLower)),
    };
    const total = filtered.restaurants.length + filtered.attractions.length + filtered.hotels.length;
    if (total === 0) return null; // caller falls through to SEARCH_MORE

    const label = total === 1 ? '1 pick' : `${total} picks`;
    return _refinementMsg(
      `Filtered to ${label} matching "${action.modifier}" from this set.`,
      ACTION.FILTER_CURRENT_SET,
      filtered,
    );
  }

  if (action.type === ACTION.REMOVE_FROM_CURRENT_SET) {
    const modLower = (action.modifier ?? '').toLowerCase();
    if (!modLower) return null;

    function shouldRemove(place) {
      return [
        place?.name ?? '',
        place?.display?.displayCategory ?? '',
        place?.cuisine ?? '',
        place?.category ?? '',
        place?.supportingDetails?.categoryLabel ?? '',
        ...(place?.tags ?? []),
      ].join(' ').toLowerCase().includes(modLower);
    }

    const result = {
      restaurants: restaurants.filter((p) => !shouldRemove(p)),
      attractions: attractions.filter((p) => !shouldRemove(p)),
      hotels: hotels.filter((p) => !shouldRemove(p)),
    };
    const removed =
      (restaurants.length + attractions.length + hotels.length) -
      (result.restaurants.length + result.attractions.length + result.hotels.length);
    const remaining = result.restaurants.length + result.attractions.length + result.hotels.length;

    const text = removed === 0
      ? `No cards matching "${action.modifier}" were found in the current set.`
      : `Removed ${removed} card${removed > 1 ? 's' : ''} matching "${action.modifier}". ${remaining} pick${remaining !== 1 ? 's' : ''} remaining.`;

    return _refinementMsg(text, ACTION.REMOVE_FROM_CURRENT_SET, result);
  }

  if (action.type === ACTION.RERANK_CURRENT_SET) {
    // If temporal modifier but no hours data visible, explain and defer to search.
    if (action.isTemporal) {
      return {
        role: 'assistant',
        text: "I can't confirm late-night or after-hours suitability from these cards. Want me to search specifically for late-night options instead? Just say \"find late-night options\" and I'll search.",
        isRefinement: true,
        refinementAction: ACTION.RERANK_CURRENT_SET,
        restaurants: [],
        attractions: [],
        hotels: [],
        researchSources: [],
        areaComparisons: [],
        retrievalUsed: false,
        sourceStatus: 'none',
      };
    }

    const sorted = {
      restaurants: sortByRating(restaurants),
      attractions: sortByRating(attractions),
      hotels: sortByRating(hotels),
    };
    const total = restaurants.length + attractions.length + hotels.length;
    if (total === 0) return _refinementMsg('No cards available to rank.', ACTION.RERANK_CURRENT_SET, sorted);

    // Best card across all categories
    const allWithKind = [
      ...sorted.restaurants.map((p) => ({ kind: 'restaurant', place: p })),
      ...sorted.attractions.map((p) => ({ kind: 'attraction', place: p })),
      ...sorted.hotels.map((p) => ({ kind: 'hotel', place: p })),
    ];
    const best = selectBestCard(allWithKind);
    const bestName = best?.place?.name ?? 'the top option';

    return _refinementMsg(
      `Based on the current set, ${bestName} stands out by rating and review count. Cards reranked below.`,
      ACTION.RERANK_CURRENT_SET,
      sorted,
    );
  }

  if (action.type === ACTION.COMPARE_CURRENT_SET) {
    const allWithKind = [
      ...restaurants.map((p) => ({ kind: 'restaurant', place: p })),
      ...attractions.map((p) => ({ kind: 'attraction', place: p })),
      ...hotels.map((p) => ({ kind: 'hotel', place: p })),
    ];
    const { text, comparisonCards } = compareCards(allWithKind);
    return {
      role: 'assistant',
      text,
      isRefinement: true,
      refinementAction: ACTION.COMPARE_CURRENT_SET,
      refinementComparison: comparisonCards,
      restaurants: [],
      attractions: [],
      hotels: [],
      researchSources: [],
      areaComparisons: [],
      retrievalUsed: false,
      sourceStatus: 'none',
    };
  }

  // ADD and SEARCH_MORE handled by caller
  return null;
}

function _refinementMsg(text, refinementAction, cards) {
  return {
    role: 'assistant',
    text,
    isRefinement: true,
    refinementAction,
    restaurants: cards.restaurants ?? [],
    attractions: cards.attractions ?? [],
    hotels: cards.hotels ?? [],
    researchSources: [],
    areaComparisons: [],
    retrievalUsed: false,
    sourceStatus: 'none',
  };
}
