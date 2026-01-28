<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore, useProfileStore } from '@/stores'
import { profileService, contextService, getErrorMessage } from '@/services'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseBadge from '@/components/common/BaseBadge.vue'
import { CONTEXT_TYPE_META } from '@/types'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()
const profileStore = useProfileStore()

const isLoading = ref(true)
const error = ref<string | null>(null)

const initials = computed(() => {
  const name = profileStore.displayName || 'User'
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
})

onMounted(async () => {
  if (!authStore.userId) return

  try {
    const [profile, names, contexts] = await Promise.all([
      profileService.get(authStore.userId),
      profileService.getNames(authStore.userId),
      contextService.list(authStore.userId)
    ])
    
    profileStore.setProfile(profile)
    profileStore.setIdentityNames(names)
    profileStore.setContexts(contexts)
  } catch (err) {
    error.value = getErrorMessage(err)
  } finally {
    isLoading.value = false
  }
})

const navigateToEdit = () => {
  router.push({ name: 'profile-edit' })
}

const navigateToContexts = () => {
  router.push({ name: 'contexts' })
}

const navigateToCreateContext = () => {
  router.push({ name: 'context-create' })
}
</script>

<template>
  <div class="profile-view">
    <div class="container container-md">
      <div v-if="isLoading" class="loading-state">
        <div class="spinner spinner-lg"></div>
        <p class="mt-4 text-secondary">{{ t('common.loading') }}</p>
      </div>

      <div v-else-if="error" class="alert alert-error mb-6">
        {{ error }}
      </div>

      <div v-else-if="profileStore.profile" class="profile-content">
        <!-- Header Section -->
        <div class="profile-header mb-8 text-center">
          <div class="avatar-lg mx-auto mb-4 bg-primary-100 text-primary-700 flex items-center justify-center rounded-full">
            {{ initials }}
          </div>
          <h1 class="text-3xl font-bold text-gray-900 mb-1">{{ profileStore.displayName }}</h1>
          <p class="text-gray-500 mb-4">{{ profileStore.profile.primary_email }}</p>
          <BaseButton variant="secondary" @click="navigateToEdit">
            {{ t('profile.editProfile') }}
          </BaseButton>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- Base Information -->
          <BaseCard>
            <template #header>
              <h2 class="text-lg font-semibold">{{ t('profile.baseProfile') }}</h2>
            </template>
            
            <div class="space-y-4">
              <div class="field-group">
                <label class="field-label">{{ t('auth.accountType.label') }}</label>
                <div>
                  <BaseBadge :variant="profileStore.profile.account_type === 'verified' ? 'success' : 'warning'">
                    {{ t(`auth.accountType.${profileStore.profile.account_type}`) }}
                  </BaseBadge>
                </div>
              </div>

              <div class="field-group" v-if="profileStore.profile.legal_name">
                <label class="field-label">{{ t('profile.legalName') }}</label>
                <div class="field-value">{{ profileStore.profile.legal_name }}</div>
              </div>

              <div class="field-group">
                <label class="field-label">{{ t('profile.primaryEmail') }}</label>
                <div class="field-value">{{ profileStore.profile.primary_email }}</div>
              </div>

              <div class="field-group" v-if="profileStore.profile.primary_phone">
                <label class="field-label">{{ t('profile.primaryPhone') }}</label>
                <div class="field-value">{{ profileStore.profile.primary_phone }}</div>
              </div>

              <div class="field-group">
                <label class="field-label">{{ t('profile.preferredLanguage') }}</label>
                <div class="field-value">{{ profileStore.profile.preferred_language }}</div>
              </div>

              <div class="field-group">
                <label class="field-label">{{ t('profile.createdAt') }}</label>
                <div class="field-value">{{ new Date(profileStore.profile.created_at).toLocaleDateString() }}</div>
              </div>
            </div>
          </BaseCard>

          <!-- Identity Names -->
          <BaseCard>
            <template #header>
              <div class="flex justify-between items-center">
                <h2 class="text-lg font-semibold">Identity Names</h2>
                <BaseButton variant="ghost" size="sm" @click="navigateToEdit">+ Add</BaseButton>
              </div>
            </template>
            
            <div v-if="profileStore.identityNames.length === 0" class="text-gray-500 text-center py-4">
              No additional names configured.
            </div>

            <div v-else class="space-y-4">
              <div
                v-for="name in profileStore.identityNames"
                :key="name.id"
                class="name-item pb-4 border-b border-gray-100 last:border-0 last:pb-0"
              >
                <div class="flex items-center gap-2 mb-2">
                  <BaseBadge variant="primary" size="sm">{{ name.name_type }}</BaseBadge>
                  <BaseBadge v-if="name.is_primary" variant="success" size="sm">Primary</BaseBadge>
                </div>
                <div class="flex flex-wrap gap-x-4 gap-y-1">
                  <div
                    v-for="(value, lang) in name.name_value"
                    :key="lang"
                    class="text-sm"
                  >
                    <span class="font-medium text-gray-500 uppercase text-xs mr-1">{{ lang }}</span>
                    <span class="text-gray-900">{{ value }}</span>
                  </div>
                </div>
              </div>
            </div>
          </BaseCard>

          <!-- Identity Contexts -->
          <BaseCard class="md:col-span-2">
            <template #header>
              <div class="flex justify-between items-center">
                <h2 class="text-lg font-semibold">Identity Contexts</h2>
                <BaseButton variant="ghost" size="sm" @click="navigateToCreateContext">+ Create</BaseButton>
              </div>
            </template>

            <div v-if="profileStore.contexts.length === 0" class="text-center py-8">
              <div class="text-gray-500 mb-4">No contexts yet. Create one to separate your identities.</div>
              <BaseButton variant="primary" @click="navigateToCreateContext">Create Context</BaseButton>
            </div>

            <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <div
                v-for="context in profileStore.contexts"
                :key="context.id"
                class="context-card p-4 border border-gray-200 rounded-lg hover:border-primary-300 hover:shadow-sm transition-all cursor-pointer bg-white"
                @click="router.push({ name: 'context-detail', params: { id: context.id } })"
              >
                <div class="flex items-start justify-between mb-2">
                  <BaseBadge :variant="context.context_type">
                    {{ CONTEXT_TYPE_META[context.context_type]?.label || context.context_type }}
                  </BaseBadge>
                  <span class="text-gray-400">→</span>
                </div>
                <h3 class="font-medium text-gray-900 mb-1">{{ context.context_name }}</h3>
                <p class="text-sm text-gray-500 line-clamp-2">{{ context.bio || 'Inherited bio' }}</p>
              </div>
            </div>
            
            <template #footer>
              <div class="text-center">
                <BaseButton variant="ghost" @click="navigateToContexts">View All Contexts</BaseButton>
              </div>
            </template>
          </BaseCard>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.profile-view {
  padding: var(--spacing-8) 0;
}

.avatar-lg {
  width: 80px;
  height: 80px;
  font-size: 2rem;
  font-weight: 600;
}

.field-label {
  font-size: var(--font-size-xs);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-gray-500);
  margin-bottom: var(--spacing-1);
}

.field-value {
  font-size: var(--font-size-base);
  color: var(--text-primary);
}

/* Utility classes that might be missing if Tailwind isn't fully set up */
.grid { display: grid; }
.grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)); }
.gap-6 { gap: 1.5rem; }
.gap-4 { gap: 1rem; }
.space-y-4 > * + * { margin-top: 1rem; }
.text-center { text-align: center; }
.mx-auto { margin-left: auto; margin-right: auto; }
.mb-8 { margin-bottom: 2rem; }
.mb-6 { margin-bottom: 1.5rem; }
.mb-4 { margin-bottom: 1rem; }
.mb-2 { margin-bottom: 0.5rem; }
.mb-1 { margin-bottom: 0.25rem; }
.text-3xl { font-size: 1.875rem; line-height: 2.25rem; }
.font-bold { font-weight: 700; }
.font-semibold { font-weight: 600; }
.font-medium { font-weight: 500; }
.text-lg { font-size: 1.125rem; line-height: 1.75rem; }
.text-sm { font-size: 0.875rem; line-height: 1.25rem; }
.text-xs { font-size: 0.75rem; line-height: 1rem; }
.text-gray-900 { color: var(--text-primary); }
.text-gray-500 { color: var(--text-secondary); }
.text-gray-400 { color: var(--text-tertiary); }
.bg-primary-100 { background-color: var(--color-primary-100); }
.text-primary-700 { color: var(--color-primary-700); }
.rounded-full { border-radius: 9999px; }
.flex { display: flex; }
.items-center { align-items: center; }
.justify-center { justify-content: center; }
.justify-between { justify-content: space-between; }
.flex-wrap { flex-wrap: wrap; }
.gap-x-4 { column-gap: 1rem; }
.gap-y-1 { row-gap: 0.25rem; }
.uppercase { text-transform: uppercase; }
.mr-1 { margin-right: 0.25rem; }
.p-4 { padding: 1rem; }
.border { border-width: 1px; }
.border-gray-200 { border-color: var(--border-primary); }
.border-gray-100 { border-color: var(--border-primary); }
.border-b { border-bottom-width: 1px; }
.rounded-lg { border-radius: 0.5rem; }
.bg-white { background-color: var(--bg-secondary); }
.cursor-pointer { cursor: pointer; }
.line-clamp-2 {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

@media (min-width: 768px) {
  .md\:grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .md\:col-span-2 { grid-column: span 2 / span 2; }
}

@media (min-width: 640px) {
  .sm\:grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (min-width: 1024px) {
  .lg\:grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
</style>
