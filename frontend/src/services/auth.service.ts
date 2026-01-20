/**
 * Authentication service for registration, login, logout, and token management.
 */

import api, { getErrorMessage } from './api'
import { useAuthStore } from '@/stores/auth.store'
import { useProfileStore } from '@/stores/profile.store'
import type {
  RegisterRequest,
  RegisterResponse,
  LoginRequest,
  LoginResponse,
  RefreshTokenResponse
} from '@/types'

export const authService = {
  /**
   * Register a new user account.
   */
  async register(data: RegisterRequest): Promise<RegisterResponse> {
    const response = await api.post<RegisterResponse>('/auth/register', data)
    return response.data
  },

  /**
   * Login with email and password.
   * Sets tokens and user data in auth store on success.
   */
  async login(data: LoginRequest): Promise<LoginResponse> {
    const response = await api.post<LoginResponse>('/auth/login', data)
    const authStore = useAuthStore()
    authStore.setUser(response.data)
    return response.data
  },

  /**
   * Logout current user.
   * Clears tokens from auth store and profile data.
   */
  async logout(): Promise<void> {
    const authStore = useAuthStore()
    const profileStore = useProfileStore()

    try {
      // Notify backend to invalidate tokens
      await api.post('/auth/logout')
    } catch {
      // Ignore errors - we still want to clear local state
    } finally {
      authStore.logout()
      profileStore.clearProfile()
    }
  },

  /**
   * Refresh access token using refresh token.
   * Called automatically by API interceptor on 401.
   */
  async refresh(refreshToken: string): Promise<RefreshTokenResponse> {
    const response = await api.post<RefreshTokenResponse>('/auth/refresh', {
      refresh_token: refreshToken
    })
    const authStore = useAuthStore()
    authStore.setTokens(response.data.access_token, response.data.refresh_token)
    return response.data
  },

  /**
   * Verify email with token from verification link.
   */
  async verifyEmail(token: string): Promise<void> {
    await api.post('/auth/verify-email', { token })
    const authStore = useAuthStore()
    authStore.updateUser({ is_email_verified: true })
  },

  /**
   * Request password reset email.
   */
  async requestPasswordReset(email: string): Promise<void> {
    await api.post('/auth/request-reset', { email })
  },

  /**
   * Reset password with token from reset email.
   */
  async resetPassword(token: string, newPassword: string): Promise<void> {
    await api.post('/auth/reset-password', { token, new_password: newPassword })
  },

  /**
   * Resend email verification link.
   */
  async resendVerificationEmail(email: string): Promise<void> {
    await api.post('/auth/resend-verification', { email })
  },

  /**
   * Change password for authenticated user.
   */
  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword
    })
  },

  /**
   * Delete user account permanently.
   */
  async deleteAccount(): Promise<void> {
    await api.delete('/auth/account')
  },

  /**
   * Exchange OAuth authorization code for tokens.
   */
  async exchangeOAuthCode(params: {
    code: string
    code_verifier?: string
    redirect_uri: string
  }): Promise<LoginResponse> {
    const response = await api.post<LoginResponse>('/oauth/token', {
      grant_type: 'authorization_code',
      code: params.code,
      code_verifier: params.code_verifier,
      redirect_uri: params.redirect_uri
    })
    return response.data
  },

  /**
   * Initialize auth state on app startup.
   * Attempts to restore session using stored refresh token.
   */
  async initializeAuth(): Promise<boolean> {
    const authStore = useAuthStore()

    if (!authStore.hasStoredSession()) {
      authStore.setInitialized(true)
      return false
    }

    try {
      await this.refresh(authStore.refreshToken!)
      authStore.setInitialized(true)
      return true
    } catch (error) {
      console.warn('Failed to restore session:', getErrorMessage(error))
      authStore.logout()
      authStore.setInitialized(true)
      return false
    }
  }
}

export default authService
