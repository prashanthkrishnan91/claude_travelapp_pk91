# Private Travel Atelier — The Folio

**Stage 3.5 art-direction contract.** Durable reference for all future design-implementation prompts. When a future slice prompt says "follow the Folio direction," it means *this file*.

- **Visual concept source:** [`docs/ai/concepts/folio-concept-v1.html`](../concepts/folio-concept-v1.html) — open in a browser to see the three reference frames (desktop trip studio, mobile day folio, mobile concierge correspondence).
- **Functional stability:** the autocomplete portal behaviour and round-trip flight leg behaviour fixed in PR #431 are **not in scope** for any design slice. Visual work must not regress them; if a slice touches `CityAutocomplete`, `api.ts:addRoundTripLegToDay`, `TripBuilder.handleAddRoundTripToItinerary`, or `ItineraryItemCard` round-trip detection, treat it as out-of-bounds and stop.
- **Status:** Slice 1 shipped (folio globals, Fraunces font, Sidebar, mobile nav paper shift). Slice 2 shipped (trips/dashboard cards, trip detail panels, ItineraryDayColumn, mobile top bar, btn-marine CTAs). Slice 3 shipped (paper planning objects — ItineraryItemCard, TripBuilderForm, OptimizeTripModal, DayPlanModal). Slice 4 (legible paper + cinematic foundation) shipped — cinema-world CSS primitives added, cinema classes applied to Discover/Saved/Concierge/Home shells. Slice 4B shipped (visual world enforcement — additive cinema stacks replaced with single intentional compositions on 5 surfaces). See Sections 16–19 for resolved decisions.

---

## 1. Final direction name

**Private Travel Atelier** (public-facing intent). **The Folio** (internal codename used across docs, tokens, and PR titles). Both names refer to the same direction. Implementation prompts should use *The Folio* as the short tag.

---

## 2. Emotional target

When my wife opens the app she should feel that someone who knows her has prepared a private edition of a travel magazine for her — bound by hand, with margins for the concierge's notes, opening occasionally onto a single cinematic photograph of where she is going. The app should feel **calm, warm, tactile, and curated**; never urgent, never loud, never generic. It should make planning feel like *reading a beautiful issue*, not operating a dashboard.

---

## 3. Core thesis

The product is a **dual world**:

- A **warm paper planning world** that owns all default chrome — lists, day pages, forms, sheets, settings, navigation.
- **Rare dark cinematic panels** that punctuate the experience — the trip hero, the AI Concierge stage, image plates, the map view, the login splash.
- **Private concierge folio objects** are the atoms — every place, flight, hotel, and note is a numbered, hand-styled card with a folio serial, an italic caption, and at most one piece of brass foil.

Paper is the *default* world. Cinema is the *signature moment*. Rarity is what makes cinema feel premium.

---

## 4. Non-negotiable design rules

These are hard rules. A slice that violates them is rejected regardless of polish.

1. **Paper world is the default chrome.** App shell, navigation, lists, day pages, forms, sheets, modals, and settings are all paper.
2. **Dark cinema is punctuation, never the base shell.** Cinema appears only in: trip hero panel, AI Concierge stage, image plates inside day folios, map view, login splash. Nowhere else.
3. **Gold / brass is foil only.** Used for hairlines, dividers, wordmark, brass-bar quality markers, the concierge dot, and small editorial ornaments. **Never a button fill.** Never the primary action.
4. **Marine ink is the primary signature accent.** Primary CTAs and selection states in the paper world use marine ink. Primary CTAs in the cinema world use brass foil; secondary CTAs everywhere are ghost (hairline-only).
5. **No black/gold SaaS aesthetic.** Pure black surfaces are not allowed. The cinema base is warm dark (umber-tinted, not navy or true black).
6. **No generic Airbnb-style light app.** No pure white surfaces. Paper base is *linen*, not `#FFFFFF`. Sans-only is forbidden — the editorial serif must appear on every screen.
7. **No scrapbook clutter.** No tape edges, no faux paper tears, no rotated cards, no sticker badges, no decorative iconography. Restraint is the look.
8. **No glassmorphism chrome.** Frosted/blurred backgrounds allowed only on the AI Concierge stage and on modal scrims — never on default cards, nav bars, or sheets.
9. **No gradient text.** Headlines are solid ink or solid pearl. Period.
10. **No loud AI-startup gradients.** Purple/teal/pink full-bleed gradients are banned. The only gradient surfaces are: the cinema panel base (sunset/horizon range) and the radial atmosphere layer (warm amber whisper).
11. **No functional behaviour changes inside design slices.** Visual work does not touch search ranking, provider selection, autocomplete portal logic, round-trip leg splitting, day resolution, persistence, auth, or any backend path. If a slice prompt cannot achieve the visual goal without behaviour change, it is the wrong slice.
12. **One accent colour per surface.** A given card carries either marine ink or brass foil — not both.
13. **No emoji in product UI.** No exclamation marks in copy. Concierge voice is lowercase, present-tense, past-conditional ("I've held the 8 pm — would you like a quieter table?").

---

## 5. Signature primitives

These nine atoms carry the identity. Every screen should use at least two.

1. **Issue masthead** — the trip title rendered as a magazine cover line: `Issue No. 07 · Spring 2026 · Folio AML` with a brass hairline rule and an italic serif title.
2. **Mapline** — a horizontal city sequence (`Naples · → · Positano · → · Ravello`) in small caps with brass pin glyphs. Appears wherever a trip is referenced.
3. **Folio serial** — a three-letter trip code + index (`AML · 03 · 02`) appearing as quiet metadata on every card.
4. **Large serif day numeral** — Day 03 rendered as a large italic serif numeral (~64–96px), the visual anchor of every day page.
5. **Italic editorial caption** — one italic serif line under every object's title ("The light at sundown turns the village to honey."). Always one line. Never headline.
6. **Framed cinema plate** — a warm-dark panel with vignette, ambient brass glow, and a paper margin around it. Maximum one per day folio in mobile, one to two in desktop.
7. **Paper sheet / folio card** — linen-toned card with hairline border (never solid stroke), soft warm shadow, optional folio serial at top, optional italic caption.
8. **Concierge correspondence** — concierge messages in italic serif inside a brass-hairlined panel; user messages in marine-ink solid; suggestions arrive as a paper sheet rising from below, not as inline bubbles.
9. **Restrained brass hairline** — a 1px brass rule, used to separate masthead from body, to underline editorial section eyebrows, to mark the top edge of a cinema plate, and to frame the brass-bar quality markers. Never used as a card border.

---

## 6. Surface system

Three card archetypes, no more. Every visible surface must be one of these or a clearly named variant.

- **Paper card** (default in paper world)
  - Fill: bone / linen
  - Border: 1px hairline (token), never a solid heavy border
  - Radius: 10–14px
  - Shadow: long, low-opacity, slightly warm
  - Top-of-card metadata: folio serial in small caps
  - At most one piece of brass foil (a brass-bar, a corner mark, or the serial)

- **Velvet (cinema) card** (default in cinema world)
  - Fill: warm dark (carbon / velvet)
  - Border: brass hairline at ~10% opacity
  - Inner top-edge highlight: pearl at ~5% opacity
  - Elevation: deeper shadow with subtle warm glow
  - Text: cream / pearl

- **Framed cinema panel** (the signature moment)
  - A velvet panel placed *inside* a paper page, with a 24–32px paper margin and a brass hairline frame
  - Contains: editorial italic quote, brass-foil eyebrow, optional brass-bar foot, vignette, ambient warmth
  - Used for: trip hero, day plate, concierge stage, gallery, map seam

**Smaller atoms:**

- **Sheets / modals** — always paper, even inside cinema-world routes. Sheets slide up from below with a brass hairline at the top edge and a small grab handle in hairline tone.
- **Chips** — pill-shaped, hairline border, ink text in paper / pearl text in cinema. No filled chips.
- **Buttons**
  - Primary in paper = marine ink fill + cream text
  - Primary in cinema = brass foil fill + ink-paper text
  - Secondary everywhere = ghost (transparent fill, 1px border in marine or brass, small caps label)
  - No pill-shaped CTAs. Subtle 4–6px radius. No drop shadow on buttons.
- **Dividers** — never a solid 1px line. Either a brass hairline (24–60px wide, centred) or an editorial `· · ·` separator.
- **Inputs** — flat linen field with hairline border, no inner shadow. On focus, the hairline becomes brass. Label is small caps above the field, not floating.

---

## 7. Typography direction

A two-typeface system. Adding a third typeface requires explicit approval.

- **Editorial serif** — used for: display headlines, day numerals, italic captions, concierge messages, issue masthead title, quote callouts. Variable, optical-size-aware. **Candidate: Fraunces** (variable, has the travel-magazine character of GT Super without the licence). Italic is used aggressively — italic serif is the product's "voice."
- **UI sans** — used for: body, UI labels, navigation, buttons, metadata, small caps eyebrows, time chips. **Stay with Inter** (already in use). One weight family.
- **Where serif is required:** every screen must contain at least one editorial serif element. A page that is all sans is wrong.
- **Where plain UI sans must remain:** form inputs, button labels, navigation, error messages, dense metadata rows, tabular data. Serif must not appear inside interactive controls.
- **Readability rules:** body text remains ≥14px on mobile, ≥15px on desktop. Italic serif must not be used for body paragraphs longer than two lines — italics fatigue at length. Small caps must use real small-caps via OpenType features (not CSS `text-transform: uppercase` shrunk).

---

## 8. Color system

Roles only. Final hex assignment and token naming will be ratified in Slice 1 against the existing `--ds-*` tokens in `frontend/src/app/globals.css`. The Folio concept HTML uses the proposed hexes; treat them as intended tones, not final tokens.

**Paper world:**
- **Linen** — default app background (warm off-white, ~`#F4EEDF`). Never `#FFFFFF`.
- **Bone** — paper card fill, slightly lighter than linen (~`#FAF5E7`).
- **Deep linen** — recessed paper surfaces, sheet headers (~`#E9DFC7`).
- **Ink** — primary text (~`#1E1A14`, warm near-black, no blue tint).
- **Ink-soft** — secondary text.
- **Ink-mist** — tertiary text and metadata.
- **Ink-ghost** — disabled / faint metadata.
- **Hairline** — 1px paper-world borders (~`#CFC4A8`).
- **Hairline-soft** — dashed sub-rules between timeline items.

**Cinema world:**
- **Velvet base** — outermost cinema fill (warm dark, ~`#0E0B07`). Never `#000000`.
- **Velvet** — primary cinema surfaces (~`#16110A`).
- **Carbon** — recessed cinema surfaces (~`#221A11`).
- **Pearl** — primary cinema text (~`#F2E7CC`).
- **Cream** — italic concierge serif body in cinema (~`#EDE2C5`).
- **Pearl-soft** — cinema metadata / tertiary text.

**Foil and accent:**
- **Brass foil** — hairlines, dividers, brass-bar, eyebrow rules, the wordmark dot (~`#B6904A` highlight, `#8C6E32` deep).
- **Marine ink** — primary signature accent in the paper world (~`#1F4256`). Owns primary CTAs and active states.
- **Marine soft** — focus rings and hover states for marine controls.

**Ambient layers:**
- **Warm ambient** — radial glow used on cinema panels (~`rgba(184, 130, 60, 0.10)`).
- **Vignette** — corner darkening on cinema panels (~`rgba(0, 0, 0, 0.55)`).

**Existing token mapping note:** several `--ds-*` tokens already exist (sandstone-gold, ember-brass, atelier-base, warm-paper, bone, linen, ink-paper). Slice 1 must remap usage, not invent new names — `--ds-sandstone-gold` becomes the brass-foil role; a new `--ds-marine-ink` is introduced as the paper-world primary; `--ds-warm-paper` and `--ds-bone` become the dominant default surfaces.

---

## 9. Motion philosophy

Atmospheric, not kinetic. Motion is mood, not feedback for its own sake.

- **Slow ambient drift** — the radial atmosphere layer on cinema panels drifts ~3% across the canvas over 30–60s with a soft ease. The eye picks it up subconsciously; the app reads as *alive*. Below 600px width, drift is disabled to save battery and render budget.
- **Paper-to-cinema reveal** — when a cinema plate enters view, it fades in over 250–350ms with a 4–6px rise. No scale, no rotation, no skew.
- **Editorial transitions** — page transitions are slow fades (250–350ms ease-out). No spring physics. No bounce. No springy modals.
- **Concierge messages** — arrive with a 400ms fade + small rise. Typing indicator is three brass-foil dots pulsing at 1.4s intervals.
- **Hover / press** — paper cards lift 1px and gain a softer shadow over 300ms. No scale > 1.02. No tilt.
- **Strict `prefers-reduced-motion`** — disables ambient drift entirely; keeps transitions at half duration; replaces concierge fade-in with instant render. Motion must degrade gracefully.
- **No decorative motion that hurts mobile performance** — no parallax photography in the shell, no looping background video, no Lottie animations as eye candy, no animation loops faster than 8s in foreground.

---

## 10. Desktop rules

- **Two-column editorial spread.** Left page is paper (the writing — day folio, day numeral, timeline, notes). Right page is the framed cinema panel (the seeing — hero, gallery, map) and a places-in-rotation grid below.
- **Generous gutters** — 56–96px outer margins, 48–64px column gap. The product should breathe.
- **Max content width** ~1280px; centred. Wider screens get more outer margin, not wider columns.
- **Top bar is silent.** Serif wordmark on the left, four nav words centred (`Trips · Library · Notes · Concierge`), `⌘K` chip + avatar on the right. No tab bar, no breadcrumbs in the top bar, no notification badges.
- **Ambient drift on by default.** Reduced-motion respects.
- **Quick actions via command palette.** `⌘K` opens a quiet command field that lives on linen with a brass hairline. No floating "+" button anywhere on desktop.
- **Concierge dock** — floating velvet pill at the bottom-right of the trip studio, with a pulsing brass dot and one italic line of correspondence. Click expands to the concierge stage.

---

## 11. Mobile rules

- **Paper-first chrome.** Status bar background, top bar, scroll surface, bottom tab bar, sheets, and modals are all paper.
- **Single column**, 24px outer margins.
- **Cinema panels appear as rare full-bleed plates** punctuating the scroll — at most one per day folio. They have a 24px paper margin top/bottom so the paper world is always visibly around them.
- **One-thumb actions.** Primary CTAs at the bottom of sheets, never the top. Tap targets ≥44pt.
- **Bottom tab bar** — 4 items max (`Folio · Map · Concierge · Library`), small caps labels, brass hairline above. Active tab uses ink + brass-deep glyph; inactive uses ink-mist + ink-mist glyph.
- **Sheets always slide up from the bottom**, paper, with a small hairline grab handle. Never a full-screen dark modal for routine actions.
- **No bottom nav on the AI Concierge full-screen stage** (the only screen where cinema is the chrome).
- **Ambient drift disabled below 600px width.** Static atmosphere only.
- **The day numeral is the largest element on the page**, not a banner or a hero image.

---

## 12. AI Concierge rules

The concierge is **correspondence, not a chatbot**.

- **Stage:** cinema world (full-screen on mobile, framed panel on desktop). The only place in the product where cinema is the default chrome.
- **Voice:** lowercase first-person, past-conditional, restrained. "I've held the 8 pm — would you like a quieter table?" Never "Sure!" Never "Here are some great suggestions!" Never an exclamation mark.
- **Message styling:**
  - Concierge messages: italic editorial serif (Fraunces italic), inside a brass-hairlined warm-glow panel, with an `CONCIERGE` small-caps label above the first message.
  - User messages: solid marine-ink panel, sans body, right-aligned.
- **Suggestions are not inline bubbles.** When the concierge offers options (restaurants, hotels, hikes, drivers), they arrive as a **paper sheet rising from below** containing 2–4 folio cards — each with a folio serial, an italic caption, and a quiet "Add" ghost button. The sheet is the only paper surface on the cinema stage.
- **Typing indicator** — three brass-foil dots pulsing slowly. No "Concierge is thinking…" text.
- **No avatars, no robot icons, no AI sparkles, no "powered by" footer.**
- **Latency feedback** — if a reply takes >2s, the typing indicator remains; no progress bars, no spinners, no "this is taking longer than expected" copy.

---

## 13. Itinerary / day rules

Day planning is a **page in a folio**, not a database timeline.

- **Day page anatomy:** Issue masthead → Day numeral (large italic serif) → italic where-line ("In Positano, slowly.") → small-caps date/weather metadata → brass hairline → timeline → one inline cinema plate → continued timeline → places-in-rotation grid.
- **Timeline items** — two-column grid: italic serif time + small-caps period label on the left (`08:30 · MORNING`); paper-card content on the right (serif title, italic caption, folio-serial metadata line).
- **Item separators** are 1px dashed hairlines between items, *not* solid lines, *not* card borders. The day reads as one continuous editorial column.
- **No database affordances** — no checkboxes next to items, no drag handles by default (long-press to reorder on mobile, hover-to-reveal on desktop), no inline edit pencils, no "type to add" placeholder rows. Add via command palette / concierge / explicit add affordance from the sheet.
- **Empty time slots are silent.** No "Add an event" ghost rows.
- **One inline cinema plate per day** — interrupts the scroll once, like a tipped-in magazine photograph. Always between two timeline groups, never above the day numeral, never below the places grid.

---

## 14. Implementation sequencing (proposed)

Future slices only. Each slice ships independently and adds visible value. No slice may touch backend, providers, search, or the regressions fixed in PR #431.

- **Slice 1 — Editorial Foundation.** Variable serif (Fraunces) display roles; shell-wide paper-grain texture; radial ambient warmth layer; slow ambient drift on cinema panels with `prefers-reduced-motion` gating; introduce `--ds-marine-ink` token; demote `--ds-sandstone-gold` to foil role (no surface conversion yet). No component refactors.

- **Slice 2 — Paper World Adoption.** Convert lists, day pages, forms, settings, drawers, modals, and bottom sheets to paper surfaces. Introduce the paper-card archetype, hairline strokes, editorial section eyebrows, and folio-serial metadata. Convert primary CTAs in paper-world routes to marine ink.

- **Slice 3 — Framed Cinema Moments.** Convert the trip hero, AI Concierge canvas, image galleries, and map view into framed velvet panels nested inside paper pages. Tune vignette + edge-glow on cinema panels only.

- **Slice 4 — Premium Motion & Empty States.** Editorial enter transitions, paper-to-cinema reveal, bespoke empty/loading states (paper-noise sheet with slow serif "preparing your folio…" fade — not skeleton loaders), standardised hover/press micro-states.

- **Slice 5 — Destination-Aware Mood & Polish.** Trip-aware ambient tint pulled from destination hero (single hue, ≤8% luminance shift, strict luminance floor). Final pass on dividers, ornaments, brass-foil details, concierge typing indicator polish.

**Risky / deferred / out of scope:** cartographic / topographic background motifs; trip cover photography pipeline; any new animation library; parallax destination photography; haptic feedback. Park in `docs/product/IDEA_INBOX.md` if revisited.

---

## 15. Acceptance checklist

A design-slice PR is accepted only if a reviewer can answer **yes** to every line that applies to its scope. Slice 1 will not satisfy items 1–6 yet; later slices must.

- [ ] On first open, the app no longer reads as "dark SaaS with gold accents."
- [ ] Paper world is visibly present as the dominant chrome (background, lists, sheets, settings).
- [ ] Dark cinematic panels appear only at: trip hero, AI Concierge stage, image plates, map view, login splash. Nowhere else.
- [ ] Marine ink is the primary action accent in paper-world routes; brass/gold has been demoted to foil-only.
- [ ] Brass/gold appears only as hairlines, dividers, brass-bars, the wordmark dot, or editorial ornaments — never as a button fill.
- [ ] At least one editorial serif element appears on every screen.
- [ ] Mobile feels usable and premium: 4-tab bottom nav, paper chrome, ≤1 cinema plate per day folio, ≥44pt tap targets, no clutter.
- [ ] Existing trip flow, autocomplete portal behaviour, and round-trip flight leg behaviour from PR #431 are untouched (no diff in `CityAutocomplete`, `api.ts:addRoundTripLegToDay`, `TripBuilder.handleAddRoundTripToItinerary`, `ItineraryItemCard` round-trip detection).
- [ ] `prefers-reduced-motion` disables ambient drift entirely and halves transition durations.
- [ ] Body text contrast meets WCAG AA on both paper and cinema surfaces.
- [ ] No new package dependencies were added (or, if one was, it is named, justified, and ≤30 KB gzipped).
- [ ] No backend, provider, ranking, or persistence behaviour changed.

---

## 16. Resolved decisions (Slice 1 — 2026-05-18)

These were blocking before Slice 1. All resolved and implemented.

1. **Editorial serif:** **Fraunces**, loaded via `next/font/google`, `--font-fraunces` CSS variable, italic + normal styles, optical size axis (`opsz`). Applied in `layout.tsx`.
2. **Marine-ink hex:** `#1F4256` confirmed. WCAG AA verified: 10.2:1 on `--ds-warm-paper` (#FAF7F0), 8.2:1 on `--ds-linen` (#E6DECB). Ships in production.
3. **Token names:** `--ds-marine-ink`, `--ds-marine-deep` (#152E3E), `--ds-marine-soft` (#2A5870). Also added `--ds-folio-ink` (#1E1A14), `--ds-folio-ink-soft` (#4A4338), `--ds-folio-ink-mist` (#7A6E5C) for paper-world text.
4. **Brass demotion path:** Option (a) — `--ds-sandstone-gold` token name unchanged; brass demoted by stopping new usage in touched areas. No rename or shim needed. Slice 2 completes the demotion across card surfaces.
5. **Desktop shell scope:** Slice 1 includes full paper-first shell: body bg, `atelier-atmosphere-root`, and Sidebar converted to paper/linen. Desktop sidebar is paper (`folio-sidebar`). Mobile bottom nav is paper. Mobile top bar stays dark (test constraint from 8J). Visible paper shift lands in Slice 1, not deferred.
6. **Concept HTML location:** Remains at `docs/ai/concepts/folio-concept-v1.html` as doc-only reference. No dev route added.
7. **Personalisation depth:** Deferred to Slice 5. No change here.

## 17. Resolved decisions (Slice 2 — 2026-05-18)

These were open questions before Slice 2. All resolved and implemented.

1. **Mobile top bar:** `mobile-top-bar` converted from midnight to paper-world (`bg-ds-bone`, `text-ds-folio-ink`, hairline bottom border). 8J test updated to assert paper tokens instead of midnight.
2. **Card surface conversion:** `trips/page.tsx` cards (JourneyCard, ContinuePlanningHero, EditModal), `trips/[id]/page.tsx` panels (trip header, chapter cover, workspace switcher), and `ItineraryDayColumn.tsx` all converted to `folio-paper-card` / `folio-paper-panel`. Old boutique/advisor-desk primitive classes removed from these surfaces.
3. **CTA migration:** Primary CTAs in trips/dashboard routes migrated to `btn-marine`. `ContinuePlanningHero` action buttons, `JourneyCard` edit/delete actions, and trip detail workspace tabs use `btn-marine`. `btn-primary` (gold) retained only on explicit booking/payment flows.
4. **Paper primitives added to globals.css:** `folio-paper-card`, `folio-paper-panel`, `folio-paper-section`, `folio-paper-header`, `folio-divider`, `folio-muted-label`, `folio-chip`, `folio-input` — all using `--ds-bone`/`--ds-warm-paper`/`--ds-linen` surfaces with `--ds-hairline` borders and `--ds-folio-ink` text.

## 18. Resolved decisions (Slice 3 — 2026-05-18)

1. **Paper planning objects:** ItineraryItemCard, TripBuilderForm, OptimizeTripModal, DayPlanModal all converted to paper-world (`folio-paper-item`, `folio-paper-panel`, `folio-paper-header`, `bg-ds-bone`/`bg-ds-linen` cards). Dark/boutique tokens removed from these surfaces.
2. **Cinema surfaces excluded from paper conversion:** AI Concierge composer + result cards remain cinema-world per dual-world contract. ExploreShell, SavedShell, DashboardClient cinema panels likewise remain dark.
3. **Folio serial + masthead:** Deferred to Slice 5.

## 19. Resolved decisions (Slice 4 + 4B — 2026-05-18)

1. **Cinema CSS primitives defined:** 7 new enforcement classes added to `globals.css` in the CINEMA WORLD ENFORCEMENT section: `folio-cinema-lounge` (Discover wrapper), `folio-cinema-tile` (Discover VerticalCard), `folio-cinema-collection` (Saved outer shell), `folio-collection-card` (Saved item card), `folio-cinema-desk` (Concierge main wrapper), `folio-cinema-composer` (Concierge sticky composer), `folio-home-cinema-card` (Dashboard cinema cards).
2. **Additive stacks replaced:** Slice 4 had applied cinema classes additively on top of old boutique/editorial classes (e.g. `editorial-scene folio-cinema-shell`), so visual composition did not change. Slice 4B explicitly replaces old stacks — the old classes are absent from the component source.
3. **DashboardClient cinematic cards:** `Card tone="dark"` (which applied `bg-ds-onyx` as a Tailwind utility overriding component-level CSS) replaced with plain `<article className="folio-home-cinema-card">` to avoid specificity conflict between `@layer utilities` and `@layer components`.
4. **TripBuilder planning cockpit:** Paper-world context header tokens corrected — `text-ds-text-tertiary`/`text-ds-text`/`text-ds-accent` (cream, invisible on warm-paper) replaced with `text-ds-folio-ink-mist`/`text-ds-folio-ink`/`text-ds-marine-ink`.
5. **Brass hairline border:** All cinema enforcement primitives use `var(--ds-brass-field-border)` (a warm amber at ~8% opacity) as a hairline border, not a full brass fill. This is the correct token for subtle cinema panel framing.
6. **`reduced-motion` guards:** All cinema enforcement primitives that include `transition` or `transform` are wrapped in `@media (prefers-reduced-motion: reduce)` overrides.

## 20. Open questions — Slice 5

1. **Folio serial + masthead:** Issue masthead, folio serials, large day numerals (currently deferred). Slice 5 is the natural home.
2. **TripBuilder CollapsiblePanel:** Still uses `bg-ds-carbon`/`bg-ds-onyx` — visual correctness for the paper world day-folio view. Candidate for Slice 5 or a standalone Slice 4C.
3. **Destination-aware mood tint:** Trip-aware ambient hue from hero — deferred to Slice 5.

---

*Reference frames live in `docs/ai/concepts/folio-concept-v1.html`. Future implementation prompts should read this file plus that concept, and not re-explain the visual direction.*
