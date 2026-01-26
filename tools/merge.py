from PyPDF2 import PdfMerger
from pathlib import Path


def merge_pdfs(pdf_paths: list[Path], output_path: Path) -> None:
    """Merge multiple PDFs into a single PDF file."""
    merger = PdfMerger()

    for pdf_path in pdf_paths:
        merger.append(str(pdf_path))

    merger.write(str(output_path))
    merger.close()
