<script setup lang="ts">
import type { OAuthScope } from '@/types'
import { CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/outline'

defineProps<{
  scopes: OAuthScope[]
}>()
</script>

<template>
  <div class="scope-list">
    <div v-for="scope in scopes" :key="scope.scope_name" class="scope-item">
      <div class="scope-icon">
        <ExclamationTriangleIcon v-if="scope.is_sensitive" class="icon text-warning" />
        <CheckCircleIcon v-else class="icon text-success" />
      </div>
      <div class="scope-content">
        <h4 class="scope-name">{{ scope.scope_name }}</h4>
        <p class="scope-description">{{ scope.description }}</p>
      </div>
      <div v-if="scope.is_sensitive" class="scope-badge">
        <span class="badge badge-warning">Sensitive</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.scope-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.scope-item {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-3);
  padding: var(--spacing-3);
  background-color: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.scope-icon {
  flex-shrink: 0;
  margin-top: 2px;
}

.icon {
  width: 20px;
  height: 20px;
}

.text-success {
  color: var(--color-success-600);
}

.text-warning {
  color: var(--color-warning-600);
}

.scope-content {
  flex: 1;
}

.scope-name {
  font-size: var(--font-size-sm);
  font-weight: 600;
  margin: 0 0 2px 0;
  color: var(--text-primary);
}

.scope-description {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.4;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 6px;
  border-radius: 9999px;
  font-size: 10px;
  font-weight: 500;
  background-color: var(--color-gray-100);
  color: var(--color-gray-700);
}

.badge-warning {
  background-color: var(--color-warning-100);
  color: var(--color-warning-700);
}
</style>
