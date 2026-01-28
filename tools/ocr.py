from pathlib import Path
from PIL import Image
import pytesseract
from pdf2image import convert_from_path


def image_to_text(input_path: Path, language: str = "eng") -> str:
    """
    Extract text from an image using Tesseract OCR.

    Args:
        input_path: Path to image file (PNG, JPG, etc.)
        language: Tesseract language code (eng, fra, deu, spa, etc.)

    Returns:
        Extracted text string
    """
    img = Image.open(input_path)

    # Convert to RGB if necessary
    if img.mode != "RGB":
        img = img.convert("RGB")

    text = pytesseract.image_to_string(img, lang=language)
    return text.strip()


def pdf_to_text_ocr(input_path: Path, language: str = "eng", dpi: int = 300) -> str:
    """
    Extract text from a scanned PDF using OCR.

    Args:
        input_path: Path to PDF file
        language: Tesseract language code
        dpi: Resolution for PDF to image conversion

    Returns:
        Extracted text from all pages
    """
    # Convert PDF pages to images
    images = convert_from_path(str(input_path), dpi=dpi)

    all_text = []
    for i, img in enumerate(images):
        # Convert to RGB if necessary
        if img.mode != "RGB":
            img = img.convert("RGB")

        page_text = pytesseract.image_to_string(img, lang=language)
        if page_text.strip():
            all_text.append(f"--- Page {i + 1} ---\n{page_text.strip()}")

    return "\n\n".join(all_text)


def get_available_languages() -> list[str]:
    """Get list of installed Tesseract languages."""
    try:
        langs = pytesseract.get_languages()
        # Filter out 'osd' (orientation/script detection)
        return [lang for lang in langs if lang != "osd"]
    except Exception:
        return ["eng"]  # Default fallback
