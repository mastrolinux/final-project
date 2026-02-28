"""
Sentinel value to distinguish "not provided" from "explicitly null" in updates.
"""

from typing import TypeVar

T = TypeVar("T")


class _Unset:
    """Singleton sentinel: use ``is UNSET`` to check if a field was provided."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNSET"

    def __bool__(self) -> bool:
        return False


UNSET: _Unset = _Unset()

Nullable = T | None | _Unset
