/**
 * Admin user management types matching backend schemas.
 * @see backend/src/schemas/admin_users.py
 */

/**
 * A soft-deleted user account.
 */
export interface SoftDeletedUser {
  user_id: string;
  email: string;
  is_email_verified: boolean;
  is_admin: boolean;
  deleted_at: string;
  created_at: string | null;
}

/**
 * Paginated list of soft-deleted users.
 */
export interface SoftDeletedUserListResponse {
  users: SoftDeletedUser[];
  total: number;
  page: number;
  page_size: number;
}

/**
 * Response from purging expired soft-deleted accounts.
 */
export interface PurgeExpiredResponse {
  purged_count: number;
}
