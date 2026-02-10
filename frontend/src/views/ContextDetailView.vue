<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore, useProfileStore, useUiStore } from '@/stores'
import { contextService, profileService, getErrorMessage } from '@/services'
import { CONTEXT_TYPE_META, type ContextProfileResponse, type ResolvedProfileResponse } from '@/types'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseBadge from '@/components/common/BaseBadge.vue'
import BaseInput from '@/components/common/BaseInput.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import AvatarDisplay from '@/components/common/AvatarDisplay.vue'
import AvatarUpload from '@/components/profile/AvatarUpload.vue'
import AppBreadcrumb from '@/components/layout/AppBreadcrumb.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const profileStore = useProfileStore()
const uiStore = useUiStore()

const contextId = computed(() => route.params.id as string)
const context = ref<ContextProfileResponse | null>(null)
const resolvedProfile = ref<ResolvedProfileResponse | null>(null)
const isLoading = ref(true)
const isEditing = ref(false)
const isSaving = ref(false)
const isDeleting = ref(false)
const isUploadingAvatar = ref(false)
const error = ref<string | null>(null)
const showDeleteConfirm = ref(false)

const editForm = ref({
  context_name: '',
  display_name_override: '',
  email_override: '',
  phone_override: '',
  bio: '',
  is_active: true
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
  editForm.value.display_name_override = resolved
}

onMounted(async () => {
  await loadContext()
  // Load identity names for the "pick from names" chips
  if (authStore.userId && profileStore.identityNames.length === 0) {
    try {
      const names = await profileService.getNames(authStore.userId)
      profileStore.setIdentityNames(names)
    } catch {
      // Non-critical: chips won't show, text input still works
    }
  }
})

async function loadContext() {
  if (!authStore.userId) return

  isLoading.value = true
  error.value = null

  try {
    const [ctx, resolved] = await Promise.all([
      contextService.get(authStore.userId, contextId.value),
      contextService.getResolved(authStore.userId, contextId.value)
    ])
    context.value = ctx
    resolvedProfile.value = resolved
    resetEditForm()
  } catch (err) {
    error.value = getErrorMessage(err)
  } finally {
    isLoading.value = false
  }
}

function resetEditForm() {
  if (!context.value) return
  editForm.value = {
    context_name: context.value.context_name,
    display_name_override: context.value.display_name_override || '',
    email_override: context.value.email_override || '',
    phone_override: context.value.phone_override || '',
    bio: context.value.bio || '',
    is_active: context.value.is_active
  }
}

function startEditing() {
  resetEditForm()
  isEditing.value = true
}

function cancelEditing() {
  isEditing.value = false
  resetEditForm()
}

async function saveChanges() {
  if (!authStore.userId || !context.value) return

  isSaving.value = true
  error.value = null

  try {
    const updatedContext = await contextService.update(authStore.userId, contextId.value, {
      context_name: editForm.value.context_name,
      display_name_override: editForm.value.display_name_override || null,
      email_override: editForm.value.email_override || null,
      phone_override: editForm.value.phone_override || null,
      bio: editForm.value.bio || null,
      is_active: editForm.value.is_active
    })
    context.value = updatedContext

    // Reload resolved profile to reflect changes
    resolvedProfile.value = await contextService.getResolved(authStore.userId, contextId.value)

    profileStore.updateContext(updatedContext)
    isEditing.value = false
    uiStore.addNotification({
      type: 'success',
      message: t('context.updateSuccess')
    })
  } catch (err) {
    error.value = getErrorMessage(err)
  } finally {
    isSaving.value = false
  }
}

async function deleteContext() {
  if (!authStore.userId) return

  isDeleting.value = true
  error.value = null

  try {
    await contextService.delete(authStore.userId, contextId.value)
    profileStore.removeContext(contextId.value)
    uiStore.addNotification({
      type: 'success',
      message: t('context.deleteSuccess')
    })
    router.push({ name: 'contexts' })
  } catch (err) {
    error.value = getErrorMessage(err)
    showDeleteConfirm.value = false
  } finally {
    isDeleting.value = false
  }
}

async function handleContextAvatarUpload(file: File) {
  if (!authStore.userId || !context.value) return

  isUploadingAvatar.value = true
  error.value = null
  try {
    const result = await contextService.uploadAvatar(
      authStore.userId,
      contextId.value,
      file
    )
    // Update local context ref
    context.value = {
      ...context.value,
      avatar_override_url: result.avatar_url,
      avatar_override_thumbnail_url: result.avatar_thumbnail_url
    }
    // Update store
    profileStore.setContextAvatar(contextId.value, result.avatar_url, result.avatar_thumbnail_url)
    // Reload resolved profile to reflect inheritance change
    resolvedProfile.value = await contextService.getResolved(authStore.userId, contextId.value)
    uiStore.addNotification({ type: 'success', message: t('context.avatar.uploadSuccess') })
  } catch (err) {
    error.value = getErrorMessage(err)
  } finally {
    isUploadingAvatar.value = false
  }
}

async function handleContextAvatarRemove() {
  if (!authStore.userId || !context.value) return

  isUploadingAvatar.value = true
  error.value = null
  try {
    await contextService.deleteAvatar(authStore.userId, contextId.value)
    context.value = {
      ...context.value,
      avatar_override_url: null,
      avatar_override_thumbnail_url: null
    }
    profileStore.clearContextAvatar(contextId.value)
    resolvedProfile.value = await contextService.getResolved(authStore.userId, contextId.value)
    uiStore.addNotification({ type: 'success', message: t('context.avatar.removeSuccess') })
  } catch (err) {
    error.value = getErrorMessage(err)
  } finally {
    isUploadingAvatar.value = false
  }
}
</script>

<template>
  <div class="page-view">
    <div class="container container-lg">
      <div class="page-header">
        <AppBreadcrumb />
      </div>

      <div v-if="isLoading" class="loading-container">
        <div class="spinner spinner-lg loading-spinner"></div>
        <p class="loading-text">{{ t('common.loading') }}</p>
      </div>

      <div v-else-if="error && !context" class="alert alert-error alert-spaced">
        {{ error }}
      </div>

      <template v-else-if="context">
        <div class="detail-grid">
          <!-- Main Content -->
          <div class="main-column">
            <!-- Context Header Card -->
            <BaseCard>
              <div class="context-header-row">
                <div>
                  <div class="context-badges">
                    <BaseBadge :variant="context.context_type" size="md">
                      {{ CONTEXT_TYPE_META[context.context_type]?.label }}
                    </BaseBadge>
                    <BaseBadge v-if="!context.is_active" variant="warning" size="sm">
                      {{ t('context.inactive') }}
                    </BaseBadge>
                  </div>
                  <h1 class="context-title">{{ context.context_name }}</h1>
                  <p class="context-meta">Created {{ new Date(context.created_at).toLocaleDateString() }}</p>
                </div>
                <div v-if="!isEditing" class="action-buttons">
                  <BaseButton variant="secondary" size="sm" @click="startEditing">
                    {{ t('common.edit') }}
                  </BaseButton>
                  <BaseButton variant="danger" size="sm" @click="showDeleteConfirm = true">
                    {{ t('common.delete') }}
                  </BaseButton>
                </div>
              </div>
            </BaseCard>

            <!-- Resolved Profile Preview -->
            <BaseCard v-if="!isEditing && resolvedProfile">
              <template #header>
                <h2 class="card-heading">Resolved Profile</h2>
                <p class="resolved-subtitle">What applications see when using this context</p>
              </template>

              <div class="fields-list">
                <div class="field-group">
                  <div class="field-header">
                    <label class="field-label-sm">Avatar</label>
                    <BaseBadge v-if="context.avatar_override_url" variant="info" size="sm">Custom</BaseBadge>
                  </div>
                  <AvatarDisplay
                    :src="resolvedProfile.avatar_url"
                    :name="resolvedProfile.display_name || ''"
                    size="lg"
                  />
                </div>

                <div class="field-group">
                  <div class="field-header">
                    <label class="field-label-sm">Display Name</label>
                    <BaseBadge v-if="context.display_name_override" variant="info" size="sm">Custom</BaseBadge>
                    <BaseBadge v-else-if="resolvedProfile.display_name" variant="neutral" size="sm">Inherited</BaseBadge>
                  </div>
                  <div class="field-value-text">{{ resolvedProfile.display_name || 'Not set' }}</div>
                </div>

                <div class="field-group">
                  <div class="field-header">
                    <label class="field-label-sm">Email</label>
                    <BaseBadge v-if="context.email_override" variant="info" size="sm">Custom</BaseBadge>
                    <BaseBadge v-else-if="resolvedProfile.email" variant="neutral" size="sm">Inherited</BaseBadge>
                  </div>
                  <div class="field-value-text">{{ resolvedProfile.email || 'Not set' }}</div>
                </div>

                <div class="field-group">
                  <div class="field-header">
                    <label class="field-label-sm">Phone</label>
                    <BaseBadge v-if="context.phone_override" variant="info" size="sm">Custom</BaseBadge>
                    <BaseBadge v-else-if="resolvedProfile.phone" variant="neutral" size="sm">Inherited</BaseBadge>
                  </div>
                  <div class="field-value-text">{{ resolvedProfile.phone || 'Not set' }}</div>
                </div>

                <div class="field-group">
                  <div class="field-header">
                    <label class="field-label-sm">Bio</label>
                    <BaseBadge v-if="context.bio" variant="info" size="sm">Custom</BaseBadge>
                    <BaseBadge v-else-if="resolvedProfile.bio" variant="neutral" size="sm">Inherited</BaseBadge>
                  </div>
                  <div class="field-value-bio">{{ resolvedProfile.bio || 'Not set' }}</div>
                </div>
              </div>
            </BaseCard>

            <!-- Edit Form -->
            <BaseCard v-if="isEditing">
              <template #header>
                <h2 class="card-heading">Edit Context</h2>
              </template>

              <form @submit.prevent="saveChanges" class="edit-form">
                <BaseInput
                  v-model="editForm.context_name"
                  id="context_name"
                  :label="t('context.name')"
                  required
                />

                <div class="edit-divider">
                  <h3 class="overrides-heading">Overrides</h3>

                  <BaseInput
                    v-model="editForm.display_name_override"
                    id="display_name"
                    :label="t('context.displayNameOverride')"
                    :placeholder="t('context.inheritFromProfile')"
                  />

                  <div v-if="availableNames.length > 0" class="name-chips-section chips-spaced">
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
                    v-model="editForm.email_override"
                    id="email"
                    type="email"
                    :label="t('context.emailOverride')"
                    :placeholder="t('context.inheritFromProfile')"
                  />

                  <BaseInput
                    v-model="editForm.phone_override"
                    id="phone"
                    type="tel"
                    :label="t('context.phoneOverride')"
                    :placeholder="t('context.inheritFromProfile')"
                  />

                  <div class="form-group textarea-group">
                    <label for="bio" class="textarea-label">{{ t('context.bio') }}</label>
                    <textarea
                      id="bio"
                      v-model="editForm.bio"
                      rows="3"
                      class="textarea-field"
                      :placeholder="t('context.inheritFromProfile')"
                    ></textarea>
                  </div>

                  <div class="form-group avatar-override-group">
                    <label class="textarea-label">{{ t('context.avatar.override') }}</label>
                    <AvatarUpload
                      :currentUrl="context?.avatar_override_url"
                      :name="editForm.display_name_override || profileStore.displayName"
                      :isUploading="isUploadingAvatar"
                      @upload="handleContextAvatarUpload"
                      @remove="handleContextAvatarRemove"
                    />
                  </div>
                </div>

                <div class="form-group">
                  <label class="checkbox-group">
                    <input type="checkbox" v-model="editForm.is_active" class="checkbox-input" />
                    <span class="checkbox-text">{{ t('context.isActive') }}</span>
                  </label>
                </div>

                <div class="form-actions">
                  <BaseButton variant="ghost" @click="cancelEditing" :disabled="isSaving">
                    {{ t('common.cancel') }}
                  </BaseButton>
                  <BaseButton type="submit" :loading="isSaving">
                    {{ t('common.save') }}
                  </BaseButton>
                </div>
              </form>
            </BaseCard>
          </div>

          <!-- Sidebar -->
          <div class="sidebar-column">
            <!-- Connected Apps (Placeholder) -->
            <BaseCard>
              <template #header>
                <h2 class="card-heading">Connected Apps</h2>
              </template>
              <div class="connected-empty">
                No applications connected to this context.
              </div>
            </BaseCard>

            <!-- Inheritance Legend -->
            <BaseCard class="legend-card">
              <h3 class="legend-title">Field Inheritance</h3>
              <div class="legend-items">
                <div class="legend-row">
                  <BaseBadge variant="neutral" size="sm">Inherited</BaseBadge>
                  <span class="legend-desc">Value comes from your base profile</span>
                </div>
                <div class="legend-row">
                  <BaseBadge variant="info" size="sm">Custom</BaseBadge>
                  <span class="legend-desc">Value is specific to this context</span>
                </div>
                <div class="legend-row">
                  <span class="legend-no-badge">No badge</span>
                  <span class="legend-desc">Not set in base profile or this context</span>
                </div>
              </div>
            </BaseCard>
          </div>
        </div>
      </template>

      <!-- Delete Confirmation Modal -->
      <BaseModal
        :isOpen="showDeleteConfirm"
        :title="t('context.deleteConfirmTitle')"
        @close="showDeleteConfirm = false"
      >
        <p class="modal-message">
          {{ t('context.deleteConfirmMessage') }}
        </p>
        <div class="delete-warning">
          <p class="delete-warning-text">
            <strong>Warning:</strong> Any applications using this context will lose access to your identity information.
          </p>
        </div>

        <template #footer>
          <div class="modal-actions">
            <BaseButton variant="ghost" @click="showDeleteConfirm = false">
              {{ t('common.cancel') }}
            </BaseButton>
            <BaseButton variant="danger" :loading="isDeleting" @click="deleteContext">
              {{ t('common.delete') }}
            </BaseButton>
          </div>
        </template>
      </BaseModal>
    </div>
  </div>
</template>

<style scoped>
/* Loading state */
.loading-container {
  text-align: center;
  padding: var(--spacing-12) 0;
}

.loading-spinner {
  margin-left: auto;
  margin-right: auto;
}

.loading-text {
  margin-top: var(--spacing-4);
  color: var(--text-secondary);
}

.alert-spaced {
  margin-bottom: var(--spacing-6);
}

/* Detail grid layout */
.detail-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--spacing-6);
}

@media (min-width: 1024px) {
  .detail-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.main-column {
  grid-column: 1;
}

@media (min-width: 1024px) {
  .main-column {
    grid-column: span 2 / span 2;
  }
}

.main-column > * + * {
  margin-top: var(--spacing-6);
}

.sidebar-column > * + * {
  margin-top: var(--spacing-6);
}

/* Context header */
.context-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.context-badges {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  margin-bottom: var(--spacing-2);
}

.context-title {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
}

.context-meta {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin-top: var(--spacing-1);
}

.action-buttons {
  display: flex;
  gap: var(--spacing-2);
}

/* Card elements */
.card-heading {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
}

.resolved-subtitle {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  font-weight: var(--font-weight-normal);
  margin-top: var(--spacing-1);
}

/* Field display */
.fields-list > * + * {
  margin-top: var(--spacing-4);
}

.field-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-1);
}

.field-label-sm {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
  text-transform: uppercase;
}

.field-value-text {
  color: var(--text-primary);
}

.field-value-bio {
  color: var(--text-primary);
  white-space: pre-wrap;
}

/* Edit form */
.edit-form > * + * {
  margin-top: var(--spacing-4);
}

.edit-divider {
  border-top: 1px solid var(--border-primary);
  margin-top: var(--spacing-4);
  margin-bottom: var(--spacing-4);
  padding-top: var(--spacing-4);
}

.overrides-heading {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  margin-bottom: var(--spacing-4);
}

/* Name chips (uses global .name-chips-section, .name-chips, .name-chip from components.css) */
.chips-spaced {
  margin-bottom: var(--spacing-4);
}

.chips-label {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

.chip-name-text {
  font-size: var(--font-size-sm);
}

/* Avatar override */
.avatar-override-group {
  margin-top: var(--spacing-4);
}

/* Textarea */
.textarea-group {
  margin-bottom: var(--spacing-4);
}

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
  padding: var(--spacing-2);
  font-size: var(--font-size-sm);
  background-color: var(--input-bg);
  color: var(--text-primary);
}

.textarea-field:focus {
  border-color: var(--color-primary-500);
  outline: none;
  box-shadow: 0 0 0 2px var(--color-primary-100);
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

/* Form actions */
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-3);
  padding-top: var(--spacing-4);
}

/* Sidebar - connected apps */
.connected-empty {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  text-align: center;
  padding: var(--spacing-4) 0;
}

/* Sidebar - inheritance legend */
.legend-card {
  background-color: var(--bg-tertiary);
}

.legend-title {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  margin-bottom: var(--spacing-3);
}

.legend-items > * + * {
  margin-top: var(--spacing-3);
}

.legend-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.legend-desc {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

.legend-no-badge {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  font-style: italic;
}

/* Modal content */
.modal-message {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-4);
}

.delete-warning {
  background-color: var(--color-error-50);
  border: 1px solid #fee2e2;
  border-radius: var(--radius-md);
  padding: var(--spacing-3);
  margin-bottom: var(--spacing-4);
}

.delete-warning-text {
  font-size: var(--font-size-xs);
  color: #991b1b;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-3);
  width: 100%;
}
</style>
