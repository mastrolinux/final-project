/**
 * Authentication types matching backend schemas.
 * @see backend/src/schemas/auth.py
 */

export type AccountType = "verified" | "unverified" | "pseudonymous";

export interface RegisterRequest {
  email: string;
  password: string;
  preferred_name: string;
  account_type?: AccountType;
  preferred_language?: string;
}

export interface RegisterResponse {
  user_id: string;
  email: string;
  is_email_verified: boolean;
  message: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
  user_id: string;
  email: string;
  is_email_verified: boolean;
  account_type: AccountType;
  is_admin: boolean;
  provider: string | null;
  has_custom_password: boolean;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface RefreshTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface VerifyEmailRequest {
  token: string;
}

export interface PasswordResetRequest {
  email: string;
}

export interface PasswordResetConfirmRequest {
  token: string;
  new_password: string;
}

export interface AuthUser {
  user_id: string;
  email: string;
  is_email_verified: boolean;
  account_type: AccountType;
  is_admin: boolean;
  provider: string | null;
  has_custom_password: boolean;
}

/**
 * Request to initiate account restoration after soft deletion.
 */
export interface RestoreAccountRequest {
  email: string;
}

/**
 * Generic response for restore request (always 202, enumeration prevention).
 */
export interface RestoreAccountResponse {
  message: string;
}

/**
 * Request to confirm account restoration with token and new password.
 */
export interface RestoreAccountConfirmRequest {
  token: string;
  new_password: string;
}

/**
 * Response for successful account restoration (includes JWT tokens).
 */
export interface RestoreAccountConfirmResponse {
  message: string;
  access_token: string;
  refresh_token: string;
  token_type: string;
  restored_at: string;
}

/**
 * Structured error detail returned by login (403) for deleted accounts.
 */
export interface AccountDeletedDetail {
  code: "ACCOUNT_DELETED";
  deletion_scheduled_at: string;
  permanent_deletion_date: string;
  recovery_info: string;
}

/**
 * Structured error detail returned by register (409) for recoverable accounts.
 */
export interface AccountRecoverableDetail {
  detail: string;
  code: "ACCOUNT_RECOVERABLE";
  account_recoverable: boolean;
  permanent_deletion_date: string;
  restore_endpoint: string;
}

/**
 * Request to set a password for an OAuth-only user.
 */
export interface SetPasswordRequest {
  new_password: string;
}

/**
 * Response after successfully setting a password.
 */
export interface SetPasswordResponse {
  message: string;
  user_id: string;
  email: string;
}
