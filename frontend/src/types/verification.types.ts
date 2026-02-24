/**
 * Types for identity document verification.
 *
 * Mirrors the backend schemas in src/schemas/verification.py.
 */

export type DocumentType = "passport" | "national_id";

export type VerificationStatus =
  | "pending"
  | "under_review"
  | "verified"
  | "rejected"
  | "expired";

export interface VerificationDocumentResponse {
  id: string;
  user_id: string;
  document_type: DocumentType;
  verification_status: VerificationStatus;
  original_filename: string;
  file_size_bytes: number;
  content_type: string;
  document_expiry_date: string | null;
  rejection_reason: string | null;
  reviewer_notes: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface VerificationStatusResponse {
  user_id: string;
  account_type: string;
  latest_document: VerificationDocumentResponse | null;
  can_create_legal_context: boolean;
}

export interface AdminContextVerificationItem {
  context_id: string;
  context_type: string;
  context_name: string;
  display_name_override: string | null;
  email_override: string | null;
  verification_status: VerificationStatus;
  user_id: string;
  user_display_name: string | null;
  document_count: number;
  created_at: string;
}

export interface AdminContextVerificationDetail {
  context_id: string;
  context_type: string;
  context_name: string;
  display_name_override: string | null;
  email_override: string | null;
  phone_override: string | null;
  bio: string | null;
  verification_status: VerificationStatus;
  rejection_reason: string | null;
  user_id: string;
  user_display_name: string | null;
  documents: VerificationDocumentResponse[];
  created_at: string;
}

export interface AdminVerificationReview {
  verification_status: "verified" | "rejected";
  reviewer_notes?: string;
  document_expiry_date?: string | null;
  rejection_reason?: string;
}
