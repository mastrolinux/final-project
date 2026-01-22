"""
API Dependencies

FastAPI dependencies for authentication, authorization, and common functionality.
"""

from src.api.dependencies.auth import (
    get_current_user,
    get_current_user_optional,
    require_admin,
    require_verified_user
)

__all__ = [
    "get_current_user",
    "get_current_user_optional",
    "require_admin",
    "require_verified_user"
]
