"""
Profile Repository

Data access layer for Profile and IdentityName entities.
Handles all database operations for profile management.
"""

from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.models.profile import BaseProfile, IdentityName, AccountType, NameType, VisibilityLevel


class ProfileRepository:
    """Repository for Profile and IdentityName database operations"""
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    # Profile CRUD operations
    
    def create_profile(
        self,
        account_type: AccountType,
        primary_email: str,
        preferred_language: str,
        legal_name: Optional[str] = None,
        primary_phone: Optional[str] = None,
    ) -> BaseProfile:
        """
        Create a new profile
        
        Args:
            account_type: Type of account (verified, unverified, pseudonymous)
            primary_email: Primary email address
            preferred_language: Preferred language code
            legal_name: Optional legal name
            primary_phone: Optional primary phone number
            
        Returns:
            Created profile instance
        """
        profile = BaseProfile(
            account_type=account_type,
            legal_name=legal_name,
            primary_email=primary_email,
            primary_phone=primary_phone,
            preferred_language=preferred_language
        )
        
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        
        return profile
    
    def get_profile_by_id(self, user_id: UUID) -> Optional[BaseProfile]:
        """
        Get profile by user ID, excluding soft-deleted profiles
        
        Args:
            user_id: User ID to look up
            
        Returns:
            Profile if found and not deleted, None otherwise
        """
        return self.db.query(BaseProfile).filter(
            and_(
                BaseProfile.user_id == user_id,
                BaseProfile.deleted_at.is_(None)
            )
        ).first()

    def get_profile_by_id_including_deleted(self, user_id: UUID) -> Optional[BaseProfile]:
        """
        Get profile by user ID, including soft-deleted profiles.
        
        Args:
            user_id: User ID to look up
            
        Returns:
            Profile if found, None otherwise
        """
        return self.db.query(BaseProfile).filter(
            BaseProfile.user_id == user_id
        ).first()
    
    def get_profile_by_email(self, email: str) -> Optional[BaseProfile]:
        """
        Get profile by email address, excluding soft-deleted profiles
        
        Args:
            email: Email address to look up
            
        Returns:
            Profile if found and not deleted, None otherwise
        """
        return self.db.query(BaseProfile).filter(
            and_(
                BaseProfile.primary_email == email,
                BaseProfile.deleted_at.is_(None)
            )
        ).first()
    
    def list_profiles(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[BaseProfile]:
        """
        List all profiles, excluding soft-deleted ones
        
        Args:
            limit: Maximum number of profiles to return
            offset: Number of profiles to skip
            
        Returns:
            List of profiles
        """
        query = self.db.query(BaseProfile).filter(
            BaseProfile.deleted_at.is_(None)
        ).order_by(BaseProfile.created_at.desc())
        
        if offset is not None:
            query = query.offset(offset)
        
        if limit is not None:
            query = query.limit(limit)
        
        return query.all()
    
    def update_profile(
        self,
        user_id: UUID,
        **updates
    ) -> Optional[BaseProfile]:
        """
        Update profile fields
        
        Args:
            user_id: User ID of profile to update
            **updates: Fields to update
            
        Returns:
            Updated profile if found, None otherwise
        """
        profile = self.get_profile_by_id(user_id)
        
        if not profile:
            return None
        
        # Update provided fields
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        # Update timestamp
        profile.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(profile)
        
        return profile
    
    def soft_delete_profile(self, user_id: UUID) -> bool:
        """
        Soft delete a profile by setting deleted_at timestamp
        
        Args:
            user_id: User ID of profile to delete
            
        Returns:
            True if profile was deleted, False if not found
        """
        # Query without the deleted_at filter to find even non-deleted
        profile = self.db.query(BaseProfile).filter(
            BaseProfile.user_id == user_id
        ).first()
        
        if not profile or profile.deleted_at is not None:
            return False
        
        profile.deleted_at = datetime.now(timezone.utc)
        
        self.db.commit()
        
        return True
    
    # IdentityName CRUD operations
    
    def create_identity_name(
        self,
        identity_id: UUID,
        name_type: NameType,
        name_value: dict,
        is_primary: bool = False,
        is_deprecated: bool = False,
        visibility_level: VisibilityLevel = VisibilityLevel.public,
        context_id: Optional[UUID] = None
    ) -> IdentityName:
        """
        Create a new identity name
        
        Args:
            identity_id: Profile user ID this name belongs to
            name_type: Type of name (given, family, full_name, etc.)
            name_value: Multilingual name dictionary
            is_primary: Whether this is the primary name of this type
            is_deprecated: Whether this name is deprecated
            visibility_level: Visibility level
            context_id: Optional context ID
            
        Returns:
            Created identity name instance
        """
        name = IdentityName(
            identity_id=identity_id,
            name_type=name_type,
            name_value=name_value,
            is_primary=is_primary,
            is_deprecated=is_deprecated,
            visibility_level=visibility_level,
            context_id=context_id
        )
        
        self.db.add(name)
        self.db.commit()
        self.db.refresh(name)
        
        return name
    
    def get_identity_name_by_id(self, name_id: UUID) -> Optional[IdentityName]:
        """
        Get identity name by ID
        
        Args:
            name_id: Identity name ID
            
        Returns:
            Identity name if found, None otherwise
        """
        return self.db.query(IdentityName).filter(
            IdentityName.id == name_id
        ).first()
    
    def get_identity_names(
        self,
        identity_id: UUID,
        include_deprecated: bool = False
    ) -> List[IdentityName]:
        """
        Get all identity names for a profile
        
        Args:
            identity_id: Profile user ID
            include_deprecated: Whether to include deprecated names
            
        Returns:
            List of identity names
        """
        query = self.db.query(IdentityName).filter(
            IdentityName.identity_id == identity_id
        )
        
        if not include_deprecated:
            query = query.filter(IdentityName.is_deprecated == False)
        
        return query.order_by(
            IdentityName.is_primary.desc(),
            IdentityName.created_at.asc()
        ).all()
    
    def update_identity_name(
        self,
        name_id: UUID,
        **updates
    ) -> Optional[IdentityName]:
        """
        Update identity name fields
        
        Args:
            name_id: Identity name ID
            **updates: Fields to update
            
        Returns:
            Updated identity name if found, None otherwise
        """
        name = self.get_identity_name_by_id(name_id)
        
        if not name:
            return None
        
        # Update provided fields
        for key, value in updates.items():
            if hasattr(name, key):
                setattr(name, key, value)
        
        # Update timestamp
        name.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(name)
        
        return name
    
    def delete_identity_name(self, name_id: UUID) -> bool:
        """
        Delete an identity name (hard delete)
        
        Args:
            name_id: Identity name ID
            
        Returns:
            True if name was deleted, False if not found
        """
        name = self.get_identity_name_by_id(name_id)
        
        if not name:
            return False
        
        self.db.delete(name)
        self.db.commit()
        
        return True
    
    # Combined operations
    
    def get_profile_with_names(
        self,
        user_id: UUID,
        include_deprecated: bool = False
    ) -> Tuple[Optional[BaseProfile], List[IdentityName]]:
        """
        Get profile with all associated identity names
        
        Args:
            user_id: User ID of profile
            include_deprecated: Whether to include deprecated names
            
        Returns:
            Tuple of (profile, list of identity names)
            Returns (None, []) if profile not found
        """
        profile = self.get_profile_by_id(user_id)
        
        if not profile:
            return None, []
        
        names = self.get_identity_names(user_id, include_deprecated=include_deprecated)

        return profile, names

    def restore_profile(self, user_id: UUID) -> bool:
        """
        Restore a soft-deleted profile by clearing deleted_at.

        Args:
            user_id: User ID of profile to restore

        Returns:
            True if profile was restored, False if not found
        """
        profile = self.db.query(BaseProfile).filter(
            BaseProfile.user_id == user_id
        ).first()
        if not profile or profile.deleted_at is None:
            return False
        profile.deleted_at = None
        self.db.commit()
        return True

    def hard_delete_profile(self, user_id: UUID) -> bool:
        """
        Permanently delete a profile. CASCADE handles identity_names.

        Args:
            user_id: User ID of profile to delete

        Returns:
            True if deleted, False if not found
        """
        profile = self.db.query(BaseProfile).filter(
            BaseProfile.user_id == user_id
        ).first()
        if not profile:
            return False
        self.db.delete(profile)
        self.db.commit()
        return True

