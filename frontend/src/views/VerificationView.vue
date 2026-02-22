<script setup lang="ts">
/**
 * User-facing verification page.
 *
 * Displays the current verification status, allows document upload,
 * and lists previously submitted documents with their review outcomes.
 */
import { ref, computed, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { useAuthStore } from "@/stores/auth.store";
import { useUiStore } from "@/stores/ui.store";
import { verificationService, getErrorMessage } from "@/services";
import BaseCard from "@/components/common/BaseCard.vue";
import BaseBadge from "@/components/common/BaseBadge.vue";
import DocumentUpload from "@/components/verification/DocumentUpload.vue";
import VerificationDocumentCard from "@/components/verification/VerificationDocumentCard.vue";
import {
  ShieldCheckIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  DocumentPlusIcon,
} from "@heroicons/vue/24/outline";
import type {
  VerificationStatusResponse,
  VerificationDocumentResponse,
  DocumentType,
} from "@/types";

const { t } = useI18n();
const authStore = useAuthStore();
const uiStore = useUiStore();

const isLoading = ref(true);
const isUploading = ref(false);
const error = ref<string | null>(null);
const status = ref<VerificationStatusResponse | null>(null);
const documents = ref<VerificationDocumentResponse[]>([]);

type BadgeVariant = "primary" | "success" | "warning" | "error" | "info" | "neutral";

const accountTypeVariant = computed<BadgeVariant>(() => {
  if (!status.value) return "neutral";
  const map: Record<string, BadgeVariant> = {
    verified: "success",
    unverified: "warning",
    pseudonymous: "neutral",
  };
  return map[status.value.account_type] || "neutral";
});

const statusIcon = computed(() => {
  if (!status.value) return ClockIcon;
  if (status.value.account_type === "verified") return ShieldCheckIcon;
  if (status.value.latest_document?.verification_status === "rejected")
    return ExclamationTriangleIcon;
  return ClockIcon;
});

const canUpload = computed(() => {
  if (!status.value) return false;
  // Allow upload if no pending/under_review document exists
  if (!status.value.latest_document) return true;
  const latestStatus = status.value.latest_document.verification_status;
  return latestStatus === "rejected" || latestStatus === "verified";
});

async function loadData(): Promise<void> {
  if (!authStore.userId) return;
  isLoading.value = true;
  error.value = null;

  try {
    const [statusData, docsData] = await Promise.all([
      verificationService.getVerificationStatus(authStore.userId),
      verificationService.listDocuments(authStore.userId),
    ]);
    status.value = statusData;
    documents.value = docsData;
  } catch (err) {
    error.value = getErrorMessage(err);
  } finally {
    isLoading.value = false;
  }
}

async function handleUpload(payload: {
  file: File;
  documentType: DocumentType;
}): Promise<void> {
  if (!authStore.userId) return;
  isUploading.value = true;

  try {
    await verificationService.uploadDocument(
      authStore.userId,
      payload.file,
      payload.documentType,
    );
    uiStore.showSuccess(t("verification.upload.success"));
    await loadData();
  } catch (err) {
    uiStore.showError(getErrorMessage(err));
  } finally {
    isUploading.value = false;
  }
}

onMounted(loadData);
</script>

<template>
  <div class="verification-view">
    <div class="container container-md">
      <div class="page-header">
        <h1 class="page-title">
          {{ t("verification.title") }}
        </h1>
        <p class="page-description">
          {{ t("verification.description") }}
        </p>
      </div>

      <!-- Loading -->
      <div v-if="isLoading" class="loading-state">
        <div class="spinner spinner-lg"></div>
        <p class="loading-text">
          {{ t("verification.loading") }}
        </p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="alert alert-error">
        {{ error }}
      </div>

      <!-- Content -->
      <template v-else>
        <!-- Verification status card -->
        <BaseCard class="status-card">
          <div class="status-content">
            <div class="status-icon-wrapper">
              <component
                :is="statusIcon"
                class="status-icon"
                :class="{
                  'status-icon-verified': status?.account_type === 'verified',
                  'status-icon-pending': status?.account_type !== 'verified',
                }"
              />
            </div>
            <div class="status-info">
              <div class="status-row">
                <span class="status-label">
                  {{ t("verification.accountType") }}
                </span>
                <BaseBadge :variant="accountTypeVariant" size="sm">
                  {{ t(`verification.accountTypes.${status?.account_type}`) }}
                </BaseBadge>
              </div>
              <p class="status-explanation">
                <template v-if="status?.account_type === 'verified'">
                  {{ t("verification.statusExplain.verified") }}
                </template>
                <template v-else-if="status?.account_type === 'pseudonymous'">
                  {{ t("verification.statusExplain.pseudonymous") }}
                </template>
                <template v-else>
                  {{ t("verification.statusExplain.unverified") }}
                </template>
              </p>
            </div>
          </div>
        </BaseCard>

        <!-- Upload section -->
        <section class="upload-section">
          <h2 class="section-title">
            <DocumentPlusIcon class="section-icon" />
            {{ t("verification.upload.title") }}
          </h2>

          <template v-if="canUpload">
            <DocumentUpload
              :is-uploading="isUploading"
              @upload="handleUpload"
            />
          </template>
          <template v-else>
            <BaseCard class="upload-blocked">
              <p class="upload-blocked-text">
                {{ t("verification.upload.pendingExists") }}
              </p>
            </BaseCard>
          </template>
        </section>

        <!-- Document history -->
        <section v-if="documents.length > 0" class="documents-section">
          <h2 class="section-title">
            {{ t("verification.documents.title") }}
          </h2>
          <div class="documents-list">
            <VerificationDocumentCard
              v-for="doc in documents"
              :key="doc.id"
              :document="doc"
            />
          </div>
        </section>
      </template>
    </div>
  </div>
</template>

<style scoped>
.verification-view {
  padding: var(--spacing-8) 0;
}

.page-header {
  margin-bottom: var(--spacing-8);
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
  line-height: 1.6;
}

/* Loading */
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
}

/* Status card */
.status-card {
  margin-bottom: var(--spacing-8);
}

.status-content {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-5);
}

.status-icon-wrapper {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: var(--radius-full);
  background-color: var(--bg-tertiary);
}

.status-icon {
  width: 28px;
  height: 28px;
}

.status-icon-verified {
  color: var(--color-success-600);
}

.status-icon-pending {
  color: var(--color-warning-600);
}

.status-info {
  flex: 1;
}

.status-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  margin-bottom: var(--spacing-2);
}

.status-label {
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

.status-explanation {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.6;
}

/* Upload section */
.upload-section {
  margin-bottom: var(--spacing-8);
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin: 0 0 var(--spacing-4) 0;
}

.section-icon {
  width: 22px;
  height: 22px;
  color: var(--text-tertiary);
}

.upload-blocked-text {
  color: var(--text-secondary);
  margin: 0;
  font-size: var(--font-size-sm);
}

/* Documents section */
.documents-section {
  margin-bottom: var(--spacing-8);
}

.documents-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

@media (max-width: 640px) {
  .status-content {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }

  .status-row {
    justify-content: center;
  }
}
</style>
