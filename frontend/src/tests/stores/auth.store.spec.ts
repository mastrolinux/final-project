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

  describe('session persistence and restoration', () => {
    it('should persist user info to localStorage on setUser', () => {
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

      expect(localStorage.setItem).toHaveBeenCalledWith(
        'auth_user',
        JSON.stringify({
          user_id: 'user-123',
          email: 'test@example.com',
          is_email_verified: true,
          account_type: 'verified'
        })
      )
    })

    it('should restore user info from localStorage on store initialization', () => {
      // Simulate existing session data in localStorage (as if from previous session)
      const storedUser = {
        user_id: 'restored-user-123',
        email: 'restored@example.com',
        is_email_verified: true,
        account_type: 'verified'
      }

      // Mock getItem to return stored values (simulating data from previous session)
      vi.mocked(localStorage.getItem).mockImplementation((key: string) => {
        if (key === 'auth_user') return JSON.stringify(storedUser)
        if (key === 'refresh_token') return 'stored-refresh-token'
        return null
      })

      // Create new Pinia and store (simulating page refresh)
      setActivePinia(createPinia())
      const store = useAuthStore()

      // User info should be restored from localStorage
      expect(store.userId).toBe('restored-user-123')
      expect(store.userEmail).toBe('restored@example.com')
      expect(store.isEmailVerified).toBe(true)
      expect(store.accountType).toBe('verified')
      expect(store.user).not.toBeNull()
    })

    it('should clear user info from localStorage on logout', () => {
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

      expect(localStorage.removeItem).toHaveBeenCalledWith('auth_user')
    })

    it('should persist updated user info when updateUser is called', () => {
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

      vi.mocked(localStorage.setItem).mockClear()
      store.updateUser({ is_email_verified: true })

      expect(localStorage.setItem).toHaveBeenCalledWith(
        'auth_user',
        expect.stringContaining('"is_email_verified":true')
      )
    })

    it('should handle corrupted localStorage data gracefully', () => {
      // Simulate corrupted data in localStorage
      vi.mocked(localStorage.getItem).mockImplementation((key: string) => {
        if (key === 'auth_user') return 'not-valid-json{'
        return null
      })

      // Should not throw, should return null user
      setActivePinia(createPinia())
      const store = useAuthStore()

      expect(store.user).toBeNull()
      expect(store.isAuthenticated).toBe(false)
      // Should also clean up corrupted data
      expect(localStorage.removeItem).toHaveBeenCalledWith('auth_user')
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
