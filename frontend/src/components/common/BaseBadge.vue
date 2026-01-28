<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    variant?: 'primary' | 'success' | 'warning' | 'error' | 'info' | 'neutral' | 'professional' | 'social' | 'legal' | 'healthcare' | 'family' | 'custom'
    size?: 'sm' | 'md'
  }>(),
  {
    variant: 'neutral',
    size: 'md'
  }
)

const classes = computed(() => {
  return [
    'badge',
    `badge-${props.variant}`,
    `badge-${props.size}`
  ]
})
</script>

<template>
  <span :class="classes">
    <slot />
  </span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  border-radius: var(--radius-full);
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
}

/* Sizes */
.badge-sm {
  padding: var(--spacing-1) var(--spacing-2);
  font-size: 11px;
}

.badge-md {
  padding: var(--spacing-1) var(--spacing-3);
  font-size: 13px;
}

/* Variants */
.badge-neutral {
  background-color: var(--color-gray-100);
  color: var(--color-gray-800);
}

.badge-primary {
  background-color: var(--color-primary-100);
  color: var(--color-primary-800);
}

.badge-success {
  background-color: var(--color-success-50);
  color: var(--color-success-700);
}

.badge-warning {
  background-color: var(--color-warning-50);
  color: var(--color-warning-700);
}

.badge-error {
  background-color: var(--color-error-50);
  color: var(--color-error-700);
}

.badge-info {
  background-color: var(--color-info-50);
  color: var(--color-info-700);
}

/* Context Type Colors */
.badge-professional {
  background-color: var(--color-primary-100);
  color: var(--color-primary-800);
}

.badge-social {
  background-color: #f3e8ff;
  color: #7e22ce;
}

.badge-legal {
  background-color: var(--color-success-50);
  color: var(--color-success-700);
}

.badge-healthcare {
  background-color: var(--color-error-50);
  color: var(--color-error-700);
}

.badge-family {
  background-color: var(--color-warning-50);
  color: var(--color-warning-700);
}

.badge-custom {
  background-color: var(--color-gray-100);
  color: var(--color-gray-800);
}
</style>
