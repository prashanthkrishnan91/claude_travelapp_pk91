"""Travel Concierge Design Bible — page templates, cover, and TOC."""

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer,
    PageBreak, Table, TableStyle, NextPageTemplate,
)
from reportlab.platypus.flowables import HRFlowable

from styles import (
    INK, ONYX, CARBON, PEN, GOLD, BRASS, PEARL, CREAM_TEXT, SAGE,
    AMBER, CORAL, MIST, RAIN, PAPER, INK_PAPER, SLATE, HAIRLINE,
    make_styles, hr, Callout, Swatch, swatch_grid, bullets,
    labeled_bullets, small_table,
)

PAGE_W, PAGE_H = LETTER


# ---------------------------------------------------------------------------
# PAGE BACKDROPS — drawn behind frames via PageTemplate.onPage
# ---------------------------------------------------------------------------
def _draw_dark_backdrop(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(INK)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    # Top hairline
    canvas.setStrokeColor(PEN)
    canvas.setLineWidth(0.5)
    canvas.line(0.75 * inch, PAGE_H - 0.65 * inch,
                PAGE_W - 0.75 * inch, PAGE_H - 0.65 * inch)
    canvas.setFillColor(GOLD)
    canvas.setFont('Helvetica-Bold', 8)
    canvas.drawString(0.75 * inch, PAGE_H - 0.5 * inch,
                      'TRAVEL CONCIERGE')
    canvas.setFillColor(MIST)
    canvas.setFont('Helvetica', 8)
    canvas.drawRightString(PAGE_W - 0.75 * inch, PAGE_H - 0.5 * inch,
                           'Design Bible v1.0')
    canvas.restoreState()


def _draw_paper_backdrop(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    # Header strip
    canvas.setFillColor(BRASS)
    canvas.rect(0.75 * inch, PAGE_H - 0.55 * inch,
                0.18 * inch, 0.18 * inch, fill=1, stroke=0)
    canvas.setFillColor(SLATE)
    canvas.setFont('Helvetica-Bold', 8)
    canvas.drawString(1.0 * inch, PAGE_H - 0.46 * inch,
                      'TRAVEL CONCIERGE  ·  DESIGN BIBLE')
    canvas.setFillColor(SLATE)
    canvas.setFont('Helvetica', 8)
    canvas.drawRightString(PAGE_W - 0.75 * inch, PAGE_H - 0.46 * inch,
                           'Luxury for Less')
    # Top hairline
    canvas.setStrokeColor(HAIRLINE)
    canvas.setLineWidth(0.4)
    canvas.line(0.75 * inch, PAGE_H - 0.62 * inch,
                PAGE_W - 0.75 * inch, PAGE_H - 0.62 * inch)
    # Footer
    canvas.setStrokeColor(HAIRLINE)
    canvas.line(0.75 * inch, 0.65 * inch,
                PAGE_W - 0.75 * inch, 0.65 * inch)
    canvas.setFillColor(SLATE)
    canvas.setFont('Helvetica', 8)
    canvas.drawString(0.75 * inch, 0.5 * inch,
                      'Design strategy · Not for implementation until phased per Section 11')
    canvas.setFillColor(BRASS)
    canvas.setFont('Helvetica-Bold', 8)
    canvas.drawRightString(PAGE_W - 0.75 * inch, 0.5 * inch,
                           '%d' % canvas.getPageNumber())
    canvas.restoreState()


def _draw_chapter_backdrop(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    # Heavy ink band on top quarter
    canvas.setFillColor(INK)
    canvas.rect(0, PAGE_H - 3.4 * inch, PAGE_W, 3.4 * inch,
                fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.setFont('Helvetica-Bold', 8)
    canvas.drawString(0.75 * inch, PAGE_H - 0.5 * inch,
                      'TRAVEL CONCIERGE')
    canvas.setFillColor(MIST)
    canvas.setFont('Helvetica', 8)
    canvas.drawRightString(PAGE_W - 0.75 * inch, PAGE_H - 0.5 * inch,
                           'Design Bible v1.0')
    # Footer
    canvas.setStrokeColor(HAIRLINE)
    canvas.line(0.75 * inch, 0.65 * inch,
                PAGE_W - 0.75 * inch, 0.65 * inch)
    canvas.setFillColor(BRASS)
    canvas.setFont('Helvetica-Bold', 8)
    canvas.drawRightString(PAGE_W - 0.75 * inch, 0.5 * inch,
                           '%d' % canvas.getPageNumber())
    canvas.restoreState()


# ---------------------------------------------------------------------------
# DOC SETUP
# ---------------------------------------------------------------------------
def make_doc(out_path):
    margin_x = 0.75 * inch
    top = 0.95 * inch
    bottom = 0.85 * inch
    frame_paper = Frame(margin_x, bottom, PAGE_W - 2 * margin_x,
                        PAGE_H - top - bottom, id='paper',
                        leftPadding=0, rightPadding=0,
                        topPadding=0, bottomPadding=0)
    frame_dark = Frame(margin_x, bottom, PAGE_W - 2 * margin_x,
                       PAGE_H - top - bottom, id='dark',
                       leftPadding=0, rightPadding=0,
                       topPadding=0, bottomPadding=0)
    frame_chapter = Frame(margin_x, bottom, PAGE_W - 2 * margin_x,
                          PAGE_H - top - bottom, id='chapter',
                          leftPadding=0, rightPadding=0,
                          topPadding=0, bottomPadding=0)

    doc = BaseDocTemplate(
        out_path, pagesize=LETTER,
        leftMargin=margin_x, rightMargin=margin_x,
        topMargin=top, bottomMargin=bottom,
        title='Travel Concierge — Design Bible',
        author='Travel Concierge Design Strategy',
        subject='Luxury-for-less travel concierge experience design',
    )
    doc.addPageTemplates([
        PageTemplate(id='cover', frames=[frame_dark],
                     onPage=_draw_dark_backdrop),
        PageTemplate(id='paper', frames=[frame_paper],
                     onPage=_draw_paper_backdrop),
        PageTemplate(id='chapter', frames=[frame_chapter],
                     onPage=_draw_chapter_backdrop),
    ])
    return doc


# ---------------------------------------------------------------------------
# COVER
# ---------------------------------------------------------------------------
def build_cover(story, styles):
    story.append(Spacer(1, 1.4 * inch))
    story.append(Paragraph('A DESIGN BIBLE FOR A WORLD-CLASS PRIVATE TRAVEL ATELIER',
                           styles['cover_overline']))
    story.append(Paragraph('Travel<br/>Concierge.', styles['cover_title']))
    story.append(Paragraph(
        'A luxury-for-less travel concierge: editorial in tone, evidence-grounded in mind, '
        'cinematic in presence, and quietly addictive in use.',
        styles['cover_subtitle']))
    story.append(Spacer(1, 0.6 * inch))
    story.append(HRFlowable(width='35%', thickness=1, color=GOLD,
                            spaceBefore=0, spaceAfter=18, hAlign='LEFT'))
    story.append(Paragraph(
        '<b>Volume:</b>  Vol. I &nbsp;·&nbsp; '
        '<b>Status:</b>  Design strategy, pre-implementation &nbsp;·&nbsp; '
        '<b>Date:</b>  May 2026',
        styles['cover_meta']))
    story.append(Paragraph(
        '<b>Audience:</b>  Founder · Design lead · Sonnet/Codex implementation pairs',
        styles['cover_meta']))
    story.append(Paragraph(
        '<b>Mantra:</b>  <i>Beauty without logic and logic without beauty are equally bad.</i>',
        styles['cover_meta']))
    story.append(Spacer(1, 0.9 * inch))
    story.append(Paragraph(
        'This document does not modify code. It is the contract every future design '
        'pull request inherits. Pressure-test it, mark it up, and only then implement '
        'in the phased slices defined in Section 11.',
        styles['cover_meta']))
    story.append(NextPageTemplate('paper'))
    story.append(PageBreak())


# ---------------------------------------------------------------------------
# TABLE OF CONTENTS  (manual — no live links because reportlab.tableofcontents
# adds complexity we do not need for a strategy doc)
# ---------------------------------------------------------------------------
TOC_ROWS = [
    ('00', 'Executive summary &amp; assumptions',                ''),
    ('01', 'Design diagnosis',                                   ''),
    ('02', 'Competitive synthesis',                              ''),
    ('03', 'Brand and experience identity',                      ''),
    ('04', 'Visual system',                                      ''),
    ('05', 'Motion and microinteraction system',                 ''),
    ('06', 'AI Concierge flagship UX',                           ''),
    ('07', 'Page-by-page product design plan',                   ''),
    ('08', 'Card design system',                                 ''),
    ('09', 'Evidence and trust UX',                              ''),
    ('10', 'Addictive personalization ideas',                    ''),
    ('11', 'Implementation roadmap',                             ''),
    ('12', 'Guardrails for future implementation prompts',       ''),
    ('13', 'First recommended design implementation slice',      ''),
    ('A',  'Appendix · Glossary, success criteria, open questions', ''),
]


def build_toc(story, styles):
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph('CONTENTS', styles['chapter_overline']))
    story.append(Paragraph('How to read this bible.', styles['chapter_title']))
    story.append(Paragraph(
        'Each chapter stands alone. Read the executive summary first, then the chapter '
        'that matches the work you are about to do. The roadmap (§11) and guardrails '
        '(§12) bind every implementation prompt.',
        styles['chapter_kicker']))
    story.append(hr())
    rows = [['No.', 'Section', '']]
    for n, t, _ in TOC_ROWS:
        rows.append([n, Paragraph(t, styles['toc_section']), ''])
    t = Table(rows, colWidths=[0.55 * inch, 5.7 * inch, 0.7 * inch],
              hAlign='LEFT')
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 8.5),
        ('TEXTCOLOR', (0, 0), (-1, 0), BRASS),
        ('LINEBELOW', (0, 0), (-1, 0), 0.75, BRASS),
        ('FONT', (0, 1), (0, -1), 'Helvetica-Bold', 11),
        ('TEXTCOLOR', (0, 1), (0, -1), GOLD),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LINEBELOW', (0, 1), (-1, -1), 0.25, HAIRLINE),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.4 * inch))
    story.append(Callout(
        'This is a contract, not a wishlist',
        'The 13 deliverables in this bible map 1:1 to the original brief. '
        'Section 11 (roadmap) sets which ones convert to PRs and in what order. '
        'Section 12 (guardrails) governs every PR prompt. Skipping either invalidates the bible.',
        kind='guardrail'))
    story.append(PageBreak())


# ---------------------------------------------------------------------------
# CHAPTER OPENER — heavy-ink top, paper bottom
# ---------------------------------------------------------------------------
def chapter_opener(story, number, title, kicker, styles):
    story.append(NextPageTemplate('chapter'))
    story.append(PageBreak())
    story.append(Spacer(1, 1.65 * inch))
    story.append(Paragraph('SECTION %s' % number, ParagraphStyle(
        'co_over', parent=styles['cover_overline'],
        fontSize=10, textColor=GOLD)))
    story.append(Paragraph(title, ParagraphStyle(
        'co_title', parent=styles['cover_title'],
        fontSize=42, leading=48, textColor=PEARL)))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(kicker, ParagraphStyle(
        'co_kick', parent=styles['cover_subtitle'],
        fontSize=14, leading=22, textColor=CREAM_TEXT)))
    story.append(NextPageTemplate('paper'))
    story.append(PageBreak())


# ---------------------------------------------------------------------------
# EXECUTIVE SUMMARY  — section 00
# ---------------------------------------------------------------------------
def build_exec_summary(story, styles):
    chapter_opener(story, '00',
                   'Executive summary &amp; assumptions',
                   'A one-page contract before the bible begins.',
                   styles)
    story.append(Paragraph('What this document is', styles['h2']))
    story.append(Paragraph(
        'A complete design bible and phased redesign roadmap for the Travel Concierge '
        'product. It is opinionated, implementation-ready in spirit, and intentionally '
        'free of code. It is the artefact that future Sonnet and Codex prompts inherit.',
        styles['body']))
    story.append(Paragraph('What this document is not', styles['h2']))
    story.append(Paragraph(
        'It is not a generic visual mood board, a product spec, a backend plan, or a '
        'permission to start a sweeping redesign PR. The visual ambition lives inside '
        'a guardrail: never weaken intelligence, evidence, or speed for decoration.',
        styles['body']))

    story.append(Paragraph('Stated assumptions', styles['h2']))
    for p in [
        '<b>A1.</b> The current product already returns verified, addable Google Place cards '
        'in 3–8 seconds via the fast dynamic place search v1, and that pipeline is the '
        'source of truth for "addable" entities. Design must not regress that contract.',
        '<b>A2.</b> A premium dark-mode foundation already shipped (PR #168) with deep navy + '
        'amber + cream tokens and Tailwind primitives. We extend, not replace.',
        '<b>A3.</b> The codebase is Next.js + Tailwind on the frontend, with CSS variables '
        'already used for tokens. We can introduce additional tokens, but not a new CSS-in-JS '
        'system or a heavy animation library, without explicit budget approval.',
        '<b>A4.</b> Backend, Supabase schema, and ranking logic are out of scope for this '
        'design bible. Design slices are frontend-only unless an explicit payload change is '
        'unavoidable, in which case it is split into its own backend PR first.',
        '<b>A5.</b> The user is more sensitive to broken intelligence and broken speed than to '
        'visual roughness. Design is a force multiplier, not a justification for regressions.',
    ]:
        story.append(Paragraph(p, styles['body']))

    story.append(Paragraph('Success criteria for the bible itself', styles['h2']))
    story.extend(labeled_bullets([
        ('Pressure-testable', 'A reviewer can mark up any chapter and produce one '
         'concrete change, not a vague “I like it”.'),
        ('Phaseable', 'The roadmap (§11) lets us ship the visual system in slices '
         'no larger than ~6 frontend files, each behind a budget gate.'),
        ('Intelligence-safe', 'Every page-level recommendation states what behaviour '
         'must not change, and how to detect a regression.'),
        ('Evidence-honest', 'No chapter encourages fabricating a vibe, view, award, '
         'or distance the backend has not verified.'),
        ('Boutique, not bling', 'No glow-on-hover, no color-soup gradients, no fake '
         'urgency, no childish gamification.'),
    ], styles))

    story.append(Paragraph('Headline recommendations', styles['h2']))
    story.append(Callout(
        'The 6 things that change everything',
        [
            '<b>1.  Adopt one tonal palette per surface.</b> Midnight ink for app shell, '
            'warm paper for trip artefacts, never both on one screen.',
            '<b>2.  Treat the Verified Place Card as the product’s atomic unit.</b> Every '
            'other surface is a frame around it.',
            '<b>3.  Make evidence beautiful.</b> Trust marks, source counts, and caveats are '
            'first-class typographic citizens, not afterthought icons.',
            '<b>4.  Earn the AI Concierge’s "intelligence" through restraint.</b> A '
            'composed thinking state and clean reason tags beat any animated avatar.',
            '<b>5.  Cinematic motion, deletable on demand.</b> 200&ndash;320&thinsp;ms easings, '
            'reduced-motion fallback baked in, no animation that delays first paint of cards.',
            '<b>6.  Phase 0 is tokens + card shell.</b> Nothing else. The first PR establishes '
            'the visual language; everything afterwards is a refactor against tokens.',
        ],
        kind='principle'))

    story.append(Paragraph('How to use this bible with Sonnet/Codex', styles['h2']))
    story.extend(labeled_bullets([
        ('Always cite', 'Every design PR prompt must reference the section(s) of '
         'this bible it is implementing, e.g. "Implements §11 Phase 1 + §8 Card Shell".'),
        ('Never bundle', 'A design PR may not touch backend, ranking, Supabase, or '
         'AI prompts. If it must, split.'),
        ('Always token', 'No raw hex on a component. If a token is missing, add the '
         'token first, then use it.'),
        ('Always test the smoke path', 'After every UI PR, manually run the spouse-friendly '
         'smoke test on mobile + desktop before merging.'),
    ], styles))
    story.append(PageBreak())
