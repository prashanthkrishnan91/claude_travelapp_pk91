"""Sections 9-13 + Appendix: Evidence, Personalization, Roadmap, Guardrails,
First implementation slice, Glossary."""

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
# SECTION 9 — Evidence and trust UX
# ---------------------------------------------------------------------------
def build_section_9(story, styles):
    chapter_opener(story, '09', 'Evidence and trust UX',
                   'How evidence appears beautifully, honestly, and without '
                   'fake precision.',
                   styles)

    story.append(Paragraph(
        'Evidence is the brand. Other AI travel planners hide their reasoning behind '
        'fluent prose; Travel Concierge surfaces it. The design challenge is to make '
        'evidence look like editorial pull-quotes, not legal disclaimers.',
        styles['lead']))

    story.append(Paragraph('9.1  The evidence ladder', styles['h2']))
    story.append(Paragraph(
        'A four-rung ladder maps backend confidence to a UI treatment. The ladder is '
        'the only mapping; no surface invents its own.',
        styles['body']))
    rows = [
        ['Rung', 'Backend signal', 'UI treatment', 'Voice example'],
        ['Verified place + 3+ sources',
         'Google Place ID OPERATIONAL + ≥ 3 corroborating sources matching the user constraint',
         '"Verified by Google" + sage source-count chip + serif why-quote',
         '"A stronger tapas/small-plates match than the cocktail bar around the corner."'],
        ['Verified place + 2 sources',
         'Google Place ID OPERATIONAL + 2 corroborating sources',
         '"Verified by Google" + neutral source-count chip',
         '"Fits the tapas brief with a dinner-date feel in River North."'],
        ['Verified place, weak constraint',
         'Google Place ID OPERATIONAL but the user-supplied constraint (e.g., '
         '"waterfront view") is not corroborated',
         '"Verified by Google" + caution-amber chip "Constraint not verified"',
         '"Best fit if you want sushi with a polished setting near waterfront; '
         'verify exact seating when booking."'],
        ['Place not verified',
         'No stable Google Place ID, or NOT_OPERATIONAL',
         'Card is not addable; treated as editorial reference only',
         '"Mentioned in two recent guides; we could not verify it as an operating '
         'venue tonight."'],
    ]
    story.append(small_table(rows,
                             [1.55*inch, 1.85*inch, 1.85*inch, 1.65*inch], styles))

    story.append(Paragraph('9.2  "Verified by Google" mark', styles['h2']))
    story.extend(labeled_bullets([
        ('Where it sits.',
         'Top-left of every verified card, above the place name. Caption-grade typography.'),
        ('What it looks like.',
         'A 12&thinsp;px sage filled circle + 8&thinsp;px sage caps overline '
         '"VERIFIED BY GOOGLE". Not an icon-only badge; the words matter.'),
        ('What it never means.',
         'It does not mean "we recommend this place". It does not mean "Google '
         'recommends this place". It means: a stable Google Place ID exists and the '
         'business is OPERATIONAL.'),
    ], styles))

    story.append(Paragraph('9.3  Source counts', styles['h2']))
    story.extend(labeled_bullets([
        ('Display.',
         '"3 sources" rendered as a typographic chip with a hairline outline. Tap to '
         'expand the inline source list.'),
        ('Source list.',
         'Each row: publication name + date + 1-line snippet that supports the claim. '
         'Snippets are extractive, never paraphrased.'),
        ('Threshold.',
         'We display the count starting at 1. We do not hide low source counts; '
         'transparency over flattering numbers.'),
    ], styles))

    story.append(Paragraph('9.4  Evidence quality (confidence chip)', styles['h2']))
    story.append(Paragraph(
        'A second small chip: <i>Confidence: high / medium / low</i>. It is plain '
        'English. We never show a number like "92% confidence" because we cannot '
        'defend the precision.',
        styles['body']))
    rows = [
        ['Chip', 'Backend rule (illustrative)', 'Color'],
        ['Confidence: high',   '≥ 3 sources + place verified + constraint corroborated',
         'sage'],
        ['Confidence: medium', '2 sources + place verified',
         'sandstone gold (no fill)'],
        ['Confidence: low',    '1 source + place verified, OR ≥ 1 unverified constraint',
         'caution amber'],
    ]
    story.append(small_table(rows, [1.55*inch, 4.2*inch, 1.15*inch], styles))

    story.append(Paragraph('9.5  "Why it fits" pull-quotes', styles['h2']))
    story.append(Paragraph(
        'The why-quote is the editorial heart of the card. It is rendered in serif '
        'italic, 16&thinsp;px on grid / 18&thinsp;px in detail. It uses '
        'curly quotes. It cites a source tag. It never paraphrases the backend '
        'reason; it shows it verbatim with hairline-styled quotation marks.',
        styles['body']))
    story.append(Paragraph(
        '“A stronger tapas/small-plates match than a generic cocktail bar in West '
        'Loop.” &mdash; <i>verified place, dynamic match</i>',
        styles['quote']))

    story.append(Paragraph('9.6  "Best for" tags', styles['h2']))
    story.append(Paragraph(
        'A small caps overline above the place name: <i>BEST FOR · DINNER DATES</i>, '
        '<i>BEST FOR · GROUPS OF 4-6</i>. These tags come only from corroborated '
        'evidence; we never invent them. If we have no evidence to support a "best '
        'for" tag, we omit the slot entirely.',
        styles['body']))

    story.append(Paragraph('9.7  Caveats', styles['h2']))
    story.append(Paragraph(
        'The caveat slot is a <i>typeset sentence</i>, not an icon. It uses caution '
        'amber for the leading word and ink/pearl for the rest of the line. Examples:',
        styles['body']))
    story.extend(labeled_bullets([
        ('"Verify when booking &mdash;', 'we could not confirm the waterfront view.'),
        ('"Older sources &mdash;', 'two reviews are from 2022; menu may have shifted.'),
        ('"Limited evidence &mdash;', 'one independent source; we trust the verification, '
         'less so the vibe.'),
    ], styles))

    story.append(Paragraph('9.8  Weak evidence', styles['h2']))
    story.append(Callout('How to communicate weakness as a feature', [
        '<b>Render the card.</b> Do not hide it. The user wants to know what is close '
        'to the brief.',
        '<b>Promote the caveat.</b> The amber sentence sits directly under the trust '
        'strip, before the why-quote. It earns its place.',
        '<b>Reduce the why-quote prominence.</b> Render at compact size; do not promote '
        'it to detail-panel hero.',
        '<b>Offer a refinement chip.</b> "Find places with stronger waterfront '
        'evidence" appears below the card, generated from the negative constraint.',
    ], kind='opportunity'))

    story.append(Paragraph('9.9  Missing details', styles['h2']))
    story.append(Paragraph(
        'When a metadata field is unknown (price band, walking distance, hours), we '
        'omit the field entirely. We never show "&mdash;", "N/A", "TBD", or a '
        'placeholder. The absence of the field is the design statement.',
        styles['body']))

    story.append(Paragraph('9.10  Unsupported claims', styles['h2']))
    story.append(Callout('What we forbid the UI from rendering', [
        '<b>Awards.</b> Michelin stars, James Beard, Bib Gourmand &mdash; never '
        'rendered unless the backend has a structured, dated source.',
        '<b>"Stunning views" / "Romantic ambiance".</b> Subjective adjectives derived '
        'from anything other than a corroborated, verbatim source quote.',
        '<b>Distance / walking time.</b> Rendered only when the backend computed it '
        'from real coordinates &mdash; never estimated client-side.',
        '<b>Neighborhood claim.</b> Rendered only when Google Places has a '
        'neighborhood label or the source explicitly names it.',
        '<b>Price band.</b> Rendered only from Google price level. We never infer '
        'price from a venue name or photo.',
        '<b>Opening hours / "open now".</b> Rendered only from a fresh Google response. '
        'Stale hours are dropped, not displayed.',
    ], kind='reject'))

    story.append(Paragraph('9.11  Confidence without fake precision', styles['h2']))
    story.append(Paragraph(
        'No percentages. No 5-star aggregate scores. No relative ranking like '
        '"#1 of 487". Three plain-English confidence rungs, source counts, and '
        'extractive snippets &mdash; nothing else. The product&rsquo;s premium feel '
        'comes from typographic restraint, not from manufactured precision.',
        styles['body']))
    story.append(PageBreak())


# ---------------------------------------------------------------------------
# SECTION 10 — Addictive personalization ideas
# ---------------------------------------------------------------------------
def build_section_10(story, styles):
    chapter_opener(story, '10', 'Addictive personalization ideas',
                   'Tasteful, evidence-grounded details that make the user return '
                   '&mdash; without urgency, gimmicks, or childish gamification.',
                   styles)

    story.append(Paragraph(
        'These ideas are all <i>opt-in by behaviour</i> &mdash; each only appears when '
        'the user has supplied enough data for it to be honest. None of them require '
        'new fabrication, new claims, or new ranking magic. Each is implementable as a '
        'frontend pass over data the backend already exposes.',
        styles['lead']))

    items = [
        ('Evolving trip covers',
         'Each trip cover is a real photo from a verified place inside the trip, '
         'rotating to a new one as the trip evolves. If the user adds a hotel in '
         'River North, the cover swaps to the hotel hero. If they add a sunrise '
         'activity, the cover swaps to that. Never stock; only verified photos.'),
        ('Destination atmosphere',
         'The trip detail page shifts a single tonal accent (a sandstone vs. brass '
         'mix) to match the destination&rsquo;s curated atmosphere &mdash; "northern, '
         'cooler" vs. "tropical, warmer". Subtle: a 4&thinsp;%-luminance shift, not '
         'a full re-skin.'),
        ('Personal travel style memory',
         'After three saves, the AI Concierge surfaces a one-line summary: '
         '"You tend to save quieter, smaller, dinner-date places. Want me to default '
         'to that vibe?" Yes/no. The choice persists. We never auto-default without '
         'asking.'),
        ('Luxury-for-less picks',
         'On any Explore tab, a single "Luxury for less" rail at the top, capped at '
         '3 cards. Inclusion requires backend evidence that the place delivers a '
         'high-end experience at a notably lower price band than peers. Never a '
         '"deal of the day".'),
        ('Worth-the-splurge moments',
         'On any verified card, when the place is meaningfully higher-priced AND has '
         'corroborating evidence of a notable experience, a brass "Worth the splurge" '
         'chip appears next to the price band. Selectively. Never on more than ~10% '
         'of cards in a result set.'),
        ('Rainy-day swaps',
         'When a trip is &lt; 7 days away and weather data shows rain on a planned '
         'day, a Concierge prompt appears: "It is forecast to rain Saturday. Want '
         'me to suggest indoor alternatives for your 2&nbsp;PM block?" Honest, '
         'optional, never automatic.'),
        ('"Tonight\'s edit"',
         'On the dashboard, a single inline strip: "Three places open tonight that '
         'fit your saved style." Only appears when the user is in the destination '
         'city (geo permission granted) and the data is fresh.'),
        ('Neighborhood mood maps',
         'On the Areas tab, each neighborhood polygon tints with a tonal accent '
         'corresponding to its dominant character (food, nightlife, museums). The '
         'tint is computed from the count and category of verified places in the '
         'polygon, not editorial.'),
        ('Saved-card collections',
         'Manual collections inside saved ideas: "Anniversary picks", "Worth a flight". '
         'Drag-and-drop. No suggested collections; the user names them.'),
        ('Trip completion rituals',
         'After the last day of a trip, the dashboard shows a single typographic '
         'card: "Chicago, May 5&ndash;9. 14 places saved, 9 visited, 3 still in your '
         'shelf." A small "save trip to scrapbook" link archives it. No badge, no '
         'celebration animation.'),
        ('Subtle unlocks / progress',
         'Light progress hints: "You have planned 3 of your 4 days." A hairline '
         'progress glyph in the trip cover, never a percentage ring.'),
        ('Conversational next-best-actions',
         'After every Concierge result, a single line: "Want me to also find a wine '
         'bar nearby for after?" derived from the ask. Single-tap continues the chain.'),
    ]
    for title, body in items:
        story.append(Paragraph(title, styles['h3']))
        story.append(Paragraph(body, styles['body']))
        story.append(hr())

    story.append(Paragraph('10.1  What we never do', styles['h2']))
    story.append(Callout('Personalization anti-patterns', [
        '<b>Streaks, XP, levels, badges.</b> Childish; antithetical to the brand.',
        '<b>"Limited time" / "ending soon" prompts.</b> Manufactured urgency.',
        '<b>Animated success bursts.</b> See §5.9.',
        '<b>"You unlocked X" modals.</b> The user did not unlock anything; we just '
        'showed them more of what they already chose.',
        '<b>Push notifications about unrelated trips.</b> Email or in-app, never noisy '
        'cross-trip pings.',
        '<b>Auto-defaults without asking.</b> Memory is consensual.',
    ], kind='reject'))
    story.append(PageBreak())


# ---------------------------------------------------------------------------
# SECTION 11 — Implementation roadmap
# ---------------------------------------------------------------------------
def _phase_block(story, styles, num, name, scope, model, risk, tests, backend_ok,
                 sql_ok, rollback, handoff_note):
    story.append(Paragraph('Phase %s — %s' % (num, name), styles['h2']))
    story.append(Paragraph('<b>Scope.</b>  ' + scope, styles['body']))
    rows = [
        ['Field', 'Value'],
        ['Recommended model',          model],
        ['Risk',                       risk],
        ['Frontend tests / screenshots', tests],
        ['Backend changes allowed?',   backend_ok],
        ['SQL allowed?',               sql_ok],
        ['Rollback strategy',          rollback],
    ]
    story.append(small_table(rows, [1.9*inch, 5.0*inch], styles))
    story.append(Paragraph('<b>HANDOFF.md / progress_log.md update.</b>  ' + handoff_note,
                           styles['body']))
    story.append(hr())


def build_section_11(story, styles):
    chapter_opener(story, '11', 'Implementation roadmap',
                   'A phased redesign that does not break existing functionality. '
                   'Each phase is one pull request, one merge gate, one rollback path.',
                   styles)

    story.append(Paragraph(
        'Each phase is independently shippable, independently rollbackable, and bounded '
        'by the UI budget gate in <i>docs/ai/PROMPT_LIBRARY.md</i>. No phase is allowed '
        'to start until the previous one has merged and survived a 48-hour stability window.',
        styles['lead']))

    _phase_block(story, styles, '0', 'Design tokens &amp; foundation',
                 scope=('Add CSS variable tokens for colors, type, spacing, elevation, '
                        'and motion; introduce the Card primitive shell (no variants '
                        'wired yet); ensure Tailwind theme reads from CSS variables. '
                        'Touch ≤ 6 files, all in <i>frontend/</i>.'),
                 model='Sonnet (precise mechanical work; Codex if PR &lt; 200 LOC).',
                 risk='Low &mdash; tokens replace existing utility classes incrementally.',
                 tests='Visual diff of Dashboard, Trip Detail, AI Concierge drawer at desktop + mobile; '
                       'reduced-motion test; WCAG AA contrast check on every token pair.',
                 backend_ok='No.',
                 sql_ok='No.',
                 rollback='Revert PR; tokens are additive on top of existing styles.',
                 handoff_note='HANDOFF.md gets a "Design Foundation Phase 0" entry naming '
                       'the new token files; progress_log.md notes the merge and the '
                       '48-hour stability window.')

    _phase_block(story, styles, '1', 'Shell &amp; navigation polish',
                 scope=('Sidebar density, mobile bottom rail polish, page header '
                        'consistency, page transitions per §5.2. Reuse existing routes; '
                        'no IA changes. Touch ≤ 6 files.'),
                 model='Sonnet.',
                 risk='Low.',
                 tests='Manual nav test on desktop + mobile; reduced-motion test; tab focus order.',
                 backend_ok='No.',
                 sql_ok='No.',
                 rollback='Revert PR; no schema or API changes to undo.',
                 handoff_note='Note: shell now consumes Phase 0 tokens; legacy classes '
                       'removed from header and sidebar.')

    _phase_block(story, styles, '2', 'AI Concierge flagship redesign',
                 scope=('Apply §6 in full: card-first hierarchy, conversation rail, '
                        'memory pill, composer, thinking breadcrumb. Frontend only; '
                        'no change to <i>fast_dynamic_place_search</i> or routes/ai.'),
                 model='Sonnet (high care).',
                 risk='Medium &mdash; the flagship surface; visual-regression risk '
                      'is meaningful. Bound to ≤ 8 files.',
                 tests=('Manual: tapas-bar query, sushi-with-waterfront query, '
                        'compare-top-3, more-options pool hit, weak-evidence chip, '
                        'no-results state, reduced-motion. Screenshot matrix saved '
                        'into the PR.'),
                 backend_ok='No.',
                 sql_ok='No.',
                 rollback='Revert PR; old AI Concierge component is preserved as '
                          '<i>AIConcierge.legacy.tsx</i> for one release.',
                 handoff_note='HANDOFF.md adds "AI Concierge Visual Pass v1" with the '
                       'screenshot matrix link; progress_log.md notes the merge.')

    _phase_block(story, styles, '3', 'Card system redesign',
                 scope=('Implement §8 in full: one Card primitive + 9 variants. '
                        'Replace existing card components route by route, starting '
                        'with verified place card and AI Concierge result card. '
                        'Touch ≤ 6 files per slice; this phase may need 2 PRs.'),
                 model='Sonnet, with Codex visual merge gate.',
                 risk='Medium &mdash; cards are the atomic unit; regressions ripple. '
                      'Mitigation: variants are added behind a feature flag '
                      '<i>--use-new-card-shell</i> at the component level so we can '
                      'fall back per surface.',
                 tests=('Visual diff of every surface that uses a card; trust strip '
                        'rendering; weak-evidence rendering; add-to-trip animation; '
                        'reduced-motion; mobile compact mode.'),
                 backend_ok='No.',
                 sql_ok='No.',
                 rollback='Per-surface fallback flag flips, then revert PR.',
                 handoff_note='HANDOFF.md adds "Card Shell v1" entry with variant list.')

    _phase_block(story, styles, '4', 'Explore redesign',
                 scope=('Apply §7.6 to all five Explore tabs. Adopt the Phase 3 '
                        'card variants. Add filter chip URL persistence. Map theme '
                        'per §4.9. Touch ≤ 6 files.'),
                 model='Sonnet.',
                 risk='Medium &mdash; map styling can break with provider quirks.',
                 tests='Filter persistence across reload; map theme on light/dark; '
                       'cluster behavior; chip-derived empty state.',
                 backend_ok='No.',
                 sql_ok='No.',
                 rollback='Revert PR; map theme falls back to Google default.',
                 handoff_note='HANDOFF.md adds "Explore Visual Pass v1".')

    _phase_block(story, styles, '5', 'Itinerary &amp; timeline redesign',
                 scope=('Apply §7.8: editorial day sections, hairline travel-time '
                        'hints, drop-zone affordances, day collapse. Touch ≤ 5 files.'),
                 model='Sonnet.',
                 risk='Medium &mdash; drag-and-drop a11y must be preserved.',
                 tests='Keyboard reorder; touch long-press reorder; reduced-motion; '
                       'collapsed-day expand; travel-time hint expand.',
                 backend_ok='No.',
                 sql_ok='No.',
                 rollback='Revert PR.',
                 handoff_note='HANDOFF.md adds "Itinerary Visual Pass v1".')

    _phase_block(story, styles, '6', 'Landing &amp; auth redesign',
                 scope=('Apply §7.1 and §7.2. Cinematic hero (still photo + 1% grain), '
                        'glass composer pill (only sanctioned glass surface), still '
                        'auth photo. Two PRs may be cleaner: hero first, auth second.'),
                 model='Sonnet, with Codex visual merge gate.',
                 risk='Medium &mdash; first impression; mobile FCP must be guarded.',
                 tests='Lighthouse FCP ≤ 2.0&thinsp;s on 3G Fast emulation; reduced-'
                       'motion; image LQIP fallback test.',
                 backend_ok='No.',
                 sql_ok='No.',
                 rollback='Revert PR; existing landing component preserved as '
                          '<i>landing.legacy.tsx</i>.',
                 handoff_note='HANDOFF.md adds "Landing &amp; Auth Visual Pass v1".')

    _phase_block(story, styles, '7', 'Mobile refinement',
                 scope=('Sweep all surfaces for mobile thumb reach, sheet behaviors, '
                        'AI Concierge sheet, Itinerary touch targets. Touch ≤ 6 files.'),
                 model='Sonnet.',
                 risk='Low.',
                 tests='Manual phone tests on iOS Safari + Android Chrome.',
                 backend_ok='No.',
                 sql_ok='No.',
                 rollback='Revert PR.',
                 handoff_note='HANDOFF.md adds "Mobile Refinement v1".')

    _phase_block(story, styles, '8', 'Motion polish',
                 scope=('Apply §5 in full: page transitions, card entrance, '
                        'thinking breadcrumb, save/add micro-moments, reduced-motion. '
                        'Bounded to motion code only; no layout changes.'),
                 model='Sonnet, with Codex visual merge gate.',
                 risk='Medium &mdash; motion regressions are subtle.',
                 tests='Reduced-motion test; FCP regression check; battery sanity '
                       'on phone for 90&thinsp;s of normal use.',
                 backend_ok='No.',
                 sql_ok='No.',
                 rollback='Revert PR; motion tokens fall back to instant.',
                 handoff_note='HANDOFF.md adds "Motion Polish v1".')

    _phase_block(story, styles, '9', 'Final cohesion pass',
                 scope=('Sweep for stragglers, light-era classes, inconsistencies '
                        'discovered post-Phase 8. Capped to 6 files of removals/'
                        'unifications. No new components.'),
                 model='Codex.',
                 risk='Low.',
                 tests='Visual diff per surface against the Phase 0 baseline.',
                 backend_ok='No.',
                 sql_ok='No.',
                 rollback='Revert PR.',
                 handoff_note='HANDOFF.md adds "Design Bible Cohesion Pass &mdash; complete".')

    story.append(Paragraph('11.x  Roadmap shape', styles['h2']))
    story.append(Callout('Why these phases, in this order', [
        '<b>Foundation first.</b> Phase 0 is the only phase that adds tokens. Every '
        'other phase consumes them.',
        '<b>Flagship before breadth.</b> Phase 2 (AI Concierge) precedes Explore and '
        'Itinerary because the Concierge sets the visual bar.',
        '<b>Cards before surfaces that use them.</b> Phase 3 precedes 4, 5 because '
        'every later phase reuses the card primitive.',
        '<b>Landing last among visual.</b> First impression edits last so the bar is '
        'set before we polish the welcome mat.',
        '<b>Motion last.</b> Motion can mask layout problems; we want layout right '
        'first.',
        '<b>No backend, no SQL, anywhere.</b> If a phase needs them, it is split '
        'before it starts &mdash; never bundled into a design PR.',
    ], kind='principle'))
    story.append(PageBreak())


# ---------------------------------------------------------------------------
# SECTION 12 — Guardrails for future implementation prompts
# ---------------------------------------------------------------------------
def build_section_12(story, styles):
    chapter_opener(story, '12', 'Guardrails for future implementation prompts',
                   'The rules every Sonnet/Codex design prompt must follow. '
                   'These are the diff between a great visual pass and a regression.',
                   styles)

    story.append(Paragraph('12.1  Hard rules', styles['h2']))
    story.append(Callout('Non-negotiable guardrails for every design PR', [
        '<b>1.  Preserve payload contracts.</b> A design PR may not change any field '
        'on the AI Concierge response, the place card payload, the trip payload, or '
        'the itinerary payload. Adding a new optional UI-only field is allowed only '
        'if it is computed from existing fields entirely on the client.',
        '<b>2.  Preserve addable card behavior.</b> Verification gates, identity keys, '
        'pool/dedup, and the "no fake addable cards" invariant are sacred. Cards '
        'render only when the backend marked them OPERATIONAL with a stable Place ID.',
        '<b>3.  Preserve tests.</b> Every existing backend and frontend test must '
        'pass. A failing test is a stop. We never delete tests to make a UI PR pass.',
        '<b>4.  No backend rewrites.</b> A design PR may not modify '
        '<i>backend/app/services/*</i>, <i>routes/*</i>, <i>concierge/*</i>, or any '
        'ranking, parsing, or evidence pipeline. If a UI claim requires backend data, '
        'the data is fetched in a separately scoped backend PR <i>first</i>.',
        '<b>5.  No SQL.</b> A design PR may not include Supabase migrations. The PR '
        'summary must explicitly state "Supabase SQL: No". If the design appears to '
        'need SQL, the PR is rejected and the work is split.',
        '<b>6.  No intelligence behavior changes.</b> A design PR may not edit prompts, '
        'intent detection, query parsing, ranking, scoring, or category gates. If a '
        'visual treatment depends on these, the dependency goes through a separate '
        'backend PR.',
        '<b>7.  No hidden errors.</b> If a fetch fails, the UI shows a calm error '
        'with a retry. We never swallow errors to make a UI look stable.',
        '<b>8.  No fake trust signals.</b> A "Verified by Google" mark may render '
        'only when the backend payload says the place is OPERATIONAL with a stable '
        'Place ID. Identical for source counts and confidence chips.',
        '<b>9.  No large all-in-one redesign PR.</b> Every PR maps to exactly one '
        'roadmap phase (§11). A PR that touches more than 6 frontend files needs Code '
        'Committee approval before merge.',
        '<b>10. Reduced-motion test required.</b> Every UI PR must include a '
        '<i>prefers-reduced-motion: reduce</i> verification screenshot or note.',
    ], kind='guardrail'))

    story.append(Paragraph('12.2  PR prompt template (mandatory)', styles['h2']))
    story.append(Paragraph(
        'Future Sonnet/Codex design prompts must conform to this template. The '
        'template is short by design.',
        styles['body']))
    story.append(Paragraph(
        '<b>Title:</b> "Design Phase X &mdash; [scope]"<br/><br/>'
        '<b>Sections cited:</b> §11 Phase X, §[other relevant chapters]<br/><br/>'
        '<b>Files allowed:</b> &lt;explicit list, ≤ 6 unless approved&gt;<br/><br/>'
        '<b>Files forbidden:</b> backend/**, supabase/**, routes/**, services/**<br/><br/>'
        '<b>Frontend tests:</b> &lt;list of manual smoke checks&gt;<br/><br/>'
        '<b>Reduced-motion test:</b> screenshot or note<br/><br/>'
        '<b>Supabase SQL:</b> No<br/><br/>'
        '<b>Rollback:</b> Revert PR; no schema or API changes to undo.<br/><br/>'
        '<b>HANDOFF.md update:</b> [yes/no + 1 line]',
        styles['body']))

    story.append(Paragraph('12.3  Soft rules (strong defaults)', styles['h2']))
    story.extend(labeled_bullets([
        ('Use tokens, never hex.',
         'If a token is missing, add the token in a separate Phase 0 follow-up PR '
         'first.'),
        ('Use the Card primitive.',
         'No new bespoke card components without a Code Committee review.'),
        ('Use the existing motion easings.',
         'No new easing curves; pick from the four defined in §5.'),
        ('Run the spouse-friendly smoke test.',
         'After every UI PR, manually run: open dashboard → tap a trip → ask the '
         'concierge for tapas → save a card → see it in the trip. Mobile + desktop. '
         'Note any regressions in the PR.'),
        ('Cap one design PR per branch per day.',
         'Avoids stacked-PR review fatigue and CI flakiness.'),
    ], styles))

    story.append(Paragraph('12.4  Stop conditions', styles['h2']))
    story.append(Callout('When to stop the PR and reclassify', [
        '<b>The PR exceeds 6 files.</b>  Stop, split.',
        '<b>The PR needs a backend change.</b>  Stop, split into a backend PR first.',
        '<b>A test fails.</b>  Stop. Diagnose. Do not delete the test.',
        '<b>The Concierge returns 0 cards on the smoke test after the PR.</b>  Stop. '
        'Roll back. Diagnose offline.',
        '<b>FCP regresses on landing or Trip Detail.</b>  Stop. Roll back.',
        '<b>Reduced-motion mode is not tested.</b>  Stop. Add the test before merging.',
    ], kind='guardrail'))
    story.append(PageBreak())


# ---------------------------------------------------------------------------
# SECTION 13 — First recommended design implementation slice
# ---------------------------------------------------------------------------
def build_section_13(story, styles):
    chapter_opener(story, '13', 'First recommended design implementation slice',
                   'A small, safe, foundation-level slice that establishes the '
                   'visual system without touching intelligence or content.',
                   styles)

    story.append(Paragraph('13.1  Recommendation', styles['h2']))
    story.append(Paragraph(
        'The first PR is <b>Phase 0 &mdash; Design tokens + Card primitive shell</b>, '
        'and nothing else. It is deliberately small enough to merge in a single '
        'Sonnet pass, deliberately important enough that every subsequent phase '
        'inherits its structure.',
        styles['body']))

    story.append(Paragraph('13.2  Why this slice', styles['h2']))
    story.extend(labeled_bullets([
        ('Foundational.',
         'Every later phase consumes the tokens and the Card primitive.'),
        ('Reversible.',
         'Tokens are additive; reverting the PR removes them without touching '
         'consumers.'),
        ('Visual but invisible.',
         'The user sees no immediate change; downstream phases unlock the visible '
         'work.'),
        ('Avoids product risk.',
         'No surface adopts the new card variants in this PR; we cannot regress '
         'rendering of any card we do not touch.'),
    ], styles))

    story.append(Paragraph('13.3  Scope (precise)', styles['h2']))
    story.extend(labeled_bullets([
        ('Add tokens to <i>frontend/src/app/globals.css</i>:',
         'colors (12 dark + 9 paper), type scale (11 roles), spacing (10 steps), '
         'elevation (5 levels), motion (4 easings, 4 durations), per §4.'),
        ('Wire Tailwind theme to read CSS variables.',
         'No raw color values inside Tailwind config &mdash; only var(--token).'),
        ('Add a Card primitive at <i>frontend/src/components/ui/Card.tsx</i>:',
         'composable slot API (identity, trust, media, why, meta, actions, caveat) '
         'with no variants wired yet. Pure structural component.'),
        ('Add a TrustStrip primitive at <i>frontend/src/components/ui/TrustStrip.tsx</i>:',
         'renders the verified mark, source count, confidence chip from a simple props '
         'shape that mirrors existing payloads.'),
        ('Update <i>UI_BASELINE.md</i>',
         'Note that token foundation v2 has shipped and link to this bible.'),
    ], styles))

    story.append(Paragraph('13.4  Out of scope (explicitly)', styles['h2']))
    story.append(Callout('What this slice does NOT do', [
        'No surface adopts the new Card primitive in this PR.',
        'No backend or API change. No SQL.',
        'No motion implementations beyond declaring the duration and easing tokens.',
        'No new icon set. No new font hosting. No new animation library.',
        'No removal of existing components yet &mdash; everything coexists.',
    ], kind='guardrail'))

    story.append(Paragraph('13.5  Files allowed (≤ 6)', styles['h2']))
    rows = [
        ['#', 'File', 'Change'],
        ['1', '<i>frontend/src/app/globals.css</i>',
         'Add CSS variables for color, type, spacing, elevation, motion.'],
        ['2', '<i>frontend/tailwind.config.ts</i>',
         'Theme keys read from var(--token).'],
        ['3', '<i>frontend/src/components/ui/Card.tsx</i>',
         'New composable Card primitive.'],
        ['4', '<i>frontend/src/components/ui/TrustStrip.tsx</i>',
         'New TrustStrip primitive.'],
        ['5', '<i>docs/ai/UI_BASELINE.md</i>',
         'Note token foundation v2 + link to bible.'],
        ['6', '<i>docs/ai/HANDOFF.md</i>',
         'Add "Design Foundation Phase 0" entry.'],
    ]
    story.append(small_table(rows, [0.4*inch, 2.7*inch, 3.85*inch], styles))

    story.append(Paragraph('13.6  Acceptance checks', styles['h2']))
    story.extend(labeled_bullets([
        ('Build passes; type checks pass.',
         'Existing UI is visually unchanged.'),
        ('Tokens visible in DevTools.',
         'Hover any element &mdash; computed colors show <i>var(--surface-1)</i> not '
         'a raw hex.'),
        ('Card primitive renders an empty shell.',
         'A Storybook entry or a /debug route demonstrates the Card primitive in dark '
         'and paper modes with each slot toggled.'),
        ('Reduced-motion respected.',
         'Card primitive has no entrance animation by default.'),
        ('Spouse-friendly smoke test.',
         'Dashboard → trip → AI Concierge → tapas search → add to trip works '
         'identically before and after the PR.'),
    ], styles))

    story.append(Paragraph('13.7  Rollback', styles['h2']))
    story.append(Paragraph(
        'Single PR revert. Tokens removed; Tailwind theme returns to its prior shape; '
        'two new components are removed. No data, no schema, no API to unwind.',
        styles['body']))

    story.append(Paragraph('13.8  What is NOT yet a prompt', styles['h2']))
    story.append(Callout('No implementation prompt yet, by design', [
        'Per the brief, this bible recommends the first slice but does not author the '
        'implementation prompt. Pressure-test this bible (especially §6, §8, §9, §11) '
        'in ChatGPT or with a second reviewer first. After agreement, write the Phase 0 '
        'prompt against §13.3&ndash;13.6 verbatim.',
    ], kind='principle'))

    story.append(Paragraph('13.9  After Phase 0', styles['h2']))
    story.append(Paragraph(
        'When Phase 0 is merged and stable for 48 hours, the next slice is Phase 2 '
        '(AI Concierge flagship redesign), not Phase 1 (shell polish). The Concierge '
        'is the highest-leverage surface; once it consumes tokens via the Card '
        'primitive, every other surface follows naturally.',
        styles['body']))
    story.append(PageBreak())


# ---------------------------------------------------------------------------
# APPENDIX — glossary, success criteria, open questions
# ---------------------------------------------------------------------------
def build_appendix(story, styles):
    chapter_opener(story, 'A', 'Appendix &middot; Glossary, success criteria, open questions',
                   'Definitions and pressure-test prompts for the next review pass.',
                   styles)

    story.append(Paragraph('A.1  Glossary', styles['h2']))
    rows = [
        ['Term', 'Meaning in this bible'],
        ['Verified place card',
         'A card backed by a stable Google Place ID with OPERATIONAL status.'],
        ['Addable',
         'A card the user can add to a trip; must be a verified place card.'],
        ['Why-quote',
         'The serif italic pull-quote on every card describing why the place fits.'],
        ['Trust strip',
         'The horizontal row of trust signals on every card.'],
        ['Evidence ladder',
         'The four-rung backend-confidence-to-UI mapping in §9.1.'],
        ['Memory pill',
         'The single editable summary of the active conversational context.'],
        ['Composer',
         'The AI Concierge prompt input, always visible.'],
        ['Result canvas',
         'The right-side region of the AI Concierge that shows verified cards.'],
        ['Conversation rail',
         'The left-side region of the AI Concierge that shows turns + intent.'],
        ['Tonal duality',
         'The two-mode system: midnight ink for active surfaces, paper for artefacts.'],
        ['Card primitive',
         'The single composable component that backs every card variant.'],
        ['Card variant',
         'A configured composition of the Card primitive (see §8.2).'],
        ['Spouse-friendly smoke test',
         'The end-to-end flow we manually validate after every UI PR.'],
        ['Roadmap phase',
         'A bounded design PR scope that maps 1:1 to a section in §11.'],
    ]
    story.append(small_table(rows, [1.7*inch, 5.2*inch], styles))

    story.append(Paragraph('A.2  Success criteria for the program', styles['h2']))
    story.extend(labeled_bullets([
        ('No design PR regresses backend tests, AI Concierge latency, or '
         'addable card count.',
         ''),
        ('After Phase 3 merges, every surface consumes the Card primitive.',
         'Audited via grep for raw hex colors and bespoke card components.'),
        ('After Phase 9 merges, the lifecycle UI cost is &lt; 35% of session.',
         'Measured against the PR #168 baseline of ~51% lifecycle cost.'),
        ('User-reported "this looks like a luxury concierge" sentiment captured.',
         'Informal but tracked.'),
        ('No fake trust signals shipped.',
         'Audited via test that asserts Verified mark only renders when the payload '
         'flag is present.'),
        ('No invented metadata.',
         'Audited via test that asserts walking-time, neighborhood, price band fields '
         'are absent in the DOM when absent in the payload.'),
    ], styles))

    story.append(Paragraph('A.3  Open questions for the next review', styles['h2']))
    story.append(Paragraph(
        'These are the questions to answer before Phase 0 ships. They are not '
        'blockers; they are the inputs to the next decision.',
        styles['body']))
    story.extend(labeled_bullets([
        ('Type system.',
         'Do we self-host an editorial serif (e.g., Editorial New, GT Super, Tiempos) '
         'or stay with system serifs for portability and FCP? Recommendation: stay '
         'system in Phase 0; add a self-hosted serif in a Phase 6 sub-slice '
         'specifically scoped for it.'),
        ('Photography pipeline.',
         'How do we source verified-place photos at scale without violating provider '
         'attribution rules? This determines whether trip covers can use real '
         'photographs in Phase 0&ndash;3 or remain typeset.'),
        ('Map provider.',
         'Are we comfortable applying a custom theme to Google Maps, or do we evaluate '
         'Mapbox / MapLibre for finer style control? Recommendation: stay on Google '
         'with a custom style JSON; defer Mapbox unless a concrete limitation surfaces.'),
        ('AI Concierge memory persistence.',
         'Currently in-memory. The bible assumes the memory pill summarizes session '
         'state only. If we persist across sessions, the pill UX is unchanged but the '
         '"forget" link becomes a real durable action; backend out of design scope.'),
        ('Mobile sheet vs. drawer on tablet.',
         'Tablet viewport is awkward; current bible says sheet. Confirm with a single '
         'mobile-tablet review.'),
        ('Light-mode admission.',
         'Saved Ideas is the only sanctioned light-mode app surface. Confirm with the '
         'founder before Phase 5 begins; if rejected, Saved Ideas stays dark and the '
         '"artefact" cue is signalled differently.'),
    ], styles))

    story.append(Paragraph('A.4  Reading order for ChatGPT pressure test', styles['h2']))
    story.append(Paragraph(
        'When you bring this bible back to ChatGPT for review, send chapters in this '
        'order to maximize useful pushback:',
        styles['body']))
    story.append(Paragraph(
        '1. <b>§00 Executive summary</b> &mdash; "challenge any assumption."<br/>'
        '2. <b>§06 AI Concierge UX</b> &mdash; "is the card-first hierarchy correct?"<br/>'
        '3. <b>§09 Evidence and trust UX</b> &mdash; "are the four rungs of the evidence '
        'ladder defensible?"<br/>'
        '4. <b>§11 Roadmap</b> &mdash; "is Phase 0 the right first slice?"<br/>'
        '5. <b>§12 Guardrails</b> &mdash; "are these enforceable without slowing the '
        'team down?"<br/>'
        '6. <b>§13 First slice</b> &mdash; "what would you cut to make this even smaller?"',
        styles['body']))

    story.append(Paragraph('A.5  Final check: the mantras', styles['h2']))
    story.append(Paragraph(
        'Beauty without logic and logic without beauty are equally bad.',
        styles['quote']))
    story.append(Paragraph(
        'Fast does not mean dumb. Honesty is luxury. Evidence is the brand. The card '
        'is the hero. The concierge is composed, not chatty. Every pixel has purpose; '
        'every word has a source; every motion has a reason; every PR has a phase.',
        styles['body']))
    story.append(PageBreak())
