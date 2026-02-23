"""
Document Expiry Task Unit Tests

Tests business logic for automatic context deactivation when linked
verification documents expire. Covers the
``VerificationService.process_expired_documents`` method using
mocked repositories and email tasks.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.models.context import ContextProfile, ContextType
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
# Helpers
# ---------------------------------------------------------------------------


def _make_expired_document(
    doc_id=None,
    user_id=None,
    expiry_date=None,
) -> MagicMock:
    """Create a mock verified document with an expiry date in the past."""
    doc = MagicMock(spec=VerificationDocument)
    doc.id = str(doc_id or uuid.uuid4())
    doc.user_id = str(user_id or uuid.uuid4())
    doc.document_type = DocumentType.passport
    doc.verification_status = VerificationStatus.verified
    doc.document_expiry_date = expiry_date or (
        date.today() - timedelta(days=1)
    )
    doc.storage_path = f"{doc.user_id}/blob/doc.pdf"
    doc.original_filename = "passport.pdf"
    doc.file_size_bytes = 2048
    doc.content_type = "application/pdf"
    doc.created_at = datetime.now(timezone.utc)
    doc.updated_at = datetime.now(timezone.utc)
    return doc


def _make_active_context(
    context_id=None,
    user_id=None,
    context_type=ContextType.legal,
    context_name="Government ID",
) -> MagicMock:
    """Create a mock active context profile linked to a document."""
    ctx = MagicMock(spec=ContextProfile)
    ctx.id = str(context_id or uuid.uuid4())
    ctx.user_id = user_id or str(uuid.uuid4())
    ctx.context_type = context_type
    ctx.context_name = context_name
    ctx.verification_status = VerificationStatus.verified
    ctx.is_active = True
    ctx.rejection_reason = None
    return ctx


def _make_profile(
    user_id=None,
    account_type=AccountType.verified,
) -> MagicMock:
    """Create a mock base profile."""
    profile = MagicMock(spec=BaseProfile)
    profile.user_id = str(user_id or uuid.uuid4())
    profile.account_type = account_type
    profile.legal_name = "Test User"
    profile.primary_email = "test@example.com"
    return profile


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_verification_repo():
    repo = MagicMock()
    repo.get_expired_verified_documents.return_value = []
    repo.mark_document_expired.return_value = None
    repo.unlink_document_from_context.return_value = True
    return repo


@pytest.fixture
def mock_context_repo():
    repo = MagicMock()
    repo.get_active_contexts_by_document_id.return_value = []
    return repo


@pytest.fixture
def mock_profile_repo():
    return MagicMock()


@pytest.fixture
def mock_audit_service():
    return MagicMock()


@pytest.fixture
def service(
    mock_verification_repo,
    mock_profile_repo,
    mock_context_repo,
    mock_audit_service,
):
    """Service instance configured for expiry processing (no storage/encryption)."""
    return VerificationService(
        verification_repo=mock_verification_repo,
        profile_repo=mock_profile_repo,
        audit_service=mock_audit_service,
        context_repo=mock_context_repo,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestProcessExpiredDocuments:
    """Tests for VerificationService.process_expired_documents."""

    def test_no_expired_documents(self, service, mock_verification_repo):
        """Returns zero counts when no documents have expired."""
        mock_verification_repo.get_expired_verified_documents.return_value = []

        result = service.process_expired_documents()

        assert result == {"expired_documents": 0, "deactivated_contexts": 0}
        mock_verification_repo.mark_document_expired.assert_not_called()

    def test_deactivates_context_for_expired_document(
        self,
        service,
        mock_verification_repo,
        mock_context_repo,
        mock_profile_repo,
    ):
        """An expired verified document deactivates its linked active context."""
        user_id = str(uuid.uuid4())
        doc = _make_expired_document(user_id=user_id)
        ctx = _make_active_context(user_id=user_id)
        profile = _make_profile(user_id=user_id)

        mock_verification_repo.get_expired_verified_documents.return_value = [doc]
        mock_context_repo.get_active_contexts_by_document_id.return_value = [ctx]
        mock_profile_repo.get_profile_by_id.return_value = profile

        with patch("src.tasks.email_tasks.send_document_expiry_email"):
            result = service.process_expired_documents()

        assert result == {"expired_documents": 1, "deactivated_contexts": 1}

        mock_context_repo.update_verification_status.assert_called_once_with(
            context_id=ctx.id,
            verification_status=VerificationStatus.pending,
            is_active=False,
        )
        mock_verification_repo.unlink_document_from_context.assert_called_once_with(
            ctx.id, doc.id
        )

    def test_marks_document_as_expired_after_processing(
        self,
        service,
        mock_verification_repo,
        mock_context_repo,
    ):
        """The document's status transitions to 'expired' after processing."""
        doc = _make_expired_document()
        mock_verification_repo.get_expired_verified_documents.return_value = [doc]
        mock_context_repo.get_active_contexts_by_document_id.return_value = []

        result = service.process_expired_documents()

        mock_verification_repo.mark_document_expired.assert_called_once_with(
            doc.id
        )
        assert result["expired_documents"] == 1

    def test_unlinks_document_from_each_context(
        self,
        service,
        mock_verification_repo,
        mock_context_repo,
        mock_profile_repo,
    ):
        """All linked contexts are unlinked from the expired document."""
        user_id = str(uuid.uuid4())
        doc = _make_expired_document(user_id=user_id)
        ctx1 = _make_active_context(user_id=user_id, context_name="Legal")
        ctx2 = _make_active_context(
            user_id=user_id,
            context_type=ContextType.healthcare,
            context_name="Healthcare",
        )
        profile = _make_profile(user_id=user_id)

        mock_verification_repo.get_expired_verified_documents.return_value = [doc]
        mock_context_repo.get_active_contexts_by_document_id.return_value = [
            ctx1, ctx2
        ]
        mock_profile_repo.get_profile_by_id.return_value = profile

        with patch("src.tasks.email_tasks.send_document_expiry_email"):
            result = service.process_expired_documents()

        assert result["deactivated_contexts"] == 2
        assert mock_verification_repo.unlink_document_from_context.call_count == 2

    @patch("src.tasks.email_tasks.send_document_expiry_email")
    def test_sends_notification_email(
        self,
        mock_email_task,
        service,
        mock_verification_repo,
        mock_context_repo,
        mock_profile_repo,
    ):
        """A notification email is queued for each affected user."""
        user_id = str(uuid.uuid4())
        doc = _make_expired_document(user_id=user_id)
        ctx = _make_active_context(user_id=user_id, context_name="Legal ID")
        profile = _make_profile(user_id=user_id)

        mock_verification_repo.get_expired_verified_documents.return_value = [doc]
        mock_context_repo.get_active_contexts_by_document_id.return_value = [ctx]
        mock_profile_repo.get_profile_by_id.return_value = profile

        service.process_expired_documents()

        mock_email_task.delay.assert_called_once_with(
            profile.primary_email,
            profile.legal_name,
            ["Legal ID"],
            str(doc.document_expiry_date),
        )

    def test_no_email_when_no_contexts_affected(
        self,
        service,
        mock_verification_repo,
        mock_context_repo,
        mock_profile_repo,
    ):
        """No email is sent when an expired document has no active contexts."""
        doc = _make_expired_document()
        mock_verification_repo.get_expired_verified_documents.return_value = [doc]
        mock_context_repo.get_active_contexts_by_document_id.return_value = []

        service.process_expired_documents()

        mock_profile_repo.get_profile_by_id.assert_not_called()

    def test_email_failure_does_not_block_processing(
        self,
        service,
        mock_verification_repo,
        mock_context_repo,
        mock_profile_repo,
    ):
        """If email queuing fails, remaining documents are still processed."""
        user_id_1 = str(uuid.uuid4())
        user_id_2 = str(uuid.uuid4())
        doc1 = _make_expired_document(user_id=user_id_1)
        doc2 = _make_expired_document(user_id=user_id_2)
        ctx1 = _make_active_context(user_id=user_id_1)
        ctx2 = _make_active_context(user_id=user_id_2)
        profile1 = _make_profile(user_id=user_id_1)
        profile2 = _make_profile(user_id=user_id_2)

        mock_verification_repo.get_expired_verified_documents.return_value = [
            doc1, doc2
        ]
        mock_context_repo.get_active_contexts_by_document_id.side_effect = [
            [ctx1], [ctx2]
        ]
        mock_profile_repo.get_profile_by_id.side_effect = [profile1, profile2]

        with patch(
            "src.tasks.email_tasks.send_document_expiry_email",
        ) as mock_email:
            mock_email.delay.side_effect = [Exception("Redis down"), None]
            result = service.process_expired_documents()

        # Both documents should be processed despite email failure
        assert result == {"expired_documents": 2, "deactivated_contexts": 2}
        assert mock_verification_repo.mark_document_expired.call_count == 2

    def test_logs_audit_event_per_context(
        self,
        service,
        mock_verification_repo,
        mock_context_repo,
        mock_audit_service,
        mock_profile_repo,
    ):
        """An audit event is recorded for each deactivated context."""
        user_id = str(uuid.uuid4())
        doc = _make_expired_document(user_id=user_id)
        ctx1 = _make_active_context(user_id=user_id)
        ctx2 = _make_active_context(user_id=user_id)
        profile = _make_profile(user_id=user_id)

        mock_verification_repo.get_expired_verified_documents.return_value = [doc]
        mock_context_repo.get_active_contexts_by_document_id.return_value = [
            ctx1, ctx2
        ]
        mock_profile_repo.get_profile_by_id.return_value = profile

        with patch("src.tasks.email_tasks.send_document_expiry_email"):
            service.process_expired_documents()

        assert mock_audit_service.log_event.call_count == 2

    def test_processes_multiple_expired_documents(
        self,
        service,
        mock_verification_repo,
        mock_context_repo,
        mock_profile_repo,
    ):
        """Multiple expired documents are all processed in a single run."""
        docs = [_make_expired_document() for _ in range(3)]
        contexts = [
            [_make_active_context(user_id=d.user_id)] for d in docs
        ]

        mock_verification_repo.get_expired_verified_documents.return_value = docs
        mock_context_repo.get_active_contexts_by_document_id.side_effect = contexts
        mock_profile_repo.get_profile_by_id.side_effect = [
            _make_profile(user_id=d.user_id) for d in docs
        ]

        with patch("src.tasks.email_tasks.send_document_expiry_email"):
            result = service.process_expired_documents()

        assert result == {"expired_documents": 3, "deactivated_contexts": 3}
        assert mock_verification_repo.mark_document_expired.call_count == 3

    def test_returns_correct_counts(
        self,
        service,
        mock_verification_repo,
        mock_context_repo,
        mock_profile_repo,
    ):
        """Counts reflect total documents and total contexts deactivated."""
        user_id = str(uuid.uuid4())
        doc = _make_expired_document(user_id=user_id)
        contexts = [
            _make_active_context(user_id=user_id) for _ in range(3)
        ]
        profile = _make_profile(user_id=user_id)

        mock_verification_repo.get_expired_verified_documents.return_value = [doc]
        mock_context_repo.get_active_contexts_by_document_id.return_value = contexts
        mock_profile_repo.get_profile_by_id.return_value = profile

        with patch("src.tasks.email_tasks.send_document_expiry_email"):
            result = service.process_expired_documents()

        assert result["expired_documents"] == 1
        assert result["deactivated_contexts"] == 3

    def test_raises_without_context_repo(
        self,
        mock_verification_repo,
        mock_profile_repo,
        mock_audit_service,
    ):
        """Raises VerificationServiceError if context_repo is not configured."""
        svc = VerificationService(
            verification_repo=mock_verification_repo,
            profile_repo=mock_profile_repo,
            audit_service=mock_audit_service,
            context_repo=None,
        )

        with pytest.raises(VerificationServiceError) as exc_info:
            svc.process_expired_documents()

        assert exc_info.value.status_code == 500
        assert "Context repository not configured" in str(exc_info.value)

    def test_service_without_storage_encryption(
        self,
        mock_verification_repo,
        mock_profile_repo,
        mock_context_repo,
        mock_audit_service,
    ):
        """Service can be instantiated without storage/encryption for expiry tasks."""
        svc = VerificationService(
            verification_repo=mock_verification_repo,
            profile_repo=mock_profile_repo,
            audit_service=mock_audit_service,
            context_repo=mock_context_repo,
        )

        assert svc.storage is None
        assert svc.encryption is None

        mock_verification_repo.get_expired_verified_documents.return_value = []
        result = svc.process_expired_documents()
        assert result == {"expired_documents": 0, "deactivated_contexts": 0}

    def test_no_email_when_user_has_no_email(
        self,
        service,
        mock_verification_repo,
        mock_context_repo,
        mock_profile_repo,
    ):
        """No email is sent when the user's profile has no primary_email."""
        user_id = str(uuid.uuid4())
        doc = _make_expired_document(user_id=user_id)
        ctx = _make_active_context(user_id=user_id)
        profile = _make_profile(user_id=user_id)
        profile.primary_email = None

        mock_verification_repo.get_expired_verified_documents.return_value = [doc]
        mock_context_repo.get_active_contexts_by_document_id.return_value = [ctx]
        mock_profile_repo.get_profile_by_id.return_value = profile

        # Should not raise and should not attempt to send email
        with patch(
            "src.tasks.email_tasks.send_document_expiry_email",
        ) as mock_email:
            service.process_expired_documents()
            mock_email.delay.assert_not_called()

    def test_context_name_fallback_to_type(
        self,
        service,
        mock_verification_repo,
        mock_context_repo,
        mock_profile_repo,
    ):
        """When context_name is None, context_type.value is used in email."""
        user_id = str(uuid.uuid4())
        doc = _make_expired_document(user_id=user_id)
        ctx = _make_active_context(user_id=user_id)
        ctx.context_name = None
        ctx.context_type = ContextType.legal
        profile = _make_profile(user_id=user_id)

        mock_verification_repo.get_expired_verified_documents.return_value = [doc]
        mock_context_repo.get_active_contexts_by_document_id.return_value = [ctx]
        mock_profile_repo.get_profile_by_id.return_value = profile

        with patch(
            "src.tasks.email_tasks.send_document_expiry_email",
        ) as mock_email:
            service.process_expired_documents()
            call_args = mock_email.delay.call_args
            context_names_arg = call_args[0][2]
            assert context_names_arg == ["legal"]
