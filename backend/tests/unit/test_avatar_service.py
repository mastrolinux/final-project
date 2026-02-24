"""Tests for avatar upload and deletion on base and context profiles."""

import io
import pytest
from uuid import uuid4

from PIL import Image

from src.core.storage import InMemoryStorageClient
from src.models.profile import BaseProfile, AccountType
from src.models.context import ContextProfile, ContextType
from src.repositories.avatar_repository import AvatarRepository
from src.services.avatar_service import AvatarService, AvatarServiceError



def _make_jpeg(width: int = 200, height: int = 200) -> bytes:
    """Generate a minimal valid JPEG image."""
    img = Image.new("RGB", (width, height), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def storage():
    return InMemoryStorageClient()


@pytest.fixture
def avatar_repo(db_session):
    return AvatarRepository(db_session)


@pytest.fixture
def avatar_service(avatar_repo, storage):
    return AvatarService(avatar_repo, storage)


@pytest.fixture
def profile_with_avatar(db_session):
    """Create a profile that already has an avatar."""
    profile = BaseProfile(
        account_type=AccountType.verified,
        legal_name="Test User",
        primary_email="avatar-test@example.com",
        preferred_language="en",
        avatar_url="https://storage.test/old/avatar.webp",
        avatar_thumbnail_url="https://storage.test/old/thumbnail.webp",
        avatar_storage_path="old",
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


@pytest.fixture
def context_profile(db_session, sample_verified_profile):
    """Create a context profile belonging to sample_verified_profile."""
    ctx = ContextProfile(
        user_id=sample_verified_profile.user_id,
        context_type=ContextType.professional,
        context_name="LinkedIn",
    )
    db_session.add(ctx)
    db_session.commit()
    db_session.refresh(ctx)
    return ctx


class TestUploadBaseAvatar:

    def test_upload_success(self, avatar_service, sample_verified_profile, storage):
        data = _make_jpeg()
        result = avatar_service.upload_base_avatar(
            sample_verified_profile.user_id, data
        )

        assert "avatar_url" in result
        assert "avatar_thumbnail_url" in result
        assert result["avatar_url"].startswith("https://storage.test/")
        assert result["avatar_thumbnail_url"].startswith("https://storage.test/")
        assert len(storage.blobs) == 2

    def test_upload_replaces_existing(self, avatar_service, profile_with_avatar, storage):
        storage.blobs["old/avatar.webp"] = b"old-avatar"
        storage.blobs["old/thumbnail.webp"] = b"old-thumb"

        data = _make_jpeg()
        result = avatar_service.upload_base_avatar(
            profile_with_avatar.user_id, data
        )

        assert "old/avatar.webp" not in storage.blobs
        assert "old/thumbnail.webp" not in storage.blobs
        assert len(storage.blobs) == 2
        assert result["avatar_url"] != "https://storage.test/old/avatar.webp"

    def test_upload_nonexistent_profile_raises(self, avatar_service):
        with pytest.raises(AvatarServiceError, match="not found"):
            avatar_service.upload_base_avatar(uuid4(), _make_jpeg())

    def test_upload_invalid_image_raises(self, avatar_service, sample_verified_profile):
        with pytest.raises(AvatarServiceError, match="not a valid image"):
            avatar_service.upload_base_avatar(
                sample_verified_profile.user_id, b"not an image"
            )

    def test_upload_gif_rejected(self, avatar_service, sample_verified_profile):
        img = Image.new("RGB", (100, 100))
        buf = io.BytesIO()
        img.save(buf, format="GIF")
        with pytest.raises(AvatarServiceError, match="not allowed"):
            avatar_service.upload_base_avatar(
                sample_verified_profile.user_id, buf.getvalue()
            )


class TestDeleteBaseAvatar:

    def test_delete_success(self, avatar_service, profile_with_avatar, storage):
        storage.blobs["old/avatar.webp"] = b"data"
        storage.blobs["old/thumbnail.webp"] = b"data"

        result = avatar_service.delete_base_avatar(profile_with_avatar.user_id)

        assert result["message"] == "Avatar deleted successfully"
        assert len(storage.blobs) == 0

    def test_delete_nonexistent_profile_raises(self, avatar_service):
        with pytest.raises(AvatarServiceError, match="not found"):
            avatar_service.delete_base_avatar(uuid4())

    def test_delete_no_avatar_raises(self, avatar_service, sample_verified_profile):
        with pytest.raises(AvatarServiceError, match="does not have an avatar"):
            avatar_service.delete_base_avatar(sample_verified_profile.user_id)


class TestUploadContextAvatar:

    def test_upload_context_avatar_success(
        self, avatar_service, sample_verified_profile, context_profile, storage
    ):
        data = _make_jpeg()
        result = avatar_service.upload_context_avatar(
            sample_verified_profile.user_id, context_profile.id, data
        )

        assert "avatar_url" in result
        assert "avatar_thumbnail_url" in result
        assert len(storage.blobs) == 2

    def test_upload_wrong_user_raises(
        self, avatar_service, context_profile, storage
    ):
        wrong_user = uuid4()
        with pytest.raises(AvatarServiceError, match="does not belong"):
            avatar_service.upload_context_avatar(
                wrong_user, context_profile.id, _make_jpeg()
            )

    def test_upload_nonexistent_context_raises(
        self, avatar_service, sample_verified_profile
    ):
        with pytest.raises(AvatarServiceError, match="not found"):
            avatar_service.upload_context_avatar(
                sample_verified_profile.user_id, uuid4(), _make_jpeg()
            )


class TestDeleteContextAvatar:

    def test_delete_context_avatar_success(
        self, avatar_service, sample_verified_profile, context_profile, db_session, storage
    ):
        data = _make_jpeg()
        avatar_service.upload_context_avatar(
            sample_verified_profile.user_id, context_profile.id, data
        )
        assert len(storage.blobs) == 2

        result = avatar_service.delete_context_avatar(
            sample_verified_profile.user_id, context_profile.id
        )
        assert result["message"] == "Context avatar deleted successfully"
        assert len(storage.blobs) == 0

    def test_delete_no_override_raises(
        self, avatar_service, sample_verified_profile, context_profile
    ):
        with pytest.raises(AvatarServiceError, match="does not have an avatar override"):
            avatar_service.delete_context_avatar(
                sample_verified_profile.user_id, context_profile.id
            )
