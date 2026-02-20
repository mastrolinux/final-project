<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    variant?: "primary" | "secondary" | "danger" | "ghost";
    size?: "sm" | "md" | "lg";
    type?: "button" | "submit" | "reset";
    disabled?: boolean;
    loading?: boolean;
    block?: boolean;
  }>(),
  {
    variant: "primary",
    size: "md",
    type: "button",
    disabled: false,
    loading: false,
    block: false,
  },
);

const classes = computed(() => {
  return [
    "btn",
    `btn-${props.variant}`,
    `btn-${props.size}`,
    {
      "w-full": props.block,
      "is-loading": props.loading,
      "is-disabled": props.disabled || props.loading,
    },
  ];
});
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
  transition: all var(--transition-normal);
  cursor: pointer;
  border: 1px solid transparent;
}

.btn:focus-visible {
  outline: none;
  box-shadow:
    0 0 0 2px var(--bg-primary),
    0 0 0 4px var(--color-primary-500);
}

.btn.is-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn.is-loading {
  opacity: 0.85;
  cursor: wait;
}

/* Variants */
.btn-primary {
  background-color: var(--color-primary-600);
  color: white;
}
.btn-primary:hover:not(:disabled) {
  background-color: var(--color-primary-700);
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.1),
    0 2px 4px -1px rgba(0, 0, 0, 0.06);
  transform: translateY(-1px);
}

.btn-secondary {
  background-color: var(--bg-secondary);
  color: var(--text-primary);
  border-color: var(--border-secondary);
}
.btn-secondary:hover:not(:disabled) {
  background-color: var(--bg-tertiary);
}

.btn-danger {
  background-color: var(--color-error-600);
  color: white;
}
.btn-danger:hover:not(:disabled) {
  background-color: var(--color-error-700);
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.1),
    0 2px 4px -1px rgba(0, 0, 0, 0.06);
  transform: translateY(-1px);
}
.btn-danger:focus-visible {
  box-shadow:
    0 0 0 2px var(--bg-primary),
    0 0 0 4px var(--color-error-500);
}

.btn-ghost {
  background-color: transparent;
  color: var(--text-secondary);
}
.btn-ghost:hover:not(:disabled) {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
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
