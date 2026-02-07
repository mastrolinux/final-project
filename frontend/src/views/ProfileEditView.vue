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
import AppBreadcrumb from '@/components/layout/AppBreadcrumb.vue'

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
  <div class="page-view">
    <div class="container container-lg">
      <AppBreadcrumb />
      <div class="page-header">
        <h1 class="page-title">{{ t('profile.editProfile') }}</h1>
      </div>

      <div v-if="isLoading" class="loading-container">
        <div class="spinner spinner-lg"></div>
        <p class="loading-text">{{ t('common.loading') }}</p>
      </div>

      <div v-else class="edit-content">
        <div v-if="error" class="alert alert-error edit-error">
          {{ error }}
        </div>

        <BaseCard>
          <template #header>
            <h2 class="card-heading">Base Information</h2>
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

            <div class="form-actions">
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
/* Header */
/* Loading */
.loading-container {
  text-align: center;
  padding: var(--spacing-12) 0;
}

.loading-text {
  margin-top: var(--spacing-4);
  color: var(--text-secondary);
}

/* Content */
.edit-content > * + * {
  margin-top: var(--spacing-6);
}

.edit-error {
  margin-bottom: var(--spacing-6);
}

/* Card heading */
.card-heading {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

/* Form actions */
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-4);
  margin-top: 2rem;
}
</style>
