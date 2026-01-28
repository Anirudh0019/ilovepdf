import os
import uuid
import shutil
from pathlib import Path
from flask import Flask, request, send_file, jsonify, render_template, after_this_request
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Import our PDF tools
from tools.merge import merge_pdfs
from tools.split import split_pdf
from tools.compress import compress_pdf
from tools.resize_image import resize_image, compress_image
from tools.watermark import add_watermark
from tools.word_to_pdf import word_to_pdf
from tools.pdf_to_images import pdf_to_images
from tools.sign_pdf import sign_pdf_with_text, sign_pdf_with_image
from tools.ocr import image_to_text, pdf_to_text_ocr
import base64

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = Path("temp_uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB max

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "gif", "webp", "docx", "doc"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_temp_dir():
    """Create a unique temp directory for this request"""
    temp_dir = UPLOAD_FOLDER / str(uuid.uuid4())
    temp_dir.mkdir(exist_ok=True)
    return temp_dir


def cleanup_temp_dir(temp_dir):
    """Immediately delete temp directory and all contents"""
    try:
        shutil.rmtree(temp_dir)
    except Exception as e:
        print(f"Cleanup error: {e}")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/merge", methods=["POST"])
def api_merge():
    """Merge multiple PDFs into one"""
    if "files" not in request.files:
        return jsonify({"error": "No files provided"}), 400

    files = request.files.getlist("files")
    if len(files) < 2:
        return jsonify({"error": "Need at least 2 PDFs to merge"}), 400

    temp_dir = get_temp_dir()
    try:
        # Save uploaded files
        pdf_paths = []
        for f in files:
            if f and allowed_file(f.filename):
                filename = secure_filename(f.filename)
                filepath = temp_dir / filename
                f.save(filepath)
                pdf_paths.append(filepath)

        if len(pdf_paths) < 2:
            cleanup_temp_dir(temp_dir)
            return jsonify({"error": "Need at least 2 valid PDFs"}), 400

        # Merge PDFs
        output_path = temp_dir / "merged.pdf"
        merge_pdfs(pdf_paths, output_path)

        @after_this_request
        def cleanup(response):
            cleanup_temp_dir(temp_dir)
            return response

        return send_file(
            output_path,
            as_attachment=True,
            download_name="merged.pdf",
            mimetype="application/pdf",
        )
    except Exception as e:
        cleanup_temp_dir(temp_dir)
        return jsonify({"error": str(e)}), 500


@app.route("/api/split", methods=["POST"])
def api_split():
    """Split PDF into individual pages or by range"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    pages = request.form.get("pages", "all")  # "all" or "1,3,5-7"

    temp_dir = get_temp_dir()
    try:
        filename = secure_filename(file.filename)
        filepath = temp_dir / filename
        file.save(filepath)

        output_dir = temp_dir / "split_output"
        output_dir.mkdir()

        split_pdf(filepath, output_dir, pages)

        # Create zip of split PDFs
        zip_path = temp_dir / "split_pages"
        shutil.make_archive(str(zip_path), "zip", output_dir)

        @after_this_request
        def cleanup(response):
            cleanup_temp_dir(temp_dir)
            return response

        return send_file(
            f"{zip_path}.zip",
            as_attachment=True,
            download_name="split_pages.zip",
            mimetype="application/zip",
        )
    except Exception as e:
        cleanup_temp_dir(temp_dir)
        return jsonify({"error": str(e)}), 500


@app.route("/api/compress", methods=["POST"])
def api_compress():
    """Compress a PDF"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    quality = request.form.get("quality", "medium")  # low, medium, high

    temp_dir = get_temp_dir()
    try:
        filename = secure_filename(file.filename)
        filepath = temp_dir / filename
        file.save(filepath)

        output_path = temp_dir / f"compressed_{filename}"
        compress_pdf(filepath, output_path, quality)

        @after_this_request
        def cleanup(response):
            cleanup_temp_dir(temp_dir)
            return response

        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"compressed_{filename}",
            mimetype="application/pdf",
        )
    except Exception as e:
        cleanup_temp_dir(temp_dir)
        return jsonify({"error": str(e)}), 500


@app.route("/api/resize-image", methods=["POST"])
def api_resize_image():
    """Resize image to exact dimensions"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    width = request.form.get("width", type=int)
    height = request.form.get("height", type=int)

    if not width or not height:
        return jsonify({"error": "Width and height are required"}), 400

    temp_dir = get_temp_dir()
    try:
        filename = secure_filename(file.filename)
        filepath = temp_dir / filename
        file.save(filepath)

        output_path = temp_dir / f"resized_{filename}"
        resize_image(filepath, output_path, width, height)

        @after_this_request
        def cleanup(response):
            cleanup_temp_dir(temp_dir)
            return response

        ext = filename.rsplit(".", 1)[1].lower()
        mimetype = f"image/{ext}" if ext != "jpg" else "image/jpeg"

        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"resized_{filename}",
            mimetype=mimetype,
        )
    except Exception as e:
        cleanup_temp_dir(temp_dir)
        return jsonify({"error": str(e)}), 500


@app.route("/api/compress-image", methods=["POST"])
def api_compress_image():
    """Compress image while maintaining quality"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    quality = request.form.get("quality", 85, type=int)

    temp_dir = get_temp_dir()
    try:
        filename = secure_filename(file.filename)
        filepath = temp_dir / filename
        file.save(filepath)

        output_path = temp_dir / f"compressed_{filename}"
        compress_image(filepath, output_path, quality)

        @after_this_request
        def cleanup(response):
            cleanup_temp_dir(temp_dir)
            return response

        ext = filename.rsplit(".", 1)[1].lower()
        mimetype = f"image/{ext}" if ext != "jpg" else "image/jpeg"

        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"compressed_{filename}",
            mimetype=mimetype,
        )
    except Exception as e:
        cleanup_temp_dir(temp_dir)
        return jsonify({"error": str(e)}), 500


@app.route("/api/watermark", methods=["POST"])
def api_watermark():
    """Add watermark to PDF"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    text = request.form.get("text", "CONFIDENTIAL")
    opacity = request.form.get("opacity", 0.3, type=float)

    temp_dir = get_temp_dir()
    try:
        filename = secure_filename(file.filename)
        filepath = temp_dir / filename
        file.save(filepath)

        output_path = temp_dir / f"watermarked_{filename}"
        add_watermark(filepath, output_path, text, opacity)

        @after_this_request
        def cleanup(response):
            cleanup_temp_dir(temp_dir)
            return response

        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"watermarked_{filename}",
            mimetype="application/pdf",
        )
    except Exception as e:
        cleanup_temp_dir(temp_dir)
        return jsonify({"error": str(e)}), 500


@app.route("/api/word-to-pdf", methods=["POST"])
def api_word_to_pdf():
    """Convert Word document to PDF"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]

    temp_dir = get_temp_dir()
    try:
        filename = secure_filename(file.filename)
        filepath = temp_dir / filename
        file.save(filepath)

        output_path = temp_dir / f"{filepath.stem}.pdf"
        word_to_pdf(filepath, output_path)

        @after_this_request
        def cleanup(response):
            cleanup_temp_dir(temp_dir)
            return response

        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"{filepath.stem}.pdf",
            mimetype="application/pdf",
        )
    except Exception as e:
        cleanup_temp_dir(temp_dir)
        return jsonify({"error": str(e)}), 500


@app.route("/api/pdf-to-images", methods=["POST"])
def api_pdf_to_images():
    """Convert PDF pages to images"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    format = request.form.get("format", "png")
    dpi = request.form.get("dpi", 150, type=int)

    temp_dir = get_temp_dir()
    try:
        filename = secure_filename(file.filename)
        filepath = temp_dir / filename
        file.save(filepath)

        output_dir = temp_dir / "images"
        output_dir.mkdir()

        output_files = pdf_to_images(filepath, output_dir, format, dpi)

        @after_this_request
        def cleanup(response):
            cleanup_temp_dir(temp_dir)
            return response

        # Single page PDF - return the image directly
        if len(output_files) == 1:
            mimetype = f"image/{format}" if format != "jpg" else "image/jpeg"
            return send_file(
                output_files[0],
                as_attachment=True,
                download_name=f"{filepath.stem}.{format}",
                mimetype=mimetype,
            )

        # Multiple pages - return zip
        zip_path = temp_dir / "pdf_images"
        shutil.make_archive(str(zip_path), "zip", output_dir)

        return send_file(
            f"{zip_path}.zip",
            as_attachment=True,
            download_name="pdf_images.zip",
            mimetype="application/zip",
        )
    except Exception as e:
        cleanup_temp_dir(temp_dir)
        return jsonify({"error": str(e)}), 500


@app.route("/api/sign-text", methods=["POST"])
def api_sign_text():
    """Add text signature to PDF"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    text = request.form.get("text", "")
    if not text:
        return jsonify({"error": "Signature text is required"}), 400

    position = request.form.get("position", "bottom-right")
    pages = request.form.get("pages", "last")
    font_size = request.form.get("font_size", 24, type=int)
    include_date = request.form.get("include_date", "false").lower() == "true"

    temp_dir = get_temp_dir()
    try:
        filename = secure_filename(file.filename)
        filepath = temp_dir / filename
        file.save(filepath)

        output_path = temp_dir / f"signed_{filename}"
        sign_pdf_with_text(
            filepath, output_path, text, position, pages, font_size, include_date
        )

        @after_this_request
        def cleanup(response):
            cleanup_temp_dir(temp_dir)
            return response

        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"signed_{filename}",
            mimetype="application/pdf",
        )
    except Exception as e:
        cleanup_temp_dir(temp_dir)
        return jsonify({"error": str(e)}), 500


@app.route("/api/sign-image", methods=["POST"])
def api_sign_image():
    """Add drawn signature image to PDF"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    signature_data = request.form.get("signature", "")

    if not signature_data:
        return jsonify({"error": "Signature image is required"}), 400

    # Handle base64 data URL from canvas
    if signature_data.startswith("data:"):
        signature_data = signature_data.split(",")[1]

    try:
        image_bytes = base64.b64decode(signature_data)
    except Exception:
        return jsonify({"error": "Invalid signature image data"}), 400

    position = request.form.get("position", "bottom-right")
    pages = request.form.get("pages", "last")
    sig_width = request.form.get("sig_width", 150, type=int)
    include_date = request.form.get("include_date", "false").lower() == "true"

    temp_dir = get_temp_dir()
    try:
        filename = secure_filename(file.filename)
        filepath = temp_dir / filename
        file.save(filepath)

        output_path = temp_dir / f"signed_{filename}"
        sign_pdf_with_image(
            filepath, output_path, image_bytes, position, pages, sig_width, include_date
        )

        @after_this_request
        def cleanup(response):
            cleanup_temp_dir(temp_dir)
            return response

        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"signed_{filename}",
            mimetype="application/pdf",
        )
    except Exception as e:
        cleanup_temp_dir(temp_dir)
        return jsonify({"error": str(e)}), 500


@app.route("/api/ocr", methods=["POST"])
def api_ocr():
    """Extract text from image or PDF using OCR"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    language = request.form.get("language", "eng")

    temp_dir = get_temp_dir()
    try:
        filename = secure_filename(file.filename)
        filepath = temp_dir / filename
        file.save(filepath)

        # Determine if it's a PDF or image
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if ext == "pdf":
            text = pdf_to_text_ocr(filepath, language)
        else:
            text = image_to_text(filepath, language)

        cleanup_temp_dir(temp_dir)

        return jsonify({
            "success": True,
            "text": text,
            "filename": filename,
        })
    except Exception as e:
        cleanup_temp_dir(temp_dir)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
