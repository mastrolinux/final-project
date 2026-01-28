<script setup lang="ts">
defineProps<{
  noPadding?: boolean
}>()
</script>

<template>
  <div class="card">
    <div v-if="$slots.header" class="card-header">
      <slot name="header" />
    </div>
    
    <div class="card-body" :class="{ 'p-0': noPadding }">
      <slot />
    </div>

    <div v-if="$slots.footer" class="card-footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<style scoped>
.card {
  background-color: var(--bg-primary);
  border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  overflow: hidden;
  transition: box-shadow var(--transition-normal);
}

:global(.dark) .card {
  border-color: var(--color-gray-700);
}

.card-header {
  padding: var(--spacing-4) var(--spacing-6);
  border-bottom: 1px solid var(--border-primary);
  background-color: var(--bg-secondary);
  font-weight: var(--font-weight-medium);
}

.card-body {
  padding: var(--spacing-6);
}

.card-body.p-0 {
  padding: 0;
}

.card-footer {
  padding: var(--spacing-4) var(--spacing-6);
  border-top: 1px solid var(--border-primary);
  background-color: var(--bg-secondary);
}
</style>
