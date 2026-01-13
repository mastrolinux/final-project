-- OAuth 2.1 Server Database Schema
-- Implements OAuth 2.1 draft specification with mandatory PKCE
-- Part of Phase 3: OAuth 2.1 Server

-- OAuth Scopes - Defines available permission scopes
CREATE TABLE oauth_scopes (
    scope_name VARCHAR(100) PRIMARY KEY,
    description TEXT NOT NULL,
    required_context_type context_type,  -- NULL means no context restriction
    access_level VARCHAR(20) NOT NULL DEFAULT 'read' CHECK (access_level IN ('read', 'write', 'admin')),
    allowed_fields TEXT[],  -- Array of field names accessible with this scope
    is_sensitive BOOLEAN NOT NULL DEFAULT false,  -- Requires explicit consent display
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE oauth_scopes IS 'Defines available OAuth scopes and their access permissions';
COMMENT ON COLUMN oauth_scopes.required_context_type IS 'If set, scope only valid for specific context type';
COMMENT ON COLUMN oauth_scopes.allowed_fields IS 'Profile fields accessible with this scope';

-- OAuth Clients - Third-party application registrations
CREATE TABLE oauth_clients (
    client_id VARCHAR(64) PRIMARY KEY,
    client_secret_hash VARCHAR(256),  -- NULL for public clients (PKCE-only)
    client_name VARCHAR(255) NOT NULL,
    client_description TEXT,
    client_uri TEXT,  -- Homepage URL
    logo_uri TEXT,  -- Client logo for consent screen
    redirect_uris TEXT[] NOT NULL,  -- Allowed callback URLs (exact match required)
    allowed_scopes TEXT[] NOT NULL DEFAULT ARRAY['profile:read:basic'],
    default_context_type context_type,  -- Default context for this client
    is_confidential BOOLEAN NOT NULL DEFAULT false,  -- Confidential vs public client
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_first_party BOOLEAN NOT NULL DEFAULT false,  -- Skip consent for first-party apps
    token_endpoint_auth_method VARCHAR(50) NOT NULL DEFAULT 'none' 
        CHECK (token_endpoint_auth_method IN ('none', 'client_secret_post', 'client_secret_basic')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ  -- Soft delete
);

COMMENT ON TABLE oauth_clients IS 'Registered OAuth client applications';
COMMENT ON COLUMN oauth_clients.client_secret_hash IS 'Argon2id hashed secret for confidential clients';
COMMENT ON COLUMN oauth_clients.redirect_uris IS 'Exact-match redirect URIs (OAuth 2.1 requirement)';
COMMENT ON COLUMN oauth_clients.is_first_party IS 'First-party apps may skip consent screen';

-- OAuth Authorization Codes - Temporary codes for Authorization Code Flow
CREATE TABLE oauth_authorization_codes (
    code VARCHAR(128) PRIMARY KEY,
    client_id VARCHAR(64) NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES base_profiles(user_id) ON DELETE CASCADE,
    redirect_uri TEXT NOT NULL,
    scope TEXT NOT NULL,  -- Space-separated scope string
    state VARCHAR(256),  -- Client state parameter
    code_challenge VARCHAR(128) NOT NULL,  -- PKCE challenge (mandatory in OAuth 2.1)
    code_challenge_method VARCHAR(10) NOT NULL DEFAULT 'S256' CHECK (code_challenge_method IN ('S256')),
    context_profile_id UUID REFERENCES context_profiles(id) ON DELETE SET NULL,  -- Optional context binding
    nonce VARCHAR(256),  -- OIDC nonce for ID token
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '10 minutes'),
    used_at TIMESTAMPTZ  -- Set when code is exchanged (prevents replay)
);

COMMENT ON TABLE oauth_authorization_codes IS 'Temporary authorization codes (10 min expiry)';
COMMENT ON COLUMN oauth_authorization_codes.code_challenge IS 'PKCE code challenge (mandatory)';
COMMENT ON COLUMN oauth_authorization_codes.used_at IS 'Non-null indicates code was consumed';

-- OAuth Access Tokens - Short-lived access tokens
CREATE TABLE oauth_access_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash VARCHAR(256) NOT NULL UNIQUE,  -- SHA-256 hash of token
    client_id VARCHAR(64) NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES base_profiles(user_id) ON DELETE CASCADE,
    scope TEXT NOT NULL,
    context_profile_id UUID REFERENCES context_profiles(id) ON DELETE SET NULL,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '1 hour'),
    revoked_at TIMESTAMPTZ  -- Token revocation timestamp
);

COMMENT ON TABLE oauth_access_tokens IS 'OAuth access tokens (1 hour default expiry)';
COMMENT ON COLUMN oauth_access_tokens.token_hash IS 'SHA-256 hash for secure storage';

-- OAuth Refresh Tokens - Long-lived tokens with rotation
CREATE TABLE oauth_refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash VARCHAR(256) NOT NULL UNIQUE,
    access_token_id UUID NOT NULL REFERENCES oauth_access_tokens(id) ON DELETE CASCADE,
    client_id VARCHAR(64) NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES base_profiles(user_id) ON DELETE CASCADE,
    scope TEXT NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '30 days'),
    revoked_at TIMESTAMPTZ,
    rotated_at TIMESTAMPTZ,  -- Set when token is rotated
    replaced_by_id UUID REFERENCES oauth_refresh_tokens(id)  -- Points to replacement token
);

COMMENT ON TABLE oauth_refresh_tokens IS 'Refresh tokens with rotation tracking';
COMMENT ON COLUMN oauth_refresh_tokens.rotated_at IS 'Non-null indicates token was rotated';
COMMENT ON COLUMN oauth_refresh_tokens.replaced_by_id IS 'Links to replacement token for audit';

-- OAuth Consents - User consent records for third-party access
CREATE TABLE oauth_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES base_profiles(user_id) ON DELETE CASCADE,
    client_id VARCHAR(64) NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
    granted_scopes TEXT[] NOT NULL,
    context_profile_id UUID REFERENCES context_profiles(id) ON DELETE SET NULL,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,  -- NULL means no expiry
    withdrawn_at TIMESTAMPTZ,  -- Consent withdrawal timestamp
    consent_method VARCHAR(50) NOT NULL DEFAULT 'explicit' 
        CHECK (consent_method IN ('explicit', 'implicit', 'first_party')),
    ip_address INET,
    user_agent TEXT
);

-- Partial unique index: One active consent per user-client pair
-- (allows multiple withdrawn consents for audit trail)
CREATE UNIQUE INDEX idx_oauth_consents_unique_active 
    ON oauth_consents(user_id, client_id) 
    WHERE withdrawn_at IS NULL;

COMMENT ON TABLE oauth_consents IS 'User consent records for OAuth authorizations';
COMMENT ON COLUMN oauth_consents.withdrawn_at IS 'Non-null indicates consent was withdrawn';
COMMENT ON COLUMN oauth_consents.consent_method IS 'How consent was obtained';

-- Indexes for performance

-- oauth_scopes indexes
CREATE INDEX idx_oauth_scopes_context_type ON oauth_scopes(required_context_type) 
    WHERE required_context_type IS NOT NULL;

-- oauth_clients indexes
CREATE INDEX idx_oauth_clients_active ON oauth_clients(client_id) 
    WHERE is_active = true AND deleted_at IS NULL;

-- oauth_authorization_codes indexes
CREATE INDEX idx_oauth_auth_codes_client ON oauth_authorization_codes(client_id);
CREATE INDEX idx_oauth_auth_codes_user ON oauth_authorization_codes(user_id);
CREATE INDEX idx_oauth_auth_codes_expires ON oauth_authorization_codes(expires_at) 
    WHERE used_at IS NULL;

-- oauth_access_tokens indexes
CREATE INDEX idx_oauth_access_tokens_user ON oauth_access_tokens(user_id);
CREATE INDEX idx_oauth_access_tokens_client ON oauth_access_tokens(client_id);
CREATE INDEX idx_oauth_access_tokens_expires ON oauth_access_tokens(expires_at) 
    WHERE revoked_at IS NULL;
CREATE INDEX idx_oauth_access_tokens_context ON oauth_access_tokens(context_profile_id) 
    WHERE context_profile_id IS NOT NULL;

-- oauth_refresh_tokens indexes
CREATE INDEX idx_oauth_refresh_tokens_user ON oauth_refresh_tokens(user_id);
CREATE INDEX idx_oauth_refresh_tokens_access ON oauth_refresh_tokens(access_token_id);
CREATE INDEX idx_oauth_refresh_tokens_expires ON oauth_refresh_tokens(expires_at) 
    WHERE revoked_at IS NULL AND rotated_at IS NULL;

-- oauth_consents indexes
CREATE INDEX idx_oauth_consents_user ON oauth_consents(user_id);
CREATE INDEX idx_oauth_consents_client ON oauth_consents(client_id);
CREATE INDEX idx_oauth_consents_active ON oauth_consents(user_id, client_id) 
    WHERE withdrawn_at IS NULL;

-- Auto-update timestamp trigger for oauth_clients
CREATE TRIGGER update_oauth_clients_updated_at
    BEFORE UPDATE ON oauth_clients
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Row-Level Security Policies

-- oauth_clients: Read-only for authenticated users, admin for management
ALTER TABLE oauth_clients ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view active clients" ON oauth_clients
    FOR SELECT USING (is_active = true AND deleted_at IS NULL);

CREATE POLICY "Admins can manage clients" ON oauth_clients
    FOR ALL USING (
        current_setting('request.jwt.claims', true)::jsonb->'roles' @> '"admin"'::jsonb
    );

-- oauth_authorization_codes: Only the user who initiated can see their codes
ALTER TABLE oauth_authorization_codes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own auth codes" ON oauth_authorization_codes
    FOR SELECT USING (
        user_id::text = current_setting('request.jwt.claims', true)::json->>'sub'
    );

CREATE POLICY "System can create auth codes" ON oauth_authorization_codes
    FOR INSERT WITH CHECK (true);  -- Handled at application level

CREATE POLICY "System can update auth codes" ON oauth_authorization_codes
    FOR UPDATE USING (true);  -- Handled at application level

-- oauth_access_tokens: Users can view/revoke their own tokens
ALTER TABLE oauth_access_tokens ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own access tokens" ON oauth_access_tokens
    FOR SELECT USING (
        user_id::text = current_setting('request.jwt.claims', true)::json->>'sub'
    );

CREATE POLICY "Users can revoke own access tokens" ON oauth_access_tokens
    FOR UPDATE USING (
        user_id::text = current_setting('request.jwt.claims', true)::json->>'sub'
    );

CREATE POLICY "System can create access tokens" ON oauth_access_tokens
    FOR INSERT WITH CHECK (true);

-- oauth_refresh_tokens: Same as access tokens
ALTER TABLE oauth_refresh_tokens ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own refresh tokens" ON oauth_refresh_tokens
    FOR SELECT USING (
        user_id::text = current_setting('request.jwt.claims', true)::json->>'sub'
    );

CREATE POLICY "Users can revoke own refresh tokens" ON oauth_refresh_tokens
    FOR UPDATE USING (
        user_id::text = current_setting('request.jwt.claims', true)::json->>'sub'
    );

CREATE POLICY "System can create refresh tokens" ON oauth_refresh_tokens
    FOR INSERT WITH CHECK (true);

-- oauth_consents: Users can view/manage their own consents
ALTER TABLE oauth_consents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own consents" ON oauth_consents
    FOR SELECT USING (
        user_id::text = current_setting('request.jwt.claims', true)::json->>'sub'
    );

CREATE POLICY "Users can create own consents" ON oauth_consents
    FOR INSERT WITH CHECK (
        user_id::text = current_setting('request.jwt.claims', true)::json->>'sub'
    );

CREATE POLICY "Users can withdraw own consents" ON oauth_consents
    FOR UPDATE USING (
        user_id::text = current_setting('request.jwt.claims', true)::json->>'sub'
    );

-- Admin override for all OAuth tables
CREATE POLICY "Admins can access all oauth_authorization_codes" ON oauth_authorization_codes
    FOR ALL USING (
        current_setting('request.jwt.claims', true)::jsonb->'roles' @> '"admin"'::jsonb
    );

CREATE POLICY "Admins can access all oauth_access_tokens" ON oauth_access_tokens
    FOR ALL USING (
        current_setting('request.jwt.claims', true)::jsonb->'roles' @> '"admin"'::jsonb
    );

CREATE POLICY "Admins can access all oauth_refresh_tokens" ON oauth_refresh_tokens
    FOR ALL USING (
        current_setting('request.jwt.claims', true)::jsonb->'roles' @> '"admin"'::jsonb
    );

CREATE POLICY "Admins can access all oauth_consents" ON oauth_consents
    FOR ALL USING (
        current_setting('request.jwt.claims', true)::jsonb->'roles' @> '"admin"'::jsonb
    );

-- Seed default OAuth scopes
INSERT INTO oauth_scopes (scope_name, description, required_context_type, access_level, allowed_fields, is_sensitive) VALUES
    -- Basic profile scopes
    ('profile:read:basic', 'Read basic profile information', NULL, 'read', 
     ARRAY['preferred_name', 'display_name', 'photo_url'], false),
    ('profile:read:email', 'Read email address', NULL, 'read', 
     ARRAY['primary_email', 'email_verified'], true),
    ('profile:read:phone', 'Read phone number', NULL, 'read', 
     ARRAY['primary_phone', 'phone_verified'], true),
    ('profile:read:full', 'Read complete profile (except legal name)', NULL, 'read', 
     ARRAY['preferred_name', 'display_name', 'photo_url', 'bio', 'website', 'primary_email', 'primary_phone', 'preferred_language'], true),
    ('profile:write', 'Update profile information', NULL, 'write', 
     ARRAY['preferred_name', 'display_name', 'bio', 'photo_url', 'website'], true),
    
    -- Context-specific scopes
    ('contexts:read', 'Read available context types', NULL, 'read', 
     ARRAY['context_type', 'context_name'], false),
    ('contexts:professional:read', 'Read professional context profile', 'professional', 'read', 
     ARRAY['display_name', 'bio', 'email_override', 'credentials', 'website'], false),
    ('contexts:social:read', 'Read social context profile', 'social', 'read', 
     ARRAY['display_name', 'bio', 'email_override', 'interests'], false),
    ('contexts:legal:read', 'Read legal context profile (requires verification)', 'legal', 'read', 
     ARRAY['display_name', 'email_override', 'date_of_birth'], true),
    ('contexts:healthcare:read', 'Read healthcare context profile (requires verification)', 'healthcare', 'read', 
     ARRAY['display_name', 'email_override', 'date_of_birth', 'medical_info'], true),
    
    -- OIDC standard scopes
    ('openid', 'OpenID Connect authentication', NULL, 'read', 
     ARRAY['sub'], false),
    ('email', 'Access email address (OIDC)', NULL, 'read', 
     ARRAY['email', 'email_verified'], true),
    ('phone', 'Access phone number (OIDC)', NULL, 'read', 
     ARRAY['phone_number', 'phone_number_verified'], true),
    
    -- Offline access for refresh tokens
    ('offline_access', 'Request refresh token for offline access', NULL, 'read', 
     NULL, false);

-- Rollback instructions:
-- DROP TABLE IF EXISTS oauth_consents;
-- DROP TABLE IF EXISTS oauth_refresh_tokens;
-- DROP TABLE IF EXISTS oauth_access_tokens;
-- DROP TABLE IF EXISTS oauth_authorization_codes;
-- DROP TABLE IF EXISTS oauth_clients;
-- DROP TABLE IF EXISTS oauth_scopes;
