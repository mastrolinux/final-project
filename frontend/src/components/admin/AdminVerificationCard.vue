<script setup lang="ts">
/**
 * Admin card for a pending verification document in the review queue.
 *
 * Displays user info, document metadata, and a link to the review page.
 */
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import BaseCard from "@/components/common/BaseCard.vue";
import BaseBadge from "@/components/common/BaseBadge.vue";
import BaseButton from "@/components/common/BaseButton.vue";
import type { AdminVerificationListItem } from "@/types";

const props = defineProps<{
  document: AdminVerificationListItem;
}>();

const emit = defineEmits<{
  (e: "review", documentId: string): void;
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
    hour: "2-digit",
    minute: "2-digit",
  });
});

const fileSizeFormatted = computed(() => {
  const bytes = props.document.file_size_bytes;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
});

const truncatedUserId = computed(() => {
  return props.document.user_id.substring(0, 8) + "...";
});
</script>

<template>
  <BaseCard class="admin-verification-card">
    <div class="card-content">
      <div class="card-main">
        <div class="card-top-row">
          <div class="user-info">
            <span class="user-name">
              {{
                document.user_display_name ||
                t("verification.admin.unknownUser")
              }}
            </span>
            <span class="user-id" :title="document.user_id">
              {{ truncatedUserId }}
            </span>
          </div>
          <BaseBadge :variant="statusVariant" size="sm">
            {{ t(`verification.status.${document.verification_status}`) }}
          </BaseBadge>
        </div>

        <div class="card-meta">
          <span class="meta-item">
            {{
              t(
                `verification.documentTypes.${document.document_type === "national_id" ? "nationalId" : document.document_type}`,
              )
            }}
          </span>
          <span class="meta-separator">|</span>
          <span class="meta-item">
            {{ document.original_filename }}
          </span>
          <span class="meta-separator">|</span>
          <span class="meta-item">{{ fileSizeFormatted }}</span>
        </div>

        <span class="card-date">
          {{ t("verification.admin.submittedOn") }}
          {{ formattedDate }}
        </span>
      </div>

      <div class="card-action">
        <BaseButton
          variant="primary"
          size="sm"
          @click="emit('review', document.id)"
        >
          {{ t("verification.admin.review") }}
        </BaseButton>
      </div>
    </div>
  </BaseCard>
</template>

<style scoped>
.admin-verification-card :deep(.card-body) {
  padding: var(--spacing-4) var(--spacing-5);
}

.card-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-4);
}

.card-main {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
  min-width: 0;
}

.card-top-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.user-info {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-2);
  min-width: 0;
}

.user-name {
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-id {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  font-family: var(--font-family-mono);
}

.card-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  flex-wrap: wrap;
}

.meta-separator {
  color: var(--border-primary);
}

.card-date {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.card-action {
  flex-shrink: 0;
}

@media (max-width: 640px) {
  .card-content {
    flex-direction: column;
    align-items: stretch;
  }

  .card-action {
    align-self: flex-end;
  }
}
</style>
