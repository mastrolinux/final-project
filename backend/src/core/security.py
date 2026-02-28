"""
Security utilities for authentication and authorization.
Implements Argon2id password hashing and JWT token management.
"""

import pathlib
import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from src.core.config import settings

#
# Password Hashing (Argon2id)
#

# Argon2id configuration (NIST SP 800-63B recommended parameters)
pwd_context = CryptContext(
    schemes=["argon2"],
    argon2__memory_cost=65536,  # 64 MB memory usage
    argon2__time_cost=3,  # 3 iterations
    argon2__parallelism=4,  # 4 parallel threads
    argon2__type="id",  # Use Argon2id variant (best security)
)


def hash_password(password: str) -> str:
    """Hash password using Argon2id (NIST SP 800-63B parameters)."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against Argon2id hash."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


# Common password blocklist (NIST SP 800-63B Section 5.1.1.2)
# Source: SecLists 10k-most-common.txt
# Loaded once at module import; frozenset provides O(1) lookup.
_COMMON_PASSWORDS_PATH = pathlib.Path(__file__).parent / "common_passwords.txt"
_COMMON_PASSWORDS: frozenset[str] = frozenset(
    line.strip().lower() for line in _COMMON_PASSWORDS_PATH.read_text().splitlines() if line.strip()
)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password per NIST SP 800-63B Section 5.1.1.2."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"

    if password.lower() in _COMMON_PASSWORDS:
        return False, "This password is too common. Please choose a different password"

    return True, "Password meets requirements"


#
# JWT Token Management (HS256)
#

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour
REFRESH_TOKEN_EXPIRE_DAYS = 30  # 30 days


class TokenData(BaseModel):
    """JWT token payload data structure."""

    user_id: str
    email: str | None = None
    account_type: str | None = None
    token_type: str  # "access" or "refresh"
    exp: datetime
    iat: datetime
    jti: str  # Unique token ID for revocation tracking


def create_access_token(user_id: str, email: str, account_type: str, is_admin: bool = False) -> str:
    """Generate HS256 JWT access token (1-hour expiry)."""
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": user_id,
        "email": email,
        "account_type": account_type,
        "is_admin": is_admin,
        "token_type": "access",
        "exp": expire,
        "iat": datetime.now(UTC),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Generate HS256 JWT refresh token (30-day expiry, minimal claims)."""
    expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": user_id,
        "token_type": "refresh",
        "exp": expire,
        "iat": datetime.now(UTC),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str, token_type: str = "access") -> TokenData | None:
    """Verify and decode HS256 JWT token, checking signature, expiry, and type."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("token_type") != token_type:
            return None

        if isinstance(payload.get("exp"), (int, float)):
            payload["exp"] = datetime.fromtimestamp(payload["exp"], tz=UTC)
        if isinstance(payload.get("iat"), (int, float)):
            payload["iat"] = datetime.fromtimestamp(payload["iat"], tz=UTC)

        return TokenData(
            user_id=payload["sub"],
            email=payload.get("email"),
            account_type=payload.get("account_type"),
            token_type=payload["token_type"],
            exp=payload["exp"],
            iat=payload["iat"],
            jti=payload["jti"],
        )
    except JWTError:
        return None
    except Exception:
        return None


def decode_token_without_verification(token: str) -> dict | None:
    """Decode JWT token without verification.

    WARNING: Do not use for authentication. Only for logging and debugging.
    """
    try:
        return jwt.decode(token, options={"verify_signature": False})
    except Exception:
        return None
