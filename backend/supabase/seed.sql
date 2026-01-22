-- Seed Data for Local Development
-- Creates sample profiles and identity names for testing
-- Part of Identity and Profile Management API - Academic Thesis Project

-- Clear existing data (for reset)
-- Note: Tables must be truncated in dependency order (children first)
TRUNCATE TABLE oauth_consents CASCADE;
TRUNCATE TABLE oauth_refresh_tokens CASCADE;
TRUNCATE TABLE oauth_access_tokens CASCADE;
TRUNCATE TABLE oauth_authorization_codes CASCADE;
TRUNCATE TABLE oauth_clients CASCADE;
TRUNCATE TABLE auth_users CASCADE;
TRUNCATE TABLE context_profiles CASCADE;
TRUNCATE TABLE identity_names CASCADE;
TRUNCATE TABLE base_profiles CASCADE;

-- Sample Profile 1: Verified Account (Western naming convention)
INSERT INTO base_profiles (user_id, account_type, legal_name, primary_email, primary_phone, preferred_language)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'verified',
    'Sarah Elizabeth Chen',
    'sarah.chen@example.com',
    '+1-555-0101',
    'en'
);

-- Names for Sarah Chen
INSERT INTO identity_names (id, identity_id, name_type, name_value, is_primary, is_deprecated, visibility_level)
VALUES
    (
        '10000000-0000-0000-0000-000000000001',
        '00000000-0000-0000-0000-000000000001',
        'given',
        '{"en": "Sarah"}'::jsonb,
        true,
        false,
        'public'
    ),
    (
        '10000000-0000-0000-0000-000000000002',
        '00000000-0000-0000-0000-000000000001',
        'family',
        '{"en": "Chen"}'::jsonb,
        true,
        false,
        'public'
    ),
    (
        '10000000-0000-0000-0000-000000000003',
        '00000000-0000-0000-0000-000000000001',
        'full_name',
        '{"en": "Dr. Sarah Chen"}'::jsonb,
        true,
        false,
        'public'
    );

-- Sample Profile 2: Unverified Account (Chinese naming convention with multilingual)
INSERT INTO base_profiles (user_id, account_type, legal_name, primary_email, primary_phone, preferred_language)
VALUES (
    '00000000-0000-0000-0000-000000000002',
    'unverified',
    NULL,
    'li.ming@example.com',
    '+86-555-0202',
    'zh'
);

-- Names for Li Ming (Chinese family-first ordering with romanization)
INSERT INTO identity_names (id, identity_id, name_type, name_value, is_primary, is_deprecated, visibility_level)
VALUES
    (
        '10000000-0000-0000-0000-000000000004',
        '00000000-0000-0000-0000-000000000002',
        'family',
        '{"zh": "李", "zh-Latn": "Li", "en": "Li"}'::jsonb,
        true,
        false,
        'public'
    ),
    (
        '10000000-0000-0000-0000-000000000005',
        '00000000-0000-0000-0000-000000000002',
        'given',
        '{"zh": "明", "zh-Latn": "Ming", "en": "Ming"}'::jsonb,
        true,
        false,
        'public'
    ),
    (
        '10000000-0000-0000-0000-000000000006',
        '00000000-0000-0000-0000-000000000002',
        'full_name',
        '{"zh": "李明", "en": "Li Ming"}'::jsonb,
        true,
        false,
        'public'
    );

-- Sample Profile 3: Pseudonymous Account (vulnerable population, minimal data)
INSERT INTO base_profiles (user_id, account_type, legal_name, primary_email, primary_phone, preferred_language)
VALUES (
    '00000000-0000-0000-0000-000000000003',
    'pseudonymous',
    NULL,
    'alex.anonymous@protonmail.com',
    NULL,
    'en'
);

-- Names for Alex (pseudonymous, preferred name only)
INSERT INTO identity_names (id, identity_id, name_type, name_value, is_primary, is_deprecated, visibility_level)
VALUES
    (
        '10000000-0000-0000-0000-000000000007',
        '00000000-0000-0000-0000-000000000003',
        'preferred',
        '{"en": "Alex"}'::jsonb,
        true,
        false,
        'private'
    ),
    (
        '10000000-0000-0000-0000-000000000008',
        '00000000-0000-0000-0000-000000000003',
        'full_name',
        '{"en": "Alex"}'::jsonb,
        true,
        false,
        'private'
    );

-- Sample Profile 4: Mononym (Indonesian naming convention)
INSERT INTO base_profiles (user_id, account_type, legal_name, primary_email, primary_phone, preferred_language)
VALUES (
    '00000000-0000-0000-0000-000000000004',
    'verified',
    'Sukarno',
    'sukarno@example.id',
    '+62-555-0303',
    'id'
);

-- Names for Sukarno (mononym - single name)
INSERT INTO identity_names (id, identity_id, name_type, name_value, is_primary, is_deprecated, visibility_level)
VALUES
    (
        '10000000-0000-0000-0000-000000000009',
        '00000000-0000-0000-0000-000000000004',
        'full_name',
        '{"id": "Sukarno", "en": "Sukarno"}'::jsonb,
        true,
        false,
        'public'
    );

-- Sample Profile 5: Example with deprecated name (name change scenario)
INSERT INTO base_profiles (user_id, account_type, legal_name, primary_email, primary_phone, preferred_language)
VALUES (
    '00000000-0000-0000-0000-000000000005',
    'verified',
    'Jordan Taylor Smith',
    'jordan.smith@example.com',
    '+1-555-0404',
    'en'
);

-- Names for Jordan (includes deprecated deadname)
INSERT INTO identity_names (id, identity_id, name_type, name_value, is_primary, is_deprecated, visibility_level)
VALUES
    -- Current preferred name
    (
        '10000000-0000-0000-0000-000000000010',
        '00000000-0000-0000-0000-000000000005',
        'preferred',
        '{"en": "Jordan"}'::jsonb,
        true,
        false,
        'public'
    ),
    -- Current full name
    (
        '10000000-0000-0000-0000-000000000011',
        '00000000-0000-0000-0000-000000000005',
        'full_name',
        '{"en": "Jordan Taylor Smith"}'::jsonb,
        true,
        false,
        'public'
    ),
    -- Deprecated deadname (historical, suppressed)
    (
        '10000000-0000-0000-0000-000000000012',
        '00000000-0000-0000-0000-000000000005',
        'given',
        '{"en": "[REDACTED]"}'::jsonb,
        false,
        true,
        'historical_suppressed'
    );

-- ============================================================================
-- CONTEXT PROFILES - Multi-Context Identity Presentation
-- ============================================================================
-- Demonstrates Goffman's dramaturgical theory: context-dependent identity

-- Context 1: Sarah Chen's Professional Context (Psychiatrist at work)
INSERT INTO context_profiles (id, user_id, context_type, context_name, display_name_override, email_override, phone_override, bio, is_active)
VALUES (
    '20000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001',  -- Sarah Chen
    'professional',
    'Hospital Network',
    'Dr. Sarah Chen, MD, PhD',
    's.chen@hospital.org',
    '+1-555-0100',
    'Board-certified psychiatrist specializing in trauma and PTSD. Over 15 years of clinical experience.',
    true
);

-- Context 2: Sarah Chen's Social Context (Fitness apps, personal use)
INSERT INTO context_profiles (id, user_id, context_type, context_name, display_name_override, email_override, phone_override, bio, is_active)
VALUES (
    '20000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000001',  -- Sarah Chen
    'social',
    'Fitness Apps',
    'Sarah',
    NULL,  -- Inherits primary_email from base profile
    NULL,  -- Inherits primary_phone from base profile
    'Health and wellness enthusiast. Loves running and yoga.',
    true
);

-- Context 3: Li Ming's Professional Context (Software engineer)
INSERT INTO context_profiles (id, user_id, context_type, context_name, display_name_override, email_override, phone_override, bio, is_active)
VALUES (
    '20000000-0000-0000-0000-000000000003',
    '00000000-0000-0000-0000-000000000002',  -- Li Ming
    'professional',
    'LinkedIn',
    'Ming Li',  -- Western order for international context
    'ming.li@techcorp.com',
    NULL,
    'Senior Software Engineer specializing in distributed systems and cloud architecture.',
    true
);

-- Context 4: Jordan's Social Context (LGBTQ+ support groups)
INSERT INTO context_profiles (id, user_id, context_type, context_name, display_name_override, email_override, phone_override, bio, is_active)
VALUES (
    '20000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000005',  -- Jordan
    'social',
    'Support Communities',
    'Jordan (they/them)',
    NULL,
    NULL,
    'Advocate for transgender rights. Always happy to help others on their journey.',
    true
);

-- Context 5: Jordan's Legal Context (Government services)
INSERT INTO context_profiles (id, user_id, context_type, context_name, display_name_override, email_override, phone_override, bio, is_active)
VALUES (
    '20000000-0000-0000-0000-000000000005',
    '00000000-0000-0000-0000-000000000005',  -- Jordan
    'legal',
    'Government ID',
    'Jordan Taylor Smith',  -- Legal name for official documents
    NULL,
    NULL,
    NULL,
    true
);

-- Note: Alex (pseudonymous profile) cannot create legal/healthcare contexts
-- This demonstrates the business rule preventing pseudonymous accounts from
-- accessing sensitive context types

-- ============================================================================
-- AUTHENTICATION USERS - Credentials for Auth System
-- ============================================================================
-- Creates auth_users entries matching the 5 base_profiles above
-- Password hashes are FAKE placeholders - real Argon2id hashing in MAS-26 Auth Service
-- Verification tokens are STUB values - real token generation in MAS-26

INSERT INTO auth_users (
    id, 
    user_id, 
    email, 
    password_hash, 
    is_email_verified, 
    email_verified_at,
    verification_token,
    verification_token_expires_at,
    password_changed_at,
    is_admin
) VALUES
    -- 1. Sarah Chen - Email verified, verified account, ADMIN
    -- Password: SecurePass123! (real hash for Postman testing)
    (
        '30000000-0000-0000-0000-000000000001',
        '00000000-0000-0000-0000-000000000001',
        'sarah.chen@example.com',
        '$argon2id$v=19$m=65536,t=3,p=4$3Fur1ZpTCoGQktLa29v7Pw$D1hdsnORIBpEEjq+SNTrDBiny0oz4H2+MqH0B9MSWCs',
        true,  -- Email verified
        '2024-10-15 10:00:00+00',  -- Verified timestamp
        NULL,  -- No token needed (already verified)
        NULL,
        '2024-10-15 09:00:00+00',
        true   -- Admin user for testing
    ),
    -- 2. Li Ming - Email NOT verified, unverified account with stub token
    (
        '30000000-0000-0000-0000-000000000002',
        '00000000-0000-0000-0000-000000000002',
        'li.ming@example.com',
        '$argon2id$v=19$m=65536,t=3,p=4$FAKE_SALT_LIMING$FAKE_HASH_PLACEHOLDER',
        false,  -- Email NOT verified
        NULL,
        'stub-verification-token-li-ming-001',  -- Stub token for testing
        '2026-12-31 23:59:59+00',  -- Far-future expiry for testing
        '2024-11-01 12:00:00+00',
        false
    ),
    -- 3. Alex - Email verified, pseudonymous account
    (
        '30000000-0000-0000-0000-000000000003',
        '00000000-0000-0000-0000-000000000003',
        'alex.anonymous@protonmail.com',
        '$argon2id$v=19$m=65536,t=3,p=4$FAKE_SALT_ALEX$FAKE_HASH_PLACEHOLDER',
        true,  -- Email verified (privacy-focused users verify)
        '2024-09-20 14:30:00+00',
        NULL,
        NULL,
        '2024-09-20 14:00:00+00',
        false
    ),
    -- 4. Sukarno - Email verified, verified account
    (
        '30000000-0000-0000-0000-000000000004',
        '00000000-0000-0000-0000-000000000004',
        'sukarno@example.id',
        '$argon2id$v=19$m=65536,t=3,p=4$FAKE_SALT_SUKARNO$FAKE_HASH_PLACEHOLDER',
        true,  -- Email verified
        '2024-08-10 08:00:00+00',
        NULL,
        NULL,
        '2024-08-10 07:30:00+00',
        false
    ),
    -- 5. Jordan Smith - Email verified, verified account
    (
        '30000000-0000-0000-0000-000000000005',
        '00000000-0000-0000-0000-000000000005',
        'jordan.smith@example.com',
        '$argon2id$v=19$m=65536,t=3,p=4$FAKE_SALT_JORDAN$FAKE_HASH_PLACEHOLDER',
        true,  -- Email verified
        '2024-07-15 16:45:00+00',
        NULL,
        NULL,
        '2024-07-15 16:00:00+00',
        false
    );

-- ============================================================================
-- OAUTH CLIENTS - Third-Party Application Registrations
-- ============================================================================
-- Sample OAuth clients for testing OAuth 2.1 flows

-- Client 1: First-party web application (confidential, skips consent)
INSERT INTO oauth_clients (
    client_id,
    client_secret_hash,
    client_name,
    client_description,
    client_uri,
    logo_uri,
    redirect_uris,
    allowed_scopes,
    default_context_type,
    is_confidential,
    is_active,
    is_first_party,
    token_endpoint_auth_method
) VALUES (
    'thesis-web-app',
    '$argon2id$v=19$m=65536,t=3,p=4$FAKE_SALT_CLIENT1$FAKE_SECRET_HASH',
    'Thesis Identity Portal',
    'First-party web application for identity management',
    'http://localhost:3000',
    NULL,
    ARRAY['http://localhost:3000/callback', 'http://localhost:3000/auth/callback'],
    ARRAY['openid', 'profile:read:basic', 'profile:read:full', 'profile:write', 'contexts:read', 'offline_access'],
    NULL,
    true,  -- Confidential client
    true,
    true,  -- First-party, skip consent
    'client_secret_post'
);

-- Client 2: Third-party professional networking app (confidential, requires consent)
INSERT INTO oauth_clients (
    client_id,
    client_secret_hash,
    client_name,
    client_description,
    client_uri,
    logo_uri,
    redirect_uris,
    allowed_scopes,
    default_context_type,
    is_confidential,
    is_active,
    is_first_party,
    token_endpoint_auth_method
) VALUES (
    'linkedin-demo',
    '$argon2id$v=19$m=65536,t=3,p=4$FAKE_SALT_CLIENT2$FAKE_SECRET_HASH',
    'LinkedIn Demo Integration',
    'Professional networking integration demonstrating context-aware identity',
    'https://linkedin-demo.example.com',
    'https://linkedin-demo.example.com/logo.png',
    ARRAY['https://linkedin-demo.example.com/callback'],
    ARRAY['openid', 'profile:read:basic', 'profile:read:email', 'contexts:professional:read'],
    'professional',  -- Default to professional context
    true,
    true,
    false,  -- Third-party, requires consent
    'client_secret_basic'
);

-- Client 3: Mobile fitness app (public client, PKCE-only)
INSERT INTO oauth_clients (
    client_id,
    client_secret_hash,
    client_name,
    client_description,
    client_uri,
    logo_uri,
    redirect_uris,
    allowed_scopes,
    default_context_type,
    is_confidential,
    is_active,
    is_first_party,
    token_endpoint_auth_method
) VALUES (
    'fitness-app-mobile',
    NULL,  -- Public client, no secret
    'FitTrack Mobile',
    'Mobile fitness tracking app requesting social context profile',
    'https://fittrack.example.com',
    'https://fittrack.example.com/icon.png',
    ARRAY['fittrack://callback', 'https://fittrack.example.com/oauth/callback'],
    ARRAY['openid', 'profile:read:basic', 'contexts:social:read'],
    'social',  -- Default to social context
    false,  -- Public client
    true,
    false,  -- Third-party
    'none'  -- No client authentication, PKCE only
);

-- Client 4: Healthcare portal (confidential, requires verification and consent)
INSERT INTO oauth_clients (
    client_id,
    client_secret_hash,
    client_name,
    client_description,
    client_uri,
    logo_uri,
    redirect_uris,
    allowed_scopes,
    default_context_type,
    is_confidential,
    is_active,
    is_first_party,
    token_endpoint_auth_method
) VALUES (
    'healthcare-portal',
    '$argon2id$v=19$m=65536,t=3,p=4$FAKE_SALT_CLIENT4$FAKE_SECRET_HASH',
    'SecureHealth Portal',
    'Healthcare provider portal requiring verified identity and healthcare context',
    'https://securehealth.example.com',
    'https://securehealth.example.com/logo.png',
    ARRAY['https://securehealth.example.com/oauth/callback'],
    ARRAY['openid', 'profile:read:full', 'contexts:healthcare:read', 'offline_access'],
    'healthcare',  -- Healthcare context
    true,
    true,
    false,
    'client_secret_post'
);

-- Client 5: Inactive/deactivated client (for testing inactive client handling)
INSERT INTO oauth_clients (
    client_id,
    client_secret_hash,
    client_name,
    client_description,
    client_uri,
    logo_uri,
    redirect_uris,
    allowed_scopes,
    default_context_type,
    is_confidential,
    is_active,
    is_first_party,
    token_endpoint_auth_method
) VALUES (
    'deactivated-client',
    '$argon2id$v=19$m=65536,t=3,p=4$FAKE_SALT_INACTIVE$FAKE_SECRET_HASH',
    'Deprecated Application',
    'This client has been deactivated for testing',
    'https://deprecated.example.com',
    NULL,
    ARRAY['https://deprecated.example.com/callback'],
    ARRAY['profile:read:basic'],
    NULL,
    true,
    false,  -- INACTIVE
    false,
    'client_secret_post'
);

-- ============================================================================
-- OAUTH CONSENTS - Sample User Consent Records
-- ============================================================================
-- Pre-granted consents for testing token flows

-- Sarah Chen has granted consent to LinkedIn Demo for professional context
INSERT INTO oauth_consents (
    id,
    user_id,
    client_id,
    granted_scopes,
    context_profile_id,
    granted_at,
    expires_at,
    withdrawn_at,
    consent_method,
    ip_address,
    user_agent
) VALUES (
    '40000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001',  -- Sarah Chen
    'linkedin-demo',
    ARRAY['openid', 'profile:read:basic', 'profile:read:email', 'contexts:professional:read'],
    '20000000-0000-0000-0000-000000000001',  -- Sarah's professional context
    '2026-01-10 10:00:00+00',
    NULL,  -- No expiry
    NULL,  -- Not withdrawn
    'explicit',
    '192.168.1.100',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
);

-- Sarah Chen has granted consent to FitTrack for social context
INSERT INTO oauth_consents (
    id,
    user_id,
    client_id,
    granted_scopes,
    context_profile_id,
    granted_at,
    expires_at,
    withdrawn_at,
    consent_method,
    ip_address,
    user_agent
) VALUES (
    '40000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000001',  -- Sarah Chen
    'fitness-app-mobile',
    ARRAY['openid', 'profile:read:basic', 'contexts:social:read'],
    '20000000-0000-0000-0000-000000000002',  -- Sarah's social context
    '2026-01-11 14:30:00+00',
    NULL,
    NULL,
    'explicit',
    '10.0.0.1',
    'FitTrack/2.0 (iOS; iPhone14,2)'
);

-- Jordan has withdrawn consent from a client (for testing withdrawal)
INSERT INTO oauth_consents (
    id,
    user_id,
    client_id,
    granted_scopes,
    context_profile_id,
    granted_at,
    expires_at,
    withdrawn_at,
    consent_method,
    ip_address,
    user_agent
) VALUES (
    '40000000-0000-0000-0000-000000000003',
    '00000000-0000-0000-0000-000000000005',  -- Jordan
    'linkedin-demo',
    ARRAY['openid', 'profile:read:basic'],
    NULL,
    '2025-12-01 09:00:00+00',
    NULL,
    '2025-12-15 11:30:00+00',  -- Consent withdrawn
    'explicit',
    '192.168.1.200',
    'Mozilla/5.0'
);

-- ============================================================================
-- Verification queries (useful for checking seed data loaded correctly)
-- ============================================================================
-- SELECT COUNT(*) FROM base_profiles;      -- Should return 5
-- SELECT COUNT(*) FROM identity_names;     -- Should return 12
-- SELECT COUNT(*) FROM context_profiles;   -- Should return 5
-- SELECT COUNT(*) FROM auth_users;         -- Should return 5
-- SELECT COUNT(*) FROM oauth_clients;      -- Should return 5
-- SELECT COUNT(*) FROM oauth_consents;     -- Should return 3

-- Test auth_users to base_profiles relationship:
-- SELECT 
--   au.email,
--   bp.primary_email,
--   bp.account_type,
--   au.is_email_verified,
--   au.verification_token
-- FROM auth_users au
-- JOIN base_profiles bp ON au.user_id = bp.user_id;

-- Test inheritance engine:
-- SELECT 
--   bp.primary_email as base_email,
--   cp.email_override as context_email,
--   COALESCE(cp.email_override, bp.primary_email) as resolved_email
-- FROM context_profiles cp
-- JOIN base_profiles bp ON cp.user_id = bp.user_id
-- WHERE cp.context_name = 'Fitness Apps';

