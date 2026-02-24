"""Tests for context profile inheritance engine and management."""

import pytest
from uuid import uuid4
from datetime import date, timedelta

from src.models.context import ContextType
from src.models.profile import BaseProfile, IdentityName, AccountType, NameType, VisibilityLevel
from src.models.verification import VerificationDocument, DocumentType, VerificationStatus
from src.repositories.context_repository import ContextRepository
from src.repositories.profile_repository import ProfileRepository
from src.services.context_service import ContextService, ContextServiceError


@pytest.fixture
def context_repository(db_session):
    """Create ContextRepository instance for testing"""
    return ContextRepository(db_session)


@pytest.fixture
def context_service(context_repository, profile_repository):
    """Create ContextService instance for testing"""
    return ContextService(context_repository, profile_repository)


class TestContextCreation:
    """Test context profile creation with business rules"""
    
    def test_create_context_profile_success(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """Test successful context profile creation"""
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.professional,
            context_name="LinkedIn",
            display_name_override="Dr. Sarah Chen, MD, PhD",
            email_override="s.chen@hospital.org",
            bio="Board-certified psychiatrist"
        )
        
        assert context.user_id == sample_verified_profile.user_id
        assert context.context_type == ContextType.professional
        assert context.context_name == "LinkedIn"
        assert context.display_name_override == "Dr. Sarah Chen, MD, PhD"
        assert context.email_override == "s.chen@hospital.org"
        assert context.bio == "Board-certified psychiatrist"
        assert context.is_active is True
    
    def test_create_context_with_minimal_overrides(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """Test creating context with only required fields"""
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.social,
            context_name="Facebook"
        )
        
        assert context.context_type == ContextType.social
        assert context.context_name == "Facebook"
        assert context.display_name_override is None
        assert context.email_override is None
        assert context.phone_override is None
        assert context.bio is None
    
    def test_create_context_for_nonexistent_user(
        self,
        context_service: ContextService
    ):
        """Test creating context for non-existent user fails"""
        fake_user_id = uuid4()
        
        with pytest.raises(ContextServiceError) as exc_info:
            context_service.create_context_profile(
                user_id=fake_user_id,
                context_type=ContextType.professional,
                context_name="Work"
            )
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_pseudonymous_cannot_create_legal_context(
        self,
        context_service: ContextService,
        sample_pseudonymous_profile: BaseProfile
    ):
        """Test pseudonymous accounts cannot create legal contexts"""
        with pytest.raises(ContextServiceError) as exc_info:
            context_service.create_context_profile(
                user_id=sample_pseudonymous_profile.user_id,
                context_type=ContextType.legal,
                context_name="Government"
            )

        assert "pseudonymous" in str(exc_info.value).lower()
        assert "legal" in str(exc_info.value).lower()

    def test_pseudonymous_cannot_create_healthcare_context(
        self,
        context_service: ContextService,
        sample_pseudonymous_profile: BaseProfile
    ):
        """Test pseudonymous accounts cannot create healthcare contexts"""
        with pytest.raises(ContextServiceError) as exc_info:
            context_service.create_context_profile(
                user_id=sample_pseudonymous_profile.user_id,
                context_type=ContextType.healthcare,
                context_name="Hospital"
            )

        assert "pseudonymous" in str(exc_info.value).lower()
        assert "healthcare" in str(exc_info.value).lower()

    def test_unverified_creates_legal_context_pending(
        self,
        context_service: ContextService,
        sample_unverified_profile: BaseProfile
    ):
        """Unverified accounts can create legal contexts (starts pending/inactive)."""
        from src.models.verification import VerificationStatus
        context = context_service.create_context_profile(
            user_id=sample_unverified_profile.user_id,
            context_type=ContextType.legal,
            context_name="Government"
        )
        assert context.verification_status == VerificationStatus.pending
        assert context.is_active is False

    def test_unverified_creates_healthcare_context_pending(
        self,
        context_service: ContextService,
        sample_unverified_profile: BaseProfile
    ):
        """Unverified accounts can create healthcare contexts (starts pending/inactive)."""
        from src.models.verification import VerificationStatus
        context = context_service.create_context_profile(
            user_id=sample_unverified_profile.user_id,
            context_type=ContextType.healthcare,
            context_name="Hospital"
        )
        assert context.verification_status == VerificationStatus.pending
        assert context.is_active is False
    
    def test_duplicate_context_fails(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """Test creating duplicate context (user_id, type, name) fails"""
        context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.professional,
            context_name="LinkedIn"
        )
        
        with pytest.raises(ContextServiceError) as exc_info:
            context_service.create_context_profile(
                user_id=sample_verified_profile.user_id,
                context_type=ContextType.professional,
                context_name="LinkedIn"
            )
        
        assert "already exists" in str(exc_info.value).lower()
    
    def test_invalid_email_override_fails(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """Test invalid email override format fails"""
        with pytest.raises(ContextServiceError) as exc_info:
            context_service.create_context_profile(
                user_id=sample_verified_profile.user_id,
                context_type=ContextType.professional,
                context_name="Work",
                email_override="not-an-email"
            )
        
        assert "invalid email" in str(exc_info.value).lower()


class TestInheritanceEngine:
    """Test profile resolution with inheritance."""
    
    def test_resolve_context_with_full_overrides(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile,
        sample_identity_name: IdentityName
    ):
        """Test resolving context with all fields overridden"""
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.professional,
            context_name="Work",
            display_name_override="Dr. Sarah Chen",
            email_override="work@hospital.org",
            phone_override="+1-555-9999",
            bio="Professional bio"
        )
        
        resolved = context_service.resolve_context_profile(
            user_id=sample_verified_profile.user_id,
            context_id=context.id
        )

        assert resolved.display_name == "Dr. Sarah Chen"
        assert resolved.email == "work@hospital.org"
        assert resolved.phone == "+1-555-9999"
        assert resolved.bio == "Professional bio"

        assert resolved.user_id == sample_verified_profile.user_id
        assert resolved.account_type == sample_verified_profile.account_type
        assert resolved.preferred_language == sample_verified_profile.preferred_language

        assert resolved.context_type == ContextType.professional
        assert resolved.context_name == "Work"
    
    def test_resolve_context_with_partial_overrides(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """Null overrides should inherit from base profile."""
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.professional,
            context_name="Work",
            email_override="work@company.com"
            # display_name_override, phone_override, bio are None
        )
        
        resolved = context_service.resolve_context_profile(
            user_id=sample_verified_profile.user_id,
            context_id=context.id
        )

        assert resolved.email == "work@company.com"
        assert resolved.phone == sample_verified_profile.primary_phone
        assert resolved.display_name is None
        assert resolved.bio is None
    
    def test_resolve_context_with_no_overrides(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """No overrides: all values should inherit from base profile."""
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.social,
            context_name="Personal"
        )
        
        resolved = context_service.resolve_context_profile(
            user_id=sample_verified_profile.user_id,
            context_id=context.id
        )

        assert resolved.email == sample_verified_profile.primary_email
        assert resolved.phone == sample_verified_profile.primary_phone
        assert resolved.display_name is None
        assert resolved.bio is None
        assert resolved.preferred_language == sample_verified_profile.preferred_language

    def test_resolve_context_does_not_inherit_base_avatar(
        self,
        db_session,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """
        Avatar is NOT inherited from the base profile into resolved contexts.

        Privacy-by-design: a user's base avatar should never leak into a
        context without explicit consent.  The resolved profile returns None
        for avatar fields unless the context has its own avatar_override.
        """
        sample_verified_profile.avatar_url = "https://storage.example.com/avatar.webp"
        sample_verified_profile.avatar_thumbnail_url = "https://storage.example.com/thumb.webp"
        db_session.commit()

        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.social,
            context_name="Social"
        )

        resolved = context_service.resolve_context_profile(
            user_id=sample_verified_profile.user_id,
            context_id=context.id
        )

        assert resolved.avatar_url is None
        assert resolved.avatar_thumbnail_url is None

    def test_resolve_context_uses_explicit_avatar_override(
        self,
        db_session,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """
        When a context has an explicit avatar_override, the resolved profile
        returns that override (not the base avatar).
        """
        sample_verified_profile.avatar_url = "https://storage.example.com/base.webp"
        sample_verified_profile.avatar_thumbnail_url = "https://storage.example.com/base-thumb.webp"
        db_session.commit()

        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.professional,
            context_name="Work"
        )
        context.avatar_override_url = "https://storage.example.com/work.webp"
        context.avatar_override_thumbnail_url = "https://storage.example.com/work-thumb.webp"
        db_session.commit()

        resolved = context_service.resolve_context_profile(
            user_id=sample_verified_profile.user_id,
            context_id=context.id
        )

        assert resolved.avatar_url == "https://storage.example.com/work.webp"
        assert resolved.avatar_thumbnail_url == "https://storage.example.com/work-thumb.webp"

    def test_resolve_base_profile_without_context(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile,
        sample_identity_name: IdentityName
    ):
        """Test resolving base profile without any context"""
        resolved = context_service.resolve_base_profile(
            user_id=sample_verified_profile.user_id
        )
        
        assert resolved.user_id == sample_verified_profile.user_id
        assert resolved.email == sample_verified_profile.primary_email
        assert resolved.phone == sample_verified_profile.primary_phone
        assert resolved.preferred_language == sample_verified_profile.preferred_language
        
        assert resolved.context_type is None
        assert resolved.context_name is None
        assert resolved.display_name is None
        assert resolved.bio is None
        
        assert len(resolved.identity_names) > 0
    
    def test_resolved_profile_includes_identity_names(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile,
        sample_identity_name: IdentityName
    ):
        """Test resolved profile includes identity names"""
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.professional,
            context_name="Work"
        )
        
        resolved = context_service.resolve_context_profile(
            user_id=sample_verified_profile.user_id,
            context_id=context.id
        )
        
        assert len(resolved.identity_names) == 1
        assert resolved.identity_names[0].name_type == NameType.full_name
        assert resolved.identity_names[0].name_value == {"en": "Dr. Sarah Chen"}
    
    def test_resolved_profile_filters_deprecated_names(
        self,
        db_session,
        context_service: ContextService,
        sample_verified_profile: BaseProfile,
        sample_identity_name: IdentityName
    ):
        """Test deprecated names are filtered from resolved profile"""
        deprecated = IdentityName(
            identity_id=sample_verified_profile.user_id,
            name_type=NameType.given,
            name_value={"en": "[REDACTED]"},
            is_primary=False,
            is_deprecated=True,
            visibility_level=VisibilityLevel.historical_suppressed
        )
        db_session.add(deprecated)
        db_session.commit()
        
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.social,
            context_name="Friends"
        )
        
        resolved = context_service.resolve_context_profile(
            user_id=sample_verified_profile.user_id,
            context_id=context.id,
            include_deprecated_names=False
        )
        
        assert len(resolved.identity_names) == 1
        assert resolved.identity_names[0].is_deprecated is False
        
        resolved_with_deprecated = context_service.resolve_context_profile(
            user_id=sample_verified_profile.user_id,
            context_id=context.id,
            include_deprecated_names=True
        )
        
        assert len(resolved_with_deprecated.identity_names) == 2
    
    def test_resolve_context_not_belonging_to_user_fails(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile,
        sample_unverified_profile: BaseProfile
    ):
        """Test resolving context that doesn't belong to user fails"""
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.professional,
            context_name="Work"
        )
        
        with pytest.raises(ContextServiceError) as exc_info:
            context_service.resolve_context_profile(
                user_id=sample_unverified_profile.user_id,
                context_id=context.id
            )
        
        assert "does not belong" in str(exc_info.value).lower()


class TestContextManagement:
    """Test context CRUD operations"""
    
    def test_get_user_contexts(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """Test retrieving all contexts for a user"""
        context1 = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.professional,
            context_name="LinkedIn"
        )
        
        context2 = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.social,
            context_name="Facebook"
        )
        
        contexts = context_service.get_user_contexts(sample_verified_profile.user_id)
        
        assert len(contexts) == 2
        assert contexts[0].context_name in ["LinkedIn", "Facebook"]
        assert contexts[1].context_name in ["LinkedIn", "Facebook"]
    
    def test_update_context_profile(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """Test updating context profile"""
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.professional,
            context_name="Work",
            bio="Old bio"
        )
        
        updated = context_service.update_context_profile(
            context_id=context.id,
            bio="New bio",
            email_override="new@work.com"
        )
        
        assert updated.bio == "New bio"
        assert updated.email_override == "new@work.com"
    
    def test_delete_context_profile(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """Test soft deleting context profile"""
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.social,
            context_name="Facebook"
        )
        
        result = context_service.delete_context_profile(context.id)
        assert result is True
        
        with pytest.raises(ContextServiceError):
            context_service.get_context_profile(context.id)


class TestResolvedProfileOutput:
    """Test ResolvedProfile to_dict conversion"""
    
    def test_resolved_profile_to_dict(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile,
        sample_identity_name: IdentityName
    ):
        """Test converting ResolvedProfile to dictionary"""
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.professional,
            context_name="Work",
            display_name_override="Dr. Sarah Chen",
            email_override="work@example.com"
        )
        
        resolved = context_service.resolve_context_profile(
            user_id=sample_verified_profile.user_id,
            context_id=context.id
        )
        
        data = resolved.to_dict()
        
        assert data["user_id"] == str(sample_verified_profile.user_id)
        assert data["account_type"] == "verified"
        assert data["display_name"] == "Dr. Sarah Chen"
        assert data["email"] == "work@example.com"
        assert data["context_type"] == "professional"
        assert data["context_name"] == "Work"
        assert isinstance(data["identity_names"], list)


class TestNewContextTypes:
    """Test new 'family' and 'custom' context types"""
    
    def test_create_family_context(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """Test creating family context for family sharing use cases"""
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.family,
            context_name="Family Photos",
            display_name_override="Mom",
            bio="Family memories and updates"
        )
        
        assert context.context_type == ContextType.family
        assert context.context_name == "Family Photos"
        assert context.display_name_override == "Mom"
        assert context.bio == "Family memories and updates"
    
    def test_create_custom_context(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """Test creating custom context for flexible use cases"""
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.custom,
            context_name="Freelance Consulting",
            display_name_override="Sarah Chen, Consultant",
            email_override="consulting@example.com",
            bio="Healthcare IT consultant"
        )
        
        assert context.context_type == ContextType.custom
        assert context.context_name == "Freelance Consulting"
        assert context.display_name_override == "Sarah Chen, Consultant"


class TestMultilingualNameResolution:
    """Test multilingual name resolution with fallback chain"""
    
    def test_resolve_exact_language_match(
        self,
        db_session,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """Test resolving name when exact language match available"""
        multilingual_name = IdentityName(
            identity_id=sample_verified_profile.user_id,
            name_type=NameType.full_name,
            name_value={"zh": "李明", "en": "Li Ming"},
            is_primary=True,
            is_deprecated=False,
            visibility_level=VisibilityLevel.public
        )
        db_session.add(multilingual_name)
        db_session.commit()
        
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.professional,
            context_name="Work"
        )
        
        resolved = context_service.resolve_context_profile(
            user_id=sample_verified_profile.user_id,
            context_id=context.id,
            language="zh"
        )
        
        assert len(resolved.identity_names) == 1
        name = resolved.identity_names[0]
        
        resolved_value = context_service._resolve_multilingual_name(
            name, 
            requested_language="zh",
            preferred_language="en"
        )
        assert resolved_value == "李明"
    
    def test_fallback_to_preferred_language(
        self,
        db_session,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """Test fallback to user's preferred language when requested unavailable"""
        multilingual_name = IdentityName(
            identity_id=sample_verified_profile.user_id,
            name_type=NameType.full_name,
            name_value={"zh": "李明", "en": "Li Ming"},
            is_primary=True,
            is_deprecated=False,
            visibility_level=VisibilityLevel.public
        )
        db_session.add(multilingual_name)
        
        sample_verified_profile.preferred_language = "zh"
        db_session.commit()
        
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.social,
            context_name="Social"
        )
        
        resolved = context_service.resolve_context_profile(
            user_id=sample_verified_profile.user_id,
            context_id=context.id,
            language="fr"  # Request French (not available)
        )
        
        name = resolved.identity_names[0]
        resolved_value = context_service._resolve_multilingual_name(
            name,
            requested_language="fr",
            preferred_language="zh"
        )
        assert resolved_value == "李明"
    
    def test_fallback_to_english_default(
        self,
        db_session,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """Test fallback to English when requested and preferred unavailable"""
        multilingual_name = IdentityName(
            identity_id=sample_verified_profile.user_id,
            name_type=NameType.full_name,
            name_value={"en": "Li Ming", "es": "Li Ming"},
            is_primary=True,
            is_deprecated=False,
            visibility_level=VisibilityLevel.public
        )
        db_session.add(multilingual_name)
        
        sample_verified_profile.preferred_language = "de"
        db_session.commit()
        
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.professional,
            context_name="Work"
        )
        
        resolved = context_service.resolve_context_profile(
            user_id=sample_verified_profile.user_id,
            context_id=context.id,
            language="fr"  # Not available
        )
        
        name = resolved.identity_names[0]
        resolved_value = context_service._resolve_multilingual_name(
            name,
            requested_language="fr",  # Not available
            preferred_language="de"   # Not available
        )
        assert resolved_value == "Li Ming"
    
    def test_fallback_to_first_available(
        self,
        db_session,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """Test fallback to first available language when all else fails"""
        multilingual_name = IdentityName(
            identity_id=sample_verified_profile.user_id,
            name_type=NameType.full_name,
            name_value={"zh": "李明", "ja": "リメイ"},  # No English
            is_primary=True,
            is_deprecated=False,
            visibility_level=VisibilityLevel.public
        )
        db_session.add(multilingual_name)
        
        sample_verified_profile.preferred_language = "fr"
        db_session.commit()
        
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.social,
            context_name="Social"
        )
        
        resolved = context_service.resolve_context_profile(
            user_id=sample_verified_profile.user_id,
            context_id=context.id,
            language="de"
        )
        
        name = resolved.identity_names[0]
        resolved_value = context_service._resolve_multilingual_name(
            name,
            requested_language="de",
            preferred_language="fr"
        )
        assert resolved_value == "リメイ"
    
    def test_empty_name_value_returns_empty_string(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """Test graceful handling of empty JSONB name_value"""
        from src.models.profile import IdentityName
        
        empty_name = IdentityName(
            identity_id=sample_verified_profile.user_id,
            name_type=NameType.full_name,
            name_value={},  # Empty JSONB
            is_primary=False,
            is_deprecated=False,
            visibility_level=VisibilityLevel.public
        )
        
        resolved_value = context_service._resolve_multilingual_name(
            empty_name,
            requested_language="en",
            preferred_language="en"
        )
        assert resolved_value == ""


class TestTemporalValidity:
    """Test temporal validity checking for expired contexts"""
    
    def test_resolve_expired_context_raises_410(
        self,
        db_session,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """Test resolving expired context raises HTTP 410 Gone"""
        from datetime import datetime, timezone, timedelta
        from sqlalchemy import text
        
        expired_context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.professional,
            context_name="Old Job"
        )
        
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        db_session.execute(
            text("UPDATE context_profiles SET valid_to = :valid_to WHERE id = :id"),
            {"valid_to": past_date, "id": str(expired_context.id)}
        )
        db_session.commit()
        
        with pytest.raises(ContextServiceError) as exc_info:
            context_service.resolve_context_profile(
                user_id=sample_verified_profile.user_id,
                context_id=expired_context.id
            )
        
        assert exc_info.value.status_code == 410
        assert "expired" in str(exc_info.value).lower()
    
    def test_resolve_valid_context_succeeds(
        self,
        db_session,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """Test resolving context with future valid_to succeeds"""
        from datetime import datetime, timezone, timedelta
        from sqlalchemy import text
        
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.professional,
            context_name="Current Job"
        )
        
        future_date = datetime.now(timezone.utc) + timedelta(days=30)
        db_session.execute(
            text("UPDATE context_profiles SET valid_to = :valid_to WHERE id = :id"),
            {"valid_to": future_date, "id": str(context.id)}
        )
        db_session.commit()
        
        resolved = context_service.resolve_context_profile(
            user_id=sample_verified_profile.user_id,
            context_id=context.id
        )
        
        assert resolved.context_type == ContextType.professional
    
    def test_resolve_context_with_null_valid_to_succeeds(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """Test resolving context with null valid_to (ongoing) succeeds"""
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.social,
            context_name="Social"
        )
        
        resolved = context_service.resolve_context_profile(
            user_id=sample_verified_profile.user_id,
            context_id=context.id
        )
        
        assert resolved.context_type == ContextType.social


class TestExpiryEnrichment:
    """Test read-time enrichment of verification_status when linked document expires."""

    def _make_verified_document(self, db_session, user_id, expiry_date):
        """Helper: create a verified document with the given expiry date."""
        doc = VerificationDocument(
            user_id=user_id,
            document_type=DocumentType.passport,
            verification_status=VerificationStatus.verified,
            original_filename="passport.pdf",
            file_size_bytes=1024,
            content_type="application/pdf",
            storage_path="test/path.enc",
            document_expiry_date=expiry_date,
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        return doc

    def test_get_context_returns_expired_when_document_expired(
        self,
        db_session,
        context_service: ContextService,
        context_repository: ContextRepository,
        sample_verified_profile: BaseProfile,
    ):
        """Context with a linked expired document returns verification_status='expired'."""
        yesterday = date.today() - timedelta(days=1)
        doc = self._make_verified_document(
            db_session, sample_verified_profile.user_id, yesterday
        )

        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.healthcare,
            context_name="Hospital",
        )
        context.verification_status = VerificationStatus.verified
        context.is_active = True
        context.document_id = doc.id
        db_session.commit()

        result = context_service.get_context_profile(context.id)

        assert result.verification_status == VerificationStatus.expired
        assert result.is_active is False

    def test_get_context_returns_verified_when_document_not_expired(
        self,
        db_session,
        context_service: ContextService,
        context_repository: ContextRepository,
        sample_verified_profile: BaseProfile,
    ):
        """Context with a non-expired document retains verification_status='verified'."""
        future = date.today() + timedelta(days=365)
        doc = self._make_verified_document(
            db_session, sample_verified_profile.user_id, future
        )

        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.healthcare,
            context_name="Hospital",
        )
        context.verification_status = VerificationStatus.verified
        context.is_active = True
        context.document_id = doc.id
        db_session.commit()

        result = context_service.get_context_profile(context.id)

        assert result.verification_status == VerificationStatus.verified
        assert result.is_active is True

    def test_get_context_unchanged_when_no_linked_document(
        self,
        db_session,
        context_service: ContextService,
        sample_verified_profile: BaseProfile,
    ):
        """Context with verification_status='verified' and no document stays verified."""
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.professional,
            context_name="Work",
        )
        context.verification_status = VerificationStatus.verified
        context.is_active = True
        db_session.commit()

        result = context_service.get_context_profile(context.id)

        assert result.verification_status == VerificationStatus.verified
        assert result.is_active is True

    def test_get_user_contexts_enriches_expired_documents(
        self,
        db_session,
        context_service: ContextService,
        context_repository: ContextRepository,
        sample_verified_profile: BaseProfile,
    ):
        """get_user_contexts enriches only the context with an expired document."""
        yesterday = date.today() - timedelta(days=1)
        future = date.today() + timedelta(days=365)
        expired_doc = self._make_verified_document(
            db_session, sample_verified_profile.user_id, yesterday
        )
        valid_doc = self._make_verified_document(
            db_session, sample_verified_profile.user_id, future
        )

        ctx_expired = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.healthcare,
            context_name="Expired Hospital",
        )
        ctx_expired.verification_status = VerificationStatus.verified
        ctx_expired.is_active = True
        ctx_expired.document_id = expired_doc.id

        ctx_valid = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.legal,
            context_name="Valid Legal",
        )
        ctx_valid.verification_status = VerificationStatus.verified
        ctx_valid.is_active = True
        ctx_valid.document_id = valid_doc.id

        db_session.commit()

        results = context_service.get_user_contexts(
            sample_verified_profile.user_id, include_inactive=True
        )
        by_name = {c.context_name: c for c in results}

        assert by_name["Expired Hospital"].verification_status == VerificationStatus.expired
        assert by_name["Expired Hospital"].is_active is False
        assert by_name["Valid Legal"].verification_status == VerificationStatus.verified
        assert by_name["Valid Legal"].is_active is True

    def test_enrichment_does_not_modify_database(
        self,
        db_session,
        context_service: ContextService,
        context_repository: ContextRepository,
        sample_verified_profile: BaseProfile,
    ):
        """The read-time enrichment must not persist changes to the database."""
        yesterday = date.today() - timedelta(days=1)
        doc = self._make_verified_document(
            db_session, sample_verified_profile.user_id, yesterday
        )

        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.healthcare,
            context_name="Hospital",
        )
        context.verification_status = VerificationStatus.verified
        context.is_active = True
        context.document_id = doc.id
        db_session.commit()
        context_id = context.id

        enriched = context_service.get_context_profile(context_id)
        assert enriched.verification_status == VerificationStatus.expired

        # Expire and re-query to force a fresh read from the database.
        # set_committed_value modifies the in-memory object without marking it
        # dirty, so we must expire the cached state to verify the DB is unchanged.
        db_session.expire_all()
        db_row = context_repository.get_context_profile_by_id(context_id)
        assert db_row.verification_status == VerificationStatus.verified
        assert db_row.is_active is True





