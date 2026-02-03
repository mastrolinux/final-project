<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { adminOAuthService, getErrorMessage } from '@/services'
import type { OAuthClientResponse } from '@/types'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import OAuthClientCard from '@/components/admin/OAuthClientCard.vue'
import { PlusIcon, Cog6ToothIcon } from '@heroicons/vue/24/outline'

const router = useRouter()

const clients = ref<OAuthClientResponse[]>([])
const isLoading = ref(true)
const error = ref<string | null>(null)
const includeInactive = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const deleteConfirm = ref<string | null>(null)
const isDeleting = ref(false)

async function loadClients(): Promise<void> {
  isLoading.value = true
  error.value = null

  try {
    const response = await adminOAuthService.listClients(
      page.value,
      pageSize.value,
      includeInactive.value
    )
    clients.value = response.clients
    total.value = response.total
  } catch (err) {
    error.value = getErrorMessage(err)
  } finally {
    isLoading.value = false
  }
}

onMounted(loadClients)

function navigateToCreate(): void {
  router.push({ name: 'admin-oauth-client-create' })
}

function handleEdit(clientId: string): void {
  router.push({ name: 'admin-oauth-client-edit', params: { clientId } })
}

function handleDeleteClick(clientId: string): void {
  deleteConfirm.value = clientId
}

function cancelDelete(): void {
  deleteConfirm.value = null
}

async function confirmDelete(): Promise<void> {
  if (!deleteConfirm.value) return

  isDeleting.value = true
  try {
    await adminOAuthService.deleteClient(deleteConfirm.value)
    await loadClients()
    deleteConfirm.value = null
  } catch (err) {
    error.value = getErrorMessage(err)
  } finally {
    isDeleting.value = false
  }
}

async function toggleInactive(): Promise<void> {
  includeInactive.value = !includeInactive.value
  page.value = 1
  await loadClients()
}
</script>

<template>
  <div class="admin-oauth-clients-view">
    <div class="container container-lg">
      <div class="page-header">
        <div class="header-content">
          <h1 class="page-title">OAuth Clients</h1>
          <p class="page-description">
            Manage OAuth client integrations for third-party applications.
          </p>
        </div>
        <BaseButton variant="primary" @click="navigateToCreate">
          <PlusIcon class="btn-icon" />
          New Client
        </BaseButton>
      </div>

      <div class="filters-bar">
        <label class="filter-checkbox">
          <input
            type="checkbox"
            :checked="includeInactive"
            @change="toggleInactive"
          />
          <span>Show inactive clients</span>
        </label>
      </div>

      <div v-if="isLoading" class="loading-state">
        <div class="spinner spinner-lg"></div>
        <p class="loading-text">Loading clients...</p>
      </div>

      <div v-else-if="error" class="alert alert-error">
        {{ error }}
      </div>

      <div v-else-if="clients.length === 0" class="empty-state">
        <BaseCard class="empty-card">
          <div class="empty-icon">
            <Cog6ToothIcon class="icon-lg" />
          </div>
          <h3 class="empty-title">No OAuth clients</h3>
          <p class="empty-description">
            Create your first OAuth client to allow third-party applications
            to integrate with your identity service.
          </p>
          <BaseButton variant="primary" @click="navigateToCreate">
            <PlusIcon class="btn-icon" />
            Create Client
          </BaseButton>
        </BaseCard>
      </div>

      <div v-else class="clients-list">
        <OAuthClientCard
          v-for="client in clients"
          :key="client.client_id"
          :client="client"
          @edit="handleEdit"
          @delete="handleDeleteClick"
        />
      </div>

      <div v-if="total > pageSize" class="pagination">
        <span class="pagination-info">
          Showing {{ clients.length }} of {{ total }} clients
        </span>
      </div>
    </div>

    <!-- Delete Confirmation Dialog -->
    <div v-if="deleteConfirm" class="modal-overlay" @click.self="cancelDelete">
      <div class="confirm-dialog">
        <h3 class="confirm-title">Delete OAuth Client?</h3>
        <p class="confirm-text">
          This will deactivate the client <strong>{{ deleteConfirm }}</strong>.
          Existing tokens will continue to work until they expire.
        </p>
        <div class="confirm-actions">
          <BaseButton variant="secondary" :disabled="isDeleting" @click="cancelDelete">
            Cancel
          </BaseButton>
          <BaseButton variant="danger" :loading="isDeleting" @click="confirmDelete">
            Delete Client
          </BaseButton>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-oauth-clients-view {
  padding: var(--spacing-8) 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-6);
  flex-wrap: wrap;
}

.header-content {
  flex: 1;
  min-width: 200px;
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
  margin: 0 0 var(--spacing-1) 0;
}

.page-description {
  color: var(--text-secondary);
  margin: 0;
}

.btn-icon {
  width: 20px;
  height: 20px;
  margin-right: var(--spacing-1);
}

.filters-bar {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-6);
  padding: var(--spacing-3) var(--spacing-4);
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
}

.filter-checkbox {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  cursor: pointer;
}

.filter-checkbox input[type='checkbox'] {
  width: 16px;
  height: 16px;
  accent-color: var(--color-primary-600);
  cursor: pointer;
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
  text-align: center;
  padding: var(--spacing-12) var(--spacing-8);
  max-width: 400px;
}

.empty-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  margin: 0 auto var(--spacing-4);
  background-color: var(--bg-tertiary);
  border-radius: var(--radius-full);
}

.icon-lg {
  width: 32px;
  height: 32px;
  color: var(--text-tertiary);
}

.empty-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin: 0 0 var(--spacing-2) 0;
}

.empty-description {
  color: var(--text-secondary);
  margin: 0 0 var(--spacing-6) 0;
  line-height: 1.5;
}

.clients-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: var(--spacing-6);
}

.pagination-info {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
}

/* Delete Confirmation Modal */
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
