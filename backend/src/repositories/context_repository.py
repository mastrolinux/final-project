"""
Context Repository

Data access layer for ContextProfile entities.
Handles all database operations for context profile management.
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.models.context import ContextProfile, ContextType


class ContextRepository:
    """Repository for ContextProfile database operations"""
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create_context_profile(
        self,
        user_id: UUID,
        context_type: ContextType,
        context_name: str,
        display_name_override: Optional[str] = None,
        email_override: Optional[str] = None,
        phone_override: Optional[str] = None,
        bio: Optional[str] = None,
        is_active: bool = True
    ) -> ContextProfile:
        """
        Create a new context profile
        
        Args:
            user_id: User ID this context belongs to
            context_type: Type of context (professional, social, legal, healthcare)
            context_name: User-defined context name
            display_name_override: Optional display name override
            email_override: Optional email override
            phone_override: Optional phone override
            bio: Optional context-specific biography
            is_active: Whether context is active (default: True)
            
        Returns:
            Created context profile instance
        """
        context = ContextProfile(
            user_id=user_id,
            context_type=context_type,
            context_name=context_name,
            display_name_override=display_name_override,
            email_override=email_override,
            phone_override=phone_override,
            bio=bio,
            is_active=is_active
        )
        
        self.db.add(context)
        self.db.commit()
        self.db.refresh(context)
        
        return context
    
    def get_context_profile_by_id(self, context_id: UUID) -> Optional[ContextProfile]:
        """
        Get context profile by ID, excluding soft-deleted contexts
        
        Args:
            context_id: Context profile ID to look up
            
        Returns:
            Context profile if found and not deleted, None otherwise
        """
        return self.db.query(ContextProfile).filter(
            and_(
                ContextProfile.id == context_id,
                ContextProfile.deleted_at.is_(None)
            )
        ).first()
    
    def get_user_context_profiles(
        self,
        user_id: UUID,
        include_inactive: bool = False
    ) -> List[ContextProfile]:
        """
        Get all context profiles for a user
        
        Args:
            user_id: User ID to get contexts for
            include_inactive: Whether to include inactive contexts
            
        Returns:
            List of context profiles
        """
        query = self.db.query(ContextProfile).filter(
            and_(
                ContextProfile.user_id == user_id,
                ContextProfile.deleted_at.is_(None)
            )
        )
        
        if not include_inactive:
            query = query.filter(ContextProfile.is_active == True)
        
        return query.order_by(ContextProfile.created_at.asc()).all()
    
    def get_context_by_type_and_name(
        self,
        user_id: UUID,
        context_type: ContextType,
        context_name: str
    ) -> Optional[ContextProfile]:
        """
        Get context profile by user, type, and name
        
        Args:
            user_id: User ID
            context_type: Context type
            context_name: Context name
            
        Returns:
            Context profile if found and not deleted, None otherwise
        """
        return self.db.query(ContextProfile).filter(
            and_(
                ContextProfile.user_id == user_id,
                ContextProfile.context_type == context_type,
                ContextProfile.context_name == context_name,
                ContextProfile.deleted_at.is_(None)
            )
        ).first()
    
    def update_context_profile(
        self,
        context_id: UUID,
        **updates
    ) -> Optional[ContextProfile]:
        """
        Update context profile fields
        
        Args:
            context_id: Context profile ID to update
            **updates: Fields to update
            
        Returns:
            Updated context profile if found, None otherwise
        """
        context = self.get_context_profile_by_id(context_id)
        
        if not context:
            return None
        
        # Update provided fields
        for key, value in updates.items():
            if hasattr(context, key):
                setattr(context, key, value)
        
        # Update timestamp
        context.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(context)
        
        return context
    
    def soft_delete_context_profile(self, context_id: UUID) -> bool:
        """
        Soft delete a context profile by setting deleted_at timestamp
        
        Args:
            context_id: Context profile ID to delete
            
        Returns:
            True if context was deleted, False if not found
        """
        context = self.db.query(ContextProfile).filter(
            ContextProfile.id == context_id
        ).first()
        
        if not context or context.deleted_at is not None:
            return False
        
        context.deleted_at = datetime.now(timezone.utc)
        
        self.db.commit()
        
        return True
    
    def count_user_contexts(self, user_id: UUID, active_only: bool = True) -> int:
        """
        Count number of context profiles for a user
        
        Args:
            user_id: User ID
            active_only: Whether to count only active contexts
            
        Returns:
            Number of context profiles
        """
        query = self.db.query(ContextProfile).filter(
            and_(
                ContextProfile.user_id == user_id,
                ContextProfile.deleted_at.is_(None)
            )
        )
        
        if active_only:
            query = query.filter(ContextProfile.is_active == True)
        
        return query.count()







