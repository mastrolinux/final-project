"""
Context Service

Business logic layer for context profile management.
Implements the inheritance engine for profile resolution.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID

from src.repositories.context_repository import ContextRepository
from src.repositories.profile_repository import ProfileRepository
from src.models.context import ContextProfile, ContextType
from src.models.profile import BaseProfile, IdentityName, AccountType


class ContextServiceError(Exception):
    """Custom exception for context service errors"""
    pass


class ResolvedProfile:
    """
    Resolved profile after applying context inheritance.
    
    This is the unified view combining base profile + context overrides.
    Returned to third-party applications via OAuth.
    """
    
    def __init__(
        self,
        user_id: UUID,
        account_type: AccountType,
        display_name: Optional[str],
        email: str,
        phone: Optional[str],
        preferred_language: str,
        bio: Optional[str],
        context_type: Optional[ContextType] = None,
        context_name: Optional[str] = None,
        identity_names: Optional[List[IdentityName]] = None
    ):
        self.user_id = user_id
        self.account_type = account_type
        self.display_name = display_name
        self.email = email
        self.phone = phone
        self.preferred_language = preferred_language
        self.bio = bio
        self.context_type = context_type
        self.context_name = context_name
        self.identity_names = identity_names or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert resolved profile to dictionary for API responses"""
        return {
            "user_id": str(self.user_id),
            "account_type": self.account_type.value,
            "display_name": self.display_name,
            "email": self.email,
            "phone": self.phone,
            "preferred_language": self.preferred_language,
            "bio": self.bio,
            "context_type": self.context_type.value if self.context_type else None,
            "context_name": self.context_name,
            "identity_names": [
                {
                    "name_type": name.name_type.value,
                    "name_value": name.name_value,
                    "is_primary": name.is_primary
                }
                for name in self.identity_names
            ]
        }


class ContextService:
    """Service layer for context profile business logic"""
    
    def __init__(
        self,
        context_repository: ContextRepository,
        profile_repository: ProfileRepository
    ):
        """
        Initialize service with repositories
        
        Args:
            context_repository: ContextRepository instance
            profile_repository: ProfileRepository instance
        """
        self.context_repo = context_repository
        self.profile_repo = profile_repository
    
    def create_context_profile(
        self,
        user_id: UUID,
        context_type: ContextType,
        context_name: str,
        display_name_override: Optional[str] = None,
        email_override: Optional[str] = None,
        phone_override: Optional[str] = None,
        bio: Optional[str] = None
    ) -> ContextProfile:
        """
        Create a new context profile with business logic validation
        
        Args:
            user_id: User ID this context belongs to
            context_type: Type of context
            context_name: User-defined context name
            display_name_override: Optional display name override
            email_override: Optional email override
            phone_override: Optional phone override
            bio: Optional context-specific biography
            
        Returns:
            Created context profile
            
        Raises:
            ContextServiceError: If validation fails
        """
        # Verify base profile exists
        base_profile = self.profile_repo.get_profile_by_id(user_id)
        if not base_profile:
            raise ContextServiceError(f"Profile {user_id} not found")
        
        # Business rule: Pseudonymous accounts cannot create legal or healthcare contexts
        if base_profile.account_type == AccountType.pseudonymous:
            if context_type in [ContextType.legal, ContextType.healthcare]:
                raise ContextServiceError(
                    f"Pseudonymous accounts cannot create {context_type.value} contexts"
                )
        
        # Check for duplicate context (user_id, context_type, context_name)
        existing = self.context_repo.get_context_by_type_and_name(
            user_id, context_type, context_name
        )
        if existing:
            raise ContextServiceError(
                f"Context '{context_name}' of type {context_type.value} already exists for this user"
            )
        
        # Validate email override format if provided
        if email_override:
            # Basic email validation (in production, use email validator library)
            if "@" not in email_override or "." not in email_override:
                raise ContextServiceError("Invalid email override format")
        
        # Create context profile
        context = self.context_repo.create_context_profile(
            user_id=user_id,
            context_type=context_type,
            context_name=context_name,
            display_name_override=display_name_override,
            email_override=email_override,
            phone_override=phone_override,
            bio=bio
        )
        
        return context
    
    def get_context_profile(self, context_id: UUID) -> ContextProfile:
        """
        Get context profile by ID
        
        Args:
            context_id: Context profile ID
            
        Returns:
            Context profile
            
        Raises:
            ContextServiceError: If context not found
        """
        context = self.context_repo.get_context_profile_by_id(context_id)
        
        if not context:
            raise ContextServiceError(f"Context profile {context_id} not found")
        
        return context
    
    def get_user_contexts(
        self,
        user_id: UUID,
        include_inactive: bool = False
    ) -> List[ContextProfile]:
        """
        Get all context profiles for a user
        
        Args:
            user_id: User ID
            include_inactive: Whether to include inactive contexts
            
        Returns:
            List of context profiles
        """
        return self.context_repo.get_user_context_profiles(
            user_id,
            include_inactive=include_inactive
        )
    
    def update_context_profile(
        self,
        context_id: UUID,
        display_name_override: Optional[str] = None,
        email_override: Optional[str] = None,
        phone_override: Optional[str] = None,
        bio: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> ContextProfile:
        """
        Update context profile with validation
        
        Args:
            context_id: Context profile ID
            display_name_override: Optional display name override
            email_override: Optional email override
            phone_override: Optional phone override
            bio: Optional biography
            is_active: Optional active status
            
        Returns:
            Updated context profile
            
        Raises:
            ContextServiceError: If validation fails
        """
        # Get existing context
        context = self.context_repo.get_context_profile_by_id(context_id)
        if not context:
            raise ContextServiceError(f"Context profile {context_id} not found")
        
        # Validate email override format if provided
        if email_override is not None:
            if "@" not in email_override or "." not in email_override:
                raise ContextServiceError("Invalid email override format")
        
        # Build update dict
        updates = {}
        if display_name_override is not None:
            updates['display_name_override'] = display_name_override
        if email_override is not None:
            updates['email_override'] = email_override
        if phone_override is not None:
            updates['phone_override'] = phone_override
        if bio is not None:
            updates['bio'] = bio
        if is_active is not None:
            updates['is_active'] = is_active
        
        # Update context
        updated_context = self.context_repo.update_context_profile(context_id, **updates)
        
        return updated_context
    
    def delete_context_profile(self, context_id: UUID) -> bool:
        """
        Soft delete a context profile
        
        Args:
            context_id: Context profile ID
            
        Returns:
            True if deleted
            
        Raises:
            ContextServiceError: If context not found
        """
        result = self.context_repo.soft_delete_context_profile(context_id)
        
        if not result:
            raise ContextServiceError(f"Context profile {context_id} not found")
        
        return result
    
    def resolve_context_profile(
        self,
        user_id: UUID,
        context_id: UUID,
        language: str = "en",
        include_deprecated_names: bool = False
    ) -> ResolvedProfile:
        """
        CRITICAL ALGORITHM: Profile resolution with inheritance
        
        Merges base profile + context overrides to create unified view.
        This implements Goffman's dramaturgical theory: context-dependent identity presentation.
        
        Resolution order:
        1. Start with base profile fields
        2. Apply context overrides (if not None)
        3. Resolve multilingual names via language preference
        4. Filter deprecated names (unless explicitly included)
        5. Return unified ResolvedProfile view
        
        Args:
            user_id: User ID
            context_id: Context profile ID
            language: Language code for name resolution (default: "en")
            include_deprecated_names: Whether to include deprecated names
            
        Returns:
            ResolvedProfile with merged base + context data
            
        Raises:
            ContextServiceError: If profile or context not found
        """
        # Get base profile
        base_profile = self.profile_repo.get_profile_by_id(user_id)
        if not base_profile:
            raise ContextServiceError(f"Profile {user_id} not found")
        
        # Get context profile
        context = self.context_repo.get_context_profile_by_id(context_id)
        if not context:
            raise ContextServiceError(f"Context profile {context_id} not found")
        
        # Verify context belongs to user
        if context.user_id != user_id:
            raise ContextServiceError(
                f"Context {context_id} does not belong to user {user_id}"
            )
        
        # Get identity names
        _, identity_names = self.profile_repo.get_profile_with_names(
            user_id,
            include_deprecated=include_deprecated_names
        )
        
        # INHERITANCE ENGINE: Merge base + overrides
        # Start with base profile values
        resolved_display_name = None
        resolved_email = base_profile.primary_email
        resolved_phone = base_profile.primary_phone
        resolved_bio = None
        
        # Apply context overrides (null means inherit from base)
        if context.display_name_override is not None:
            resolved_display_name = context.display_name_override
        
        if context.email_override is not None:
            resolved_email = context.email_override
        
        if context.phone_override is not None:
            resolved_phone = context.phone_override
        
        if context.bio is not None:
            resolved_bio = context.bio
        
        # Create resolved profile
        resolved = ResolvedProfile(
            user_id=user_id,
            account_type=base_profile.account_type,
            display_name=resolved_display_name,
            email=resolved_email,
            phone=resolved_phone,
            preferred_language=base_profile.preferred_language,
            bio=resolved_bio,
            context_type=context.context_type,
            context_name=context.context_name,
            identity_names=identity_names
        )
        
        return resolved
    
    def resolve_base_profile(
        self,
        user_id: UUID,
        language: str = "en",
        include_deprecated_names: bool = False
    ) -> ResolvedProfile:
        """
        Resolve base profile without context overrides
        
        Useful for displaying user's default identity presentation.
        
        Args:
            user_id: User ID
            language: Language code for name resolution
            include_deprecated_names: Whether to include deprecated names
            
        Returns:
            ResolvedProfile with base profile data only
            
        Raises:
            ContextServiceError: If profile not found
        """
        # Get base profile
        base_profile = self.profile_repo.get_profile_by_id(user_id)
        if not base_profile:
            raise ContextServiceError(f"Profile {user_id} not found")
        
        # Get identity names
        _, identity_names = self.profile_repo.get_profile_with_names(
            user_id,
            include_deprecated=include_deprecated_names
        )
        
        # Create resolved profile without context
        resolved = ResolvedProfile(
            user_id=user_id,
            account_type=base_profile.account_type,
            display_name=None,  # No override
            email=base_profile.primary_email,
            phone=base_profile.primary_phone,
            preferred_language=base_profile.preferred_language,
            bio=None,  # No context-specific bio
            context_type=None,
            context_name=None,
            identity_names=identity_names
        )
        
        return resolved







