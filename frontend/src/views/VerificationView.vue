<script setup lang="ts">
/**
 * Documents page.
 *
 * Lists all identity documents uploaded by the current user, with
 * expiry date tracking and verification status. Provides standalone
 * upload functionality (documents can later be linked to contexts).
 */
import { ref, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { useAuthStore } from "@/stores/auth.store";
import { useUiStore } from "@/stores/ui.store";
import { verificationService, getErrorMessage } from "@/services";
import BaseCard from "@/components/common/BaseCard.vue";
import DocumentUpload from "@/components/verification/DocumentUpload.vue";
import VerificationDocumentCard from "@/components/verification/VerificationDocumentCard.vue";
import { DocumentPlusIcon } from "@heroicons/vue/24/outline";
import type { VerificationDocumentResponse, DocumentType } from "@/types";

const { t } = useI18n();
const authStore = useAuthStore();
const uiStore = useUiStore();

const isLoading = ref(true);
const isUploading = ref(false);
const error = ref<string | null>(null);
const documents = ref<VerificationDocumentResponse[]>([]);

async function loadData(): Promise<void> {
  if (!authStore.userId) return;
  isLoading.value = true;
  error.value = null;

  try {
    documents.value = await verificationService.listDocuments(authStore.userId);
  } catch (err) {
    error.value = getErrorMessage(err);
  } finally {
    isLoading.value = false;
  }
}

async function handleUpload(payload: {
  file: File;
  documentType: DocumentType;
  expiryDate: string;
}): Promise<void> {
  if (!authStore.userId) return;
  isUploading.value = true;

  try {
    await verificationService.uploadDocument(
      authStore.userId,
      payload.file,
      payload.documentType,
      payload.expiryDate,
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
  <div class="documents-view">
    <div class="container container-md">
      <div class="page-header">
        <h1 class="page-title">
          {{ t("documents.title") }}
        </h1>
        <p class="page-description">
          {{ t("documents.description") }}
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
        <!-- Upload section -->
        <section class="upload-section">
          <h2 class="section-title">
            <DocumentPlusIcon class="section-icon" />
            {{ t("verification.upload.title") }}
          </h2>
          <DocumentUpload :is-uploading="isUploading" @upload="handleUpload" />
        </section>

        <!-- Document list -->
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

        <!-- Empty state -->
        <BaseCard v-else class="empty-state">
          <p class="empty-text">
            {{ t("documents.empty") }}
          </p>
        </BaseCard>
      </template>
    </div>
  </div>
</template>

<style scoped>
.documents-view {
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

/* Documents section */
.documents-section {
  margin-bottom: var(--spacing-8);
}

.documents-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

/* Empty state */
.empty-state {
  text-align: center;
}

.empty-text {
  color: var(--text-secondary);
  margin: 0;
  font-size: var(--font-size-sm);
}
</style>
