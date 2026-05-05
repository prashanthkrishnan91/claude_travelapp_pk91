"""Sections 1-4: Diagnosis, Competitive synthesis, Brand identity, Visual system."""

from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether,
)

from styles import (
    INK, ONYX, CARBON, PEN, GOLD, BRASS, PEARL, CREAM_TEXT, SAGE,
    AMBER, CORAL, MIST, RAIN, PAPER, INK_PAPER, SLATE, HAIRLINE,
    Callout, Swatch, swatch_grid, bullets, labeled_bullets, hr,
    small_table,
)
from layout import chapter_opener


# ---------------------------------------------------------------------------
# SECTION 1 — Design diagnosis
# ---------------------------------------------------------------------------
def build_section_1(story, styles):
    chapter_opener(story, '01', 'Design diagnosis',
                   'What the product risks becoming if visual work is handled '
                   'piecemeal &mdash; and what we must protect on the way to a '
                   'world-class concierge.',
                   styles)

    story.append(Paragraph('1.1  What the app risks becoming', styles['h2']))
    story.append(Paragraph(
        'The most realistic failure mode is not ugliness. It is the slow drift into '
        'a "competent travel SaaS dashboard" &mdash; clean, accessible, navigable, '
        'and emotionally inert. That product has no reason to exist next to Google '
        'Travel. The diagnosis below identifies the four drift vectors we must arrest '
        'before any decorative pass is allowed.',
        styles['body']))

    story.extend(labeled_bullets([
        ('Drift 1 — “Card grid as wallpaper.”',
         'Every surface becomes a 3-column grid of equal-weight cards. The user '
         'cannot tell what is editorial, what is verified, what is AI-generated, and '
         'what is a saved idea. Information hierarchy collapses into a checkerboard.'),
        ('Drift 2 — “Glow on hover.”',
         'The team mistakes neon hover states, gradient blobs, and soft shadows for '
         'luxury. The result feels like a 2021 crypto landing page, not a boutique '
         'concierge. Beauty-as-decoration without typographic restraint or content '
         'structure is the giveaway.'),
        ('Drift 3 — “Chatbot UI inside a travel app.”',
         'The AI Concierge is rendered as a generic chat panel with avatar bubbles. '
         'The verified card &mdash; the actual product &mdash; is buried in a scrollable '
         'message thread. The conversational scaffold dominates the result.'),
        ('Drift 4 — “Evidence theatre.”',
         'Trust signals are rendered as small green checkmarks tacked onto cards. '
         'They communicate “verified” the way a TLS padlock does &mdash; mute, '
         'commodity, defensive. They do not earn the price of the screen real estate.'),
    ], styles))

    story.append(Paragraph('1.2  What must be protected', styles['h2']))
    story.append(Callout('Non-negotiables inherited from the product', [
        '<b>Verified addable cards only.</b> A card that can be added to a trip must come '
        'from a Google Place verification &mdash; never an editorial extract, never an LLM '
        'paraphrase, never a Tavily snippet. Visual design must communicate this rather '
        'than obscure it.',
        '<b>Evidence honesty.</b> Reasons cite verifiable signals. If we lack evidence, '
        'we say so beautifully &mdash; we never invent a waterfront view, a Michelin '
        'mention, or a neighborhood claim.',
        '<b>Speed of return.</b> Cards must paint in &lt; 8&thinsp;s on first search, '
        '&lt; 1&thinsp;s on pool/follow-up. No animation, image fetch, or font load '
        'may block first paint of card content.',
        '<b>Card identity stability.</b> Follow-ups (“top 3”, “compare”, “best one”) reuse '
        'cards by identity key. Visual treatment must not re-issue, re-key, or re-fetch '
        'these cards.',
        '<b>The display ↔ supportingDetails ↔ whyPick contract.</b> The three fields stay '
        'aligned. UI shall not invent a new field that fragments this contract.',
    ], kind='protect'))

    story.append(Paragraph('1.3  Design debt to fix before polish', styles['h2']))
    story.append(Paragraph(
        'Polish on top of structural debt amplifies the debt. The following must be '
        'fixed inside the foundation phase before any decorative pass.',
        styles['body']))
    story.extend(labeled_bullets([
        ('No global token contract.',
         'Some surfaces still ship light-era Tailwind utility classes. Tokens must be '
         'CSS variables, with a single source of truth in <i>globals.css</i>, and a '
         'naming convention that survives a re-skin.'),
        ('Card shell variants are fragmented.',
         'Verified cards, AI Concierge cards, Saved Idea cards, and Itinerary cards each '
         'render through slightly different components. Reduce to one Card primitive with '
         'composable slots (media, identity, evidence, actions).'),
        ('Trust marks are not first-class.',
         'Verified-by-Google, source count, evidence quality, and weak-evidence states '
         'are scattered across components. They need a single TrustStrip primitive.'),
        ('Loading states are gray skeletons.',
         'Skeletons are correct but not concierge-grade. We need an editorial loading '
         'language: typeset placeholders, hairline pulses, deterministic order.'),
        ('Empty states are dead.',
         'Empty states currently say “no results” instead of doing the concierge’s job '
         '&mdash; offering a thoughtful next step, a refinement chip, or an admission '
         'that the data is thin in this neighborhood.'),
        ('Mobile is an afterthought.',
         'Several deep trip-detail pages are desktop-first. The luxury concierge feeling '
         'must work on a phone in a hotel lobby with one thumb.'),
    ], styles))

    story.append(Paragraph(
        '1.4  Where design can amplify the AI Concierge instead of distract',
        styles['h2']))
    story.append(Paragraph(
        'Design earns its place when it makes the intelligence <i>legible</i>. '
        'The four amplification moves below cost nothing in latency and pay back '
        'every interaction.',
        styles['body']))
    story.extend(labeled_bullets([
        ('Make the verified card the hero of the chat.',
         'The card, not the bubble, owns the visual weight. The conversation thread '
         'is a slim left rail of intent &mdash; the right side is the editorial result.'),
        ('Render reasoning as quotation, not chrome.',
         '“Why this fits” is a typeset pull-quote with a small evidence tag, not an icon. '
         'It tells the user what the system noticed without exposing pipelines.'),
        ('Communicate uncertainty as a feature.',
         'When evidence is thin, render a beautiful weak-evidence card with an explicit '
         '“verify when booking” line. Honesty becomes a luxury cue.'),
        ('Compose the thinking state.',
         'Replace the spinner with a typeset “searching · verifying · composing” '
         'breadcrumb that matches the actual pipeline stages logged by '
         '<i>fast_dynamic_place_search.timing</i>.'),
    ], styles))
    story.append(PageBreak())


# ---------------------------------------------------------------------------
# SECTION 2 — Competitive synthesis
# ---------------------------------------------------------------------------
def build_section_2(story, styles):
    chapter_opener(story, '02', 'Competitive synthesis',
                   'What to learn, what to reject, and what we can do better than '
                   'every reference product.',
                   styles)

    story.append(Paragraph(
        'Every reference below is studied for one thing: the smallest pattern we can '
        'borrow without inheriting its limitations. Generic praise (“Airbnb is clean”) '
        'is forbidden in this chapter.',
        styles['lead']))

    refs = [
        ('Airbnb',
         [
            'Information density per card is exceptional. Photo-first hierarchy with '
            'price + rating + neighborhood as a tight metadata strip.',
            'Map ↔ list co-presence on desktop with a sticky-pan filter that does not '
            'requery on tiny pan deltas.',
            'Calendar UI handles flex dates gracefully without modal hell.',
         ],
         [
            'The “Rare Finds / Luxe” category split is hand-curated marketing. We will '
            'not copy categories that imply editorial human review we do not have.',
            'The hero gallery on a listing page is so dominant it crowds out trust '
            'evidence. We will keep media restrained on verified cards.',
            'Recent dark-mode and Stays/Experiences toggles feel like SaaS chrome on '
            'top of editorial photography. We avoid that collision by committing to '
            'one tonal mode per surface.',
         ],
         'Borrow the metadata strip rhythm. Reject the photo-as-everything hierarchy. '
         'Beat them on evidence: where Airbnb shows star ratings, we show structured '
         '“why this fits” with sources.'),

        ('Expedia',
         [
            'Multi-leg flight + hotel + car bundling logic is the strongest in the '
            'industry. The data model exposes price-by-component cleanly.',
            'Filter chips persist across a session and restore from URL state.',
         ],
         [
            'The visual language is loud and promotional &mdash; banners, sale badges, '
            'urgency timers. We will not import any of it.',
            'Comparison views become spreadsheet-grade dense. Boutique users bounce.',
         ],
         'Borrow the URL-stateful filter pattern for Explore. Reject the ad-banner '
         'aesthetic outright. Beat them on calm: the absence of "only 3 left!" is the '
         'design statement.'),

        ('Booking.com',
         [
            'Price transparency is excellent &mdash; total-with-fees is shown by default '
            'in many regions.',
            'Map clusters degrade gracefully at low zoom.',
         ],
         [
            'Dark patterns: scarcity messaging, “85 people viewing now”, color-coded '
            'urgency. Forbidden.',
            'Hyper-saturated blues and yellows that telegraph “discount aggregator”.',
         ],
         'Borrow the all-in price honesty norm and the map cluster behavior. Beat them '
         'on dignity: no scarcity theatre, ever.'),

        ('Tripadvisor',
         [
            'User reviews aggregate at scale and make “consensus quality” a useful '
            'signal even when individual reviews are noisy.',
            '“Things to do” taxonomy is a useful POI ontology.',
         ],
         [
            'Visual identity is undifferentiated &mdash; green-on-white, ad-driven.',
            'Editorial voice has been worn down to advertorial. Trust is leaking.',
         ],
         'Borrow the consensus aggregation idea, but render it as our own evidence ladder '
         '(see §9). Reject the advertorial voice. Beat them on voice: a concierge that '
         'sounds like a person, not a feed.'),

        ('Google Travel &amp; Google AI travel planning',
         [
            'Map-first navigation; instant zoom-to-pin; the place panel is the highest-'
            'fidelity POI surface in production.',
            'AI itinerary surfaces (Bard / Gemini) cite sources inline and let users '
            'edit a structured plan.',
         ],
         [
            'Surfaces are emotionally cold. The product is a utility, not an experience.',
            'Cards have no “personality” &mdash; they are extractive panels of GMB data.',
            'AI-generated plans collapse into bulleted text without addable identity.',
         ],
         'Borrow the place-panel fidelity for our verified card detail. Reject the cold '
         'utility tone. Beat them on warmth: the same data, dressed for evening.'),

        ('Kayak / Hopper / Skyscanner',
         [
            'Calendar heatmaps, price-prediction indicators, and flexible-month grids.',
            'Multi-airport selection patterns and inline error messages.',
         ],
         [
            'Loud color-coded prediction badges that turn the screen into a casino.',
            'In Hopper specifically, the mascot-driven UI is too whimsical for our brand.',
         ],
         'Borrow the calendar-heatmap mental model for trip-date suggestions. Reject the '
         'casino color palette. Beat them on calm: a single typographic price-trend line.'),

        ('Mr &amp; Mrs Smith / Belmond / boutique luxury sites',
         [
            'Editorial photography commitment: full-bleed images shot for the brand, '
            'never stock. Type pairing of a serif display with a clean sans body.',
            '“Insider” voice &mdash; first-person, knowing, uncluttered.',
         ],
         [
            'Booking flows are often anaemic on these sites. They optimize for awe, '
            'not for trip planning.',
            'Mobile experiences are sometimes sacrificed to art-directed desktop hero '
            'sequences.',
         ],
         'Borrow the type pairing, the insider voice, the photographic commitment. '
         'Beat them on utility: we will not let the editorial layer slow trip planning '
         'by a single second.'),

        ('Awwwards luxury hospitality &amp; AI-first planners',
         [
            'Custom cursor work, scroll-driven storytelling, restrained color systems, '
            'serif-display typography.',
            'AI-first planners (e.g., Layla, Wonderplan, Mindtrip) experiment with '
            'inline card-in-chat patterns.',
         ],
         [
            'Most are demo-grade. Performance, accessibility, and content depth are '
            'frequently sacrificed for the showreel.',
            'AI planners often invent reasons. They are exactly what we must not become.',
         ],
         'Borrow the typographic discipline and the inline card-in-chat shape. Reject '
         'every performance-sacrificing flourish. Beat them on substance: we will be '
         'the AI planner that <i>cites its sources</i>.'),
    ]

    for name, learn, reject, beat in refs:
        story.append(Paragraph(name, styles['h2']))
        story.append(Paragraph('What to learn', styles['h4']))
        for it in learn:
            story.append(Paragraph(u'•  ' + it, styles['bullet']))
        story.append(Paragraph('What to reject', styles['h4']))
        for it in reject:
            story.append(Paragraph(u'•  ' + it, styles['bullet']))
        story.append(Paragraph('How Travel Concierge wins', styles['h4']))
        story.append(Paragraph(beat, styles['body']))
        story.append(hr())

    story.append(Paragraph('2.9  Patterns we synthesize across the field', styles['h2']))
    story.extend(labeled_bullets([
        ('Map ↔ list parity.',
         'Adopted from Airbnb, Google. We treat the map as a first-class twin of the '
         'list, not a popup. Filter changes update both atomically.'),
        ('Inline citations.',
         'Adopted from Google AI; we show source provenance under every reason chip.'),
        ('Editorial typography.',
         'Adopted from Mr &amp; Mrs Smith and Awwwards; serif display + restrained '
         'sans body, never both serif.'),
        ('All-in pricing posture.',
         'Adopted from Booking; price honesty becomes a brand signal.'),
        ('Calendar heatmap mental model.',
         'Adopted from Kayak; we use it sparingly to suggest cheaper trip windows '
         'when we have provider data, never as urgency.'),
    ], styles))
    story.append(PageBreak())


# ---------------------------------------------------------------------------
# SECTION 3 — Brand and experience identity
# ---------------------------------------------------------------------------
def build_section_3(story, styles):
    chapter_opener(story, '03', 'Brand and experience identity',
                   'The product personality, voice, and emotional bar &mdash; in '
                   'concrete, testable terms.',
                   styles)

    story.append(Paragraph('3.1  Emotional tone', styles['h2']))
    story.append(Paragraph(
        'Walking into a small, candle-lit travel atelier on a side street. The owner '
        'remembers your last trip, has the right book on the shelf, and never raises '
        'their voice. Confidence without showmanship. Warmth without sweetness. '
        'Speed without urgency.',
        styles['quote']))

    story.append(Paragraph('3.2  Product personality', styles['h2']))
    rows = [
        ['Trait', 'Means', 'Does not mean'],
        ['Boutique',  'Hand-feel; restraint; specific choices',
                      'Niche, exclusionary, esoteric'],
        ['Editorial', 'Voice; typographic care; long-form when warranted',
                      'Magazine pastiche, cover lines, splash images on every screen'],
        ['Concierge', 'Anticipatory; remembers context; offers next-best-action',
                      'Servile, fawning, scripted'],
        ['Honest',    'Cites evidence; admits weak signal; shows uncertainty',
                      'Self-flagellating; over-apologizing; “as an AI I cannot…”'],
        ['Quiet',     'Calm motion; no urgency; no shouting',
                      'Sleepy, slow, lacking opinion'],
        ['Generous',  '“Worth-the-splurge” + “luxury-for-less” equally weighted',
                      'Couponing, deal-bait, fake markdowns'],
    ]
    story.append(small_table(rows, [1.1*inch, 3.0*inch, 2.8*inch], styles))

    story.append(Paragraph('3.3  Visual language headline', styles['h2']))
    story.extend(labeled_bullets([
        ('Tonal duality.', 'Two surfaces only: <b>Midnight Ink</b> for the app shell, '
         'concierge thinking, and the AI surface; <b>Warm Paper</b> for itineraries, '
         'saved scrapbooks, and shareable trip artefacts. Never both at once.'),
        ('Type as identity.', 'A display serif with personality (e.g., Tiempos Headline, '
         'Editorial New, GT Super Display, or self-hosted equivalents) paired with a '
         'humanist sans (e.g., Söhne, Inter, or system-ui) for body. No third family.'),
        ('Photograph or no image.',
         'Where we can show a real photograph, we go full-bleed and edge-to-content. '
         'Where we cannot, we never put a stock image on screen &mdash; we typeset.'),
        ('Hairline geometry.',
         'Borders, dividers, table rules sit at 0.4&ndash;0.6&thinsp;px. The grid is '
         'felt, not seen.'),
        ('Light as lacquer, not as glow.',
         'A single subtle radial highlight on raised surfaces in dark mode. No glow on '
         'hover; the cursor is the highlight.'),
    ], styles))

    story.append(Paragraph('3.4  Interaction language', styles['h2']))
    story.extend(labeled_bullets([
        ('Direct manipulation over modal forms.',
         'Drag a card to a day. Tap a chip to refine. Long-press to compare. Modals '
         'only for legally distinct actions (sign out, delete trip).'),
        ('Persistence is a vibe.',
         'Filters, scroll positions, and prompt history survive page transitions. The '
         'concierge does not forget what you asked five seconds ago.'),
        ('Two-finger generosity on mobile.',
         'Every primary action is reachable by the right thumb. Secondary actions live '
         'in a tap-to-reveal sheet, not in a hamburger.'),
        ('Keyboard for power users.',
         'k = open command bar; ⌘K opens AI Concierge from anywhere; / focuses search; '
         'esc closes any drawer. Keyboard shortcuts are <i>complementary</i>, not '
         'required.'),
    ], styles))

    story.append(Paragraph('3.5  Content voice', styles['h2']))
    story.append(Paragraph(
        'A first-person concierge who has been to the city, knows what the user means '
        'when they say “tapas bar,” and is too dignified to upsell. We write as if a '
        'real person is composing each line.',
        styles['body']))
    rows = [
        ['Use', 'Avoid'],
        ['"A stronger tapas/small-plates match than the cocktail bar around the corner."',
         '"Highly rated! Top pick! Don\'t miss out!"'],
        ['"Worth booking ahead on weekends — it fills early."',
         '"Limited availability — only 3 spots left!"'],
        ['"We could not verify the waterfront view; ask when booking."',
         '"Stunning waterfront views!" (when unverified)'],
        ['"You saved three hidden gems in River North."',
         '"You\'ve unlocked the River North expert badge 🎉"'],
        ['"This is closer to your hotel than the others by ~12 minutes on foot."',
         '"OMG so close!! 😍"'],
    ]
    story.append(small_table(rows, [3.5*inch, 3.4*inch], styles))

    story.append(Paragraph('3.6  Trust language', styles['h2']))
    story.extend(labeled_bullets([
        ('“Verified by Google.”',
         'Used only when we have a stable Google Place ID and OPERATIONAL status. '
         'Never as decoration.'),
        ('“Reviews aggregated from N sources.”',
         'A small numeric strip with a link to expand the source list. Never a fake '
         'aggregate score.'),
        ('“Confidence: high / medium / low” mapped to evidence count.',
         'High = 3+ corroborating sources; Medium = 2; Low = 1 + verified place. The '
         'language is plain English, not a numeric percentile.'),
        ('“We could not verify…”',
         'A first-class sentence pattern. It appears as a typeset caveat under any '
         'reason that includes a constraint we did not confirm.'),
    ], styles))

    story.append(Paragraph('3.7  Luxury-for-less positioning', styles['h2']))
    story.append(Paragraph(
        'The brand is not “cheap luxury”. It is <i>known luxury</i>: we know which '
        'splurges return value and which do not. The product surfaces this through '
        'two recurring chips on cards.',
        styles['body']))
    story.extend(labeled_bullets([
        ('“Worth the splurge.”',
         'Applied only when the verified place has a meaningfully higher price band and '
         'corroborating evidence of a notable experience. Never on a generic mid-tier place.'),
        ('“Luxury for less.”',
         'Applied when a verified place delivers a high-end experience at a notably '
         'lower price band than peers in the same neighborhood. Both chips use the '
         'same sandstone gold accent &mdash; siblings, not rivals.'),
    ], styles))

    story.append(Paragraph('3.8  What the app must never feel like', styles['h2']))
    story.append(Callout('Anti-patterns the brand forbids', [
        '<b>OTA aggregator.</b> No "Best price guarantee", no countdown timers, no '
        '"Lowest prices in 24 hours" badges.',
        '<b>SaaS dashboard.</b> No KPI tiles, sparklines, "completion percentage" rings, '
        'or productivity-app empty states.',
        '<b>Crypto landing page.</b> No animated gradient meshes, no neon hover glows, '
        'no glitch type, no “ETA: live data” chips.',
        '<b>Generic chatbot.</b> No animated thinking dots inside speech bubbles, no '
        'avatar with cute facial expressions, no “Hi! I\'m your AI assistant!” opener.',
        '<b>Gamified app.</b> No streaks, no XP, no badges, no level-up modals, no '
        'confetti, ever.',
        '<b>Stock-photo magazine.</b> No generic “sunset over a city” hero. Either we '
        'have a real verified-place photo or we typeset.',
    ], kind='reject'))
    story.append(PageBreak())


# ---------------------------------------------------------------------------
# SECTION 4 — Visual system
# ---------------------------------------------------------------------------
def build_section_4(story, styles):
    chapter_opener(story, '04', 'Visual system',
                   'A complete token-level visual direction: dark-primary, '
                   'paper-secondary, with motion-aware surfaces and accessible '
                   'contrast guarantees.',
                   styles)

    # ---- 4.1 Dark mode (primary)
    story.append(Paragraph('4.1  Dark mode (primary system)', styles['h2']))
    story.append(Paragraph(
        'Dark mode is the canonical canvas. It hosts the AI Concierge, Explore, the '
        'shell, and any surface where the product is <i>composing for</i> the user. '
        'It is built from a five-step ink ladder, not a single black.',
        styles['body']))
    dark_swatches = [
        [
            ('Midnight Ink',  '#0B1320', 'page background',           INK),
            ('Onyx Velvet',   '#0F1A2C', 'surface',                   ONYX),
            ('Carbon Mist',   '#1A2538', 'raised surface',            CARBON),
        ],
        [
            ('Pen Stroke',    '#22324A', 'divider',                   PEN),
            ('Sandstone Gold','#E0B888', 'primary accent',            GOLD),
            ('Ember Brass',   '#C5944D', 'deep accent',               BRASS),
        ],
        [
            ('Pearl Cream',   '#F2EBDD', 'headline text',             PEARL),
            ('Cream',         '#E8E2D4', 'body text',                 CREAM_TEXT),
            ('Mist',          '#9AA4B2', 'subdued text',              MIST),
        ],
        [
            ('Verified Sage', '#88A899', 'trust signal',              SAGE),
            ('Caution Amber', '#E8B26B', 'soft caution',              AMBER),
            ('Whisper Coral', '#D88478', 'gentle warning',            CORAL),
        ],
    ]
    story.append(swatch_grid(dark_swatches))
    story.append(Paragraph(
        'Every surface uses one ink for background, one ink one step lighter for the '
        'card, and one ink one step lighter again for the raised state. No more, no '
        'less. Cards on cards on cards is the killer of dark UI.',
        styles['caption']))

    # ---- 4.2 Light mode
    story.append(Paragraph('4.2  Light mode (secondary system)', styles['h2']))
    story.append(Paragraph(
        'Light mode is the <i>artefact</i> mode &mdash; trip itineraries that someone '
        'might print or screenshot to share, the saved-ideas scrapbook, and the user '
        'profile. It is warm paper, not stark white.',
        styles['body']))
    paper_swatches = [
        [
            ('Warm Paper',   '#FAF7F0', 'page background',     PAPER),
            ('Bone',         '#F1ECE0', 'surface',             None),
            ('Linen',        '#E6DECB', 'raised surface',      None),
        ],
        [
            ('Hairline',     '#D9D2C2', 'divider',             HAIRLINE),
            ('Slate',        '#4A5568', 'secondary text',      SLATE),
            ('Ink Paper',    '#1F2530', 'body text',           INK_PAPER),
        ],
        [
            ('Brass',        '#C5944D', 'accent',              BRASS),
            ('Sage',         '#88A899', 'trust',               SAGE),
            ('Coral',        '#D88478', 'warning',             CORAL),
        ],
    ]
    # Quick fix for the None colors above:
    from reportlab.lib.colors import HexColor as _H
    paper_swatches[0][1] = ('Bone', '#F1ECE0', 'surface', _H('#F1ECE0'))
    paper_swatches[0][2] = ('Linen', '#E6DECB', 'raised surface', _H('#E6DECB'))
    story.append(swatch_grid(paper_swatches))

    # ---- 4.3 Color roles, not random colors
    story.append(Paragraph('4.3  Color roles, not random colors', styles['h2']))
    rows = [
        ['Role token', 'Dark mode', 'Light mode', 'Used for'],
        ['--surface-0',     'Midnight Ink',  'Warm Paper',   'Page canvas'],
        ['--surface-1',     'Onyx Velvet',   'Bone',         'Default cards'],
        ['--surface-2',     'Carbon Mist',   'Linen',        'Raised cards / drawers'],
        ['--divider',       'Pen Stroke',    'Hairline',     'Hairline borders, table rules'],
        ['--text-strong',   'Pearl Cream',   'Ink Paper',    'Headlines'],
        ['--text-body',     'Cream',         'Slate',        'Body copy'],
        ['--text-mute',     'Mist',          'Slate@70%',    'Captions, timestamps'],
        ['--accent',        'Sandstone Gold','Brass',        'Primary CTAs, "Add to trip"'],
        ['--accent-deep',   'Ember Brass',   'Brass-deep',   'Hover/pressed accent'],
        ['--trust',         'Verified Sage', 'Sage',         '"Verified by Google" mark'],
        ['--caution',       'Caution Amber', 'Amber',        'Weak-evidence chip'],
        ['--warn',          'Whisper Coral', 'Coral',        'Booking caveat, blocked action'],
    ]
    story.append(small_table(rows,
                             [1.45*inch, 1.4*inch, 1.4*inch, 2.65*inch], styles))

    # ---- 4.4 Typography
    story.append(Paragraph('4.4  Typography roles', styles['h2']))
    story.append(Paragraph(
        'Two families. One serif display, one humanist sans. A monospace for '
        'evidence/code/IDs only. No third family. Sizes climb a 1.25 modular scale '
        'anchored at 16&thinsp;px body.',
        styles['body']))
    rows = [
        ['Role', 'Family', 'Size / Leading', 'Use'],
        ['Display XL',     'Serif Display', '64 / 68', 'Cover hero, landing'],
        ['Display L',      'Serif Display', '44 / 50', 'Page hero / section title'],
        ['Display M',      'Serif Display', '32 / 38', 'Card detail title'],
        ['Display S',      'Serif Display', '24 / 30', 'Section title in card'],
        ['Body L',         'Sans',          '18 / 28', 'Lead paragraph'],
        ['Body',           'Sans',          '15 / 24', 'Default body'],
        ['Body S',         'Sans',          '13 / 20', 'Card metadata, list rows'],
        ['Caption',        'Sans',          '12 / 16', 'Trust marks, timestamps'],
        ['Overline',       'Sans (caps, +tracking)', '10 / 14', 'Section labels'],
        ['Mono',           'Mono',          '12 / 16', 'Identity keys, debug only'],
        ['Quote',          'Serif Italic',  '18 / 28', 'Concierge reasoning quotes'],
    ]
    story.append(small_table(rows, [1.05*inch, 1.6*inch, 1.2*inch, 3.05*inch], styles))

    # ---- 4.5 Spacing
    story.append(Paragraph('4.5  Spacing rhythm', styles['h2']))
    story.append(Paragraph(
        'A single 4&thinsp;px base unit, with semantic tokens above it. Hairlines and '
        'borders sit on a 1&thinsp;px grid; everything else snaps to 4.',
        styles['body']))
    rows = [
        ['Token', 'Pixels', 'Usage'],
        ['--space-1',  '4',  'Sub-icon padding'],
        ['--space-2',  '8',  'Default chip padding, inline gap'],
        ['--space-3',  '12', 'Card metadata gap'],
        ['--space-4',  '16', 'Card padding (compact)'],
        ['--space-5',  '20', 'Card padding (default)'],
        ['--space-6',  '24', 'Section gap'],
        ['--space-8',  '32', 'Heading-to-content gap'],
        ['--space-10', '40', 'Card-to-card gap on Explore'],
        ['--space-12', '48', 'Hero block padding'],
        ['--space-16', '64', 'Page-edge gutter (desktop)'],
    ]
    story.append(small_table(rows, [1.0*inch, 0.7*inch, 5.2*inch], styles))

    # ---- 4.6 Elevation
    story.append(Paragraph('4.6  Card elevation system', styles['h2']))
    story.append(Paragraph(
        'In dark mode, elevation is achieved by stepping up the ink ladder, never by '
        'increasing shadow softness. In light mode, elevation is achieved with hairline '
        'borders and a 2&thinsp;%-luminance surface lift, not drop shadows.',
        styles['body']))
    rows = [
        ['Level', 'Dark mode', 'Light mode', 'Use'],
        ['e0',  'Surface 0',                       'Paper',                          'Page canvas'],
        ['e1',  'Surface 1 + 0.4&thinsp;px border','Bone + 0.4&thinsp;px border',    'Default card'],
        ['e2',  'Surface 2 + 1&thinsp;px border',  'Linen + 1&thinsp;px border',     'Hovered/active card'],
        ['e3',  'Surface 2 + soft 8&thinsp;px shadow @ 18% black', 'Linen + 8&thinsp;px shadow @ 6%', 'Drawer, modal'],
        ['e4',  'Surface 2 + 16&thinsp;px shadow @ 24% black',     'Linen + 16&thinsp;px shadow @ 10%', 'Floating composer'],
    ]
    story.append(small_table(rows, [0.55*inch, 2.3*inch, 2.0*inch, 2.05*inch], styles))

    # ---- 4.7 Borders, shadows, glass, texture
    story.append(Paragraph('4.7  Borders, shadows, glass, texture, gradients', styles['h2']))
    story.extend(labeled_bullets([
        ('Borders.', 'Always 0.4&ndash;1&thinsp;px hairlines. Token: <i>--divider</i>. '
         'Border-radius scale: 4 (chip), 8 (card), 12 (drawer), 16 (modal). No 24+; '
         'we are not a soft-toy app.'),
        ('Shadows.', 'Used sparingly, only on e3/e4. Two-stop: a tight 1&thinsp;px '
         'shadow for crispness, plus a soft 12&ndash;24&thinsp;px shadow for atmosphere. '
         'Shadows are warmer (slightly brass-tinted) in dark mode.'),
        ('Glass.', 'One use only: the AI Concierge composer floating over a destination '
         'photo on landing. <i>backdrop-filter: blur(22&thinsp;px) saturate(140%)</i>. '
         'Forbidden everywhere else &mdash; it kills mobile performance and hides text.'),
        ('Texture.', 'A 1&thinsp;%-opacity film grain layer is permitted on the landing '
         'and login page only, baked into a single SVG, no JS animation.'),
        ('Gradients.', 'Two permitted: a vertical ink-fade behind the AI Concierge '
         'thinking state, and a 2-stop sandstone-to-brass on the primary CTA hover. '
         'Banned: 4+ stop conic gradients, neon edges, animated mesh.'),
    ], styles))

    # ---- 4.8 Iconography
    story.append(Paragraph('4.8  Iconography', styles['h2']))
    story.append(Paragraph(
        'Single-weight 1.5&thinsp;px stroke, 24&thinsp;px grid, rounded joins, no '
        'fills except for filled "saved" states. Source: Lucide or Phosphor; never '
        'mix two icon libraries on one screen. Icons never carry semantic meaning '
        'alone &mdash; always paired with a label or aria-label.',
        styles['body']))

    # ---- 4.9 Map styling
    story.append(Paragraph('4.9  Map styling direction', styles['h2']))
    story.extend(labeled_bullets([
        ('Two map themes, both ours.',
         'Dark map: deep ink with brass roads and sage parks. Paper map: cream with '
         'umber roads and sage parks. Both lower-saturation than default Google.'),
        ('Pins as identity, not as decoration.',
         'A verified place pin is a small filled circle in sandstone gold; a hovered '
         'pin gains a 1.5x ring. Saved places get a hairline ring around the pin.'),
        ('Cluster typography.',
         'Cluster counts are typeset in the same humanist sans as the app, never '
         'a system default.'),
        ('Density discipline.',
         'Show at most 30 pins on screen. Beyond that, cluster. Never paint a swarm.'),
    ], styles))

    # ---- 4.10 Image treatment
    story.append(Paragraph('4.10  Image treatment', styles['h2']))
    story.extend(labeled_bullets([
        ('Aspect ratios.', '4:5 portrait for verified place hero; 3:2 landscape for '
         'Explore covers; 1:1 square for Saved Idea thumbnails. No 16:9 unless we are '
         'showing a video clip we control.'),
        ('Edges.', 'All images sit inside the card; we never bleed them to the page edge '
         'except on the cover/landing hero.'),
        ('Treatment.',
         'A subtle 4% midnight-ink overlay in dark mode for legibility of overlaid '
         'metadata; never a vignette, never a photo filter that distorts color.'),
        ('Fallbacks.',
         'No stock photos, ever. If we have no photo, we typeset. The card surfaces a '
         'monogram letter in serif display + a tonal background derived from the '
         'place type.'),
        ('Loading.',
         'Images load progressively: tonal background → blurred low-res → full. Card '
         'content paints before the image &mdash; the user reads the reason first.'),
    ], styles))

    # ---- 4.11 Empty/loading/error
    story.append(Paragraph('4.11  Empty, loading, and error states', styles['h2']))
    story.extend(labeled_bullets([
        ('Empty: a sentence, then a refinement.',
         '“Nothing matches <i>%s</i> in this neighborhood yet. Try widening to %s, or ask '
         'for a different cuisine.” Always include two clickable refinements derived '
         'from the prior search.'),
        ('Loading: a typeset breadcrumb.',
         '<i>Searching · Verifying · Composing</i>, with the active stage in pearl '
         'cream and inactive stages in mist. Progress is real (driven by '
         '<i>fast_dynamic_place_search.timing</i>), not theatre.'),
        ('Error: name the cause, offer a path.',
         '“The Google Places verifier is unavailable. We will retry; meanwhile, here '
         'are your saved places.” No stack traces, no “Oops!” cartoons.'),
        ('Skeletons: typed, not gray.',
         'Card skeletons render the actual card geometry with hairline outlines; the '
         'place name is a 60&thinsp;%-width typeset bar, not a flat rectangle.'),
    ], styles))

    # ---- 4.12 Responsiveness & a11y
    story.append(Paragraph('4.12  Mobile responsiveness principles', styles['h2']))
    story.extend(labeled_bullets([
        ('Three breakpoints only.',
         'Phone (&lt; 640&thinsp;px), tablet (640&ndash;1024), desktop (≥ 1024). No '
         'between-breakpoint adjustments.'),
        ('Right-thumb reachability.',
         'Primary actions sit in the bottom 25&thinsp;% on phone, never in a fixed top '
         'app-bar pill.'),
        ('AI Concierge as a sheet, not a page, on mobile.',
         'It opens as a 90vh bottom sheet that can be dragged closed. The composer is '
         'always visible.'),
        ('Map → list precedence.',
         'On phone, list is default; map is reachable through a single chip. We do '
         'not split the screen 50/50 on phones.'),
    ], styles))

    story.append(Paragraph('4.13  Accessibility constraints', styles['h2']))
    story.extend(labeled_bullets([
        ('Contrast.',
         'All text passes WCAG 2.2 AA at the rendered size. Pearl Cream on Midnight Ink '
         '≈ 13.4:1; Cream on Onyx ≈ 11.2:1. We test every accent on both surfaces.'),
        ('Focus.',
         'A 2&thinsp;px sandstone-gold focus ring with 2&thinsp;px offset on every '
         'interactive element. Never <i>outline: none</i>.'),
        ('Motion.',
         '<i>prefers-reduced-motion</i> disables all entrance animations and reduces '
         'durations to ≤ 80&thinsp;ms.'),
        ('Hit area.',
         '44&times;44&thinsp;px minimum on touch. Chips have invisible padding to '
         'reach this without inflating visual size.'),
        ('Text resizing.',
         'Layout survives 200&thinsp;% browser zoom without horizontal scroll.'),
        ('Color is never the only signal.',
         'Trust marks pair sage with a label; weak-evidence pairs amber with the '
         'phrase “We could not verify…”.'),
    ], styles))
    story.append(PageBreak())
