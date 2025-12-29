"""
Context Profile Models

SQLAlchemy models for context-dependent identity profiles.
Implements multi-context identity presentation based on Goffman's dramaturgical theory.
"""

from datetime import datetime, timezone
from typing import Any, Optional
import uuid as uuid_pkg
import enum
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, 
    Enum as SQLEnum, Text
)
from sqlalchemy.orm import relationship

from src.core.database import Base
from src.models.profile import UUID, TimestampMixin, SoftDeleteMixin, TemporalMixin


class ContextType(str, enum.Enum):
    """Context type enumeration for different social contexts"""
    professional = "professional"
    social = "social"
    legal = "legal"
    healthcare = "healthcare"


class ContextProfile(Base, TimestampMixin, SoftDeleteMixin, TemporalMixin):
    """
    Context Profile Model
    
    Enables users to present different identity aspects in different social contexts.
    Implements Goffman's dramaturgical theory: identity as performative and context-dependent.
    
    Design Pattern: Stores only overrides, not full profiles.
    Base profile remains single source of truth.
    Resolution merges base profile + context overrides.
    
    Example Use Cases:
    - Professional: Work-appropriate name and credentials for LinkedIn
    - Social: Preferred name and casual bio for social apps
    - Legal: Official name and credentials for government services
    - Healthcare: Medical information for health apps
    """
    __tablename__ = "context_profiles"

    id = Column(
        UUID(),
        primary_key=True,
        default=uuid_pkg.uuid4
    )
    
    user_id = Column(
        UUID(),
        ForeignKey("base_profiles.user_id", ondelete="CASCADE"),
        nullable=False
    )
    
    context_type = Column(
        SQLEnum(ContextType, name="context_type"),
        nullable=False
    )
    
    context_name = Column(
        Text,
        nullable=False
    )
    
    # Override fields - nullable (null means inherit from base profile)
    display_name_override = Column(Text, nullable=True)
    email_override = Column(String(255), nullable=True)
    phone_override = Column(String(50), nullable=True)
    bio = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Relationships
    base_profile = relationship(
        "BaseProfile",
        foreign_keys=[user_id],
        backref="context_profiles"
    )

    def __repr__(self) -> str:
        return f"<ContextProfile(id={self.id}, user_id={self.user_id}, type={self.context_type}, name={self.context_name})>"
    
    def has_overrides(self) -> bool:
        """Check if this context has any field overrides"""
        return any([
            self.display_name_override is not None,
            self.email_override is not None,
            self.phone_override is not None,
            self.bio is not None
        ])
    
    def get_override_fields(self) -> dict[str, Any]:
        """
        Get dictionary of fields that are overridden in this context
        
        Returns:
            Dict mapping field names to override values (excludes None values)
        """
        overrides = {}
        
        if self.display_name_override is not None:
            overrides['display_name'] = self.display_name_override
        if self.email_override is not None:
            overrides['email'] = self.email_override
        if self.phone_override is not None:
            overrides['phone'] = self.phone_override
        if self.bio is not None:
            overrides['bio'] = self.bio
            
        return overrides





