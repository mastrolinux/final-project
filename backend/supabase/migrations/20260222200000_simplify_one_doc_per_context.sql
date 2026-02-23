-- Simplify document-to-context relationship from many-to-many
-- (context_document_links join table) to one-to-one (direct FK).
--
-- Each context profile may reference at most one verification document.
-- A single document can still be referenced by multiple contexts
-- (e.g. a passport verifying both a legal and a healthcare context).

-- 1. Add direct FK from context_profiles to verification_documents.
ALTER TABLE context_profiles
    ADD COLUMN document_id UUID REFERENCES verification_documents(id)
    ON DELETE SET NULL;

CREATE INDEX idx_context_profiles_document_id
    ON context_profiles(document_id);

-- 2. Migrate existing links (keep the most recently linked document per context).
UPDATE context_profiles cp
SET document_id = sub.document_id
FROM (
    SELECT DISTINCT ON (context_id) context_id, document_id
    FROM context_document_links
    ORDER BY context_id, created_at DESC
) sub
WHERE cp.id = sub.context_id;

-- 3. Drop the join table (no longer needed).
DROP TABLE context_document_links;
