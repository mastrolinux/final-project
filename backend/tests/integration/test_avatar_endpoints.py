"""
Integration Tests for Avatar Endpoints

Tests the full HTTP request cycle for avatar upload and deletion,
using the FastAPI TestClient with an in-memory SQLite database and
InMemoryStorageClient dependency override.
"""

import io
import pytest
from uuid import uuid4

from PIL import Image
from fastapi.testclient import TestClient

from src.main import app
from src.core.storage import InMemoryStorageClient, get_storage_client
from src.models.profile import BaseProfile, AccountType
from src.models.context import ContextProfile, ContextType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_jpeg(width: int = 200, height: int = 200) -> bytes:
    img = Image.new("RGB", (width, height), color="green")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_png(width: int = 200, height: int = 200) -> bytes:
    img = Image.new("RGB", (width, height), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_gif(width: int = 100, height: int = 100) -> bytes:
    img = Image.new("RGB", (width, height), color="yellow")
    buf = io.BytesIO()
    img.save(buf, format="GIF")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def storage_client():
    """Provide a fresh InMemoryStorageClient per test."""
    return InMemoryStorageClient()


@pytest.fixture
def client_with_storage(client, storage_client):
    """
    Extend the standard test client with a storage dependency override.

    The ``client`` fixture from conftest already overrides ``get_db``.
    This fixture additionally overrides ``get_storage_client`` with the
    in-memory implementation.
    """
    app.dependency_overrides[get_storage_client] = lambda: storage_client
    yield client
    # The conftest client fixture clears all overrides on teardown,
    # but clean up storage specifically in case of ordering issues.
    app.dependency_overrides.pop(get_storage_client, None)


@pytest.fixture
def profile(db_session) -> BaseProfile:
    p = BaseProfile(
        account_type=AccountType.verified,
        legal_name="Avatar Integration",
        primary_email="avatar-int@example.com",
        preferred_language="en",
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.fixture
def context(db_session, profile) -> ContextProfile:
    ctx = ContextProfile(
        user_id=profile.user_id,
        context_type=ContextType.professional,
        context_name="Work",
    )
    db_session.add(ctx)
    db_session.commit()
    db_session.refresh(ctx)
    return ctx


# ---------------------------------------------------------------------------
# Base avatar endpoint tests
# ---------------------------------------------------------------------------

class TestBaseAvatarUpload:

    def test_upload_jpeg(self, client_with_storage, profile, storage_client):
        resp = client_with_storage.post(
            f"/api/v1/profiles/{profile.user_id}/avatar",
            files={"file": ("photo.jpg", _make_jpeg(), "image/jpeg")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["avatar_url"].startswith("https://storage.test/")
        assert body["avatar_thumbnail_url"].startswith("https://storage.test/")
        assert len(storage_client.blobs) == 2

    def test_upload_png(self, client_with_storage, profile):
        resp = client_with_storage.post(
            f"/api/v1/profiles/{profile.user_id}/avatar",
            files={"file": ("photo.png", _make_png(), "image/png")},
        )
        assert resp.status_code == 200

    def test_upload_gif_rejected(self, client_with_storage, profile):
        resp = client_with_storage.post(
            f"/api/v1/profiles/{profile.user_id}/avatar",
            files={"file": ("anim.gif", _make_gif(), "image/gif")},
        )
        assert resp.status_code == 400
        assert "not allowed" in resp.json()["detail"]

    def test_upload_text_rejected(self, client_with_storage, profile):
        resp = client_with_storage.post(
            f"/api/v1/profiles/{profile.user_id}/avatar",
            files={"file": ("readme.txt", b"hello world", "text/plain")},
        )
        assert resp.status_code == 400

    def test_upload_nonexistent_profile(self, client_with_storage):
        fake_id = uuid4()
        resp = client_with_storage.post(
            f"/api/v1/profiles/{fake_id}/avatar",
            files={"file": ("photo.jpg", _make_jpeg(), "image/jpeg")},
        )
        assert resp.status_code == 404

    def test_upload_replaces_previous(self, client_with_storage, profile, storage_client):
        # Upload first avatar
        client_with_storage.post(
            f"/api/v1/profiles/{profile.user_id}/avatar",
            files={"file": ("v1.jpg", _make_jpeg(), "image/jpeg")},
        )
        first_blobs = set(storage_client.blobs.keys())

        # Upload replacement
        client_with_storage.post(
            f"/api/v1/profiles/{profile.user_id}/avatar",
            files={"file": ("v2.jpg", _make_jpeg(), "image/jpeg")},
        )
        second_blobs = set(storage_client.blobs.keys())

        # Old blobs should be gone, new ones should exist
        assert first_blobs != second_blobs
        assert len(storage_client.blobs) == 2


class TestBaseAvatarDelete:

    def test_delete_success(self, client_with_storage, profile, storage_client):
        # Upload first
        client_with_storage.post(
            f"/api/v1/profiles/{profile.user_id}/avatar",
            files={"file": ("photo.jpg", _make_jpeg(), "image/jpeg")},
        )
        assert len(storage_client.blobs) == 2

        # Delete
        resp = client_with_storage.delete(
            f"/api/v1/profiles/{profile.user_id}/avatar",
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Avatar deleted successfully"
        assert len(storage_client.blobs) == 0

    def test_delete_no_avatar(self, client_with_storage, profile):
        resp = client_with_storage.delete(
            f"/api/v1/profiles/{profile.user_id}/avatar",
        )
        assert resp.status_code == 400
        assert "does not have" in resp.json()["detail"]

    def test_delete_nonexistent_profile(self, client_with_storage):
        resp = client_with_storage.delete(
            f"/api/v1/profiles/{uuid4()}/avatar",
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Context avatar endpoint tests
# ---------------------------------------------------------------------------

class TestContextAvatarUpload:

    def test_upload_context_avatar(self, client_with_storage, profile, context, storage_client):
        resp = client_with_storage.post(
            f"/api/v1/profiles/{profile.user_id}/contexts/{context.id}/avatar",
            files={"file": ("work.jpg", _make_jpeg(), "image/jpeg")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "avatar_url" in body
        assert len(storage_client.blobs) == 2

    def test_upload_wrong_user(self, client_with_storage, context):
        wrong_user = uuid4()
        resp = client_with_storage.post(
            f"/api/v1/profiles/{wrong_user}/contexts/{context.id}/avatar",
            files={"file": ("photo.jpg", _make_jpeg(), "image/jpeg")},
        )
        # Context not found because wrong user's profile doesn't have this context
        assert resp.status_code in (403, 404)

    def test_upload_nonexistent_context(self, client_with_storage, profile):
        resp = client_with_storage.post(
            f"/api/v1/profiles/{profile.user_id}/contexts/{uuid4()}/avatar",
            files={"file": ("photo.jpg", _make_jpeg(), "image/jpeg")},
        )
        assert resp.status_code == 404


class TestContextAvatarDelete:

    def test_delete_context_avatar(self, client_with_storage, profile, context, storage_client):
        # Upload first
        client_with_storage.post(
            f"/api/v1/profiles/{profile.user_id}/contexts/{context.id}/avatar",
            files={"file": ("work.jpg", _make_jpeg(), "image/jpeg")},
        )

        resp = client_with_storage.delete(
            f"/api/v1/profiles/{profile.user_id}/contexts/{context.id}/avatar",
        )
        assert resp.status_code == 200
        assert len(storage_client.blobs) == 0

    def test_delete_no_override(self, client_with_storage, profile, context):
        resp = client_with_storage.delete(
            f"/api/v1/profiles/{profile.user_id}/contexts/{context.id}/avatar",
        )
        assert resp.status_code == 400
        assert "does not have" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Profile response includes avatar fields
# ---------------------------------------------------------------------------

class TestProfileResponseIncludesAvatar:

    def test_get_profile_shows_avatar_fields(self, client_with_storage, profile):
        # Upload an avatar
        client_with_storage.post(
            f"/api/v1/profiles/{profile.user_id}/avatar",
            files={"file": ("photo.jpg", _make_jpeg(), "image/jpeg")},
        )

        # GET the profile and verify avatar fields are present
        resp = client_with_storage.get(
            f"/api/v1/profiles/{profile.user_id}",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["avatar_url"] is not None
        assert body["avatar_thumbnail_url"] is not None
        assert body["avatar_url"].startswith("https://storage.test/")

    def test_get_profile_without_avatar_shows_null(self, client_with_storage, profile):
        resp = client_with_storage.get(
            f"/api/v1/profiles/{profile.user_id}",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["avatar_url"] is None
        assert body["avatar_thumbnail_url"] is None
