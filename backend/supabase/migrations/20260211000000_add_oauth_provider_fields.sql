-- Migration: Add OAuth provider fields to auth_users table
-- Description: Adds provider and provider_id fields to support social login
-- Author: Identity Management System
-- Date: 2026-02-11

-- Add OAuth provider fields to auth_users table
ALTER TABLE auth_users
ADD COLUMN IF NOT EXISTS provider VARCHAR(50),
ADD COLUMN IF NOT EXISTS provider_id VARCHAR(255);

-- Create unique index on provider + provider_id combination
-- This prevents duplicate OAuth accounts from the same provider
-- Partial index excludes NULL values (email/password users)
CREATE UNIQUE INDEX IF NOT EXISTS idx_auth_users_provider_id
ON auth_users (provider, provider_id)
WHERE provider IS NOT NULL AND provider_id IS NOT NULL;

-- Create index for faster provider lookups
CREATE INDEX IF NOT EXISTS idx_auth_users_provider
ON auth_users (provider)
WHERE provider IS NOT NULL;

-- Add comment to document the fields
COMMENT ON COLUMN auth_users.provider IS 'OAuth provider name (google, github, etc.). NULL for email/password users.';
COMMENT ON COLUMN auth_users.provider_id IS 'Provider-specific user identifier (e.g., Google sub claim). NULL for email/password users.';

-- Note: password_hash will remain NOT NULL for now, but OAuth users will have a random hash
-- This maintains backward compatibility without schema changes
