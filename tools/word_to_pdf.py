from pathlib import Path
import subprocess
import shutil


def word_to_pdf(input_path: Path, output_path: Path) -> None:
    """
    Convert Word document to PDF using LibreOffice.
    Preserves formatting, tables, images, and styles.
    """
    # Check if LibreOffice is available
    libreoffice_cmd = _find_libreoffice()

    if libreoffice_cmd:
        _convert_with_libreoffice(input_path, output_path, libreoffice_cmd)
    else:
        # Fallback to basic conversion if LibreOffice not available
        _convert_basic(input_path, output_path)


def _find_libreoffice() -> str | None:
    """Find LibreOffice executable."""
    # Common locations
    candidates = [
        "libreoffice",
        "soffice",
        "/usr/bin/libreoffice",
        "/usr/bin/soffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ]

    for cmd in candidates:
        if shutil.which(cmd):
            return cmd

    return None


def _convert_with_libreoffice(input_path: Path, output_path: Path, libreoffice_cmd: str) -> None:
    """Convert using LibreOffice headless mode."""
    output_dir = output_path.parent

    # Run LibreOffice in headless mode
    result = subprocess.run(
        [
            libreoffice_cmd,
            "--headless",
            "--convert-to", "pdf",
            "--outdir", str(output_dir),
            str(input_path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice conversion failed: {result.stderr}")

    # LibreOffice outputs with same name but .pdf extension
    generated_pdf = output_dir / f"{input_path.stem}.pdf"

    # Rename if needed
    if generated_pdf != output_path and generated_pdf.exists():
        shutil.move(str(generated_pdf), str(output_path))

    if not output_path.exists():
        raise RuntimeError("PDF conversion failed - output file not created")


def _convert_basic(input_path: Path, output_path: Path) -> None:
    """Fallback: Basic text-only conversion using reportlab."""
    from docx import Document
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    doc = Document(str(input_path))

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

        style_name = para.style.name.lower() if para.style else ""

        if "heading" in style_name:
            story.append(Paragraph(text, styles["CustomHeading"]))
        else:
            story.append(Paragraph(text, styles["CustomBody"]))

    if story:
        pdf.build(story)
    else:
        story.append(Paragraph("(Empty document)", styles["Normal"]))
        pdf.build(story)
