"""
Document validation using magic-byte detection (PDF, JPEG, PNG). Max 10 MB.
"""

import io
import logging

from PIL import Image

logger = logging.getLogger(__name__)

MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

_PILLOW_FORMAT_TO_MIME = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
}

ALLOWED_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}


class DocumentValidationError(Exception):
    """Raised when document validation fails."""

    pass


def validate_document(data: bytes, claimed_content_type: str = "") -> str:
    """Validate raw document bytes and return the detected MIME type."""
    if not data:
        raise DocumentValidationError("Empty file")

    if len(data) > MAX_DOCUMENT_SIZE_BYTES:
        raise DocumentValidationError(
            f"File size {len(data)} bytes exceeds maximum of "
            f"{MAX_DOCUMENT_SIZE_BYTES} bytes (10 MB)"
        )

    if data[:4] == b"%PDF":
        if claimed_content_type and claimed_content_type != "application/pdf":
            logger.warning(
                "Client claimed content type '%s' but file is PDF",
                claimed_content_type,
            )
        return "application/pdf"

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
            f"Image format '{detected_format}' is not allowed. Accepted formats: PDF, JPEG, PNG"
        )

    if claimed_content_type and claimed_content_type != mime_type:
        logger.warning(
            "Client claimed content type '%s' but Pillow detected '%s'",
            claimed_content_type,
            mime_type,
        )

    return mime_type
