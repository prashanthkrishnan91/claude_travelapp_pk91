/**
 * Stage 3.5 Phase 8F — Explore / Discover Curated Search Lounge
 *
 * Contract tests verifying:
 * 1. ExploreShell lounge structure and editorial identity
 * 2. Premium search instrument framing
 * 3. Vertical tabs and search behavior preserved
 * 4. Semantic buttons/links only
 * 5. No card-level click-only navigation
 * 6. No fake/mock/sample visible data or hardcoded city prompts
 * 7. No backend/provider imports in Explore components
 * 8. No AI Concierge routing from default hotel/attraction Explore flows
 * 9. Preserved restaurant/hotel/attraction/flight actions
 * 10. Preserved Google Maps/source/compare affordances
 * 11. No raw rgba( or raw hex in touched Explore surfaces
 * 12. Mobile-safe layout cues
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

// ── Source files ──────────────────────────────────────────────────────────────

const exploreShell = readFileSync(
  new URL('../src/components/explore/ExploreShell.tsx', import.meta.url), 'utf8');

const restaurantFlow = readFileSync(
  new URL('../src/components/explore/RestaurantExploreFlow.tsx', import.meta.url), 'utf8');

const hotelFlow = readFileSync(
  new URL('../src/components/explore/HotelExploreFlow.tsx', import.meta.url), 'utf8');

const attractionFlow = readFileSync(
  new URL('../src/components/explore/AttractionExploreFlow.tsx', import.meta.url), 'utf8');

const flightFlow = readFileSync(
  new URL('../src/components/explore/FlightExploreFlow.tsx', import.meta.url), 'utf8');

const resultActionSheet = readFileSync(
  new URL('../src/components/explore/ResultActionSheet.tsx', import.meta.url), 'utf8');

// ── A. ExploreShell — Lounge Structure ───────────────────────────────────────

test('ExploreShell has explore-lounge-header testid', () => {
  assert.match(exploreShell, /data-testid="explore-lounge-header"/);
});

test('ExploreShell has Overline "Curated Discovery" label in lounge header', () => {
  assert.match(exploreShell, /Curated Discovery/);
});

test('ExploreShell renders "Discover" as the editorial page heading', () => {
  assert.match(exploreShell, /<h1[^>]*>Discover<\/h1>/);
});

test('ExploreShell retains explore-home testid for backward compatibility', () => {
  assert.match(exploreShell, /data-testid="explore-home"/);
});

test('ExploreShell has "no trip required" copy for discovery-lounge framing', () => {
  assert.match(exploreShell, /no trip required/i);
});

test('ExploreShell active state has explore-lounge-breadcrumb testid', () => {
  assert.match(exploreShell, /data-testid="explore-lounge-breadcrumb"/);
});

test('ExploreShell active state has explore-instrument-header testid on section header', () => {
  assert.match(exploreShell, /data-testid="explore-instrument-header"/);
});

test('ExploreShell active section uses bg-ds-onyx (ink-ladder elevation)', () => {
  assert.match(exploreShell, /bg-ds-onyx/);
});

test('ExploreShell active section uses border-ds-pen-stroke hairline', () => {
  assert.match(exploreShell, /border-ds-pen-stroke/);
});

test('ExploreShell active section uses elevation or boutique shadow treatment', () => {
  assert.ok(
    /shadow-\[var\(--ds-elevation-2\)\]/.test(exploreShell) || exploreShell.includes("boutique-instrument"),
    "ExploreShell must apply elevation shadow or boutique-instrument to active section"
  );
});

test('ExploreShell has VERTICAL_OVERLINES constant with all four verticals', () => {
  assert.match(exploreShell, /VERTICAL_OVERLINES/);
  assert.match(exploreShell, /flights:/);
  assert.match(exploreShell, /hotels:/);
  assert.match(exploreShell, /restaurants:/);
  assert.match(exploreShell, /attractions:/);
});

test('ExploreShell instrument header Overline uses text-ds-accent color', () => {
  assert.match(exploreShell, /text-ds-accent/);
});

// ── B. Search Instrument Visual Quality ──────────────────────────────────────

test('VerticalCard has focus-visible outline with ds-accent ring', () => {
  assert.match(exploreShell, /focus-visible:outline-ds-accent/);
});

test('VerticalCard uses card-lift for discovery-tray hover', () => {
  assert.match(exploreShell, /card-lift/);
});

test('VerticalCard icon uses var(--ds-accent-subtle) background (no legacy colors)', () => {
  assert.match(exploreShell, /var\(--ds-accent-subtle\)/);
});

test('VerticalCard icon uses text-ds-accent (uniform sandstone-gold)', () => {
  assert.match(exploreShell, /text-ds-accent/);
});

test('VerticalCard Overline label uses tracking-[0.1em]', () => {
  assert.match(exploreShell, /tracking-\[0\.1em\]/);
});

test('VerticalCard Overline label uses text-ds-text-tertiary', () => {
  assert.match(exploreShell, /text-ds-text-tertiary/);
});

test('Instrument header Overline uses tracking-[0.1em] (Design Bible §4.3 exact)', () => {
  const overlineCount = (exploreShell.match(/tracking-\[0\.1em\]/g) || []).length;
  assert.ok(overlineCount >= 2, 'Expected at least 2 tracking-[0.1em] usages (card + section header)');
});

test('ExploreShell back button uses text-ds-text-tertiary (not legacy cream color)', () => {
  assert.match(exploreShell, /text-ds-text-tertiary hover:text-ds-text/);
});

test('ExploreShell breadcrumb heading uses text-ds-text', () => {
  assert.match(exploreShell, /className="text-sm font-semibold text-ds-text"/);
});

test('ExploreShell instrument section has rounded-xl border style', () => {
  assert.match(exploreShell, /rounded-xl border border-ds-pen-stroke bg-ds-onyx/);
});

// ── C. No Legacy Colors in Touched Surfaces ───────────────────────────────────

test('ExploreShell has no legacy text-cream-* colors', () => {
  assert.doesNotMatch(exploreShell, /text-cream-\d+/);
});

test('ExploreShell has no legacy bg-sky-* colors', () => {
  assert.doesNotMatch(exploreShell, /bg-sky-\d+/);
});

test('ExploreShell has no legacy text-sky-* colors', () => {
  assert.doesNotMatch(exploreShell, /text-sky-\d+/);
});

test('ExploreShell has no legacy bg-violet-* colors', () => {
  assert.doesNotMatch(exploreShell, /bg-violet-\d+/);
});

test('ExploreShell has no legacy text-violet-* colors', () => {
  assert.doesNotMatch(exploreShell, /text-violet-\d+/);
});

test('ExploreShell has no legacy bg-amber-* colors', () => {
  assert.doesNotMatch(exploreShell, /bg-amber-\d+/);
});

test('ExploreShell has no legacy text-amber-* colors', () => {
  assert.doesNotMatch(exploreShell, /text-amber-\d+/);
});

test('ExploreShell has no legacy bg-emerald-* colors', () => {
  assert.doesNotMatch(exploreShell, /bg-emerald-\d+/);
});

test('ExploreShell has no legacy text-emerald-* colors', () => {
  assert.doesNotMatch(exploreShell, /text-emerald-\d+/);
});

test('RestaurantExploreFlow has no legacy text-cream-* colors', () => {
  assert.doesNotMatch(restaurantFlow, /text-cream-\d+/);
});

test('HotelExploreFlow has no legacy text-cream-* colors', () => {
  assert.doesNotMatch(hotelFlow, /text-cream-\d+/);
});

test('AttractionExploreFlow has no legacy text-cream-* colors', () => {
  assert.doesNotMatch(attractionFlow, /text-cream-\d+/);
});

test('ExploreShell has no raw rgba( inline colors', () => {
  assert.doesNotMatch(exploreShell, /rgba\s*\(/);
});

test('ExploreShell has no raw hex colors in className strings', () => {
  // Raw hex in className would look like className="... #1A2538 ..." — forbidden
  assert.doesNotMatch(exploreShell, /className="[^"]*#[0-9a-fA-F]{3,6}/);
});

// ── D. Preserved Vertical Behavior ───────────────────────────────────────────

test('ExploreShell renders all four vertical flows', () => {
  assert.match(exploreShell, /RestaurantExploreFlow/);
  assert.match(exploreShell, /AttractionExploreFlow/);
  assert.match(exploreShell, /HotelExploreFlow/);
  assert.match(exploreShell, /FlightExploreFlow/);
});

test('ExploreShell manages vertical selection with useState', () => {
  assert.match(exploreShell, /const \[active, setActive\] = useState/);
});

test('ExploreShell shows only one vertical at a time (state-driven)', () => {
  assert.match(exploreShell, /if \(active\)/);
});

test('RestaurantExploreFlow uses ResultActionSheet on each result card', () => {
  assert.match(restaurantFlow, /ResultActionSheet/);
  assert.match(restaurantFlow, /<ResultActionSheet/);
});

test('HotelExploreFlow uses ResultActionSheet on each result card', () => {
  assert.match(hotelFlow, /ResultActionSheet/);
  assert.match(hotelFlow, /<ResultActionSheet/);
});

test('AttractionExploreFlow uses ResultActionSheet on each result card', () => {
  assert.match(attractionFlow, /ResultActionSheet/);
  assert.match(attractionFlow, /<ResultActionSheet/);
});

test('FlightExploreFlow uses ResultActionSheet for save action', () => {
  assert.match(flightFlow, /ResultActionSheet/);
});

test('HotelExploreFlow preserves Google Hotels compare CTA (hotel-compare-cta)', () => {
  assert.match(hotelFlow, /data-testid="hotel-compare-cta"/);
  assert.match(hotelFlow, /Compare prices/);
});

test('RestaurantExploreFlow preserves Google Maps link (googleMapsUri)', () => {
  assert.match(restaurantFlow, /googleMapsUri/);
  assert.match(restaurantFlow, /View.*on Google Maps/);
});

test('HotelExploreFlow preserves Google Maps link (googleMapsUri)', () => {
  assert.match(hotelFlow, /googleMapsUri/);
  assert.match(hotelFlow, /View.*on Google Maps/);
});

test('AttractionExploreFlow preserves Google Maps link (googleMapsUri)', () => {
  assert.match(attractionFlow, /googleMapsUri/);
  assert.match(attractionFlow, /View.*on Google Maps/);
});

test('ResultActionSheet save/unsave buttons preserved (save-action-btn)', () => {
  assert.match(resultActionSheet, /data-testid="save-action-btn"/);
  assert.match(resultActionSheet, /Save/);
  assert.match(resultActionSheet, /handleSave/);
  assert.match(resultActionSheet, /handleUnsave/);
});

test('ResultActionSheet more-actions-toggle preserved', () => {
  assert.match(resultActionSheet, /data-testid="more-actions-toggle"/);
});

test('ResultActionSheet manage-in-saved link preserved', () => {
  assert.match(resultActionSheet, /data-testid="manage-in-saved-link"/);
  assert.match(resultActionSheet, /\/saved/);
});

// ── E. No AI Concierge Routing from Default Explore Flows ────────────────────

test('HotelExploreFlow does not call callConciergeSearch', () => {
  assert.doesNotMatch(hotelFlow, /callConciergeSearch/);
});

test('HotelExploreFlow does not route to AI Concierge endpoint', () => {
  assert.doesNotMatch(hotelFlow, /\/ai\/concierge/);
});

test('AttractionExploreFlow does not call callConciergeSearch', () => {
  assert.doesNotMatch(attractionFlow, /callConciergeSearch/);
});

test('AttractionExploreFlow does not route to AI Concierge endpoint', () => {
  assert.doesNotMatch(attractionFlow, /\/ai\/concierge/);
});

test('HotelExploreFlow uses canonical searchHotelsExplore (Google Places backend)', () => {
  assert.match(hotelFlow, /searchHotelsExplore/);
});

test('AttractionExploreFlow uses canonical searchAttractionsExplore (Google Places backend)', () => {
  assert.match(attractionFlow, /searchAttractionsExplore/);
});

test('RestaurantExploreFlow uses canonical searchRestaurants', () => {
  assert.match(restaurantFlow, /searchRestaurants/);
});

test('FlightExploreFlow uses canonical searchFlightsExplore', () => {
  assert.match(flightFlow, /searchFlightsExplore/);
});

// ── F. No Fake / Mock / Sample Data ──────────────────────────────────────────

test('ExploreShell has no hardcoded city prompt chips or destination examples in prompts', () => {
  // The explore shell must not render hardcoded destination chips to search
  assert.doesNotMatch(exploreShell, /Paris|London|Tokyo|Barcelona|New York/);
});

test('ExploreShell has no mock/sample/hardcoded data references', () => {
  assert.doesNotMatch(exploreShell, /mock/i);
  assert.doesNotMatch(exploreShell, /sample/i);
  assert.doesNotMatch(exploreShell, /hardcoded/i);
  assert.doesNotMatch(exploreShell, /placeholder.*luxury/i);
});

test('RestaurantExploreFlow has no mock/sample data', () => {
  assert.doesNotMatch(restaurantFlow, /source === "mock"/);
  assert.doesNotMatch(restaurantFlow, /\bsampleRestaurant/);
});

test('HotelExploreFlow has no mock/sample data', () => {
  assert.doesNotMatch(hotelFlow, /source === "mock"/);
  assert.doesNotMatch(hotelFlow, /\bsampleHotel/);
});

test('AttractionExploreFlow has no mock/sample data', () => {
  assert.doesNotMatch(attractionFlow, /source === "mock"/);
  assert.doesNotMatch(attractionFlow, /\bsampleAttraction/);
});

test('RestaurantExploreFlow placeholder has no hardcoded city examples', () => {
  assert.doesNotMatch(restaurantFlow, /placeholder="[^"]*(?:Paris|Marais|Barcelona|Tokyo|Shinjuku|New York|London)/);
});

test('HotelExploreFlow placeholder has no hardcoded city examples', () => {
  assert.doesNotMatch(hotelFlow, /placeholder="[^"]*(?:Paris|Marais|Barcelona|Tokyo|Shinjuku|New York|London)/);
});

test('AttractionExploreFlow placeholder has no hardcoded city examples', () => {
  assert.doesNotMatch(attractionFlow, /placeholder="[^"]*(?:Paris|Marais|Barcelona|Tokyo|Shinjuku|New York|London)/);
});

test('RestaurantExploreFlow destination placeholder is generic', () => {
  assert.match(restaurantFlow, /placeholder="City or area"/);
});

test('HotelExploreFlow destination placeholder is generic', () => {
  assert.match(hotelFlow, /placeholder="Destination city"/);
});

test('AttractionExploreFlow destination placeholder is generic', () => {
  assert.match(attractionFlow, /placeholder="City or area"/);
});

// ── G. Accessibility and Semantic Actions ─────────────────────────────────────

test('VerticalCard is a semantic <button> element (not div onClick)', () => {
  // VerticalCard renders a <button> with onClick, not a <div onClick>
  assert.match(exploreShell, /<button\s[^>]*onClick=\{onSelect\}/);
  assert.doesNotMatch(exploreShell, /<div[^>]*onClick=\{onSelect\}/);
});

test('VerticalCard has aria-label for accessible name', () => {
  assert.match(exploreShell, /aria-label=\{`Explore \$\{meta\.label\}`\}/);
});

test('Back button is semantic <button> (not <a> or <div>)', () => {
  // Button and aria-label may be on different lines in JSX — check both exist
  assert.match(exploreShell, /<button/);
  assert.match(exploreShell, /aria-label="Back to Explore"/);
  assert.doesNotMatch(exploreShell, /<a[^>]*aria-label="Back to Explore"/);
});

test('Back button preserves aria-label="Back to Explore"', () => {
  assert.match(exploreShell, /aria-label="Back to Explore"/);
});

test('Icon containers have aria-hidden="true"', () => {
  assert.match(exploreShell, /aria-hidden="true"/);
});

test('ExploreShell active section has aria-label for search context', () => {
  assert.match(exploreShell, /aria-label=\{`\$\{VERTICAL_TITLES\[active\]\} search`\}/);
});

test('No card-level click-only navigation — result card article roots have no onClick', () => {
  // RestaurantCard uses Card as="article" — should not have onClick on root
  assert.doesNotMatch(restaurantFlow, /<Card[^>]*onClick/);
});

test('ResultActionSheet has no card-level onClick navigation', () => {
  assert.doesNotMatch(resultActionSheet, /<div[^>]*onClick=\{[^}]*router/);
});

test('ExploreShell vertical cards not wrapped with <a> tag click-only navigation', () => {
  assert.doesNotMatch(exploreShell, /href=\{`\/explore\/\$\{/);
});

// ── H. Mobile-Safe Layout ────────────────────────────────────────────────────

test('ExploreShell vertical grid has grid-cols-1 sm:grid-cols-2 (responsive)', () => {
  assert.match(exploreShell, /grid-cols-1 sm:grid-cols-2/);
});

test('ExploreShell vertical card layout is flex with items-start (mobile-safe)', () => {
  assert.match(exploreShell, /flex items-start gap-4/);
});

test('ExploreShell instrument section uses CSS var padding (mobile-responsive)', () => {
  // Updated in Phase 8I: inline padding replaced with responsive Tailwind classes p-4 sm:p-6
  assert.ok(exploreShell.includes('p-4 sm:p-6') || exploreShell.includes('padding: "var(--ds-space-6)"'),
    'ExploreShell active section must use responsive padding');
});

test('HotelExploreFlow date inputs use grid-cols-3 (structured mobile layout)', () => {
  assert.match(hotelFlow, /grid-cols-3/);
});

test('RestaurantExploreFlow search form has flex gap-3 layout', () => {
  assert.match(restaurantFlow, /flex gap-3/);
});

// ── I. Result Count Overline Typography ──────────────────────────────────────

test('RestaurantExploreFlow result count uses tracking-[0.1em] (Design Bible Overline)', () => {
  assert.match(restaurantFlow, /tracking-\[0\.1em\]/);
});

test('HotelExploreFlow result count uses tracking-[0.1em]', () => {
  assert.match(hotelFlow, /tracking-\[0\.1em\]/);
});

test('AttractionExploreFlow result count uses tracking-[0.1em]', () => {
  assert.match(attractionFlow, /tracking-\[0\.1em\]/);
});

test('RestaurantExploreFlow result count has explore-results-header testid', () => {
  assert.match(restaurantFlow, /data-testid="explore-results-header"/);
});

test('HotelExploreFlow result count has explore-results-header testid', () => {
  assert.match(hotelFlow, /data-testid="explore-results-header"/);
});

test('AttractionExploreFlow result count has explore-results-header testid', () => {
  assert.match(attractionFlow, /data-testid="explore-results-header"/);
});

// ── J. No Backend / Provider Imports ─────────────────────────────────────────

test('ExploreShell has no backend imports', () => {
  assert.doesNotMatch(exploreShell, /from "@\/backend/);
  assert.doesNotMatch(exploreShell, /from "\.\.\/\.\.\/backend/);
});

test('ExploreShell has no Supabase imports', () => {
  assert.doesNotMatch(exploreShell, /supabase/i);
});

test('RestaurantExploreFlow has no backend service imports', () => {
  assert.doesNotMatch(restaurantFlow, /from "@\/backend/);
  assert.doesNotMatch(restaurantFlow, /from "\.\.\/\.\.\/backend/);
});

test('HotelExploreFlow has no backend service imports', () => {
  assert.doesNotMatch(hotelFlow, /from "@\/backend/);
  assert.doesNotMatch(hotelFlow, /from "\.\.\/\.\.\/backend/);
});

test('AttractionExploreFlow has no backend service imports', () => {
  assert.doesNotMatch(attractionFlow, /from "@\/backend/);
  assert.doesNotMatch(attractionFlow, /from "\.\.\/\.\.\/backend/);
});

// ── K. Design Contract Audit ──────────────────────────────────────────────────

test('ExploreShell does not use legacy .card class (migrated to ds-tokens)', () => {
  // The old VerticalCard used className="card card-lift p-5..." — must be gone
  assert.doesNotMatch(exploreShell, /"card card-lift/);
  assert.doesNotMatch(exploreShell, /"card p-6"/);
});

test('ExploreShell does not reference iconBg or iconColor (removed from VerticalMeta)', () => {
  assert.doesNotMatch(exploreShell, /iconBg/);
  assert.doesNotMatch(exploreShell, /iconColor/);
});

test('ExploreShell does not have badge rendering for verticals', () => {
  // Badge was a pre-8F pattern; removed in favor of Overline category labels
  assert.doesNotMatch(exploreShell, /meta\.badge/);
});

test('ExploreShell VerticalCard icon does not use group-hover:scale (forbidden decorative motion)', () => {
  assert.doesNotMatch(exploreShell, /group-hover:scale/);
});

test('ExploreShell uses responsive padding for section (spacing token contract)', () => {
  // Updated in Phase 8I: inline var(--ds-space-6) replaced with responsive p-4 sm:p-6
  assert.ok(exploreShell.includes('p-4 sm:p-6') || exploreShell.includes('var(--ds-space-6)'),
    'ExploreShell active section must use responsive or token-based padding');
});

// ── L. Icon-Only Map Link Touch Targets (44px minimum) ───────────────────────

test('RestaurantCard Google Maps link has min-w-[44px] touch target', () => {
  assert.match(restaurantFlow, /min-w-\[44px\]/);
});

test('RestaurantCard Google Maps link has min-h-[44px] touch target', () => {
  assert.match(restaurantFlow, /min-h-\[44px\]/);
});

test('HotelCard Google Maps link has min-w-[44px] touch target', () => {
  assert.match(hotelFlow, /min-w-\[44px\]/);
});

test('HotelCard Google Maps link has min-h-[44px] touch target', () => {
  assert.match(hotelFlow, /min-h-\[44px\]/);
});

test('AttractionCard Google Maps link has min-w-[44px] touch target', () => {
  assert.match(attractionFlow, /min-w-\[44px\]/);
});

test('AttractionCard Google Maps link has min-h-[44px] touch target', () => {
  assert.match(attractionFlow, /min-h-\[44px\]/);
});

test('RestaurantCard Google Maps link preserves aria-label and href', () => {
  assert.match(restaurantFlow, /aria-label=\{`View \$\{r\.name\} on Google Maps`\}/);
  assert.match(restaurantFlow, /href=\{r\.googleMapsUri\}/);
});

test('HotelCard Google Maps link preserves aria-label and href', () => {
  assert.match(hotelFlow, /aria-label=\{`View \$\{h\.name\} on Google Maps`\}/);
  assert.match(hotelFlow, /href=\{h\.googleMapsUri\}/);
});

test('AttractionCard Google Maps link preserves aria-label and href', () => {
  assert.match(attractionFlow, /aria-label=\{`View \$\{a\.name\} on Google Maps`\}/);
  assert.match(attractionFlow, /href=\{a\.googleMapsUri\}/);
});
