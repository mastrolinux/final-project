<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { adminUsersService, getErrorMessage } from "@/services";
import { useUiStore } from "@/stores/ui.store";
import type { SoftDeletedUser } from "@/types";
import BaseCard from "@/components/common/BaseCard.vue";
import BaseButton from "@/components/common/BaseButton.vue";
import SoftDeletedUserCard from "@/components/admin/SoftDeletedUserCard.vue";
import { TrashIcon, UsersIcon } from "@heroicons/vue/24/outline";

const uiStore = useUiStore();

const users = ref<SoftDeletedUser[]>([]);
const isLoading = ref(true);
const error = ref<string | null>(null);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);

// Purge modal state
const showPurgeModal = ref(false);
const purgeConfirmInput = ref("");
const isPurging = ref(false);

const canPurge = computed(() => purgeConfirmInput.value === "PURGE");

const expiredCount = computed(() => {
  const now = new Date();
  return users.value.filter((u) => {
    const deletedAt = new Date(u.deleted_at);
    const purgeDate = new Date(
      deletedAt.getTime() + 30 * 24 * 60 * 60 * 1000,
    );
    return purgeDate <= now;
  }).length;
});

async function loadUsers(): Promise<void> {
  isLoading.value = true;
  error.value = null;

  try {
    const response = await adminUsersService.listSoftDeletedUsers(
      page.value,
      pageSize.value,
    );
    users.value = response.users;
    total.value = response.total;
  } catch (err) {
    error.value = getErrorMessage(err);
  } finally {
    isLoading.value = false;
  }
}

onMounted(loadUsers);

function openPurgeModal(): void {
  purgeConfirmInput.value = "";
  showPurgeModal.value = true;
}

function closePurgeModal(): void {
  showPurgeModal.value = false;
  purgeConfirmInput.value = "";
}

async function confirmPurge(): Promise<void> {
  if (!canPurge.value) return;

  isPurging.value = true;
  try {
    const result = await adminUsersService.purgeExpiredUsers();
    closePurgeModal();
    if (result.purged_count > 0) {
      uiStore.showSuccess(
        `Permanently purged ${result.purged_count} expired account(s).`,
      );
    } else {
      uiStore.showInfo("No expired accounts to purge.");
    }
    await loadUsers();
  } catch (err) {
    error.value = getErrorMessage(err);
  } finally {
    isPurging.value = false;
  }
}
</script>

<template>
  <div class="admin-soft-deleted-users-view">
    <div class="container container-lg">
      <div class="page-header">
        <div class="header-content">
          <h1 class="page-title">Soft-Deleted Users</h1>
          <p class="page-description">
            User accounts scheduled for permanent deletion. Accounts are
            automatically purged after a 30-day retention period.
          </p>
        </div>
        <BaseButton
          v-if="users.length > 0"
          variant="danger"
          @click="openPurgeModal"
        >
          <TrashIcon class="btn-icon" />
          Purge Expired
        </BaseButton>
      </div>

      <div v-if="!isLoading && users.length > 0" class="summary-bar">
        <span class="summary-text">
          {{ total }} soft-deleted account(s), {{ expiredCount }} expired
        </span>
      </div>

      <div v-if="isLoading" class="loading-state">
        <div class="spinner spinner-lg"></div>
        <p class="loading-text">Loading soft-deleted users...</p>
      </div>

      <div v-else-if="error" class="alert alert-error">
        {{ error }}
      </div>

      <div v-else-if="users.length === 0" class="empty-state">
        <BaseCard class="empty-card">
          <div class="empty-icon">
            <UsersIcon class="icon-lg" />
          </div>
          <h3 class="empty-title">No soft-deleted accounts</h3>
          <p class="empty-description">
            There are no user accounts currently scheduled for deletion.
          </p>
        </BaseCard>
      </div>

      <div v-else class="users-list">
        <SoftDeletedUserCard
          v-for="user in users"
          :key="user.user_id"
          :user="user"
        />
      </div>

      <div v-if="total > pageSize" class="pagination">
        <span class="pagination-info">
          Showing {{ users.length }} of {{ total }} accounts
        </span>
      </div>
    </div>

    <!-- Purge Confirmation Modal -->
    <div
      v-if="showPurgeModal"
      class="modal-overlay"
      @click.self="closePurgeModal"
    >
      <div class="confirm-dialog">
        <h3 class="confirm-title">Purge Expired Accounts?</h3>
        <p class="confirm-text">
          This will permanently delete all soft-deleted accounts whose 30-day
          retention period has expired. This action is irreversible.
        </p>
        <p v-if="expiredCount > 0" class="confirm-count">
          {{ expiredCount }} account(s) will be permanently purged.
        </p>
        <p v-else class="confirm-count confirm-count-none">
          No accounts have expired yet. Running this will purge 0 accounts.
        </p>
        <label class="confirm-label" for="purge-confirm-input">
          Type PURGE to confirm
        </label>
        <input
          id="purge-confirm-input"
          v-model="purgeConfirmInput"
          type="text"
          class="confirm-input"
          placeholder="PURGE"
          autocomplete="off"
        />
        <div class="confirm-actions">
          <BaseButton
            variant="secondary"
            :disabled="isPurging"
            @click="closePurgeModal"
          >
            Cancel
          </BaseButton>
          <BaseButton
            variant="danger"
            :disabled="!canPurge"
            :loading="isPurging"
            @click="confirmPurge"
          >
            Purge Expired Accounts
          </BaseButton>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-soft-deleted-users-view {
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

.btn-icon {
  width: 20px;
  height: 20px;
  margin-right: var(--spacing-1);
}

.summary-bar {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-6);
  padding: var(--spacing-3) var(--spacing-4);
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
}

.summary-text {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
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
  margin: 0;
  line-height: 1.5;
}

.users-list {
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

/* Purge Confirmation Modal */
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
  max-width: 440px;
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
  margin: 0 0 var(--spacing-3) 0;
  line-height: 1.5;
}

.confirm-count {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-error-600);
  margin: 0 0 var(--spacing-4) 0;
}

.confirm-count-none {
  color: var(--text-tertiary);
}

.confirm-label {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-2);
}

.confirm-input {
  width: 100%;
  padding: var(--spacing-2) var(--spacing-3);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  background-color: var(--input-bg);
  color: var(--text-primary);
  margin-bottom: var(--spacing-4);
  box-sizing: border-box;
}

.confirm-input:focus {
  outline: none;
  border-color: var(--color-primary-500);
  box-shadow: 0 0 0 2px var(--color-primary-100);
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-3);
}
</style>
