"""Sections 5-8: Motion, AI Concierge flagship UX, Page-by-page, Card system."""

from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether,
)

from styles import (
    INK, ONYX, CARBON, PEN, GOLD, BRASS, PEARL, CREAM_TEXT, SAGE,
    AMBER, CORAL, MIST, RAIN, PAPER, INK_PAPER, SLATE, HAIRLINE,
    Callout, bullets, labeled_bullets, hr, small_table,
)
from layout import chapter_opener


# ---------------------------------------------------------------------------
# SECTION 5 — Motion and microinteraction system
# ---------------------------------------------------------------------------
def build_section_5(story, styles):
    chapter_opener(story, '05', 'Motion and microinteraction system',
                   'Cinematic motion that respects performance, reduced-motion '
                   'preferences, and the speed of the intelligence pipeline.',
                   styles)

    story.append(Paragraph('5.1  Motion principles', styles['h2']))
    story.extend(labeled_bullets([
        ('Motion explains, never decorates.',
         'Every motion answers a question: where did this come from, where did it go, '
         'why is it different now? Motion that does not answer one of these is removed.'),
        ('Easing is a brand asset.',
         'A single ease-out-quad on entrance and ease-in-quad on exit. No bouncy '
         'springs, no overshoot, no elastic. Boutique motion is contained.'),
        ('Durations are short and rhythmic.',
         'Micro: 120&thinsp;ms (chip press, focus). Default: 200&thinsp;ms (card hover, '
         'drawer open). Spatial: 320&thinsp;ms (page transition, sheet enter). Nothing '
         'longer than 400&thinsp;ms.'),
        ('Motion never blocks first paint.',
         'Card content renders immediately at final position, then fades from 0.6 → 1 '
         'opacity. We never animate <i>from offscreen → onscreen</i> for primary content.'),
        ('Reduced-motion is a real product.',
         '<i>prefers-reduced-motion</i> swaps every animation for a 60&thinsp;ms opacity '
         'fade. Every component must be tested in this mode.'),
    ], styles))

    story.append(Paragraph('5.2  Page transitions', styles['h2']))
    rows = [
        ['Transition', 'From → To', 'Treatment', 'Duration'],
        ['Trip enter',     'Trips list → Trip detail',
         'Trip cover image cross-fades; sidebar persists',                         '320 ms'],
        ['Concierge open', 'Any page → AI Concierge drawer',
         'Drawer slides in from right (desktop) / up (mobile); page dims to 60&thinsp;%', '280 ms'],
        ['Tab switch',     'Explore tabs',
         'Content cross-fades 200 ms; tab indicator slides 220 ms',               '220 ms'],
        ['Auth → app',     'Login → Dashboard',
         'Cinematic dim of background image; serif-heading entrance',              '600 ms'],
        ['Modal open',     'Any → modal',
         'Backdrop fades in 200 ms; modal scales 0.96 → 1 with 240 ms ease-out',   '240 ms'],
    ]
    story.append(small_table(rows, [1.3*inch, 1.7*inch, 3.05*inch, 0.85*inch], styles))

    story.append(Paragraph('5.3  Card entrance', styles['h2']))
    story.append(Paragraph(
        'When a verified card list returns from the AI Concierge, cards fade in with a '
        '40&thinsp;ms stagger between siblings, in score order. The stagger is capped: '
        'after the 6th card we stop staggering, so the 12th result is not delayed by '
        '480&thinsp;ms. Cards that come from a cache or pool hit do <b>not</b> stagger '
        '&mdash; they paint at once, signalling speed.',
        styles['body']))
    story.append(Callout('What happens when the pipeline is faster than the animation', [
        'On a pool/follow-up hit, total backend time can be &lt; 1&thinsp;s. We must '
        'not invent a 600&thinsp;ms thinking animation to make the system look "smart". '
        'When data arrives in &lt; 200&thinsp;ms, render immediately with no staggered '
        'entrance. Speed is the luxury cue.',
    ], kind='principle'))

    story.append(Paragraph('5.4  AI Concierge thinking, searching, verifying states',
                           styles['h2']))
    story.extend(labeled_bullets([
        ('Composed breadcrumb.',
         '<i>Searching · Verifying · Composing</i>. Active stage glows gently '
         '(opacity 1.0 + 1&thinsp;px pearl underline); inactive stages at opacity 0.4. '
         'Stage transitions are driven by real timing events from '
         '<i>fast_dynamic_place_search.timing</i>.'),
        ('Cursor pulse, not spinner.',
         'A single 1&thinsp;px pearl-cream caret blinks at the end of the active stage '
         'label. No spinner, no loading bar, no animated dots.'),
        ('Verification micro-moment.',
         'When a Google Place verifies, a small sage hairline draws across the bottom '
         'of the appearing card in 220&thinsp;ms. This is the only "verification '
         'animation" we ship.'),
        ('Hard cap.',
         'If the pipeline exceeds 12&thinsp;s, the breadcrumb adds a fourth stage, '
         '“Stretching the search”, and surfaces a “show what you have so far” chip. '
         'We never let the user wait silently.'),
    ], styles))

    story.append(Paragraph('5.5  Save / Add-to-trip moments', styles['h2']))
    story.extend(labeled_bullets([
        ('Add-to-trip.',
         'The card briefly slides 6&thinsp;px right while a sandstone hairline pulses '
         'across it. A toast does NOT appear; instead, the trip&rsquo;s tab indicator '
         'in the sidebar gains a 1.5x dot for 1.6&thinsp;s.'),
        ('Save (heart) toggle.',
         'The icon transitions stroke→fill in 160&thinsp;ms with a 4&thinsp;% scale '
         'pulse. No confetti, no toast.'),
        ('Move to a day.',
         'A drag handle is always visible on itinerary cards on desktop. A long-press '
         'starts drag on mobile. Drop zones gain a sandstone hairline on hover; the '
         'whole row is the drop target, not a tiny gap between cards.'),
    ], styles))

    story.append(Paragraph('5.6  Timeline transitions', styles['h2']))
    story.extend(labeled_bullets([
        ('Day reorder.',
         'Re-ordering items animates the surrounding rows 200&thinsp;ms with FLIP. '
         'No vertical scroll jump.'),
        ('Travel-time hint reveal.',
         'When a hint inserts (e.g., "12 min walk"), it expands from height 0 → '
         'computed height in 220&thinsp;ms. The hint is hairline + caption type, never '
         'a full card.'),
        ('Day collapse.',
         'Days collapse to a single row that shows the day&rsquo;s "headline pick" + '
         'count. Expansion uses the same 220&thinsp;ms transition.'),
    ], styles))

    story.append(Paragraph('5.7  Map ↔ card interactions', styles['h2']))
    story.extend(labeled_bullets([
        ('Hover-to-pin.',
         'Hovering a card highlights its pin (1.5x ring) and dims unrelated pins to '
         '0.4 opacity. Hovering a pin highlights its card by 1&thinsp;px sandstone '
         'border &mdash; the list does NOT auto-scroll.'),
        ('Click-to-fly.',
         'Clicking a pin flies the map to the pin in 320&thinsp;ms with ease-out-cubic '
         'and opens the card&rsquo;s detail drawer. Clicking the same pin twice closes '
         'the drawer.'),
        ('Pan locks the requery.',
         'A small "search this area" chip appears in the top-center of the map after a '
         '300&thinsp;px pan. We never auto-requery on pan.'),
    ], styles))

    story.append(Paragraph('5.8  Hover and tap states', styles['h2']))
    story.extend(labeled_bullets([
        ('Cards.',
         'Hover lifts elevation e1 → e2 (border becomes 1&thinsp;px sandstone @ 30%). '
         'No scale, no shadow puff, no glow.'),
        ('Buttons.',
         'Primary button hover: background goes from sandstone to ember-brass over '
         '120&thinsp;ms. Secondary: hairline border thickens 0.5 → 1&thinsp;px. '
         'Pressed: a 1&thinsp;px inner shadow, no scale.'),
        ('Chips.',
         'Hover: 1&thinsp;px sandstone outline. Active: filled sandstone with ink text. '
         'No "wiggle" or "bounce".'),
    ], styles))

    story.append(Paragraph('5.9  Forbidden animations', styles['h2']))
    story.append(Callout('Animations that harm the brand or the pipeline', [
        '<b>Parallax scrolling.</b> Slows everything; not boutique.',
        '<b>Glow pulses on hover.</b> Generic SaaS aesthetic.',
        '<b>Animated gradient meshes.</b> Crypto-landing aesthetic.',
        '<b>Bouncing/elasticy springs.</b> Not boutique.',
        '<b>Confetti, fireworks, “success” bursts.</b> Childish.',
        '<b>Auto-playing video backgrounds.</b> Slow on mobile, dishonest evidence.',
        '<b>Scroll-jacking.</b> Removes the user&rsquo;s control of pacing.',
        '<b>Letter-by-letter typewriter effects on AI replies.</b> Adds latency, '
        'feels like a chatbot, undermines our card-first hierarchy.',
    ], kind='reject'))

    story.append(Paragraph('5.10  Reduced-motion fallback', styles['h2']))
    story.append(Paragraph(
        '<i>@media (prefers-reduced-motion: reduce)</i> applies the following overrides '
        'globally: all transform animations disabled; all opacity transitions capped at '
        '60&thinsp;ms; all stagger removed; map fly-to becomes a hard cut. The product '
        'still feels intentional; it just stops moving.',
        styles['body']))
    story.append(PageBreak())


# ---------------------------------------------------------------------------
# SECTION 6 — AI Concierge flagship UX
# ---------------------------------------------------------------------------
def build_section_6(story, styles):
    chapter_opener(story, '06', 'AI Concierge flagship UX',
                   'The flagship surface. Treats verified cards as the hero and '
                   'the conversation as a slim editorial rail.',
                   styles)

    story.append(Paragraph(
        'The AI Concierge must feel like the most intelligent surface in the product '
        '<i>without</i> exposing pipeline internals, debug payloads, or cute chatbot '
        'tropes. The design move is structural: invert the dominance from '
        '<i>chat-bubble-with-cards</i> to <i>cards-with-conversation-rail</i>.',
        styles['lead']))

    story.append(Paragraph('6.1  Layout', styles['h2']))
    story.append(Paragraph(
        'Two-column layout on desktop (≥ 1024&thinsp;px); single-column sheet on mobile.',
        styles['body']))
    rows = [
        ['Region', 'Width', 'Contents'],
        ['Conversation rail (left)', '320&thinsp;px',
         'Prompt history as small typeset turns, intent chip, "show evidence" toggle, '
         'memory pill ("planning Chicago, May 2026, anniversary").'],
        ['Result canvas (right)', 'fills',
         'Verified card grid (3 columns desktop, 2 tablet, 1 mobile), with the active '
         'card promotable to a half-bleed detail panel.'],
        ['Composer (sticky)',     'full',
         'Always visible on the bottom 88&thinsp;px of the result canvas. Houses the '
         'prompt input, suggestion chips, and the &uarr;/&darr; result navigator.'],
    ]
    story.append(small_table(rows, [1.7*inch, 1.0*inch, 4.25*inch], styles))

    story.append(Paragraph('6.2  Prompt composer', styles['h2']))
    story.extend(labeled_bullets([
        ('A typeset textarea, not a chat input.',
         'Sans 16&thinsp;px, 4-line max, autoresizes. Placeholder rotates between three '
         'concrete examples per session: '
         '"sushi with a waterfront view", '
         '"tapas bar that is not too loud", '
         '"the ones I\'d actually take my mother to". '
         'Placeholders never advertise capabilities.'),
        ('Composer chips.',
         'Three contextual chips above the input: <b>Refine</b>, <b>Compare</b>, '
         '<b>More options</b>. They post the prompt with the right intent so the user '
         'does not type the magic phrase.'),
        ('Submit on enter, newline on shift-enter.',
         'Standard. The send affordance is a 24&thinsp;px outlined arrow in sandstone, '
         'not a "Send" button.'),
        ('Token budget hint.',
         'A faint counter appears only when the prompt exceeds 240 characters: '
         '“Long prompt &mdash; we will summarize.” Honest, restrained.'),
    ], styles))

    story.append(Paragraph('6.3  Verified card result layout', styles['h2']))
    story.append(Callout('Card-first hierarchy', [
        'The conversation rail summarizes the user&rsquo;s ask in one line: '
        '<i>"Tapas bars in West Loop, evening, dinner-date feel."</i> Below, the result '
        'canvas opens directly into the card grid &mdash; <b>no AI reply paragraph</b>. '
        'The prose belongs in the card&rsquo;s "why this fits" section, not above the grid. '
        'This is the single most opinionated decision in this bible.',
    ], kind='principle'))

    story.extend(labeled_bullets([
        ('No "Here are some options for you" preamble.',
         'Preambles are a chatbot tell. They cost an extra line of vertical space, push '
         'the verified cards below the fold, and add nothing the cards do not say.'),
        ('Result count is editorial.',
         '"Six places that fit." with the count rendered as a small Display S serif. '
         'Not "I found 6 results.".'),
        ('A "Why these six" link.',
         'Below the count, a small caption: <i>How we picked these &mdash; tap to see.</i> '
         'Expands a 1-paragraph plain-language summary citing the constraints we '
         'detected (cuisine, vibe, neighborhood). Honest, brief.'),
    ], styles))

    story.append(Paragraph('6.4  Evidence and trust indicators on cards', styles['h2']))
    story.append(Paragraph(
        'See §9 for the full evidence chapter. Inside the AI Concierge result canvas, '
        'the trust strip on each card is identical to the trust strip on the rest of '
        'the product. The Concierge is not allowed to invent its own trust language.',
        styles['body']))

    story.append(Paragraph('6.5  Follow-up chips', styles['h2']))
    story.append(Paragraph(
        'Below the result grid, a row of follow-up chips. They are not generic; they '
        'are derived from the parsed intent (cuisine, vibe, constraint, neighborhood) '
        'and from the cards just returned.',
        styles['body']))
    story.extend(labeled_bullets([
        ('Refinement chips.',
         '"Quieter", "More upscale", "Walking distance from my hotel", "Better wine '
         'list". Each one mutates the prompt; we never invent a constraint we did not '
         'detect.'),
        ('Compare chip.',
         '"Compare top 3" routes to the existing refine_previous flow without re-issuing '
         'card identity keys.'),
        ('Negate chip.',
         '"Not these" lets the user dismiss the current set and re-search with a '
         'negative-constraint hint.'),
    ], styles))

    story.append(Paragraph('6.6  Conversational memory indicators', styles['h2']))
    story.extend(labeled_bullets([
        ('Memory pill.',
         'Top-left of the rail: a tiny pill summarizing the active context &mdash; '
         '<i>"Chicago · May 2026 · anniversary trip"</i>. Tapping the pill opens an '
         'edit drawer. The pill is the only place memory is exposed.'),
        ('Edit, do not deny.',
         'If the user wants to change the destination, we let them edit the pill. We '
         'never "auto-clear" memory or pretend we forgot.'),
        ('Forget toggle.',
         'A "start fresh" link in the pill drawer wipes context cleanly. We do not hide '
         'this.'),
    ], styles))

    story.append(Paragraph('6.7  Weak-evidence handling', styles['h2']))
    story.append(Paragraph(
        'When evidence is thin (single source, place verified but key constraint not '
        'corroborated), the card surfaces a <i>weak-evidence chip</i> in caution amber, '
        'and the "why this fits" line begins with <i>“Likely fits &mdash; we could not '
        'verify…”</i>. We never hide the weak-evidence card; we present it honestly.',
        styles['body']))
    story.append(Callout('Weak evidence is a feature, not a failure', [
        'Other AI planners hide their uncertainty by inventing prose. Travel Concierge '
        'turns uncertainty into a luxury cue: a beautifully typeset caveat says we '
        'looked, we did not find corroboration, and we will help the user verify on '
        'booking. Honesty becomes the brand.',
    ], kind='opportunity'))

    story.append(Paragraph('6.8  No-results handling', styles['h2']))
    story.append(Paragraph(
        'When zero verified places match, we never show a “No results found” state. '
        'We show a typeset, three-paragraph editorial empty state:',
        styles['body']))
    story.append(Paragraph(
        '"<i>Nothing in West Loop matched ‘tapas bar’ tonight that we are confident '
        'about. The closest fits we can find are in River North, ~12&thinsp;min away. '
        'You can broaden the area, change the cuisine, or open the search to '
        'tomorrow night.</i>"',
        styles['quote']))
    story.append(Paragraph(
        'Three refinement chips appear under the empty state, derived from the '
        'parsed intent.',
        styles['body']))

    story.append(Paragraph('6.9  Card add flow', styles['h2']))
    story.extend(labeled_bullets([
        ('Single-tap add.',
         'A primary "Add to trip" button on every verified card. If the user has more '
         'than one trip, a small popover lets them choose &mdash; never a full modal.'),
        ('Default trip.',
         'The most-recently-touched trip is the default. The popover offers other '
         'trips as a list, with a "Save without trip" option.'),
        ('Acknowledgement.',
         'See §5.5. The card briefly slides right with a sandstone pulse; no toast.'),
    ], styles))

    story.append(Paragraph('6.10  Compare / refine flow', styles['h2']))
    story.extend(labeled_bullets([
        ('Top-3 compare.',
         '"Compare top 3" promotes three cards to a horizontal scroll lane with the '
         'evidence rows aligned: cuisine match, vibe match, source count, walking '
         'distance from hotel. Each row is a typeset list, not a table chrome.'),
        ('Refine without re-fetching.',
         'A refinement chip ("quieter", "better wine list") that we can satisfy from '
         'existing card metadata never triggers a new search; we re-rank the existing '
         'pool. The composer shows a hairline pulse rather than the full thinking '
         'breadcrumb &mdash; the user feels the speed.'),
    ], styles))

    story.append(Paragraph('6.11  Mobile behavior', styles['h2']))
    story.extend(labeled_bullets([
        ('Concierge as a 90vh sheet.',
         'Opened from any screen via the floating composer pill or ⌘K equivalent. '
         'Drag-down dismiss; the composer is always visible.'),
        ('Conversation rail collapses to a header.',
         'Memory pill + intent line live in the sheet header; full history opens via a '
         'small "history" link &mdash; not a hamburger.'),
        ('Single-column card stack.',
         'Cards stack at 100% width, with horizontal swipe to compare neighbors. The '
         'add-to-trip button stays sticky inside the sheet.'),
    ], styles))

    story.append(Paragraph('6.12  Making it feel intelligent without exposing internals',
                           styles['h2']))
    story.append(Callout('Intelligence cues we ship vs. ones we forbid', [
        '<b>Ship:</b> the parsed-intent line ("Tapas bars in West Loop, evening, '
        'dinner-date feel."), the composed thinking breadcrumb, the dynamic "why this '
        'fits" line, the weak-evidence chip, the source count, the refine chips '
        'derived from constraints we actually parsed.',
        '<b>Forbid:</b> animated thinking dots, simulated typing, a chatbot avatar, '
        'a "thought process" panel showing chain-of-thought, exposing model name or '
        'token counts, exposing the raw search query we sent to Google, exposing '
        'place IDs or identity keys.',
    ], kind='guardrail'))
    story.append(PageBreak())


# ---------------------------------------------------------------------------
# SECTION 7 — Page-by-page product design plan
# ---------------------------------------------------------------------------
def _page_block(story, styles, name, body_pairs, risks=None, impl_notes=None,
                no_change=None):
    story.append(Paragraph(name, styles['h2']))
    for k, v in body_pairs:
        story.append(Paragraph(k, styles['h4']))
        if isinstance(v, list):
            for it in v:
                story.append(Paragraph(u'•  ' + it, styles['bullet']))
        else:
            story.append(Paragraph(v, styles['body']))
    if risks:
        story.append(Paragraph('Risks', styles['h4']))
        for it in risks:
            story.append(Paragraph(u'•  ' + it, styles['bullet']))
    if impl_notes:
        story.append(Paragraph('Implementation notes', styles['h4']))
        for it in impl_notes:
            story.append(Paragraph(u'•  ' + it, styles['bullet']))
    if no_change:
        story.append(Callout('What not to change yet', no_change, kind='guardrail'))
    story.append(hr())


def build_section_7(story, styles):
    chapter_opener(story, '07', 'Page-by-page product design plan',
                   'Every major surface, with intent, hierarchy, components, '
                   'states, risks, and what must not change yet.',
                   styles)

    story.append(Paragraph(
        'For each surface we list: <b>user intent</b>, <b>visual goal</b>, '
        '<b>information hierarchy</b>, <b>key components</b>, <b>interactions</b>, '
        '<b>empty/loading/error</b>, <b>risks</b>, <b>implementation notes</b>, '
        '<b>what not to change yet</b>.',
        styles['lead']))

    # ---- 7.1 Landing
    _page_block(story, styles, '7.1  Unauthenticated landing', [
        ('User intent', 'Decide in 8 seconds whether this product is for me.'),
        ('Visual goal', 'A cinematic hero, not a SaaS landing. Single full-bleed '
         'destination photograph, serif display headline, single CTA.'),
        ('Information hierarchy', [
            '1. Headline statement of brand promise (serif Display XL).',
            '2. One-line value proposition (sans body).',
            '3. Single CTA: "Plan your trip." (no secondary CTA above the fold).',
            '4. Three-card editorial proof strip below the fold (no logos wall).',
            '5. AI Concierge inline demo &mdash; a real, throttled demo prompt.',
        ]),
        ('Key components', [
            'Cinematic hero with photo + 4% ink overlay + 1% grain.',
            'Composer pill (glass, the only glass surface in the product).',
            'Editorial proof strip: three real verified-place cards.',
            'Footer with restraint &mdash; no eight-column link grid.',
        ]),
        ('Interactions', [
            'Composer pill in the hero accepts a real prompt; submitting routes to '
            'sign-up with the prompt prefilled in the AI Concierge.',
            'Scroll triggers a 600&thinsp;ms ink fade behind the proof strip.',
        ]),
        ('Empty / loading / error', 'No empty state. Loading: only the proof strip '
         'awaits an image; the rest of the page paints immediately.'),
    ],
    risks=[
        'Glass + photo can hurt mobile FCP. Mitigate by serving an LQIP and '
        'capping blur radius on phone.',
        'A real demo composer can be misused. Throttle by IP and by prompt length.',
    ],
    impl_notes=[
        'Photo asset must be licensed; no Unsplash placeholders shipped to prod.',
        'Demo composer goes to the existing AI route with a "demo" flag; no new API.',
    ],
    no_change=[
        'Do not redesign the auth flow yet; the demo only routes to existing sign-up.',
        'Do not introduce a video hero before mobile FCP budgets are set.',
    ])

    # ---- 7.2 Login / signup
    _page_block(story, styles, '7.2  Login / signup', [
        ('User intent', 'Get in fast, feel like I have arrived somewhere nice.'),
        ('Visual goal', 'A still hero (not a moving one), a single column form, '
         'identical type and tokens to the rest of the product.'),
        ('Information hierarchy', [
            '1. Brand wordmark, 24&thinsp;px, top-left.',
            '2. Serif Display L: "Welcome back."',
            '3. Email + password fields, OAuth buttons stacked below.',
            '4. Switch to sign-up link, plain underline, no card.',
        ]),
        ('Key components', ['Cinematic still photo (swappable for one of three '
         'curated destinations).',
            'Single-column form, 360&thinsp;px width, 24&thinsp;px field gap.',
            'Inline error: hairline coral border + sentence below the field.']),
        ('Interactions', ['Submit on enter; OAuth buttons go to provider modal '
         'directly.', 'No "remember me" checkbox &mdash; we use long-lived sessions.']),
        ('Empty / loading / error',
         'Loading: button label changes to "Signing you in"; no spinner. '
         'Error: hairline coral, plain English message ("That password is wrong" not '
         '"Authentication failed").'),
    ],
    risks=['Password reset flow lives outside this slice; do not bundle.'],
    impl_notes=['Reuse existing auth API; no payload changes.'],
    no_change=['Do not touch the auth backend or session cookie strategy.'])

    # ---- 7.3 Dashboard / trips home
    _page_block(story, styles, '7.3  Dashboard / Trips home', [
        ('User intent', 'See my trips, jump back in, plan the next one.'),
        ('Visual goal', 'An editorial reading room: a short concierge greeting, '
         'two or three trip "covers" with destination atmosphere, a quiet AI Concierge '
         'launchpad.'),
        ('Information hierarchy', [
            '1. Concierge greeting line ("Good evening, Prashanth. Three trips on '
            'your shelf.") &mdash; serif Display M.',
            '2. Trip covers (large, full-bleed photo + cover details).',
            '3. AI Concierge launch pill, sticky bottom on mobile.',
            '4. Travel hints strip ("Your Chicago trip is in 18 days &mdash; '
            'restaurants are filling Saturdays.")',
        ]),
        ('Key components', [
            'Trip cover card (see §8.x).',
            'Greeting block (h1) with destination memory pill.',
            'Concierge launch pill (sticky on mobile, sidebar entry on desktop).',
            'Hint strip with at most 3 hints, all ranked by trip recency.',
        ]),
        ('Interactions', [
            'Tap a trip cover to open trip detail with the cover image cross-fade '
            '(see §5.2).',
            'Tap the concierge pill to open the drawer with the trip in context.',
        ]),
        ('Empty / loading / error', [
            'Empty: a single typographic state &mdash; "No trips yet. Where to next?" '
            '&mdash; with a single CTA. No illustration.',
            'Loading: the greeting paints immediately with the user&rsquo;s name; trip '
            'covers fade in with stagger.',
            'Error on trip fetch: a calm strip at top: "Could not load your trips. '
            'Retrying." with a manual retry link.',
        ]),
    ],
    risks=['Trip cover photos require sourcing &mdash; if we do not have one, we '
           'typeset the destination name in serif. Never stock photo.'],
    impl_notes=['Reuse existing /trips data; no API change.'],
    no_change=['Do not introduce a new trip-creation flow on this page; the '
               '"plan a trip" CTA opens the existing flow.'])

    # ---- 7.4 Trip detail
    _page_block(story, styles, '7.4  Trip detail page', [
        ('User intent', 'Plan, refine, and live in this trip.'),
        ('Visual goal', 'A reading-room layout with three persistent regions: '
         'cover + memory header, body (tabs: Itinerary / Saved Ideas / Explore), '
         'AI Concierge drawer that is always one keystroke away.'),
        ('Information hierarchy', [
            '1. Trip cover: full-bleed image + destination + dates + party size.',
            '2. Tabs: Itinerary (default), Saved Ideas, Explore, Notes.',
            '3. Right-rail summary on desktop: hotel, flights, total saved spots.',
            '4. AI Concierge drawer (collapsed by default).',
        ]),
        ('Key components', ['Trip cover header, Tab bar, Itinerary timeline, '
         'Saved Ideas grid, Explore grid, Concierge drawer toggle.']),
        ('Interactions', [
            'Tabs switch with content cross-fade.',
            'Drag-to-day from Saved Ideas to Itinerary.',
            'Concierge drawer remembers trip context (memory pill).',
        ]),
        ('Empty / loading / error', [
            'Empty itinerary: typographic, with three concierge prompts ("Restaurants '
            'we should book first?", "Best half-day in Lincoln Park?", "Anything '
            'unmissable for an anniversary?").',
            'Loading: the cover paints immediately; tabs and itinerary fade in.',
            'Error: per-tab error chip, not a page-level red banner.',
        ]),
    ],
    risks=['Drag interactions on mobile must be long-press to avoid scroll '
           'conflicts.'],
    impl_notes=['Existing trip detail components are mostly intact; this is a '
                'visual + IA pass, not a data refactor.'],
    no_change=['Do not change the trip data model or any persistence contract.'])

    # ---- 7.5 AI Concierge drawer / page
    _page_block(story, styles, '7.5  AI Concierge drawer / page', [
        ('User intent', 'Ask the concierge anything; get verified, addable answers.'),
        ('Visual goal', 'Card-first, see §6 for the full chapter.'),
        ('Information hierarchy', '1. Memory pill.  2. Intent line.  3. Result grid. '
         '4. Refinement chips.  5. Composer.'),
        ('Key components', ['Memory pill, intent line, result grid (§8), '
         'thinking breadcrumb, refinement chips, composer.']),
        ('Interactions', 'See §6 in full; this entry is a stub for completeness.'),
        ('Empty / loading / error', 'See §6.7&ndash;6.8.'),
    ],
    no_change=['Do not modify intent detection, query parsing, ranking, or '
               'evidence pipelines. Frontend only.'])

    # ---- 7.6 Explore tabs
    _page_block(story, styles, '7.6  Explore tabs (Areas, Restaurants, Attractions, '
                                'Nightlife, Hotels)', [
        ('User intent', 'Browse curated, verified options when I do not have a '
         'specific question.'),
        ('Visual goal', 'A magazine-section feel, with tabs as discreet metadata '
         'rather than dominant chrome. Each tab uses the same Card primitive but with '
         'a distinct top motif (a sandstone hairline + tab-name overline) to provide '
         'rhythm without changing the card itself.'),
        ('Information hierarchy', [
            '1. Section title ("Restaurants in Chicago") + filter chip row.',
            '2. Map ↔ list split (desktop) or list-default (mobile).',
            '3. Pagination/lazy load &mdash; not infinite scroll without anchor.',
        ]),
        ('Key components', [
            'Tab bar (Areas / Restaurants / Attractions / Nightlife / Hotels).',
            'Filter chip row (cuisine, price band, neighborhood, vibe).',
            'Map (themed per §4.9).',
            'Card grid (3 desktop / 2 tablet / 1 mobile).',
        ]),
        ('Interactions', [
            'Filter chips persist in URL state (Expedia pattern, §2).',
            'Map ↔ card hover sync (§5.7).',
            '"Search this area" chip on pan; never auto-requery.',
        ]),
        ('Empty / loading / error', [
            'Empty: typed, with three refinement chips.',
            'Loading: 9 skeleton cards in dark mode.',
            'Error: per-section coral hairline strip.',
        ]),
    ],
    risks=['Hotels tab depends on hotel data we may not have for every destination; '
           'design must handle "no inventory yet" gracefully.'],
    impl_notes=['Areas tab uses neighborhood polygons styled per §4.9; if absent, '
                'fall back to typeset neighborhood list.'],
    no_change=['Do not introduce hotel booking flow yet; if Hotels tab opens, it is '
               'browse-only with a hand-off link.'])

    # ---- 7.7 Saved Ideas / Trip Ideas
    _page_block(story, styles, '7.7  Saved Ideas / Trip Ideas', [
        ('User intent', 'A scrapbook of places I might want, with the lightest '
         'possible commitment.'),
        ('Visual goal', 'Light-mode, paper surface. The only place we use light '
         'mode <i>inside</i> the app shell, because saved ideas are the trip\'s '
         'artefacts. The shift in tone is intentional and signals "this is yours, '
         'keep it."'),
        ('Information hierarchy', [
            '1. Date-grouped sections ("Saved this week", "From your Paris trip", etc.).',
            '2. Card grid in paper-mode treatment.',
            '3. Drag handles always visible on desktop.',
        ]),
        ('Key components', ['Saved Idea card (paper variant of §8 card).',
                              'Section headers in serif Display S.',
                              '"Move to trip" inline action per card.']),
        ('Interactions', ['Drag-to-trip on desktop, long-press-to-move on mobile.',
                           'Bulk select with keyboard (J/K to navigate, X to add to bin).']),
        ('Empty / loading / error', [
            'Empty: "Your scrapbook is empty. Tap &hearts; on anything to keep it."',
            'Loading: skeletons in paper tone.',
            'Error: hairline coral strip with a manual retry.',
        ]),
    ],
    risks=['The dark-to-light tonal switch must be done at the page-template level, '
           'not per-component, to avoid collision.'],
    impl_notes=['One CSS class on the route container drives the mode switch; tokens '
                'do the rest.'],
    no_change=['Do not split saved ideas storage from trip-scoped saves; the data '
               'model stays.'])

    # ---- 7.8 Itinerary timeline / day plan
    _page_block(story, styles, '7.8  Itinerary timeline / day planning', [
        ('User intent', 'See and shape my day-by-day plan.'),
        ('Visual goal', 'Editorial timeline. Days are not boxes; they are typeset '
         'sections separated by a hairline. Items are cards. Travel-time hints are '
         'caption-grade typography between cards.'),
        ('Information hierarchy', [
            '1. Trip dates header (always visible).',
            '2. Day section: serif Display S date + meta ("Sat, May 9 · light rain '
            'forecast").',
            '3. Itinerary cards in chronological order.',
            '4. Travel-time hints between cards.',
        ]),
        ('Key components', ['Itinerary card (§8), Day section header, Travel-time '
         'hint, AI Concierge "Suggest for this day" inline trigger.']),
        ('Interactions', ['Drag to reorder; drop zones span the full row.',
                           'Tap a card to open its detail drawer.',
                           '"Suggest for this day" opens the Concierge with the day in context.']),
        ('Empty / loading / error', [
            'Empty day: a single typographic line ("Nothing planned for Saturday yet.") '
            'and a "Suggest for this day" chip.',
            'Loading: the day headers paint immediately; cards stagger in.',
            'Error: day-level coral hairline strip.',
        ]),
    ],
    risks=['Drag-and-drop reorder must work with keyboard for accessibility.'],
    impl_notes=['Reuse existing itinerary state; no API change.'],
    no_change=['Do not introduce time-of-day blocks (morning/afternoon/evening) on '
               'top of explicit times unless the user explicitly opts in.'])

    # ---- 7.9 Travel time hints, hotels, flights, activities
    _page_block(story, styles, '7.9  Travel hints, flights, hotels, activities', [
        ('User intent', 'See research-stage information without committing.'),
        ('Visual goal', 'Caption-grade type for hints; cards reused for hotels/flights/'
         'activities, with the same trust strip discipline.'),
        ('Information hierarchy', [
            'Hints are always inline with the relevant itinerary item.',
            'Hotels/flights/activities are full sections in Trip Detail with the same '
            'card grid as Explore.',
        ]),
        ('Key components', ['Travel-time hint (caption + chip "view route").',
                              'Hotel card variant of §8.',
                              'Flight card variant of §8 (price, stops, duration).']),
        ('Interactions', ['"View route" opens the map with the route plotted.',
                           '"Open in booking provider" hands off; we do not book in-app yet.']),
        ('Empty / loading / error', ['Empty: section omitted entirely; we do not '
         'show "No hotels yet" placeholders.']),
    ],
    risks=['Provider hand-off must use a clean target=_blank with rel="noopener".'],
    impl_notes=['No new providers in design slices; just visual reuse.'],
    no_change=['Do not introduce in-app booking until a separate, explicit roadmap '
               'phase.'])

    # ---- 7.10 Cards and modals
    _page_block(story, styles, '7.10  Cards and modals', [
        ('User intent', 'Drill into a place, save it, add it, share it.'),
        ('Visual goal', 'A half-bleed detail panel (right rail on desktop, full sheet '
         'on mobile) rather than a full-screen modal. The panel breathes; the page '
         'stays visible behind it dimmed to 60&thinsp;%.'),
        ('Information hierarchy', [
            '1. Hero photo (or typeset monogram).',
            '2. Place name (Display M serif), trust strip, neighborhood + walking '
            'distance.',
            '3. "Why this fits" pull-quote with sources.',
            '4. Metadata grid: hours, price band, phone, website.',
            '5. Map preview with pin.',
            '6. Actions: Add to trip, Save, Share.',
        ]),
        ('Key components', ['Card detail panel, Trust strip, Pull-quote, Metadata '
         'grid, Map preview.']),
        ('Interactions', ['Esc closes; backdrop click closes; deep-link with URL '
         'param.']),
        ('Empty / loading / error', ['Loading: hero placeholder, content paints '
         'first.', 'Error: panel header + "Could not load this place" + retry.']),
    ],
    risks=['Half-bleed panels can collide with mobile bottom sheets; on mobile, '
           'panel becomes a 90vh sheet identical to AI Concierge.'],
    impl_notes=['Reuse Concierge sheet shell; one panel primitive for both surfaces.'],
    no_change=['Do not introduce in-card booking actions yet.'])

    # ---- 7.11 Profile / settings
    _page_block(story, styles, '7.11  Profile / settings', [
        ('User intent', 'Manage account, preferences, and travel style.'),
        ('Visual goal', 'Light mode, two-column on desktop, single-column on mobile. '
         'Sections are paper cards. Restraint over breadth.'),
        ('Information hierarchy', [
            '1. Identity: name, email, photo (optional), default home city.',
            '2. Travel style: party size default, pace (slow/balanced/fast), '
            'cuisine likes/dislikes.',
            '3. Account: password, sign out.',
            '4. Privacy: data export, delete account.',
        ]),
        ('Key components', ['Section card, Inline-edit field, Travel-style chip '
         'group.']),
        ('Interactions', ['Inline edit; save on blur or enter; never a "Save '
         'profile" big button at the bottom.']),
        ('Empty / loading / error', ['Loading: section cards skeleton; identity '
         'paints first.']),
    ],
    risks=['Travel-style preferences may eventually feed the AI Concierge; the '
           'design must accommodate that without making the UI noisy now.'],
    impl_notes=['No new fields shipped beyond what the backend supports today.'],
    no_change=['Do not wire travel-style preferences into the Concierge in this '
               'design slice.'])

    # ---- 7.12 Mobile nav / sidebar
    _page_block(story, styles, '7.12  Mobile nav / sidebar', [
        ('User intent', 'Move between trips, dashboard, and the Concierge.'),
        ('Visual goal', 'A bottom rail of three icons + concierge pill on mobile. '
         'A slim 72&thinsp;px sidebar on desktop with iconography only, '
         'expanding to 240&thinsp;px on hover/click.'),
        ('Information hierarchy', [
            '1. Dashboard.  2. Trips.  3. Concierge (pill).  4. Profile.',
        ]),
        ('Key components', ['Bottom rail, Sidebar, Concierge pill (sticky).']),
        ('Interactions', ['Tap rail items to navigate; Concierge pill always opens '
         'the sheet/drawer in context.']),
        ('Empty / loading / error', ['No empty state.']),
    ],
    risks=['Bottom rail collides with iOS home-bar; pad 12&thinsp;px.'],
    impl_notes=['The sidebar shipped in PR #168 already; this is a refinement, not a '
                'rebuild.'],
    no_change=['Do not change navigation routes.'])
    story.append(PageBreak())


# ---------------------------------------------------------------------------
# SECTION 8 — Card design system
# ---------------------------------------------------------------------------
def build_section_8(story, styles):
    chapter_opener(story, '08', 'Card design system',
                   'Cards are the atomic unit of the product. One primitive, one '
                   'shape language, configurable slots.',
                   styles)

    story.append(Paragraph('8.1  The Card primitive', styles['h2']))
    story.append(Paragraph(
        'There is one Card primitive. Every other card type composes it with different '
        'slots. The primitive enforces tokens; variants only choose which slots to render.',
        styles['body']))
    rows = [
        ['Slot', 'Required', 'Notes'],
        ['Identity (name + place type)', 'always', 'Display S serif on detail; Body L on grid.'],
        ['Trust strip',                  'always', 'Verified mark + source count + confidence chip.'],
        ['Media (image or monogram)',    'optional', 'Aspect 4:5 grid, 3:2 detail; never stock.'],
        ['Why this fits',                'optional', 'Pull-quote with at least one source tag.'],
        ['Metadata strip',               'optional', 'Neighborhood · price band · walking time.'],
        ['Actions',                      'always', '"Add to trip", "Save", "Open" affordances.'],
        ['Caveat',                       'conditional', 'Weak-evidence sentence in caution amber.'],
    ]
    story.append(small_table(rows, [2.0*inch, 0.9*inch, 4.0*inch], styles))

    story.append(Paragraph('8.2  Card variants', styles['h2']))
    rows = [
        ['Variant', 'Used in', 'Slot config', 'Key cue'],
        ['Verified place card',  'AI Concierge, Explore',
         'identity, trust, media, why, meta, actions',
         'Sandstone "Verified by Google" mark.'],
        ['AI Concierge result',  'Concierge result canvas',
         'identity, trust, why, meta, actions; media is lazy',
         'Why-this-fits is hero typography.'],
        ['Explore card',         'Explore tabs',
         'identity, trust, media, meta, actions',
         'Top hairline + tab overline (cuisine/area).'],
        ['Saved idea card',      'Saved Ideas (paper)',
         'identity, media, meta, action: move-to-trip',
         'Paper surface; warm tones.'],
        ['Itinerary item card',  'Itinerary timeline',
         'identity, time, meta, action: edit/move',
         'Time stamp typography is the lead.'],
        ['Area card',            'Areas tab',
         'identity, neighborhood polygon thumbnail, meta',
         'Neighborhood map preview replaces hero.'],
        ['Hotel card',           'Hotels tab',
         'identity, trust, media, price band, actions',
         'Price band is part of meta strip.'],
        ['Flight card',          'Flights research',
         'identity, route, time, price, actions',
         'Typographic route ribbon (DEN &rarr; ORD).'],
        ['Activity card',        'Activities research',
         'identity, trust, media, duration, price, actions',
         'Duration chip in caution amber if &gt; 1 day.'],
    ]
    story.append(small_table(rows, [1.4*inch, 1.5*inch, 2.4*inch, 1.6*inch], styles))

    story.append(Paragraph('8.3  Trust badges', styles['h2']))
    story.extend(labeled_bullets([
        ('"Verified by Google".',
         'A small icon + caps overline label, sage on dark, sage on paper. Only on '
         'cards where backend has a stable Google Place ID and OPERATIONAL status.'),
        ('"3 sources".',
         'A typographic chip rendered as the count + the word "sources". Tapping '
         'expands the source list inline.'),
        ('"Confidence: high / medium / low".',
         'Plain-English chip mapped to evidence count. Never a numeric percentile.'),
        ('"Worth the splurge" / "Luxury for less".',
         'See §3.7. Brass background, ink text. Used selectively, not on every card.'),
    ], styles))

    story.append(Paragraph('8.4  Reason / why sections', styles['h2']))
    story.append(Paragraph(
        'On every card variant, the "why this fits" string is the one we receive from '
        'the backend (e.g., <i>_build_dynamic_why()</i>). The UI never paraphrases it. '
        'It is rendered as a serif italic pull-quote (Quote style, §4.4) with an inline '
        'source tag at the end. If the reason is generic, the source tag reads '
        '<i>(verified place, no editorial)</i>.',
        styles['body']))

    story.append(Paragraph('8.5  Source / evidence indicators', styles['h2']))
    story.extend(labeled_bullets([
        ('Source list is one tap away.',
         'Tapping the source count reveals a typeset list of sources (publication name, '
         'date, link). The list is not collapsed in HTML &mdash; it lives inline so '
         'screen readers see it.'),
        ('Source chips, not stars.',
         'We never aggregate sources into a star rating. If aggregation is meaningful '
         '(e.g., 3 of 4 mention "tapas"), we render: <i>"3 of 4 sources call out '
         'tapas/small plates."</i>'),
        ('Date discipline.',
         'Sources show a date when available. If a source is &gt; 24 months old, it '
         'gets a faint "older source" caption.'),
    ], styles))

    story.append(Paragraph('8.6  Add / save actions', styles['h2']))
    story.extend(labeled_bullets([
        ('Primary: "Add to trip".',
         'Sandstone gold filled button on dark; brass on paper. 36&thinsp;px height '
         'on grid, 44&thinsp;px in detail panel. Always paired with a label.'),
        ('Secondary: heart-toggle save.',
         'Outline → fill on save. No "Saved!" toast; sidebar dot pulses (see §5.5).'),
        ('Tertiary: "Open" / "Share".',
         'Hairline outline buttons. "Open" handsoff to map or external; "Share" '
         'copies a shareable link in light-mode paper aesthetic.'),
    ], styles))

    story.append(Paragraph('8.7  Map-linked behavior', styles['h2']))
    story.extend(labeled_bullets([
        ('Hover to highlight.',
         'Hovering a card highlights its pin and dims unrelated pins (§5.7).'),
        ('Tap pin to open card detail.',
         'Same affordance as tapping the card itself; deep-linked.'),
        ('Travel-time chip.',
         'When in trip context, every card surfaces "12 min walk from your hotel" or '
         '"22 min from the Field Museum (your last stop)" if backend provides it. '
         'When not in trip context, this chip is omitted &mdash; never invented.'),
    ], styles))

    story.append(Paragraph('8.8  Compact vs expanded variants', styles['h2']))
    story.append(Paragraph(
        'Each card has two density modes: <b>compact</b> for grid contexts, and '
        '<b>expanded</b> for the detail drawer. The compact mode hides the why-pull-'
        'quote behind a "show why" link; the expanded mode renders it as the hero '
        'block. The trust strip is identical in both modes &mdash; never compressed '
        'into a single icon.',
        styles['body']))

    story.append(Paragraph('8.9  What the card system forbids', styles['h2']))
    story.append(Callout('Card anti-patterns', [
        '<b>No price-strikethrough.</b> We are not an aggregator.',
        '<b>No urgency badges.</b> No "limited", "popular", "going fast".',
        '<b>No "edited by AI" labels.</b> The card is the AI&rsquo;s output; if it is '
        'on screen, it is verified. Labels imply doubt.',
        '<b>No multi-color category badges.</b> Categories live in the meta strip as '
        'caption text, not as color-coded pills.',
        '<b>No "Recommended for you" pseudo-personalization.</b> We use the user&rsquo;s '
        'real preferences when we have them, or we say nothing.',
    ], kind='reject'))
    story.append(PageBreak())
