"""Tests for image validation, center-cropping, resizing, and WebP conversion."""

import io

import pytest
from PIL import Image

from src.core.image import (
    AVATAR_SIZE,
    MAX_FILE_SIZE_BYTES,
    THUMBNAIL_SIZE,
    ImageProcessingError,
    ProcessedImage,
    process_avatar_image,
    validate_image_bytes,
)


def _make_image_bytes(
    width: int = 800,
    height: int = 600,
    fmt: str = "JPEG",
    color: str = "red",
) -> bytes:
    """Generate an in-memory image of the given format and dimensions."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def _make_png_rgba(width: int = 200, height: int = 200) -> bytes:
    """Generate a PNG with an alpha channel."""
    img = Image.new("RGBA", (width, height), color=(255, 0, 0, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_palette_image(width: int = 100, height: int = 100) -> bytes:
    """Generate a palette-mode (P) PNG."""
    img = Image.new("P", (width, height))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestImageValidation:
    """Tests for validate_image_bytes and format/size constraints."""

    def test_valid_jpeg(self):
        data = _make_image_bytes(fmt="JPEG")
        img = validate_image_bytes(data)
        assert img.format == "JPEG"

    def test_valid_png(self):
        data = _make_image_bytes(fmt="PNG")
        img = validate_image_bytes(data)
        assert img.format == "PNG"

    def test_valid_webp(self):
        data = _make_image_bytes(fmt="WEBP")
        img = validate_image_bytes(data)
        assert img.format == "WEBP"

    def test_reject_gif(self):
        data = _make_image_bytes(fmt="GIF")
        with pytest.raises(ImageProcessingError, match="not allowed"):
            validate_image_bytes(data)

    def test_reject_non_image_bytes(self):
        with pytest.raises(ImageProcessingError, match="not a valid image"):
            validate_image_bytes(b"this is just plain text")

    def test_reject_empty_bytes(self):
        with pytest.raises(ImageProcessingError, match="not a valid image"):
            validate_image_bytes(b"")

    def test_reject_oversized_file(self):
        # Create data that exceeds the 5 MB limit
        oversized = b"\x00" * (MAX_FILE_SIZE_BYTES + 1)
        with pytest.raises(ImageProcessingError, match="exceeds maximum"):
            validate_image_bytes(oversized)

    def test_accept_file_at_exact_limit(self):
        """A file exactly at the size limit should be accepted (if valid)."""
        data = _make_image_bytes(fmt="JPEG")
        # This image is well under 5 MB, so it validates fine.
        img = validate_image_bytes(data)
        assert img is not None

    def test_reject_svg_xml(self):
        svg_data = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>'
        with pytest.raises(ImageProcessingError, match="not a valid image"):
            validate_image_bytes(svg_data)


class TestProcessAvatarImage:
    """Tests for the full processing pipeline: validate, crop, resize, encode."""

    def test_square_input_produces_correct_sizes(self):
        data = _make_image_bytes(width=1000, height=1000, fmt="JPEG")
        result = process_avatar_image(data)

        assert isinstance(result, ProcessedImage)
        assert result.content_type == "image/webp"

        avatar = Image.open(io.BytesIO(result.avatar))
        assert avatar.size == AVATAR_SIZE

        thumb = Image.open(io.BytesIO(result.thumbnail))
        assert thumb.size == THUMBNAIL_SIZE

    def test_landscape_input_center_cropped(self):
        """A 1200x600 image should be center-cropped to 600x600 before resize."""
        data = _make_image_bytes(width=1200, height=600, fmt="PNG")
        result = process_avatar_image(data)

        avatar = Image.open(io.BytesIO(result.avatar))
        assert avatar.size == AVATAR_SIZE

    def test_portrait_input_center_cropped(self):
        """A 600x1200 image should be center-cropped to 600x600 before resize."""
        data = _make_image_bytes(width=600, height=1200, fmt="PNG")
        result = process_avatar_image(data)

        avatar = Image.open(io.BytesIO(result.avatar))
        assert avatar.size == AVATAR_SIZE

    def test_rgba_png_converts_to_rgb_webp(self):
        data = _make_png_rgba()
        result = process_avatar_image(data)

        avatar = Image.open(io.BytesIO(result.avatar))
        assert avatar.mode == "RGB"

    def test_palette_mode_converts_to_rgb(self):
        data = _make_palette_image()
        result = process_avatar_image(data)

        avatar = Image.open(io.BytesIO(result.avatar))
        assert avatar.mode == "RGB"

    def test_webp_input_accepted(self):
        data = _make_image_bytes(fmt="WEBP")
        result = process_avatar_image(data)
        assert len(result.avatar) > 0
        assert len(result.thumbnail) > 0

    def test_small_image_upscales(self):
        """An image smaller than 400x400 is still resized to the target dimensions."""
        data = _make_image_bytes(width=50, height=50, fmt="JPEG")
        result = process_avatar_image(data)

        avatar = Image.open(io.BytesIO(result.avatar))
        assert avatar.size == AVATAR_SIZE

    def test_invalid_format_raises(self):
        data = _make_image_bytes(fmt="GIF")
        with pytest.raises(ImageProcessingError):
            process_avatar_image(data)

    def test_output_is_webp_format(self):
        data = _make_image_bytes(fmt="JPEG")
        result = process_avatar_image(data)

        avatar = Image.open(io.BytesIO(result.avatar))
        assert avatar.format == "WEBP"

        thumb = Image.open(io.BytesIO(result.thumbnail))
        assert thumb.format == "WEBP"
