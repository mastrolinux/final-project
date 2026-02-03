/**
 * Authentication types matching backend schemas.
 * @see backend/src/schemas/auth.py
 */

export type AccountType = 'verified' | 'unverified' | 'pseudonymous'

export interface RegisterRequest {
  email: string
  password: string
  preferred_name: string
  account_type?: AccountType
  preferred_language?: string
}

export interface RegisterResponse {
  user_id: string
  email: string
  is_email_verified: boolean
  message: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  expires_in: number
  user_id: string
  email: string
  is_email_verified: boolean
  account_type: AccountType
  is_admin: boolean
}

export interface RefreshTokenRequest {
  refresh_token: string
}

export interface RefreshTokenResponse {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  expires_in: number
}

export interface VerifyEmailRequest {
  token: string
}

export interface PasswordResetRequest {
  email: string
}

export interface PasswordResetConfirmRequest {
  token: string
  new_password: string
}

export interface AuthUser {
  user_id: string
  email: string
  is_email_verified: boolean
  account_type: AccountType
  is_admin: boolean
}
