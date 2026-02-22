"""
Context Creation Verification Rule Tests

Validates the tightened business rule: only verified accounts can
create legal or healthcare context profiles. Both unverified and
pseudonymous accounts must be blocked.
"""

import pytest
from sqlalchemy.orm import Session

from src.models.context import ContextType
from src.models.profile import AccountType, BaseProfile
from src.repositories.context_repository import ContextRepository
from src.repositories.profile_repository import ProfileRepository
from src.repositories.audit_repository import AuditRepository
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
    """Tests for the tightened legal/healthcare context creation rule."""

    def test_verified_can_create_legal_context(
        self, context_service, sample_verified_profile
    ):
        """A verified account must be allowed to create a legal context."""
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.legal,
            context_name="Government ID",
        )
        assert context.context_type == ContextType.legal

    def test_verified_can_create_healthcare_context(
        self, context_service, sample_verified_profile
    ):
        """A verified account must be allowed to create a healthcare context."""
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.healthcare,
            context_name="Hospital Records",
        )
        assert context.context_type == ContextType.healthcare

    def test_unverified_blocked_from_legal_context(
        self, context_service, sample_unverified_profile
    ):
        """An unverified account must be blocked from creating legal contexts."""
        with pytest.raises(ContextServiceError, match="identity-verified accounts"):
            context_service.create_context_profile(
                user_id=sample_unverified_profile.user_id,
                context_type=ContextType.legal,
                context_name="Government ID",
            )

    def test_unverified_blocked_from_healthcare_context(
        self, context_service, sample_unverified_profile
    ):
        """An unverified account must be blocked from creating healthcare contexts."""
        with pytest.raises(ContextServiceError, match="identity-verified accounts"):
            context_service.create_context_profile(
                user_id=sample_unverified_profile.user_id,
                context_type=ContextType.healthcare,
                context_name="Medical Records",
            )

    def test_pseudonymous_blocked_from_legal_context(
        self, context_service, sample_pseudonymous_profile
    ):
        """A pseudonymous account must be blocked from creating legal contexts."""
        with pytest.raises(ContextServiceError, match="identity-verified accounts"):
            context_service.create_context_profile(
                user_id=sample_pseudonymous_profile.user_id,
                context_type=ContextType.legal,
                context_name="Government ID",
            )

    def test_pseudonymous_blocked_from_healthcare_context(
        self, context_service, sample_pseudonymous_profile
    ):
        """A pseudonymous account must be blocked from creating healthcare contexts."""
        with pytest.raises(ContextServiceError, match="identity-verified accounts"):
            context_service.create_context_profile(
                user_id=sample_pseudonymous_profile.user_id,
                context_type=ContextType.healthcare,
                context_name="Medical Records",
            )

    def test_unverified_can_create_professional_context(
        self, context_service, sample_unverified_profile
    ):
        """Unverified accounts must still be allowed to create professional contexts."""
        context = context_service.create_context_profile(
            user_id=sample_unverified_profile.user_id,
            context_type=ContextType.professional,
            context_name="LinkedIn",
        )
        assert context.context_type == ContextType.professional

    def test_unverified_can_create_social_context(
        self, context_service, sample_unverified_profile
    ):
        """Unverified accounts must still be allowed to create social contexts."""
        context = context_service.create_context_profile(
            user_id=sample_unverified_profile.user_id,
            context_type=ContextType.social,
            context_name="Twitter",
        )
        assert context.context_type == ContextType.social

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
