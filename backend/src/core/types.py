"""
Custom types and sentinel values for the application.

This module provides type utilities for handling optional fields in update
operations, where we need to distinguish between "field not provided" and
"field explicitly set to null".
"""

from typing import TypeVar, Union

T = TypeVar("T")


class _Unset:
    """
    Sentinel class to represent an unset/not-provided value.

    This is used to distinguish between:
    - Field not provided in request (use UNSET, keep existing value)
    - Field explicitly set to null (use None, clear the value)

    Example usage in service methods:
        def update_context_profile(
            self,
            context_id: UUID,
            phone_override: Union[str, None, _Unset] = UNSET,
        ):
            if phone_override is not UNSET:
                # Field was provided (could be string or None)
                updates['phone_override'] = phone_override
    """

    _instance = None

    def __new__(cls):
        """Ensure singleton instance for identity comparison."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNSET"

    def __bool__(self) -> bool:
        """UNSET is falsy for convenience."""
        return False


# Singleton instance - use `is UNSET` for comparison
UNSET: _Unset = _Unset()

# Type alias for optional fields that support explicit null
Nullable = Union[T, None, _Unset]
