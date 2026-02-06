-- Audit Logging System
-- Immutable, hash-chained audit trail for privacy accountability
-- Part of Phase 4: Privacy Features
--
-- Design notes:
--   - No updated_at or deleted_at columns (immutable, never deleted)
--   - Hash chaining: each entry stores SHA-256 hash of previous entry
--   - RLS denies UPDATE and DELETE for all roles
--   - ON DELETE SET NULL on FKs preserves audit records after user purge
--   - event_type is VARCHAR (not DB enum) to avoid migration churn

-- Create audit_operation enum type
DO $$ BEGIN
    CREATE TYPE audit_operation AS ENUM (
        'create', 'update', 'delete',
        'login', 'logout', 'register',
        'verify', 'grant', 'withdraw', 'revoke'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Audit logs table - immutable, append-only
CREATE TABLE audit_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type VARCHAR(100) NOT NULL,
    user_id UUID REFERENCES base_profiles(user_id) ON DELETE SET NULL,
    actor_id UUID REFERENCES base_profiles(user_id) ON DELETE SET NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255) NOT NULL,
    operation audit_operation NOT NULL,
    changes JSONB,
    ip_address INET,
    user_agent TEXT,
    legal_basis VARCHAR(100),
    previous_hash VARCHAR(64) NOT NULL,
    entry_hash VARCHAR(64) NOT NULL
);

COMMENT ON TABLE audit_logs IS 'Immutable audit trail with hash chaining for tamper evidence.';
COMMENT ON COLUMN audit_logs.user_id IS 'The data subject (whose data was affected)';
COMMENT ON COLUMN audit_logs.actor_id IS 'The actor who performed the action (may differ from user_id for admin actions)';
COMMENT ON COLUMN audit_logs.previous_hash IS 'SHA-256 hash of the previous log entry for chain integrity';
COMMENT ON COLUMN audit_logs.entry_hash IS 'SHA-256 hash of this entry including previous_hash';
COMMENT ON COLUMN audit_logs.legal_basis IS 'GDPR processing basis (e.g., consent, legitimate_interest, contract)';

-- Indexes for query performance
CREATE INDEX idx_audit_logs_user_timestamp
    ON audit_logs(user_id, created_at DESC);

CREATE INDEX idx_audit_logs_resource
    ON audit_logs(resource_type, resource_id);

CREATE INDEX idx_audit_logs_event_timestamp
    ON audit_logs(event_type, created_at DESC);

CREATE INDEX idx_audit_logs_actor
    ON audit_logs(actor_id) WHERE actor_id IS NOT NULL;

-- Row-Level Security
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- No UPDATE policy: denies all updates (immutable)
-- No DELETE policy: denies all deletes (never deleted)

-- SELECT: users can view their own audit records (data subject access)
CREATE POLICY "Users can view own audit logs" ON audit_logs
    FOR SELECT USING (
        user_id::text = current_setting('request.jwt.claims', true)::json->>'sub'
    );

-- SELECT: admins can view all audit records
CREATE POLICY "Admins can view all audit logs" ON audit_logs
    FOR SELECT USING (
        (current_setting('request.jwt.claims', true)::jsonb->>'is_admin')::boolean = true
    );

-- INSERT: application-level control via service role
CREATE POLICY "Service can insert audit logs" ON audit_logs
    FOR INSERT WITH CHECK (true);
