"""
Document Validation Module

Validates uploaded identity documents using format-specific detection.
Image formats (JPEG, PNG) are validated with Pillow, which parses the
file header and verifies structural integrity rather than relying on
client-supplied MIME types or file extensions. PDF files are identified
by the ``%PDF`` prefix as specified in ISO 32000.

Supported formats:
    - PDF  (prefix: ``%PDF``, validated manually)
    - JPEG, PNG (validated via Pillow: header parse + structural verify)

Maximum file size: 10 MB.
"""

import io
import logging

from PIL import Image

logger = logging.getLogger(__name__)

# Constraints
MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# Pillow format names mapped to canonical MIME types
_PILLOW_FORMAT_TO_MIME = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
}

ALLOWED_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}


class DocumentValidationError(Exception):
    """Raised when document validation fails."""

    pass


def validate_document(data: bytes, claimed_content_type: str = "") -> str:
    """
    Validate raw document bytes and return the detected MIME type.

    The function checks three properties:
        1. The file is non-empty.
        2. The file size does not exceed ``MAX_DOCUMENT_SIZE_BYTES``.
        3. The content is a valid PDF, JPEG, or PNG.

    For images, Pillow's ``Image.open()`` and ``verify()`` are used
    to confirm both the format and structural integrity, matching
    the validation approach used for avatar uploads. PDF files are
    identified by the ``%PDF`` prefix (ISO 32000).

    Args:
        data: Raw file bytes.
        claimed_content_type: Optional MIME type supplied by the client.
            Used only for logging; the authoritative type is determined
            from file content.

    Returns:
        The detected MIME type (e.g. ``"application/pdf"``).

    Raises:
        DocumentValidationError: If the file exceeds the size limit,
            is empty, or does not match any supported format.
    """
    if not data:
        raise DocumentValidationError("Empty file")

    if len(data) > MAX_DOCUMENT_SIZE_BYTES:
        raise DocumentValidationError(
            f"File size {len(data)} bytes exceeds maximum of "
            f"{MAX_DOCUMENT_SIZE_BYTES} bytes (10 MB)"
        )

    # PDF: Pillow cannot parse PDFs, so check the prefix manually
    if data[:4] == b"%PDF":
        if claimed_content_type and claimed_content_type != "application/pdf":
            logger.warning(
                "Client claimed content type '%s' but file is PDF",
                claimed_content_type,
            )
        return "application/pdf"

    # Images: delegate to Pillow for header parsing + structural verification
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
    except Exception:
        raise DocumentValidationError(
            "Unsupported document format. Accepted formats: PDF, JPEG, PNG"
        )

    detected_format = img.format
    mime_type = _PILLOW_FORMAT_TO_MIME.get(detected_format or "")
    if mime_type is None:
        raise DocumentValidationError(
            f"Image format '{detected_format}' is not allowed. "
            "Accepted formats: PDF, JPEG, PNG"
        )

    if claimed_content_type and claimed_content_type != mime_type:
        logger.warning(
            "Client claimed content type '%s' but Pillow detected '%s'",
            claimed_content_type,
            mime_type,
        )

    return mime_type
