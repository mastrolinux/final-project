/**
 * Authentication store managing JWT tokens and user session.
 *
 * Security considerations:
 * - Access tokens stored in memory only (XSS protection)
 * - Refresh tokens persisted to localStorage for session persistence
 * - User info (non-sensitive: user_id, email, account_type) persisted to
 *   localStorage to restore session state after page refresh
 * - Automatic token refresh on 401 responses handled by API interceptor
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { LoginResponse, AuthUser } from '@/types'

const REFRESH_TOKEN_KEY = 'refresh_token'
const USER_INFO_KEY = 'auth_user'

/**
 * Restore user info from localStorage.
 * Returns null if no stored data or parsing fails.
 */
function restoreUserFromStorage(): AuthUser | null {
  try {
    const stored = localStorage.getItem(USER_INFO_KEY)
    if (!stored) return null
    return JSON.parse(stored) as AuthUser
  } catch {
    localStorage.removeItem(USER_INFO_KEY)
    return null
  }
}

/**
 * Persist user info to localStorage.
 */
function persistUserToStorage(userData: AuthUser | null): void {
  if (userData) {
    localStorage.setItem(USER_INFO_KEY, JSON.stringify(userData))
  } else {
    localStorage.removeItem(USER_INFO_KEY)
  }
}

export const useAuthStore = defineStore('auth', () => {
  // State - access token in memory only for security
  const accessToken = ref<string | null>(null)
  const refreshToken = ref<string | null>(localStorage.getItem(REFRESH_TOKEN_KEY))
  const user = ref<AuthUser | null>(restoreUserFromStorage())
  const preferredLanguage = ref<string>(navigator.language.split('-')[0] || 'en')
  const isInitialized = ref<boolean>(false)

  // Computed
  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)
  const isEmailVerified = computed(() => user.value?.is_email_verified ?? false)
  const isVerified = computed(() => user.value?.account_type === 'verified')
  const userId = computed(() => user.value?.user_id ?? null)
  const accountType = computed(() => user.value?.account_type ?? null)
  const userEmail = computed(() => user.value?.email ?? null)
  const isAdmin = computed(() => user.value?.is_admin ?? false)
  const isOAuthUser = computed(() => !!user.value?.provider)
  const hasCustomPassword = computed(() => user.value?.has_custom_password ?? false)

  // Actions
  function setTokens(access: string, refresh: string): void {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh)
  }

  function setUser(loginResponse: LoginResponse): void {
    accessToken.value = loginResponse.access_token
    refreshToken.value = loginResponse.refresh_token
    const userData: AuthUser = {
      user_id: loginResponse.user_id,
      email: loginResponse.email,
      is_email_verified: loginResponse.is_email_verified,
      account_type: loginResponse.account_type,
      is_admin: loginResponse.is_admin,
      provider: loginResponse.provider ?? null,
      has_custom_password: loginResponse.has_custom_password ?? false
    }
    user.value = userData
    localStorage.setItem(REFRESH_TOKEN_KEY, loginResponse.refresh_token)
    persistUserToStorage(userData)
  }

  function updateUser(updates: Partial<AuthUser>): void {
    if (user.value) {
      user.value = { ...user.value, ...updates }
      persistUserToStorage(user.value)
    }
  }

  function logout(): void {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    persistUserToStorage(null)
  }

  function setPreferredLanguage(lang: string): void {
    preferredLanguage.value = lang
  }

  function setEmailVerified(verified: boolean): void {
    if (user.value) {
      user.value.is_email_verified = verified
      persistUserToStorage(user.value)
    }
  }

  function setInitialized(initialized: boolean): void {
    isInitialized.value = initialized
  }

  /**
   * Check if we have a stored refresh token that could be used
   * to restore the session on app initialization.
   */
  function hasStoredSession(): boolean {
    return !!localStorage.getItem(REFRESH_TOKEN_KEY)
  }

  return {
    // State
    accessToken,
    refreshToken,
    user,
    preferredLanguage,
    isInitialized,

    // Computed
    isAuthenticated,
    isEmailVerified,
    isVerified,
    userId,
    accountType,
    userEmail,
    isAdmin,
    isOAuthUser,
    hasCustomPassword,

    // Actions
    setTokens,
    setUser,
    updateUser,
    logout,
    setPreferredLanguage,
    setEmailVerified,
    setInitialized,
    hasStoredSession
  }
})
