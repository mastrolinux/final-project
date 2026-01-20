/**
 * Unit tests for auth store.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth.store'
import type { LoginResponse } from '@/types'

describe('useAuthStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('initial state', () => {
    it('should have null access token initially', () => {
      const store = useAuthStore()
      expect(store.accessToken).toBeNull()
    })

    it('should not be authenticated initially', () => {
      const store = useAuthStore()
      expect(store.isAuthenticated).toBe(false)
    })

    it('should not be initialized initially', () => {
      const store = useAuthStore()
      expect(store.isInitialized).toBe(false)
    })

    it('should have null user initially', () => {
      const store = useAuthStore()
      expect(store.userId).toBeNull()
      expect(store.userEmail).toBeNull()
      expect(store.accountType).toBeNull()
    })
  })

  describe('setUser', () => {
    it('should set user data from login response', () => {
      const store = useAuthStore()
      const loginResponse: LoginResponse = {
        access_token: 'test-access-token',
        refresh_token: 'test-refresh-token',
        token_type: 'bearer',
        expires_in: 3600,
        user_id: 'user-123',
        email: 'test@example.com',
        is_email_verified: true,
        account_type: 'verified'
      }

      store.setUser(loginResponse)

      expect(store.accessToken).toBe('test-access-token')
      expect(store.refreshToken).toBe('test-refresh-token')
      expect(store.userId).toBe('user-123')
      expect(store.userEmail).toBe('test@example.com')
      expect(store.isEmailVerified).toBe(true)
      expect(store.accountType).toBe('verified')
      expect(store.isAuthenticated).toBe(true)
    })

    it('should persist refresh token to localStorage', () => {
      const store = useAuthStore()
      const loginResponse: LoginResponse = {
        access_token: 'test-access-token',
        refresh_token: 'test-refresh-token',
        token_type: 'bearer',
        expires_in: 3600,
        user_id: 'user-123',
        email: 'test@example.com',
        is_email_verified: false,
        account_type: 'unverified'
      }

      store.setUser(loginResponse)

      expect(localStorage.setItem).toHaveBeenCalledWith('refresh_token', 'test-refresh-token')
    })
  })

  describe('setTokens', () => {
    it('should update both tokens', () => {
      const store = useAuthStore()
      store.setTokens('new-access', 'new-refresh')

      expect(store.accessToken).toBe('new-access')
      expect(store.refreshToken).toBe('new-refresh')
    })
  })

  describe('updateUser', () => {
    it('should update user properties partially', () => {
      const store = useAuthStore()
      store.setUser({
        access_token: 'token',
        refresh_token: 'refresh',
        token_type: 'bearer',
        expires_in: 3600,
        user_id: 'user-123',
        email: 'old@example.com',
        is_email_verified: false,
        account_type: 'unverified'
      })

      store.updateUser({ is_email_verified: true })

      expect(store.isEmailVerified).toBe(true)
      expect(store.userEmail).toBe('old@example.com')
    })
  })

  describe('setEmailVerified', () => {
    it('should update email verification status', () => {
      const store = useAuthStore()
      store.setUser({
        access_token: 'token',
        refresh_token: 'refresh',
        token_type: 'bearer',
        expires_in: 3600,
        user_id: 'user-123',
        email: 'test@example.com',
        is_email_verified: false,
        account_type: 'unverified'
      })

      expect(store.isEmailVerified).toBe(false)
      store.setEmailVerified(true)
      expect(store.isEmailVerified).toBe(true)
    })
  })

  describe('logout', () => {
    it('should clear all auth state', () => {
      const store = useAuthStore()
      store.setUser({
        access_token: 'token',
        refresh_token: 'refresh',
        token_type: 'bearer',
        expires_in: 3600,
        user_id: 'user-123',
        email: 'test@example.com',
        is_email_verified: true,
        account_type: 'verified'
      })

      store.logout()

      expect(store.accessToken).toBeNull()
      expect(store.refreshToken).toBeNull()
      expect(store.userId).toBeNull()
      expect(store.isAuthenticated).toBe(false)
    })

    it('should remove refresh token from localStorage', () => {
      const store = useAuthStore()
      store.setUser({
        access_token: 'token',
        refresh_token: 'refresh',
        token_type: 'bearer',
        expires_in: 3600,
        user_id: 'user-123',
        email: 'test@example.com',
        is_email_verified: true,
        account_type: 'verified'
      })

      store.logout()

      expect(localStorage.removeItem).toHaveBeenCalledWith('refresh_token')
    })
  })

  describe('hasStoredSession', () => {
    it('should return false when no refresh token in localStorage', () => {
      const store = useAuthStore()
      vi.mocked(localStorage.getItem).mockReturnValue(null)
      expect(store.hasStoredSession()).toBe(false)
    })

    it('should return true when refresh token exists in localStorage', () => {
      const store = useAuthStore()
      vi.mocked(localStorage.getItem).mockReturnValue('stored-refresh-token')
      expect(store.hasStoredSession()).toBe(true)
    })
  })

  describe('computed properties', () => {
    it('isVerified should return true only for verified accounts', () => {
      const store = useAuthStore()
      store.setUser({
        access_token: 'token',
        refresh_token: 'refresh',
        token_type: 'bearer',
        expires_in: 3600,
        user_id: 'user-123',
        email: 'test@example.com',
        is_email_verified: true,
        account_type: 'verified'
      })

      expect(store.isVerified).toBe(true)
    })

    it('isVerified should return false for unverified accounts', () => {
      const store = useAuthStore()
      store.setUser({
        access_token: 'token',
        refresh_token: 'refresh',
        token_type: 'bearer',
        expires_in: 3600,
        user_id: 'user-123',
        email: 'test@example.com',
        is_email_verified: false,
        account_type: 'unverified'
      })

      expect(store.isVerified).toBe(false)
    })

    it('isVerified should return false for pseudonymous accounts', () => {
      const store = useAuthStore()
      store.setUser({
        access_token: 'token',
        refresh_token: 'refresh',
        token_type: 'bearer',
        expires_in: 3600,
        user_id: 'user-123',
        email: 'anon@example.com',
        is_email_verified: false,
        account_type: 'pseudonymous'
      })

      expect(store.isVerified).toBe(false)
    })
  })
})
