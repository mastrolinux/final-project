/**
 * Audit logging types matching backend schemas.
 * @see backend/src/schemas/audit.py
 */

/**
 * Audit operation types (maps to AuditOperation enum on the backend).
 */
export type AuditOperation =
  | 'create'
  | 'update'
  | 'delete'
  | 'login'
  | 'logout'
  | 'register'
  | 'verify'
  | 'grant'
  | 'withdraw'
  | 'revoke'

/**
 * A single audit log entry as returned by the API.
 * The user_agent field is intentionally excluded for privacy.
 */
export interface AuditLogEntry {
  log_id: string
  created_at: string
  event_type: string
  user_id: string | null
  actor_id: string | null
  resource_type: string
  resource_id: string
  operation: AuditOperation
  changes: Record<string, unknown> | null
  ip_address: string | null
  legal_basis: string | null
}

/**
 * Paginated response for user audit trail (GET /audit/me).
 */
export interface AuditTrailResponse {
  entries: AuditLogEntry[]
  total: number
  limit: number
  offset: number
}

/**
 * Query parameters for filtering audit trail entries.
 */
export interface AuditTrailFilter {
  event_type?: string
  resource_type?: string
  limit?: number
  offset?: number
}

/**
 * Hash chain integrity verification result (GET /audit/verify).
 */
export interface AuditIntegrityResponse {
  is_valid: boolean
  entries_verified: number
  error_message: string | null
}
