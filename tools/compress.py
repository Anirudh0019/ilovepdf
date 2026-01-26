import pikepdf
from pathlib import Path
from PIL import Image
import io


# Image quality for recompression (JPEG quality 0-100)
QUALITY_SETTINGS = {
    "low": {"image_quality": 30, "scale": 0.5},      # Aggressive - smallest file
    "medium": {"image_quality": 60, "scale": 0.75}, # Balanced
    "high": {"image_quality": 85, "scale": 1.0},    # Minimal loss
}


def compress_pdf(input_path: Path, output_path: Path, quality: str = "medium") -> dict:
    """
    Compress PDF file to reduce size.

    Returns dict with original_size and compressed_size for reporting.
    """
    settings = QUALITY_SETTINGS.get(quality, QUALITY_SETTINGS["medium"])
    original_size = input_path.stat().st_size

    with pikepdf.open(input_path) as pdf:
        # Recompress images within the PDF
        for page in pdf.pages:
            _compress_page_images(page, settings)

        # Remove unreferenced resources
        pdf.remove_unreferenced_resources()

        # Save with compression
        pdf.save(
            output_path,
            compress_streams=True,
            object_stream_mode=pikepdf.ObjectStreamMode.generate,
            recompress_flate=True,
        )

    compressed_size = output_path.stat().st_size

    return {
        "original_size": original_size,
        "compressed_size": compressed_size,
        "reduction_percent": round((1 - compressed_size / original_size) * 100, 1) if original_size > 0 else 0
    }


def _compress_page_images(page, settings: dict) -> None:
    """Compress images within a PDF page."""
    try:
        if "/Resources" not in page:
            return

        resources = page["/Resources"]
        if "/XObject" not in resources:
            return

        xobjects = resources["/XObject"]

        for key in list(xobjects.keys()):
            try:
                xobj = xobjects[key]
                if not isinstance(xobj, pikepdf.Stream):
                    continue

                # Check if it's an image
                if xobj.get("/Subtype") != "/Image":
                    continue

                # Get image properties
                width = int(xobj.get("/Width", 0))
                height = int(xobj.get("/Height", 0))

                if width == 0 or height == 0:
                    continue

                # Skip small images (icons, etc.)
                if width < 100 or height < 100:
                    continue

                # Try to extract and recompress the image
                _recompress_image(xobj, settings)

            except Exception:
                # Skip images that can't be processed
                continue

    except Exception:
        pass


def _recompress_image(xobj: pikepdf.Stream, settings: dict) -> None:
    """Recompress a single image stream."""
    try:
        # Get raw image data
        raw_data = xobj.read_raw_bytes()

        # Get image dimensions
        width = int(xobj.get("/Width", 0))
        height = int(xobj.get("/Height", 0))
        color_space = xobj.get("/ColorSpace", "/DeviceRGB")

        # Determine mode based on color space
        if str(color_space) == "/DeviceGray":
            mode = "L"
        elif str(color_space) == "/DeviceCMYK":
            mode = "CMYK"
        else:
            mode = "RGB"

        # Check bits per component
        bpc = int(xobj.get("/BitsPerComponent", 8))
        if bpc != 8:
            return  # Skip non-8-bit images

        # Check current filter
        current_filter = xobj.get("/Filter")

        # Handle DCT (JPEG) encoded images
        if current_filter == "/DCTDecode":
            # Already JPEG - try to recompress at lower quality
            try:
                img = Image.open(io.BytesIO(raw_data))

                # Scale down if needed
                if settings["scale"] < 1.0:
                    new_width = int(img.width * settings["scale"])
                    new_height = int(img.height * settings["scale"])
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # Recompress
                output = io.BytesIO()
                if img.mode == "RGBA":
                    img = img.convert("RGB")
                img.save(output, format="JPEG", quality=settings["image_quality"], optimize=True)

                # Update the stream
                xobj.write(output.getvalue(), filter=pikepdf.Name("/DCTDecode"))

                # Update dimensions if scaled
                if settings["scale"] < 1.0:
                    xobj["/Width"] = new_width
                    xobj["/Height"] = new_height

            except Exception:
                pass

        # Handle FlateDecode (raw compressed) images
        elif current_filter == "/FlateDecode" or current_filter is None:
            try:
                # Decompress and convert to JPEG
                raw = xobj.read_bytes()

                # Calculate expected size
                components = 3 if mode == "RGB" else (4 if mode == "CMYK" else 1)
                expected_size = width * height * components

                if len(raw) != expected_size:
                    return  # Size mismatch, skip

                img = Image.frombytes(mode, (width, height), raw)

                # Scale down if needed
                if settings["scale"] < 1.0:
                    new_width = int(width * settings["scale"])
                    new_height = int(height * settings["scale"])
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                else:
                    new_width, new_height = width, height

                # Convert to JPEG
                if img.mode == "CMYK":
                    img = img.convert("RGB")
                if img.mode == "RGBA":
                    img = img.convert("RGB")

                output = io.BytesIO()
                img.save(output, format="JPEG", quality=settings["image_quality"], optimize=True)

                # Update the stream
                xobj.write(output.getvalue(), filter=pikepdf.Name("/DCTDecode"))
                xobj["/ColorSpace"] = pikepdf.Name("/DeviceRGB")
                xobj["/Width"] = new_width
                xobj["/Height"] = new_height

            except Exception:
                pass

    except Exception:
        pass
