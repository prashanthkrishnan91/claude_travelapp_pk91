# Travel Concierge — Design Implementation Contract v1

**Last updated:** 2026-05-14  
**Status:** Active implementation reference  
**Stage:** 3.5 — Wife-Wow design system foundation Phase 0

---

## 1. Purpose and authority

This contract exists because Claude must not infer exact implementation rules from an 87-page PDF.

- **Design Bible v1.0** (`artifacts/Travel_Concierge_Design_Bible.pdf`) remains the **taste/strategy north star**. It owns product philosophy, emotional tone, and feature direction.
- **Design Bible Addendum v1.1** (`docs/product/DESIGN_BIBLE_ADDENDUM_V1_1.md`) sharpens emotional architecture and UX grammar (private atelier, constraint-first feasibility, concierge search grammar, trip-as-story model).
- **This contract** is the **exact implementation reference** for future design PRs. It owns token values, primitive contracts, visual rules, phase sequencing, forbidden patterns, and self-audit checklists.

**Golden rule:** If the contract is incomplete or conflicts with the Design Bible/Addendum, future work must **stop and ask**. Do not infer, do not improvise, do not patch around missing detail. The contract is the source of truth for "what exact values go in code."

---

## 2. Current Stage 3.5 status

- **Stage 3** is functionally exited (2026-05-14).
- **Stage 3.5 Phase 0** is **MERGED** (2026-05-14).
  - `frontend/src/app/globals.css` — design tokens (`:root` CSS vars, `--ds-*`)
  - `frontend/tailwind.config.ts` — semantic color `@theme` wiring
  - `frontend/src/components/ui/Card.tsx` — Card primitive shell (7 named slots)
  - `frontend/src/components/ui/TrustStrip.tsx` — TrustStrip primitive (verified/sourceCount/confidence/caveat)
  - `docs/ai/UI_BASELINE.md` — token/primitive inventory and adoption status
  - `docs/ai/HANDOFF.md` — current state summary

- **No surfaces have adopted** the Card primitive or new tokens yet. Existing UI is visually unchanged.
- **Next work** is Phase 1 (bounded first visible adoption on one surface, no behavior changes).

---

## 3. Exact color tokens

All values are Design Bible v1.0 §4.1 exact. These are the **only** official colors; do not substitute, interpolate, or infer alternates.

| CSS Variable | Token Name | Hex Value | Use |
|---|---|---|---|
| `--ds-midnight-ink` | Midnight Ink | `#0B1320` | App shell, Explore, AI Concierge (dark surfaces) |
| `--ds-onyx-velvet` | Onyx Velvet | `#0F1A2C` | Card bg (dark tone) |
| `--ds-carbon-mist` | Carbon Mist | `#1A2538` | Secondary dark surface |
| `--ds-pen-stroke` | Pen Stroke | `#22324A` | Card border (dark tone) |
| `--ds-warm-paper` | Warm Paper | `#FAF7F0` | Saved Ideas, trip artefacts (warm paper mode) |
| `--ds-bone` | Bone | `#F1ECE0` | Paper surface accent |
| `--ds-linen` | Linen | `#E6DECB` | Paper surface tertiary |
| `--ds-hairline` | Hairline | `#D9D2C2` | Divider/border (paper tone) |
| `--ds-sandstone-gold` | Sandstone Gold | `#E0B888` | Primary accent (luxury) |
| `--ds-ember-brass` | Ember Brass | `#C5944D` | Muted accent, secondary gold |
| `--ds-pearl-cream` | Pearl Cream | `#F2EBDD` | Primary text (light) |
| `--ds-cream` | Cream | `#E8E2D4` | Secondary text (light) |
| `--ds-mist` | Mist | `#9AA4B2` | Tertiary text, disabled state |
| `--ds-verified-sage` | Verified Sage | `#88A899` | Trust verified, high confidence |
| `--ds-caution-amber` | Caution Amber | `#E8B26B` | Medium confidence, weak evidence, warnings |
| `--ds-whisper-coral` | Whisper Coral | `#D88478` | Error, caveat, low trust |
| `--ds-slate` | Slate | `#4A5568` | Neutral gray (secondary UI) |
| `--ds-ink-paper` | Ink Paper | `#1F2530` | Inverse text (on light backgrounds) |

**Rules:**
- Do not substitute colors in new components when a `ds-*` token exists.
- Do not infer alternate "luxury palettes" or adjusted saturation variants.
- All new design primitives must use `ds-*` CSS variables, not raw hex or Tailwind utility classes.

---

## 4. Semantic aliases (reference tokens above)

Semantic aliases allow components to use role-based names instead of literal color names. All aliases are **frozen**; new aliases require a contract amendment.

| Alias | References | Use |
|---|---|---|
| `--ds-text-primary` | `--ds-pearl-cream` | Primary body text on dark surfaces |
| `--ds-text-secondary` | `--ds-cream` | Secondary body text, meta |
| `--ds-text-tertiary` | `--ds-mist` | Tertiary text, hints, disabled |
| `--ds-text-inverse` | `--ds-ink-paper` | Text on light/warm backgrounds |
| `--ds-accent` | `--ds-sandstone-gold` | Primary interactive element, gold button, primary CTA |
| `--ds-accent-muted` | `--ds-ember-brass` | Secondary interactive, muted gold |
| `--ds-accent-subtle` | `rgba(224, 184, 136, 0.12)` | Sandstone Gold alpha 12%, background tint only |
| `--ds-trust-verified` | `--ds-verified-sage` | Verified status, high confidence, trust signals |
| `--ds-trust-partial` | `--ds-caution-amber` | Medium confidence, partial trust |
| `--ds-trust-caveat` | `rgba(232, 178, 107, 0.15)` | Caution Amber alpha 15%, caveat background |
| `--ds-caution` | `--ds-caution-amber` | Warning, medium risk, medium confidence |
| `--ds-warning` | `--ds-whisper-coral` | Error, high risk, low trust |
| `--ds-parchment` | `--ds-bone` | Paper surface warm accent |
| `--ds-aged-paper` | `--ds-linen` | Paper surface tertiary |

**Rules:**
- New design components should prefer semantic aliases over named palette tokens for color styling.
- Semantic aliases may be used in component CSS; named palette tokens are allowed only in token definitions and `@theme` wiring.
- Do not invent new semantic aliases without a contract amendment.

---

## 5. Exact spacing scale

All values are Design Bible v1.0 §4.2 exact. This is the **only** spacing system for Phase 1+.

| Token | Value (rem) | Value (px) | Use |
|---|---|---|---|
| `--ds-space-1` | 0.25 | 4 | Sub-icon padding, tight gaps |
| `--ds-space-2` | 0.5 | 8 | Chip padding, inline gap, small spacing |
| `--ds-space-3` | 0.75 | 12 | Metadata gap, compact spacing |
| `--ds-space-4` | 1 | 16 | Compact card padding, standard gap |
| `--ds-space-5` | 1.25 | 20 | Default card padding, standard spacing |
| `--ds-space-6` | 1.5 | 24 | Section gap, heading-to-content gap |
| `--ds-space-8` | 2 | 32 | Large section gap, feature spacing |
| `--ds-space-10` | 2.5 | 40 | Explore card-to-card gap, card grid spacing |
| `--ds-space-12` | 3 | 48 | Hero block padding, major spacing |
| `--ds-space-16` | 4 | 64 | Desktop page-edge gutter, full-width margin |

**Rules:**
- New components must use `--ds-space-*` tokens for padding, margin, and gaps.
- Do not use Tailwind spacing utilities (e.g., `gap-3`, `p-4`) in new design-system components; use CSS vars instead.
- Spacing should be additive: e.g., card padding + gap = `--ds-space-5` padding + `--ds-space-4` internal gaps.

---

## 6. Exact typography roles

All size/line-height pairs are Design Bible v1.0 §4.3 exact. Two font families only: **display serif + humanist sans**. Mono role is reserved for identity keys and debug output only.

| Role | Size | Line-height | Weight | Tracking | Use |
|---|---|---|---|---|---|
| Display XL | 64px | 68px | 700 | −0.03em | Cover hero, landing hero |
| Display L | 44px | 50px | 700 | −0.025em | Page hero, section title |
| Display M | 32px | 38px | 700 | −0.02em | Card detail title |
| Display S | 24px | 30px | 600 | −0.015em | Section title in card, subheader |
| Body L | 18px | 28px | 400 | — | Lead paragraph, intro text |
| Body | 15px | 24px | 400 | — | Default body text, card description |
| Body S | 13px | 20px | 400 | — | Card metadata, list row, caption |
| Caption | 12px | 16px | 400 | — | Trust marks, timestamps, small text |
| Overline | 10px | 14px | 600 | +0.1em | Section labels, uppercase only |
| Mono | 12px | 16px | 400 | — | Identity keys, debug only |
| Quote | 18px | 28px | 400 (italic) | — | Concierge reasoning quotes |

**Rules:**
- Two font families only: **display serif + humanist sans**. No third family without a contract amendment and Phase gate.
- Overline text is always uppercase; use `text-transform: uppercase` or render uppercase text.
- Quote role is italic only; always paired with attribution/source.
- New fonts may not be hosted without explicit Phase scope.
- UI must not introduce style variants not listed in this table.

---

## 7. Motion and reduced-motion contract

All durations are Design Bible v1.0 §4.5 exact. Motion explains; it never decorates.

**Exact durations:**
- **Fast:** `--ds-duration-fast` = `120ms` (loading states, hover feedback, micro-interactions)
- **Standard/default:** `--ds-duration-standard` = `200ms` (state changes, fade-in, slide)
- **Spatial:** `320ms` when explicitly scoped and part of a feature contract (elaborate reveal, multi-step transition)
- **Absolutely forbidden:** anything >400ms except cinematic auth-to-app transition (if explicitly scoped in a feature contract)

**Principles:**
- Motion explains (reveals hierarchy, indicates state change, guides attention).
- Motion never delays first content or card paint.
- Follow-up queries / cache hits should render immediately; do not fake intelligence with artificial loading delays.
- No motion may apply opacity, transform, or filter changes that extend perceived load time.

**Reduced-motion requirement (Design Bible v1.0 §4.13):**
- Global `@media (prefers-reduced-motion: reduce)` rule must apply to **every** visual PR.
- Reduced-motion mode: remove all `transform`, `filter`, and `scale` animations; cap opacity transitions to fade only.
- No reduced-motion mode bypass; it applies to all users who set the OS preference.

**Forbidden motion patterns (Design Bible v1.0 §3.8, §12):**
- Parallax scrolling
- Glow pulses or pulsing shadows
- Animated gradient meshes
- Bouncy springs or overshoot/elastic easing
- Confetti, fireworks, or success bursts
- Autoplay video backgrounds
- Scroll-jacking or scroll-triggered animations
- Typewriter effects or character-by-character typing
- Animated counting / number tickers

---

## 8. Elevation, borders, glass, texture, and image rules

**Hairline geometry:**
- Borders / dividers: 0.4–1px (use CSS `border: 1px` and rely on subpixel rendering or alpha for visual weight).
- No drop-shadows on light/paper surfaces; elevation via luminance lift and hairline only.
- Dark mode elevation: comes from ink ladder (`--ds-midnight-ink`, `--ds-onyx-velvet`, etc.), not shadow puff.

**Dark surface elevation (Midnight Ink backgrounds):**
- Use shadow stack: `--ds-elevation-1` through `--ds-elevation-4` (defined in `globals.css`).
- Elevation via inset highlight + shadow blur (Design Bible v1.0 §4.6).

**Paper mode elevation:**
- Use hairline borders and luminance (lighter background color), not heavy shadows.
- Example: card on Warm Paper uses `border-ds-hairline` + higher value background to convey lift.

**Glass:**
- Glass (backdrop-filter blur) allowed **only** for landing/hero AI composer.
- No glass on standard card shells, navigation, or content surfaces.

**Grain / texture:**
- 1% noise grain allowed **only** on landing/login screens.
- Forbidden elsewhere; the texture should not be visible on product surfaces.

**Image rules:**
- No stock photos. If no verified source photo exists, render typeset layout instead.
- Card content (text, trust strip, identity) must paint **before** images (lazy-load images or use `content-visibility`).
- Image aspect ratios (Design Bible v1.0 §5.6):
  - Verified place hero: 4:5 (portrait, primary hero)
  - Explore cover/detail: 3:2 (landscape, editorial)
  - Saved thumbnail: 1:1 (square, collection grid)
  - Forbidden: generic 16:9 (except for controlled video, explicitly scoped)

**Border radius (Design Bible v1.0 §4.7):**
- Chip: `4px` (`rounded-sm` in Tailwind)
- Card: `8px` (`rounded-lg`)
- Drawer: `12px` (`rounded-2xl`)
- Modal: `16px` (explicit, `rounded-3xl`)
- Avoid 24px+ unless explicitly approved in feature contract

---

## 9. Tonal surface rules

**Two tonal systems only:**

1. **Dark mode (Midnight Ink):**
   - Shell, Explore, AI Concierge, active intelligence surfaces.
   - Cards use Onyx Velvet (`--ds-onyx-velvet`) background + Pen Stroke border.
   - Text: Pearl Cream primary, Cream secondary, Mist tertiary.

2. **Paper mode (Warm Paper):**
   - Saved Ideas, trip artefacts, profile/shareable/scrapbook-like surfaces.
   - Cards use Warm Paper (`--ds-warm-paper`) background + Hairline border.
   - Text: Ink Paper (inverse), all text roles dark on light.

**Rules:**
- Never mix both tonal systems casually on one screen.
- Surface mode changes happen **at route/page-template level**, not on random individual cards.
- Saved Ideas / paper mode should feel like a **scrapbook**, not a generic list.
- Do not use "light mode" or "dark mode" UI toggles; surface mode is determined by route and data context, not user preference.

---

## 10. Brand and emotional architecture

Durable principles (Design Bible v1.0 §3, Design Bible Addendum v1.1):

- **Boutique.** Small, curated, editorial attention to detail.
- **Concierge.** Composed, knowing, honest. Never chatty, never performative.
- **Private atelier.** Feels like a member-club concierge room, not a productivity dashboard. Remembered, not fabricated.
- **Honest.** Evidence is the brand. Show constraints beautifully, not hidden.
- **Quiet.** Beauty without logic and logic without beauty are equally bad. Both must be visible.
- **Generous.** The card is the hero; layout should serve the card, not compete with it.
- **Luxury-for-less.** Known luxury (verified, researched), not cheap imitation.

**Product must never feel like:**
- OTA aggregator or Booking.com clone
- SaaS dashboard or project-management tool
- Crypto landing page or Web3 hype
- Generic chatbot or AI assistant
- Gamified app (streaks, XP, badges)
- Stock-photo magazine or inspirational Pinterest clone

**No fake urgency. No childish gamification. No generic "AI" tone.**

---

## 11. Card primitive contract

**Based on merged `Card.tsx` (2026-05-14).**

### Root props:
- `tone: "dark" | "paper"` (default: `"dark"`)
- `as: "article" | "div" | "li" | "section"` (default: `"div"`)
- Standard HTML attributes (className, id, data-*, etc.)

### Seven named slots:

1. **Card.Identity** — Name, category, rating, primary identity of place/offer. Always visible.
2. **Card.Trust** — Trust strip, source count, verification badge, confidence. Use `<TrustStrip />` primitive.
3. **Card.Media** — Hero image or map preview. Lazy-load; content paints first.
4. **Card.Why** — "Why pick this" explanation (AI reasoning or editorial note). Renders backend verbatim; UI never paraphrases.
5. **Card.Meta** — Tags, price tier, distance chips, secondary metadata. Omit missing fields; never render placeholder text.
6. **Card.Actions** — Primary and secondary CTAs (buttons, link-outs).
7. **Card.Caveat** — Weak-evidence note, data-freshness caveat, disclaimer.

### Rules:
- Card root has **no business logic, no data fetching, no animation by default**.
- Slots are composable; create variants by composing slots, not by creating bespoke card shells.
- Missing fields are **omitted entirely**, never shown as `N/A`, `TBD`, `—`, or placeholder text.
- Do not adopt the primitive outside the specifically scoped Phase/surface.
- **Do not export variants from the primitive.** Variants live in the consuming surface layer; the primitive stays token-owned.

### Forbidden in Card:
- Color styling outside `ds-*` tokens.
- Inline animation or GSAP library.
- Search/API calls or data fetching.
- Form inputs.
- Third-party embeds.
- Multiple variants stacked in one file.

### Usage pattern:
```jsx
<Card tone="dark" as="article" data-id={id}>
  <Card.Identity>
    <h3>Place Name</h3>
    <p>Category</p>
  </Card.Identity>
  <Card.Trust>
    <TrustStrip verified={true} sourceCount={3} />
  </Card.Trust>
  <Card.Media>
    <img src={photo} alt="Place" />
  </Card.Media>
  <Card.Why>Why this fits...</Card.Why>
  <Card.Meta>
    {/* tags, chips */}
  </Card.Meta>
  <Card.Actions>
    {/* buttons */}
  </Card.Actions>
</Card>
```

---

## 12. Card system adoption rules

**Preserve Design Bible §8 (Card Design System).**

**One Card primitive; variants compose slots.**

Future variant patterns (Phase 1+):
- Verified place card
- AI Concierge result card
- Explore card (attractions, restaurants, hotels)
- Saved idea card
- Itinerary item card
- Area / neighborhood card
- Hotel card (discovery-only until provider integration)
- Flight card (round-trip + one-way, fully canonical)
- Activity card

**Rules:**
- Trust strip is **always present** where trust applies and **never compressed to an icon**.
- "Why this fits" (Card.Why) renders backend reason **verbatim**; UI must not paraphrase or rewrite it.
- Compact cards may hide why behind "show why" button / disclosure; expanded/detail cards promote the why-quote.
- Missing fields are **omitted**, never shown as `N/A`, `TBD`, `—`, or placeholder text.

**Forbidden card patterns (Design Bible v1.0 §8):**
- Price strikethrough or "was $X now $Y" formatting
- Urgency badges ("Only 2 left", "Book now")
- Multi-color category badges
- Fake "recommended for you" label without data backing
- AI-edited or rewritten labels without source attribution
- Fake personalization or invented social proof
- Missing metadata rendered as skeleton/spinner (lazy-load only if needed; omit if unknown)

---

## 13. TrustStrip contract

**Based on merged `TrustStrip.tsx` (2026-05-14).**

### Props:
- `verified?: boolean` — When true, renders "Verified by Google". Must be explicitly set; never inferred from data.
- `sourceCount?: number` — Number of distinct sources. Omitted when unknown.
- `confidence?: TrustConfidence` — "high" | "medium" | "low". Omitted when unknown.
- `caveat?: string` — Short caveat text shown when evidence is weak/incomplete.
- `className?: string` — Additional CSS classes.

### Rules:
- **"Verified by Google"** renders only when `verified=true`. Never infer verified status from place type, rating, or other heuristics.
- Source counts start at 1 and are tappable/expandable when source list exists.
- Confidence levels are **high / medium / low only**. No percentages (e.g., "92% confidence" forbidden).
- Caveats are **first-class sentences**, not abbreviations or acronyms.
- Weak evidence is shown **honestly**, not hidden or downplayed.

**No fake trust signals.**

---

## 14. Evidence and trust UX contract

**Preserve Design Bible §9 (Trust + Evidence).**

**Four-rung evidence ladder:**

1. Verified place + 3+ independent sources → highest confidence
2. Verified place + 2 sources → high confidence
3. Verified place + weak/unverified constraint → medium confidence
4. Place not verified (no Google Place ID or OPERATIONAL status) → not addable, editorial/research only

**"Verified by Google"** means:
- Stable Google Place ID confirmed.
- OPERATIONAL status only (no CLOSED, OPENING_SOON, etc.).
- Rendered via `<TrustStrip verified={true} />` only when backend confirms verification.

**Source counts:**
- Start at 1.
- Tappable/expandable when a source list is available to show.
- Never fabricated; only render when backend supplies the list.

**Confidence levels:**
- **High:** Verified place + 3+ sources OR multiple high-quality sources.
- **Medium:** Verified place + 2 sources OR strong partial verification.
- **Low:** Weak sources, unverified constraint, single source.

**Caveats:**
- First-class sentences, e.g., "Data is 3 days old." or "Opening hours not confirmed."
- Render via `<TrustStrip caveat={text} />`.
- Never omit or hide weak evidence.

**Forbidden unsupported claims (Design Bible v1.0 §9.10):**
- Awards without source (Michelin, James Beard, Bib Gourmand, etc.)
- "Stunning views" without photo evidence
- "Romantic ambiance" without sourced description
- Estimated distance / walking time without backend computation
- Neighborhood claim without geographic data
- Price band / cost estimate without menu/provider data
- Opening hours / "open now" without current data
- "#1 of 487" ranking without data backing
- "92% confidence" — only high / medium / low

**Missing metadata:**
- Render only when backend provides the data.
- When absent, omit the field entirely (no "—", no "TBD", no spinner/skeleton unless actively loading).

---

## 15. AI Concierge flagship UX contract

**Preserve Design Bible §6 (AI Concierge).**

### Card-first hierarchy, not chat-bubble hierarchy.

**Desktop layout:**
- Left: Conversation rail (past queries, follow-ups)
- Center: Result canvas (cards grid or list)
- Bottom/right: Sticky composer (textarea + chips + memory pill)

**Mobile layout:**
- 90vh bottom sheet (results + composer, dismiss to dismiss)
- Composer always visible (not hidden until user scrolls)

### Composer contract:
- Typeset textarea (not generic chat input).
- Placeholder: "Where would you like to go?"
- No chat bubbles, no avatar, no "thinking" dots.
- Follow-up chips derive from parsed intent/cards (do not invent).
- Memory pill summarizes context and is editable (edit resets conversation, not incremental).

### Result display:
- No preamble ("Here are some options for you" forbidden).
- Result count is editorial: "Six places that fit your mood."
- "Why these six?" is a small explanation (1–2 sentences), not a chain-of-thought panel.
- Cards shown in order of relevance (highest confidence first).
- Compare top 3 aligns evidence rows for quick comparison.
- Weak evidence is shown honestly (not hidden).

### Prompt chips:
- **Refine** — Add constraints or change mood.
- **Compare** — Compare top results side-by-side.
- **More options** — Request additional results.
- No invented chips; parse intent from user message to populate chips.

### Forbidden (Design Bible v1.0 §6.7):
- Model name, token count, system prompt.
- Raw search query or `debug` mode.
- Place IDs or backend identity keys.
- Chain-of-thought reasoning panels or internal API responses.
- Avatar or "AI assistant" branding.
- Typing dots or "thinking" animation.
- Chatbot tropes ("How can I help?" greeting).
- Typewriter effect or character-by-character typing.
- Multi-turn memory without explicit user edit/reset.
- Fake personalization ("Based on your saved places").

---

## 16. Page-by-page implementation direction

**Durable rules from Design Bible §7 (Page-by-Page Implementation).**

### Landing
- Cinematic still hero (no video yet; video hero deferred to later phase).
- One primary CTA ("Plan a trip", "Get started").
- Proof strip (sample itineraries, trip count, social proof).
- Glass only for hero AI composer exploration; no glass elsewhere.
- No session/backend changes.

### Auth (login/signup)
- Calm single-column form (email + password).
- Still hero (cinematic background, not video).
- No complex multi-step or OTP flows unless explicitly scoped.
- No backend/session changes; Form validates client-side first.

### Dashboard
- Editorial reading room (greeting + trip covers).
- Greeting reads like concierge ("Good evening, Prashanth. Three trips on your shelf."), not stats header.
- Trip covers feel like cover of a personal travel volume.
- AI launch pill (one-tap to Concierge).
- Forbidden: KPI dashboard feel, progress rings, completion %, streaks, badges.

### Trip detail
- Reading-room layout (cover header, editorial spacing, flow).
- Tab or section structure (Overview, Itinerary, Notes, etc.).
- Right rail summary (when scoped; not default).
- AI drawer one keystroke away.
- Day sections read like chapters: chapter header + evidence-grounded cards + hairline separation.
- Forbidden: data model changes, new time-of-day blocks, in-card booking unless explicitly scoped.

### Explore
- Magazine-section feel (editorial curation, discreet tabs, hierarchy).
- Tabs/metadata placement unobtrusive (not chrome-heavy).
- Map/list parity only when explicitly scoped.
- List default on mobile.
- No provider/search behavior change (Explore uses canonical vertical search, not AI Concierge).

### Saved Ideas
- Paper/scrapbook tone (Warm Paper background, personal collection feel).
- Not a generic list view; feels like a kept scrapbook.
- No storage model changes, no new fields.

### Itinerary
- Editorial timeline (days as chapters, hairline travel-time hints).
- Day sections: typeset chapter header + cards + hairline.
- Hairline travel-time hints (distance, walking time, driving time) only when backend supplies data.
- Forbidden: new time-of-day blocks, completion %, progress rings unless explicitly scoped.

### Cards / detail panels
- Half-bleed panel on desktop (slide-out or modal).
- 90vh sheet on mobile.
- Forbidden: in-card booking actions unless explicitly scoped.

### Profile / settings
- Paper sections (Warm Paper tone, restraint).
- No unsupported fields (bio, image, preferences without backend support).

### Mobile nav / sidebar
- Thumb-friendly bottom rail (44px+ hit area).
- Concierge pill (one-tap launch).
- Forbidden: route changes, new nav structure, unsupported screens.

---

## 17. Concierge Search Bar grammar

**From Design Bible Addendum v1.1 §2, preserve shared grammar across surfaces.**

Shared search grammar (Explore, trip creation, saved-trip creation, hotels, flights, future surfaces):

1. **Destination** — City autocomplete with verified city selection.
2. **Dates** — Calendar picker (check-in / check-out or start/end).
3. **Guests / passengers** — Dropdown or stepper (adults, children, infants).
4. **Intent** — Text field or chips (mood, type of trip, interests).
5. **Primary CTA** — One button (Search, Create Trip, etc.).

**Premium components:**
- City autocomplete (not browser input, verified selection only).
- Date picker (calendar UI, accessible, not text input).
- Passenger selector (stepper, not text; validated adult count).
- Intent chips (predefined or freeform, clear semantics).

All components must:
- Follow `--ds-space-*` and `--ds-type-*` tokens.
- Pass `@media (prefers-reduced-motion: reduce)` safety (44px+ hit area, focus rings).
- Not extend perceived latency (no fake loading delays).

**Constraint: beauty must not slow task completion.** A more beautiful selector that adds taps, modal hops, or latency fails this addendum (Design Bible Addendum v1.1 §2).

**This is grammar guidance for future phases.** It does not authorize Stage 3.5 to build search components, change routes, or alter search/provider behavior.

---

## 18. Constraint-first planning / feasibility UX

**From Design Bible Addendum v1.1 §5, preserve honest constraint visualization.**

**Principle: "Beauty should expose feasibility, not hide it."**

Feasibility constraints render beautifully **only when backend data supports them**:
- Distance from hotel (when available)
- Arrival time vs. first-night plans (when timing data exists)
- Restaurant timing / service window (when sourced)
- Route / travel-time hints (hairline, caption-grade, Design Bible v1.0 §5.6 spec)
- Weather-sensitive alternatives (when forecast data available)
- Saved-place clustering by neighborhood (when geographic data computed)

**Rules:**
- Render as typeset, caption-grade, hairline treatments (never alarmist badges).
- Never invent feasibility claims or estimates.
- When data is absent, the field is **omitted entirely** (no "—", no estimate, no client-side guess).
- Bound by Design Bible v1.0 §9.10 (no unsupported claims) and §9.9 (missing details).

**This section adds no new backend data or computation.** It is presentation grammar for data the product already exposes.

---

## 19. Addictive personalization guardrails

**Preserve Design Bible v1.0 §10 (Addictive Personalization Guardrails).**

**Allowed later only when data/evidence supports it:**
- Evolving trip covers (based on destination mood/aesthetic data)
- Destination atmosphere recommendations (based on real weather/event data)
- Personal travel style memory (based on saved trips and preferences, opt-in)
- Luxury-for-less rail (based on price-vs-quality scoring)
- Worth-the-splurge moments (based on sourced luxury recommendations)
- Rainy-day swaps (based on weather forecast + saved places)
- Tonight's edit (based on real-time event data)
- Neighborhood mood maps (based on geographic + real-time data)
- Saved-card collections (grouped by user-created or inferred interest)
- Trip completion rituals (celebration or memory-save, not gamification)
- Subtle progress hints (not streaks, not XP, not badges)
- Conversational next-best-actions (parsed intent, not invented)

**Forbidden:**
- Streaks, XP levels, badges, achievement unlocks
- Limited-time prompts ("Finish your trip by Thursday")
- Unlock modals or paywalls disguised as progression
- Confetti, success bursts, or celebration animations
- Unrelated push notifications or email spam
- Auto-defaults without explicit user action

**Status:** These are **future ideas only** and do not authorize Phase 1 implementation unless specifically scoped in a Phase 2+ feature contract.

---

## 20. Stage 3.5 phase roadmap and sequencing

**Preserve Design Bible roadmap direction (§13.1, §12 Stop Conditions).**

### Phase roadmap:

| Phase | Scope | Deliverable | Status |
|---|---|---|---|
| 0 | Tokens + Card + TrustStrip | CSS vars, primitives, baseline doc | ✅ MERGED 2026-05-14 |
| 1 | First visible adoption (one surface) | Adopt Card + tokens on Explore, Saved, or Trip list | Next |
| 2 | AI Concierge flagship redesign | Full Card-first composer + results canvas + prompt chips | Queued |
| 3 | Card system redesign | Variant adoption across all place-like surfaces | Queued |
| 4 | Explore redesign | Magazine section feel, editorial hierarchy | Queued |
| 5 | Itinerary/timeline redesign | Reading-room layout, chapter structure, travel-time hints | Queued |
| 6 | Landing/auth redesign | Hero contract, proof strip, form simplification | Queued |
| 7 | Mobile refinement | Bottom-rail nav, 90vh sheets, thumb-friendly spacing | Queued |
| 8 | Motion polish | Reduced-motion verified, micro-interactions, reveal choreography | Queued |
| 9 | Final cohesion pass | Cross-surface consistency, token coverage, edge cases | Queued |

### Sequencing principles:
- **Foundation first:** Tokens, primitives, baseline (Phase 0) ✅
- **Flagship before breadth:** AI Concierge (Phase 2) before card variant breadth (Phase 3)
- **Cards before surfaces:** Card primitive (Phase 0) before Explore redesign (Phase 4)
- **Landing last:** Landing redesign (Phase 6) after core surfaces are solid
- **Motion last:** Motion polish (Phase 8) after visual layout complete
- **No jumping:** Do not jump to broad redesign; each phase builds on prior foundation

---

## 21. Hard forbidden patterns

**Cumulative list from Design Bible v1.0 §12 (Guardrails) and Addendum v1.1 (sharpening).**

### Colors:
- No raw hex in new components when a `ds-*` token exists.
- No legacy palette classes in new design primitives (no `emerald-*`, `amber-*`, `cream-*`, `dark-*`, `white/` in Card or TrustStrip).

### Effects:
- No neon glows or glow pulses.
- No animated gradient meshes.
- No confetti, fireworks, or success bursts.
- No parallax scrolling.
- No scroll-jacking.

### AI / Concierge:
- No chatbot avatar.
- No typing dots or "thinking" animation.
- No preamble ("Here are some options for you").
- No typewriter effect or character-by-character typing.
- No invented follow-up chips.
- No model name, token count, or debug output in UI.

### Trust / evidence:
- No fake urgency badges ("Only 2 left", "Book now").
- No invented trust signals (no inferred "Verified" status).
- No percentages ("92% confidence").
- No unsupported awards (Michelin without source).
- No missing fields rendered as `N/A`, `TBD`, `—`, or placeholder text.

### Personalization:
- No streaks, XP, levels, badges, or achievement unlocks.
- No confetti or success-burst animations.
- No fake personalization ("Based on your travel style" without data).
- No auto-defaults without explicit user action.
- No unrelated push notifications or email spam.

### Scope:
- No surface adoption outside the named Phase.
- No backend/API/provider/search/Tavily changes in design PRs.
- No SQL in design PRs.
- No new fonts unless explicitly scoped in feature contract.
- No new animation library unless explicitly scoped.
- No broad all-in-one redesign PR (scope and split Phase-by-Phase).

---

## 22. Stop conditions

**Preserve Design Bible v1.0 §12 (Stop Conditions).**

Stop immediately and escalate if any of the following occur:

1. **PR exceeds scoped file count** → Stop / split phase.
2. **Needs backend/API/schema changes** → Stop / split phase (mark for Phase 2+).
3. **Test fails** → Stop / diagnose root cause; never delete or skip test.
4. **Concierge returns 0 cards after UI PR** → Stop / rollback immediately.
5. **FCP regresses on landing or trip detail** → Stop / rollback immediately.
6. **Reduced-motion not tested / safety unverified** → Stop; test before opening PR.
7. **Behavior change not explicitly in scope** → Stop; roll back or explicitly scope.
8. **Color token not in contract** → Stop / ask for amendment.
9. **Changed files exceed target set** → Stop / split or scope clearly.
10. **New font, animation library, or broad architecture change** → Stop / escalate to feature contract.

---

## 23. Required self-audit checks for future design PRs

**Include before opening any design PR.**

- [ ] Changed files **exactly match** PR scope and prompt.
- [ ] **No backend, Supabase, provider, search, API, Tavily, flight, hotel, or saved-trip files** changed.
- [ ] **No raw hex** in new components when `ds-*` token exists.
- [ ] **No legacy color classes** (`emerald-*`, `amber-*`, `cream-*`, `dark-*`, `white/`) in new primitives.
- [ ] **Card.tsx used** where place-like cards are shown (not custom shells).
- [ ] **TrustStrip.tsx used** where trust signals apply (not custom badges).
- [ ] **No visible behavior changes** outside explicit scope.
- [ ] **Reduced-motion tested** and respected (no transform/filter when preference=reduce).
- [ ] **"Verified by Google" only when `verified=true`** (never inferred).
- [ ] **Missing metadata omitted**, not rendered as `N/A` or placeholder.
- [ ] **No invented claims** (awards, distance, neighborhood, price, hours without backend data).
- [ ] **No unsupported awards** (Michelin, James Beard, Bib Gourmand without sourced data).
- [ ] **Spacing uses `--ds-space-*` tokens**, not Tailwind utilities.
- [ ] **Typography uses proper role tokens**, not mixed font sizes.
- [ ] **Smoke path tested:**
  - [ ] Open dashboard
  - [ ] Open a trip detail
  - [ ] Ask concierge for a place query
  - [ ] Save / add a card
  - [ ] Verify no card-count regression
  - [ ] Verify addability and Card behavior unchanged

---

## 24. Future prompt checklist

Include when writing a design-focused implementation prompt:

- [ ] Which Design Bible section is being implemented?
- [ ] Which Addendum section is relevant (if any)?
- [ ] Which contract section is binding?
- [ ] Exact allowed files (design components, CSS, docs, tests).
- [ ] Exact forbidden files (backend, SQL, routes, provider, API, Tavily).
- [ ] Which behavior contracts are preserved (Card slots, TrustStrip props, spacing scale, colors)?
- [ ] Visual acceptance checks (reduced-motion, theme toggle, mobile/desktop, light/dark).
- [ ] Reduced-motion verification checklist.
- [ ] Grep checks for forbidden patterns (raw hex, legacy classes, unsupported claims).
- [ ] Manual smoke path (dashboard → trip → concierge → save).
- [ ] Test tier (see `docs/ai/TEST_ROUTING.md`; design PRs typically Tier 1 or 2).

---

## 25. Prompt usage snippet

**For future design-focused prompts, cite this contract and the Design Bible/Addendum:**

> Read `docs/product/DESIGN_IMPLEMENTATION_CONTRACT.md` as the exact implementation source for token values, primitive contracts, visual rules, phase scope, forbidden patterns, and self-audit checks. Do not infer implementation rules from the PDF.
>
> Also read the Design Bible v1.0 (`artifacts/Travel_Concierge_Design_Bible.pdf`) and Design Bible Addendum v1.1 (`docs/product/DESIGN_BIBLE_ADDENDUM_V1_1.md`) for taste, strategy, and emotional-architecture guidance.
>
> **Golden rule:** If the contract is incomplete or conflicts with the Design Bible/Addendum, stop and ask. Do not improvise or patch around missing detail.

---

## Acceptance and governance

This contract is **live** as of 2026-05-14 and replaces ad-hoc inference from the Design Bible PDF.

- **Authority hierarchy:** Contract (exact implementation values) > Addendum (emotional architecture) > Design Bible (strategy/taste).
- **Amendments:** Any change to color tokens, spacing scale, typography roles, primitives, or phase scope requires a contract amendment PR.
- **Versioning:** This is v1. Future amendments will be v1.1, v1.2, etc., with change log noted in this file.
- **Enforcement:** Every design PR must audit against this contract before opening.

---

## Change log

- **2026-05-14:** v1 — Initial contract. Consolidates Phase 0 shipped work (tokens, Card, TrustStrip) + full implementation guidance + forbidden patterns + self-audit checks + prompt snippet.
