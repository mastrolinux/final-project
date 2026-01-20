/**
 * Axios API client with JWT authentication interceptors.
 *
 * Features:
 * - Automatic Authorization header injection
 * - Accept-Language header for multilingual name resolution
 * - 401 response handling with automatic token refresh
 * - Request queuing during token refresh to prevent race conditions
 * - 410 Gone handling for expired context profiles
 */

import axios, {
  type AxiosInstance,
  type AxiosError,
  type InternalAxiosRequestConfig
} from 'axios'
import { useAuthStore } from '@/stores/auth.store'
import { useUiStore } from '@/stores/ui.store'
import type { RefreshTokenResponse } from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const API_VERSION = import.meta.env.VITE_API_VERSION || 'v1'

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api/${API_VERSION}`,
  headers: {
    'Content-Type': 'application/json'
  },
  timeout: 30000
})

// Track refresh state to prevent concurrent refresh attempts
let isRefreshing = false
let failedQueue: Array<{
  resolve: (value?: unknown) => void
  reject: (reason?: unknown) => void
}> = []

/**
 * Process queued requests after token refresh completes.
 */
function processQueue(error: Error | null, token: string | null = null): void {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

/**
 * Get router instance lazily to avoid circular imports.
 */
async function getRouter() {
  const { default: router } = await import('@/router')
  return router
}

// Request interceptor: Add Authorization and Accept-Language headers
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const authStore = useAuthStore()

    if (authStore.accessToken) {
      config.headers.Authorization = `Bearer ${authStore.accessToken}`
    }

    // Add Accept-Language for multilingual name resolution
    // Backend uses 4-tier fallback: Accept-Language > preferred_language > 'en' > first available
    if (authStore.preferredLanguage) {
      config.headers['Accept-Language'] = `${authStore.preferredLanguage},en;q=0.9`
    }

    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor: Handle 401 (token refresh) and 410 (expired context)
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean
    }

    // Handle 401 Unauthorized - attempt token refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      const authStore = useAuthStore()

      // If no refresh token available, redirect to login
      if (!authStore.refreshToken) {
        authStore.logout()
        const router = await getRouter()
        router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
        return Promise.reject(error)
      }

      // If already refreshing, queue this request
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        // Call refresh endpoint directly to avoid interceptor loop
        const response = await axios.post<RefreshTokenResponse>(
          `${API_BASE_URL}/api/${API_VERSION}/auth/refresh`,
          { refresh_token: authStore.refreshToken }
        )

        const { access_token, refresh_token } = response.data
        authStore.setTokens(access_token, refresh_token)

        processQueue(null, access_token)

        originalRequest.headers.Authorization = `Bearer ${access_token}`
        return api(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError as Error, null)
        authStore.logout()
        const router = await getRouter()
        router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    // Handle 410 Gone - context profile has expired
    if (error.response?.status === 410) {
      const uiStore = useUiStore()
      uiStore.showWarning('This context profile has expired and is no longer accessible.')
    }

    // Handle 403 Forbidden
    if (error.response?.status === 403) {
      const uiStore = useUiStore()
      uiStore.showError('You do not have permission to perform this action.')
    }

    return Promise.reject(error)
  }
)

export default api

/**
 * Helper to extract error message from API error response.
 */
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data
    if (typeof data?.detail === 'string') {
      return data.detail
    }
    if (typeof data?.detail?.message === 'string') {
      return data.detail.message
    }
    if (data?.error_description) {
      return data.error_description
    }
    if (Array.isArray(data?.detail)) {
      // Validation errors
      return data.detail.map((e: { msg: string }) => e.msg).join(', ')
    }
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'An unexpected error occurred'
}
