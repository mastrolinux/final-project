-- Add 'family' and 'custom' to context_type enum
-- Supports family sharing and flexible custom contexts
-- Part of Phase 2: Context Profiles enhancement

-- Add 'family' context type for family-specific identity contexts
ALTER TYPE context_type ADD VALUE IF NOT EXISTS 'family';

-- Add 'custom' context type for user-defined contexts beyond standard types
ALTER TYPE context_type ADD VALUE IF NOT EXISTS 'custom';

-- Update table comment to reflect new context types
COMMENT ON TYPE context_type IS 'Type of social context: professional, social, legal, healthcare, family, or custom';

-- Rollback instructions:
-- PostgreSQL does not support removing enum values after they're added.
-- To rollback, we would need to:
-- 1. Remove all context_profiles using these values
-- 2. Drop and recreate the enum with old values
-- 3. Recreate the context_profiles table
-- This is destructive, so plan carefully before applying.
