"""Tests for document upload, status queries, and admin review."""

import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from src.core.encryption import EncryptionService
from src.core.storage import InMemoryStorageClient
from src.models.profile import AccountType, BaseProfile
from src.models.context import ContextProfile, ContextType
from src.models.verification import (
    DocumentType,
    VerificationDocument,
    VerificationStatus,
)
from src.services.verification_service import (
    VerificationService,
    VerificationServiceError,
)


#
# Fixtures
#


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
def mock_context_repo():
    return MagicMock()


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


@pytest.fixture
def service_with_context(
    mock_verification_repo,
    mock_profile_repo,
    mock_context_repo,
    storage,
    encryption,
    mock_audit_service,
):
    """Service instance with context_repo injected."""
    return VerificationService(
        verification_repo=mock_verification_repo,
        profile_repo=mock_profile_repo,
        storage=storage,
        encryption=encryption,
        audit_service=mock_audit_service,
        context_repo=mock_context_repo,
    )


def _make_profile(
    user_id=None, account_type=AccountType.unverified
) -> MagicMock:
    """Create a mock profile with the given account type."""
    profile = MagicMock(spec=BaseProfile)
    profile.user_id = str(user_id or uuid.uuid4())
    profile.account_type = account_type
    profile.legal_name = "Test User"
    profile.primary_email = "test@example.com"
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


def _make_context(
    context_id=None,
    user_id=None,
    context_type=ContextType.legal,
    verification_status=VerificationStatus.pending,
    requires_verification=True,
) -> MagicMock:
    """Create a mock context profile for verification tests."""
    ctx = MagicMock(spec=ContextProfile)
    ctx.id = str(context_id or uuid.uuid4())
    ctx.user_id = user_id or uuid.uuid4()
    ctx.context_type = MagicMock()
    ctx.context_type.value = context_type.value if hasattr(context_type, "value") else context_type
    ctx.context_name = "Government ID"
    ctx.verification_status = verification_status
    ctx.requires_verification = requires_verification
    ctx.is_active = False
    ctx.rejection_reason = None
    ctx.display_name_override = None
    ctx.email_override = None
    ctx.phone_override = None
    ctx.bio = None
    ctx.base_profile = None
    ctx.document_id = None
    ctx.created_at = datetime.now(timezone.utc)
    ctx.updated_at = datetime.now(timezone.utc)
    return ctx


# Valid PDF bytes for upload tests
PDF_BYTES = b"%PDF-1.4 test content for upload validation"


#
# Upload tests
#


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
            document_expiry_date=date(2030, 6, 15),
        )

        assert result == doc
        mock_verification_repo.create_document.assert_called_once()
        call_kwargs = mock_verification_repo.create_document.call_args
        assert call_kwargs.kwargs["document_type"] == DocumentType.passport
        assert call_kwargs.kwargs["document_expiry_date"] == date(2030, 6, 15)

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
            document_expiry_date=date(2030, 1, 1),
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

    def test_upload_without_expiry_uses_none(
        self, service, mock_verification_repo, mock_profile_repo
    ):
        """Uploading without an expiry date must pass None to the repository."""
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

        call_kwargs = mock_verification_repo.create_document.call_args.kwargs
        assert call_kwargs["document_expiry_date"] is None

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
            document_expiry_date=date(2030, 6, 15),
        )

        mock_audit_service.log_event.assert_called_once()
        audit_kwargs = mock_audit_service.log_event.call_args.kwargs
        assert audit_kwargs["changes"]["document_expiry_date"] == "2030-06-15"


#
# Status query tests
#


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


#
# Admin review tests
#


class TestReviewContext:
    """Tests for VerificationService.review_context."""

    @patch("src.tasks.email_tasks.send_approval_email")
    def test_approve_context_promotes_account(
        self,
        mock_email_task,
        service_with_context,
        mock_verification_repo,
        mock_profile_repo,
        mock_context_repo,
    ):
        """Approving a context must promote the user's account to verified."""
        context_id = uuid.uuid4()
        user_id = uuid.uuid4()
        reviewer_id = uuid.uuid4()

        ctx = _make_context(context_id=context_id, user_id=user_id)
        mock_context_repo.get_context_profile_by_id.return_value = ctx

        doc = _make_document(user_id=user_id)
        mock_verification_repo.get_documents_for_context.return_value = [doc]

        profile = _make_profile(user_id=user_id)
        profile.primary_email = "user@example.com"
        profile.legal_name = "Test User"
        mock_profile_repo.get_profile_by_id.return_value = profile

        updated_ctx = _make_context(
            context_id=context_id,
            user_id=user_id,
            verification_status=VerificationStatus.verified,
        )
        updated_ctx.is_active = True
        mock_context_repo.update_verification_status.return_value = updated_ctx

        result = service_with_context.review_context(
            context_id=context_id,
            reviewer_id=reviewer_id,
            status=VerificationStatus.verified,
            document_expiry_date=date(2030, 6, 15),
        )

        assert result == updated_ctx
        mock_profile_repo.update_profile.assert_called_once_with(
            ctx.user_id, account_type=AccountType.verified
        )
        mock_context_repo.update_verification_status.assert_called_once()
        call_kwargs = mock_context_repo.update_verification_status.call_args.kwargs
        assert call_kwargs["verification_status"] == VerificationStatus.verified
        assert call_kwargs["is_active"] is True

    @patch("src.tasks.email_tasks.send_rejection_email")
    def test_reject_context_does_not_promote(
        self,
        mock_email_task,
        service_with_context,
        mock_verification_repo,
        mock_profile_repo,
        mock_context_repo,
    ):
        """Rejecting a context must not change the user's account type."""
        context_id = uuid.uuid4()
        user_id = uuid.uuid4()

        ctx = _make_context(context_id=context_id, user_id=user_id)
        mock_context_repo.get_context_profile_by_id.return_value = ctx

        doc = _make_document(user_id=user_id)
        mock_verification_repo.get_documents_for_context.return_value = [doc]

        profile = _make_profile(user_id=user_id)
        profile.primary_email = "user@example.com"
        profile.legal_name = "Test User"
        mock_profile_repo.get_profile_by_id.return_value = profile

        updated_ctx = _make_context(
            context_id=context_id,
            user_id=user_id,
            verification_status=VerificationStatus.rejected,
        )
        mock_context_repo.update_verification_status.return_value = updated_ctx

        service_with_context.review_context(
            context_id=context_id,
            reviewer_id=uuid.uuid4(),
            status=VerificationStatus.rejected,
            rejection_reason="Document not legible",
        )

        mock_profile_repo.update_profile.assert_not_called()
        call_kwargs = mock_context_repo.update_verification_status.call_args.kwargs
        assert call_kwargs["verification_status"] == VerificationStatus.rejected
        assert call_kwargs["is_active"] is False
        assert call_kwargs["rejection_reason"] == "Document not legible"

    def test_reject_without_reason_raises(
        self,
        service_with_context,
        mock_verification_repo,
        mock_context_repo,
    ):
        """Rejecting without a reason must raise."""
        ctx = _make_context()
        mock_context_repo.get_context_profile_by_id.return_value = ctx
        mock_verification_repo.get_documents_for_context.return_value = [
            _make_document()
        ]

        with pytest.raises(
            VerificationServiceError, match="rejection_reason is required"
        ):
            service_with_context.review_context(
                context_id=uuid.uuid4(),
                reviewer_id=uuid.uuid4(),
                status=VerificationStatus.rejected,
            )

    def test_review_already_verified_raises(
        self,
        service_with_context,
        mock_context_repo,
    ):
        """A context already in verified state must not be re-reviewed."""
        ctx = _make_context(verification_status=VerificationStatus.verified)
        mock_context_repo.get_context_profile_by_id.return_value = ctx

        with pytest.raises(VerificationServiceError, match="cannot be reviewed"):
            service_with_context.review_context(
                context_id=uuid.uuid4(),
                reviewer_id=uuid.uuid4(),
                status=VerificationStatus.verified,
            )

    def test_review_nonexistent_context_raises(
        self,
        service_with_context,
        mock_context_repo,
    ):
        """Reviewing a non-existent context must raise 404."""
        mock_context_repo.get_context_profile_by_id.return_value = None

        with pytest.raises(VerificationServiceError, match="not found"):
            service_with_context.review_context(
                context_id=uuid.uuid4(),
                reviewer_id=uuid.uuid4(),
                status=VerificationStatus.verified,
            )

    def test_review_with_pending_status_raises(
        self,
        service_with_context,
        mock_context_repo,
        mock_verification_repo,
    ):
        """Setting status to 'pending' in a review must be rejected."""
        ctx = _make_context()
        mock_context_repo.get_context_profile_by_id.return_value = ctx
        mock_verification_repo.get_documents_for_context.return_value = [
            _make_document()
        ]

        with pytest.raises(
            VerificationServiceError, match="must be 'verified' or 'rejected'"
        ):
            service_with_context.review_context(
                context_id=uuid.uuid4(),
                reviewer_id=uuid.uuid4(),
                status=VerificationStatus.pending,
            )

    def test_review_context_without_documents_raises(
        self,
        service_with_context,
        mock_context_repo,
        mock_verification_repo,
    ):
        """Approving a context with no linked documents must raise 409."""
        ctx = _make_context()
        mock_context_repo.get_context_profile_by_id.return_value = ctx
        mock_verification_repo.get_documents_for_context.return_value = []

        with pytest.raises(
            VerificationServiceError, match="no linked verification documents"
        ):
            service_with_context.review_context(
                context_id=uuid.uuid4(),
                reviewer_id=uuid.uuid4(),
                status=VerificationStatus.verified,
            )

    @patch("src.tasks.email_tasks.send_approval_email")
    def test_review_logs_audit_event(
        self,
        mock_email_task,
        service_with_context,
        mock_verification_repo,
        mock_profile_repo,
        mock_context_repo,
        mock_audit_service,
    ):
        """A review must log an audit event with reviewer details."""
        ctx = _make_context()
        mock_context_repo.get_context_profile_by_id.return_value = ctx
        mock_verification_repo.get_documents_for_context.return_value = [
            _make_document()
        ]
        mock_context_repo.update_verification_status.return_value = ctx
        mock_profile_repo.get_profile_by_id.return_value = _make_profile()

        service_with_context.review_context(
            context_id=uuid.uuid4(),
            reviewer_id=uuid.uuid4(),
            status=VerificationStatus.verified,
        )

        mock_audit_service.log_event.assert_called_once()

    @patch("src.tasks.email_tasks.send_approval_email")
    def test_approve_propagates_verified_to_documents(
        self,
        mock_email_task,
        service_with_context,
        mock_verification_repo,
        mock_profile_repo,
        mock_context_repo,
    ):
        """Approving a context must mark linked documents as verified."""
        context_id = uuid.uuid4()
        user_id = uuid.uuid4()
        reviewer_id = uuid.uuid4()

        ctx = _make_context(context_id=context_id, user_id=user_id)
        mock_context_repo.get_context_profile_by_id.return_value = ctx

        doc1 = _make_document(user_id=user_id)
        doc2 = _make_document(user_id=user_id)
        mock_verification_repo.get_documents_for_context.return_value = [doc1, doc2]
        mock_context_repo.update_verification_status.return_value = ctx

        profile = _make_profile(user_id=user_id)
        profile.primary_email = "user@example.com"
        mock_profile_repo.get_profile_by_id.return_value = profile

        service_with_context.review_context(
            context_id=context_id,
            reviewer_id=reviewer_id,
            status=VerificationStatus.verified,
            document_expiry_date=date(2030, 6, 15),
        )

        assert mock_verification_repo.update_document_status.call_count == 2
        for call in mock_verification_repo.update_document_status.call_args_list:
            assert call.kwargs["status"] == VerificationStatus.verified
            assert call.kwargs["document_expiry_date"] == date(2030, 6, 15)

    @patch("src.tasks.email_tasks.send_rejection_email")
    def test_reject_propagates_rejected_to_documents(
        self,
        mock_email_task,
        service_with_context,
        mock_verification_repo,
        mock_profile_repo,
        mock_context_repo,
    ):
        """Rejecting a context must mark linked documents as rejected."""
        context_id = uuid.uuid4()
        user_id = uuid.uuid4()
        reviewer_id = uuid.uuid4()

        ctx = _make_context(context_id=context_id, user_id=user_id)
        mock_context_repo.get_context_profile_by_id.return_value = ctx

        doc = _make_document(user_id=user_id)
        mock_verification_repo.get_documents_for_context.return_value = [doc]
        mock_context_repo.update_verification_status.return_value = ctx

        profile = _make_profile(user_id=user_id)
        profile.primary_email = "user@example.com"
        mock_profile_repo.get_profile_by_id.return_value = profile

        service_with_context.review_context(
            context_id=context_id,
            reviewer_id=reviewer_id,
            status=VerificationStatus.rejected,
            rejection_reason="Image is blurry",
        )

        mock_verification_repo.update_document_status.assert_called_once()
        call_kwargs = mock_verification_repo.update_document_status.call_args.kwargs
        assert call_kwargs["status"] == VerificationStatus.rejected
        assert call_kwargs["rejection_reason"] == "Image is blurry"

    @patch("src.tasks.email_tasks.send_rejection_email")
    def test_reject_sends_rejection_email(
        self,
        mock_email_task,
        service_with_context,
        mock_verification_repo,
        mock_profile_repo,
        mock_context_repo,
    ):
        """Rejecting a context must send a rejection notification email."""
        context_id = uuid.uuid4()
        user_id = uuid.uuid4()

        ctx = _make_context(context_id=context_id, user_id=user_id)
        mock_context_repo.get_context_profile_by_id.return_value = ctx

        doc = _make_document(user_id=user_id)
        mock_verification_repo.get_documents_for_context.return_value = [doc]
        mock_context_repo.update_verification_status.return_value = ctx

        profile = _make_profile(user_id=user_id)
        profile.primary_email = "user@example.com"
        profile.legal_name = "Test User"
        mock_profile_repo.get_profile_by_id.return_value = profile

        service_with_context.review_context(
            context_id=context_id,
            reviewer_id=uuid.uuid4(),
            status=VerificationStatus.rejected,
            rejection_reason="Image is blurry",
        )

        mock_email_task.delay.assert_called_once_with(
            "user@example.com",
            "Test User",
            "Government ID",
            "Image is blurry",
        )

    @patch("src.tasks.email_tasks.send_approval_email")
    def test_approve_sends_approval_email(
        self,
        mock_email_task,
        service_with_context,
        mock_verification_repo,
        mock_profile_repo,
        mock_context_repo,
    ):
        """Approving a context must send an approval notification email."""
        context_id = uuid.uuid4()
        user_id = uuid.uuid4()

        ctx = _make_context(context_id=context_id, user_id=user_id)
        mock_context_repo.get_context_profile_by_id.return_value = ctx

        doc = _make_document(user_id=user_id)
        mock_verification_repo.get_documents_for_context.return_value = [doc]
        mock_context_repo.update_verification_status.return_value = ctx

        profile = _make_profile(user_id=user_id)
        profile.primary_email = "user@example.com"
        profile.legal_name = "Test User"
        mock_profile_repo.get_profile_by_id.return_value = profile

        service_with_context.review_context(
            context_id=context_id,
            reviewer_id=uuid.uuid4(),
            status=VerificationStatus.verified,
        )

        mock_email_task.delay.assert_called_once_with(
            "user@example.com",
            "Test User",
            "Government ID",
        )


#
# Delete tests
#


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


#
# Context-bound upload tests
#


class TestDocumentContextLinking:
    """Tests for link_document_to_context, unlink, and get_documents_for_context."""

    def test_link_document_to_valid_context(
        self,
        service_with_context,
        mock_verification_repo,
        mock_context_repo,
    ):
        """Linking a document to a valid legal context must succeed."""
        user_id = uuid.uuid4()
        context_id = uuid.uuid4()
        document_id = uuid.uuid4()

        doc = _make_document(doc_id=document_id, user_id=user_id)
        mock_verification_repo.get_document_by_id.return_value = doc

        ctx = _make_context(context_id=context_id, user_id=user_id)
        mock_context_repo.get_context_profile_by_id.return_value = ctx

        result = service_with_context.link_document_to_context(
            user_id=user_id,
            context_id=context_id,
            document_id=document_id,
        )

        assert result == doc
        mock_verification_repo.link_document_to_context.assert_called_once_with(
            context_id, document_id
        )

    def test_link_replaces_document_on_pending_context(
        self,
        service_with_context,
        mock_verification_repo,
        mock_context_repo,
    ):
        """Replacing a document on a pending context swaps the FK without changing status."""
        user_id = uuid.uuid4()
        context_id = uuid.uuid4()
        new_doc_id = uuid.uuid4()

        doc = _make_document(doc_id=new_doc_id, user_id=user_id)
        mock_verification_repo.get_document_by_id.return_value = doc

        ctx = _make_context(
            context_id=context_id,
            user_id=user_id,
            verification_status=VerificationStatus.pending,
        )
        ctx.document_id = str(uuid.uuid4())  # previous document
        mock_context_repo.get_context_profile_by_id.return_value = ctx

        service_with_context.link_document_to_context(
            user_id=user_id,
            context_id=context_id,
            document_id=new_doc_id,
        )

        mock_verification_repo.link_document_to_context.assert_called_once_with(
            context_id, new_doc_id,
        )
        mock_context_repo.update_verification_status.assert_not_called()

    def test_link_replaces_document_on_verified_context_triggers_reverification(
        self,
        service_with_context,
        mock_verification_repo,
        mock_context_repo,
    ):
        """Replacing a document on a verified context must reset status to pending."""
        user_id = uuid.uuid4()
        context_id = uuid.uuid4()
        new_doc_id = uuid.uuid4()

        doc = _make_document(doc_id=new_doc_id, user_id=user_id)
        mock_verification_repo.get_document_by_id.return_value = doc

        ctx = _make_context(
            context_id=context_id,
            user_id=user_id,
            verification_status=VerificationStatus.verified,
        )
        ctx.document_id = str(uuid.uuid4())  # previous verified document
        mock_context_repo.get_context_profile_by_id.return_value = ctx

        service_with_context.link_document_to_context(
            user_id=user_id,
            context_id=context_id,
            document_id=new_doc_id,
        )

        mock_verification_repo.link_document_to_context.assert_called_once_with(
            context_id, new_doc_id,
        )
        mock_context_repo.update_verification_status.assert_called_once_with(
            context_id=context_id,
            verification_status=VerificationStatus.pending,
            is_active=False,
        )

    def test_link_replaces_document_on_under_review_context(
        self,
        service_with_context,
        mock_verification_repo,
        mock_context_repo,
    ):
        """Replacing a document mid-review must reset status to pending."""
        user_id = uuid.uuid4()
        context_id = uuid.uuid4()
        new_doc_id = uuid.uuid4()

        doc = _make_document(doc_id=new_doc_id, user_id=user_id)
        mock_verification_repo.get_document_by_id.return_value = doc

        ctx = _make_context(
            context_id=context_id,
            user_id=user_id,
            verification_status=VerificationStatus.under_review,
        )
        ctx.document_id = str(uuid.uuid4())
        mock_context_repo.get_context_profile_by_id.return_value = ctx

        service_with_context.link_document_to_context(
            user_id=user_id,
            context_id=context_id,
            document_id=new_doc_id,
        )

        mock_context_repo.update_verification_status.assert_called_once_with(
            context_id=context_id,
            verification_status=VerificationStatus.pending,
            is_active=False,
        )

    def test_link_nonexistent_document_raises(
        self,
        service_with_context,
        mock_verification_repo,
        mock_context_repo,
    ):
        """Linking a non-existent document must raise 404."""
        mock_verification_repo.get_document_by_id.return_value = None

        with pytest.raises(VerificationServiceError, match="not found"):
            service_with_context.link_document_to_context(
                user_id=uuid.uuid4(),
                context_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
            )

    def test_link_document_wrong_user_raises(
        self,
        service_with_context,
        mock_verification_repo,
        mock_context_repo,
    ):
        """Linking a document belonging to another user must raise 403."""
        user_id = uuid.uuid4()
        other_user = uuid.uuid4()

        doc = _make_document(user_id=other_user)
        mock_verification_repo.get_document_by_id.return_value = doc

        with pytest.raises(VerificationServiceError, match="does not belong"):
            service_with_context.link_document_to_context(
                user_id=user_id,
                context_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
            )

    def test_link_nonexistent_context_raises(
        self,
        service_with_context,
        mock_verification_repo,
        mock_context_repo,
    ):
        """Linking to a non-existent context must raise 404."""
        user_id = uuid.uuid4()
        doc = _make_document(user_id=user_id)
        mock_verification_repo.get_document_by_id.return_value = doc
        mock_context_repo.get_context_profile_by_id.return_value = None

        with pytest.raises(VerificationServiceError, match="not found"):
            service_with_context.link_document_to_context(
                user_id=user_id,
                context_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
            )

    def test_link_context_wrong_user_raises(
        self,
        service_with_context,
        mock_verification_repo,
        mock_context_repo,
    ):
        """Linking to a context owned by another user must raise 403."""
        user_id = uuid.uuid4()
        other_user = uuid.uuid4()

        doc = _make_document(user_id=user_id)
        mock_verification_repo.get_document_by_id.return_value = doc

        ctx = _make_context(user_id=other_user)
        mock_context_repo.get_context_profile_by_id.return_value = ctx

        with pytest.raises(VerificationServiceError, match="does not belong"):
            service_with_context.link_document_to_context(
                user_id=user_id,
                context_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
            )

    def test_link_to_non_verification_context_raises(
        self,
        service_with_context,
        mock_verification_repo,
        mock_context_repo,
    ):
        """Linking to a context that does not require verification must raise."""
        user_id = uuid.uuid4()

        doc = _make_document(user_id=user_id)
        mock_verification_repo.get_document_by_id.return_value = doc

        ctx = _make_context(
            user_id=user_id,
            context_type=ContextType.social,
            requires_verification=False,
        )
        mock_context_repo.get_context_profile_by_id.return_value = ctx

        with pytest.raises(
            VerificationServiceError, match="does not require verification"
        ):
            service_with_context.link_document_to_context(
                user_id=user_id,
                context_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
            )

    def test_unlink_document_from_context(
        self,
        service_with_context,
        mock_verification_repo,
        mock_context_repo,
    ):
        """Unlinking a linked document must succeed."""
        user_id = uuid.uuid4()
        context_id = uuid.uuid4()
        document_id = uuid.uuid4()

        ctx = _make_context(context_id=context_id, user_id=user_id)
        mock_context_repo.get_context_profile_by_id.return_value = ctx
        mock_verification_repo.unlink_document_from_context.return_value = True

        service_with_context.unlink_document_from_context(
            user_id=user_id,
            context_id=context_id,
            document_id=document_id,
        )

        mock_verification_repo.unlink_document_from_context.assert_called_once_with(
            context_id, document_id
        )

    def test_unlink_nonexistent_link_raises(
        self,
        service_with_context,
        mock_verification_repo,
        mock_context_repo,
    ):
        """Unlinking a document not linked to the context must raise 404."""
        user_id = uuid.uuid4()

        ctx = _make_context(user_id=user_id)
        mock_context_repo.get_context_profile_by_id.return_value = ctx
        mock_verification_repo.unlink_document_from_context.return_value = False

        with pytest.raises(VerificationServiceError, match="not linked"):
            service_with_context.unlink_document_from_context(
                user_id=user_id,
                context_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
            )

    def test_link_document_resubmits_rejected_context(
        self,
        service_with_context,
        mock_verification_repo,
        mock_context_repo,
    ):
        """Linking a document to a rejected context must reset status to pending."""
        user_id = uuid.uuid4()
        context_id = uuid.uuid4()
        document_id = uuid.uuid4()

        doc = _make_document(doc_id=document_id, user_id=user_id)
        mock_verification_repo.get_document_by_id.return_value = doc

        ctx = _make_context(
            context_id=context_id,
            user_id=user_id,
            verification_status=VerificationStatus.rejected,
        )
        ctx.document_id = str(uuid.uuid4())  # previous rejected document
        ctx.rejection_reason = "Blurry image"
        mock_context_repo.get_context_profile_by_id.return_value = ctx

        service_with_context.link_document_to_context(
            user_id=user_id,
            context_id=context_id,
            document_id=document_id,
        )

        mock_context_repo.update_verification_status.assert_called_once_with(
            context_id=context_id,
            verification_status=VerificationStatus.pending,
            is_active=False,
            rejection_reason=None,
        )

    def test_link_document_does_not_change_pending_context(
        self,
        service_with_context,
        mock_verification_repo,
        mock_context_repo,
    ):
        """Linking a document to a pending context must not alter its status."""
        user_id = uuid.uuid4()
        context_id = uuid.uuid4()
        document_id = uuid.uuid4()

        doc = _make_document(doc_id=document_id, user_id=user_id)
        mock_verification_repo.get_document_by_id.return_value = doc

        ctx = _make_context(
            context_id=context_id,
            user_id=user_id,
            verification_status=VerificationStatus.pending,
        )
        mock_context_repo.get_context_profile_by_id.return_value = ctx

        service_with_context.link_document_to_context(
            user_id=user_id,
            context_id=context_id,
            document_id=document_id,
        )

        mock_context_repo.update_verification_status.assert_not_called()

    def test_get_documents_for_context(
        self,
        service_with_context,
        mock_verification_repo,
        mock_context_repo,
    ):
        """Listing documents for a context must return linked documents."""
        user_id = uuid.uuid4()
        context_id = uuid.uuid4()

        ctx = _make_context(context_id=context_id, user_id=user_id)
        mock_context_repo.get_context_profile_by_id.return_value = ctx

        docs = [_make_document(user_id=user_id), _make_document(user_id=user_id)]
        mock_verification_repo.get_documents_for_context.return_value = docs

        result = service_with_context.get_documents_for_context(
            user_id=user_id, context_id=context_id
        )

        assert result == docs
        mock_verification_repo.get_documents_for_context.assert_called_once_with(
            context_id
        )


#
# Download tests
#


class TestDownloadDocument:
    """Tests for VerificationService.download_document."""

    def test_download_returns_decrypted_content(
        self, service, mock_verification_repo, storage, encryption, mock_audit_service
    ):
        """Downloading a document must return decrypted bytes and content type."""
        doc = _make_document()
        mock_verification_repo.get_document_by_id.return_value = doc

        # Store encrypted data
        encrypted = encryption.encrypt(PDF_BYTES)
        storage.blobs[doc.storage_path] = encrypted

        plaintext, content_type = service.download_document(
            document_id=uuid.uuid4(),
            admin_id=uuid.uuid4(),
        )

        assert plaintext == PDF_BYTES
        assert content_type == "application/pdf"

    def test_download_logs_audit_event(
        self, service, mock_verification_repo, storage, encryption, mock_audit_service
    ):
        """Downloading a document must log a document_view audit event."""
        doc = _make_document()
        mock_verification_repo.get_document_by_id.return_value = doc

        encrypted = encryption.encrypt(PDF_BYTES)
        storage.blobs[doc.storage_path] = encrypted

        service.download_document(
            document_id=uuid.uuid4(),
            admin_id=uuid.uuid4(),
        )

        mock_audit_service.log_event.assert_called_once()
        call_kwargs = mock_audit_service.log_event.call_args.kwargs
        assert call_kwargs["event_type"].value == "verification.document.view"
        assert call_kwargs["operation"].value == "read"

    def test_download_nonexistent_raises(
        self, service, mock_verification_repo
    ):
        """Downloading a non-existent document must raise 404."""
        mock_verification_repo.get_document_by_id.return_value = None

        with pytest.raises(VerificationServiceError, match="not found"):
            service.download_document(uuid.uuid4(), uuid.uuid4())

    def test_download_no_storage_path_raises(
        self, service, mock_verification_repo
    ):
        """Downloading a document without storage_path must raise 404."""
        doc = _make_document()
        doc.storage_path = None
        mock_verification_repo.get_document_by_id.return_value = doc

        with pytest.raises(VerificationServiceError, match="no associated file"):
            service.download_document(uuid.uuid4(), uuid.uuid4())


#
# Owner download tests
#


class TestDownloadDocumentForOwner:
    """Tests for VerificationService.download_document_for_owner."""

    def test_download_own_document_success(
        self, service, mock_verification_repo, storage, encryption, mock_audit_service
    ):
        """The owning user must be able to download their own document."""
        user_id = uuid.uuid4()
        doc = _make_document(user_id=user_id)
        mock_verification_repo.get_document_by_id.return_value = doc

        encrypted = encryption.encrypt(PDF_BYTES)
        storage.blobs[doc.storage_path] = encrypted

        plaintext, content_type = service.download_document_for_owner(
            document_id=uuid.uuid4(),
            owner_id=user_id,
        )

        assert plaintext == PDF_BYTES
        assert content_type == "application/pdf"
        mock_audit_service.log_event.assert_called_once()
        call_kwargs = mock_audit_service.log_event.call_args.kwargs
        assert call_kwargs["legal_basis"] == "consent"

    def test_download_wrong_user_raises(
        self, service, mock_verification_repo
    ):
        """Downloading another user's document must raise 403."""
        doc = _make_document(user_id=uuid.uuid4())
        mock_verification_repo.get_document_by_id.return_value = doc

        with pytest.raises(VerificationServiceError, match="your own"):
            service.download_document_for_owner(
                document_id=uuid.uuid4(),
                owner_id=uuid.uuid4(),
            )

    def test_download_nonexistent_raises(
        self, service, mock_verification_repo
    ):
        """Downloading a non-existent document must raise 404."""
        mock_verification_repo.get_document_by_id.return_value = None

        with pytest.raises(VerificationServiceError, match="not found"):
            service.download_document_for_owner(uuid.uuid4(), uuid.uuid4())
