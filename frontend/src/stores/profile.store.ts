/**
 * Profile store managing base profile, identity names, and context profiles.
 *
 * Key concepts:
 * - Base profile contains core identity data
 * - Context profiles override specific fields (null = inherit from base)
 * - Resolved profiles merge base + context with inheritance engine
 * - Identity names support multilingual values with JSONB storage
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  ProfileResponse,
  IdentityName,
  ContextProfileResponse,
  ResolvedProfileResponse
} from '@/types'

export const useProfileStore = defineStore('profile', () => {
  // State
  const profile = ref<ProfileResponse | null>(null)
  const identityNames = ref<IdentityName[]>([])
  const contexts = ref<ContextProfileResponse[]>([])
  const activeContextId = ref<string | null>(null)
  const resolvedProfile = ref<ResolvedProfileResponse | null>(null)
  const isLoading = ref<boolean>(false)
  const error = ref<string | null>(null)

  // Computed
  const activeContext = computed(() =>
    contexts.value.find((c) => c.id === activeContextId.value) ?? null
  )

  const activeContexts = computed(() => contexts.value.filter((c) => c.is_active))

  const primaryName = computed(() =>
    identityNames.value.find((n) => n.is_primary && !n.is_deprecated) ?? null
  )

  const displayName = computed(() => {
    // Priority: resolved profile > primary name > email
    if (resolvedProfile.value?.display_name) {
      return resolvedProfile.value.display_name
    }
    if (primaryName.value) {
      const lang = navigator.language.split('-')[0]
      return (
        primaryName.value.name_value[lang] ??
        primaryName.value.name_value['en'] ??
        Object.values(primaryName.value.name_value)[0]
      )
    }
    return profile.value?.primary_email ?? ''
  })

  const hasProfile = computed(() => !!profile.value)
  const hasContexts = computed(() => contexts.value.length > 0)

  // Actions
  function setProfile(p: ProfileResponse): void {
    profile.value = p
    error.value = null
  }

  function setIdentityNames(names: IdentityName[]): void {
    identityNames.value = names
  }

  function addIdentityName(name: IdentityName): void {
    identityNames.value.push(name)
  }

  function updateIdentityName(id: string, updates: Partial<IdentityName>): void {
    const index = identityNames.value.findIndex((n) => n.id === id)
    if (index !== -1) {
      identityNames.value[index] = { ...identityNames.value[index], ...updates }
    }
  }

  function setContexts(ctxs: ContextProfileResponse[]): void {
    contexts.value = ctxs
  }

  function addContext(ctx: ContextProfileResponse): void {
    contexts.value.push(ctx)
  }

  function updateContext(context: ContextProfileResponse): void {
    const index = contexts.value.findIndex((c) => c.id === context.id)
    if (index !== -1) {
      contexts.value[index] = context
    }
  }

  function removeContext(id: string): void {
    contexts.value = contexts.value.filter((c) => c.id !== id)
    if (activeContextId.value === id) {
      activeContextId.value = null
      resolvedProfile.value = null
    }
  }

  function setActiveContext(contextId: string | null): void {
    activeContextId.value = contextId
  }

  function setResolvedProfile(resolved: ResolvedProfileResponse | null): void {
    resolvedProfile.value = resolved
  }

  function setLoading(loading: boolean): void {
    isLoading.value = loading
  }

  function setError(err: string | null): void {
    error.value = err
  }

  function clearProfile(): void {
    profile.value = null
    identityNames.value = []
    contexts.value = []
    activeContextId.value = null
    resolvedProfile.value = null
    error.value = null
  }

  return {
    // State
    profile,
    identityNames,
    contexts,
    activeContextId,
    resolvedProfile,
    isLoading,
    error,

    // Computed
    activeContext,
    activeContexts,
    primaryName,
    displayName,
    hasProfile,
    hasContexts,

    // Actions
    setProfile,
    setIdentityNames,
    addIdentityName,
    updateIdentityName,
    setContexts,
    addContext,
    updateContext,
    removeContext,
    setActiveContext,
    setResolvedProfile,
    setLoading,
    setError,
    clearProfile
  }
})
