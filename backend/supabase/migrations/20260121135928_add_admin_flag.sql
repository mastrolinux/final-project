-- Add admin flag to auth_users
-- Enables admin-only functionality like OAuth client management
-- Part of Phase 3: OAuth 2.1 Admin Features

-- Add is_admin column to auth_users table
ALTER TABLE auth_users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT false;

-- Create partial index for efficient admin lookups
-- Only indexes rows where is_admin is true (sparse index)
CREATE INDEX idx_auth_users_admin ON auth_users(is_admin) WHERE is_admin = true;

-- Add comment for documentation
COMMENT ON COLUMN auth_users.is_admin IS 'Admin flag - grants access to admin endpoints (OAuth client management, etc.)';

-- Update the seed data to make Sarah Chen an admin (for testing)
-- In production, admins should be set via ADMIN_USER_EMAILS env var or direct DB update
UPDATE auth_users 
SET is_admin = true 
WHERE email = 'sarah.chen@example.com';
