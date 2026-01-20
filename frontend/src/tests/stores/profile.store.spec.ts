/**
 * Unit tests for profile store.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useProfileStore } from '@/stores/profile.store'
import type { ProfileResponse, ContextProfileResponse } from '@/types'

describe('useProfileStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('initial state', () => {
    it('should have null profile initially', () => {
      const store = useProfileStore()
      expect(store.profile).toBeNull()
    })

    it('should have empty contexts array initially', () => {
      const store = useProfileStore()
      expect(store.contexts).toEqual([])
    })

    it('should have null active context ID initially', () => {
      const store = useProfileStore()
      expect(store.activeContextId).toBeNull()
    })

    it('should not be loading initially', () => {
      const store = useProfileStore()
      expect(store.isLoading).toBe(false)
    })
  })

  describe('setProfile', () => {
    it('should set profile data', () => {
      const store = useProfileStore()
      const profile: ProfileResponse = {
        id: 'profile-123',
        user_id: 'user-123',
        account_type: 'verified',
        primary_email: 'test@example.com',
        primary_phone: null,
        preferred_language: 'en',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        deleted_at: null
      }

      store.setProfile(profile)

      expect(store.profile).toEqual(profile)
      expect(store.hasProfile).toBe(true)
    })
  })

  describe('setContexts', () => {
    it('should set contexts array', () => {
      const store = useProfileStore()
      const contexts: ContextProfileResponse[] = [
        {
          id: 'ctx-1',
          user_id: 'user-123',
          context_type: 'professional',
          context_name: 'Work',
          display_name_override: null,
          email_override: 'work@example.com',
          phone_override: null,
          bio: null,
          is_active: true,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
          deleted_at: null,
          valid_from: '2024-01-01T00:00:00Z',
          valid_to: null
        }
      ]

      store.setContexts(contexts)

      expect(store.contexts).toEqual(contexts)
      expect(store.hasContexts).toBe(true)
    })
  })

  describe('addContext', () => {
    it('should add a context to the array', () => {
      const store = useProfileStore()
      const context: ContextProfileResponse = {
        id: 'ctx-1',
        user_id: 'user-123',
        context_type: 'social',
        context_name: 'Social Media',
        display_name_override: 'Nickname',
        email_override: null,
        phone_override: null,
        bio: 'My social profile',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        deleted_at: null,
        valid_from: '2024-01-01T00:00:00Z',
        valid_to: null
      }

      store.addContext(context)

      expect(store.contexts).toHaveLength(1)
      expect(store.contexts[0]).toEqual(context)
    })
  })

  describe('updateContext', () => {
    it('should update an existing context', () => {
      const store = useProfileStore()
      const original: ContextProfileResponse = {
        id: 'ctx-1',
        user_id: 'user-123',
        context_type: 'professional',
        context_name: 'Work',
        display_name_override: null,
        email_override: null,
        phone_override: null,
        bio: null,
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        deleted_at: null,
        valid_from: '2024-01-01T00:00:00Z',
        valid_to: null
      }

      store.setContexts([original])

      const updated: ContextProfileResponse = {
        ...original,
        context_name: 'Updated Work',
        bio: 'Professional context',
        updated_at: '2024-01-02T00:00:00Z'
      }

      store.updateContext(updated)

      expect(store.contexts[0].context_name).toBe('Updated Work')
      expect(store.contexts[0].bio).toBe('Professional context')
    })

    it('should not modify array if context not found', () => {
      const store = useProfileStore()
      const context: ContextProfileResponse = {
        id: 'ctx-1',
        user_id: 'user-123',
        context_type: 'professional',
        context_name: 'Work',
        display_name_override: null,
        email_override: null,
        phone_override: null,
        bio: null,
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        deleted_at: null,
        valid_from: '2024-01-01T00:00:00Z',
        valid_to: null
      }

      store.setContexts([context])

      const nonExistent: ContextProfileResponse = {
        ...context,
        id: 'ctx-999',
        context_name: 'Nonexistent'
      }

      store.updateContext(nonExistent)

      expect(store.contexts).toHaveLength(1)
      expect(store.contexts[0].context_name).toBe('Work')
    })
  })

  describe('removeContext', () => {
    it('should remove a context by ID', () => {
      const store = useProfileStore()
      const contexts: ContextProfileResponse[] = [
        {
          id: 'ctx-1',
          user_id: 'user-123',
          context_type: 'professional',
          context_name: 'Work',
          display_name_override: null,
          email_override: null,
          phone_override: null,
          bio: null,
          is_active: true,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
          deleted_at: null,
          valid_from: '2024-01-01T00:00:00Z',
          valid_to: null
        },
        {
          id: 'ctx-2',
          user_id: 'user-123',
          context_type: 'social',
          context_name: 'Social',
          display_name_override: null,
          email_override: null,
          phone_override: null,
          bio: null,
          is_active: true,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
          deleted_at: null,
          valid_from: '2024-01-01T00:00:00Z',
          valid_to: null
        }
      ]

      store.setContexts(contexts)
      store.removeContext('ctx-1')

      expect(store.contexts).toHaveLength(1)
      expect(store.contexts[0].id).toBe('ctx-2')
    })
  })

  describe('clearProfile', () => {
    it('should clear all profile data', () => {
      const store = useProfileStore()

      store.setProfile({
        id: 'profile-123',
        user_id: 'user-123',
        account_type: 'verified',
        primary_email: 'test@example.com',
        primary_phone: null,
        preferred_language: 'en',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        deleted_at: null
      })

      store.setContexts([
        {
          id: 'ctx-1',
          user_id: 'user-123',
          context_type: 'professional',
          context_name: 'Work',
          display_name_override: null,
          email_override: null,
          phone_override: null,
          bio: null,
          is_active: true,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
          deleted_at: null,
          valid_from: '2024-01-01T00:00:00Z',
          valid_to: null
        }
      ])

      store.setActiveContext('ctx-1')

      store.clearProfile()

      expect(store.profile).toBeNull()
      expect(store.contexts).toEqual([])
      expect(store.activeContextId).toBeNull()
    })
  })

  describe('activeContext', () => {
    it('should return the active context', () => {
      const store = useProfileStore()
      const contexts: ContextProfileResponse[] = [
        {
          id: 'ctx-1',
          user_id: 'user-123',
          context_type: 'professional',
          context_name: 'Work',
          display_name_override: null,
          email_override: null,
          phone_override: null,
          bio: null,
          is_active: true,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
          deleted_at: null,
          valid_from: '2024-01-01T00:00:00Z',
          valid_to: null
        },
        {
          id: 'ctx-2',
          user_id: 'user-123',
          context_type: 'social',
          context_name: 'Social',
          display_name_override: null,
          email_override: null,
          phone_override: null,
          bio: null,
          is_active: true,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
          deleted_at: null,
          valid_from: '2024-01-01T00:00:00Z',
          valid_to: null
        }
      ]

      store.setContexts(contexts)
      store.setActiveContext('ctx-2')

      expect(store.activeContext?.context_name).toBe('Social')
    })

    it('should return null if no active context', () => {
      const store = useProfileStore()
      expect(store.activeContext).toBeNull()
    })
  })
})
