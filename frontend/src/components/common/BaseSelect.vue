<script setup lang="ts">
import { computed } from 'vue'

export interface SelectOption {
  label: string
  value: string | number
  disabled?: boolean
}

const props = withDefaults(
  defineProps<{
    modelValue: string | number | null
    options: SelectOption[]
    label?: string
    id: string
    placeholder?: string
    error?: string
    hint?: string
    disabled?: boolean
    required?: boolean
  }>(),
  {
    modelValue: '',
    disabled: false,
    required: false
  }
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: string | number): void
}>()

const handleChange = (event: Event) => {
  const target = event.target as HTMLSelectElement
  emit('update:modelValue', target.value)
}

const describedBy = computed(() => {
  const ids = []
  if (props.hint) ids.push(`${props.id}-hint`)
  if (props.error) ids.push(`${props.id}-error`)
  return ids.length ? ids.join(' ') : undefined
})
</script>

<template>
  <div class="form-group">
    <label v-if="label" :for="id" class="form-label">
      {{ label }}
      <span v-if="required" class="text-error" aria-hidden="true">*</span>
    </label>
    
    <div class="select-wrapper">
      <select
        :id="id"
        :value="modelValue"
        :disabled="disabled"
        :required="required"
        :aria-invalid="!!error"
        :aria-describedby="describedBy"
        class="form-select"
        :class="{ 'has-error': error }"
        @change="handleChange"
      >
        <option v-if="placeholder" value="" disabled selected>{{ placeholder }}</option>
        <option
          v-for="option in options"
          :key="option.value"
          :value="option.value"
          :disabled="option.disabled"
        >
          {{ option.label }}
        </option>
      </select>
      <div class="select-arrow">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd" />
        </svg>
      </div>
    </div>

    <p v-if="error" :id="`${id}-error`" class="form-error" role="alert">
      {{ error }}
    </p>
    <p v-else-if="hint" :id="`${id}-hint`" class="form-hint">
      {{ hint }}
    </p>
  </div>
</template>

<style scoped>
.form-group {
  margin-bottom: var(--spacing-4);
}

.form-label {
  display: block;
  margin-bottom: var(--spacing-1);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

.select-wrapper {
  position: relative;
}

.form-select {
  display: block;
  width: 100%;
  padding: var(--spacing-2) var(--spacing-3);
  padding-right: var(--spacing-8); /* Space for arrow */
  font-size: var(--font-size-base);
  line-height: 1.5;
  color: var(--text-primary);
  background-color: var(--input-bg);
  border: 1px solid var(--input-border);
  border-radius: var(--radius-md);
  appearance: none;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.form-select:focus {
  border-color: var(--color-primary-500);
  outline: 0;
  box-shadow: 0 0 0 2px var(--color-primary-100);
}

.form-select:disabled {
  background-color: var(--bg-tertiary);
  opacity: 0.7;
  cursor: not-allowed;
}

.form-select.has-error {
  border-color: var(--color-error-500);
}

.form-select.has-error:focus {
  box-shadow: 0 0 0 2px var(--color-error-100);
}

.select-arrow {
  position: absolute;
  top: 0;
  bottom: 0;
  right: 0;
  display: flex;
  align-items: center;
  padding-right: var(--spacing-2);
  pointer-events: none;
}

.select-arrow svg {
  height: 20px;
  width: 20px;
  color: var(--text-tertiary);
}

.form-error {
  margin-top: var(--spacing-1);
  font-size: var(--font-size-sm);
  color: var(--color-error-600);
}

.form-hint {
  margin-top: var(--spacing-1);
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
}

.text-error {
  color: var(--color-error-600);
}
</style>
