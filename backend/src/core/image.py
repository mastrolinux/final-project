"""
Image Processing Module

Validates, resizes, and normalizes uploaded images for avatar storage.
All output is converted to WebP format for consistent compression and quality.

Validation uses Pillow's image parser (magic bytes) rather than file extensions,
preventing MIME spoofing attacks where a malicious file is renamed to .jpg.

Processing pipeline:
    1. Validate file size (max 5 MB)
    2. Parse image with Pillow (validates magic bytes)
    3. Reject disallowed formats (only JPEG, PNG, WebP accepted)
    4. Center-crop to square aspect ratio
    5. Resize to target dimensions (400x400 avatar, 80x80 thumbnail)
    6. Encode as WebP (quality 85)
"""

import io
import logging
from dataclasses import dataclass
from typing import Tuple

from PIL import Image

logger = logging.getLogger(__name__)

# Constraints
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
AVATAR_SIZE = (400, 400)
THUMBNAIL_SIZE = (80, 80)
WEBP_QUALITY = 85
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


class ImageProcessingError(Exception):
    """Raised when image validation or processing fails."""
    pass


@dataclass
class ProcessedImage:
    """Result of image processing: avatar and thumbnail as WebP bytes."""
    avatar: bytes
    thumbnail: bytes
    content_type: str = "image/webp"


def validate_image_bytes(data: bytes) -> Image.Image:
    """
    Validate raw bytes as a supported image format using Pillow's parser.

    Pillow reads the file header (magic bytes) to determine the actual format,
    independent of any file extension the client may have provided.

    Args:
        data: Raw file bytes

    Returns:
        Opened PIL Image

    Raises:
        ImageProcessingError: If the file exceeds the size limit, is not a
            valid image, or uses a disallowed format.
    """
    if len(data) > MAX_FILE_SIZE_BYTES:
        raise ImageProcessingError(
            f"File size {len(data)} bytes exceeds maximum of {MAX_FILE_SIZE_BYTES} bytes (5 MB)"
        )

    try:
        img = Image.open(io.BytesIO(data))
        img.verify()  # verify integrity without fully decoding
        # Re-open because verify() can leave the image in an unusable state
        img = Image.open(io.BytesIO(data))
    except Exception as exc:
        raise ImageProcessingError(
            f"File is not a valid image: {exc}"
        ) from exc

    detected_format = img.format
    if detected_format not in ALLOWED_FORMATS:
        raise ImageProcessingError(
            f"Image format '{detected_format}' is not allowed. "
            f"Accepted formats: {', '.join(sorted(ALLOWED_FORMATS))}"
        )

    return img


def _center_crop_square(img: Image.Image) -> Image.Image:
    """
    Crop the image to a centered square using the shorter dimension.

    For a 1200x800 image, this produces an 800x800 crop centered horizontally.
    """
    width, height = img.size
    if width == height:
        return img

    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    return img.crop((left, top, left + side, top + side))


def _resize_and_encode_webp(
    img: Image.Image,
    size: Tuple[int, int],
    quality: int = WEBP_QUALITY,
) -> bytes:
    """
    Resize an image to the given dimensions and encode as WebP.

    Uses LANCZOS resampling for high-quality downscaling.
    Converts RGBA images to RGB (WebP lossy does not support alpha at quality < 100
    in all decoders, and avatars do not require transparency).
    """
    resized = img.resize(size, Image.LANCZOS)  # type: ignore[attr-defined]
    if resized.mode in ("RGBA", "LA", "P"):
        resized = resized.convert("RGB")

    buf = io.BytesIO()
    resized.save(buf, format="WEBP", quality=quality)
    return buf.getvalue()


def process_avatar_image(data: bytes) -> ProcessedImage:
    """
    Full processing pipeline: validate, crop, resize, and encode.

    Args:
        data: Raw uploaded file bytes

    Returns:
        ProcessedImage containing avatar (400x400) and thumbnail (80x80)
            both encoded as WebP.

    Raises:
        ImageProcessingError: On any validation or processing failure.
    """
    img = validate_image_bytes(data)

    # Convert palette and grayscale modes to RGB before processing
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")

    cropped = _center_crop_square(img)

    avatar_bytes = _resize_and_encode_webp(cropped, AVATAR_SIZE)
    thumbnail_bytes = _resize_and_encode_webp(cropped, THUMBNAIL_SIZE)

    logger.info(
        "Processed avatar image: avatar=%d bytes, thumbnail=%d bytes",
        len(avatar_bytes),
        len(thumbnail_bytes),
    )

    return ProcessedImage(avatar=avatar_bytes, thumbnail=thumbnail_bytes)
