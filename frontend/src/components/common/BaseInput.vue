<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: string | number | null
    label?: string
    id: string
    type?: string
    placeholder?: string
    error?: string
    hint?: string
    disabled?: boolean
    required?: boolean
  }>(),
  {
    type: 'text',
    modelValue: '',
    disabled: false,
    required: false
  }
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: string | number): void
}>()

const handleInput = (event: Event) => {
  const target = event.target as HTMLInputElement
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
    
    <input
      :id="id"
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :required="required"
      :aria-invalid="!!error"
      :aria-describedby="describedBy"
      class="form-input"
      :class="{ 'has-error': error }"
      @input="handleInput"
    />

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

.form-input {
  display: block;
  width: 100%;
  padding: var(--spacing-2) var(--spacing-3);
  font-size: var(--font-size-base);
  line-height: 1.5;
  color: var(--text-primary);
  background-color: var(--input-bg);
  background-clip: padding-box;
  border: 1px solid var(--input-border);
  border-radius: var(--radius-md);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.form-input:focus {
  border-color: var(--color-primary-500);
  outline: 0;
  box-shadow: 0 0 0 2px var(--color-primary-100);
}

.form-input:disabled {
  background-color: var(--bg-tertiary);
  opacity: 0.7;
  cursor: not-allowed;
}

.form-input.has-error {
  border-color: var(--color-error-500);
}

.form-input.has-error:focus {
  box-shadow: 0 0 0 2px var(--color-error-100);
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
