<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { adminOAuthService, getErrorMessage } from '@/services'
import type { OAuthClientCreate, OAuthClientUpdate, OAuthClientCreateResponse } from '@/types'
import BaseCard from '@/components/common/BaseCard.vue'
import OAuthClientForm from '@/components/admin/OAuthClientForm.vue'
import OAuthClientSecretModal from '@/components/admin/OAuthClientSecretModal.vue'
import AppBreadcrumb from '@/components/layout/AppBreadcrumb.vue'

const router = useRouter()

const isLoading = ref(false)
const error = ref<string | null>(null)
const createdClient = ref<OAuthClientCreateResponse | null>(null)
const showSecretModal = ref(false)

async function handleSubmit(data: OAuthClientCreate | OAuthClientUpdate): Promise<void> {
  isLoading.value = true
  error.value = null

  try {
    const response = await adminOAuthService.createClient(data as OAuthClientCreate)
    createdClient.value = response
    showSecretModal.value = true
  } catch (err) {
    error.value = getErrorMessage(err)
  } finally {
    isLoading.value = false
  }
}

function handleCancel(): void {
  router.push({ name: 'admin-oauth-clients' })
}

function handleSecretModalClose(): void {
  showSecretModal.value = false
  router.push({ name: 'admin-oauth-clients' })
}

</script>

<template>
  <div class="admin-oauth-client-create-view">
    <div class="container container-lg">
      <AppBreadcrumb />

      <div class="page-header">
        <h1 class="page-title">Create OAuth Client</h1>
        <p class="page-description">
          Register a new OAuth client for third-party application integration.
        </p>
      </div>

      <div v-if="error" class="alert alert-error">
        {{ error }}
      </div>

      <BaseCard>
        <OAuthClientForm
          mode="create"
          :is-loading="isLoading"
          @submit="handleSubmit"
          @cancel="handleCancel"
        />
      </BaseCard>
    </div>

    <OAuthClientSecretModal
      :is-open="showSecretModal"
      :client-id="createdClient?.client_id ?? ''"
      :client-secret="createdClient?.client_secret ?? null"
      @close="handleSecretModalClose"
    />
  </div>
</template>

<style scoped>
.admin-oauth-client-create-view {
  padding: var(--spacing-8) 0;
}

.alert-error {
  padding: var(--spacing-4);
  background-color: var(--color-error-50);
  border: 1px solid var(--color-error-200);
  border-radius: var(--radius-md);
  color: var(--color-error-700);
  margin-bottom: var(--spacing-6);
}
</style>
