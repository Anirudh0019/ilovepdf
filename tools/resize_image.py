from PIL import Image
from pathlib import Path


def resize_image(
    input_path: Path,
    output_path: Path,
    width: int,
    height: int,
    maintain_aspect: bool = False,
) -> None:
    """Resize image to exact dimensions (pixel-perfect matching)."""
    with Image.open(input_path) as img:
        # Convert to RGB if necessary (for JPEG output)
        if img.mode in ("RGBA", "P") and output_path.suffix.lower() in (".jpg", ".jpeg"):
            img = img.convert("RGB")

        if maintain_aspect:
            img.thumbnail((width, height), Image.Resampling.LANCZOS)
        else:
            img = img.resize((width, height), Image.Resampling.LANCZOS)

        img.save(output_path, quality=95)


def compress_image(input_path: Path, output_path: Path, quality: int = 85) -> None:
    """Compress image while maintaining reasonable quality."""
    with Image.open(input_path) as img:
        # Convert to RGB if necessary (for JPEG output)
        if img.mode in ("RGBA", "P"):
            # For PNG with transparency, keep as PNG
            if output_path.suffix.lower() == ".png":
                img.save(output_path, optimize=True)
                return
            img = img.convert("RGB")

        img.save(output_path, quality=quality, optimize=True)


def match_dimensions(
    image1_path: Path, image2_path: Path, output_path: Path
) -> None:
    """Resize image1 to exactly match image2's dimensions."""
    with Image.open(image2_path) as ref_img:
        target_size = ref_img.size

    resize_image(image1_path, output_path, target_size[0], target_size[1])
