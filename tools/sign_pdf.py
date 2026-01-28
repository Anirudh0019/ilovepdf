from pathlib import Path
import io
import base64
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image
from datetime import datetime


# Position presets (as percentage of page)
POSITIONS = {
    "bottom-right": (0.95, 0.05),  # x from left, y from bottom
    "bottom-left": (0.05, 0.05),
    "bottom-center": (0.5, 0.05),
    "top-right": (0.95, 0.95),
    "top-left": (0.05, 0.95),
    "top-center": (0.5, 0.95),
}


def create_text_signature_overlay(
    text: str,
    page_width: float,
    page_height: float,
    position: str = "bottom-right",
    font_size: int = 24,
    include_date: bool = False,
    color: tuple = (0, 0, 0.5),  # Dark blue
) -> bytes:
    """Create a PDF overlay with text signature."""
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))

    # Get position
    pos_x_pct, pos_y_pct = POSITIONS.get(position, POSITIONS["bottom-right"])

    # Calculate actual position
    x = page_width * pos_x_pct
    y = page_height * pos_y_pct

    # Prepare signature text
    sig_text = text
    if include_date:
        date_str = datetime.now().strftime("%Y-%m-%d")
        sig_text = f"{text}\n{date_str}"

    # Set font - use Helvetica-Oblique for a slight cursive feel
    # (True handwriting fonts would need to be bundled)
    c.setFont("Helvetica-Oblique", font_size)
    c.setFillColor(Color(color[0], color[1], color[2]))

    # Adjust position based on alignment
    if "right" in position:
        c.drawRightString(x - 20, y + 20, text)
        if include_date:
            c.setFont("Helvetica", font_size * 0.6)
            c.drawRightString(x - 20, y + 5, date_str)
    elif "center" in position:
        c.drawCentredString(x, y + 20, text)
        if include_date:
            c.setFont("Helvetica", font_size * 0.6)
            c.drawCentredString(x, y + 5, date_str)
    else:  # left
        c.drawString(x + 20, y + 20, text)
        if include_date:
            c.setFont("Helvetica", font_size * 0.6)
            c.drawString(x + 20, y + 5, date_str)

    c.save()
    packet.seek(0)
    return packet.getvalue()


def create_image_signature_overlay(
    image_data: bytes,
    page_width: float,
    page_height: float,
    position: str = "bottom-right",
    sig_width: int = 150,
    include_date: bool = False,
) -> bytes:
    """Create a PDF overlay with image signature."""
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))

    # Load signature image
    img = Image.open(io.BytesIO(image_data))

    # Convert RGBA to RGB if needed (for PDF compatibility)
    if img.mode == "RGBA":
        # Create white background
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background

    # Calculate signature dimensions maintaining aspect ratio
    aspect = img.height / img.width
    sig_height = int(sig_width * aspect)

    # Get position
    pos_x_pct, pos_y_pct = POSITIONS.get(position, POSITIONS["bottom-right"])

    # Calculate actual position
    x = page_width * pos_x_pct
    y = page_height * pos_y_pct

    # Adjust for signature size and alignment
    if "right" in position:
        x = x - sig_width - 20
    elif "center" in position:
        x = x - sig_width / 2
    else:
        x = x + 20

    if "top" in position:
        y = y - sig_height - 20
    else:
        y = y + 20

    # Save image to temp bytes for reportlab
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    img_buffer.seek(0)

    # Draw image
    from reportlab.lib.utils import ImageReader
    c.drawImage(ImageReader(img_buffer), x, y, width=sig_width, height=sig_height)

    # Add date if requested
    if include_date:
        date_str = datetime.now().strftime("%Y-%m-%d")
        c.setFont("Helvetica", 10)
        c.setFillColor(Color(0, 0, 0))
        if "right" in position:
            c.drawRightString(x + sig_width, y - 5, date_str)
        elif "center" in position:
            c.drawCentredString(x + sig_width / 2, y - 5, date_str)
        else:
            c.drawString(x, y - 5, date_str)

    c.save()
    packet.seek(0)
    return packet.getvalue()


def sign_pdf_with_text(
    input_path: Path,
    output_path: Path,
    text: str,
    position: str = "bottom-right",
    pages: str = "last",  # "all", "first", "last", or "1,3,5"
    font_size: int = 24,
    include_date: bool = False,
) -> None:
    """Add text signature to PDF."""
    reader = PdfReader(str(input_path))
    writer = PdfWriter()

    total_pages = len(reader.pages)
    pages_to_sign = _parse_pages(pages, total_pages)

    for i, page in enumerate(reader.pages):
        if i in pages_to_sign:
            # Get page dimensions
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)

            # Create signature overlay
            sig_bytes = create_text_signature_overlay(
                text, page_width, page_height, position, font_size, include_date
            )
            sig_reader = PdfReader(io.BytesIO(sig_bytes))
            sig_page = sig_reader.pages[0]

            # Merge signature with page
            page.merge_page(sig_page)

        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)


def sign_pdf_with_image(
    input_path: Path,
    output_path: Path,
    image_data: bytes,
    position: str = "bottom-right",
    pages: str = "last",
    sig_width: int = 150,
    include_date: bool = False,
) -> None:
    """Add image signature to PDF."""
    reader = PdfReader(str(input_path))
    writer = PdfWriter()

    total_pages = len(reader.pages)
    pages_to_sign = _parse_pages(pages, total_pages)

    for i, page in enumerate(reader.pages):
        if i in pages_to_sign:
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)

            sig_bytes = create_image_signature_overlay(
                image_data, page_width, page_height, position, sig_width, include_date
            )
            sig_reader = PdfReader(io.BytesIO(sig_bytes))
            sig_page = sig_reader.pages[0]

            page.merge_page(sig_page)

        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)


def _parse_pages(pages: str, total: int) -> set[int]:
    """Parse page selection string to set of 0-based indices."""
    if pages == "all":
        return set(range(total))
    elif pages == "first":
        return {0}
    elif pages == "last":
        return {total - 1}
    else:
        # Parse comma-separated list
        result = set()
        for part in pages.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-")
                result.update(range(int(start) - 1, int(end)))
            else:
                result.add(int(part) - 1)
        return {p for p in result if 0 <= p < total}
