"""
Unit Tests for Context Service

Tests the inheritance engine and business logic for context profile management.
Critical test scenarios focus on profile resolution algorithm.
"""

import pytest
from uuid import uuid4

from src.models.context import ContextType
from src.models.profile import BaseProfile, IdentityName, AccountType, NameType, VisibilityLevel
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

        assert "identity-verified" in str(exc_info.value).lower()
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

        assert "identity-verified" in str(exc_info.value).lower()
        assert "healthcare" in str(exc_info.value).lower()

    def test_unverified_cannot_create_legal_context(
        self,
        context_service: ContextService,
        sample_unverified_profile: BaseProfile
    ):
        """Test unverified accounts cannot create legal contexts"""
        with pytest.raises(ContextServiceError) as exc_info:
            context_service.create_context_profile(
                user_id=sample_unverified_profile.user_id,
                context_type=ContextType.legal,
                context_name="Government"
            )

        assert "identity-verified" in str(exc_info.value).lower()
        assert "legal" in str(exc_info.value).lower()

    def test_unverified_cannot_create_healthcare_context(
        self,
        context_service: ContextService,
        sample_unverified_profile: BaseProfile
    ):
        """Test unverified accounts cannot create healthcare contexts"""
        with pytest.raises(ContextServiceError) as exc_info:
            context_service.create_context_profile(
                user_id=sample_unverified_profile.user_id,
                context_type=ContextType.healthcare,
                context_name="Hospital"
            )

        assert "identity-verified" in str(exc_info.value).lower()
        assert "healthcare" in str(exc_info.value).lower()
    
    def test_duplicate_context_fails(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """Test creating duplicate context (user_id, type, name) fails"""
        # Create first context
        context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.professional,
            context_name="LinkedIn"
        )
        
        # Try to create duplicate
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
    """
    CRITICAL TESTS: Profile resolution with inheritance
    
    Tests the core algorithm implementing Goffman's dramaturgical theory.
    """
    
    def test_resolve_context_with_full_overrides(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile,
        sample_identity_name: IdentityName
    ):
        """Test resolving context with all fields overridden"""
        # Create context with full overrides
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.professional,
            context_name="Work",
            display_name_override="Dr. Sarah Chen",
            email_override="work@hospital.org",
            phone_override="+1-555-9999",
            bio="Professional bio"
        )
        
        # Resolve profile
        resolved = context_service.resolve_context_profile(
            user_id=sample_verified_profile.user_id,
            context_id=context.id
        )
        
        # All overrides should be applied
        assert resolved.display_name == "Dr. Sarah Chen"
        assert resolved.email == "work@hospital.org"
        assert resolved.phone == "+1-555-9999"
        assert resolved.bio == "Professional bio"
        
        # Base profile fields should be preserved
        assert resolved.user_id == sample_verified_profile.user_id
        assert resolved.account_type == sample_verified_profile.account_type
        assert resolved.preferred_language == sample_verified_profile.preferred_language
        
        # Context metadata should be included
        assert resolved.context_type == ContextType.professional
        assert resolved.context_name == "Work"
    
    def test_resolve_context_with_partial_overrides(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """
        Test resolving context with partial overrides
        
        CRITICAL: Null overrides should inherit from base profile
        """
        # Create context with only email override
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.professional,
            context_name="Work",
            email_override="work@company.com"
            # display_name_override, phone_override, bio are None
        )
        
        # Resolve profile
        resolved = context_service.resolve_context_profile(
            user_id=sample_verified_profile.user_id,
            context_id=context.id
        )
        
        # Email should be overridden
        assert resolved.email == "work@company.com"
        
        # Phone should inherit from base profile
        assert resolved.phone == sample_verified_profile.primary_phone
        
        # Display name should be None (no override, no base field)
        assert resolved.display_name is None
        
        # Bio should be None (no override)
        assert resolved.bio is None
    
    def test_resolve_context_with_no_overrides(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """
        Test resolving context with no overrides
        
        Should return base profile values for all fields
        """
        # Create context with no overrides
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.social,
            context_name="Personal"
        )
        
        # Resolve profile
        resolved = context_service.resolve_context_profile(
            user_id=sample_verified_profile.user_id,
            context_id=context.id
        )
        
        # All values should inherit from base profile
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
        # Set a base profile avatar
        sample_verified_profile.avatar_url = "https://storage.example.com/avatar.webp"
        sample_verified_profile.avatar_thumbnail_url = "https://storage.example.com/thumb.webp"
        db_session.commit()

        # Create context with NO avatar override
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.social,
            context_name="Social"
        )

        resolved = context_service.resolve_context_profile(
            user_id=sample_verified_profile.user_id,
            context_id=context.id
        )

        # Avatar must NOT be inherited from base profile
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
        # Set a base profile avatar
        sample_verified_profile.avatar_url = "https://storage.example.com/base.webp"
        sample_verified_profile.avatar_thumbnail_url = "https://storage.example.com/base-thumb.webp"
        db_session.commit()

        # Create context and set an avatar override directly
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
        
        # Should return base profile values
        assert resolved.user_id == sample_verified_profile.user_id
        assert resolved.email == sample_verified_profile.primary_email
        assert resolved.phone == sample_verified_profile.primary_phone
        assert resolved.preferred_language == sample_verified_profile.preferred_language
        
        # No context-specific fields
        assert resolved.context_type is None
        assert resolved.context_name is None
        assert resolved.display_name is None
        assert resolved.bio is None
        
        # Identity names should be included
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
        
        # Identity names should be included
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
        # Add deprecated name
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
        
        # Resolve without deprecated names
        resolved = context_service.resolve_context_profile(
            user_id=sample_verified_profile.user_id,
            context_id=context.id,
            include_deprecated_names=False
        )
        
        # Should only have non-deprecated name
        assert len(resolved.identity_names) == 1
        assert resolved.identity_names[0].is_deprecated is False
        
        # Resolve with deprecated names
        resolved_with_deprecated = context_service.resolve_context_profile(
            user_id=sample_verified_profile.user_id,
            context_id=context.id,
            include_deprecated_names=True
        )
        
        # Should have both names
        assert len(resolved_with_deprecated.identity_names) == 2
    
    def test_resolve_context_not_belonging_to_user_fails(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile,
        sample_unverified_profile: BaseProfile
    ):
        """Test resolving context that doesn't belong to user fails"""
        # Create context for user 1
        context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.professional,
            context_name="Work"
        )
        
        # Try to resolve for user 2
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
        # Create multiple contexts
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
        
        # Retrieve contexts
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
        
        # Update context
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
        
        # Delete context
        result = context_service.delete_context_profile(context.id)
        assert result is True
        
        # Context should no longer be retrievable
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
        
        # Convert to dict
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
        # Create multilingual name: Chinese and English
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
        
        # Resolve with Chinese language
        resolved = context_service.resolve_context_profile(
            user_id=sample_verified_profile.user_id,
            context_id=context.id,
            language="zh"
        )
        
        # Verify Chinese name is resolved (test internal method works)
        assert len(resolved.identity_names) == 1
        name = resolved.identity_names[0]
        
        # Test the multilingual resolution method directly
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
        # Create name with Chinese and English, no French
        multilingual_name = IdentityName(
            identity_id=sample_verified_profile.user_id,
            name_type=NameType.full_name,
            name_value={"zh": "李明", "en": "Li Ming"},
            is_primary=True,
            is_deprecated=False,
            visibility_level=VisibilityLevel.public
        )
        db_session.add(multilingual_name)
        
        # Set user's preferred language to Chinese
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
        
        # Test fallback to preferred language (zh)
        name = resolved.identity_names[0]
        resolved_value = context_service._resolve_multilingual_name(
            name,
            requested_language="fr",
            preferred_language="zh"
        )
        assert resolved_value == "李明"  # Falls back to preferred language
    
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
        
        # Preferred language not in name_value
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
        
        # Test fallback to English default
        name = resolved.identity_names[0]
        resolved_value = context_service._resolve_multilingual_name(
            name,
            requested_language="fr",  # Not available
            preferred_language="de"   # Not available
        )
        assert resolved_value == "Li Ming"  # Falls back to English
    
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
        
        # Test fallback to first available (alphabetically: 'ja' before 'zh')
        name = resolved.identity_names[0]
        resolved_value = context_service._resolve_multilingual_name(
            name,
            requested_language="de",
            preferred_language="fr"
        )
        assert resolved_value == "リメイ"  # First alphabetically (ja)
    
    def test_empty_name_value_returns_empty_string(
        self,
        context_service: ContextService,
        sample_verified_profile: BaseProfile
    ):
        """Test graceful handling of empty JSONB name_value"""
        from src.models.profile import IdentityName
        
        # Create name with empty JSONB
        empty_name = IdentityName(
            identity_id=sample_verified_profile.user_id,
            name_type=NameType.full_name,
            name_value={},  # Empty JSONB
            is_primary=False,
            is_deprecated=False,
            visibility_level=VisibilityLevel.public
        )
        
        # Test method handles empty dict gracefully
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
        
        # Create context that expired yesterday
        expired_context = context_service.create_context_profile(
            user_id=sample_verified_profile.user_id,
            context_type=ContextType.professional,
            context_name="Old Job"
        )
        
        # Manually set valid_to to past date (timezone-aware)
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        db_session.execute(
            text("UPDATE context_profiles SET valid_to = :valid_to WHERE id = :id"),
            {"valid_to": past_date, "id": str(expired_context.id)}
        )
        db_session.commit()
        
        # Attempt to resolve expired context
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
        
        # Set valid_to to future date (timezone-aware)
        future_date = datetime.now(timezone.utc) + timedelta(days=30)
        db_session.execute(
            text("UPDATE context_profiles SET valid_to = :valid_to WHERE id = :id"),
            {"valid_to": future_date, "id": str(context.id)}
        )
        db_session.commit()
        
        # Should resolve successfully
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
        
        # valid_to is None by default (ongoing)
        resolved = context_service.resolve_context_profile(
            user_id=sample_verified_profile.user_id,
            context_id=context.id
        )
        
        assert resolved.context_type == ContextType.social









