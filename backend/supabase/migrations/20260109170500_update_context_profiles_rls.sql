-- Update Row-Level Security policies for context_profiles
-- Replace placeholder "allow all" with strict user-scoped policies
-- Part of Phase 2: Context Profiles security enhancement

-- Remove placeholder policy
DROP POLICY IF EXISTS "Allow all access to context_profiles for now" ON context_profiles;

-- Create strict RLS policies enforcing user-scoped access

-- SELECT: Users can only view their own context profiles
CREATE POLICY "Users can view own contexts" 
    ON context_profiles 
    FOR SELECT 
    USING (
        user_id::text = current_setting('request.jwt.claims', true)::json->>'sub'
    );

-- INSERT: Users can only create contexts for themselves
CREATE POLICY "Users can create own contexts" 
    ON context_profiles 
    FOR INSERT 
    WITH CHECK (
        user_id::text = current_setting('request.jwt.claims', true)::json->>'sub'
    );

-- UPDATE: Users can only update their own contexts
CREATE POLICY "Users can update own contexts" 
    ON context_profiles 
    FOR UPDATE 
    USING (
        user_id::text = current_setting('request.jwt.claims', true)::json->>'sub'
    );

-- DELETE: Users can only delete their own contexts (soft delete via application layer)
CREATE POLICY "Users can delete own contexts" 
    ON context_profiles 
    FOR DELETE 
    USING (
        user_id::text = current_setting('request.jwt.claims', true)::json->>'sub'
    );

-- Admin override policy for support and audit purposes
-- Allows users with 'admin' role to access all context profiles
CREATE POLICY "Admins can access all contexts"
    ON context_profiles
    FOR ALL
    USING (
        current_setting('request.jwt.claims', true)::jsonb->'roles' @> '"admin"'::jsonb
    );

COMMENT ON POLICY "Users can view own contexts" ON context_profiles IS 'RLS: Users can only SELECT their own context profiles';
COMMENT ON POLICY "Users can create own contexts" ON context_profiles IS 'RLS: Users can only INSERT contexts for themselves';
COMMENT ON POLICY "Users can update own contexts" ON context_profiles IS 'RLS: Users can only UPDATE their own contexts';
COMMENT ON POLICY "Users can delete own contexts" ON context_profiles IS 'RLS: Users can only DELETE their own contexts';
COMMENT ON POLICY "Admins can access all contexts" ON context_profiles IS 'RLS: Admin role can access all contexts for support/audit';

-- Rollback instructions:
-- To rollback to placeholder policy:
-- DROP POLICY "Users can view own contexts" ON context_profiles;
-- DROP POLICY "Users can create own contexts" ON context_profiles;
-- DROP POLICY "Users can update own contexts" ON context_profiles;
-- DROP POLICY "Users can delete own contexts" ON context_profiles;
-- DROP POLICY "Admins can access all contexts" ON context_profiles;
-- CREATE POLICY "Allow all access to context_profiles for now" ON context_profiles FOR ALL USING (true);
