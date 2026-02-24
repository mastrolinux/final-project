"""Tests for document format detection, size limits, and format rejection."""

import io

import pytest
from PIL import Image

from src.core.document import (
    MAX_DOCUMENT_SIZE_BYTES,
    DocumentValidationError,
    validate_document,
)


def _make_image_bytes(fmt: str = "JPEG", size: tuple = (100, 100)) -> bytes:
    """Generate a structurally valid image of the given format."""
    img = Image.new("RGB", size, color="red")
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


PDF_HEADER = b"%PDF-1.4 fake pdf content"
JPEG_BYTES = _make_image_bytes("JPEG")
PNG_BYTES = _make_image_bytes("PNG")


class TestValidateDocument:
    """Tests for the validate_document function."""

    def test_valid_pdf(self):
        """PDF prefix must be detected correctly."""
        assert validate_document(PDF_HEADER) == "application/pdf"

    def test_valid_jpeg(self):
        """A valid JPEG image must be accepted via Pillow."""
        assert validate_document(JPEG_BYTES) == "image/jpeg"

    def test_valid_png(self):
        """A valid PNG image must be accepted via Pillow."""
        assert validate_document(PNG_BYTES) == "image/png"

    def test_empty_file_rejected(self):
        """Empty byte strings must be rejected."""
        with pytest.raises(DocumentValidationError, match="Empty file"):
            validate_document(b"")

    def test_exceeds_size_limit(self):
        """Files larger than 10 MB must be rejected."""
        oversized = PDF_HEADER + b"\x00" * (MAX_DOCUMENT_SIZE_BYTES + 1)
        with pytest.raises(DocumentValidationError, match="exceeds maximum"):
            validate_document(oversized)

    def test_exactly_at_size_limit(self):
        """A file at exactly 10 MB must be accepted."""
        data = b"%PDF" + b"\x00" * (MAX_DOCUMENT_SIZE_BYTES - 4)
        assert validate_document(data) == "application/pdf"

    def test_gif_format_rejected(self):
        """A valid GIF image must be rejected (format not allowed)."""
        gif_bytes = _make_image_bytes("GIF")
        with pytest.raises(DocumentValidationError, match="not allowed"):
            validate_document(gif_bytes)

    def test_random_bytes_rejected(self):
        """Random bytes that match no known format must be rejected."""
        with pytest.raises(DocumentValidationError, match="Unsupported document format"):
            validate_document(b"\x00\x01\x02\x03 random data")

    def test_bmp_format_rejected(self):
        """A valid BMP image must be rejected (format not allowed)."""
        bmp_bytes = _make_image_bytes("BMP")
        with pytest.raises(DocumentValidationError, match="not allowed"):
            validate_document(bmp_bytes)

    def test_claimed_content_type_ignored_for_detection(self):
        """The claimed MIME type does not affect detection logic."""
        result = validate_document(
            PDF_HEADER, claimed_content_type="image/jpeg"
        )
        assert result == "application/pdf"

    def test_claimed_content_type_matching(self):
        """When the claim matches the detected type, no warning is logged."""
        result = validate_document(
            JPEG_BYTES, claimed_content_type="image/jpeg"
        )
        assert result == "image/jpeg"

    def test_pdf_with_trailing_content(self):
        """PDF files with realistic content after the header must be accepted."""
        data = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
        assert validate_document(data) == "application/pdf"

    def test_jpeg_with_exif_metadata(self):
        """JPEG images with EXIF metadata must be accepted."""
        # Generate a JPEG with EXIF data via Pillow
        img = Image.new("RGB", (50, 50), color="blue")
        buf = io.BytesIO()
        # Pillow saves JPEG with JFIF by default; this produces a valid
        # JPEG that exercises the Pillow parsing path
        img.save(buf, format="JPEG", quality=85)
        assert validate_document(buf.getvalue()) == "image/jpeg"

    def test_png_rgba_accepted(self):
        """PNG images with an alpha channel must be accepted."""
        img = Image.new("RGBA", (50, 50), color=(255, 0, 0, 128))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        assert validate_document(buf.getvalue()) == "image/png"

    def test_claimed_mismatch_still_returns_detected(self):
        """When the claim differs from the actual format, the detected
        type is returned (not the claimed type)."""
        result = validate_document(
            PNG_BYTES, claimed_content_type="image/jpeg"
        )
        assert result == "image/png"
