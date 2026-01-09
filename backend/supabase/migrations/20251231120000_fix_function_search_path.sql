-- ============================================================================
-- FIX: Function Search Path Security
-- ============================================================================
-- Addresses Supabase linter warning: function_search_path_mutable
-- Setting search_path to empty string prevents search path injection attacks.
--
-- Reference: https://supabase.com/docs/guides/database/database-linter?lint=0011_function_search_path_mutable
-- ============================================================================

-- Recreate the function with security-hardened search_path
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- Add comment documenting the security fix
COMMENT ON FUNCTION public.update_updated_at_column() IS 
    'Trigger function to automatically update updated_at timestamp. '
    'Uses SET search_path = '''' for security (prevents search path injection).';
