<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { contextService, getErrorMessage } from '@/services'
import type { ResolvedProfileResponse } from '@/types'
import BaseBadge from '@/components/common/BaseBadge.vue'

const props = defineProps<{
  userId: string
  contextId: string | null
  selectedScopes: string[]
}>()

const { t } = useI18n()

const resolved = ref<ResolvedProfileResponse | null>(null)
const isLoading = ref(false)
const error = ref<string | null>(null)

/**
 * Mapping from scope names to the resolved profile fields they expose.
 * Each entry maps to a { key, label } pair referencing ResolvedProfileResponse fields.
 */
const SCOPE_FIELD_MAP: Record<string, { key: keyof ResolvedProfileResponse; label: string }[]> = {
  openid: [{ key: 'user_id', label: 'User ID' }],
  'profile:read:basic': [
    { key: 'display_name', label: 'Display name' },
    { key: 'account_type', label: 'Account type' },
    { key: 'avatar_url', label: 'Avatar' }
  ],
  'profile:read:email': [{ key: 'email', label: 'Email' }],
  email: [{ key: 'email', label: 'Email' }],
  'profile:read:phone': [{ key: 'phone', label: 'Phone' }],
  phone: [{ key: 'phone', label: 'Phone' }],
  'profile:read:full': [
    { key: 'display_name', label: 'Display name' },
    { key: 'email', label: 'Email' },
    { key: 'phone', label: 'Phone' },
    { key: 'bio', label: 'Bio' },
    { key: 'avatar_url', label: 'Avatar' },
    { key: 'account_type', label: 'Account type' }
  ],
  'contexts:read': [
    { key: 'context_type', label: 'Context type' },
    { key: 'context_name', label: 'Context name' }
  ]
}

interface PreviewField {
  label: string
  value: string | null
  isOverride: boolean
}

function getPreviewFields(): PreviewField[] {
  if (!resolved.value) return []

  const seen = new Set<string>()
  const fields: PreviewField[] = []

  for (const scope of props.selectedScopes) {
    const mappings = SCOPE_FIELD_MAP[scope]
    if (!mappings) continue

    for (const mapping of mappings) {
      if (seen.has(mapping.key)) continue
      seen.add(mapping.key)

      const rawValue = resolved.value[mapping.key]
      const value = rawValue != null ? String(rawValue) : null

      // A field is an override if the context provides it (non-null context_type
      // and the field is one of the override fields: display_name, email, phone, bio)
      const overrideFields = new Set(['display_name', 'email', 'phone', 'bio'])
      const isOverride = resolved.value.context_type != null && overrideFields.has(mapping.key)

      fields.push({ label: mapping.label, value, isOverride })
    }
  }

  return fields
}

watch(
  () => props.contextId,
  async (newId) => {
    if (!newId) {
      resolved.value = null
      return
    }

    isLoading.value = true
    error.value = null

    try {
      resolved.value = await contextService.getResolved(props.userId, newId)
    } catch (err) {
      error.value = getErrorMessage(err)
      resolved.value = null
    } finally {
      isLoading.value = false
    }
  },
  { immediate: true }
)
</script>

<template>
  <div class="context-preview">
    <!-- Loading -->
    <div v-if="isLoading" class="preview-loading">
      <div class="spinner-sm"></div>
      <span>{{ t('common.loading') }}</span>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="preview-error">
      {{ error }}
    </div>

    <!-- No context selected -->
    <div v-else-if="!contextId" class="preview-info">
      {{ t('oauth.fieldFromBase') }}
    </div>

    <!-- Preview fields -->
    <div v-else-if="resolved" class="preview-fields">
      <div
        v-for="field in getPreviewFields()"
        :key="field.label"
        class="preview-field"
      >
        <span class="field-label">{{ field.label }}</span>
        <span class="field-value">{{ field.value || '-' }}</span>
        <BaseBadge
          v-if="field.isOverride"
          variant="primary"
          size="sm"
        >
          {{ t('oauth.fieldFromContext') }}
        </BaseBadge>
        <BaseBadge
          v-else
          variant="neutral"
          size="sm"
        >
          {{ t('oauth.fieldFromBase') }}
        </BaseBadge>
      </div>
    </div>
  </div>
</template>

<style scoped>
.context-preview {
  min-height: 40px;
}

.preview-loading {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
  padding: var(--spacing-2) 0;
}

.spinner-sm {
  width: 16px;
  height: 16px;
  border: 2px solid var(--color-gray-200);
  border-top-color: var(--color-primary-600);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.preview-error {
  color: var(--color-error-600);
  font-size: var(--font-size-sm);
  padding: var(--spacing-2) 0;
}

.preview-info {
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
  padding: var(--spacing-2) 0;
}

.preview-fields {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.preview-field {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-2) var(--spacing-3);
  background-color: var(--bg-secondary);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
}

.field-label {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  min-width: 100px;
  flex-shrink: 0;
}

.field-value {
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
