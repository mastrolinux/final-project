-- Add 'expired' value to the verification_status enum.
-- Used by the daily Celery Beat task to mark documents whose
-- document_expiry_date has passed, preventing re-processing.
ALTER TYPE verification_status ADD VALUE 'expired';
