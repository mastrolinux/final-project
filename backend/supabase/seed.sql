SET session_replication_role = replica;

-- ============================================================================
-- SEED DATA for Identity and Profile Management API
-- ============================================================================
-- Populates the database with test data for manual testing, Postman runs,
-- and OAuth 2.1 endpoint validation.
--
-- Deterministic UUIDs allow downstream tables to reference profiles and
-- contexts without subqueries. All passwords are TestPassword123!
--
-- session_replication_role = replica disables triggers and RLS during seeding.
--
-- This file is idempotent: it deletes any pre-existing seed rows before
-- reinserting them, so it can be run multiple times safely.
-- ============================================================================


-- ============================================================================
-- 0. CLEANUP (reverse dependency order for idempotency)
-- ============================================================================

DELETE FROM oauth_consents WHERE id IN (
    'dddddddd-0001-0001-0001-dddddddddddd',
    'dddddddd-0002-0001-0002-dddddddddddd'
);

DELETE FROM oauth_clients WHERE client_id IN (
    'hr-portal', 'social-connect', 'legal-verify',
    'health-records', 'family-tree', 'custom-app', 'oauth-debugger'
);

DELETE FROM context_profiles WHERE id IN (
    'cccccccc-0001-0001-0001-cccccccccccc',
    'cccccccc-0001-0002-0001-cccccccccccc',
    'cccccccc-0002-0001-0002-cccccccccccc',
    'cccccccc-0002-0002-0002-cccccccccccc',
    'cccccccc-0005-0001-0005-cccccccccccc',
    'cccccccc-0005-0002-0005-cccccccccccc'
);

DELETE FROM auth_users WHERE user_id IN (
    '11111111-1111-1111-1111-111111111111',
    '22222222-2222-2222-2222-222222222222',
    '33333333-3333-3333-3333-333333333333',
    '44444444-4444-4444-4444-444444444444',
    '55555555-5555-5555-5555-555555555555'
);

DELETE FROM identity_names WHERE identity_id IN (
    '11111111-1111-1111-1111-111111111111',
    '22222222-2222-2222-2222-222222222222',
    '33333333-3333-3333-3333-333333333333',
    '44444444-4444-4444-4444-444444444444',
    '55555555-5555-5555-5555-555555555555'
);

DELETE FROM base_profiles WHERE user_id IN (
    '11111111-1111-1111-1111-111111111111',
    '22222222-2222-2222-2222-222222222222',
    '33333333-3333-3333-3333-333333333333',
    '44444444-4444-4444-4444-444444444444',
    '55555555-5555-5555-5555-555555555555'
);


-- ============================================================================
-- 1. BASE PROFILES (5 personas)
-- ============================================================================

INSERT INTO base_profiles (user_id, account_type, legal_name, primary_email, primary_phone, preferred_language, created_at, updated_at, valid_from) VALUES
    -- Sarah Chen: verified, admin, professional + legal contexts
    ('11111111-1111-1111-1111-111111111111', 'verified', 'Sarah Chen', 'sarah.chen@example.com', '+1-555-0101', 'en',
     NOW(), NOW(), NOW()),
    -- Li Ming: unverified, multilingual (en + zh), social + healthcare contexts
    ('22222222-2222-2222-2222-222222222222', 'unverified', NULL, 'li.ming@example.com', '+86-10-5550-0102', 'zh',
     NOW(), NOW(), NOW()),
    -- Alex: pseudonymous, no legal name
    ('33333333-3333-3333-3333-333333333333', 'pseudonymous', NULL, 'alex.shadow@example.com', NULL, 'en',
     NOW(), NOW(), NOW()),
    -- Sukarno: verified, mononym (single name)
    ('44444444-4444-4444-4444-444444444444', 'verified', 'Sukarno', 'sukarno@example.com', '+62-21-5550-0104', 'id',
     NOW(), NOW(), NOW()),
    -- Jordan Smith: verified, name-change scenario, family + custom contexts
    ('55555555-5555-5555-5555-555555555555', 'verified', 'Jordan Smith', 'jordan.smith@example.com', '+1-555-0105', 'en',
     NOW(), NOW(), NOW());


-- ============================================================================
-- 2. IDENTITY NAMES (multilingual JSONB)
-- ============================================================================

INSERT INTO identity_names (id, identity_id, name_type, name_value, is_primary, is_deprecated, visibility_level, valid_from) VALUES
    -- Sarah Chen
    ('aaaaaaaa-0001-0001-0001-aaaaaaaaaaaa', '11111111-1111-1111-1111-111111111111', 'preferred',
     '{"en": "Sarah"}', true, false, 'public', NOW()),
    ('aaaaaaaa-0001-0002-0001-aaaaaaaaaaaa', '11111111-1111-1111-1111-111111111111', 'family',
     '{"en": "Chen"}', false, false, 'public', NOW()),
    ('aaaaaaaa-0001-0003-0001-aaaaaaaaaaaa', '11111111-1111-1111-1111-111111111111', 'given',
     '{"en": "Sarah"}', false, false, 'public', NOW()),

    -- Li Ming (multilingual: en + zh)
    ('aaaaaaaa-0002-0001-0002-aaaaaaaaaaaa', '22222222-2222-2222-2222-222222222222', 'preferred',
     '{"en": "Li Ming", "zh": "李明"}', true, false, 'public', NOW()),
    ('aaaaaaaa-0002-0002-0002-aaaaaaaaaaaa', '22222222-2222-2222-2222-222222222222', 'family',
     '{"en": "Li", "zh": "李"}', false, false, 'public', NOW()),
    ('aaaaaaaa-0002-0003-0002-aaaaaaaaaaaa', '22222222-2222-2222-2222-222222222222', 'given',
     '{"en": "Ming", "zh": "明"}', false, false, 'public', NOW()),

    -- Alex (pseudonymous, single language)
    ('aaaaaaaa-0003-0001-0003-aaaaaaaaaaaa', '33333333-3333-3333-3333-333333333333', 'preferred',
     '{"en": "Alex"}', true, false, 'public', NOW()),

    -- Sukarno (mononym)
    ('aaaaaaaa-0004-0001-0004-aaaaaaaaaaaa', '44444444-4444-4444-4444-444444444444', 'preferred',
     '{"en": "Sukarno", "id": "Sukarno"}', true, false, 'public', NOW()),
    ('aaaaaaaa-0004-0002-0004-aaaaaaaaaaaa', '44444444-4444-4444-4444-444444444444', 'full_name',
     '{"en": "Sukarno", "id": "Sukarno"}', false, false, 'public', NOW()),

    -- Jordan Smith (with deprecated former name)
    ('aaaaaaaa-0005-0001-0005-aaaaaaaaaaaa', '55555555-5555-5555-5555-555555555555', 'preferred',
     '{"en": "Jordan"}', true, false, 'public', NOW()),
    ('aaaaaaaa-0005-0002-0005-aaaaaaaaaaaa', '55555555-5555-5555-5555-555555555555', 'family',
     '{"en": "Smith"}', false, false, 'public', NOW()),
    ('aaaaaaaa-0005-0003-0005-aaaaaaaaaaaa', '55555555-5555-5555-5555-555555555555', 'given',
     '{"en": "Jordan"}', false, false, 'public', NOW()),
    ('aaaaaaaa-0005-0004-0005-aaaaaaaaaaaa', '55555555-5555-5555-5555-555555555555', 'given',
     '{"en": "Jamie"}', false, true, 'historical_suppressed', NOW());


-- ============================================================================
-- 3. AUTH USERS (1:1 with base_profiles, password: TestPassword123!)
-- ============================================================================
-- Argon2id hash generated with memory_cost=65536, time_cost=3, parallelism=4

INSERT INTO auth_users (id, user_id, email, password_hash, is_email_verified, email_verified_at, is_admin, has_custom_password, password_changed_at, created_at, updated_at) VALUES
    ('bbbbbbbb-0001-0001-0001-bbbbbbbbbbbb', '11111111-1111-1111-1111-111111111111',
     'sarah.chen@example.com',
     '$argon2id$v=19$m=65536,t=3,p=4$IkSIkdLaGyPEuHcu5RwjBA$Ye4MN7Ey9RCTSkS2JeGYcV0YtX8Te2IpJDMuASO0AIY',
     true, NOW(), true, true, NOW(), NOW(), NOW()),

    ('bbbbbbbb-0002-0002-0002-bbbbbbbbbbbb', '22222222-2222-2222-2222-222222222222',
     'li.ming@example.com',
     '$argon2id$v=19$m=65536,t=3,p=4$IkSIkdLaGyPEuHcu5RwjBA$Ye4MN7Ey9RCTSkS2JeGYcV0YtX8Te2IpJDMuASO0AIY',
     true, NOW(), false, true, NOW(), NOW(), NOW()),

    ('bbbbbbbb-0003-0003-0003-bbbbbbbbbbbb', '33333333-3333-3333-3333-333333333333',
     'alex.shadow@example.com',
     '$argon2id$v=19$m=65536,t=3,p=4$IkSIkdLaGyPEuHcu5RwjBA$Ye4MN7Ey9RCTSkS2JeGYcV0YtX8Te2IpJDMuASO0AIY',
     true, NOW(), false, true, NOW(), NOW(), NOW()),

    ('bbbbbbbb-0004-0004-0004-bbbbbbbbbbbb', '44444444-4444-4444-4444-444444444444',
     'sukarno@example.com',
     '$argon2id$v=19$m=65536,t=3,p=4$IkSIkdLaGyPEuHcu5RwjBA$Ye4MN7Ey9RCTSkS2JeGYcV0YtX8Te2IpJDMuASO0AIY',
     true, NOW(), false, true, NOW(), NOW(), NOW()),

    ('bbbbbbbb-0005-0005-0005-bbbbbbbbbbbb', '55555555-5555-5555-5555-555555555555',
     'jordan.smith@example.com',
     '$argon2id$v=19$m=65536,t=3,p=4$IkSIkdLaGyPEuHcu5RwjBA$Ye4MN7Ey9RCTSkS2JeGYcV0YtX8Te2IpJDMuASO0AIY',
     true, NOW(), false, true, NOW(), NOW(), NOW());


-- ============================================================================
-- 4. CONTEXT PROFILES (6 rows, one per context type)
-- ============================================================================

INSERT INTO context_profiles (id, user_id, context_type, context_name, display_name_override, email_override, bio, is_active, verification_status, created_at, updated_at, valid_from) VALUES
    -- Sarah Chen: professional context
    ('cccccccc-0001-0001-0001-cccccccccccc', '11111111-1111-1111-1111-111111111111',
     'professional', 'Work',
     'Dr. Sarah Chen', 'sarah.chen@company.com', 'Senior software engineer specializing in identity systems',
     true, NULL,
     NOW(), NOW(), NOW()),

    -- Sarah Chen: legal context (requires verification)
    ('cccccccc-0001-0002-0001-cccccccccccc', '11111111-1111-1111-1111-111111111111',
     'legal', 'Legal Identity',
     NULL, NULL, NULL,
     true, 'verified',
     NOW(), NOW(), NOW()),

    -- Li Ming: social context
    ('cccccccc-0002-0001-0002-cccccccccccc', '22222222-2222-2222-2222-222222222222',
     'social', 'WeChat',
     'Xiao Ming', NULL, 'Photography and travel enthusiast',
     true, NULL,
     NOW(), NOW(), NOW()),

    -- Li Ming: healthcare context (requires verification)
    ('cccccccc-0002-0002-0002-cccccccccccc', '22222222-2222-2222-2222-222222222222',
     'healthcare', 'Medical Records',
     NULL, 'li.ming.medical@example.com', NULL,
     true, 'verified',
     NOW(), NOW(), NOW()),

    -- Jordan Smith: family context
    ('cccccccc-0005-0001-0005-cccccccccccc', '55555555-5555-5555-5555-555555555555',
     'family', 'Smith Family',
     'JJ', NULL, 'Family sharing profile',
     true, NULL,
     NOW(), NOW(), NOW()),

    -- Jordan Smith: custom context
    ('cccccccc-0005-0002-0005-cccccccccccc', '55555555-5555-5555-5555-555555555555',
     'custom', 'Gaming',
     'ShadowWolf99', 'shadowwolf@gaming.example.com', 'Competitive FPS player',
     true, NULL,
     NOW(), NOW(), NOW());


-- ============================================================================
-- 5. OAUTH CLIENTS (6 confidential + 1 public debugger)
-- ============================================================================
-- Client secrets are Argon2id hashes of dev-seed-secret-<client_id>.
-- The oauth-debugger is a public client (no secret, PKCE-only).

INSERT INTO oauth_clients (client_id, client_secret_hash, client_name, client_description, client_uri, redirect_uris, allowed_scopes, default_context_type, is_confidential, is_active, is_first_party, token_endpoint_auth_method, created_at, updated_at) VALUES
    -- HR Portal: professional context
    ('hr-portal',
     '$argon2id$v=19$m=65536,t=3,p=4$BoDwHuNcay3lPKe0do7Reg$h0kKNGMh1vliPMBtdgqZJWPeWqN6A3vuR5CuqI+cvi0',
     'HR Portal', 'Human resources management application',
     'https://hr-portal.example.com',
     ARRAY['https://hr-portal.example.com/callback'],
     ARRAY['openid', 'profile:read:basic', 'profile:read:email', 'email', 'contexts:read', 'contexts:professional:read', 'offline_access'],
     'professional', true, true, false, 'client_secret_post',
     NOW(), NOW()),

    -- Social Connect: social context
    ('social-connect',
     '$argon2id$v=19$m=65536,t=3,p=4$DWEMwZiT8r537r1XKmVszQ$e1erGrAEkISrUuazRtHOPhDh7VGm/CpDGD4erImxw0Q',
     'Social Connect', 'Social networking integration',
     'https://social-connect.example.com',
     ARRAY['https://social-connect.example.com/callback'],
     ARRAY['openid', 'profile:read:basic', 'profile:read:email', 'email', 'contexts:read', 'contexts:social:read', 'offline_access'],
     'social', true, true, false, 'client_secret_post',
     NOW(), NOW()),

    -- Legal Verify: legal context
    ('legal-verify',
     '$argon2id$v=19$m=65536,t=3,p=4$Scl5L0VIyVkLQciZE+K8Fw$9+rVQ6210dAWzmjzgy9FhudhQszyfRuHg8U7YzEQs5Q',
     'Legal Verify', 'Legal identity verification service',
     'https://legal-verify.example.com',
     ARRAY['https://legal-verify.example.com/callback'],
     ARRAY['openid', 'profile:read:basic', 'profile:read:email', 'email', 'contexts:read', 'contexts:legal:read', 'offline_access'],
     'legal', true, true, false, 'client_secret_basic',
     NOW(), NOW()),

    -- Health Records App: healthcare context
    ('health-records',
     '$argon2id$v=19$m=65536,t=3,p=4$l9JaCwEAoDQm5Lz3vpdSCg$RjMiW3n5yFPdWVSIAogZ364aF5lu+aqLTEU5BsObfF0',
     'Health Records App', 'Healthcare records management',
     'https://health-records.example.com',
     ARRAY['https://health-records.example.com/callback'],
     ARRAY['openid', 'profile:read:basic', 'profile:read:email', 'email', 'contexts:read', 'contexts:healthcare:read', 'offline_access'],
     'healthcare', true, true, false, 'client_secret_basic',
     NOW(), NOW()),

    -- Family Tree App: family context
    ('family-tree',
     '$argon2id$v=19$m=65536,t=3,p=4$K2Us5XxPSckZQ+i911qLMQ$l63oZtH4iGRCnccdo31FrnWgVkSLTfGr6lbZHTEquX4',
     'Family Tree App', 'Family genealogy and sharing platform',
     'https://family-tree.example.com',
     ARRAY['https://family-tree.example.com/callback'],
     ARRAY['openid', 'profile:read:basic', 'profile:read:email', 'email', 'contexts:read', 'offline_access'],
     'family', true, true, false, 'client_secret_post',
     NOW(), NOW()),

    -- Custom Integration: custom context
    ('custom-app',
     '$argon2id$v=19$m=65536,t=3,p=4$AwBgLMV4zzlHaA0B4PzfOw$Zv9LZ5eCRQHhn5lEfjGzkAPgR3rUrNP8PLAgI8RW3wI',
     'Custom Integration', 'Custom third-party integration',
     'https://custom-app.example.com',
     ARRAY['https://custom-app.example.com/callback'],
     ARRAY['openid', 'profile:read:basic', 'profile:read:email', 'email', 'contexts:read', 'offline_access'],
     'custom', true, true, false, 'client_secret_post',
     NOW(), NOW()),

    -- OAuth 2.0 Debugger: public client (PKCE-only, no secret)
    ('oauth-debugger',
     NULL,
     'OAuth 2.0 Debugger', 'Public debugging tool for OAuth 2.0 flows (oauthdebugger.com)',
     'https://oauthdebugger.com',
     ARRAY['https://oauthdebugger.com/debug'],
     ARRAY['openid', 'profile:read:basic', 'profile:read:email', 'email', 'offline_access'],
     NULL, false, true, false, 'none',
     NOW(), NOW());


-- ============================================================================
-- 6. OAUTH CONSENTS (pre-granted for end-to-end token flow testing)
-- ============================================================================

INSERT INTO oauth_consents (id, user_id, client_id, granted_scopes, context_profile_id, granted_at, consent_method) VALUES
    -- Sarah Chen consents to HR Portal (professional scopes)
    ('dddddddd-0001-0001-0001-dddddddddddd',
     '11111111-1111-1111-1111-111111111111', 'hr-portal',
     ARRAY['openid', 'profile:read:basic', 'profile:read:email', 'email', 'contexts:read', 'contexts:professional:read', 'offline_access'],
     'cccccccc-0001-0001-0001-cccccccccccc',
     NOW(), 'explicit'),

    -- Li Ming consents to Social Connect (social scopes)
    ('dddddddd-0002-0001-0002-dddddddddddd',
     '22222222-2222-2222-2222-222222222222', 'social-connect',
     ARRAY['openid', 'profile:read:basic', 'profile:read:email', 'email', 'contexts:read', 'contexts:social:read', 'offline_access'],
     'cccccccc-0002-0001-0002-cccccccccccc',
     NOW(), 'explicit');


-- ============================================================================
-- Reset session_replication_role to default
-- ============================================================================
SET session_replication_role = DEFAULT;
