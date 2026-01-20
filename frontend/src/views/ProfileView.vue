<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore, useProfileStore } from '@/stores'
import { profileService, getErrorMessage } from '@/services'

const { t } = useI18n()
const authStore = useAuthStore()
const profileStore = useProfileStore()

const isLoading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  if (!authStore.userId) return

  try {
    const profile = await profileService.get(authStore.userId)
    profileStore.setProfile(profile)

    const names = await profileService.getNames(authStore.userId)
    profileStore.setIdentityNames(names)
  } catch (err) {
    error.value = getErrorMessage(err)
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <div class="profile-view">
    <div class="container container-md">
      <div class="page-header">
        <h1 class="page-title">{{ t('profile.title') }}</h1>
      </div>

      <div v-if="isLoading" class="loading-state">
        <div class="spinner"></div>
        <p>{{ t('common.loading') }}</p>
      </div>

      <div v-else-if="error" class="alert alert-error">
        {{ error }}
      </div>

      <div v-else-if="profileStore.profile" class="profile-content">
        <div class="card">
          <div class="card-header">
            <h2>{{ t('profile.baseProfile') }}</h2>
          </div>
          <div class="card-body">
            <div class="profile-field">
              <label>{{ t('auth.accountType.label') }}</label>
              <span class="badge" :class="`badge-${profileStore.profile.account_type}`">
                {{ t(`auth.accountType.${profileStore.profile.account_type}`) }}
              </span>
            </div>

            <div class="profile-field" v-if="profileStore.profile.legal_name">
              <label>{{ t('profile.legalName') }}</label>
              <span>{{ profileStore.profile.legal_name }}</span>
            </div>

            <div class="profile-field">
              <label>{{ t('profile.primaryEmail') }}</label>
              <span>{{ profileStore.profile.primary_email }}</span>
            </div>

            <div class="profile-field" v-if="profileStore.profile.primary_phone">
              <label>{{ t('profile.primaryPhone') }}</label>
              <span>{{ profileStore.profile.primary_phone }}</span>
            </div>

            <div class="profile-field">
              <label>{{ t('profile.preferredLanguage') }}</label>
              <span>{{ profileStore.profile.preferred_language }}</span>
            </div>

            <div class="profile-field">
              <label>{{ t('profile.createdAt') }}</label>
              <span>{{ new Date(profileStore.profile.created_at).toLocaleDateString() }}</span>
            </div>
          </div>
          <div class="card-footer">
            <button class="btn btn-secondary">
              {{ t('profile.editProfile') }}
            </button>
          </div>
        </div>

        <div class="card mt-6" v-if="profileStore.identityNames.length > 0">
          <div class="card-header">
            <h2>Identity Names</h2>
          </div>
          <div class="card-body">
            <div
              v-for="name in profileStore.identityNames"
              :key="name.id"
              class="name-item"
            >
              <div class="name-type">
                <span class="badge badge-primary">{{ name.name_type }}</span>
                <span v-if="name.is_primary" class="badge badge-success">Primary</span>
              </div>
              <div class="name-values">
                <span
                  v-for="(value, lang) in name.name_value"
                  :key="lang"
                  class="name-value"
                >
                  <strong>{{ lang }}:</strong> {{ value }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.profile-view {
  padding: var(--spacing-6) 0;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-12);
  color: var(--text-secondary);
}

.profile-field {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
  padding: var(--spacing-3) 0;
  border-bottom: 1px solid var(--border-primary);
}

.profile-field:last-child {
  border-bottom: none;
}

.profile-field label {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  margin-bottom: 0;
}

.profile-field span {
  font-size: var(--font-size-base);
}

.name-item {
  padding: var(--spacing-3) 0;
  border-bottom: 1px solid var(--border-primary);
}

.name-item:last-child {
  border-bottom: none;
}

.name-type {
  display: flex;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-2);
}

.name-values {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-4);
}

.name-value {
  font-size: var(--font-size-sm);
}

.badge-verified {
  background-color: var(--color-success-50);
  color: var(--color-success-700);
}

.badge-unverified {
  background-color: var(--color-warning-50);
  color: var(--color-warning-700);
}

.badge-pseudonymous {
  background-color: var(--color-gray-100);
  color: var(--color-gray-700);
}
</style>
