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
        """Create a new base profile."""
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
        """Get profile by user ID, excluding soft-deleted."""
        return self.db.query(BaseProfile).filter(
            and_(
                BaseProfile.user_id == user_id,
                BaseProfile.deleted_at.is_(None)
            )
        ).first()

    def get_profile_by_id_including_deleted(self, user_id: UUID) -> Optional[BaseProfile]:
        """Get profile by user ID, including soft-deleted."""
        return self.db.query(BaseProfile).filter(
            BaseProfile.user_id == user_id
        ).first()
    
    def get_profile_by_email(self, email: str) -> Optional[BaseProfile]:
        """Get profile by email address, excluding soft-deleted."""
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
        """List all profiles with pagination, excluding soft-deleted."""
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
        """Update profile fields."""
        profile = self.get_profile_by_id(user_id)
        
        if not profile:
            return None

        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        profile.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(profile)
        
        return profile
    
    def soft_delete_profile(self, user_id: UUID) -> bool:
        """Soft delete a profile by setting deleted_at timestamp."""
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
        """Create a new identity name."""
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
        """Get identity name by ID."""
        return self.db.query(IdentityName).filter(
            IdentityName.id == name_id
        ).first()
    
    def get_identity_names(
        self,
        identity_id: UUID,
        include_deprecated: bool = False
    ) -> List[IdentityName]:
        """Get all identity names for a profile."""
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
        """Update identity name fields."""
        name = self.get_identity_name_by_id(name_id)
        
        if not name:
            return None

        for key, value in updates.items():
            if hasattr(name, key):
                setattr(name, key, value)

        name.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(name)
        
        return name
    
    def delete_identity_name(self, name_id: UUID) -> bool:
        """Delete an identity name (hard delete)."""
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
        """Get profile with all associated identity names.

        Returns (None, []) if profile not found.
        """
        profile = self.get_profile_by_id(user_id)
        
        if not profile:
            return None, []
        
        names = self.get_identity_names(user_id, include_deprecated=include_deprecated)

        return profile, names

    def restore_profile(self, user_id: UUID) -> bool:
        """Restore a soft-deleted profile by clearing deleted_at."""
        profile = self.db.query(BaseProfile).filter(
            BaseProfile.user_id == user_id
        ).first()
        if not profile or profile.deleted_at is None:
            return False
        profile.deleted_at = None
        self.db.commit()
        return True

    def hard_delete_profile(self, user_id: UUID) -> bool:
        """Permanently delete a profile. CASCADE handles identity_names."""
        profile = self.db.query(BaseProfile).filter(
            BaseProfile.user_id == user_id
        ).first()
        if not profile:
            return False
        self.db.delete(profile)
        self.db.commit()
        return True

