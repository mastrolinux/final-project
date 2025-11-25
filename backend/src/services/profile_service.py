"""
Profile Service

Business logic layer for profile management.
Implements validation rules and account type constraints.
"""

from typing import Optional, List, Tuple
from uuid import UUID

from src.repositories.profile_repository import ProfileRepository
from src.schemas.profile import ProfileCreate, ProfileUpdate, IdentityNameCreate
from src.models.profile import BaseProfile, IdentityName, AccountType


class ProfileServiceError(Exception):
    """Custom exception for profile service errors"""
    pass


class ProfileService:
    """Service layer for profile business logic"""
    
    def __init__(self, repository: ProfileRepository):
        """
        Initialize service with repository
        
        Args:
            repository: ProfileRepository instance
        """
        self.repository = repository
    
    def create_profile(self, profile_data: ProfileCreate) -> BaseProfile:
        """
        Create a new profile with business logic validation
        
        Args:
            profile_data: Profile creation data
            
        Returns:
            Created profile
            
        Raises:
            ProfileServiceError: If validation fails
        """
        # Validate verified accounts have legal_name
        if profile_data.account_type == AccountType.verified and not profile_data.legal_name:
            raise ProfileServiceError(
                "Verified accounts require a legal_name"
            )
        
        # Check for duplicate email
        existing = self.repository.get_profile_by_email(profile_data.primary_email)
        if existing:
            raise ProfileServiceError(
                f"Profile with email {profile_data.primary_email} already exists"
            )
        
        # Create profile
        profile = self.repository.create_profile(
            account_type=profile_data.account_type,
            legal_name=profile_data.legal_name,
            primary_email=profile_data.primary_email,
            primary_phone=profile_data.primary_phone,
            preferred_language=profile_data.preferred_language
        )
        
        return profile
    
    def get_profile(self, user_id: UUID) -> BaseProfile:
        """
        Get profile by ID
        
        Args:
            user_id: User ID
            
        Returns:
            Profile
            
        Raises:
            ProfileServiceError: If profile not found
        """
        profile = self.repository.get_profile_by_id(user_id)
        
        if not profile:
            raise ProfileServiceError(f"Profile {user_id} not found")
        
        return profile
    
    def get_profile_with_names(
        self,
        user_id: UUID,
        include_deprecated: bool = False
    ) -> Tuple[BaseProfile, List[IdentityName]]:
        """
        Get profile with identity names
        
        Args:
            user_id: User ID
            include_deprecated: Whether to include deprecated names
            
        Returns:
            Tuple of (profile, names)
            
        Raises:
            ProfileServiceError: If profile not found
        """
        profile, names = self.repository.get_profile_with_names(
            user_id,
            include_deprecated=include_deprecated
        )
        
        if not profile:
            raise ProfileServiceError(f"Profile {user_id} not found")
        
        return profile, names
    
    def update_profile(
        self,
        user_id: UUID,
        update_data: ProfileUpdate
    ) -> BaseProfile:
        """
        Update profile with business logic validation
        
        Args:
            user_id: User ID
            update_data: Update data
            
        Returns:
            Updated profile
            
        Raises:
            ProfileServiceError: If validation fails
        """
        # Get existing profile
        existing = self.repository.get_profile_by_id(user_id)
        if not existing:
            raise ProfileServiceError(f"Profile {user_id} not found")
        
        # Validate account type transitions
        if update_data.account_type is not None:
            # Check if upgrading to verified
            if update_data.account_type == AccountType.verified:
                # Need legal_name either in update or existing profile
                legal_name = update_data.legal_name or existing.legal_name
                if not legal_name:
                    raise ProfileServiceError(
                        "Cannot upgrade to verified account without legal_name"
                    )
            
            # Prevent downgrading from verified
            if existing.account_type == AccountType.verified:
                if update_data.account_type != AccountType.verified:
                    raise ProfileServiceError(
                        "Cannot downgrade from verified account type"
                    )
        
        # Check for duplicate email if updating email
        if update_data.primary_email:
            if update_data.primary_email != existing.primary_email:
                duplicate = self.repository.get_profile_by_email(update_data.primary_email)
                if duplicate:
                    raise ProfileServiceError(
                        f"Email {update_data.primary_email} already in use"
                    )
        
        # Build update dict
        updates = {}
        for field in ['account_type', 'legal_name', 'primary_email', 'primary_phone', 'preferred_language']:
            value = getattr(update_data, field)
            if value is not None:
                updates[field] = value
        
        # Update profile
        profile = self.repository.update_profile(user_id, **updates)
        
        return profile
    
    def delete_profile(self, user_id: UUID) -> bool:
        """
        Soft delete a profile
        
        Args:
            user_id: User ID
            
        Returns:
            True if deleted
            
        Raises:
            ProfileServiceError: If profile not found
        """
        result = self.repository.soft_delete_profile(user_id)
        
        if not result:
            raise ProfileServiceError(f"Profile {user_id} not found")
        
        return result
    
    def add_identity_name(
        self,
        user_id: UUID,
        name_data: IdentityNameCreate
    ) -> IdentityName:
        """
        Add an identity name to a profile
        
        Args:
            user_id: User ID
            name_data: Identity name data
            
        Returns:
            Created identity name
            
        Raises:
            ProfileServiceError: If profile not found
        """
        # Verify profile exists
        profile = self.repository.get_profile_by_id(user_id)
        if not profile:
            raise ProfileServiceError(f"Profile {user_id} not found")
        
        # Create identity name
        name = self.repository.create_identity_name(
            identity_id=user_id,
            name_type=name_data.name_type,
            name_value=name_data.name_value,
            is_primary=name_data.is_primary,
            is_deprecated=name_data.is_deprecated,
            visibility_level=name_data.visibility_level,
            context_id=name_data.context_id
        )
        
        return name

