-- Seed Data for Local Development
-- Creates sample profiles and identity names for testing
-- Part of Identity and Profile Management API - Academic Thesis Project

-- Clear existing data (for reset)
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

-- Verification query (useful for checking seed data loaded correctly)
-- SELECT COUNT(*) FROM base_profiles;  -- Should return 5
-- SELECT COUNT(*) FROM identity_names; -- Should return 12

