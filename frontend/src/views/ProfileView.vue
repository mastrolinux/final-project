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
  <div class="page-view">
    <div class="container container-lg">
      <div v-if="isLoading" class="loading-state">
        <div class="spinner spinner-lg"></div>
        <p class="loading-text">{{ t('common.loading') }}</p>
      </div>

      <div v-else-if="error" class="alert alert-error alert-spaced">
        {{ error }}
      </div>

      <div v-else-if="profileStore.profile" class="profile-content">
        <!-- Header Section -->
        <div class="profile-header">
          <div class="profile-avatar">
            {{ initials }}
          </div>
          <h1 class="profile-name">{{ profileStore.displayName }}</h1>
          <p class="profile-email">{{ profileStore.profile.primary_email }}</p>
          <BaseButton variant="secondary" @click="navigateToEdit">
            {{ t('profile.editProfile') }}
          </BaseButton>
        </div>

        <div class="profile-grid">
          <!-- Base Information -->
          <BaseCard>
            <template #header>
              <h2 class="card-heading">{{ t('profile.baseProfile') }}</h2>
            </template>

            <div class="fields-list">
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
              <div class="card-header-row">
                <h2 class="card-heading">Identity Names</h2>
                <BaseButton variant="ghost" size="sm" @click="navigateToEdit">+ Add</BaseButton>
              </div>
            </template>

            <div v-if="profileStore.identityNames.length === 0" class="empty-names">
              No additional names configured.
            </div>

            <div v-else class="fields-list">
              <div
                v-for="name in profileStore.identityNames"
                :key="name.id"
                class="name-item"
              >
                <div class="name-badges">
                  <BaseBadge variant="primary" size="sm">{{ name.name_type }}</BaseBadge>
                  <BaseBadge v-if="name.is_primary" variant="success" size="sm">Primary</BaseBadge>
                </div>
                <div class="name-languages">
                  <div
                    v-for="(value, lang) in name.name_value"
                    :key="lang"
                    class="name-lang-entry"
                  >
                    <span class="name-lang-code">{{ lang }}</span>
                    <span class="name-lang-value">{{ value }}</span>
                  </div>
                </div>
              </div>
            </div>
          </BaseCard>

          <!-- Identity Contexts -->
          <BaseCard class="col-span-full">
            <template #header>
              <div class="card-header-row">
                <h2 class="card-heading">Identity Contexts</h2>
                <BaseButton variant="ghost" size="sm" @click="navigateToCreateContext">+ Create</BaseButton>
              </div>
            </template>

            <div v-if="profileStore.contexts.length === 0" class="empty-contexts">
              <div class="empty-contexts-text">No contexts yet. Create one to separate your identities.</div>
              <BaseButton variant="primary" @click="navigateToCreateContext">Create Context</BaseButton>
            </div>

            <div v-else class="contexts-cards">
              <div
                v-for="context in profileStore.contexts"
                :key="context.id"
                class="context-card"
                @click="router.push({ name: 'context-detail', params: { id: context.id } })"
              >
                <div class="context-card-header">
                  <BaseBadge :variant="context.context_type">
                    {{ CONTEXT_TYPE_META[context.context_type]?.label || context.context_type }}
                  </BaseBadge>
                  <span class="context-card-arrow">-></span>
                </div>
                <h3 class="context-card-title">{{ context.context_name }}</h3>
                <p class="context-card-bio">{{ context.bio || 'Inherited bio' }}</p>
              </div>
            </div>

            <template #footer>
              <div class="card-footer-center">
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
/* Loading state */
.loading-state {
  text-align: center;
  padding: var(--spacing-12) 0;
}

.loading-text {
  margin-top: var(--spacing-4);
  color: var(--text-secondary);
}

.alert-spaced {
  margin-bottom: var(--spacing-6);
}

/* Profile header */
.profile-header {
  text-align: center;
  margin-bottom: var(--spacing-8);
}

.profile-avatar {
  width: 80px;
  height: 80px;
  font-size: 2rem;
  font-weight: var(--font-weight-semibold);
  margin: 0 auto var(--spacing-4);
  background-color: var(--color-primary-100);
  color: var(--color-primary-700);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
}

.profile-name {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
  margin-bottom: var(--spacing-1);
}

.profile-email {
  color: var(--text-secondary);
  margin-bottom: var(--spacing-4);
}

/* Profile grid */
.profile-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--spacing-6);
}

@media (min-width: 768px) {
  .profile-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .col-span-full {
    grid-column: span 2 / span 2;
  }
}

/* Card elements */
.card-heading {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-footer-center {
  text-align: center;
}

/* Field display */
.fields-list > * + * {
  margin-top: var(--spacing-4);
}

.field-label {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-tertiary);
  margin-bottom: var(--spacing-1);
}

.field-value {
  font-size: var(--font-size-base);
  color: var(--text-primary);
}

/* Identity names */
.empty-names {
  color: var(--text-secondary);
  text-align: center;
  padding: var(--spacing-4) 0;
}

.name-item {
  padding-bottom: var(--spacing-4);
  border-bottom: 1px solid var(--border-primary);
}

.name-item:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

.name-badges {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-2);
}

.name-languages {
  display: flex;
  flex-wrap: wrap;
  column-gap: var(--spacing-4);
  row-gap: var(--spacing-1);
}

.name-lang-entry {
  font-size: var(--font-size-sm);
}

.name-lang-code {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
  text-transform: uppercase;
  margin-right: var(--spacing-1);
}

.name-lang-value {
  color: var(--text-primary);
}

/* Context cards */
.empty-contexts {
  text-align: center;
  padding: var(--spacing-8) 0;
}

.empty-contexts-text {
  color: var(--text-secondary);
  margin-bottom: var(--spacing-4);
}

.contexts-cards {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--spacing-4);
}

@media (min-width: 640px) {
  .contexts-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 1024px) {
  .contexts-cards {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.context-card {
  padding: var(--spacing-4);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  background-color: var(--bg-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.context-card:hover {
  border-color: var(--color-primary-300);
  box-shadow: var(--shadow-sm);
}

.context-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: var(--spacing-2);
}

.context-card-arrow {
  color: var(--text-tertiary);
}

.context-card-title {
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  margin-bottom: var(--spacing-1);
}

.context-card-bio {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}
</style>
