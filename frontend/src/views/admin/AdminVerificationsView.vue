<script setup lang="ts">
/**
 * Admin view listing context profiles pending verification review.
 *
 * Displays a queue of contexts with linked identity documents that
 * administrators can review, approve, or reject.
 */
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { adminVerificationService, getErrorMessage } from "@/services";
import BaseCard from "@/components/common/BaseCard.vue";
import AdminVerificationCard from "@/components/admin/AdminVerificationCard.vue";
import { DocumentCheckIcon } from "@heroicons/vue/24/outline";
import type { AdminContextVerificationItem } from "@/types";

const router = useRouter();
const { t } = useI18n();

const contexts = ref<AdminContextVerificationItem[]>([]);
const isLoading = ref(true);
const error = ref<string | null>(null);

async function loadContexts(): Promise<void> {
  isLoading.value = true;
  error.value = null;

  try {
    contexts.value = await adminVerificationService.listPendingContexts();
  } catch (err) {
    error.value = getErrorMessage(err);
  } finally {
    isLoading.value = false;
  }
}

function handleReview(contextId: string): void {
  router.push({
    name: "admin-verification-review",
    params: { contextId },
  });
}

onMounted(loadContexts);
</script>

<template>
  <div class="admin-verifications-view">
    <div class="container container-lg">
      <div class="page-header">
        <div class="header-content">
          <h1 class="page-title">
            {{ t("verification.admin.title") }}
          </h1>
          <p class="page-description">
            {{ t("verification.admin.description") }}
          </p>
        </div>
      </div>

      <div v-if="!isLoading && contexts.length > 0" class="summary-bar">
        <span class="summary-text">
          {{
            t("verification.admin.pendingCount", {
              count: contexts.length,
            })
          }}
        </span>
      </div>

      <!-- Loading -->
      <div v-if="isLoading" class="loading-state">
        <div class="spinner spinner-lg"></div>
        <p class="loading-text">
          {{ t("verification.admin.loading") }}
        </p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="alert alert-error">
        {{ error }}
      </div>

      <!-- Empty state -->
      <div v-else-if="contexts.length === 0" class="empty-state">
        <BaseCard class="empty-card">
          <div class="empty-icon">
            <DocumentCheckIcon class="icon-lg" />
          </div>
          <h3 class="empty-title">
            {{ t("verification.admin.emptyTitle") }}
          </h3>
          <p class="empty-description">
            {{ t("verification.admin.emptyDescription") }}
          </p>
        </BaseCard>
      </div>

      <!-- Context queue -->
      <div v-else class="documents-queue">
        <AdminVerificationCard
          v-for="ctx in contexts"
          :key="ctx.context_id"
          :context="ctx"
          @review="handleReview"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-verifications-view {
  padding: var(--spacing-8) 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-6);
}

.header-content {
  flex: 1;
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
  margin: 0 0 var(--spacing-2) 0;
}

.page-description {
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.5;
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

.documents-queue {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}
</style>
