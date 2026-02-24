"""
Image validation and processing for avatar uploads (magic-byte detection, WebP output).
"""

import io
import logging
from dataclasses import dataclass
from typing import Tuple

from PIL import Image

logger = logging.getLogger(__name__)

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
    """Validate raw bytes as a supported image format using Pillow's magic-byte parser."""
    if len(data) > MAX_FILE_SIZE_BYTES:
        raise ImageProcessingError(
            f"File size {len(data)} bytes exceeds maximum of {MAX_FILE_SIZE_BYTES} bytes (5 MB)"
        )

    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
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
    """Crop to a centered square using the shorter dimension."""
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
    """Resize to given dimensions and encode as WebP (LANCZOS resampling)."""
    resized = img.resize(size, Image.LANCZOS)  # type: ignore[attr-defined]
    if resized.mode in ("RGBA", "LA", "P"):
        resized = resized.convert("RGB")

    buf = io.BytesIO()
    resized.save(buf, format="WEBP", quality=quality)
    return buf.getvalue()


def process_avatar_image(data: bytes) -> ProcessedImage:
    """Validate, crop, resize, and encode to WebP (400x400 avatar, 80x80 thumbnail)."""
    img = validate_image_bytes(data)

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
