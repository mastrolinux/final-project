<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore, useProfileStore } from '@/stores'
import { profileService, getErrorMessage } from '@/services'
import BaseInput from '@/components/common/BaseInput.vue'
import BaseSelect from '@/components/common/BaseSelect.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import IdentityNameManager from '@/components/profile/IdentityNameManager.vue'
import type { ProfileUpdate } from '@/types'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()
const profileStore = useProfileStore()

const isLoading = ref(true)
const isSaving = ref(false)
const error = ref<string | null>(null)

const form = reactive<{
  legal_name: string
  primary_email: string
  primary_phone: string
  preferred_language: string
}>({
  legal_name: '',
  primary_email: '',
  primary_phone: '',
  preferred_language: 'en'
})

// Language options
const languageOptions = [
  { label: 'English', value: 'en' },
  { label: 'Chinese (Simplified)', value: 'zh' },
  { label: 'Spanish', value: 'es' },
  { label: 'Arabic', value: 'ar' }
]

onMounted(async () => {
  if (!authStore.userId) return

  try {
    // Ensure we have the latest profile data
    const profile = await profileService.get(authStore.userId)
    profileStore.setProfile(profile)
    
    // Also fetch identity names for the manager
    const names = await profileService.getNames(authStore.userId)
    profileStore.setIdentityNames(names)
    
    // Populate form
    form.legal_name = profile.legal_name || ''
    form.primary_email = profile.primary_email
    form.primary_phone = profile.primary_phone || ''
    form.preferred_language = profile.preferred_language
  } catch (err) {
    error.value = getErrorMessage(err)
  } finally {
    isLoading.value = false
  }
})

const handleSave = async () => {
  if (!authStore.userId) return
  
  isSaving.value = true
  error.value = null

  try {
    const updates: ProfileUpdate = {
      legal_name: form.legal_name || undefined,
      primary_email: form.primary_email,
      primary_phone: form.primary_phone || undefined,
      preferred_language: form.preferred_language
    }

    const updatedProfile = await profileService.update(authStore.userId, updates)
    profileStore.setProfile(updatedProfile)
    
    router.back()
  } catch (err) {
    error.value = getErrorMessage(err)
  } finally {
    isSaving.value = false
  }
}

const handleCancel = () => {
  router.back()
}
</script>

<template>
  <div class="profile-edit-view">
    <div class="container container-sm">
      <div class="page-header mb-6">
        <h1 class="text-2xl font-bold text-gray-900">{{ t('profile.editProfile') }}</h1>
      </div>

      <div v-if="isLoading" class="loading-state text-center py-12">
        <div class="spinner spinner-lg mx-auto"></div>
        <p class="mt-4 text-gray-500">{{ t('common.loading') }}</p>
      </div>

      <div v-else class="edit-content space-y-6">
        <div v-if="error" class="alert alert-error mb-6">
          {{ error }}
        </div>

        <BaseCard>
          <template #header>
            <h2 class="text-lg font-semibold">Base Information</h2>
          </template>
          
          <form @submit.prevent="handleSave">
            <BaseInput
              v-model="form.legal_name"
              id="legal_name"
              :label="t('profile.legalName')"
              :placeholder="t('profile.legalNamePlaceholder')"
            />

            <BaseInput
              v-model="form.primary_email"
              id="primary_email"
              type="email"
              :label="t('profile.primaryEmail')"
              required
              :hint="t('profile.emailChangeWarning')"
            />

            <BaseInput
              v-model="form.primary_phone"
              id="primary_phone"
              type="tel"
              :label="t('profile.primaryPhone')"
              placeholder="+1234567890"
            />

            <BaseSelect
              v-model="form.preferred_language"
              id="preferred_language"
              :label="t('profile.preferredLanguage')"
              :options="languageOptions"
            />

            <div class="form-actions mt-8 flex justify-end gap-4">
              <BaseButton variant="ghost" @click="handleCancel" :disabled="isSaving">
                {{ t('common.cancel') }}
              </BaseButton>
              <BaseButton type="submit" :loading="isSaving">
                {{ t('common.save') }}
              </BaseButton>
            </div>
          </form>
        </BaseCard>

        <BaseCard>
          <IdentityNameManager />
        </BaseCard>
      </div>
    </div>
  </div>
</template>

<style scoped>
.profile-edit-view {
  padding: var(--spacing-8) 0;
}

.container-sm {
  max-width: 640px;
  margin-left: auto;
  margin-right: auto;
  padding-left: var(--spacing-4);
  padding-right: var(--spacing-4);
}

.space-y-6 > * + * {
  margin-top: 1.5rem;
}
</style>
