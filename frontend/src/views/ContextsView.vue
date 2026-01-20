<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore, useProfileStore } from '@/stores'
import { contextService, getErrorMessage } from '@/services'
import type { ContextType } from '@/types'

const { t } = useI18n()
const authStore = useAuthStore()
const profileStore = useProfileStore()

const isLoading = ref(true)
const error = ref<string | null>(null)

function getContextBadgeClass(contextType: ContextType): string {
  return `badge badge-${contextType}`
}

onMounted(async () => {
  if (!authStore.userId) return

  try {
    const contexts = await contextService.list(authStore.userId)
    profileStore.setContexts(contexts)
  } catch (err) {
    error.value = getErrorMessage(err)
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <div class="contexts-view">
    <div class="container container-lg">
      <div class="page-header flex justify-between items-center">
        <div>
          <h1 class="page-title">{{ t('context.title') }}</h1>
          <p class="page-description">{{ t('context.description') }}</p>
        </div>
        <router-link to="/contexts/new" class="btn btn-primary">
          {{ t('context.create') }}
        </router-link>
      </div>

      <div v-if="isLoading" class="loading-state">
        <div class="spinner"></div>
        <p>{{ t('common.loading') }}</p>
      </div>

      <div v-else-if="error" class="alert alert-error">
        {{ error }}
      </div>

      <div v-else-if="profileStore.contexts.length === 0" class="empty-state card">
        <div class="card-body text-center">
          <h3>No contexts yet</h3>
          <p class="text-secondary">Create your first identity context to get started.</p>
          <router-link to="/contexts/new" class="btn btn-primary mt-4">
            {{ t('context.create') }}
          </router-link>
        </div>
      </div>

      <div v-else class="contexts-grid">
        <router-link
          v-for="context in profileStore.contexts"
          :key="context.id"
          :to="`/contexts/${context.id}`"
          class="context-card card"
        >
          <div class="card-body">
            <div class="context-header">
              <span :class="getContextBadgeClass(context.context_type)">
                {{ t(`context.types.${context.context_type}`) }}
              </span>
              <span v-if="!context.is_active" class="badge badge-warning">
                {{ t('context.inactive') }}
              </span>
            </div>

            <h3 class="context-name">{{ context.context_name }}</h3>

            <div class="context-details">
              <p v-if="context.display_name_override" class="context-field">
                <span class="field-label">Display:</span>
                {{ context.display_name_override }}
              </p>
              <p v-if="context.email_override" class="context-field">
                <span class="field-label">Email:</span>
                {{ context.email_override }}
              </p>
              <p v-if="context.bio" class="context-bio">
                {{ context.bio }}
              </p>
            </div>
          </div>
        </router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.contexts-view {
  padding: var(--spacing-6) 0;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-12);
  color: var(--text-secondary);
}

.empty-state {
  max-width: 400px;
  margin: var(--spacing-8) auto;
}

.contexts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--spacing-4);
}

.context-card {
  text-decoration: none;
  color: inherit;
  transition: all var(--transition-fast);
}

.context-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.context-header {
  display: flex;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-3);
}

.context-name {
  font-size: var(--font-size-lg);
  margin-bottom: var(--spacing-3);
}

.context-details {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.context-field {
  margin-bottom: var(--spacing-1);
}

.field-label {
  color: var(--text-tertiary);
}

.context-bio {
  margin-top: var(--spacing-2);
  font-style: italic;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
</style>
