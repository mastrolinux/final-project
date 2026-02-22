<script setup lang="ts">
/**
 * Displays a single verification document with its status, metadata,
 * and optional rejection reason or expiry date.
 */
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import BaseCard from "@/components/common/BaseCard.vue";
import BaseBadge from "@/components/common/BaseBadge.vue";
import type { VerificationDocumentResponse } from "@/types";

const props = defineProps<{
  document: VerificationDocumentResponse;
}>();

const { t } = useI18n();

type BadgeVariant = "primary" | "success" | "warning" | "error" | "info" | "neutral";

const statusVariant = computed<BadgeVariant>(() => {
  const map: Record<string, BadgeVariant> = {
    pending: "warning",
    under_review: "info",
    verified: "success",
    rejected: "error",
  };
  return map[props.document.verification_status] || "neutral";
});

const formattedDate = computed(() => {
  return new Date(props.document.created_at).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
});

const formattedExpiry = computed(() => {
  if (!props.document.document_expiry_date) return null;
  return new Date(props.document.document_expiry_date).toLocaleDateString(
    undefined,
    {
      year: "numeric",
      month: "short",
      day: "numeric",
    },
  );
});

const formattedReviewedAt = computed(() => {
  if (!props.document.reviewed_at) return null;
  return new Date(props.document.reviewed_at).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
});

const fileSizeFormatted = computed(() => {
  const bytes = props.document.file_size_bytes;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
});

const isExpiringSoon = computed(() => {
  if (!props.document.document_expiry_date) return false;
  const expiry = new Date(props.document.document_expiry_date);
  const now = new Date();
  const daysUntilExpiry = Math.ceil(
    (expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24),
  );
  return daysUntilExpiry <= 30 && daysUntilExpiry > 0;
});

const isExpired = computed(() => {
  if (!props.document.document_expiry_date) return false;
  return new Date(props.document.document_expiry_date) < new Date();
});
</script>

<template>
  <BaseCard class="document-card">
    <div class="document-header">
      <div class="document-type-info">
        <span class="document-type">
          {{
            t(
              `verification.documentTypes.${document.document_type === "national_id" ? "nationalId" : document.document_type}`,
            )
          }}
        </span>
        <BaseBadge :variant="statusVariant" size="sm">
          {{ t(`verification.status.${document.verification_status}`) }}
        </BaseBadge>
      </div>
      <span class="document-date">{{ formattedDate }}</span>
    </div>

    <div class="document-details">
      <div class="detail-row">
        <span class="detail-label">
          {{ t("verification.document.filename") }}
        </span>
        <span class="detail-value detail-filename">
          {{ document.original_filename }}
        </span>
      </div>
      <div class="detail-row">
        <span class="detail-label">
          {{ t("verification.document.fileSize") }}
        </span>
        <span class="detail-value">{{ fileSizeFormatted }}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">
          {{ t("verification.document.format") }}
        </span>
        <span class="detail-value">{{ document.content_type }}</span>
      </div>
    </div>

    <!-- Expiry date -->
    <div
      v-if="formattedExpiry"
      class="document-expiry"
      :class="{
        'expiry-warning': isExpiringSoon,
        'expiry-expired': isExpired,
      }"
    >
      <span class="expiry-label">
        {{ t("verification.document.expiryDate") }}
      </span>
      <span class="expiry-value">
        {{ formattedExpiry }}
        <template v-if="isExpired">
          ({{ t("verification.document.expired") }})
        </template>
        <template v-else-if="isExpiringSoon">
          ({{ t("verification.document.expiringSoon") }})
        </template>
      </span>
    </div>

    <!-- Review info -->
    <div v-if="document.reviewed_at" class="review-info">
      <span class="review-date">
        {{
          t("verification.document.reviewedOn", { date: formattedReviewedAt })
        }}
      </span>
      <p v-if="document.reviewer_notes" class="review-notes">
        {{ document.reviewer_notes }}
      </p>
    </div>

    <!-- Rejection reason -->
    <div v-if="document.rejection_reason" class="rejection-reason">
      <span class="rejection-label">
        {{ t("verification.document.rejectionReason") }}
      </span>
      <p class="rejection-text">{{ document.rejection_reason }}</p>
    </div>
  </BaseCard>
</template>

<style scoped>
.document-card {
  padding: 0;
}

.document-card :deep(.card-body) {
  padding: 0;
}

.document-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-4) var(--spacing-5);
  border-bottom: 1px solid var(--border-primary);
}

.document-type-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.document-type {
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.document-date {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
}

.document-details {
  padding: var(--spacing-4) var(--spacing-5);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.detail-row {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-3);
}

.detail-label {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  flex-shrink: 0;
  min-width: 80px;
}

.detail-value {
  font-size: var(--font-size-sm);
  color: var(--text-primary);
}

.detail-filename {
  word-break: break-all;
}

.document-expiry {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-3) var(--spacing-5);
  border-top: 1px solid var(--border-primary);
  font-size: var(--font-size-sm);
}

.expiry-label {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.expiry-value {
  color: var(--text-primary);
}

.expiry-warning .expiry-value {
  color: var(--color-warning-700);
  font-weight: var(--font-weight-medium);
}

.expiry-expired .expiry-value {
  color: var(--color-error-700);
  font-weight: var(--font-weight-medium);
}

.review-info {
  padding: var(--spacing-3) var(--spacing-5);
  border-top: 1px solid var(--border-primary);
  background-color: var(--bg-secondary);
}

.review-date {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.review-notes {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin: var(--spacing-1) 0 0 0;
  line-height: 1.5;
}

.rejection-reason {
  padding: var(--spacing-3) var(--spacing-5);
  border-top: 1px solid var(--color-error-200);
  background-color: var(--color-error-50);
}

:global(.dark) .rejection-reason {
  background-color: rgba(239, 68, 68, 0.08);
  border-top-color: rgba(239, 68, 68, 0.2);
}

.rejection-label {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  color: var(--color-error-700);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.rejection-text {
  font-size: var(--font-size-sm);
  color: var(--color-error-800);
  margin: var(--spacing-1) 0 0 0;
  line-height: 1.5;
}

:global(.dark) .rejection-label {
  color: var(--color-error-400);
}

:global(.dark) .rejection-text {
  color: var(--color-error-300);
}
</style>
