/**
 * Profile types matching backend schemas.
 * @see backend/src/schemas/profile.py
 */

import type { AccountType } from './auth.types'

export type NameType =
  | 'given'
  | 'family'
  | 'preferred'
  | 'legal'
  | 'patronymic'
  | 'full_name'
  | 'custom'

export type VisibilityLevel = 'public' | 'private' | 'historical_suppressed'

export interface ProfileCreate {
  account_type?: AccountType
  legal_name?: string
  primary_email: string
  primary_phone?: string
  preferred_language?: string
}

export interface ProfileUpdate {
  legal_name?: string
  primary_email?: string
  primary_phone?: string
  preferred_language?: string
}

export interface ProfileResponse {
  id: string
  user_id: string
  account_type: AccountType
  legal_name: string | null
  primary_email: string
  primary_phone: string | null
  preferred_language: string
  created_at: string
  updated_at: string
  deleted_at: string | null
  valid_from?: string
  valid_to?: string | null
}

export interface IdentityNameCreate {
  name_type: NameType
  name_value: Record<string, string>
  is_primary?: boolean
  visibility_level?: VisibilityLevel
  context_id?: string
}

export interface IdentityName {
  id: string
  identity_id: string
  name_type: NameType
  name_value: Record<string, string>
  is_primary: boolean
  is_deprecated: boolean
  visibility_level: VisibilityLevel
  context_id: string | null
  created_at: string
  updated_at: string
  valid_from: string
  valid_to: string | null
}

export interface ResolvedBaseProfile {
  user_id: string
  account_type: AccountType
  display_name: string | null
  email: string
  phone: string | null
  preferred_language: string
  identity_names: IdentityNameInResolved[]
}

export interface IdentityNameInResolved {
  name_type: NameType
  name_value: Record<string, string>
  is_primary: boolean
}
