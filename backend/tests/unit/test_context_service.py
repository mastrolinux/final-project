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
        
        assert "cannot create" in str(exc_info.value).lower()
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
        
        assert "cannot create" in str(exc_info.value).lower()
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







