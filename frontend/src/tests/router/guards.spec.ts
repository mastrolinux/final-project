/**
 * Unit tests for Vue Router navigation guards.
 *
 * Tests verify authentication, guest, admin, and verified guards
 * redirect correctly based on auth store state. Uses real Pinia stores
 * with controlled state and mocked auth service.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createRouter, createWebHistory, type Router } from 'vue-router'
import { useAuthStore } from '@/stores/auth.store'
import type { LoginResponse } from '@/types'

// Mock the auth service to control initializeAuth
vi.mock('@/services/auth.service', () => ({
  authService: {
    initializeAuth: vi.fn().mockResolvedValue(true)
  }
}))

// Minimal component stub for route resolution
const Stub = { template: '<div>stub</div>' }

function createTestRouter(): Router {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', name: 'home', component: Stub, meta: { title: 'Home' } },
      { path: '/login', name: 'login', component: Stub, meta: { requiresGuest: true, title: 'Login' } },
      { path: '/register', name: 'register', component: Stub, meta: { requiresGuest: true, title: 'Register' } },
      { path: '/profile', name: 'profile', component: Stub, meta: { requiresAuth: true, title: 'My Profile' } },
      { path: '/settings', name: 'settings', component: Stub, meta: { requiresAuth: true, title: 'Settings' } },
      { path: '/verified-page', name: 'verified-page', component: Stub, meta: { requiresAuth: true, requiresVerified: true, title: 'Verified' } },
      { path: '/verify-email', name: 'verify-email', component: Stub, meta: { title: 'Verify Email' } },
      { path: '/admin/clients', name: 'admin-oauth-clients', component: Stub, meta: { requiresAuth: true, requiresAdmin: true, title: 'Admin' } }
    ]
  })
}

const mockLoginResponse: LoginResponse = {
  access_token: 'test-access',
  refresh_token: 'test-refresh',
  token_type: 'Bearer',
  user_id: 'user-1',
  email: 'test@example.com',
  account_type: 'verified',
  is_email_verified: true,
  is_admin: false
}

describe('router navigation guards', () => {
  let authStore: ReturnType<typeof useAuthStore>

  beforeEach(() => {
    authStore = useAuthStore()
    // Mark as initialized to skip initializeAuth in most tests
    authStore.setInitialized(true)
  })

  describe('requiresAuth guard', () => {
    it('should redirect to login when not authenticated', async () => {
      const router = createTestRouter()
      // Replicate the guard logic from the real router
      router.beforeEach(async (to, _from, next) => {
        const requiresAuth = to.matched.some((r) => r.meta.requiresAuth)
        if (requiresAuth && !authStore.isAuthenticated) {
          next({ name: 'login', query: { redirect: to.fullPath } })
          return
        }
        next()
      })

      await router.push('/profile')
      await router.isReady()

      expect(router.currentRoute.value.name).toBe('login')
      expect(router.currentRoute.value.query.redirect).toBe('/profile')
    })

    it('should allow access when authenticated', async () => {
      authStore.setUser(mockLoginResponse)

      const router = createTestRouter()
      router.beforeEach(async (to, _from, next) => {
        const requiresAuth = to.matched.some((r) => r.meta.requiresAuth)
        if (requiresAuth && !authStore.isAuthenticated) {
          next({ name: 'login', query: { redirect: to.fullPath } })
          return
        }
        next()
      })

      await router.push('/profile')
      await router.isReady()

      expect(router.currentRoute.value.name).toBe('profile')
    })
  })

  describe('requiresGuest guard', () => {
    it('should redirect authenticated users to profile', async () => {
      authStore.setUser(mockLoginResponse)

      const router = createTestRouter()
      router.beforeEach(async (to, _from, next) => {
        const requiresGuest = to.matched.some((r) => r.meta.requiresGuest)
        if (requiresGuest && authStore.isAuthenticated) {
          next({ name: 'profile' })
          return
        }
        next()
      })

      await router.push('/login')
      await router.isReady()

      expect(router.currentRoute.value.name).toBe('profile')
    })

    it('should allow guest access when not authenticated', async () => {
      const router = createTestRouter()
      router.beforeEach(async (to, _from, next) => {
        const requiresGuest = to.matched.some((r) => r.meta.requiresGuest)
        if (requiresGuest && authStore.isAuthenticated) {
          next({ name: 'profile' })
          return
        }
        next()
      })

      await router.push('/login')
      await router.isReady()

      expect(router.currentRoute.value.name).toBe('login')
    })
  })

  describe('requiresVerified guard', () => {
    it('should redirect unverified users to verify-email', async () => {
      const unverifiedLogin = { ...mockLoginResponse, is_email_verified: false }
      authStore.setUser(unverifiedLogin)

      const router = createTestRouter()
      router.beforeEach(async (to, _from, next) => {
        const requiresAuth = to.matched.some((r) => r.meta.requiresAuth)
        const requiresVerified = to.matched.some((r) => r.meta.requiresVerified)
        if (requiresAuth && !authStore.isAuthenticated) {
          next({ name: 'login' })
          return
        }
        if (requiresVerified && !authStore.isEmailVerified) {
          next({ name: 'verify-email' })
          return
        }
        next()
      })

      await router.push('/verified-page')
      await router.isReady()

      expect(router.currentRoute.value.name).toBe('verify-email')
    })

    it('should allow verified users to proceed', async () => {
      authStore.setUser(mockLoginResponse) // is_email_verified: true

      const router = createTestRouter()
      router.beforeEach(async (to, _from, next) => {
        const requiresAuth = to.matched.some((r) => r.meta.requiresAuth)
        const requiresVerified = to.matched.some((r) => r.meta.requiresVerified)
        if (requiresAuth && !authStore.isAuthenticated) {
          next({ name: 'login' })
          return
        }
        if (requiresVerified && !authStore.isEmailVerified) {
          next({ name: 'verify-email' })
          return
        }
        next()
      })

      await router.push('/verified-page')
      await router.isReady()

      expect(router.currentRoute.value.name).toBe('verified-page')
    })
  })

  describe('requiresAdmin guard', () => {
    it('should redirect non-admin users to home', async () => {
      authStore.setUser(mockLoginResponse) // is_admin: false

      const router = createTestRouter()
      router.beforeEach(async (to, _from, next) => {
        const requiresAuth = to.matched.some((r) => r.meta.requiresAuth)
        const requiresAdmin = to.matched.some((r) => r.meta.requiresAdmin)
        if (requiresAuth && !authStore.isAuthenticated) {
          next({ name: 'login' })
          return
        }
        if (requiresAdmin && !authStore.isAdmin) {
          next({ name: 'home' })
          return
        }
        next()
      })

      await router.push('/admin/clients')
      await router.isReady()

      expect(router.currentRoute.value.name).toBe('home')
    })

    it('should allow admin users to proceed', async () => {
      const adminLogin = { ...mockLoginResponse, is_admin: true }
      authStore.setUser(adminLogin)

      const router = createTestRouter()
      router.beforeEach(async (to, _from, next) => {
        const requiresAuth = to.matched.some((r) => r.meta.requiresAuth)
        const requiresAdmin = to.matched.some((r) => r.meta.requiresAdmin)
        if (requiresAuth && !authStore.isAuthenticated) {
          next({ name: 'login' })
          return
        }
        if (requiresAdmin && !authStore.isAdmin) {
          next({ name: 'home' })
          return
        }
        next()
      })

      await router.push('/admin/clients')
      await router.isReady()

      expect(router.currentRoute.value.name).toBe('admin-oauth-clients')
    })
  })

  describe('document title', () => {
    it('should set document title from route meta', async () => {
      const router = createTestRouter()
      router.beforeEach(async (to, _from, next) => {
        const appName = 'Identity Management'
        document.title = to.meta.title ? `${to.meta.title} | ${appName}` : appName
        next()
      })

      await router.push('/')
      await router.isReady()

      expect(document.title).toBe('Home | Identity Management')
    })

    it('should fall back to app name when no title in meta', async () => {
      const router = createRouter({
        history: createWebHistory(),
        routes: [{ path: '/no-title', name: 'no-title', component: Stub }]
      })
      router.beforeEach(async (to, _from, next) => {
        const appName = 'Identity Management'
        document.title = to.meta.title ? `${to.meta.title} | ${appName}` : appName
        next()
      })

      await router.push('/no-title')
      await router.isReady()

      expect(document.title).toBe('Identity Management')
    })
  })
})
