"""
pdf_generator.py
Builds the polished "Smart Notes" output PDF from the structured data
produced by extractor.process_pdf().
"""

import re
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, HRFlowable
)


def _highlight(text: str, keywords) -> str:
    """Bold+color any keyword occurrences inside a sentence (XML-escaped first)."""
    safe = escape(text)
    for kw in sorted(set(keywords), key=len, reverse=True):
        if not kw or len(kw) < 3:
            continue
        pattern = re.compile(r"(?<!\w)(" + re.escape(kw) + r")(?!\w)", re.I)
        safe = pattern.sub(r'<b><font color="#b5451b">\1</font></b>', safe)
    return safe


def build_notes_pdf(output_path: str, source_filename: str, data: dict):
    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("TitleX", parent=styles["Title"], fontSize=22, spaceAfter=4)
    subtitle_style = ParagraphStyle("Subtitle", parent=styles["Normal"], textColor=colors.grey, spaceAfter=18)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], textColor=colors.HexColor("#1a3c6e"), spaceBefore=16, spaceAfter=6)
    bullet_style = ParagraphStyle("Bullet", parent=styles["Normal"], fontSize=10.5, leading=15)
    topic_style = ParagraphStyle("Topic", parent=styles["Normal"], fontSize=11, leading=16)

    story = []
    story.append(Paragraph("📘 Smart Notes", title_style))
    story.append(Paragraph(f"Generated from: {escape(source_filename)} &nbsp;|&nbsp; {data['page_count']} page(s) analyzed", subtitle_style))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#cccccc")))

    # Important topics box
    story.append(Paragraph("⭐ Important Topics", h2))
    topic_items = [
        ListItem(Paragraph(escape(t), topic_style), bulletColor=colors.HexColor("#b5451b"))
        for t in data["important_topics"]
    ]
    if topic_items:
        story.append(ListFlowable(topic_items, bulletType="bullet", start="circle", leftIndent=18))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#cccccc")))

    # Condensed section notes
    for section in data["sections"]:
        if not section["summary_points"]:
            continue
        story.append(Paragraph(escape(section["heading"]), h2))
        bullets = [
            ListItem(Paragraph(_highlight(point, section["keywords"] + data["keywords"]), bullet_style))
            for point in section["summary_points"]
        ]
        story.append(ListFlowable(bullets, bulletType="bullet", leftIndent=18, spaceBefore=2))

    if not data["sections"]:
        story.append(Paragraph("No readable text was found in this PDF (it may be a scanned/image-only document).", styles["Normal"]))

    doc.build(story)
    return output_path
