from PyPDF2 import PdfReader, PdfWriter
from pathlib import Path


def parse_page_range(pages_str: str, total_pages: int) -> list[int]:
    """Parse page range string like '1,3,5-7' into list of page indices (0-based)."""
    if pages_str.lower() == "all":
        return list(range(total_pages))

    pages = []
    parts = pages_str.split(",")

    for part in parts:
        part = part.strip()
        if "-" in part:
            start, end = part.split("-")
            start = int(start) - 1  # Convert to 0-based
            end = int(end)  # End is inclusive, so no -1
            pages.extend(range(start, min(end, total_pages)))
        else:
            page = int(part) - 1  # Convert to 0-based
            if 0 <= page < total_pages:
                pages.append(page)

    return sorted(set(pages))


def split_pdf(input_path: Path, output_dir: Path, pages: str = "all") -> list[Path]:
    """Split PDF into individual pages or by specified range."""
    reader = PdfReader(str(input_path))
    total_pages = len(reader.pages)

    page_indices = parse_page_range(pages, total_pages)
    output_files = []

    for i, page_idx in enumerate(page_indices):
        writer = PdfWriter()
        writer.add_page(reader.pages[page_idx])

        output_path = output_dir / f"page_{page_idx + 1}.pdf"
        with open(output_path, "wb") as f:
            writer.write(f)
        output_files.append(output_path)

    return output_files
