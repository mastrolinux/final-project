<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore, useProfileStore, useUiStore } from '@/stores'
import { contextService, getErrorMessage } from '@/services'
import { CONTEXT_TYPES, type ContextType } from '@/types'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()
const profileStore = useProfileStore()
const uiStore = useUiStore()

const isSubmitting = ref(false)
const error = ref<string | null>(null)

const form = ref({
  context_type: 'professional' as ContextType,
  context_name: '',
  display_name_override: '',
  email_override: '',
  phone_override: '',
  bio: '',
  is_active: true
})

// Pseudonymous accounts cannot create legal or healthcare contexts
const availableContextTypes = computed(() => {
  if (authStore.accountType === 'pseudonymous') {
    return CONTEXT_TYPES.filter((type) => type !== 'legal' && type !== 'healthcare')
  }
  return CONTEXT_TYPES
})

function getContextBadgeClass(contextType: ContextType): string {
  return `badge badge-${contextType}`
}

async function handleSubmit() {
  if (!authStore.userId) return

  isSubmitting.value = true
  error.value = null

  try {
    const newContext = await contextService.create(authStore.userId, {
      context_type: form.value.context_type,
      context_name: form.value.context_name,
      display_name_override: form.value.display_name_override || undefined,
      email_override: form.value.email_override || undefined,
      phone_override: form.value.phone_override || undefined,
      bio: form.value.bio || undefined,
      is_active: form.value.is_active
    })

    profileStore.addContext(newContext)

    uiStore.addNotification({
      type: 'success',
      message: t('context.createSuccess')
    })

    router.push({ name: 'context-detail', params: { id: newContext.id } })
  } catch (err) {
    error.value = getErrorMessage(err)
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="context-create-view">
    <div class="container container-md">
      <div class="page-header">
        <router-link to="/contexts" class="back-link">
          &larr; {{ t('common.back') }}
        </router-link>
        <h1 class="page-title">{{ t('context.createNew') }}</h1>
        <p class="page-description">{{ t('context.createDescription') }}</p>
      </div>

      <div class="card">
        <div class="card-body">
          <form @submit.prevent="handleSubmit" class="create-form">
            <div v-if="error" class="alert alert-error">
              {{ error }}
            </div>

            <div class="form-group">
              <label class="form-label">{{ t('context.type') }}</label>
              <div class="context-type-grid">
                <label
                  v-for="contextType in availableContextTypes"
                  :key="contextType"
                  class="context-type-option"
                  :class="{ selected: form.context_type === contextType }"
                >
                  <input
                    type="radio"
                    v-model="form.context_type"
                    :value="contextType"
                    class="sr-only"
                  />
                  <span :class="getContextBadgeClass(contextType)">
                    {{ t(`context.types.${contextType}`) }}
                  </span>
                  <span class="context-type-description">
                    {{ t(`context.typeDescriptions.${contextType}`) }}
                  </span>
                </label>
              </div>
              <p
                v-if="authStore.accountType === 'pseudonymous'"
                class="form-hint text-warning"
              >
                {{ t('context.pseudonymousRestriction') }}
              </p>
            </div>

            <div class="form-group">
              <label for="context_name" class="form-label">{{ t('context.name') }} *</label>
              <input
                id="context_name"
                v-model="form.context_name"
                type="text"
                class="form-input"
                :placeholder="t('context.namePlaceholder')"
                required
              />
              <p class="form-hint">{{ t('context.nameHint') }}</p>
            </div>

            <hr class="form-divider" />

            <h3 class="form-section-title">{{ t('context.overrides') }}</h3>
            <p class="form-section-description">{{ t('context.overridesDescription') }}</p>

            <div class="form-group">
              <label for="display_name" class="form-label">{{
                t('context.displayNameOverride')
              }}</label>
              <input
                id="display_name"
                v-model="form.display_name_override"
                type="text"
                class="form-input"
                :placeholder="t('context.inheritFromProfile')"
              />
            </div>

            <div class="form-group">
              <label for="email" class="form-label">{{ t('context.emailOverride') }}</label>
              <input
                id="email"
                v-model="form.email_override"
                type="email"
                class="form-input"
                :placeholder="t('context.inheritFromProfile')"
              />
            </div>

            <div class="form-group">
              <label for="phone" class="form-label">{{ t('context.phoneOverride') }}</label>
              <input
                id="phone"
                v-model="form.phone_override"
                type="tel"
                class="form-input"
                :placeholder="t('context.inheritFromProfile')"
              />
            </div>

            <div class="form-group">
              <label for="bio" class="form-label">{{ t('context.bio') }}</label>
              <textarea
                id="bio"
                v-model="form.bio"
                class="form-input form-textarea"
                rows="4"
                :placeholder="t('context.bioPlaceholder')"
              ></textarea>
            </div>

            <div class="form-group">
              <label class="form-checkbox">
                <input type="checkbox" v-model="form.is_active" />
                <span>{{ t('context.isActive') }}</span>
              </label>
              <p class="form-hint">{{ t('context.isActiveHint') }}</p>
            </div>

            <div class="form-actions">
              <router-link to="/contexts" class="btn btn-outline">
                {{ t('common.cancel') }}
              </router-link>
              <button type="submit" class="btn btn-primary" :disabled="isSubmitting">
                {{ isSubmitting ? t('common.creating') : t('context.create') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.context-create-view {
  padding: var(--spacing-6) 0;
}

.page-header {
  margin-bottom: var(--spacing-6);
}

.back-link {
  display: inline-block;
  color: var(--text-secondary);
  text-decoration: none;
  margin-bottom: var(--spacing-2);
}

.back-link:hover {
  color: var(--text-primary);
}

.create-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-5);
}

.context-type-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--spacing-3);
  margin-top: var(--spacing-2);
}

.context-type-option {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
  padding: var(--spacing-3);
  border: 2px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.context-type-option:hover {
  border-color: var(--color-primary-300);
}

.context-type-option.selected {
  border-color: var(--color-primary-500);
  background-color: var(--color-primary-50);
}

.context-type-description {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.form-divider {
  border: none;
  border-top: 1px solid var(--border-color);
  margin: var(--spacing-2) 0;
}

.form-section-title {
  font-size: var(--font-size-lg);
  margin-bottom: var(--spacing-1);
}

.form-section-description {
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-2);
}

.form-hint {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  margin-top: var(--spacing-1);
}

.text-warning {
  color: var(--color-warning-600);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-3);
  margin-top: var(--spacing-4);
}

/* Screen reader only class */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
