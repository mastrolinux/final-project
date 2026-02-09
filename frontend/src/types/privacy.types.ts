/**
 * Privacy / GDPR data export types matching backend schemas.
 * @see backend/src/schemas/privacy.py
 */

/**
 * Export envelope metadata.
 */
export interface ExportMetadata {
  exported_at: string
  user_id: string
  format_version: string
  legal_basis: string
}

/**
 * Base profile data included in the export.
 */
export interface ProfileExport {
  user_id: string
  account_type: string
  legal_name: string | null
  primary_email: string
  primary_phone: string | null
  preferred_language: string
  valid_from: string | null
  valid_to: string | null
  created_at: string | null
  updated_at: string | null
}

/**
 * Identity name record (active or deprecated).
 */
export interface IdentityNameExport {
  id: string
  name_type: string
  name_value: Record<string, string>
  is_primary: boolean
  is_deprecated: boolean
  visibility_level: string
  context_id: string | null
  valid_from: string | null
  valid_to: string | null
  created_at: string | null
  updated_at: string | null
}

/**
 * Context profile record (active or inactive).
 */
export interface ContextProfileExport {
  id: string
  context_type: string
  context_name: string
  display_name_override: string | null
  email_override: string | null
  phone_override: string | null
  bio: string | null
  is_active: boolean
  valid_from: string | null
  valid_to: string | null
  created_at: string | null
  updated_at: string | null
}

/**
 * Authentication metadata (sensitive fields excluded by backend).
 */
export interface AuthenticationExport {
  email: string
  is_email_verified: boolean
  email_verified_at: string | null
  last_login_at: string | null
  password_changed_at: string | null
  is_admin: boolean
  created_at: string | null
}

/**
 * OAuth consent record.
 */
export interface OAuthConsentExport {
  id: string
  client_id: string
  granted_scopes: string[]
  context_profile_id: string | null
  consent_method: string
  granted_at: string | null
  expires_at: string | null
  withdrawn_at: string | null
}

/**
 * Static GDPR Article 15 informational metadata.
 */
export interface GDPRMetadata {
  processing_purposes: string[]
  retention_periods: Record<string, string>
  data_subject_rights: string[]
  data_sources: string[]
  recipients_or_categories: string[]
  automated_decision_making: string
}

/**
 * Complete GDPR Article 15 data export response.
 */
export interface DataExportResponse {
  export_metadata: ExportMetadata
  profile: ProfileExport
  identity_names: IdentityNameExport[]
  context_profiles: ContextProfileExport[]
  authentication: AuthenticationExport | null
  oauth_consents: OAuthConsentExport[]
  gdpr_metadata: GDPRMetadata
}

/**
 * Response for account deletion request (GDPR Art. 17 soft delete).
 */
export interface DeletionRequestResponse {
  status: string
  deletion_scheduled_at: string
  permanent_deletion_date: string
  message: string
}

/**
 * Response for deletion status check.
 */
export type DeletionStatus = 'active' | 'scheduled' | 'purged'

export interface DeletionStatusResponse {
  status: DeletionStatus
  deletion_scheduled_at: string | null
  permanent_deletion_date: string | null
}
