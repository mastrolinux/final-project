"""
OAuth 2.1 Service

Business logic for OAuth 2.1 authorization server.
Implements Authorization Code Flow with mandatory PKCE.
"""

import hashlib
import base64
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING
from uuid import UUID
from dataclasses import dataclass
from sqlalchemy.orm import Session

from src.repositories.oauth_repository import OAuthRepository
from src.repositories.profile_repository import ProfileRepository
from src.repositories.context_repository import ContextRepository
from src.models.oauth import (
    OAuthClient,
    OAuthAuthorizationCode,
    OAuthAccessToken,
    OAuthRefreshToken,
    OAuthConsent,
    OAuthScope
)
from src.models.profile import BaseProfile, AccountType
from src.models.context import ContextProfile, ContextType
from src.models.audit import AuditEventType, AuditOperation

if TYPE_CHECKING:
    from src.services.audit_service import AuditService


class OAuthServiceError(Exception):
    """Base exception for OAuth service errors"""
    
    def __init__(self, error: str, error_description: str, status_code: int = 400):
        self.error = error
        self.error_description = error_description
        self.status_code = status_code
        super().__init__(f"{error}: {error_description}")


class InvalidClientError(OAuthServiceError):
    """Client authentication failed"""
    
    def __init__(self, description: str = "Client authentication failed"):
        super().__init__("invalid_client", description, 401)


class InvalidGrantError(OAuthServiceError):
    """Invalid or expired grant"""
    
    def __init__(self, description: str = "The provided authorization grant is invalid"):
        super().__init__("invalid_grant", description, 400)


class InvalidRequestError(OAuthServiceError):
    """Invalid request parameters"""
    
    def __init__(self, description: str = "Invalid request"):
        super().__init__("invalid_request", description, 400)


class InvalidScopeError(OAuthServiceError):
    """Invalid or unsupported scope"""
    
    def __init__(self, description: str = "The requested scope is invalid"):
        super().__init__("invalid_scope", description, 400)


class AccessDeniedError(OAuthServiceError):
    """User denied authorization"""
    
    def __init__(self, description: str = "The resource owner denied the request"):
        super().__init__("access_denied", description, 403)


class UnauthorizedClientError(OAuthServiceError):
    """Client not authorized for this grant type"""
    
    def __init__(self, description: str = "Client not authorized"):
        super().__init__("unauthorized_client", description, 403)


@dataclass
class TokenResponse:
    """Response from token issuance"""
    access_token: str
    token_type: str
    expires_in: int
    scope: str
    refresh_token: Optional[str] = None
    context_profile_id: Optional[UUID] = None


@dataclass
class IntrospectionResult:
    """Result from token introspection"""
    active: bool
    scope: Optional[str] = None
    client_id: Optional[str] = None
    username: Optional[str] = None
    token_type: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None
    sub: Optional[str] = None
    aud: Optional[str] = None
    context_profile_id: Optional[UUID] = None
    context_type: Optional[str] = None


class OAuthService:
    """
    OAuth 2.1 Authorization Server Service
    
    Implements:
    - Authorization Code Flow with PKCE (mandatory)
    - Token issuance and validation
    - Refresh token rotation
    - Scope validation and filtering
    - Context-aware token binding
    """
    
    # Token expiry times (seconds)
    ACCESS_TOKEN_EXPIRY = 3600  # 1 hour
    REFRESH_TOKEN_EXPIRY = 2592000  # 30 days
    AUTHORIZATION_CODE_EXPIRY = 600  # 10 minutes
    
    def __init__(
        self,
        oauth_repo: OAuthRepository,
        profile_repo: Optional[ProfileRepository] = None,
        context_repo: Optional[ContextRepository] = None,
        audit_service: Optional["AuditService"] = None
    ):
        self.oauth_repo = oauth_repo
        self.profile_repo = profile_repo
        self.context_repo = context_repo
        self.audit_service = audit_service
    
# PKCE Validation
    
    @staticmethod
    def generate_pkce_challenge(code_verifier: str) -> str:
        """
        Generate PKCE code_challenge from code_verifier.
        
        Uses SHA-256 hash encoded as base64url (S256 method).
        This is the only method allowed in OAuth 2.1.
        
        Args:
            code_verifier: Random string between 43-128 characters
            
        Returns:
            Base64url-encoded SHA-256 hash of the verifier
        """
        # SHA-256 hash
        digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
        
        # Base64url encode (no padding)
        challenge = base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
        
        return challenge
    
    @staticmethod
    def verify_pkce(code_verifier: str, code_challenge: str) -> bool:
        """
        Verify PKCE code_verifier matches code_challenge.
        
        Args:
            code_verifier: Original verifier sent by client
            code_challenge: Challenge stored with authorization code
            
        Returns:
            True if verification succeeds, False otherwise
        """
        expected_challenge = OAuthService.generate_pkce_challenge(code_verifier)
        return expected_challenge == code_challenge
    
# Client Validation
    
    def get_client(self, client_id: str) -> OAuthClient:
        """
        Get and validate an OAuth client.
        
        Raises:
            InvalidClientError: If client not found or inactive
        """
        client = self.oauth_repo.get_active_client(client_id)
        if not client:
            raise InvalidClientError("Unknown client")
        return client
    
    def validate_client_credentials(
        self,
        client_id: str,
        client_secret: Optional[str] = None
    ) -> OAuthClient:
        """
        Validate client credentials.
        
        For confidential clients, requires valid client_secret.
        For public clients, no secret required.
        
        Raises:
            InvalidClientError: If validation fails
        """
        client = self.get_client(client_id)
        
        if client.is_confidential:
            if not client_secret:
                raise InvalidClientError("Client secret required")
            
            # Verify secret hash
            from passlib.hash import argon2
            if not client.client_secret_hash:
                raise InvalidClientError("Client secret not configured")
            
            try:
                if not argon2.verify(client_secret, client.client_secret_hash):
                    raise InvalidClientError("Invalid client secret")
            except Exception:
                raise InvalidClientError("Invalid client secret")
        
        return client
    
    def validate_redirect_uri(self, client: OAuthClient, redirect_uri: str) -> None:
        """
        Validate redirect URI against client's registered URIs.
        
        OAuth 2.1 requires exact string matching (no wildcards).
        
        Raises:
            InvalidRequestError: If redirect URI not registered
        """
        if not client.is_redirect_uri_valid(redirect_uri):
            raise InvalidRequestError(
                f"Invalid redirect_uri: must match one of the registered URIs"
            )
    
# Scope Validation
    
    def validate_scopes(
        self,
        client: OAuthClient,
        requested_scopes: List[str],
        user_profile: Optional[BaseProfile] = None,
        context_type: Optional[ContextType] = None
    ) -> List[str]:
        """
        Validate and filter requested scopes.
        
        Checks:
        1. Client is allowed to request each scope
        2. Scope exists in the system
        3. User's account type allows the scope (if applicable)
        4. Context type restriction is met (if applicable)
        
        Args:
            client: OAuth client requesting authorization
            requested_scopes: List of scope strings requested
            user_profile: User's profile (for account type checks)
            context_type: Requested context type
            
        Returns:
            List of validated/approved scopes
            
        Raises:
            InvalidScopeError: If any scope is invalid
        """
        validated_scopes = []
        
        for scope_name in requested_scopes:
            # Check client is allowed to request this scope
            if not client.can_request_scope(scope_name):
                raise InvalidScopeError(
                    f"Client not authorized for scope: {scope_name}"
                )
            
            # Check scope exists
            scope = self.oauth_repo.get_scope(scope_name)
            if not scope:
                # Some common scopes may not need database entry
                if scope_name in ['openid', 'offline_access']:
                    validated_scopes.append(scope_name)
                    continue
                raise InvalidScopeError(f"Unknown scope: {scope_name}")
            
            # Check context type restriction
            if scope.required_context_type:
                if not context_type:
                    raise InvalidScopeError(
                        f"Scope '{scope_name}' requires context type '{scope.required_context_type}'"
                    )
                if context_type != scope.required_context_type:
                    raise InvalidScopeError(
                        f"Scope '{scope_name}' requires context type '{scope.required_context_type}'"
                    )
            
            # Check user account type restrictions
            if user_profile and scope.is_sensitive:
                # Pseudonymous accounts have limited access to sensitive scopes
                if user_profile.account_type == AccountType.pseudonymous:
                    if scope_name in ['contexts:legal:read', 'contexts:healthcare:read']:
                        raise InvalidScopeError(
                            f"Pseudonymous accounts cannot access scope: {scope_name}"
                        )
            
            validated_scopes.append(scope_name)
        
        if not validated_scopes:
            raise InvalidScopeError("At least one valid scope required")
        
        return validated_scopes

    def get_scope_details(self, scope_names: List[str]) -> List["OAuthScope"]:
        """
        Get full scope information for consent screen display.
        
        Retrieves scope objects with descriptions, sensitivity flags,
        and context type requirements for informed user consent.
        
        Args:
            scope_names: List of scope name strings
            
        Returns:
            List of OAuthScope objects with full details
        """
        # Handle special scopes that may not be in database
        db_scope_names = [
            s for s in scope_names 
            if s not in ['openid', 'offline_access']
        ]
        
        scopes = self.oauth_repo.get_scopes(db_scope_names)
        
        # Add placeholder info for special scopes
        from src.models.oauth import OAuthScope as OAuthScopeModel
        
        for scope_name in scope_names:
            if scope_name == 'openid':
                # Create transient scope object for openid
                openid_scope = OAuthScopeModel(
                    scope_name='openid',
                    description='Access your user identifier',
                    is_sensitive=False
                )
                scopes.append(openid_scope)
            elif scope_name == 'offline_access':
                offline_scope = OAuthScopeModel(
                    scope_name='offline_access',
                    description='Maintain access when you are not actively using the application',
                    is_sensitive=False
                )
                scopes.append(offline_scope)
        
        return scopes
    
    def filter_profile_fields_by_scopes(
        self,
        profile_data: Dict[str, Any],
        scopes: List[str]
    ) -> Dict[str, Any]:
        """
        Filter profile data based on granted scopes.
        
        Each scope grants access to specific fields.
        
        Args:
            profile_data: Full profile data dictionary
            scopes: List of granted scope strings
            
        Returns:
            Filtered profile data with only allowed fields
        """
        # Define field access by scope
        scope_fields = {
            'openid': {'sub'},
            'profile:read:basic': {'preferred_name', 'display_name', 'avatar_url', 'avatar_thumbnail_url'},
            'profile:read:photo': {'avatar_url', 'avatar_thumbnail_url'},
            'profile:read:email': {'primary_email', 'email', 'email_verified'},
            'profile:read:phone': {'primary_phone', 'phone', 'phone_verified'},
            'profile:read:full': {
                'preferred_name', 'display_name', 'avatar_url', 'avatar_thumbnail_url', 'bio',
                'website', 'primary_email', 'email', 'primary_phone', 'phone',
                'preferred_language', 'email_verified', 'phone_verified'
            },
            'email': {'email', 'primary_email', 'email_verified'},
            'phone': {'phone', 'phone_number', 'primary_phone', 'phone_verified'},
            'contexts:read': {'context_type', 'context_name'},
            'contexts:professional:read': {
                'display_name', 'bio', 'email_override', 'credentials', 'website'
            },
            'contexts:social:read': {
                'display_name', 'bio', 'email_override', 'interests'
            },
        }
        
        # Always include certain fields
        allowed_fields = {'sub', 'user_id', 'account_type'}
        
        # Add fields from each granted scope
        for scope in scopes:
            if scope in scope_fields:
                allowed_fields.update(scope_fields[scope])
        
        # Filter the profile data
        filtered = {}
        for key, value in profile_data.items():
            if key in allowed_fields:
                filtered[key] = value
        
        return filtered
    
# Authorization Code Flow
    
    def create_authorization_code(
        self,
        client_id: str,
        user_id: UUID,
        redirect_uri: str,
        scope: str,
        code_challenge: str,
        code_challenge_method: str = "S256",
        state: Optional[str] = None,
        context_profile_id: Optional[UUID] = None,
        nonce: Optional[str] = None
    ) -> OAuthAuthorizationCode:
        """
        Create an authorization code after user grants consent.
        
        Args:
            client_id: Client requesting authorization
            user_id: User granting authorization
            redirect_uri: Client's callback URL
            scope: Space-separated scope string
            code_challenge: PKCE challenge
            code_challenge_method: Must be 'S256' (OAuth 2.1)
            state: Client state parameter
            context_profile_id: Optional context binding
            nonce: OIDC nonce for ID token
            
        Returns:
            Authorization code record
            
        Raises:
            InvalidRequestError: If PKCE method invalid
            InvalidClientError: If client invalid
        """
        # Validate PKCE method (OAuth 2.1 only allows S256)
        if code_challenge_method != "S256":
            raise InvalidRequestError(
                "code_challenge_method must be 'S256'"
            )
        
        # Validate client
        client = self.get_client(client_id)
        self.validate_redirect_uri(client, redirect_uri)
        
        # Create authorization code
        auth_code = self.oauth_repo.create_authorization_code(
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            state=state,
            context_profile_id=context_profile_id,
            nonce=nonce,
            expires_in_seconds=self.AUTHORIZATION_CODE_EXPIRY
        )
        
        return auth_code
    
    def exchange_authorization_code(
        self,
        code: str,
        client_id: str,
        redirect_uri: str,
        code_verifier: str,
        client_secret: Optional[str] = None
    ) -> TokenResponse:
        """
        Exchange authorization code for tokens.
        
        Validates:
        1. Client credentials (if confidential)
        2. Authorization code validity
        3. PKCE code_verifier
        4. Redirect URI matches
        
        Args:
            code: Authorization code to exchange
            client_id: Client ID
            redirect_uri: Must match original request
            code_verifier: PKCE verifier
            client_secret: Optional for confidential clients
            
        Returns:
            TokenResponse with access_token (and refresh_token if offline_access)
            
        Raises:
            InvalidGrantError: If code invalid or verification fails
        """
        # Validate client
        client = self.validate_client_credentials(client_id, client_secret)
        
        # Get authorization code
        auth_code = self.oauth_repo.get_valid_authorization_code(code)
        if not auth_code:
            raise InvalidGrantError("Authorization code is invalid or expired")
        
        # Verify client matches
        if auth_code.client_id != client_id:
            raise InvalidGrantError("Authorization code was issued to another client")
        
        # Verify redirect URI matches (exact match per OAuth 2.1)
        if auth_code.redirect_uri != redirect_uri:
            raise InvalidGrantError("redirect_uri mismatch")
        
        # Verify PKCE
        if not self.verify_pkce(code_verifier, auth_code.code_challenge):
            raise InvalidGrantError("PKCE verification failed")
        
        # Mark code as used (prevents replay)
        self.oauth_repo.mark_authorization_code_used(code)
        
        # Issue tokens
        return self._issue_tokens(
            client=client,
            user_id=auth_code.user_id,
            scope=auth_code.scope,
            context_profile_id=auth_code.context_profile_id
        )
    
    def refresh_access_token(
        self,
        refresh_token: str,
        client_id: str,
        client_secret: Optional[str] = None,
        scope: Optional[str] = None
    ) -> TokenResponse:
        """
        Exchange refresh token for new token pair.
        
        Implements refresh token rotation: issues new refresh token
        and invalidates the old one.
        
        Args:
            refresh_token: Current refresh token
            client_id: Client ID
            client_secret: Optional for confidential clients
            scope: Optional reduced scope (must be subset)
            
        Returns:
            TokenResponse with new tokens
            
        Raises:
            InvalidGrantError: If refresh token invalid
        """
        # Validate client
        client = self.validate_client_credentials(client_id, client_secret)
        
        # Get refresh token
        token = self.oauth_repo.get_active_refresh_token(refresh_token)
        if not token:
            raise InvalidGrantError("Refresh token is invalid or expired")
        
        # Verify client matches
        if token.client_id != client_id:
            raise InvalidGrantError("Refresh token was issued to another client")
        
        # Handle scope reduction
        final_scope = token.scope
        if scope:
            requested_scopes = set(scope.split())
            original_scopes = set(token.scope.split())
            
            # Can only reduce scope, not expand
            if not requested_scopes.issubset(original_scopes):
                raise InvalidScopeError("Can only request subset of original scopes")
            
            final_scope = scope
        
        # Issue new tokens with rotation
        return self._issue_tokens(
            client=client,
            user_id=token.user_id,
            scope=final_scope,
            context_profile_id=None,  # Context binding from original auth
            old_refresh_token_id=token.id
        )
    
    def _issue_tokens(
        self,
        client: OAuthClient,
        user_id: UUID,
        scope: str,
        context_profile_id: Optional[UUID] = None,
        old_refresh_token_id: Optional[UUID] = None
    ) -> TokenResponse:
        """
        Internal method to issue access and refresh tokens.
        
        Args:
            client: OAuth client
            user_id: User ID
            scope: Scope string
            context_profile_id: Optional context binding
            old_refresh_token_id: If rotating, ID of old token
            
        Returns:
            TokenResponse with tokens
        """
        # Create access token
        access_token_model, access_token = self.oauth_repo.create_access_token(
            client_id=client.client_id,
            user_id=user_id,
            scope=scope,
            context_profile_id=context_profile_id,
            expires_in_seconds=self.ACCESS_TOKEN_EXPIRY
        )
        
        # Create or rotate refresh token if offline_access scope
        refresh_token = None
        if 'offline_access' in scope.split():
            if old_refresh_token_id:
                # Rotate existing refresh token
                _, refresh_token = self.oauth_repo.rotate_refresh_token(
                    old_token_id=old_refresh_token_id,
                    new_access_token_id=access_token_model.id,
                    client_id=client.client_id,
                    user_id=user_id,
                    scope=scope,
                    expires_in_seconds=self.REFRESH_TOKEN_EXPIRY
                )
            else:
                # Create new refresh token
                _, refresh_token = self.oauth_repo.create_refresh_token(
                    access_token_id=access_token_model.id,
                    client_id=client.client_id,
                    user_id=user_id,
                    scope=scope,
                    expires_in_seconds=self.REFRESH_TOKEN_EXPIRY
                )
        
        return TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=self.ACCESS_TOKEN_EXPIRY,
            scope=scope,
            refresh_token=refresh_token,
            context_profile_id=context_profile_id
        )
    
# Token Introspection and Revocation
    
    def introspect_token(
        self,
        token: str,
        token_type_hint: Optional[str] = None
    ) -> IntrospectionResult:
        """
        Introspect a token to determine its validity and metadata.
        
        Used by resource servers to validate tokens.
        
        Args:
            token: Token to introspect
            token_type_hint: Optional hint ('access_token' or 'refresh_token')
            
        Returns:
            IntrospectionResult with token metadata if active
        """
        # Try as access token
        access_token = self.oauth_repo.get_access_token_by_raw(token)
        if access_token:
            if access_token.is_active:
                return IntrospectionResult(
                    active=True,
                    scope=access_token.scope,
                    client_id=access_token.client_id,
                    token_type="access_token",
                    exp=int(access_token.expires_at.timestamp()),
                    iat=int(access_token.issued_at.timestamp()),
                    sub=str(access_token.user_id),
                    aud=access_token.client_id,
                    context_profile_id=access_token.context_profile_id
                )
            return IntrospectionResult(active=False)
        
        # Try as refresh token
        refresh_token = self.oauth_repo.get_refresh_token_by_raw(token)
        if refresh_token:
            if refresh_token.is_active:
                return IntrospectionResult(
                    active=True,
                    scope=refresh_token.scope,
                    client_id=refresh_token.client_id,
                    token_type="refresh_token",
                    exp=int(refresh_token.expires_at.timestamp()),
                    iat=int(refresh_token.issued_at.timestamp()),
                    sub=str(refresh_token.user_id)
                )
            return IntrospectionResult(active=False)
        
        return IntrospectionResult(active=False)
    
    def revoke_token(
        self,
        token: str,
        token_type_hint: Optional[str] = None,
        client_id: Optional[str] = None
    ) -> bool:
        """
        Revoke a token.
        
        Per RFC 7009, returns success even if token unknown.
        
        Args:
            token: Token to revoke
            token_type_hint: Optional hint
            client_id: Optional client ID for validation
            
        Returns:
            True (always, per spec)
        """
        # Try as access token
        revoked = self.oauth_repo.revoke_access_token_by_raw(token)
        if revoked:
            return True
        
        # Try as refresh token
        revoked = self.oauth_repo.revoke_refresh_token_by_raw(token)

        # Audit: token revocation
        if self.audit_service:
            self.audit_service.log_event(
                event_type=AuditEventType.token_revoke,
                user_id=None,
                actor_id=None,
                resource_type="oauth_token",
                resource_id="redacted",
                operation=AuditOperation.revoke,
                legal_basis="consent"
            )

        # Always return success per RFC 7009
        return True
    
# Consent Management
    
    def record_consent(
        self,
        user_id: UUID,
        client_id: str,
        granted_scopes: List[str],
        context_profile_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> OAuthConsent:
        """
        Record user consent for a client.
        
        Called when user approves authorization request.
        """
        # Validate client
        client = self.get_client(client_id)
        
        # Validate scopes
        self.validate_scopes(client, granted_scopes)
        
        # Create consent
        consent = self.oauth_repo.create_consent(
            user_id=user_id,
            client_id=client_id,
            granted_scopes=granted_scopes,
            context_profile_id=context_profile_id,
            consent_method="explicit",
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Audit: consent grant
        if self.audit_service:
            self.audit_service.log_event(
                event_type=AuditEventType.consent_grant,
                user_id=user_id,
                actor_id=user_id,
                resource_type="oauth_consent",
                resource_id=client_id,
                operation=AuditOperation.grant,
                changes={"granted_scopes": granted_scopes},
                ip_address=ip_address,
                user_agent=user_agent,
                legal_basis="consent"
            )

        return consent
    
    def check_consent(
        self,
        user_id: UUID,
        client_id: str,
        required_scopes: List[str]
    ) -> bool:
        """
        Check if user has granted consent for required scopes.
        
        Returns:
            True if consent exists and covers all scopes
        """
        return self.oauth_repo.has_valid_consent(
            user_id=user_id,
            client_id=client_id,
            required_scopes=required_scopes
        )
    
    def withdraw_consent(self, user_id: UUID, client_id: str) -> bool:
        """
        Withdraw user consent for a client.

        Also revokes all tokens for this user-client pair.
        """
        result = self.oauth_repo.withdraw_consent(user_id, client_id)

        # Audit: consent withdrawal
        if self.audit_service:
            self.audit_service.log_event(
                event_type=AuditEventType.consent_withdraw,
                user_id=user_id,
                actor_id=user_id,
                resource_type="oauth_consent",
                resource_id=client_id,
                operation=AuditOperation.withdraw,
                legal_basis="consent"
            )

        return result
    
    def get_user_consents(self, user_id: UUID) -> List[OAuthConsent]:
        """Get all active consents for a user."""
        return self.oauth_repo.get_user_active_consents(user_id)
