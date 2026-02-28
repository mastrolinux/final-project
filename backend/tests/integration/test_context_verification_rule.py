"""Integration tests for context-bound verification business rules."""

import pytest
from sqlalchemy.orm import Session

from src.models.context import ContextType
from src.models.verification import VerificationStatus
from src.repositories.audit_repository import AuditRepository
from src.repositories.context_repository import ContextRepository
from src.repositories.profile_repository import ProfileRepository
from src.services.audit_service import AuditService
from src.services.context_service import ContextService, ContextServiceError


@pytest.fixture
def context_service(db_session: Session):
    """Build a ContextService with real repositories."""
    context_repo = ContextRepository(db_session)
    profile_repo = ProfileRepository(db_session)
    audit_repo = AuditRepository(db_session)
    audit_service = AuditService(audit_repo)
    return ContextService(context_repo, profile_repo, audit_service=audit_service)


class TestContextVerificationRule:
    """Tests for the context-bound legal/healthcare verification rules."""

    def test_verified_can_create_legal_context(self, context_service, sample_verified_profile):
        """A verified account creates a legal context starting as pending."""
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.legal,
            context_name="Government ID",
        )
        assert context.context_type == ContextType.legal
        assert context.verification_status == VerificationStatus.pending
        assert context.is_active is False

    def test_verified_can_create_healthcare_context(self, context_service, sample_verified_profile):
        """A verified account creates a healthcare context starting as pending."""
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.healthcare,
            context_name="Hospital Records",
        )
        assert context.context_type == ContextType.healthcare
        assert context.verification_status == VerificationStatus.pending
        assert context.is_active is False

    def test_unverified_can_create_legal_context_pending(
        self, context_service, sample_unverified_profile
    ):
        """An unverified account can create a legal context (starts pending)."""
        context = context_service.create_context_profile(
            user_id=sample_unverified_profile.user_id,
            context_type=ContextType.legal,
            context_name="Government ID",
        )
        assert context.context_type == ContextType.legal
        assert context.verification_status == VerificationStatus.pending
        assert context.is_active is False

    def test_unverified_can_create_healthcare_context_pending(
        self, context_service, sample_unverified_profile
    ):
        """An unverified account can create a healthcare context (starts pending)."""
        context = context_service.create_context_profile(
            user_id=sample_unverified_profile.user_id,
            context_type=ContextType.healthcare,
            context_name="Medical Records",
        )
        assert context.verification_status == VerificationStatus.pending
        assert context.is_active is False

    def test_pseudonymous_blocked_from_legal_context(
        self, context_service, sample_pseudonymous_profile
    ):
        """A pseudonymous account must be blocked from creating legal contexts."""
        with pytest.raises(ContextServiceError, match="Pseudonymous accounts"):
            context_service.create_context_profile(
                user_id=sample_pseudonymous_profile.user_id,
                context_type=ContextType.legal,
                context_name="Government ID",
            )

    def test_pseudonymous_blocked_from_healthcare_context(
        self, context_service, sample_pseudonymous_profile
    ):
        """A pseudonymous account must be blocked from creating healthcare contexts."""
        with pytest.raises(ContextServiceError, match="Pseudonymous accounts"):
            context_service.create_context_profile(
                user_id=sample_pseudonymous_profile.user_id,
                context_type=ContextType.healthcare,
                context_name="Medical Records",
            )

    def test_professional_context_starts_active_no_verification(
        self, context_service, sample_unverified_profile
    ):
        """Professional contexts must start active with no verification requirement."""
        context = context_service.create_context_profile(
            user_id=sample_unverified_profile.user_id,
            context_type=ContextType.professional,
            context_name="LinkedIn",
        )
        assert context.context_type == ContextType.professional
        assert context.is_active is True
        assert context.verification_status is None

    def test_social_context_starts_active_no_verification(
        self, context_service, sample_unverified_profile
    ):
        """Social contexts must start active with no verification requirement."""
        context = context_service.create_context_profile(
            user_id=sample_unverified_profile.user_id,
            context_type=ContextType.social,
            context_name="Twitter",
        )
        assert context.context_type == ContextType.social
        assert context.is_active is True
        assert context.verification_status is None

    def test_pseudonymous_can_create_social_context(
        self, context_service, sample_pseudonymous_profile
    ):
        """Pseudonymous accounts must still be allowed to create social contexts."""
        context = context_service.create_context_profile(
            user_id=sample_pseudonymous_profile.user_id,
            context_type=ContextType.social,
            context_name="Reddit",
        )
        assert context.context_type == ContextType.social
        assert context.is_active is True


class TestIdentityChangeReverification:
    """Tests for re-verification when identity fields change on verified contexts."""

    def test_identity_change_resets_verified_legal_context(
        self, context_service, sample_verified_profile, db_session
    ):
        """Changing display_name on a verified legal context resets verification."""
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.legal,
            context_name="Tax Filing",
            display_name_override="Original Name",
        )

        context_repo = ContextRepository(db_session)
        context_repo.update_verification_status(
            context.id, VerificationStatus.verified, is_active=True
        )

        updated = context_service.update_context_profile(
            context_id=context.id,
            display_name_override="Changed Name",
        )

        assert updated.verification_status == VerificationStatus.pending
        assert updated.is_active is False

    def test_non_identity_change_preserves_verification(
        self, context_service, sample_verified_profile, db_session
    ):
        """Changing bio on a verified legal context must not reset verification."""
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.legal,
            context_name="Contract Signing",
        )

        context_repo = ContextRepository(db_session)
        context_repo.update_verification_status(
            context.id, VerificationStatus.verified, is_active=True
        )

        updated = context_service.update_context_profile(
            context_id=context.id,
            bio="Updated biography text",
        )

        assert updated.verification_status == VerificationStatus.verified
        assert updated.is_active is True
