<script setup lang="ts">
/**
 * Admin card for a pending context verification in the review queue.
 *
 * Displays user info, context metadata, document count, and a link
 * to the context review page.
 */
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import BaseCard from "@/components/common/BaseCard.vue";
import BaseBadge from "@/components/common/BaseBadge.vue";
import BaseButton from "@/components/common/BaseButton.vue";
import type { AdminContextVerificationItem } from "@/types";

const props = defineProps<{
  context: AdminContextVerificationItem;
}>();

const emit = defineEmits<{
  (e: "review", contextId: string): void;
}>();

const { t } = useI18n();

type BadgeVariant =
  | "primary"
  | "success"
  | "warning"
  | "error"
  | "info"
  | "neutral";

const statusVariant = computed<BadgeVariant>(() => {
  const map: Record<string, BadgeVariant> = {
    pending: "warning",
    under_review: "info",
    verified: "success",
    rejected: "error",
  };
  return map[props.context.verification_status] || "neutral";
});

const contextTypeVariant = computed<BadgeVariant>(() => {
  const map: Record<string, BadgeVariant> = {
    legal: "primary",
    healthcare: "error",
  };
  return map[props.context.context_type] || "neutral";
});

const formattedDate = computed(() => {
  return new Date(props.context.created_at).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
});

const truncatedUserId = computed(() => {
  return props.context.user_id.substring(0, 8) + "...";
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
                context.user_display_name || t("verification.admin.unknownUser")
              }}
            </span>
            <span class="user-id" :title="context.user_id">
              {{ truncatedUserId }}
            </span>
          </div>
          <BaseBadge :variant="statusVariant" size="sm">
            {{ t(`verification.status.${context.verification_status}`) }}
          </BaseBadge>
        </div>

        <div class="card-meta">
          <BaseBadge :variant="contextTypeVariant" size="sm">
            {{ context.context_type }}
          </BaseBadge>
          <span class="meta-item">
            {{ context.context_name }}
          </span>
          <template v-if="context.display_name_override">
            <span class="meta-separator">|</span>
            <span class="meta-item">
              {{ context.display_name_override }}
            </span>
          </template>
          <span class="meta-separator">|</span>
          <span class="meta-item">
            {{
              t("verification.admin.documentCount", {
                count: context.document_count,
              })
            }}
          </span>
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
          @click="emit('review', context.context_id)"
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
