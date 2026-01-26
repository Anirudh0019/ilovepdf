from pathlib import Path
from pdf2image import convert_from_path


def pdf_to_images(
    input_path: Path,
    output_dir: Path,
    format: str = "png",
    dpi: int = 150,
) -> list[Path]:
    """Convert PDF pages to images."""
    images = convert_from_path(str(input_path), dpi=dpi)
    output_files = []

    for i, image in enumerate(images):
        output_path = output_dir / f"page_{i + 1}.{format}"
        image.save(output_path, format.upper())
        output_files.append(output_path)

    return output_files
