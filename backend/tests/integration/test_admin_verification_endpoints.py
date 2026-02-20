"""
Admin Verification Endpoint Integration Tests

Tests the full HTTP request cycle for admin document review,
including listing pending documents and approving/rejecting
with account type promotion.
"""

import io

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.main import app
from src.core.database import get_db
from src.core.encryption import EncryptionService, get_encryption_service
from src.core.security import create_access_token
from src.core.storage import InMemoryStorageClient, get_document_storage_client
from src.models.auth import AuthUser
from src.models.profile import AccountType, BaseProfile


PDF_CONTENT = b"%PDF-1.4 test document for admin review"


@pytest.fixture
def encryption_service():
    return EncryptionService(Fernet.generate_key().decode())


@pytest.fixture
def storage_client():
    return InMemoryStorageClient()


@pytest.fixture
def client_with_deps(client, storage_client, encryption_service):
    """Test client with document storage and encryption overrides."""
    app.dependency_overrides[get_document_storage_client] = lambda: storage_client
    app.dependency_overrides[get_encryption_service] = lambda: encryption_service
    yield client
    app.dependency_overrides.pop(get_document_storage_client, None)
    app.dependency_overrides.pop(get_encryption_service, None)


@pytest.fixture
def admin_user(db_session: Session):
    """Create an admin user with profile and auth record."""
    user_id = "00000000-0000-0000-0000-000000000099"
    profile = BaseProfile(
        user_id=user_id,
        account_type=AccountType.verified,
        primary_email="admin@example.com",
        preferred_language="en",
    )
    db_session.add(profile)
    db_session.commit()

    auth_user = AuthUser(
        user_id=user_id,
        email="admin@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$FAKE_HASH",
        is_email_verified=True,
        is_admin=True,
    )
    db_session.add(auth_user)
    db_session.commit()
    return auth_user


@pytest.fixture
def regular_user(db_session: Session):
    """Create a regular (non-admin) unverified user."""
    user_id = "11111111-1111-1111-1111-111111111111"
    profile = BaseProfile(
        user_id=user_id,
        account_type=AccountType.unverified,
        primary_email="regular@example.com",
        preferred_language="en",
    )
    db_session.add(profile)
    db_session.commit()

    auth_user = AuthUser(
        user_id=user_id,
        email="regular@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$FAKE_HASH",
        is_email_verified=True,
        is_admin=False,
    )
    db_session.add(auth_user)
    db_session.commit()
    return auth_user


@pytest.fixture
def admin_token(admin_user):
    return create_access_token(
        user_id=str(admin_user.user_id),
        email=admin_user.email,
        account_type="verified",
    )


@pytest.fixture
def regular_token(regular_user):
    return create_access_token(
        user_id=str(regular_user.user_id),
        email=regular_user.email,
        account_type="unverified",
    )


@pytest.fixture
def uploaded_document(client_with_deps, regular_user, regular_token):
    """Upload a document as the regular user and return its metadata."""
    user_id = str(regular_user.user_id)
    resp = client_with_deps.post(
        f"/api/v1/profiles/{user_id}/verification-documents",
        headers={"Authorization": f"Bearer {regular_token}"},
        files={"file": ("passport.pdf", io.BytesIO(PDF_CONTENT), "application/pdf")},
        data={"document_type": "passport"},
    )
    assert resp.status_code == 201
    return resp.json()


class TestAdminListPending:
    """Integration tests for GET /admin/verifications/pending."""

    def test_list_pending_empty(self, client_with_deps, admin_user, admin_token):
        """An empty queue must return an empty list."""
        resp = client_with_deps.get(
            "/api/v1/admin/verifications/pending",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_pending_with_document(
        self, client_with_deps, admin_user, admin_token, uploaded_document
    ):
        """A pending document must appear in the admin list."""
        resp = client_with_deps.get(
            "/api/v1/admin/verifications/pending",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["verification_status"] == "pending"

    def test_list_pending_requires_admin(
        self, client_with_deps, regular_user, regular_token
    ):
        """Non-admin users must be rejected with 403."""
        resp = client_with_deps.get(
            "/api/v1/admin/verifications/pending",
            headers={"Authorization": f"Bearer {regular_token}"},
        )
        assert resp.status_code == 403


class TestAdminGetDocument:
    """Integration tests for GET /admin/verifications/{document_id}."""

    def test_get_document_details(
        self, client_with_deps, admin_user, admin_token, uploaded_document
    ):
        """Admin must be able to view full document metadata."""
        doc_id = uploaded_document["id"]
        resp = client_with_deps.get(
            f"/api/v1/admin/verifications/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == doc_id

    def test_get_nonexistent_returns_404(
        self, client_with_deps, admin_user, admin_token
    ):
        """Requesting a non-existent document must return 404."""
        resp = client_with_deps.get(
            "/api/v1/admin/verifications/99999999-9999-9999-9999-999999999999",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404


class TestAdminReview:
    """Integration tests for PATCH /admin/verifications/{document_id}."""

    def test_approve_document(
        self, client_with_deps, admin_user, admin_token, uploaded_document, db_session
    ):
        """Approving a document must set status to verified and promote account."""
        doc_id = uploaded_document["id"]
        resp = client_with_deps.patch(
            f"/api/v1/admin/verifications/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "verification_status": "verified",
                "reviewer_notes": "Passport matches profile",
                "document_expiry_date": "2030-06-15",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["verification_status"] == "verified"
        assert body["document_expiry_date"] == "2030-06-15"

        # Verify the user's account type was promoted
        profile = db_session.query(BaseProfile).filter(
            BaseProfile.user_id == uploaded_document["user_id"]
        ).first()
        assert profile.account_type == AccountType.verified

    def test_reject_document(
        self, client_with_deps, admin_user, admin_token, uploaded_document, db_session
    ):
        """Rejecting a document must set status to rejected without promoting."""
        doc_id = uploaded_document["id"]
        resp = client_with_deps.patch(
            f"/api/v1/admin/verifications/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "verification_status": "rejected",
                "rejection_reason": "Image is blurry",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["verification_status"] == "rejected"
        assert body["rejection_reason"] == "Image is blurry"

        # Account type must remain unverified
        profile = db_session.query(BaseProfile).filter(
            BaseProfile.user_id == uploaded_document["user_id"]
        ).first()
        assert profile.account_type == AccountType.unverified

    def test_reject_without_reason_returns_422(
        self, client_with_deps, admin_user, admin_token, uploaded_document
    ):
        """Rejecting without a reason must fail validation."""
        doc_id = uploaded_document["id"]
        resp = client_with_deps.patch(
            f"/api/v1/admin/verifications/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"verification_status": "rejected"},
        )
        assert resp.status_code == 422

    def test_review_requires_admin(
        self, client_with_deps, regular_user, regular_token, uploaded_document
    ):
        """Non-admin users must not be able to review documents."""
        doc_id = uploaded_document["id"]
        resp = client_with_deps.patch(
            f"/api/v1/admin/verifications/{doc_id}",
            headers={"Authorization": f"Bearer {regular_token}"},
            json={"verification_status": "verified"},
        )
        assert resp.status_code == 403
