<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore, useUiStore } from '@/stores'
import { oauthService, getErrorMessage } from '@/services'
import type { OAuthConsent } from '@/types'
import ConsentCard from '@/components/oauth/ConsentCard.vue'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseEmptyState from '@/components/common/BaseEmptyState.vue'
import { ShieldCheckIcon } from '@heroicons/vue/24/outline'

const { t } = useI18n()
const authStore = useAuthStore()
const uiStore = useUiStore()

const consents = ref<OAuthConsent[]>([])
const isLoading = ref(true)
const error = ref<string | null>(null)
const revokeTarget = ref<OAuthConsent | null>(null)
const isRevoking = ref(false)

async function loadConsents(): Promise<void> {
  isLoading.value = true
  error.value = null

  try {
    const userId = authStore.userId
    if (!userId) throw new Error('User not authenticated')
    consents.value = await oauthService.getConsents(userId)
  } catch (err) {
    error.value = getErrorMessage(err)
  } finally {
    isLoading.value = false
  }
}

onMounted(loadConsents)

function handleRevokeClick(consent: OAuthConsent): void {
  revokeTarget.value = consent
}

function cancelRevoke(): void {
  revokeTarget.value = null
}

async function confirmRevoke(): Promise<void> {
  if (!revokeTarget.value) return

  const target = revokeTarget.value
  isRevoking.value = true

  try {
    const userId = authStore.userId
    if (!userId) throw new Error('User not authenticated')
    await oauthService.revokeConsent(target.client_id, userId)
    revokeTarget.value = null
    uiStore.addNotification({
      type: 'success',
      message: t('oauth.revokeSuccess', { client: target.client_name })
    })
    await loadConsents()
  } catch (err) {
    error.value = getErrorMessage(err)
  } finally {
    isRevoking.value = false
  }
}
</script>

<template>
  <div class="consents-view">
    <div class="container container-lg">
      <div class="page-header">
        <div class="header-content">
          <div class="breadcrumb">
            <router-link to="/settings" class="breadcrumb-link">
              {{ t('nav.settings') }}
            </router-link>
            <span class="breadcrumb-separator">/</span>
            <span class="breadcrumb-current">{{ t('oauth.connectedApps') }}</span>
          </div>
          <h1 class="page-title">{{ t('oauth.connectedApps') }}</h1>
          <p class="page-description">{{ t('oauth.connectedAppsDescription') }}</p>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="isLoading" class="loading-state">
        <div class="spinner spinner-lg"></div>
        <p class="loading-text">{{ t('common.loading') }}</p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="alert alert-error">
        {{ error }}
      </div>

      <!-- Empty state -->
      <div v-else-if="consents.length === 0" class="empty-state">
        <BaseCard class="empty-card">
          <BaseEmptyState
            :title="t('oauth.noConnectedApps')"
            :description="t('oauth.noConnectedAppsDescription')"
          >
            <template #icon>
              <ShieldCheckIcon />
            </template>
          </BaseEmptyState>
        </BaseCard>
      </div>

      <!-- Consent list -->
      <div v-else class="consents-list">
        <ConsentCard
          v-for="consent in consents"
          :key="consent.id"
          :consent="consent"
          @revoke="handleRevokeClick"
        />
      </div>
    </div>

    <!-- Revoke confirmation modal -->
    <div v-if="revokeTarget" class="modal-overlay" @click.self="cancelRevoke">
      <div class="confirm-dialog">
        <h3 class="confirm-title">{{ t('oauth.revokeConfirmTitle') }}</h3>
        <p class="confirm-text">
          {{ t('oauth.revokeConfirmMessage', { client: revokeTarget.client_name }) }}
        </p>
        <div class="confirm-actions">
          <BaseButton variant="secondary" :disabled="isRevoking" @click="cancelRevoke">
            {{ t('common.cancel') }}
          </BaseButton>
          <BaseButton variant="danger" :loading="isRevoking" @click="confirmRevoke">
            {{ t('oauth.revokeAccess') }}
          </BaseButton>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.consents-view {
  padding: var(--spacing-8) 0;
}

.page-header {
  margin-bottom: var(--spacing-6);
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-2);
  font-size: var(--font-size-sm);
}

.breadcrumb-link {
  color: var(--text-secondary);
  text-decoration: none;
}

.breadcrumb-link:hover {
  color: var(--color-primary-600);
  text-decoration: underline;
}

.breadcrumb-separator {
  color: var(--text-tertiary);
}

.breadcrumb-current {
  color: var(--text-primary);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--spacing-12) 0;
}

.loading-text {
  margin-top: var(--spacing-4);
  color: var(--text-tertiary);
}

.alert-error {
  padding: var(--spacing-4);
  background-color: var(--color-error-50);
  border: 1px solid var(--color-error-200);
  border-radius: var(--radius-md);
  color: var(--color-error-700);
  margin-bottom: var(--spacing-6);
}

.empty-state {
  display: flex;
  justify-content: center;
}

.empty-card {
  max-width: 400px;
}

.consents-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

/* Revoke Confirmation Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal);
}

.confirm-dialog {
  background-color: var(--bg-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  padding: var(--spacing-6);
  max-width: 400px;
  width: 90%;
}

.confirm-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin: 0 0 var(--spacing-3) 0;
}

.confirm-text {
  color: var(--text-secondary);
  margin: 0 0 var(--spacing-6) 0;
  line-height: 1.5;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-3);
}
</style>
