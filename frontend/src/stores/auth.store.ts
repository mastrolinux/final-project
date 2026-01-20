/**
 * Authentication store managing JWT tokens and user session.
 *
 * Security considerations:
 * - Access tokens stored in memory only (XSS protection)
 * - Refresh tokens persisted to localStorage for session persistence
 * - Automatic token refresh on 401 responses handled by API interceptor
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { LoginResponse, AuthUser } from '@/types'

const REFRESH_TOKEN_KEY = 'refresh_token'

export const useAuthStore = defineStore('auth', () => {
  // State - access token in memory only for security
  const accessToken = ref<string | null>(null)
  const refreshToken = ref<string | null>(localStorage.getItem(REFRESH_TOKEN_KEY))
  const user = ref<AuthUser | null>(null)
  const preferredLanguage = ref<string>(navigator.language.split('-')[0] || 'en')
  const isInitialized = ref<boolean>(false)

  // Computed
  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)
  const isEmailVerified = computed(() => user.value?.is_email_verified ?? false)
  const isVerified = computed(() => user.value?.account_type === 'verified')
  const userId = computed(() => user.value?.user_id ?? null)
  const accountType = computed(() => user.value?.account_type ?? null)
  const userEmail = computed(() => user.value?.email ?? null)

  // Actions
  function setTokens(access: string, refresh: string): void {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh)
  }

  function setUser(loginResponse: LoginResponse): void {
    accessToken.value = loginResponse.access_token
    refreshToken.value = loginResponse.refresh_token
    user.value = {
      user_id: loginResponse.user_id,
      email: loginResponse.email,
      is_email_verified: loginResponse.is_email_verified,
      account_type: loginResponse.account_type
    }
    localStorage.setItem(REFRESH_TOKEN_KEY, loginResponse.refresh_token)
  }

  function updateUser(updates: Partial<AuthUser>): void {
    if (user.value) {
      user.value = { ...user.value, ...updates }
    }
  }

  function logout(): void {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  }

  function setPreferredLanguage(lang: string): void {
    preferredLanguage.value = lang
  }

  function setEmailVerified(verified: boolean): void {
    if (user.value) {
      user.value.is_email_verified = verified
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
