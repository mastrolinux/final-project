-- Authentication Users Migration
-- Creates auth_users table for storing authentication credentials separately from profile data
-- Part of Identity and Profile Management API - Academic Thesis Project
-- MAS-25: auth_users Table + Migration

-- ============================================================================
-- TABLE: auth_users
-- ============================================================================
-- Stores authentication credentials with 1:1 relationship to base_profiles
-- Separates authentication concerns from profile data following separation of concerns principle

CREATE TABLE auth_users (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Foreign key to base_profiles (1:1 relationship)
    user_id UUID NOT NULL UNIQUE REFERENCES base_profiles(user_id) ON DELETE CASCADE,
    
    -- Login credentials
    email TEXT NOT NULL,  -- Login email (should match base_profiles.primary_email)
    password_hash TEXT NOT NULL,  -- Argon2id hashed password (implementation in MAS-26)
    
    -- Email verification
    is_email_verified BOOLEAN NOT NULL DEFAULT false,
    email_verified_at TIMESTAMPTZ,
    verification_token TEXT,
    verification_token_expires_at TIMESTAMPTZ,
    
    -- Login tracking and protection
    last_login_at TIMESTAMPTZ,
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMPTZ,  -- Account lockout timestamp for rate limiting
    password_changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Password reset flow
    reset_token TEXT,
    reset_token_expires_at TIMESTAMPTZ,
    
    -- Standard mixins (timestamps and soft delete)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ  -- Soft delete support
);

-- ============================================================================
-- CONSTRAINTS
-- ============================================================================

-- Unique email constraint (only active accounts)
CREATE UNIQUE INDEX idx_auth_users_email_unique ON auth_users(email) WHERE deleted_at IS NULL;

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Fast email lookup for login
CREATE INDEX idx_auth_users_email ON auth_users(email);

-- Fast profile lookup (1:1 relationship)
CREATE INDEX idx_auth_users_user_id ON auth_users(user_id);

-- Email verification lookups
CREATE INDEX idx_auth_users_verification_token ON auth_users(verification_token) WHERE verification_token IS NOT NULL;

-- Password reset lookups
CREATE INDEX idx_auth_users_reset_token ON auth_users(reset_token) WHERE reset_token IS NOT NULL;

-- Query locked accounts
CREATE INDEX idx_auth_users_locked ON auth_users(locked_until) WHERE locked_until IS NOT NULL;

-- Soft delete queries
CREATE INDEX idx_auth_users_deleted ON auth_users(deleted_at) WHERE deleted_at IS NOT NULL;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE TRIGGER update_auth_users_updated_at
    BEFORE UPDATE ON auth_users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ROW-LEVEL SECURITY (RLS)
-- ============================================================================

-- Enable RLS on auth_users table
ALTER TABLE auth_users ENABLE ROW LEVEL SECURITY;

-- Placeholder policy: Allow all access for now
-- Will be replaced with proper JWT-based policies in MAS-28 (JWT Middleware)
CREATE POLICY "Allow all access to auth_users for now" 
    ON auth_users 
    FOR ALL 
    USING (true);

-- ============================================================================
-- DOCUMENTATION COMMENTS
-- ============================================================================

COMMENT ON TABLE auth_users IS 'Authentication credentials storage with 1:1 relationship to base_profiles. Separates auth concerns from profile data.';
COMMENT ON COLUMN auth_users.id IS 'Primary key - authentication user identifier';
COMMENT ON COLUMN auth_users.user_id IS 'Foreign key to base_profiles.user_id (UNIQUE for 1:1 relationship)';
COMMENT ON COLUMN auth_users.email IS 'Login email - should match base_profiles.primary_email for consistency';
COMMENT ON COLUMN auth_users.password_hash IS 'Argon2id hashed password - real hashing implementation in MAS-26 Auth Service';
COMMENT ON COLUMN auth_users.is_email_verified IS 'Email verification status - false until user clicks verification link';
COMMENT ON COLUMN auth_users.email_verified_at IS 'Timestamp when email was verified';
COMMENT ON COLUMN auth_users.verification_token IS 'Token sent via email for verification - expires after use or timeout';
COMMENT ON COLUMN auth_users.verification_token_expires_at IS 'Expiration timestamp for verification token (typically 24-48 hours)';
COMMENT ON COLUMN auth_users.last_login_at IS 'Timestamp of last successful login';
COMMENT ON COLUMN auth_users.failed_login_attempts IS 'Counter for failed login attempts - used for account lockout logic';
COMMENT ON COLUMN auth_users.locked_until IS 'Account locked until this timestamp - prevents brute force attacks';
COMMENT ON COLUMN auth_users.password_changed_at IS 'Timestamp of last password change - for security auditing';
COMMENT ON COLUMN auth_users.reset_token IS 'Password reset token sent via email';
COMMENT ON COLUMN auth_users.reset_token_expires_at IS 'Expiration timestamp for reset token (typically 1 hour)';
COMMENT ON COLUMN auth_users.created_at IS 'Account creation timestamp';
COMMENT ON COLUMN auth_users.updated_at IS 'Last update timestamp (auto-updated by trigger)';
COMMENT ON COLUMN auth_users.deleted_at IS 'Soft delete timestamp - enables 30-day grace period for account recovery';

