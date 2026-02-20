<script setup lang="ts">
import { computed } from "vue";
import type { SoftDeletedUser } from "@/types";
import BaseCard from "@/components/common/BaseCard.vue";
import BaseBadge from "@/components/common/BaseBadge.vue";

const RETENTION_DAYS = 30;

const props = defineProps<{
  user: SoftDeletedUser;
}>();

const deletedDate = computed(() => {
  return new Date(props.user.deleted_at).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
});

const daysRemaining = computed(() => {
  const deletedAt = new Date(props.user.deleted_at);
  const purgeDate = new Date(
    deletedAt.getTime() + RETENTION_DAYS * 24 * 60 * 60 * 1000,
  );
  const now = new Date();
  const diffMs = purgeDate.getTime() - now.getTime();
  return Math.max(0, Math.ceil(diffMs / (24 * 60 * 60 * 1000)));
});

const isExpired = computed(() => daysRemaining.value <= 0);

const urgencyVariant = computed<"error" | "warning" | "neutral">(() => {
  if (isExpired.value || daysRemaining.value <= 5) return "error";
  if (daysRemaining.value <= 15) return "warning";
  return "neutral";
});

const truncatedId = computed(() => {
  const id = props.user.user_id;
  if (id.length > 13) {
    return id.substring(0, 8) + "...";
  }
  return id;
});
</script>

<template>
  <BaseCard>
    <div class="user-card">
      <div class="user-header">
        <div class="user-info">
          <h3 class="user-email">{{ user.email }}</h3>
          <code class="user-id" :title="user.user_id">{{ truncatedId }}</code>
        </div>
        <div class="user-badges">
          <BaseBadge
            :variant="user.is_email_verified ? 'success' : 'warning'"
            size="sm"
          >
            {{ user.is_email_verified ? "Verified" : "Unverified" }}
          </BaseBadge>
          <BaseBadge v-if="user.is_admin" variant="info" size="sm">
            Admin
          </BaseBadge>
          <BaseBadge :variant="urgencyVariant" size="sm">
            {{ isExpired ? "Expired" : daysRemaining + "d remaining" }}
          </BaseBadge>
        </div>
      </div>

      <div class="user-meta">
        <div class="meta-item">
          <span class="meta-label">Deleted:</span>
          <span class="meta-value">{{ deletedDate }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Status:</span>
          <span class="meta-value" :class="{ 'text-expired': isExpired }">
            {{ isExpired ? "Eligible for purge" : "Grace period active" }}
          </span>
        </div>
      </div>
    </div>
  </BaseCard>
</template>

<style scoped>
.user-card {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.user-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-4);
  flex-wrap: wrap;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.user-email {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin: 0;
}

.user-id {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  background-color: var(--bg-tertiary);
  padding: var(--spacing-1) var(--spacing-2);
  border-radius: var(--radius-sm);
}

.user-badges {
  display: flex;
  gap: var(--spacing-2);
  flex-wrap: wrap;
}

.user-meta {
  display: flex;
  gap: var(--spacing-6);
  flex-wrap: wrap;
  padding-top: var(--spacing-2);
  border-top: 1px solid var(--border-primary);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.meta-label {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
}

.meta-value {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

.text-expired {
  color: var(--color-error-600);
}
</style>
