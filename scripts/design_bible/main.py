"""Travel Concierge — Design Bible PDF generator (entry point)."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from styles import make_styles
from layout import make_doc, build_cover, build_toc, build_exec_summary
from content_part1 import build_section_1, build_section_2, build_section_3, build_section_4
from content_part2 import build_section_5, build_section_6, build_section_7, build_section_8
from content_part3 import (
    build_section_9, build_section_10, build_section_11, build_section_12,
    build_section_13, build_appendix,
)


def build(out_path):
    styles = make_styles()
    doc = make_doc(out_path)

    story = []
    build_cover(story, styles)
    build_toc(story, styles)
    build_exec_summary(story, styles)

    build_section_1(story, styles)
    build_section_2(story, styles)
    build_section_3(story, styles)
    build_section_4(story, styles)
    build_section_5(story, styles)
    build_section_6(story, styles)
    build_section_7(story, styles)
    build_section_8(story, styles)
    build_section_9(story, styles)
    build_section_10(story, styles)
    build_section_11(story, styles)
    build_section_12(story, styles)
    build_section_13(story, styles)
    build_appendix(story, styles)

    doc.build(story)


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'travel_concierge_design_bible.pdf'
    build(out)
    size = os.path.getsize(out)
    print('PDF written: %s (%.1f KB)' % (out, size / 1024.0))
