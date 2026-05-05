"""Travel Concierge Design Bible — shared styles, colors, and flowables."""

from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.platypus.flowables import Flowable, HRFlowable

# ---------------------------------------------------------------------------
# COLOR SYSTEM — these mirror the palette proposed inside the document itself
# ---------------------------------------------------------------------------
INK         = HexColor('#0B1320')   # midnight ink — primary dark canvas
ONYX        = HexColor('#0F1A2C')   # onyx velvet — surface
CARBON      = HexColor('#1A2538')   # carbon mist — raised surface
PEN         = HexColor('#22324A')   # pen-stroke — divider
GOLD        = HexColor('#E0B888')   # sandstone gold — primary accent
BRASS       = HexColor('#C5944D')   # ember brass — deeper gold
PEARL       = HexColor('#F2EBDD')   # pearl cream — warm headline text
CREAM_TEXT  = HexColor('#E8E2D4')   # body text on dark surfaces
SAGE        = HexColor('#88A899')   # verified sage — trust signal
AMBER       = HexColor('#E8B26B')   # caution amber — soft caution
CORAL       = HexColor('#D88478')   # whisper coral — gentle warning
MIST        = HexColor('#9AA4B2')   # subdued text on dark
RAIN        = HexColor('#6E7787')   # caption text on dark
PAPER       = HexColor('#FAF7F0')   # warm paper — body page background
INK_PAPER   = HexColor('#1F2530')   # body text on paper
SLATE       = HexColor('#4A5568')   # secondary text on paper
HAIRLINE    = HexColor('#D9D2C2')   # divider on paper

# Functional callout palettes
CALLOUT_KINDS = {
    'protect':    {'bar': SAGE,    'bg': HexColor('#F2F5F0'), 'title': 'Protect'},
    'reject':     {'bar': CORAL,   'bg': HexColor('#FBF2F0'), 'title': 'Reject'},
    'guardrail':  {'bar': BRASS,   'bg': HexColor('#FBF6EB'), 'title': 'Guardrail'},
    'principle':  {'bar': INK,     'bg': HexColor('#F1F0EC'), 'title': 'Principle'},
    'opportunity':{'bar': GOLD,    'bg': HexColor('#FBF5E8'), 'title': 'Opportunity'},
    'warning':    {'bar': AMBER,   'bg': HexColor('#FBF3E2'), 'title': 'Watch out'},
    'note':       {'bar': SLATE,   'bg': HexColor('#F1F2F4'), 'title': 'Note'},
}


# ---------------------------------------------------------------------------
# TYPOGRAPHY — uses built-in 14-fonts so the PDF is portable on every system
# ---------------------------------------------------------------------------
def make_styles():
    base = getSampleStyleSheet()
    s = {}

    # Cover / chapter typography (used on dark pages)
    s['cover_overline'] = ParagraphStyle(
        'cover_overline', parent=base['Normal'],
        fontName='Helvetica', fontSize=10, leading=14,
        textColor=GOLD, alignment=TA_LEFT, spaceAfter=18,
    )
    s['cover_title'] = ParagraphStyle(
        'cover_title', parent=base['Title'],
        fontName='Times-Roman', fontSize=46, leading=52,
        textColor=PEARL, alignment=TA_LEFT, spaceAfter=14,
    )
    s['cover_subtitle'] = ParagraphStyle(
        'cover_subtitle', parent=base['Normal'],
        fontName='Times-Italic', fontSize=18, leading=24,
        textColor=CREAM_TEXT, alignment=TA_LEFT, spaceAfter=24,
    )
    s['cover_meta'] = ParagraphStyle(
        'cover_meta', parent=base['Normal'],
        fontName='Helvetica', fontSize=9, leading=14,
        textColor=MIST, alignment=TA_LEFT,
    )
    s['chapter_overline'] = ParagraphStyle(
        'chapter_overline', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=9, leading=12,
        textColor=BRASS, spaceAfter=6,
    )
    s['chapter_title'] = ParagraphStyle(
        'chapter_title', parent=base['Title'],
        fontName='Times-Roman', fontSize=34, leading=40,
        textColor=INK_PAPER, spaceAfter=8,
    )
    s['chapter_kicker'] = ParagraphStyle(
        'chapter_kicker', parent=base['Normal'],
        fontName='Times-Italic', fontSize=14, leading=20,
        textColor=SLATE, spaceAfter=22,
    )

    # Body typography (paper pages)
    s['h2'] = ParagraphStyle(
        'h2', parent=base['Heading2'],
        fontName='Times-Roman', fontSize=20, leading=26,
        textColor=INK_PAPER, spaceBefore=18, spaceAfter=6,
    )
    s['h3'] = ParagraphStyle(
        'h3', parent=base['Heading3'],
        fontName='Helvetica-Bold', fontSize=12, leading=16,
        textColor=INK_PAPER, spaceBefore=12, spaceAfter=4,
    )
    s['h4'] = ParagraphStyle(
        'h4', parent=base['Heading4'],
        fontName='Helvetica-Bold', fontSize=10, leading=14,
        textColor=BRASS, spaceBefore=8, spaceAfter=2,
    )
    s['body'] = ParagraphStyle(
        'body', parent=base['BodyText'],
        fontName='Helvetica', fontSize=10, leading=15,
        textColor=INK_PAPER, alignment=TA_LEFT, spaceAfter=8,
    )
    s['lead'] = ParagraphStyle(
        'lead', parent=base['BodyText'],
        fontName='Times-Italic', fontSize=12, leading=18,
        textColor=SLATE, alignment=TA_LEFT, spaceAfter=12,
    )
    s['bullet'] = ParagraphStyle(
        'bullet', parent=base['BodyText'],
        fontName='Helvetica', fontSize=10, leading=15,
        textColor=INK_PAPER, leftIndent=18, bulletIndent=6, spaceAfter=3,
    )
    s['caption'] = ParagraphStyle(
        'caption', parent=base['BodyText'],
        fontName='Helvetica-Oblique', fontSize=8, leading=11,
        textColor=SLATE, alignment=TA_LEFT, spaceAfter=4,
    )
    s['callout_title'] = ParagraphStyle(
        'callout_title', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=9, leading=12,
        textColor=INK_PAPER, spaceAfter=4,
    )
    s['callout_body'] = ParagraphStyle(
        'callout_body', parent=base['BodyText'],
        fontName='Helvetica', fontSize=9.5, leading=14,
        textColor=INK_PAPER, alignment=TA_LEFT,
    )
    s['mono'] = ParagraphStyle(
        'mono', parent=base['Code'],
        fontName='Courier', fontSize=8.5, leading=12,
        textColor=INK_PAPER, leftIndent=8,
    )
    s['toc_section'] = ParagraphStyle(
        'toc_section', parent=base['Normal'],
        fontName='Times-Roman', fontSize=14, leading=20,
        textColor=INK_PAPER,
    )
    s['toc_dot'] = ParagraphStyle(
        'toc_dot', parent=base['Normal'],
        fontName='Helvetica', fontSize=10, leading=14,
        textColor=SLATE,
    )
    s['quote'] = ParagraphStyle(
        'quote', parent=base['BodyText'],
        fontName='Times-Italic', fontSize=14, leading=22,
        textColor=INK_PAPER, leftIndent=18, rightIndent=18, spaceAfter=14,
    )
    return s


# ---------------------------------------------------------------------------
# CALLOUT FLOWABLE — colored side bar + title + body
# ---------------------------------------------------------------------------
class Callout(Flowable):
    """A boxed callout with a left color-bar and a tinted background."""

    def __init__(self, title, body_paragraphs, kind='note', width=None):
        super().__init__()
        self.title = title
        if isinstance(body_paragraphs, str):
            body_paragraphs = [body_paragraphs]
        self.body = body_paragraphs
        self.kind = kind if kind in CALLOUT_KINDS else 'note'
        self.width = width or 7.0 * inch
        self.styles = make_styles()
        self._render = None

    def wrap(self, avail_w, avail_h):
        if self.width > avail_w:
            self.width = avail_w
        meta = CALLOUT_KINDS[self.kind]
        title = '<b>%s &middot; %s</b>' % (meta['title'].upper(), self.title)
        title_style = ParagraphStyle(
            'cb_title', parent=self.styles['callout_title'],
            fontSize=8.5, leading=11, textColor=meta['bar'])
        body_style = self.styles['callout_body']
        self._title_p = Paragraph(title, title_style)
        self._body_ps = [Paragraph(t, body_style) for t in self.body]

        pad_x = 12
        pad_y = 9
        inner_w = self.width - pad_x * 2 - 5  # minus left bar
        _, h_title = self._title_p.wrap(inner_w, 1000)
        body_h = 0
        for p in self._body_ps:
            _, ph = p.wrap(inner_w, 1000)
            body_h += ph + 3
        self._height = h_title + 6 + body_h + pad_y * 2
        return self.width, self._height

    def draw(self):
        meta = CALLOUT_KINDS[self.kind]
        c = self.canv
        # Background
        c.setFillColor(meta['bg'])
        c.setStrokeColor(meta['bg'])
        c.roundRect(0, 0, self.width, self._height, 4, fill=1, stroke=0)
        # Left bar
        c.setFillColor(meta['bar'])
        c.rect(0, 0, 5, self._height, fill=1, stroke=0)

        pad_x = 12 + 5
        pad_y = 9
        inner_w = self.width - pad_x - 12
        # Layout content top-down (Platypus origin = bottom-left)
        y_cursor = self._height - pad_y
        _, h_title = self._title_p.wrap(inner_w, 1000)
        y_cursor -= h_title
        self._title_p.drawOn(c, pad_x, y_cursor)
        y_cursor -= 6
        for p in self._body_ps:
            _, ph = p.wrap(inner_w, 1000)
            y_cursor -= ph
            p.drawOn(c, pad_x, y_cursor)
            y_cursor -= 3


# ---------------------------------------------------------------------------
# COLOR SWATCH FLOWABLE — for the visual system chapter
# ---------------------------------------------------------------------------
class Swatch(Flowable):
    def __init__(self, name, hex_code, role, color, text_on='auto', width=2.25*inch, height=1.05*inch):
        super().__init__()
        self.name = name
        self.hex_code = hex_code
        self.role = role
        self.color = color
        self.width = width
        self.height = height
        if text_on == 'auto':
            r, g, b = color.red, color.green, color.blue
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            self.text_on = white if lum < 0.55 else INK_PAPER
        else:
            self.text_on = text_on

    def wrap(self, *_):
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(self.color)
        c.setStrokeColor(self.color)
        c.roundRect(0, 0, self.width, self.height, 4, fill=1, stroke=0)
        c.setFillColor(self.text_on)
        c.setFont('Helvetica-Bold', 10)
        c.drawString(10, self.height - 18, self.name)
        c.setFont('Courier', 8)
        c.drawString(10, self.height - 32, self.hex_code.upper())
        c.setFont('Helvetica-Oblique', 7.5)
        c.drawString(10, 10, self.role)


def swatch_grid(rows):
    """rows = list of list of (name, hex, role, color) tuples"""
    cells = []
    for r in rows:
        cells.append([Swatch(n, h, role, col) for (n, h, role, col) in r])
    t = Table(cells, hAlign='LEFT', colWidths=[2.35*inch] * 3)
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return t


# ---------------------------------------------------------------------------
# Helpers for paragraph lists
# ---------------------------------------------------------------------------
def bullets(items, styles, key='bullet'):
    """Render a tight list of bullet paragraphs."""
    return [Paragraph(u'•  ' + it, styles[key]) for it in items]


def labeled_bullets(pairs, styles):
    """Bullets formatted as <b>label</b> — body."""
    out = []
    for label, body in pairs:
        out.append(Paragraph(
            u'•  <b>%s</b> &mdash; %s' % (label, body),
            styles['bullet']))
    return out


def hr(color=HAIRLINE, width='100%', thickness=0.5, space_before=4, space_after=8):
    return HRFlowable(width=width, thickness=thickness, color=color,
                      spaceBefore=space_before, spaceAfter=space_after,
                      hAlign='LEFT')


def small_table(rows, col_widths, styles, header=True):
    """Build a clean table with a top header row in brass."""
    t = Table(rows, colWidths=col_widths, hAlign='LEFT')
    style = [
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 9),
        ('TEXTCOLOR', (0, 0), (-1, -1), INK_PAPER),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LINEBELOW', (0, 0), (-1, -1), 0.25, HAIRLINE),
    ]
    if header:
        style += [
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 8.5),
            ('TEXTCOLOR', (0, 0), (-1, 0), BRASS),
            ('LINEBELOW', (0, 0), (-1, 0), 0.75, BRASS),
        ]
    t.setStyle(TableStyle(style))
    return t
