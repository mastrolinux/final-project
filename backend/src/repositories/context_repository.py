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

from sqlalchemy.orm import joinedload

from src.models.context import ContextProfile, ContextType
from src.models.verification import VerificationStatus


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
        is_active: bool = True,
        verification_status: Optional["VerificationStatus"] = None,
    ) -> ContextProfile:
        """
        Create a new context profile.

        Args:
            user_id: User ID this context belongs to
            context_type: Type of context
            context_name: User-defined context name
            display_name_override: Optional display name override
            email_override: Optional email override
            phone_override: Optional phone override
            bio: Optional context-specific biography
            is_active: Whether context is active (default: True)
            verification_status: Verification state for legal/healthcare contexts

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
            is_active=is_active,
            verification_status=verification_status,
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
        query = self.db.query(ContextProfile).options(
            joinedload(ContextProfile.document)
        ).filter(
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

    def soft_delete_user_contexts(self, user_id: UUID) -> int:
        """
        Soft delete all context profiles for a user.

        Args:
            user_id: User ID

        Returns:
            Number of context profiles soft-deleted
        """
        now = datetime.now(timezone.utc)
        count = self.db.query(ContextProfile).filter(
            ContextProfile.user_id == user_id,
            ContextProfile.deleted_at.is_(None)
        ).update({ContextProfile.deleted_at: now}, synchronize_session=False)
        self.db.commit()
        return count

    def update_verification_status(
        self,
        context_id: UUID,
        verification_status: VerificationStatus,
        is_active: bool,
        rejection_reason: Optional[str] = None,
    ) -> Optional[ContextProfile]:
        """
        Update the verification status and active flag of a context profile.

        Used by the verification service when an admin approves or rejects
        a context verification request.

        Args:
            context_id: Context profile ID
            verification_status: New verification status
            is_active: Whether the context should be active
            rejection_reason: Reason for rejection (set on reject, cleared on approve)

        Returns:
            Updated context profile, or None if not found
        """
        context = self.db.query(ContextProfile).filter(
            ContextProfile.id == context_id
        ).first()

        if not context:
            return None

        context.verification_status = verification_status
        context.is_active = is_active
        context.rejection_reason = rejection_reason
        context.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(context)

        return context

    def get_contexts_pending_verification(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ContextProfile]:
        """
        Return contexts awaiting admin verification that have at least
        one linked document.

        Eagerly loads the base_profile relationship for display_name access.

        Args:
            limit: Maximum results to return
            offset: Results offset for pagination

        Returns:
            List of context profiles pending verification
        """
        return (
            self.db.query(ContextProfile)
            .options(joinedload(ContextProfile.base_profile))
            .filter(
                and_(
                    ContextProfile.verification_status.in_([
                        VerificationStatus.pending,
                        VerificationStatus.under_review,
                    ]),
                    ContextProfile.deleted_at.is_(None),
                    ContextProfile.document_id.isnot(None),
                )
            )
            .order_by(ContextProfile.created_at.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_active_contexts_by_document_id(
        self, document_id: UUID
    ) -> List[ContextProfile]:
        """
        Return all active, non-deleted contexts linked to the given document.

        Used by the expiry task to find contexts that need deactivation
        when their backing verification document expires.

        Args:
            document_id: Verification document ID

        Returns:
            List of active context profiles linked to the document
        """
        return (
            self.db.query(ContextProfile)
            .filter(
                and_(
                    ContextProfile.document_id == str(document_id),
                    ContextProfile.is_active == True,
                    ContextProfile.deleted_at.is_(None),
                )
            )
            .all()
        )

    def restore_user_contexts(self, user_id: UUID) -> int:
        """
        Restore all soft-deleted context profiles for a user.

        Args:
            user_id: User ID

        Returns:
            Number of context profiles restored
        """
        count = self.db.query(ContextProfile).filter(
            ContextProfile.user_id == user_id,
            ContextProfile.deleted_at.isnot(None)
        ).update({ContextProfile.deleted_at: None}, synchronize_session=False)
        self.db.commit()
        return count









