"""
Models Package

SQLAlchemy models for the Identity and Profile Management API.
Defines database entities and their relationships.
"""

from src.models.profile import BaseProfile, IdentityName

__all__ = ["BaseProfile", "IdentityName"]

