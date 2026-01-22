<script setup lang="ts">
import type { ContextProfileResponse } from '@/types'
import { CheckIcon } from '@heroicons/vue/24/solid'

defineProps<{
  contexts: ContextProfileResponse[]
  modelValue: string | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

function selectContext(id: string) {
  emit('update:modelValue', id)
}
</script>

<template>
  <div class="context-selector">
    <div
      v-for="context in contexts"
      :key="context.id"
      class="context-card"
      :class="{ selected: modelValue === context.id }"
      @click="selectContext(context.id)"
    >
      <div class="context-info">
        <div class="context-header">
          <span class="context-name">{{ context.context_name }}</span>
          <span class="context-type badge">{{ context.context_type }}</span>
        </div>
        <div class="context-details">
          <span class="detail">{{ context.display_name_override || 'Inherited Name' }}</span>
          <span class="detail text-secondary">{{ context.email_override || 'Inherited Email' }}</span>
        </div>
      </div>
      <div class="selection-indicator">
        <div class="radio-circle">
          <CheckIcon v-if="modelValue === context.id" class="check-icon" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.context-selector {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.context-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-3);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s ease;
  background-color: var(--bg-primary);
}

.context-card:hover {
  border-color: var(--color-primary-300);
  background-color: var(--bg-secondary);
}

.context-card.selected {
  border-color: var(--color-primary-500);
  background-color: var(--color-primary-50);
  box-shadow: 0 0 0 1px var(--color-primary-500);
}

.context-info {
  flex: 1;
}

.context-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-1);
}

.context-name {
  font-weight: 600;
  font-size: var(--font-size-sm);
  color: var(--text-primary);
}

.context-type {
  text-transform: capitalize;
  font-size: 10px;
  padding: 1px 6px;
  background-color: var(--color-gray-100);
  border-radius: 4px;
}

.context-details {
  display: flex;
  flex-direction: column;
  font-size: var(--font-size-xs);
}

.detail {
  color: var(--text-secondary);
  margin-right: var(--spacing-2);
}

.text-secondary {
  color: var(--text-tertiary);
}

.selection-indicator {
  padding-left: var(--spacing-3);
}

.radio-circle {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: white;
}

.selected .radio-circle {
  border-color: var(--color-primary-600);
  background-color: var(--color-primary-600);
}

.check-icon {
  width: 14px;
  height: 14px;
  color: white;
}
</style>
