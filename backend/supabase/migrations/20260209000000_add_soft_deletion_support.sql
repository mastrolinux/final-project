-- ============================================================================
-- Migration: Soft Deletion Support (MAS-42)
-- Description: Add restoration token fields to auth_users for account
--   recovery after soft deletion. Add 'restore' to audit_operation enum.
-- ============================================================================

-- Add restoration token columns to auth_users
-- Follows the same pattern as reset_token and verification_token
ALTER TABLE auth_users
    ADD COLUMN IF NOT EXISTS restoration_token VARCHAR(255),
    ADD COLUMN IF NOT EXISTS restoration_token_expires_at TIMESTAMPTZ;

-- Partial index for restoration token lookups (only non-null tokens)
CREATE INDEX IF NOT EXISTS idx_auth_users_restoration_token
    ON auth_users(restoration_token)
    WHERE restoration_token IS NOT NULL;

-- Add 'restore' operation to audit_operation enum
ALTER TYPE audit_operation ADD VALUE IF NOT EXISTS 'restore';

-- ============================================================================
-- DOCUMENTATION
-- ============================================================================
COMMENT ON COLUMN auth_users.restoration_token IS
    'Time-limited token sent via email for account restoration after soft deletion';
COMMENT ON COLUMN auth_users.restoration_token_expires_at IS
    'Expiration timestamp for the restoration token (24-hour default)';
