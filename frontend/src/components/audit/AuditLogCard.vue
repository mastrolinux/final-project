<script setup lang="ts">
import { computed } from "vue";
import type { AuditLogEntry } from "@/types";
import BaseCard from "@/components/common/BaseCard.vue";
import BaseBadge from "@/components/common/BaseBadge.vue";

const props = defineProps<{
  entry: AuditLogEntry;
}>();

/**
 * Maps audit operations to badge color variants.
 */
const operationVariant = computed(() => {
  const map: Record<
    string,
    "success" | "warning" | "error" | "info" | "neutral" | "primary"
  > = {
    create: "success",
    register: "success",
    grant: "success",
    login: "info",
    verify: "info",
    update: "primary",
    logout: "neutral",
    delete: "error",
    withdraw: "warning",
    revoke: "warning",
  };
  return map[props.entry.operation] || "neutral";
});

/**
 * Extracts the event category from the dot-delimited event type
 * (e.g., "auth.login.success" -> "auth").
 */
const eventCategory = computed(() => {
  return props.entry.event_type.split(".")[0];
});

/**
 * Maps event categories to badge variants for visual grouping.
 */
const categoryVariant = computed(() => {
  const map: Record<string, "primary" | "info" | "warning" | "neutral"> = {
    auth: "primary",
    profile: "info",
    context: "info",
    consent: "warning",
    oauth: "neutral",
  };
  return map[eventCategory.value] || "neutral";
});

/**
 * Formats an ISO timestamp into a locale-appropriate date and time string.
 */
function formatTimestamp(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/**
 * Formats an event type string for display, replacing dots with arrows
 * (e.g., "auth.login.success" -> "auth > login > success").
 */
function formatEventType(eventType: string): string {
  return eventType.replace(/\./g, " > ");
}

/**
 * Returns true if the changes object contains any entries worth displaying.
 */
const hasChanges = computed(() => {
  return (
    props.entry.changes !== null && Object.keys(props.entry.changes).length > 0
  );
});
</script>

<template>
  <BaseCard>
    <div class="audit-card">
      <div class="audit-header">
        <div class="audit-event">
          <span class="event-type">{{
            formatEventType(entry.event_type)
          }}</span>
          <span class="event-time">{{
            formatTimestamp(entry.created_at)
          }}</span>
        </div>
        <div class="audit-badges">
          <BaseBadge :variant="categoryVariant" size="sm">
            {{ eventCategory }}
          </BaseBadge>
          <BaseBadge :variant="operationVariant" size="sm">
            {{ entry.operation }}
          </BaseBadge>
        </div>
      </div>

      <div class="audit-meta">
        <div class="meta-item">
          <span class="meta-label">Resource:</span>
          <span class="meta-value">
            {{ entry.resource_type }}
            <code class="resource-id"
              >{{ entry.resource_id.substring(0, 8) }}...</code
            >
          </span>
        </div>
        <div v-if="entry.ip_address" class="meta-item">
          <span class="meta-label">IP:</span>
          <span class="meta-value">{{ entry.ip_address }}</span>
        </div>
        <div v-if="entry.legal_basis" class="meta-item">
          <span class="meta-label">Legal basis:</span>
          <span class="meta-value">{{ entry.legal_basis }}</span>
        </div>
        <div
          v-if="entry.actor_id && entry.actor_id !== entry.user_id"
          class="meta-item"
        >
          <span class="meta-label">Actor:</span>
          <span class="meta-value">
            <code class="resource-id"
              >{{ entry.actor_id.substring(0, 8) }}...</code
            >
          </span>
        </div>
      </div>

      <div v-if="hasChanges" class="audit-changes">
        <details>
          <summary class="changes-toggle">View changes</summary>
          <pre class="changes-content">{{
            JSON.stringify(entry.changes, null, 2)
          }}</pre>
        </details>
      </div>
    </div>
  </BaseCard>
</template>

<style scoped>
.audit-card {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.audit-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-4);
  flex-wrap: wrap;
}

.audit-event {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.event-type {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.event-time {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.audit-badges {
  display: flex;
  gap: var(--spacing-2);
  flex-wrap: wrap;
}

.audit-meta {
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
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
}

.resource-id {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  background-color: var(--bg-tertiary);
  padding: 1px var(--spacing-1);
  border-radius: var(--radius-sm);
}

.audit-changes {
  padding-top: var(--spacing-2);
}

.changes-toggle {
  font-size: var(--font-size-sm);
  color: var(--color-primary-600);
  cursor: pointer;
  user-select: none;
}

.changes-toggle:hover {
  color: var(--color-primary-700);
}

.changes-content {
  margin-top: var(--spacing-2);
  padding: var(--spacing-3);
  background-color: var(--bg-tertiary);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  font-family: var(--font-family-mono);
  color: var(--text-secondary);
  overflow-x: auto;
  max-height: 200px;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
