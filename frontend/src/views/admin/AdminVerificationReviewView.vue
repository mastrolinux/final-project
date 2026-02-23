<script setup lang="ts">
/**
 * Admin context verification review page.
 *
 * Displays the context's identity claims alongside linked document
 * previews, enabling administrators to compare document content
 * against claimed fields before approving or rejecting.
 */
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useUiStore } from "@/stores/ui.store";
import { adminVerificationService, getErrorMessage } from "@/services";
import BaseCard from "@/components/common/BaseCard.vue";
import BaseBadge from "@/components/common/BaseBadge.vue";
import BaseButton from "@/components/common/BaseButton.vue";
import {
  CheckCircleIcon,
  XCircleIcon,
  ArrowLeftIcon,
} from "@heroicons/vue/24/outline";
import type {
  AdminContextVerificationDetail,
  AdminVerificationReview,
} from "@/types";

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const uiStore = useUiStore();

const contextId = computed(() => route.params.contextId as string);

const context = ref<AdminContextVerificationDetail | null>(null);
const isLoading = ref(true);
const isSubmitting = ref(false);
const error = ref<string | null>(null);

// Document preview state (keyed by document id)
const previewUrls = ref<Record<string, string>>({});
const previewLoading = ref<Record<string, boolean>>({});
const previewErrors = ref<Record<string, string>>({});

// Review form state
const reviewAction = ref<"verified" | "rejected" | null>(null);
const reviewerNotes = ref("");
const documentExpiryDate = ref("");
const rejectionReason = ref("");
const formError = ref<string | null>(null);

type BadgeVariant =
  | "primary"
  | "success"
  | "warning"
  | "error"
  | "info"
  | "neutral";

const statusVariant = computed<BadgeVariant>(() => {
  if (!context.value) return "neutral";
  const map: Record<string, BadgeVariant> = {
    pending: "warning",
    under_review: "info",
    verified: "success",
    rejected: "error",
  };
  return map[context.value.verification_status] || "neutral";
});

const contextTypeVariant = computed<BadgeVariant>(() => {
  if (!context.value) return "neutral";
  const map: Record<string, BadgeVariant> = {
    legal: "primary",
    healthcare: "error",
  };
  return map[context.value.context_type] || "neutral";
});

const isReviewable = computed(() => {
  if (!context.value) return false;
  return ["pending", "under_review"].includes(
    context.value.verification_status,
  );
});

const canSubmit = computed(() => {
  if (!reviewAction.value) return false;
  if (reviewAction.value === "rejected" && !rejectionReason.value.trim())
    return false;
  return true;
});

const formattedCreatedAt = computed(() => {
  if (!context.value) return "";
  return new Date(context.value.created_at).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
});

// Clear rejection reason when switching to approve
watch(reviewAction, (action) => {
  if (action === "verified") {
    rejectionReason.value = "";
  }
  formError.value = null;
});

async function loadContext(): Promise<void> {
  isLoading.value = true;
  error.value = null;

  try {
    context.value = await adminVerificationService.getContextVerification(
      contextId.value,
    );
    // Pre-fill expiry date from the earliest declared expiry
    const declaredExpiries = context.value.documents
      .map((d) => d.document_expiry_date)
      .filter(Boolean)
      .sort();
    if (declaredExpiries.length > 0) {
      documentExpiryDate.value = declaredExpiries[0] as string;
    }

    // Load previews for each linked document
    for (const doc of context.value.documents) {
      loadPreview(doc.id);
    }
  } catch (err) {
    error.value = getErrorMessage(err);
  } finally {
    isLoading.value = false;
  }
}

async function loadPreview(documentId: string): Promise<void> {
  previewLoading.value[documentId] = true;
  previewErrors.value[documentId] = "";

  try {
    const blob = await adminVerificationService.downloadDocument(documentId);
    previewUrls.value[documentId] = URL.createObjectURL(blob);
  } catch (err) {
    previewErrors.value[documentId] = getErrorMessage(err);
  } finally {
    previewLoading.value[documentId] = false;
  }
}

function isPreviewImage(contentType: string): boolean {
  return contentType?.startsWith("image/") ?? false;
}

function isPreviewPdf(contentType: string): boolean {
  return contentType === "application/pdf";
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

async function handleSubmitReview(): Promise<void> {
  if (!reviewAction.value || !canSubmit.value) return;

  formError.value = null;
  isSubmitting.value = true;

  const review: AdminVerificationReview = {
    verification_status: reviewAction.value,
    reviewer_notes: reviewerNotes.value.trim() || undefined,
    document_expiry_date: documentExpiryDate.value || undefined,
    rejection_reason:
      reviewAction.value === "rejected"
        ? rejectionReason.value.trim()
        : undefined,
  };

  try {
    await adminVerificationService.reviewContext(contextId.value, review);

    if (reviewAction.value === "verified") {
      uiStore.showSuccess(t("verification.admin.reviewSuccess.approved"));
    } else {
      uiStore.showSuccess(t("verification.admin.reviewSuccess.rejected"));
    }

    router.push({ name: "admin-verifications" });
  } catch (err) {
    formError.value = getErrorMessage(err);
  } finally {
    isSubmitting.value = false;
  }
}

function goBack(): void {
  router.push({ name: "admin-verifications" });
}

onMounted(loadContext);

onUnmounted(() => {
  for (const url of Object.values(previewUrls.value)) {
    URL.revokeObjectURL(url);
  }
});
</script>

<template>
  <div class="admin-review-view">
    <div class="container container-md">
      <!-- Back link -->
      <button class="back-link" @click="goBack">
        <ArrowLeftIcon class="back-icon" />
        {{ t("verification.admin.backToQueue") }}
      </button>

      <h1 class="page-title">
        {{ t("verification.admin.reviewTitle") }}
      </h1>

      <!-- Loading -->
      <div v-if="isLoading" class="loading-state">
        <div class="spinner spinner-lg"></div>
        <p class="loading-text">
          {{ t("verification.admin.loadingDocument") }}
        </p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="alert alert-error">
        {{ error }}
      </div>

      <!-- Context details and review form -->
      <template v-else-if="context">
        <!-- Context identity card -->
        <BaseCard class="context-identity-card">
          <template #header>
            <div class="detail-header">
              <span class="detail-header-title">
                {{ t("verification.admin.contextIdentity") }}
              </span>
              <div class="header-badges">
                <BaseBadge :variant="contextTypeVariant" size="sm">
                  {{ context.context_type }}
                </BaseBadge>
                <BaseBadge :variant="statusVariant" size="sm">
                  {{ t(`verification.status.${context.verification_status}`) }}
                </BaseBadge>
              </div>
            </div>
          </template>

          <p class="context-hint">
            {{ t("verification.admin.compareHint") }}
          </p>

          <div class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">
                {{ t("verification.admin.contextName") }}
              </span>
              <span class="detail-value">
                {{ context.context_name }}
              </span>
            </div>
            <div v-if="context.display_name_override" class="detail-item">
              <span class="detail-label">
                {{ t("verification.admin.displayName") }}
              </span>
              <span class="detail-value detail-highlight">
                {{ context.display_name_override }}
              </span>
            </div>
            <div v-if="context.email_override" class="detail-item">
              <span class="detail-label">
                {{ t("verification.admin.emailOverride") }}
              </span>
              <span class="detail-value">
                {{ context.email_override }}
              </span>
            </div>
            <div v-if="context.phone_override" class="detail-item">
              <span class="detail-label">
                {{ t("verification.admin.phoneOverride") }}
              </span>
              <span class="detail-value">
                {{ context.phone_override }}
              </span>
            </div>
            <div class="detail-item">
              <span class="detail-label">
                {{ t("verification.admin.userId") }}
              </span>
              <span class="detail-value detail-mono">
                {{ context.user_id }}
              </span>
            </div>
            <div class="detail-item">
              <span class="detail-label">
                {{ t("verification.admin.submittedOn") }}
              </span>
              <span class="detail-value">
                {{ formattedCreatedAt }}
              </span>
            </div>
          </div>

          <div v-if="context.bio" class="bio-section">
            <span class="detail-label">Bio</span>
            <p class="bio-text">{{ context.bio }}</p>
          </div>
        </BaseCard>

        <!-- Document preview cards -->
        <BaseCard
          v-for="doc in context.documents"
          :key="doc.id"
          class="document-card"
        >
          <template #header>
            <div class="detail-header">
              <span class="detail-header-title">
                {{
                  t(
                    `verification.documentTypes.${doc.document_type === "national_id" ? "nationalId" : doc.document_type}`,
                  )
                }}
                - {{ doc.original_filename }}
              </span>
              <span class="file-size">
                {{ formatFileSize(doc.file_size_bytes) }}
              </span>
            </div>
          </template>

          <div v-if="doc.document_expiry_date" class="declared-expiry">
            <span class="declared-expiry-label">
              {{ t("verification.admin.declaredExpiry") }}
            </span>
            <span class="declared-expiry-value">
              {{
                new Date(doc.document_expiry_date).toLocaleDateString(
                  undefined,
                  { year: "numeric", month: "short", day: "numeric" },
                )
              }}
            </span>
          </div>

          <div v-if="previewLoading[doc.id]" class="preview-loading">
            <div class="spinner spinner-md"></div>
            <p class="loading-text">
              {{ t("verification.admin.loadingPreview") }}
            </p>
          </div>
          <div v-else-if="previewErrors[doc.id]" class="alert alert-error">
            {{ previewErrors[doc.id] }}
          </div>
          <div v-else-if="previewUrls[doc.id]" class="preview-container">
            <img
              v-if="isPreviewImage(doc.content_type)"
              :src="previewUrls[doc.id]"
              :alt="doc.original_filename"
              class="preview-image"
            />
            <iframe
              v-else-if="isPreviewPdf(doc.content_type)"
              :src="previewUrls[doc.id]"
              class="preview-pdf"
              title="Document preview"
            ></iframe>
            <p v-else class="preview-unsupported">
              {{ t("verification.admin.previewUnsupported") }}
            </p>
          </div>
        </BaseCard>

        <!-- Review form (only if reviewable) -->
        <BaseCard v-if="isReviewable" class="review-form-card">
          <template #header>
            <span class="review-form-title">
              {{ t("verification.admin.reviewFormTitle") }}
            </span>
          </template>

          <!-- Action selection -->
          <div class="action-buttons">
            <button
              class="action-btn action-approve"
              :class="{
                'action-selected': reviewAction === 'verified',
              }"
              @click="reviewAction = 'verified'"
            >
              <CheckCircleIcon class="action-icon" />
              {{ t("verification.admin.approve") }}
            </button>
            <button
              class="action-btn action-reject"
              :class="{
                'action-selected': reviewAction === 'rejected',
              }"
              @click="reviewAction = 'rejected'"
            >
              <XCircleIcon class="action-icon" />
              {{ t("verification.admin.reject") }}
            </button>
          </div>

          <!-- Approval fields -->
          <template v-if="reviewAction === 'verified'">
            <div class="form-field">
              <label class="form-label" for="expiry-date">
                {{ t("verification.admin.expiryDate") }}
              </label>
              <input
                id="expiry-date"
                v-model="documentExpiryDate"
                type="date"
                class="form-input"
                :min="new Date().toISOString().split('T')[0]"
              />
              <p class="form-hint">
                {{ t("verification.admin.expiryHint") }}
              </p>
            </div>
          </template>

          <!-- Rejection fields -->
          <template v-if="reviewAction === 'rejected'">
            <div class="form-field">
              <label class="form-label" for="rejection-reason">
                {{ t("verification.admin.rejectionReason") }}
                <span class="required">*</span>
              </label>
              <textarea
                id="rejection-reason"
                v-model="rejectionReason"
                class="form-textarea"
                :placeholder="
                  t('verification.admin.rejectionReasonPlaceholder')
                "
                rows="3"
                maxlength="500"
              ></textarea>
              <p class="form-hint">{{ rejectionReason.length }}/500</p>
            </div>
          </template>

          <!-- Reviewer notes (both actions) -->
          <div v-if="reviewAction" class="form-field">
            <label class="form-label" for="reviewer-notes">
              {{ t("verification.admin.reviewerNotes") }}
            </label>
            <textarea
              id="reviewer-notes"
              v-model="reviewerNotes"
              class="form-textarea"
              :placeholder="t('verification.admin.reviewerNotesPlaceholder')"
              rows="2"
              maxlength="1000"
            ></textarea>
            <p class="form-hint">{{ reviewerNotes.length }}/1000</p>
          </div>

          <!-- Form error -->
          <div v-if="formError" class="alert alert-error form-alert">
            {{ formError }}
          </div>

          <!-- Submit -->
          <div v-if="reviewAction" class="form-actions">
            <BaseButton
              variant="secondary"
              :disabled="isSubmitting"
              @click="reviewAction = null"
            >
              {{ t("common.cancel") }}
            </BaseButton>
            <BaseButton
              :variant="reviewAction === 'verified' ? 'primary' : 'danger'"
              :disabled="!canSubmit"
              :loading="isSubmitting"
              @click="handleSubmitReview"
            >
              {{
                reviewAction === "verified"
                  ? t("verification.admin.confirmApprove")
                  : t("verification.admin.confirmReject")
              }}
            </BaseButton>
          </div>
        </BaseCard>

        <!-- Already reviewed notice -->
        <BaseCard v-else class="already-reviewed">
          <p class="already-reviewed-text">
            {{
              t("verification.admin.alreadyReviewed", {
                status: t(`verification.status.${context.verification_status}`),
              })
            }}
          </p>
        </BaseCard>
      </template>
    </div>
  </div>
</template>

<style scoped>
.admin-review-view {
  padding: var(--spacing-8) 0;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-2);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  margin-bottom: var(--spacing-4);
  font-family: inherit;
  transition: color var(--transition-fast);
}

.back-link:hover {
  color: var(--text-primary);
}

.back-icon {
  width: 16px;
  height: 16px;
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
  margin: 0 0 var(--spacing-6) 0;
}

/* Loading / Error */
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

/* Context identity card */
.context-identity-card {
  margin-bottom: var(--spacing-6);
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-badges {
  display: flex;
  gap: var(--spacing-2);
}

.detail-header-title {
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.context-hint {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin: 0 0 var(--spacing-4) 0;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: var(--spacing-4);
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.detail-label {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.detail-value {
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  word-break: break-all;
}

.detail-highlight {
  font-weight: var(--font-weight-semibold);
}

.detail-mono {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-xs);
}

.bio-section {
  margin-top: var(--spacing-4);
  padding-top: var(--spacing-4);
  border-top: 1px solid var(--border-primary);
}

.bio-text {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  line-height: 1.5;
  margin: var(--spacing-1) 0 0 0;
}

/* Document cards */
.document-card {
  margin-bottom: var(--spacing-6);
}

.file-size {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.declared-expiry {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-3) var(--spacing-5);
  border-bottom: 1px solid var(--border-primary);
  background-color: var(--bg-secondary);
  font-size: var(--font-size-sm);
}

.declared-expiry-label {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.declared-expiry-value {
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

/* Document preview */
.preview-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--spacing-8) 0;
}

.preview-container {
  display: flex;
  justify-content: center;
}

.preview-image {
  max-width: 100%;
  max-height: 600px;
  border-radius: var(--radius-md);
  object-fit: contain;
}

.preview-pdf {
  width: 100%;
  height: 600px;
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
}

.preview-unsupported {
  text-align: center;
  color: var(--text-tertiary);
  padding: var(--spacing-8) 0;
}

/* Review form */
.review-form-card {
  margin-bottom: var(--spacing-6);
}

.review-form-title {
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

/* Action buttons */
.action-buttons {
  display: flex;
  gap: var(--spacing-3);
  margin-bottom: var(--spacing-5);
}

.action-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3) var(--spacing-4);
  border: 2px solid var(--border-primary);
  border-radius: var(--radius-lg);
  background-color: var(--bg-primary);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  font-family: inherit;
  cursor: pointer;
  transition:
    border-color var(--transition-fast),
    background-color var(--transition-fast),
    color var(--transition-fast);
}

.action-btn:hover {
  border-color: var(--color-gray-400);
}

.action-icon {
  width: 20px;
  height: 20px;
}

.action-approve.action-selected {
  border-color: var(--color-success-500);
  background-color: var(--color-success-50);
  color: var(--color-success-700);
}

:global(.dark) .action-approve.action-selected {
  background-color: rgba(34, 197, 94, 0.08);
}

.action-reject.action-selected {
  border-color: var(--color-error-500);
  background-color: var(--color-error-50);
  color: var(--color-error-700);
}

:global(.dark) .action-reject.action-selected {
  background-color: rgba(239, 68, 68, 0.08);
}

/* Form fields */
.form-field {
  margin-bottom: var(--spacing-4);
}

.form-label {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  margin-bottom: var(--spacing-2);
}

.required {
  color: var(--color-error-600);
}

.form-input {
  display: block;
  width: 100%;
  padding: var(--spacing-2) var(--spacing-3);
  border: 1px solid var(--input-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  background-color: var(--input-bg);
  color: var(--text-primary);
  font-family: inherit;
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: var(--color-primary-500);
  box-shadow: 0 0 0 2px var(--color-primary-100);
}

.form-textarea {
  display: block;
  width: 100%;
  padding: var(--spacing-2) var(--spacing-3);
  border: 1px solid var(--input-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  background-color: var(--input-bg);
  color: var(--text-primary);
  font-family: inherit;
  resize: vertical;
  box-sizing: border-box;
  line-height: 1.5;
}

.form-textarea:focus {
  outline: none;
  border-color: var(--color-primary-500);
  box-shadow: 0 0 0 2px var(--color-primary-100);
}

.form-hint {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  margin: var(--spacing-1) 0 0 0;
}

.form-alert {
  margin-bottom: var(--spacing-4);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-3);
  padding-top: var(--spacing-4);
  border-top: 1px solid var(--border-primary);
}

/* Already reviewed */
.already-reviewed-text {
  color: var(--text-secondary);
  margin: 0;
}

@media (max-width: 640px) {
  .action-buttons {
    flex-direction: column;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
