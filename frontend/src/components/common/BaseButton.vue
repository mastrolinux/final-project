<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
    size?: 'sm' | 'md' | 'lg'
    type?: 'button' | 'submit' | 'reset'
    disabled?: boolean
    loading?: boolean
    block?: boolean
  }>(),
  {
    variant: 'primary',
    size: 'md',
    type: 'button',
    disabled: false,
    loading: false,
    block: false
  }
)

const classes = computed(() => {
  return [
    'btn',
    `btn-${props.variant}`,
    `btn-${props.size}`,
    { 'w-full': props.block, 'opacity-50 cursor-not-allowed': props.disabled || props.loading }
  ]
})
</script>

<template>
  <button :type="type" :class="classes" :disabled="disabled || loading">
    <span v-if="loading" class="spinner spinner-sm mr-2"></span>
    <slot />
  </button>
</template>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  font-weight: var(--font-weight-medium);
  transition: all var(--transition-fast);
  cursor: pointer;
  border: 1px solid transparent;
}

.btn:focus-visible {
  outline: 2px solid var(--color-primary-500);
  outline-offset: 2px;
}

/* Variants */
.btn-primary {
  background-color: var(--color-primary-600);
  color: white;
}
.btn-primary:hover:not(:disabled) {
  background-color: var(--color-primary-700);
}

.btn-secondary {
  background-color: white;
  color: var(--color-gray-700);
  border-color: var(--color-gray-300);
}
.btn-secondary:hover:not(:disabled) {
  background-color: var(--color-gray-50);
}

.btn-danger {
  background-color: var(--color-error-600);
  color: white;
}
.btn-danger:hover:not(:disabled) {
  background-color: var(--color-error-700);
}

.btn-ghost {
  background-color: transparent;
  color: var(--color-gray-600);
}
.btn-ghost:hover:not(:disabled) {
  background-color: var(--color-gray-100);
}

/* Sizes */
.btn-sm {
  padding: var(--spacing-1) var(--spacing-3);
  font-size: var(--font-size-sm);
  height: 32px;
}

.btn-md {
  padding: var(--spacing-2) var(--spacing-4);
  font-size: var(--font-size-base);
  height: 40px;
}

.btn-lg {
  padding: var(--spacing-3) var(--spacing-6);
  font-size: var(--font-size-lg);
  height: 48px;
}

.w-full {
  width: 100%;
}
</style>
