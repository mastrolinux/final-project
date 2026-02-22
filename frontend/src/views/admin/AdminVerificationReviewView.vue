<script setup lang="ts">
/**
 * Admin document review page.
 *
 * Displays full document details and provides a form for administrators
 * to approve (with optional expiry date) or reject (with required reason)
 * a verification submission.
 */
import { ref, computed, onMounted, watch } from "vue";
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
  VerificationDocumentResponse,
  AdminVerificationReview,
} from "@/types";

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const uiStore = useUiStore();

const documentId = computed(() => route.params.documentId as string);

const document = ref<VerificationDocumentResponse | null>(null);
const isLoading = ref(true);
const isSubmitting = ref(false);
const error = ref<string | null>(null);

// Review form state
const reviewAction = ref<"verified" | "rejected" | null>(null);
const reviewerNotes = ref("");
const documentExpiryDate = ref("");
const rejectionReason = ref("");
const formError = ref<string | null>(null);

type BadgeVariant = "primary" | "success" | "warning" | "error" | "info" | "neutral";

const statusVariant = computed<BadgeVariant>(() => {
  if (!document.value) return "neutral";
  const map: Record<string, BadgeVariant> = {
    pending: "warning",
    under_review: "info",
    verified: "success",
    rejected: "error",
  };
  return map[document.value.verification_status] || "neutral";
});

const isReviewable = computed(() => {
  if (!document.value) return false;
  return ["pending", "under_review"].includes(
    document.value.verification_status,
  );
});

const canSubmit = computed(() => {
  if (!reviewAction.value) return false;
  if (reviewAction.value === "rejected" && !rejectionReason.value.trim())
    return false;
  return true;
});

const fileSizeFormatted = computed(() => {
  if (!document.value) return "";
  const bytes = document.value.file_size_bytes;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
});

const formattedCreatedAt = computed(() => {
  if (!document.value) return "";
  return new Date(document.value.created_at).toLocaleDateString(undefined, {
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

async function loadDocument(): Promise<void> {
  isLoading.value = true;
  error.value = null;

  try {
    document.value = await adminVerificationService.getDocument(
      documentId.value,
    );
  } catch (err) {
    error.value = getErrorMessage(err);
  } finally {
    isLoading.value = false;
  }
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
    await adminVerificationService.reviewDocument(documentId.value, review);

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

onMounted(loadDocument);
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

      <!-- Document details and review form -->
      <template v-else-if="document">
        <!-- Document info card -->
        <BaseCard class="document-detail-card">
          <template #header>
            <div class="detail-header">
              <span class="detail-header-title">
                {{ t("verification.admin.documentDetails") }}
              </span>
              <BaseBadge :variant="statusVariant" size="sm">
                {{ t(`verification.status.${document.verification_status}`) }}
              </BaseBadge>
            </div>
          </template>

          <div class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">
                {{ t("verification.admin.userId") }}
              </span>
              <span class="detail-value detail-mono">
                {{ document.user_id }}
              </span>
            </div>
            <div class="detail-item">
              <span class="detail-label">
                {{ t("verification.upload.documentType") }}
              </span>
              <span class="detail-value">
                {{
                  t(
                    `verification.documentTypes.${document.document_type === "national_id" ? "nationalId" : document.document_type}`,
                  )
                }}
              </span>
            </div>
            <div class="detail-item">
              <span class="detail-label">
                {{ t("verification.document.filename") }}
              </span>
              <span class="detail-value">
                {{ document.original_filename }}
              </span>
            </div>
            <div class="detail-item">
              <span class="detail-label">
                {{ t("verification.document.fileSize") }}
              </span>
              <span class="detail-value">
                {{ fileSizeFormatted }}
              </span>
            </div>
            <div class="detail-item">
              <span class="detail-label">
                {{ t("verification.document.format") }}
              </span>
              <span class="detail-value">
                {{ document.content_type }}
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
                status: t(
                  `verification.status.${document.verification_status}`,
                ),
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

/* Document detail card */
.document-detail-card {
  margin-bottom: var(--spacing-6);
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.detail-header-title {
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
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

.detail-mono {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-xs);
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
