FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # PDF processing
    poppler-utils \
    libpoppler-cpp-dev \
    # LibreOffice for Word to PDF conversion
    libreoffice-writer \
    libreoffice-common \
    # Tesseract OCR
    tesseract-ocr \
    tesseract-ocr-eng \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application code
COPY . .

# Create temp directory for uploads
RUN mkdir -p temp_uploads

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120", "app:app"]
