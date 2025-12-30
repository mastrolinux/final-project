"""
Security utilities for authentication and authorization.
Implements Argon2id password hashing and JWT token management.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel

from src.core.config import settings


# ============================================================================
# Password Hashing (Argon2id)
# ============================================================================

# Argon2id configuration (NIST SP 800-63B recommended parameters)
pwd_context = CryptContext(
    schemes=["argon2"],
    argon2__memory_cost=65536,      # 64 MB memory usage
    argon2__time_cost=3,            # 3 iterations
    argon2__parallelism=4,          # 4 parallel threads
    argon2__type="id"               # Use Argon2id variant (best security)
)


def hash_password(password: str) -> str:
    """
    Hash password using Argon2id.
    
    Uses NIST-recommended parameters:
    - Memory cost: 64 MB (resists GPU attacks)
    - Time cost: 3 iterations
    - Parallelism: 4 threads
    - Variant: Argon2id (side-channel resistant)
    
    Args:
        password: Plain text password
        
    Returns:
        Argon2id hash string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against Argon2id hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Argon2id hash from database
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password meets minimum security requirements.
    
    Requirements:
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    return True, "Password meets requirements"


# ============================================================================
# JWT Token Management (HS256)
# ============================================================================

# JWT Configuration from settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour
REFRESH_TOKEN_EXPIRE_DAYS = 30    # 30 days


class TokenData(BaseModel):
    """JWT token payload data structure."""
    user_id: str
    email: Optional[str] = None
    account_type: Optional[str] = None
    token_type: str  # "access" or "refresh"
    exp: datetime
    iat: datetime
    jti: str  # Unique token ID for revocation tracking


def create_access_token(user_id: str, email: str, account_type: str) -> str:
    """
    Generate JWT access token with HS256 signing.
    
    Token includes:
    - sub: user_id
    - email: user email
    - account_type: verified/unverified/pseudonymous
    - token_type: "access"
    - exp: expiration timestamp (1 hour)
    - iat: issued at timestamp
    - jti: unique token ID
    
    Args:
        user_id: User identifier from auth_users.user_id
        email: User email
        account_type: Account verification level
        
    Returns:
        Encoded JWT token string
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": user_id,
        "email": email,
        "account_type": account_type,
        "token_type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4())
    }
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """
    Generate JWT refresh token with HS256 signing.
    
    Refresh tokens are long-lived (30 days) and used to obtain new access tokens.
    They contain minimal claims for security.
    
    Args:
        user_id: User identifier from auth_users.user_id
        
    Returns:
        Encoded JWT refresh token string
    """
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": user_id,
        "token_type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4())
    }
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str, token_type: str = "access") -> Optional[TokenData]:
    """
    Verify and decode JWT token.
    
    Validates:
    - Signature (HS256)
    - Expiration
    - Token type (access vs refresh)
    
    Args:
        token: JWT token string
        token_type: Expected token type ("access" or "refresh")
        
    Returns:
        TokenData if valid, None if invalid/expired
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
        
        # Verify token type matches expected
        if payload.get("token_type") != token_type:
            return None
        
        # Convert timestamps to datetime objects if they're integers
        if isinstance(payload.get("exp"), (int, float)):
            payload["exp"] = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        if isinstance(payload.get("iat"), (int, float)):
            payload["iat"] = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        
        return TokenData(
            user_id=payload["sub"],
            email=payload.get("email"),
            account_type=payload.get("account_type"),
            token_type=payload["token_type"],
            exp=payload["exp"],
            iat=payload["iat"],
            jti=payload["jti"]
        )
    except JWTError:
        return None
    except Exception:
        return None


def decode_token_without_verification(token: str) -> Optional[dict]:
    """
    Decode JWT token without verification (for debugging/logging only).
    
    WARNING: Do not use for authentication. Only for logging and debugging.
    
    Args:
        token: JWT token string
        
    Returns:
        Token payload dict if decodable, None otherwise
    """
    try:
        return jwt.decode(token, options={"verify_signature": False})
    except Exception:
        return None

