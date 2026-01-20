<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore, useProfileStore, useUiStore } from '@/stores'
import { contextService, getErrorMessage } from '@/services'
import type { ContextType, ContextProfileResponse } from '@/types'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const profileStore = useProfileStore()
const uiStore = useUiStore()

const contextId = computed(() => route.params.id as string)
const context = ref<ContextProfileResponse | null>(null)
const isLoading = ref(true)
const isEditing = ref(false)
const isSaving = ref(false)
const isDeleting = ref(false)
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

function getContextBadgeClass(contextType: ContextType): string {
  return `badge badge-${contextType}`
}

onMounted(async () => {
  await loadContext()
})

async function loadContext() {
  if (!authStore.userId) return

  isLoading.value = true
  error.value = null

  try {
    context.value = await contextService.get(authStore.userId, contextId.value)
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
</script>

<template>
  <div class="context-detail-view">
    <div class="container container-md">
      <div class="page-header">
        <router-link to="/contexts" class="back-link">
          &larr; {{ t('common.back') }}
        </router-link>
      </div>

      <div v-if="isLoading" class="loading-state">
        <div class="spinner"></div>
        <p>{{ t('common.loading') }}</p>
      </div>

      <div v-else-if="error && !context" class="alert alert-error">
        {{ error }}
      </div>

      <template v-else-if="context">
        <div class="card">
          <div class="card-header flex justify-between items-center">
            <div class="context-title">
              <span :class="getContextBadgeClass(context.context_type)">
                {{ t(`context.types.${context.context_type}`) }}
              </span>
              <h1>{{ context.context_name }}</h1>
            </div>
            <div v-if="!isEditing" class="header-actions">
              <button class="btn btn-outline" @click="startEditing">
                {{ t('common.edit') }}
              </button>
              <button class="btn btn-danger-outline" @click="showDeleteConfirm = true">
                {{ t('common.delete') }}
              </button>
            </div>
          </div>

          <div class="card-body">
            <div v-if="error" class="alert alert-error mb-4">
              {{ error }}
            </div>

            <form v-if="isEditing" @submit.prevent="saveChanges" class="edit-form">
              <div class="form-group">
                <label for="context_name" class="form-label">{{ t('context.name') }}</label>
                <input
                  id="context_name"
                  v-model="editForm.context_name"
                  type="text"
                  class="form-input"
                  required
                />
              </div>

              <div class="form-group">
                <label for="display_name" class="form-label">{{
                  t('context.displayNameOverride')
                }}</label>
                <input
                  id="display_name"
                  v-model="editForm.display_name_override"
                  type="text"
                  class="form-input"
                  :placeholder="t('context.inheritFromProfile')"
                />
              </div>

              <div class="form-group">
                <label for="email" class="form-label">{{ t('context.emailOverride') }}</label>
                <input
                  id="email"
                  v-model="editForm.email_override"
                  type="email"
                  class="form-input"
                  :placeholder="t('context.inheritFromProfile')"
                />
              </div>

              <div class="form-group">
                <label for="phone" class="form-label">{{ t('context.phoneOverride') }}</label>
                <input
                  id="phone"
                  v-model="editForm.phone_override"
                  type="tel"
                  class="form-input"
                  :placeholder="t('context.inheritFromProfile')"
                />
              </div>

              <div class="form-group">
                <label for="bio" class="form-label">{{ t('context.bio') }}</label>
                <textarea
                  id="bio"
                  v-model="editForm.bio"
                  class="form-input form-textarea"
                  rows="4"
                ></textarea>
              </div>

              <div class="form-group">
                <label class="form-checkbox">
                  <input type="checkbox" v-model="editForm.is_active" />
                  <span>{{ t('context.isActive') }}</span>
                </label>
              </div>

              <div class="form-actions">
                <button type="button" class="btn btn-outline" @click="cancelEditing">
                  {{ t('common.cancel') }}
                </button>
                <button type="submit" class="btn btn-primary" :disabled="isSaving">
                  {{ isSaving ? t('common.saving') : t('common.save') }}
                </button>
              </div>
            </form>

            <div v-else class="context-details">
              <div class="detail-row">
                <span class="detail-label">{{ t('common.status') }}</span>
                <span :class="['badge', context.is_active ? 'badge-success' : 'badge-warning']">
                  {{ context.is_active ? t('context.active') : t('context.inactive') }}
                </span>
              </div>

              <div v-if="context.display_name_override" class="detail-row">
                <span class="detail-label">{{ t('context.displayName') }}</span>
                <span class="detail-value">{{ context.display_name_override }}</span>
              </div>

              <div v-if="context.email_override" class="detail-row">
                <span class="detail-label">{{ t('common.email') }}</span>
                <span class="detail-value">{{ context.email_override }}</span>
              </div>

              <div v-if="context.phone_override" class="detail-row">
                <span class="detail-label">{{ t('common.phone') }}</span>
                <span class="detail-value">{{ context.phone_override }}</span>
              </div>

              <div v-if="context.bio" class="detail-row">
                <span class="detail-label">{{ t('context.bio') }}</span>
                <p class="detail-value bio">{{ context.bio }}</p>
              </div>

              <div class="detail-row">
                <span class="detail-label">{{ t('common.created') }}</span>
                <span class="detail-value">{{
                  new Date(context.created_at).toLocaleDateString()
                }}</span>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- Delete confirmation modal -->
      <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="showDeleteConfirm = false">
        <div class="modal">
          <div class="modal-header">
            <h2>{{ t('context.deleteConfirmTitle') }}</h2>
          </div>
          <div class="modal-body">
            <p>{{ t('context.deleteConfirmMessage') }}</p>
          </div>
          <div class="modal-footer">
            <button class="btn btn-outline" @click="showDeleteConfirm = false">
              {{ t('common.cancel') }}
            </button>
            <button class="btn btn-danger" :disabled="isDeleting" @click="deleteContext">
              {{ isDeleting ? t('common.deleting') : t('common.delete') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.context-detail-view {
  padding: var(--spacing-6) 0;
}

.page-header {
  margin-bottom: var(--spacing-4);
}

.back-link {
  color: var(--text-secondary);
  text-decoration: none;
}

.back-link:hover {
  color: var(--text-primary);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--spacing-12);
  color: var(--text-secondary);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: var(--spacing-4) var(--spacing-6);
  border-bottom: 1px solid var(--border-color);
}

.context-title h1 {
  font-size: var(--font-size-xl);
  margin-top: var(--spacing-2);
}

.header-actions {
  display: flex;
  gap: var(--spacing-2);
}

.edit-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-2);
  margin-top: var(--spacing-4);
}

.context-details {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.detail-row {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.detail-label {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  font-weight: 500;
}

.detail-value {
  color: var(--text-primary);
}

.detail-value.bio {
  white-space: pre-wrap;
}

/* Modal styles */
.modal-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  max-width: 400px;
  width: 90%;
}

.modal-header {
  padding: var(--spacing-4) var(--spacing-6);
  border-bottom: 1px solid var(--border-color);
}

.modal-header h2 {
  font-size: var(--font-size-lg);
  margin: 0;
}

.modal-body {
  padding: var(--spacing-6);
}

.modal-footer {
  padding: var(--spacing-4) var(--spacing-6);
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-2);
}

.btn-danger-outline {
  color: var(--color-error-600);
  border-color: var(--color-error-300);
}

.btn-danger-outline:hover {
  background-color: var(--color-error-50);
}

.btn-danger {
  background-color: var(--color-error-600);
  color: white;
}

.btn-danger:hover {
  background-color: var(--color-error-700);
}
</style>
