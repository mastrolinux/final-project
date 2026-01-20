/**
 * UI store managing global UI state: loading states, notifications, theme.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type NotificationType = 'success' | 'error' | 'warning' | 'info'

export interface Notification {
  id: string
  type: NotificationType
  message: string
  duration?: number
}

export type Theme = 'light' | 'dark' | 'system'

export const useUiStore = defineStore('ui', () => {
  // State
  const isLoading = ref<boolean>(false)
  const loadingMessage = ref<string | null>(null)
  const notifications = ref<Notification[]>([])
  const theme = ref<Theme>((localStorage.getItem('theme') as Theme) ?? 'system')
  const sidebarOpen = ref<boolean>(true)

  // Computed
  const hasNotifications = computed(() => notifications.value.length > 0)

  const effectiveTheme = computed(() => {
    if (theme.value === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }
    return theme.value
  })

  // Actions
  function setLoading(loading: boolean, message?: string): void {
    isLoading.value = loading
    loadingMessage.value = message ?? null
  }

  function showNotification(notification: Omit<Notification, 'id'>): string {
    const id = `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    const newNotification: Notification = {
      ...notification,
      id,
      duration: notification.duration ?? 5000
    }
    notifications.value.push(newNotification)

    // Auto-remove after duration
    if (newNotification.duration && newNotification.duration > 0) {
      setTimeout(() => {
        removeNotification(id)
      }, newNotification.duration)
    }

    return id
  }

  function removeNotification(id: string): void {
    notifications.value = notifications.value.filter((n) => n.id !== id)
  }

  function clearNotifications(): void {
    notifications.value = []
  }

  function setTheme(newTheme: Theme): void {
    theme.value = newTheme
    localStorage.setItem('theme', newTheme)

    // Apply theme class to document
    const root = document.documentElement
    root.classList.remove('light', 'dark')
    root.classList.add(effectiveTheme.value)
  }

  function toggleSidebar(): void {
    sidebarOpen.value = !sidebarOpen.value
  }

  function setSidebarOpen(open: boolean): void {
    sidebarOpen.value = open
  }

  // Convenience methods for common notification types
  function showSuccess(message: string, duration?: number): string {
    return showNotification({ type: 'success', message, duration })
  }

  function showError(message: string, duration?: number): string {
    return showNotification({ type: 'error', message, duration: duration ?? 8000 })
  }

  function showWarning(message: string, duration?: number): string {
    return showNotification({ type: 'warning', message, duration })
  }

  function showInfo(message: string, duration?: number): string {
    return showNotification({ type: 'info', message, duration })
  }

  // Alias for backward compatibility
  const addNotification = showNotification

  return {
    // State
    isLoading,
    loadingMessage,
    notifications,
    theme,
    sidebarOpen,

    // Computed
    hasNotifications,
    effectiveTheme,

    // Actions
    setLoading,
    showNotification,
    addNotification,
    removeNotification,
    clearNotifications,
    setTheme,
    toggleSidebar,
    setSidebarOpen,
    showSuccess,
    showError,
    showWarning,
    showInfo
  }
})
