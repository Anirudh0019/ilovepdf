from pathlib import Path
import io
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import Color


def create_watermark_pdf(
    text: str, page_width: float, page_height: float, opacity: float = 0.3
) -> bytes:
    """Create a PDF with watermark text."""
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))

    # Set watermark properties
    c.setFillColor(Color(0.5, 0.5, 0.5, alpha=opacity))
    c.setFont("Helvetica-Bold", 60)

    # Rotate and center the watermark
    c.saveState()
    c.translate(page_width / 2, page_height / 2)
    c.rotate(45)
    c.drawCentredString(0, 0, text)
    c.restoreState()

    c.save()
    packet.seek(0)
    return packet.getvalue()


def add_watermark(
    input_path: Path, output_path: Path, text: str, opacity: float = 0.3
) -> None:
    """Add text watermark to all pages of a PDF."""
    reader = PdfReader(str(input_path))
    writer = PdfWriter()

    for page in reader.pages:
        # Get page dimensions
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)

        # Create watermark for this page size
        watermark_bytes = create_watermark_pdf(text, page_width, page_height, opacity)
        watermark_reader = PdfReader(io.BytesIO(watermark_bytes))
        watermark_page = watermark_reader.pages[0]

        # Merge watermark with page
        page.merge_page(watermark_page)
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)
