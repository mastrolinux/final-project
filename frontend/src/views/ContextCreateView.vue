<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore, useProfileStore, useUiStore } from '@/stores'
import { contextService, profileService, getErrorMessage } from '@/services'
import { CONTEXT_TYPES, CONTEXT_TYPE_META, type ContextType } from '@/types'
import BaseInput from '@/components/common/BaseInput.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseBadge from '@/components/common/BaseBadge.vue'
import AvatarUpload from '@/components/profile/AvatarUpload.vue'
import AppBreadcrumb from '@/components/layout/AppBreadcrumb.vue'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()
const profileStore = useProfileStore()
const uiStore = useUiStore()

const isSubmitting = ref(false)
const error = ref<string | null>(null)
const pendingAvatarFile = ref<File | null>(null)

const form = reactive({
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

// Non-deprecated identity names for the "pick from names" chips
const availableNames = computed(() =>
  profileStore.identityNames.filter((n) => !n.is_deprecated)
)

function resolveNameValue(nameValue: Record<string, string>): string {
  const lang = navigator.language.split('-')[0]
  return nameValue[lang] ?? nameValue['en'] ?? Object.values(nameValue)[0] ?? ''
}

function pickName(resolved: string) {
  form.display_name_override = resolved
}

onMounted(async () => {
  if (authStore.userId && profileStore.identityNames.length === 0) {
    try {
      const names = await profileService.getNames(authStore.userId)
      profileStore.setIdentityNames(names)
    } catch {
      // Non-critical: chips won't show, text input still works
    }
  }
})

async function handleSubmit() {
  if (!authStore.userId) return

  isSubmitting.value = true
  error.value = null

  try {
    const newContext = await contextService.create(authStore.userId, {
      context_type: form.context_type,
      context_name: form.context_name,
      display_name_override: form.display_name_override || undefined,
      email_override: form.email_override || undefined,
      phone_override: form.phone_override || undefined,
      bio: form.bio || undefined,
      is_active: form.is_active
    })

    profileStore.addContext(newContext)

    // Upload pending avatar if the user selected one during creation.
    // The upload requires a context ID, so it runs after create succeeds.
    if (pendingAvatarFile.value && authStore.userId) {
      try {
        const result = await contextService.uploadAvatar(
          authStore.userId,
          newContext.id,
          pendingAvatarFile.value
        )
        profileStore.setContextAvatar(newContext.id, result.avatar_url, result.avatar_thumbnail_url)
      } catch {
        // Context was created successfully but avatar upload failed.
        // User can retry from the context detail page.
        uiStore.addNotification({
          type: 'warning',
          message: t('context.avatar.uploadFailed')
        })
        router.push({ name: 'context-detail', params: { id: newContext.id } })
        return
      }
    }

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

function handleAvatarSelect(file: File) {
  pendingAvatarFile.value = file
}

function handleAvatarClear() {
  pendingAvatarFile.value = null
}

const handleCancel = () => {
  router.back()
}
</script>

<template>
  <div class="page-view">
    <div class="container container-lg">
      <AppBreadcrumb />
      <div class="page-header">
        <h1 class="page-title">{{ t('context.createNew') }}</h1>
        <p class="page-description">{{ t('context.createDescription') }}</p>
      </div>

      <div v-if="error" class="alert alert-error create-error">
        {{ error }}
      </div>

      <div class="create-grid">
        <!-- Main Form -->
        <div class="form-column">
          <BaseCard>
            <form @submit.prevent="handleSubmit">
              <!-- Context Type Selection -->
              <div class="form-section">
                <label class="section-label">{{ t('context.type') }}</label>
                <div class="type-grid">
                  <div
                    v-for="contextType in availableContextTypes"
                    :key="contextType"
                    class="context-type-card"
                    :class="{ 'is-selected': form.context_type === contextType }"
                    @click="form.context_type = contextType"
                  >
                    <div class="card-content">
                      <div class="card-info">
                        <div class="card-title">
                          {{ t(`context.types.${contextType}`) }}
                          <BaseBadge :variant="contextType" size="sm">
                            {{ CONTEXT_TYPE_META[contextType].label }}
                          </BaseBadge>
                        </div>
                        <div class="card-description">
                          {{ t(`context.typeDescriptions.${contextType}`) }}
                        </div>
                      </div>
                      <div v-if="form.context_type === contextType" class="card-check">
                        <svg class="check-icon" viewBox="0 0 20 20" fill="currentColor">
                          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                        </svg>
                      </div>
                    </div>
                  </div>
                </div>
                <p v-if="authStore.accountType === 'pseudonymous'" class="pseudo-warning">
                  {{ t('context.pseudonymousRestriction') }}
                </p>
              </div>

              <!-- Basic Info -->
              <div class="form-section">
                <h3 class="section-heading">Basic Information</h3>
                <BaseInput
                  v-model="form.context_name"
                  id="context_name"
                  :label="t('context.name')"
                  :placeholder="t('context.namePlaceholder')"
                  required
                  :hint="t('context.nameHint')"
                />

                <div class="form-group">
                  <label class="checkbox-group">
                    <input type="checkbox" v-model="form.is_active" class="checkbox-input" />
                    <span class="checkbox-text">{{ t('context.isActive') }}</span>
                  </label>
                  <p class="checkbox-hint">{{ t('context.isActiveHint') }}</p>
                </div>
              </div>

              <!-- Overrides -->
              <div class="form-section">
                <div class="overrides-header">
                  <h3 class="section-heading">{{ t('context.overrides') }}</h3>
                  <span class="optional-badge">Optional</span>
                </div>
                <p class="overrides-description">{{ t('context.overridesDescription') }}</p>

                <BaseInput
                  v-model="form.display_name_override"
                  id="display_name"
                  :label="t('context.displayNameOverride')"
                  :placeholder="t('context.inheritFromProfile')"
                />

                <div v-if="availableNames.length > 0" class="name-chips-section">
                  <span class="chips-label">{{ t('context.pickFromNames') }}</span>
                  <div class="name-chips">
                    <button
                      v-for="name in availableNames"
                      :key="name.id"
                      type="button"
                      class="name-chip"
                      @click="pickName(resolveNameValue(name.name_value))"
                    >
                      <BaseBadge variant="primary" size="sm">{{ name.name_type }}</BaseBadge>
                      <span class="chip-name-text">{{ resolveNameValue(name.name_value) }}</span>
                    </button>
                  </div>
                </div>

                <BaseInput
                  v-model="form.email_override"
                  id="email"
                  type="email"
                  :label="t('context.emailOverride')"
                  :placeholder="t('context.inheritFromProfile')"
                />

                <BaseInput
                  v-model="form.phone_override"
                  id="phone"
                  type="tel"
                  :label="t('context.phoneOverride')"
                  :placeholder="t('context.inheritFromProfile')"
                />

                <div class="form-group">
                  <label for="bio" class="textarea-label">{{ t('context.bio') }}</label>
                  <textarea
                    id="bio"
                    v-model="form.bio"
                    rows="3"
                    class="textarea-field"
                    :placeholder="t('context.bioPlaceholder')"
                  ></textarea>
                </div>

                <div class="form-group avatar-override-group">
                  <label class="textarea-label">{{ t('context.avatar.override') }}</label>
                  <AvatarUpload
                    :currentUrl="null"
                    :name="form.display_name_override || profileStore.displayName"
                    :isUploading="isSubmitting"
                    deferred
                    @upload="handleAvatarSelect"
                    @remove="handleAvatarClear"
                  />
                </div>
              </div>

              <div class="form-footer">
                <BaseButton variant="ghost" @click="handleCancel" :disabled="isSubmitting">
                  {{ t('common.cancel') }}
                </BaseButton>
                <BaseButton type="submit" :loading="isSubmitting">
                  {{ t('context.create') }}
                </BaseButton>
              </div>
            </form>
          </BaseCard>
        </div>

        <!-- Sidebar / Help -->
        <div class="help-column">
          <BaseCard class="help-card">
            <h3 class="help-title">About Contexts</h3>
            <p class="help-text">
              Contexts allow you to present different sides of your identity to different applications.
            </p>
            <ul class="help-list">
              <li>Override your name and email</li>
              <li>Keep your phone number private</li>
              <li>Customize your bio per context</li>
            </ul>
          </BaseCard>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Page header */
.create-error {
  margin-bottom: var(--spacing-6);
}

/* Layout grid */
.create-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--spacing-6);
}

@media (min-width: 1024px) {
  .create-grid {
    grid-template-columns: 2fr 1fr;
  }
}

.form-column {
  min-width: 0;
}

.help-column {
  min-width: 0;
}

/* Form sections */
.form-section {
  margin-bottom: 2rem;
}

.section-label {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-3);
}

.section-heading {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  margin-bottom: var(--spacing-4);
}

/* Context type selection grid */
.type-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--spacing-3);
}

@media (min-width: 640px) {
  .type-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.pseudo-warning {
  margin-top: var(--spacing-2);
  font-size: var(--font-size-sm);
  color: var(--color-warning-600);
}

/* Context Type Selection Cards */
.context-type-card {
  position: relative;
  display: flex;
  cursor: pointer;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-secondary);
  padding: var(--spacing-4);
  background-color: var(--bg-secondary);
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-fast);
}

.context-type-card:hover {
  background-color: var(--bg-tertiary);
  border-color: var(--border-primary);
}

.context-type-card.is-selected {
  border-color: var(--color-primary-500);
  box-shadow: 0 0 0 2px var(--color-primary-500);
  background-color: var(--color-primary-600);
}

.context-type-card .card-content {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
}

.context-type-card .card-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.context-type-card .card-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-weight: var(--font-weight-medium);
  font-size: var(--font-size-sm);
  color: var(--text-primary);
}

.context-type-card .card-description {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

.context-type-card .card-check {
  color: var(--color-primary-600);
}

.check-icon {
  width: 1.25rem;
  height: 1.25rem;
}

/* Selected state overrides - high contrast */
.context-type-card.is-selected .card-title {
  color: white;
}

.context-type-card.is-selected .card-description {
  color: rgba(255, 255, 255, 0.8);
}

.context-type-card.is-selected .card-check {
  color: white;
}

/* Checkbox */
.checkbox-group {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  cursor: pointer;
}

.checkbox-input {
  border-radius: var(--radius-sm);
  border-color: var(--border-secondary);
  color: var(--color-primary-600);
}

.checkbox-text {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
}

.checkbox-hint {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  margin-top: var(--spacing-1);
  margin-left: var(--spacing-6);
}

/* Overrides section */
.overrides-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-4);
}

.overrides-header .section-heading {
  margin-bottom: 0;
}

.optional-badge {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  background-color: var(--bg-tertiary);
  padding: var(--spacing-1) var(--spacing-2);
  border-radius: var(--radius-sm);
}

.overrides-description {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-4);
}

/* Name chips */
.chips-label {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.chip-name-text {
  font-size: var(--font-size-sm);
}

/* Textarea */
.textarea-label {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-1);
}

.textarea-field {
  display: block;
  width: 100%;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-secondary);
  box-shadow: var(--shadow-sm);
  padding: var(--spacing-2) var(--spacing-3);
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  background-color: var(--bg-primary);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.textarea-field:focus {
  outline: none;
  border-color: var(--color-primary-500);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}

/* Avatar override */
.avatar-override-group {
  margin-top: var(--spacing-4);
}

/* Form footer */
.form-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-4);
  padding-top: var(--spacing-4);
  border-top: 1px solid var(--border-primary);
}

/* Help card */
.help-card {
  background-color: var(--color-primary-50);
  border-color: var(--color-primary-200);
}

:global(.dark) .help-card {
  background-color: rgba(59, 130, 246, 0.1);
  border-color: var(--color-primary-700);
}

.help-title {
  color: var(--color-primary-700);
  font-weight: var(--font-weight-medium);
  margin-bottom: var(--spacing-2);
}

:global(.dark) .help-title {
  color: var(--color-primary-300);
}

.help-text {
  font-size: var(--font-size-sm);
  color: var(--color-primary-600);
  margin-bottom: var(--spacing-4);
}

:global(.dark) .help-text {
  color: var(--color-primary-400);
}

.help-list {
  font-size: var(--font-size-sm);
  color: var(--color-primary-600);
  list-style-type: disc;
  list-style-position: inside;
}

.help-list > li + li {
  margin-top: var(--spacing-1);
}

:global(.dark) .help-list {
  color: var(--color-primary-400);
}
</style>
