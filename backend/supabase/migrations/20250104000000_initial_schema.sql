-- Initial Schema Migration
-- Creates base_profiles and identity_names tables with proper indexes and constraints
-- Part of Identity and Profile Management API - Academic Thesis Project

-- Create enum types
CREATE TYPE account_type AS ENUM ('verified', 'unverified', 'pseudonymous');
CREATE TYPE name_type AS ENUM ('given', 'family', 'preferred', 'legal', 'patronymic', 'full_name', 'custom');
CREATE TYPE visibility_level AS ENUM ('public', 'private', 'historical_suppressed');

-- Base Profiles Table
-- Stores core user profile information
CREATE TABLE base_profiles (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_type account_type NOT NULL DEFAULT 'unverified',
    legal_name TEXT,  -- Optional: Only required for verified accounts
    primary_email TEXT NOT NULL,
    primary_phone TEXT,
    preferred_language TEXT NOT NULL DEFAULT 'en',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_to TIMESTAMPTZ
);

-- Identity Names Table
-- Stores multilingual name representations with JSONB flexibility
CREATE TABLE identity_names (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_id UUID NOT NULL REFERENCES base_profiles(user_id) ON DELETE CASCADE,
    name_type name_type NOT NULL,
    name_value JSONB NOT NULL,  -- Stores multilingual names: {"en": "John", "es": "Juan"}
    is_primary BOOLEAN NOT NULL DEFAULT false,
    is_deprecated BOOLEAN NOT NULL DEFAULT false,  -- For deadnames, historical names
    visibility_level visibility_level NOT NULL DEFAULT 'public',
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_to TIMESTAMPTZ,
    context_id UUID,  -- Future: Link to context_profiles
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for base_profiles
CREATE UNIQUE INDEX idx_base_profiles_email ON base_profiles(primary_email) WHERE deleted_at IS NULL;
CREATE INDEX idx_base_profiles_deleted ON base_profiles(deleted_at) WHERE deleted_at IS NOT NULL;
CREATE INDEX idx_base_profiles_account_type ON base_profiles(account_type);
CREATE INDEX idx_base_profiles_validity ON base_profiles(valid_from, valid_to);

-- Indexes for identity_names
CREATE INDEX idx_identity_names_identity_id ON identity_names(identity_id);
CREATE INDEX idx_identity_names_type ON identity_names(name_type);
CREATE INDEX idx_identity_names_primary ON identity_names(is_primary) WHERE is_primary = true;
CREATE INDEX idx_identity_names_deprecated ON identity_names(is_deprecated) WHERE is_deprecated = true;
CREATE INDEX idx_identity_names_value_gin ON identity_names USING GIN(name_value);
CREATE INDEX idx_identity_names_validity ON identity_names(valid_from, valid_to);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers to auto-update updated_at
CREATE TRIGGER update_base_profiles_updated_at
    BEFORE UPDATE ON base_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_identity_names_updated_at
    BEFORE UPDATE ON identity_names
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Row-Level Security (RLS) Policies
-- Enable RLS on tables (policies to be implemented when auth is ready)
ALTER TABLE base_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity_names ENABLE ROW LEVEL SECURITY;

-- Placeholder policy: Allow all for now (will be restricted with Supabase Auth)
CREATE POLICY "Allow all access to base_profiles for now" ON base_profiles FOR ALL USING (true);
CREATE POLICY "Allow all access to identity_names for now" ON identity_names FOR ALL USING (true);

-- Comments for documentation
COMMENT ON TABLE base_profiles IS 'Core user profiles with account type distinction (verified/unverified/pseudonymous)';
COMMENT ON COLUMN base_profiles.legal_name IS 'Optional legal name - only required for verified accounts accessing legal/healthcare contexts';
COMMENT ON COLUMN base_profiles.account_type IS 'Account verification level: verified (full access), unverified (limited), pseudonymous (minimal)';
COMMENT ON TABLE identity_names IS 'Multilingual name storage supporting diverse cultural naming conventions via JSONB';
COMMENT ON COLUMN identity_names.name_value IS 'JSONB field storing name in multiple languages/scripts, e.g., {"en": "John", "zh": "约翰"}';
COMMENT ON COLUMN identity_names.is_deprecated IS 'Marks names as deprecated (e.g., deadnames) to prevent display in public contexts';
COMMENT ON COLUMN identity_names.visibility_level IS 'Controls visibility: public, private, or historical_suppressed';

