-- ============================================================================
-- Migration: Verification Documents (MAS-79)
-- Description: Create verification_documents table for ID document upload
--   and verification workflow. Adds document_type and verification_status
--   enums, and extends audit_operation with 'review'.
-- ============================================================================

-- Create document_type enum
DO $$ BEGIN
    CREATE TYPE document_type AS ENUM ('passport', 'national_id');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Create verification_status enum
DO $$ BEGIN
    CREATE TYPE verification_status AS ENUM (
        'pending', 'under_review', 'verified', 'rejected'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Add 'review' operation to audit_operation enum
ALTER TYPE audit_operation ADD VALUE IF NOT EXISTS 'review';

-- Create verification_documents table
CREATE TABLE verification_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES base_profiles(user_id) ON DELETE CASCADE,
    document_type document_type NOT NULL,
    verification_status verification_status NOT NULL DEFAULT 'pending',
    storage_path TEXT,
    original_filename TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    reviewer_id UUID REFERENCES base_profiles(user_id) ON DELETE SET NULL,
    reviewer_notes TEXT,
    reviewed_at TIMESTAMPTZ,
    document_expiry_date DATE,
    rejection_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_verification_docs_user
    ON verification_documents(user_id);

CREATE INDEX idx_verification_docs_status
    ON verification_documents(verification_status);

CREATE INDEX idx_verification_docs_pending
    ON verification_documents(verification_status)
    WHERE verification_status IN ('pending', 'under_review');

CREATE INDEX idx_verification_docs_expiry
    ON verification_documents(document_expiry_date)
    WHERE document_expiry_date IS NOT NULL;

CREATE INDEX idx_verification_docs_not_deleted
    ON verification_documents(user_id, verification_status)
    WHERE deleted_at IS NULL;

-- Auto-update updated_at timestamp
CREATE TRIGGER update_verification_documents_updated_at
    BEFORE UPDATE ON verification_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Row-Level Security
ALTER TABLE verification_documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY "verification_docs_access"
    ON verification_documents FOR ALL USING (true);

-- Documentation
COMMENT ON TABLE verification_documents
    IS 'Identity verification documents uploaded by users for account verification';
COMMENT ON COLUMN verification_documents.document_type
    IS 'Type of government-issued ID: passport, national_id';
COMMENT ON COLUMN verification_documents.verification_status
    IS 'Workflow state: pending -> under_review -> verified/rejected';
COMMENT ON COLUMN verification_documents.storage_path
    IS 'Path to Fernet-encrypted blob in the verification-documents bucket';
COMMENT ON COLUMN verification_documents.document_expiry_date
    IS 'Expiry date of the physical document; NULL means no expiry';
