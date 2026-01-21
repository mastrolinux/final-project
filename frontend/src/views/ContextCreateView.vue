<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore, useProfileStore, useUiStore } from '@/stores'
import { contextService, getErrorMessage } from '@/services'
import { CONTEXT_TYPES, CONTEXT_TYPE_META, type ContextType } from '@/types'
import BaseInput from '@/components/common/BaseInput.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseBadge from '@/components/common/BaseBadge.vue'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()
const profileStore = useProfileStore()
const uiStore = useUiStore()

const isSubmitting = ref(false)
const error = ref<string | null>(null)

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

const handleCancel = () => {
  router.back()
}
</script>

<template>
  <div class="context-create-view">
    <div class="container container-md">
      <div class="page-header mb-6">
        <h1 class="text-2xl font-bold text-gray-900">{{ t('context.createNew') }}</h1>
        <p class="text-gray-500 mt-1">{{ t('context.createDescription') }}</p>
      </div>

      <div v-if="error" class="alert alert-error mb-6">
        {{ error }}
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Main Form -->
        <div class="lg:col-span-2">
          <BaseCard>
            <form @submit.prevent="handleSubmit">
              <!-- Context Type Selection -->
              <div class="mb-8">
                <label class="block text-sm font-medium text-gray-700 mb-3">{{ t('context.type') }}</label>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div
                    v-for="contextType in availableContextTypes"
                    :key="contextType"
                    class="relative flex cursor-pointer rounded-lg border p-4 shadow-sm focus:outline-none"
                    :class="[
                      form.context_type === contextType 
                        ? 'border-primary-500 ring-2 ring-primary-500 bg-primary-50' 
                        : 'border-gray-300 bg-white hover:bg-gray-50'
                    ]"
                    @click="form.context_type = contextType"
                  >
                    <div class="flex w-full items-center justify-between">
                      <div class="flex items-center">
                        <div class="text-sm">
                          <div class="font-medium text-gray-900 flex items-center gap-2">
                            {{ t(`context.types.${contextType}`) }}
                            <BaseBadge :variant="contextType" size="sm" class="ml-1">
                              {{ CONTEXT_TYPE_META[contextType].label }}
                            </BaseBadge>
                          </div>
                          <div class="text-gray-500 mt-1 text-xs">
                            {{ t(`context.typeDescriptions.${contextType}`) }}
                          </div>
                        </div>
                      </div>
                      <div v-if="form.context_type === contextType" class="text-primary-600">
                        <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                        </svg>
                      </div>
                    </div>
                  </div>
                </div>
                <p v-if="authStore.accountType === 'pseudonymous'" class="mt-2 text-sm text-warning-600">
                  {{ t('context.pseudonymousRestriction') }}
                </p>
              </div>

              <!-- Basic Info -->
              <div class="mb-8">
                <h3 class="text-lg font-medium text-gray-900 mb-4">Basic Information</h3>
                <BaseInput
                  v-model="form.context_name"
                  id="context_name"
                  :label="t('context.name')"
                  :placeholder="t('context.namePlaceholder')"
                  required
                  :hint="t('context.nameHint')"
                />
                
                <div class="form-group mb-4">
                  <label class="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" v-model="form.is_active" class="rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
                    <span class="text-sm font-medium text-gray-700">{{ t('context.isActive') }}</span>
                  </label>
                  <p class="text-xs text-gray-500 mt-1 ml-6">{{ t('context.isActiveHint') }}</p>
                </div>
              </div>

              <!-- Overrides -->
              <div class="mb-8">
                <div class="flex items-center justify-between mb-4">
                  <h3 class="text-lg font-medium text-gray-900">{{ t('context.overrides') }}</h3>
                  <span class="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">Optional</span>
                </div>
                <p class="text-sm text-gray-500 mb-4">{{ t('context.overridesDescription') }}</p>

                <BaseInput
                  v-model="form.display_name_override"
                  id="display_name"
                  :label="t('context.displayNameOverride')"
                  :placeholder="t('context.inheritFromProfile')"
                />

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

                <div class="form-group mb-4">
                  <label for="bio" class="block text-sm font-medium text-gray-700 mb-1">{{ t('context.bio') }}</label>
                  <textarea
                    id="bio"
                    v-model="form.bio"
                    rows="3"
                    class="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                    :placeholder="t('context.bioPlaceholder')"
                  ></textarea>
                </div>
              </div>

              <div class="flex justify-end gap-4 pt-4 border-t border-gray-200">
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
        <div class="lg:col-span-1">
          <BaseCard class="bg-blue-50 border-blue-100">
            <h3 class="text-blue-900 font-medium mb-2">About Contexts</h3>
            <p class="text-sm text-blue-800 mb-4">
              Contexts allow you to present different sides of your identity to different applications.
            </p>
            <ul class="text-sm text-blue-800 list-disc list-inside space-y-1">
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
.context-create-view {
  padding: var(--spacing-8) 0;
}

/* Tailwind-like utilities */
.grid { display: grid; }
.grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)); }
.gap-6 { gap: 1.5rem; }
.gap-3 { gap: 0.75rem; }
.gap-4 { gap: 1rem; }
.gap-2 { gap: 0.5rem; }
.mb-8 { margin-bottom: 2rem; }
.mb-6 { margin-bottom: 1.5rem; }
.mb-4 { margin-bottom: 1rem; }
.mb-3 { margin-bottom: 0.75rem; }
.mb-2 { margin-bottom: 0.5rem; }
.mb-1 { margin-bottom: 0.25rem; }
.mt-1 { margin-top: 0.25rem; }
.mt-2 { margin-top: 0.5rem; }
.ml-1 { margin-left: 0.25rem; }
.ml-6 { margin-left: 1.5rem; }
.pt-4 { padding-top: 1rem; }
.px-2 { padding-left: 0.5rem; padding-right: 0.5rem; }
.py-1 { padding-top: 0.25rem; padding-bottom: 0.25rem; }
.p-4 { padding: 1rem; }
.w-full { width: 100%; }
.h-5 { height: 1.25rem; }
.w-5 { width: 1.25rem; }
.flex { display: flex; }
.items-center { align-items: center; }
.justify-between { justify-content: space-between; }
.justify-end { justify-content: flex-end; }
.relative { position: relative; }
.block { display: block; }
.rounded-lg { border-radius: 0.5rem; }
.rounded-md { border-radius: 0.375rem; }
.rounded { border-radius: 0.25rem; }
.border { border-width: 1px; }
.border-t { border-top-width: 1px; }
.border-gray-200 { border-color: var(--color-gray-200); }
.border-gray-300 { border-color: var(--color-gray-300); }
.border-primary-500 { border-color: var(--color-primary-500); }
.border-blue-100 { border-color: #dbeafe; }
.bg-white { background-color: white; }
.bg-gray-50 { background-color: var(--color-gray-50); }
.bg-gray-100 { background-color: var(--color-gray-100); }
.bg-primary-50 { background-color: var(--color-primary-50); }
.bg-blue-50 { background-color: #eff6ff; }
.text-gray-900 { color: var(--color-gray-900); }
.text-gray-700 { color: var(--color-gray-700); }
.text-gray-500 { color: var(--color-gray-500); }
.text-primary-600 { color: var(--color-primary-600); }
.text-warning-600 { color: var(--color-warning-600); }
.text-blue-900 { color: #1e3a8a; }
.text-blue-800 { color: #1e40af; }
.font-bold { font-weight: 700; }
.font-medium { font-weight: 500; }
.text-2xl { font-size: 1.5rem; line-height: 2rem; }
.text-lg { font-size: 1.125rem; line-height: 1.75rem; }
.text-sm { font-size: 0.875rem; line-height: 1.25rem; }
.text-xs { font-size: 0.75rem; line-height: 1rem; }
.cursor-pointer { cursor: pointer; }
.shadow-sm { box-shadow: var(--shadow-sm); }
.list-disc { list-style-type: disc; }
.list-inside { list-style-position: inside; }

@media (min-width: 640px) {
  .sm\:grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .sm\:text-sm { font-size: 0.875rem; line-height: 1.25rem; }
}

@media (min-width: 1024px) {
  .lg\:grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .lg\:col-span-2 { grid-column: span 2 / span 2; }
  .lg\:col-span-1 { grid-column: span 1 / span 1; }
}
</style>
