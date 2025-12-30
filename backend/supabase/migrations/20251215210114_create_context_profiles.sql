-- Context Profiles Migration
-- Implements multi-context identity presentation supporting Goffman's dramaturgical theory
-- Part of Identity and Profile Management API - Academic Thesis Project

-- Create context_type enum
CREATE TYPE context_type AS ENUM ('professional', 'social', 'legal', 'healthcare');

-- Context Profiles Table
-- Stores context-specific profile overrides that inherit from base profiles
-- Only override fields are stored; resolution merges with base profile
CREATE TABLE context_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES base_profiles(user_id) ON DELETE CASCADE,
    context_type context_type NOT NULL,
    context_name TEXT NOT NULL,  -- User-defined label like "Work", "LinkedIn", "Family"
    
    -- Override fields (nullable - only store if different from base)
    display_name_override TEXT,
    email_override TEXT,
    phone_override TEXT,
    bio TEXT,  -- Context-specific biography
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT true,
    
    -- Standard mixins
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_to TIMESTAMPTZ,
    
    -- Ensure unique context per user
    CONSTRAINT unique_user_context UNIQUE(user_id, context_type, context_name)
);

-- Indexes for context_profiles
CREATE INDEX idx_context_profiles_user_id ON context_profiles(user_id);
CREATE INDEX idx_context_profiles_type ON context_profiles(context_type);
CREATE INDEX idx_context_profiles_active ON context_profiles(is_active) WHERE is_active = true;
CREATE INDEX idx_context_profiles_deleted ON context_profiles(deleted_at) WHERE deleted_at IS NOT NULL;
CREATE INDEX idx_context_profiles_validity ON context_profiles(valid_from, valid_to);

-- Composite index for efficient context lookup
CREATE INDEX idx_context_profiles_user_type_name ON context_profiles(user_id, context_type, context_name) WHERE deleted_at IS NULL;

-- Trigger to auto-update updated_at
CREATE TRIGGER update_context_profiles_updated_at
    BEFORE UPDATE ON context_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Row-Level Security (RLS)
ALTER TABLE context_profiles ENABLE ROW LEVEL SECURITY;

-- Placeholder policy: Allow all for now (will be restricted with authentication)
CREATE POLICY "Allow all access to context_profiles for now" ON context_profiles FOR ALL USING (true);

-- Comments for documentation
COMMENT ON TABLE context_profiles IS 'Context-specific profile overrides enabling multi-context identity presentation (Goffman dramaturgical theory)';
COMMENT ON COLUMN context_profiles.context_type IS 'Type of social context: professional, social, legal, or healthcare';
COMMENT ON COLUMN context_profiles.context_name IS 'User-defined label for this context (e.g., "LinkedIn", "Family Photos", "Medical Records")';
COMMENT ON COLUMN context_profiles.display_name_override IS 'Override display name for this context (null inherits from base profile)';
COMMENT ON COLUMN context_profiles.email_override IS 'Override email for this context (null inherits from base profile)';
COMMENT ON COLUMN context_profiles.bio IS 'Context-specific biography or description';
COMMENT ON COLUMN context_profiles.is_active IS 'Whether this context profile is currently active';

-- Constraint: Pseudonymous accounts cannot create legal or healthcare contexts
-- This will be enforced at the service layer for flexibility







