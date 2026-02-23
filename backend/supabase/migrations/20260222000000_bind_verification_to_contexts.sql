-- Bind verification documents to specific context profiles
-- and add per-context verification status.
--
-- Previously, verification was account-level: approving a document
-- promoted the user's account_type globally. This migration adds
-- context-level verification so admins can verify the identity
-- claimed in a specific legal/healthcare context.

-- Link a verification document to its target context profile
ALTER TABLE verification_documents
    ADD COLUMN context_id UUID REFERENCES context_profiles(id) ON DELETE SET NULL;

CREATE INDEX idx_verification_docs_context
    ON verification_documents(context_id)
    WHERE context_id IS NOT NULL;

-- Track verification status per context profile (nullable: NULL for
-- context types that do not require verification)
ALTER TABLE context_profiles
    ADD COLUMN verification_status verification_status;

CREATE INDEX idx_context_profiles_verification
    ON context_profiles(verification_status)
    WHERE verification_status IS NOT NULL;

-- Retroactive: existing legal/healthcare contexts require verification
-- under the new context-bound model
UPDATE context_profiles
    SET verification_status = 'pending', is_active = false
    WHERE context_type IN ('legal', 'healthcare')
    AND deleted_at IS NULL;

-- Add 'read' operation for audit logging of document downloads
ALTER TYPE audit_operation ADD VALUE IF NOT EXISTS 'read';
