/**
 * Vue Router configuration with authentication guards.
 *
 * Route meta options:
 * - requiresAuth: true - Route requires authenticated user
 * - requiresGuest: true - Route only accessible when not authenticated
 * - requiresVerified: true - Route requires verified account (email verified)
 */

import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth.store'
import { authService } from '@/services/auth.service'

// Extend route meta types
declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    requiresGuest?: boolean
    requiresVerified?: boolean
    requiresAdmin?: boolean
    title?: string
    breadcrumb?: {
      parent: string
      parentLabel: string
      currentLabel?: string
    }
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
    meta: { title: 'Home' }
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresGuest: true, title: 'Login' }
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { requiresGuest: true, title: 'Register' }
  },
  {
    path: '/verify-email',
    name: 'verify-email',
    component: () => import('@/views/VerifyEmailView.vue'),
    meta: { title: 'Verify Email' }
  },
  {
    path: '/forgot-password',
    name: 'forgot-password',
    component: () => import('@/views/ForgotPasswordView.vue'),
    meta: { requiresGuest: true, title: 'Forgot Password' }
  },
  {
    path: '/reset-password',
    name: 'reset-password',
    component: () => import('@/views/ResetPasswordView.vue'),
    meta: { requiresGuest: true, title: 'Reset Password' }
  },
  {
    path: '/restore-account',
    name: 'restore-account',
    component: () => import('@/views/RestoreAccountView.vue'),
    meta: {
      requiresGuest: true,
      title: 'Restore Account',
      breadcrumb: { parent: '/', parentLabel: 'nav.home' }
    }
  },
  {
    path: '/restore-account/confirm',
    name: 'restore-account-confirm',
    component: () => import('@/views/RestoreAccountConfirmView.vue'),
    meta: {
      requiresGuest: true,
      title: 'Restore Account',
      breadcrumb: { parent: '/', parentLabel: 'nav.home' }
    }
  },
  {
    path: '/profile/edit',
    name: 'profile-edit',
    component: () => import('@/views/ProfileEditView.vue'),
    meta: {
      requiresAuth: true,
      title: 'Edit Profile',
      breadcrumb: { parent: '/profile', parentLabel: 'nav.profile' }
    }
  },
  {
    path: '/profile',
    name: 'profile',
    component: () => import('@/views/ProfileView.vue'),
    meta: { requiresAuth: true, title: 'My Profile' }
  },
  {
    path: '/contexts',
    name: 'contexts',
    component: () => import('@/views/ContextsView.vue'),
    meta: { requiresAuth: true, title: 'Identity Contexts' }
  },
  {
    path: '/contexts/new',
    name: 'context-create',
    component: () => import('@/views/ContextCreateView.vue'),
    meta: {
      requiresAuth: true,
      title: 'Create Context',
      breadcrumb: { parent: '/contexts', parentLabel: 'nav.contexts' }
    }
  },
  {
    path: '/contexts/:id',
    name: 'context-detail',
    component: () => import('@/views/ContextDetailView.vue'),
    meta: {
      requiresAuth: true,
      title: 'Context Details',
      breadcrumb: { parent: '/contexts', parentLabel: 'nav.contexts' }
    }
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { requiresAuth: true, title: 'Settings' }
  },
  {
    path: '/settings/data-export',
    name: 'data-export',
    component: () => import('@/views/DataExportView.vue'),
    meta: {
      requiresAuth: true,
      title: 'Data Export',
      breadcrumb: { parent: '/settings', parentLabel: 'nav.settings' }
    }
  },
  {
    path: '/oauth/authorize',
    name: 'oauth-consent',
    component: () => import('@/views/OAuthConsentView.vue'),
    meta: { requiresAuth: true, title: 'Authorization Request' }
  },
  {
    path: '/oauth/callback',
    name: 'oauth-callback',
    component: () => import('@/views/OAuthCallbackView.vue'),
    meta: { title: 'Authorization' }
  },
  {
    path: '/auth/social/:provider/callback',
    name: 'social-auth-callback',
    component: () => import('@/views/SocialAuthCallbackView.vue'),
    meta: { title: 'Social Login' }
  },
  // Audit trail (any authenticated user)
  {
    path: '/audit',
    name: 'audit-trail',
    component: () => import('@/views/AuditTrailView.vue'),
    meta: { requiresAuth: true, title: 'Audit Trail' }
  },
  // Admin routes
  {
    path: '/admin/oauth/clients',
    name: 'admin-oauth-clients',
    component: () => import('@/views/admin/AdminOAuthClientsView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'OAuth Clients' }
  },
  {
    path: '/admin/oauth/clients/new',
    name: 'admin-oauth-client-create',
    component: () => import('@/views/admin/AdminOAuthClientCreateView.vue'),
    meta: {
      requiresAuth: true,
      requiresAdmin: true,
      title: 'Create OAuth Client',
      breadcrumb: { parent: '/admin/oauth/clients', parentLabel: 'nav.adminOAuthClients' }
    }
  },
  {
    path: '/admin/oauth/clients/:clientId/edit',
    name: 'admin-oauth-client-edit',
    component: () => import('@/views/admin/AdminOAuthClientEditView.vue'),
    meta: {
      requiresAuth: true,
      requiresAdmin: true,
      title: 'Edit OAuth Client',
      breadcrumb: { parent: '/admin/oauth/clients', parentLabel: 'nav.adminOAuthClients' }
    }
  },
  {
    path: '/admin/audit/verify',
    name: 'admin-audit-verify',
    component: () => import('@/views/admin/AdminAuditVerifyView.vue'),
    meta: {
      requiresAuth: true,
      requiresAdmin: true,
      title: 'Audit Integrity',
      breadcrumb: { parent: '/admin/oauth/clients', parentLabel: 'nav.adminOAuthClients' }
    }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: 'Page Not Found' }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(_to, _from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    }
    return { top: 0 }
  }
})

// Navigation guard for authentication
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  // Initialize auth on first navigation if not done
  if (!authStore.isInitialized && authStore.hasStoredSession()) {
    await authService.initializeAuth()
  } else if (!authStore.isInitialized) {
    authStore.setInitialized(true)
  }

  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth)
  const requiresGuest = to.matched.some((record) => record.meta.requiresGuest)
  const requiresVerified = to.matched.some((record) => record.meta.requiresVerified)
  const requiresAdmin = to.matched.some((record) => record.meta.requiresAdmin)

  // Update document title
  const appName = 'Identity Management'
  document.title = to.meta.title ? `${to.meta.title} | ${appName}` : appName

  // Check authentication requirements
  if (requiresAuth && !authStore.isAuthenticated) {
    // Store intended destination for redirect after login
    next({ name: 'login', query: { redirect: to.fullPath } })
    return
  }

  // Check admin requirement
  if (requiresAdmin && !authStore.isAdmin) {
    next({ name: 'home' })
    return
  }

  // Check verified requirement
  if (requiresVerified && !authStore.isEmailVerified) {
    next({ name: 'verify-email' })
    return
  }

  // Redirect authenticated users away from guest-only pages
  if (requiresGuest && authStore.isAuthenticated) {
    next({ name: 'profile' })
    return
  }

  next()
})

export default router
