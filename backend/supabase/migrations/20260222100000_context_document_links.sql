-- Replace one-to-one verification_documents.context_id FK with a
-- many-to-many join table so that the same document (e.g. a passport)
-- can be linked to multiple contexts, and each context can reference
-- multiple documents.
--
-- Also adds rejection_reason to context_profiles so that users can
-- see why their context verification was rejected.

-- 1. Many-to-many join table: contexts <-> documents
CREATE TABLE context_document_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    context_id UUID NOT NULL REFERENCES context_profiles(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES verification_documents(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(context_id, document_id)
);

CREATE INDEX idx_context_doc_links_context
    ON context_document_links(context_id);
CREATE INDEX idx_context_doc_links_document
    ON context_document_links(document_id);

-- 2. Migrate existing FK data to join table
INSERT INTO context_document_links (context_id, document_id)
SELECT context_id, id FROM verification_documents
WHERE context_id IS NOT NULL AND deleted_at IS NULL;

-- 3. Drop the old FK column (no longer needed)
ALTER TABLE verification_documents DROP COLUMN context_id;

-- 4. Add rejection_reason to context_profiles
ALTER TABLE context_profiles ADD COLUMN rejection_reason TEXT;
