<script setup lang="ts">
defineProps<{
  title: string;
  description?: string;
}>();
</script>

<template>
  <div class="empty-state">
    <div v-if="$slots.icon" class="empty-state-icon">
      <slot name="icon" />
    </div>

    <h3 class="empty-state-title">{{ title }}</h3>

    <p v-if="description" class="empty-state-description">
      {{ description }}
    </p>

    <div v-if="$slots.action" class="empty-state-action">
      <slot name="action" />
    </div>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: var(--spacing-8) var(--spacing-4);
}

.empty-state-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  margin-bottom: var(--spacing-4);
  border-radius: var(--radius-full);
  background-color: var(--color-gray-100);
  color: var(--color-gray-400);
}

:global(.dark) .empty-state-icon {
  background-color: var(--color-gray-800);
  color: var(--color-gray-500);
}

.empty-state-icon :deep(svg) {
  width: 32px;
  height: 32px;
}

.empty-state-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin-bottom: var(--spacing-2);
}

.empty-state-description {
  font-size: var(--font-size-base);
  color: var(--text-secondary);
  max-width: 28rem;
  margin-bottom: var(--spacing-6);
}

.empty-state-action {
  display: flex;
  gap: var(--spacing-3);
}
</style>
