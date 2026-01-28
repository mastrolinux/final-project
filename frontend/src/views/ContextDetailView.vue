<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore, useProfileStore, useUiStore } from '@/stores'
import { contextService, getErrorMessage } from '@/services'
import { CONTEXT_TYPE_META, type ContextProfileResponse, type ResolvedProfileResponse } from '@/types'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseBadge from '@/components/common/BaseBadge.vue'
import BaseInput from '@/components/common/BaseInput.vue'
import BaseModal from '@/components/common/BaseModal.vue'

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

onMounted(async () => {
  await loadContext()
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
</script>

<template>
  <div class="context-detail-view">
    <div class="container container-md">
      <div class="page-header mb-6">
        <router-link to="/contexts" class="back-link inline-flex items-center text-gray-500 hover:text-gray-900 mb-4">
          <span class="mr-1">&larr;</span> {{ t('common.back') }}
        </router-link>
      </div>

      <div v-if="isLoading" class="loading-state text-center py-12">
        <div class="spinner spinner-lg mx-auto"></div>
        <p class="mt-4 text-gray-500">{{ t('common.loading') }}</p>
      </div>

      <div v-else-if="error && !context" class="alert alert-error mb-6">
        {{ error }}
      </div>

      <template v-else-if="context">
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <!-- Main Content -->
          <div class="lg:col-span-2 space-y-6">
            <!-- Context Header Card -->
            <BaseCard>
              <div class="flex justify-between items-start">
                <div>
                  <div class="flex items-center gap-3 mb-2">
                    <BaseBadge :variant="context.context_type" size="md">
                      {{ CONTEXT_TYPE_META[context.context_type]?.label }}
                    </BaseBadge>
                    <BaseBadge v-if="!context.is_active" variant="warning" size="sm">
                      {{ t('context.inactive') }}
                    </BaseBadge>
                  </div>
                  <h1 class="text-2xl font-bold text-gray-900">{{ context.context_name }}</h1>
                  <p class="text-sm text-gray-500 mt-1">Created {{ new Date(context.created_at).toLocaleDateString() }}</p>
                </div>
                <div v-if="!isEditing" class="flex gap-2">
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
                <h2 class="text-lg font-semibold">Resolved Profile</h2>
                <p class="text-sm text-gray-500 font-normal mt-1">What applications see when using this context</p>
              </template>
              
              <div class="space-y-4">
                <div class="field-group">
                  <div class="flex justify-between items-center mb-1">
                    <label class="text-xs font-medium text-gray-500 uppercase">Display Name</label>
                    <BaseBadge v-if="context.display_name_override" variant="info" size="sm">Custom</BaseBadge>
                    <BaseBadge v-else variant="neutral" size="sm">Inherited</BaseBadge>
                  </div>
                  <div class="text-gray-900">{{ resolvedProfile.display_name || 'Not set' }}</div>
                </div>

                <div class="field-group">
                  <div class="flex justify-between items-center mb-1">
                    <label class="text-xs font-medium text-gray-500 uppercase">Email</label>
                    <BaseBadge v-if="context.email_override" variant="info" size="sm">Custom</BaseBadge>
                    <BaseBadge v-else variant="neutral" size="sm">Inherited</BaseBadge>
                  </div>
                  <div class="text-gray-900">{{ resolvedProfile.email }}</div>
                </div>

                <div class="field-group">
                  <div class="flex justify-between items-center mb-1">
                    <label class="text-xs font-medium text-gray-500 uppercase">Phone</label>
                    <BaseBadge v-if="context.phone_override" variant="info" size="sm">Custom</BaseBadge>
                    <BaseBadge v-else variant="neutral" size="sm">Inherited</BaseBadge>
                  </div>
                  <div class="text-gray-900">{{ resolvedProfile.phone || 'Not set' }}</div>
                </div>

                <div class="field-group">
                  <div class="flex justify-between items-center mb-1">
                    <label class="text-xs font-medium text-gray-500 uppercase">Bio</label>
                    <BaseBadge v-if="context.bio" variant="info" size="sm">Custom</BaseBadge>
                    <BaseBadge v-else variant="neutral" size="sm">Inherited</BaseBadge>
                  </div>
                  <div class="text-gray-900 whitespace-pre-wrap">{{ resolvedProfile.bio || 'Not set' }}</div>
                </div>
              </div>
            </BaseCard>

            <!-- Edit Form -->
            <BaseCard v-if="isEditing">
              <template #header>
                <h2 class="text-lg font-semibold">Edit Context</h2>
              </template>

              <form @submit.prevent="saveChanges" class="space-y-4">
                <BaseInput
                  v-model="editForm.context_name"
                  id="context_name"
                  :label="t('context.name')"
                  required
                />

                <div class="border-t border-gray-200 my-4 pt-4">
                  <h3 class="text-sm font-medium text-gray-900 mb-4">Overrides</h3>
                  
                  <BaseInput
                    v-model="editForm.display_name_override"
                    id="display_name"
                    :label="t('context.displayNameOverride')"
                    :placeholder="t('context.inheritFromProfile')"
                  />

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

                  <div class="form-group mb-4">
                    <label for="bio" class="block text-sm font-medium text-gray-700 mb-1">{{ t('context.bio') }}</label>
                    <textarea
                      id="bio"
                      v-model="editForm.bio"
                      rows="3"
                      class="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                      :placeholder="t('context.inheritFromProfile')"
                    ></textarea>
                  </div>
                </div>

                <div class="form-group">
                  <label class="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" v-model="editForm.is_active" class="rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
                    <span class="text-sm font-medium text-gray-700">{{ t('context.isActive') }}</span>
                  </label>
                </div>

                <div class="flex justify-end gap-3 pt-4">
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
          <div class="lg:col-span-1 space-y-6">
            <!-- Connected Apps (Placeholder) -->
            <BaseCard>
              <template #header>
                <h2 class="text-lg font-semibold">Connected Apps</h2>
              </template>
              <div class="text-sm text-gray-500 text-center py-4">
                No applications connected to this context.
              </div>
            </BaseCard>

            <!-- Inheritance Legend -->
            <BaseCard class="bg-gray-50">
              <h3 class="text-sm font-medium text-gray-900 mb-3">Field Inheritance</h3>
              <div class="space-y-3">
                <div class="flex items-center gap-2">
                  <BaseBadge variant="neutral" size="sm">Inherited</BaseBadge>
                  <span class="text-xs text-gray-600">Value comes from your base profile</span>
                </div>
                <div class="flex items-center gap-2">
                  <BaseBadge variant="info" size="sm">Custom</BaseBadge>
                  <span class="text-xs text-gray-600">Value is specific to this context</span>
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
        <p class="text-sm text-gray-500 mb-4">
          {{ t('context.deleteConfirmMessage') }}
        </p>
        <div class="bg-red-50 border border-red-100 rounded-md p-3 mb-4">
          <p class="text-xs text-red-800">
            <strong>Warning:</strong> Any applications using this context will lose access to your identity information.
          </p>
        </div>
        
        <template #footer>
          <div class="flex justify-end gap-3 w-full">
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
.context-detail-view {
  padding: var(--spacing-8) 0;
}

/* Tailwind-like utilities */
.grid { display: grid; }
.grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)); }
.gap-6 { gap: 1.5rem; }
.gap-3 { gap: 0.75rem; }
.gap-2 { gap: 0.5rem; }
.space-y-6 > * + * { margin-top: 1.5rem; }
.space-y-4 > * + * { margin-top: 1rem; }
.space-y-3 > * + * { margin-top: 0.75rem; }
.mb-6 { margin-bottom: 1.5rem; }
.mb-4 { margin-bottom: 1rem; }
.mb-3 { margin-bottom: 0.75rem; }
.mb-2 { margin-bottom: 0.5rem; }
.mb-1 { margin-bottom: 0.25rem; }
.mt-1 { margin-top: 0.25rem; }
.mt-4 { margin-top: 1rem; }
.mr-1 { margin-right: 0.25rem; }
.my-4 { margin-top: 1rem; margin-bottom: 1rem; }
.pt-4 { padding-top: 1rem; }
.py-12 { padding-top: 3rem; padding-bottom: 3rem; }
.py-4 { padding-top: 1rem; padding-bottom: 1rem; }
.p-3 { padding: 0.75rem; }
.text-center { text-align: center; }
.text-2xl { font-size: 1.5rem; line-height: 2rem; }
.text-lg { font-size: 1.125rem; line-height: 1.75rem; }
.text-sm { font-size: 0.875rem; line-height: 1.25rem; }
.text-xs { font-size: 0.75rem; line-height: 1rem; }
.font-bold { font-weight: 700; }
.font-semibold { font-weight: 600; }
.font-medium { font-weight: 500; }
.font-normal { font-weight: 400; }
.uppercase { text-transform: uppercase; }
.text-gray-900 { color: var(--text-primary); }
.text-gray-600 { color: var(--text-secondary); }
.text-gray-500 { color: var(--text-secondary); }
.text-red-800 { color: #991b1b; }
.bg-gray-50 { background-color: var(--bg-secondary); }
.bg-red-50 { background-color: #fef2f2; }
.border-t { border-top-width: 1px; }
.border-gray-200 { border-color: var(--border-primary); }
.border-gray-300 { border-color: var(--border-secondary); }
.border-red-100 { border-color: #fee2e2; }
.rounded-md { border-radius: 0.375rem; }
.rounded { border-radius: 0.25rem; }
.shadow-sm { box-shadow: var(--shadow-sm); }
.flex { display: flex; }
.items-center { align-items: center; }
.items-start { align-items: flex-start; }
.justify-between { justify-content: space-between; }
.justify-end { justify-content: flex-end; }
.inline-flex { display: inline-flex; }
.block { display: block; }
.w-full { width: 100%; }
.whitespace-pre-wrap { white-space: pre-wrap; }
.cursor-pointer { cursor: pointer; }

@media (min-width: 1024px) {
  .lg\:grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .lg\:col-span-2 { grid-column: span 2 / span 2; }
  .lg\:col-span-1 { grid-column: span 1 / span 1; }
}
</style>
