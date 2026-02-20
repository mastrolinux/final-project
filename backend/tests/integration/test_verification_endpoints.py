"""
Verification Endpoint Integration Tests (User-Facing)

Tests the full HTTP request cycle for document upload, status queries,
and document listing, using the FastAPI TestClient with an in-memory
SQLite database, InMemoryStorageClient, and a test EncryptionService.
"""

import io

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from src.main import app
from src.core.database import get_db
from src.core.encryption import EncryptionService, get_encryption_service
from src.core.security import create_access_token
from src.core.storage import InMemoryStorageClient, get_document_storage_client
from src.models.auth import AuthUser
from src.models.profile import AccountType, BaseProfile


# Valid file content: PDF with standard prefix
PDF_CONTENT = b"%PDF-1.4 test document content for integration testing"

# Valid JPEG generated with Pillow (structurally valid for Pillow's verify)
def _make_jpeg() -> bytes:
    img = Image.new("RGB", (50, 50), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

JPEG_CONTENT = _make_jpeg()


@pytest.fixture
def encryption_service():
    """Provide a fresh EncryptionService with a test key."""
    return EncryptionService(Fernet.generate_key().decode())


@pytest.fixture
def storage_client():
    """Provide a fresh InMemoryStorageClient per test."""
    return InMemoryStorageClient()


@pytest.fixture
def client_with_deps(client, storage_client, encryption_service):
    """
    Extend the standard test client with document storage and encryption
    dependency overrides.
    """
    app.dependency_overrides[get_document_storage_client] = lambda: storage_client
    app.dependency_overrides[get_encryption_service] = lambda: encryption_service
    yield client
    app.dependency_overrides.pop(get_document_storage_client, None)
    app.dependency_overrides.pop(get_encryption_service, None)


@pytest.fixture
def user_with_profile(db_session: Session):
    """Create an unverified user with base profile and auth record."""
    user_id = "11111111-1111-1111-1111-111111111111"
    profile = BaseProfile(
        user_id=user_id,
        account_type=AccountType.unverified,
        primary_email="testuser@example.com",
        preferred_language="en",
    )
    db_session.add(profile)
    db_session.commit()

    auth_user = AuthUser(
        user_id=user_id,
        email="testuser@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$FAKE_HASH",
        is_email_verified=True,
        is_admin=False,
    )
    db_session.add(auth_user)
    db_session.commit()
    return auth_user


@pytest.fixture
def other_user(db_session: Session):
    """Create a second user for authorization tests."""
    user_id = "22222222-2222-2222-2222-222222222222"
    profile = BaseProfile(
        user_id=user_id,
        account_type=AccountType.unverified,
        primary_email="other@example.com",
        preferred_language="en",
    )
    db_session.add(profile)
    db_session.commit()

    auth_user = AuthUser(
        user_id=user_id,
        email="other@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$FAKE_HASH",
        is_email_verified=True,
        is_admin=False,
    )
    db_session.add(auth_user)
    db_session.commit()
    return auth_user


@pytest.fixture
def user_token(user_with_profile):
    """Generate an access token for the test user."""
    return create_access_token(
        user_id=str(user_with_profile.user_id),
        email=user_with_profile.email,
        account_type="unverified",
    )


@pytest.fixture
def other_token(other_user):
    """Generate an access token for the other user."""
    return create_access_token(
        user_id=str(other_user.user_id),
        email=other_user.email,
        account_type="unverified",
    )


class TestUploadEndpoint:
    """Integration tests for POST /profiles/{user_id}/verification-documents."""

    def test_upload_pdf_success(
        self, client_with_deps, user_with_profile, user_token
    ):
        """Uploading a valid PDF must return 201 with document metadata."""
        user_id = str(user_with_profile.user_id)
        resp = client_with_deps.post(
            f"/api/v1/profiles/{user_id}/verification-documents",
            headers={"Authorization": f"Bearer {user_token}"},
            files={"file": ("passport.pdf", io.BytesIO(PDF_CONTENT), "application/pdf")},
            data={"document_type": "passport"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["document_type"] == "passport"
        assert body["verification_status"] == "pending"
        assert body["original_filename"] == "passport.pdf"
        assert body["content_type"] == "application/pdf"
        # storage_path must not be exposed
        assert "storage_path" not in body

    def test_upload_jpeg_success(
        self, client_with_deps, user_with_profile, user_token
    ):
        """Uploading a JPEG document must be accepted."""
        user_id = str(user_with_profile.user_id)
        resp = client_with_deps.post(
            f"/api/v1/profiles/{user_id}/verification-documents",
            headers={"Authorization": f"Bearer {user_token}"},
            files={"file": ("id_card.jpg", io.BytesIO(JPEG_CONTENT), "image/jpeg")},
            data={"document_type": "national_id"},
        )
        assert resp.status_code == 201
        assert resp.json()["document_type"] == "national_id"

    def test_upload_unauthorized_returns_401(self, client_with_deps):
        """Uploading without authentication must return 401."""
        resp = client_with_deps.post(
            "/api/v1/profiles/11111111-1111-1111-1111-111111111111/verification-documents",
            files={"file": ("doc.pdf", io.BytesIO(PDF_CONTENT), "application/pdf")},
            data={"document_type": "passport"},
        )
        assert resp.status_code == 401

    def test_upload_other_user_returns_403(
        self, client_with_deps, user_with_profile, other_user, other_token
    ):
        """Uploading a document to another user's profile must return 403."""
        user_id = str(user_with_profile.user_id)
        resp = client_with_deps.post(
            f"/api/v1/profiles/{user_id}/verification-documents",
            headers={"Authorization": f"Bearer {other_token}"},
            files={"file": ("doc.pdf", io.BytesIO(PDF_CONTENT), "application/pdf")},
            data={"document_type": "passport"},
        )
        assert resp.status_code == 403

    def test_upload_invalid_format_returns_400(
        self, client_with_deps, user_with_profile, user_token
    ):
        """Uploading an unsupported format (GIF) must return 400."""
        user_id = str(user_with_profile.user_id)
        gif_bytes = b"GIF89a fake gif content"
        resp = client_with_deps.post(
            f"/api/v1/profiles/{user_id}/verification-documents",
            headers={"Authorization": f"Bearer {user_token}"},
            files={"file": ("photo.gif", io.BytesIO(gif_bytes), "image/gif")},
            data={"document_type": "passport"},
        )
        assert resp.status_code == 400
        assert "Unsupported" in resp.json()["detail"]


class TestVerificationStatusEndpoint:
    """Integration tests for GET /profiles/{user_id}/verification-status."""

    def test_status_no_documents(
        self, client_with_deps, user_with_profile, user_token
    ):
        """A user with no documents must see can_create_legal_context=False."""
        user_id = str(user_with_profile.user_id)
        resp = client_with_deps.get(
            f"/api/v1/profiles/{user_id}/verification-status",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["account_type"] == "unverified"
        assert body["can_create_legal_context"] is False
        assert body["latest_document"] is None

    def test_status_after_upload(
        self, client_with_deps, user_with_profile, user_token
    ):
        """After uploading a document, the status must include it."""
        user_id = str(user_with_profile.user_id)

        # Upload first
        client_with_deps.post(
            f"/api/v1/profiles/{user_id}/verification-documents",
            headers={"Authorization": f"Bearer {user_token}"},
            files={"file": ("passport.pdf", io.BytesIO(PDF_CONTENT), "application/pdf")},
            data={"document_type": "passport"},
        )

        # Check status
        resp = client_with_deps.get(
            f"/api/v1/profiles/{user_id}/verification-status",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["latest_document"] is not None
        assert body["latest_document"]["verification_status"] == "pending"

    def test_status_other_user_returns_403(
        self, client_with_deps, user_with_profile, other_user, other_token
    ):
        """Viewing another user's status must return 403."""
        user_id = str(user_with_profile.user_id)
        resp = client_with_deps.get(
            f"/api/v1/profiles/{user_id}/verification-status",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert resp.status_code == 403


class TestDocumentListEndpoint:
    """Integration tests for GET /profiles/{user_id}/verification-documents."""

    def test_list_empty(
        self, client_with_deps, user_with_profile, user_token
    ):
        """A user with no documents must get an empty list."""
        user_id = str(user_with_profile.user_id)
        resp = client_with_deps.get(
            f"/api/v1/profiles/{user_id}/verification-documents",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_after_uploads(
        self, client_with_deps, user_with_profile, user_token
    ):
        """Uploaded documents must appear in the listing."""
        user_id = str(user_with_profile.user_id)

        # Upload two documents
        for _ in range(2):
            client_with_deps.post(
                f"/api/v1/profiles/{user_id}/verification-documents",
                headers={"Authorization": f"Bearer {user_token}"},
                files={
                    "file": ("doc.pdf", io.BytesIO(PDF_CONTENT), "application/pdf")
                },
                data={"document_type": "passport"},
            )

        resp = client_with_deps.get(
            f"/api/v1/profiles/{user_id}/verification-documents",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2
