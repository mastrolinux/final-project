<script setup lang="ts">
import { computed } from "vue";
import type { OAuthClientResponse } from "@/types";
import BaseCard from "@/components/common/BaseCard.vue";
import BaseBadge from "@/components/common/BaseBadge.vue";
import BaseButton from "@/components/common/BaseButton.vue";
import { PencilIcon, TrashIcon } from "@heroicons/vue/24/outline";

const props = defineProps<{
  client: OAuthClientResponse;
}>();

const emit = defineEmits<{
  edit: [clientId: string];
  delete: [clientId: string];
}>();

const clientType = computed(() => {
  return props.client.is_confidential ? "Confidential" : "Public";
});

const statusVariant = computed(() => {
  return props.client.is_active ? "success" : "error";
});

const statusLabel = computed(() => {
  return props.client.is_active ? "Active" : "Inactive";
});

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}
</script>

<template>
  <BaseCard>
    <div class="client-card">
      <div class="client-header">
        <div class="client-info">
          <h3 class="client-name">{{ client.client_name }}</h3>
          <code class="client-id">{{ client.client_id }}</code>
        </div>
        <div class="client-badges">
          <BaseBadge :variant="statusVariant" size="sm">
            {{ statusLabel }}
          </BaseBadge>
          <BaseBadge variant="neutral" size="sm">
            {{ clientType }}
          </BaseBadge>
          <BaseBadge v-if="client.is_first_party" variant="info" size="sm">
            First Party
          </BaseBadge>
        </div>
      </div>

      <p v-if="client.client_description" class="client-description">
        {{ client.client_description }}
      </p>

      <div class="client-meta">
        <div class="meta-item">
          <span class="meta-label">Redirect URIs:</span>
          <span class="meta-value">{{ client.redirect_uris.length }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Scopes:</span>
          <span class="meta-value">{{ client.allowed_scopes.length }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Created:</span>
          <span class="meta-value">{{ formatDate(client.created_at) }}</span>
        </div>
      </div>

      <div class="client-actions">
        <BaseButton
          variant="secondary"
          size="sm"
          @click="emit('edit', client.client_id)"
        >
          <PencilIcon class="icon" />
          Edit
        </BaseButton>
        <BaseButton
          variant="danger"
          size="sm"
          @click="emit('delete', client.client_id)"
        >
          <TrashIcon class="icon" />
          Delete
        </BaseButton>
      </div>
    </div>
  </BaseCard>
</template>

<style scoped>
.client-card {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.client-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-4);
  flex-wrap: wrap;
}

.client-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.client-name {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin: 0;
}

.client-id {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  background-color: var(--bg-tertiary);
  padding: var(--spacing-1) var(--spacing-2);
  border-radius: var(--radius-sm);
}

.client-badges {
  display: flex;
  gap: var(--spacing-2);
  flex-wrap: wrap;
}

.client-description {
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  margin: 0;
}

.client-meta {
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

.client-actions {
  display: flex;
  gap: var(--spacing-2);
  padding-top: var(--spacing-2);
}

.icon {
  width: 16px;
  height: 16px;
  margin-right: var(--spacing-1);
}
</style>
