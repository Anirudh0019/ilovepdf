from pathlib import Path
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY


def word_to_pdf(input_path: Path, output_path: Path) -> None:
    """
    Convert Word document to PDF.
    Note: This is a basic conversion that handles text content.
    Complex formatting, images, and tables may not be perfectly preserved.
    """
    doc = Document(str(input_path))

    # Create PDF
    pdf = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )

    styles = getSampleStyleSheet()
    story = []

    # Add custom styles
    styles.add(
        ParagraphStyle(
            name="CustomBody",
            parent=styles["Normal"],
            fontSize=11,
            leading=14,
            spaceAfter=12,
        )
    )

    styles.add(
        ParagraphStyle(
            name="CustomHeading",
            parent=styles["Heading1"],
            fontSize=16,
            leading=20,
            spaceAfter=12,
            spaceBefore=12,
        )
    )

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            story.append(Spacer(1, 12))
            continue

        # Detect headings by style name
        style_name = para.style.name.lower() if para.style else ""

        if "heading" in style_name:
            story.append(Paragraph(text, styles["CustomHeading"]))
        else:
            story.append(Paragraph(text, styles["CustomBody"]))

    if story:
        pdf.build(story)
    else:
        # Create empty PDF with a note
        story.append(Paragraph("(Empty document)", styles["Normal"]))
        pdf.build(story)
