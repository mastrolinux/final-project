"""
Verification Service Unit Tests

Tests business logic for document upload, status queries, and admin
review using mocked repositories and in-memory storage/encryption.
"""

import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from src.core.encryption import EncryptionService
from src.core.storage import InMemoryStorageClient
from src.models.profile import AccountType, BaseProfile
from src.models.verification import (
    DocumentType,
    VerificationDocument,
    VerificationStatus,
)
from src.services.verification_service import (
    VerificationService,
    VerificationServiceError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_verification_repo():
    return MagicMock()


@pytest.fixture
def mock_profile_repo():
    return MagicMock()


@pytest.fixture
def mock_audit_service():
    return MagicMock()


@pytest.fixture
def storage():
    return InMemoryStorageClient()


@pytest.fixture
def encryption():
    key = Fernet.generate_key().decode()
    return EncryptionService(key)


@pytest.fixture
def service(
    mock_verification_repo,
    mock_profile_repo,
    storage,
    encryption,
    mock_audit_service,
):
    return VerificationService(
        verification_repo=mock_verification_repo,
        profile_repo=mock_profile_repo,
        storage=storage,
        encryption=encryption,
        audit_service=mock_audit_service,
    )


def _make_profile(
    user_id=None, account_type=AccountType.unverified
) -> MagicMock:
    """Create a mock profile with the given account type."""
    profile = MagicMock(spec=BaseProfile)
    profile.user_id = str(user_id or uuid.uuid4())
    profile.account_type = account_type
    return profile


def _make_document(
    doc_id=None,
    user_id=None,
    status=VerificationStatus.pending,
    document_type=DocumentType.passport,
) -> MagicMock:
    """Create a mock verification document."""
    doc = MagicMock(spec=VerificationDocument)
    doc.id = str(doc_id or uuid.uuid4())
    doc.user_id = str(user_id or uuid.uuid4())
    doc.document_type = document_type
    doc.verification_status = status
    doc.storage_path = f"{doc.user_id}/blob/doc.pdf"
    doc.original_filename = "passport.pdf"
    doc.file_size_bytes = 2048
    doc.content_type = "application/pdf"
    doc.is_reviewable = status in (
        VerificationStatus.pending,
        VerificationStatus.under_review,
    )
    doc.is_verified = status == VerificationStatus.verified
    doc.reviewer_id = None
    doc.reviewed_at = None
    doc.reviewer_notes = None
    doc.document_expiry_date = None
    doc.rejection_reason = None
    doc.created_at = datetime.now(timezone.utc)
    doc.updated_at = datetime.now(timezone.utc)
    return doc


# Valid PDF bytes for upload tests
PDF_BYTES = b"%PDF-1.4 test content for upload validation"


# ---------------------------------------------------------------------------
# Upload tests
# ---------------------------------------------------------------------------


class TestUploadDocument:
    """Tests for VerificationService.upload_document."""

    def test_upload_success(self, service, mock_verification_repo, mock_profile_repo):
        """A valid document upload must create a record with status pending."""
        user_id = uuid.uuid4()
        profile = _make_profile(user_id=user_id)
        mock_profile_repo.get_profile_by_id.return_value = profile

        doc = _make_document(user_id=user_id)
        mock_verification_repo.create_document.return_value = doc

        result = service.upload_document(
            user_id=user_id,
            file_data=PDF_BYTES,
            filename="passport.pdf",
            claimed_content_type="application/pdf",
            document_type=DocumentType.passport,
        )

        assert result == doc
        mock_verification_repo.create_document.assert_called_once()
        call_kwargs = mock_verification_repo.create_document.call_args
        assert call_kwargs.kwargs["document_type"] == DocumentType.passport

    def test_upload_encrypts_data(
        self, service, mock_verification_repo, mock_profile_repo, storage, encryption
    ):
        """Uploaded data must be encrypted before storage."""
        user_id = uuid.uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(
            user_id=user_id
        )
        mock_verification_repo.create_document.return_value = _make_document(
            user_id=user_id
        )

        service.upload_document(
            user_id=user_id,
            file_data=PDF_BYTES,
            filename="doc.pdf",
            claimed_content_type="application/pdf",
            document_type=DocumentType.passport,
        )

        # Verify blob in storage is encrypted (not plaintext)
        assert len(storage.blobs) == 1
        stored_data = list(storage.blobs.values())[0]
        assert stored_data != PDF_BYTES
        # Decrypting stored data must recover original
        assert encryption.decrypt(stored_data) == PDF_BYTES

    def test_upload_profile_not_found(self, service, mock_profile_repo):
        """Upload for a non-existent profile must raise 404."""
        mock_profile_repo.get_profile_by_id.return_value = None

        with pytest.raises(VerificationServiceError, match="not found") as exc_info:
            service.upload_document(
                user_id=uuid.uuid4(),
                file_data=PDF_BYTES,
                filename="doc.pdf",
                claimed_content_type="application/pdf",
                document_type=DocumentType.passport,
            )
        assert exc_info.value.status_code == 404

    def test_upload_invalid_format_rejected(
        self, service, mock_profile_repo
    ):
        """A GIF file (unsupported) must be rejected during upload."""
        user_id = uuid.uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(
            user_id=user_id
        )

        with pytest.raises(VerificationServiceError, match="Unsupported"):
            service.upload_document(
                user_id=user_id,
                file_data=b"GIF89a fake gif",
                filename="image.gif",
                claimed_content_type="image/gif",
                document_type=DocumentType.passport,
            )

    def test_upload_empty_file_rejected(self, service, mock_profile_repo):
        """An empty file must be rejected."""
        user_id = uuid.uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(
            user_id=user_id
        )

        with pytest.raises(VerificationServiceError, match="Empty file"):
            service.upload_document(
                user_id=user_id,
                file_data=b"",
                filename="empty.pdf",
                claimed_content_type="application/pdf",
                document_type=DocumentType.passport,
            )

    def test_upload_logs_audit_event(
        self, service, mock_profile_repo, mock_verification_repo, mock_audit_service
    ):
        """A successful upload must log an audit event."""
        user_id = uuid.uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(
            user_id=user_id
        )
        mock_verification_repo.create_document.return_value = _make_document(
            user_id=user_id
        )

        service.upload_document(
            user_id=user_id,
            file_data=PDF_BYTES,
            filename="passport.pdf",
            claimed_content_type="application/pdf",
            document_type=DocumentType.passport,
        )

        mock_audit_service.log_event.assert_called_once()


# ---------------------------------------------------------------------------
# Status query tests
# ---------------------------------------------------------------------------


class TestGetVerificationStatus:
    """Tests for VerificationService.get_verification_status."""

    def test_status_verified_user(
        self, service, mock_profile_repo, mock_verification_repo
    ):
        """A verified user must have can_create_legal_context=True."""
        user_id = uuid.uuid4()
        profile = _make_profile(user_id=user_id, account_type=AccountType.verified)
        mock_profile_repo.get_profile_by_id.return_value = profile
        mock_verification_repo.get_latest_user_document.return_value = None

        result = service.get_verification_status(user_id)
        assert result["can_create_legal_context"] is True
        assert result["account_type"] == AccountType.verified

    def test_status_unverified_user(
        self, service, mock_profile_repo, mock_verification_repo
    ):
        """An unverified user must have can_create_legal_context=False."""
        user_id = uuid.uuid4()
        profile = _make_profile(user_id=user_id, account_type=AccountType.unverified)
        mock_profile_repo.get_profile_by_id.return_value = profile
        mock_verification_repo.get_latest_user_document.return_value = None

        result = service.get_verification_status(user_id)
        assert result["can_create_legal_context"] is False

    def test_status_with_pending_document(
        self, service, mock_profile_repo, mock_verification_repo
    ):
        """A pending document must be included in the status response."""
        user_id = uuid.uuid4()
        mock_profile_repo.get_profile_by_id.return_value = _make_profile(
            user_id=user_id
        )
        doc = _make_document(user_id=user_id, status=VerificationStatus.pending)
        mock_verification_repo.get_latest_user_document.return_value = doc

        result = service.get_verification_status(user_id)
        assert result["latest_document"] == doc

    def test_status_profile_not_found(self, service, mock_profile_repo):
        """Querying status for a non-existent profile must raise 404."""
        mock_profile_repo.get_profile_by_id.return_value = None

        with pytest.raises(VerificationServiceError, match="not found"):
            service.get_verification_status(uuid.uuid4())


# ---------------------------------------------------------------------------
# Admin review tests
# ---------------------------------------------------------------------------


class TestReviewDocument:
    """Tests for VerificationService.review_document."""

    def test_approve_document_promotes_account(
        self, service, mock_verification_repo, mock_profile_repo
    ):
        """Approving a document must promote the user's account to verified."""
        doc_id = uuid.uuid4()
        user_id = uuid.uuid4()
        reviewer_id = uuid.uuid4()

        doc = _make_document(
            doc_id=doc_id, user_id=user_id, status=VerificationStatus.pending
        )
        mock_verification_repo.get_document_by_id.return_value = doc

        updated_doc = _make_document(
            doc_id=doc_id, user_id=user_id, status=VerificationStatus.verified
        )
        mock_verification_repo.update_document_status.return_value = updated_doc

        result = service.review_document(
            document_id=doc_id,
            reviewer_id=reviewer_id,
            status=VerificationStatus.verified,
            document_expiry_date=date(2030, 6, 15),
        )

        assert result == updated_doc
        mock_profile_repo.update_profile.assert_called_once_with(
            doc.user_id, account_type=AccountType.verified
        )

    def test_reject_document_does_not_promote(
        self, service, mock_verification_repo, mock_profile_repo
    ):
        """Rejecting a document must not change the user's account type."""
        doc_id = uuid.uuid4()
        doc = _make_document(doc_id=doc_id, status=VerificationStatus.pending)
        mock_verification_repo.get_document_by_id.return_value = doc

        updated_doc = _make_document(
            doc_id=doc_id, status=VerificationStatus.rejected
        )
        mock_verification_repo.update_document_status.return_value = updated_doc

        service.review_document(
            document_id=doc_id,
            reviewer_id=uuid.uuid4(),
            status=VerificationStatus.rejected,
            rejection_reason="Document not legible",
        )

        mock_profile_repo.update_profile.assert_not_called()

    def test_reject_without_reason_raises(
        self, service, mock_verification_repo
    ):
        """Rejecting without a reason must raise."""
        doc = _make_document(status=VerificationStatus.pending)
        mock_verification_repo.get_document_by_id.return_value = doc

        with pytest.raises(
            VerificationServiceError, match="rejection_reason is required"
        ):
            service.review_document(
                document_id=uuid.uuid4(),
                reviewer_id=uuid.uuid4(),
                status=VerificationStatus.rejected,
            )

    def test_review_already_verified_raises(
        self, service, mock_verification_repo
    ):
        """A document already in verified state must not be re-reviewed."""
        doc = _make_document(status=VerificationStatus.verified)
        doc.is_reviewable = False
        mock_verification_repo.get_document_by_id.return_value = doc

        with pytest.raises(VerificationServiceError, match="cannot be reviewed"):
            service.review_document(
                document_id=uuid.uuid4(),
                reviewer_id=uuid.uuid4(),
                status=VerificationStatus.verified,
            )

    def test_review_nonexistent_document_raises(
        self, service, mock_verification_repo
    ):
        """Reviewing a non-existent document must raise 404."""
        mock_verification_repo.get_document_by_id.return_value = None

        with pytest.raises(VerificationServiceError, match="not found"):
            service.review_document(
                document_id=uuid.uuid4(),
                reviewer_id=uuid.uuid4(),
                status=VerificationStatus.verified,
            )

    def test_review_with_pending_status_raises(
        self, service, mock_verification_repo
    ):
        """Setting status to 'pending' in a review must be rejected."""
        doc = _make_document(status=VerificationStatus.pending)
        mock_verification_repo.get_document_by_id.return_value = doc

        with pytest.raises(
            VerificationServiceError, match="must be 'verified' or 'rejected'"
        ):
            service.review_document(
                document_id=uuid.uuid4(),
                reviewer_id=uuid.uuid4(),
                status=VerificationStatus.pending,
            )

    def test_review_logs_audit_event(
        self, service, mock_verification_repo, mock_audit_service
    ):
        """A review must log an audit event with reviewer details."""
        doc = _make_document(status=VerificationStatus.pending)
        mock_verification_repo.get_document_by_id.return_value = doc
        mock_verification_repo.update_document_status.return_value = doc

        service.review_document(
            document_id=uuid.uuid4(),
            reviewer_id=uuid.uuid4(),
            status=VerificationStatus.verified,
        )

        mock_audit_service.log_event.assert_called_once()


# ---------------------------------------------------------------------------
# Delete tests
# ---------------------------------------------------------------------------


class TestDeleteDocument:
    """Tests for VerificationService.delete_document."""

    def test_delete_removes_storage_blob(
        self, service, mock_verification_repo, storage
    ):
        """Deleting a document must remove its encrypted blob from storage."""
        doc = _make_document()
        mock_verification_repo.get_document_by_id.return_value = doc
        mock_verification_repo.soft_delete_document.return_value = True

        # Pre-populate storage
        storage.blobs[doc.storage_path] = b"encrypted data"

        service.delete_document(uuid.uuid4(), uuid.uuid4())

        assert doc.storage_path not in storage.blobs
        mock_verification_repo.soft_delete_document.assert_called_once()

    def test_delete_nonexistent_raises(self, service, mock_verification_repo):
        """Deleting a non-existent document must raise 404."""
        mock_verification_repo.get_document_by_id.return_value = None

        with pytest.raises(VerificationServiceError, match="not found"):
            service.delete_document(uuid.uuid4(), uuid.uuid4())
