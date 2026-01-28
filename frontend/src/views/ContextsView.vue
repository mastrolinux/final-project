<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore, useProfileStore } from '@/stores'
import { contextService, getErrorMessage } from '@/services'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseBadge from '@/components/common/BaseBadge.vue'
import { CONTEXT_TYPE_META } from '@/types'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()
const profileStore = useProfileStore()

const isLoading = ref(true)
const error = ref<string | null>(null)

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

const navigateToCreate = () => {
  router.push({ name: 'context-create' })
}

const navigateToDetail = (id: string) => {
  router.push({ name: 'context-detail', params: { id } })
}
</script>

<template>
  <div class="contexts-view">
    <div class="container container-lg">
      <div class="page-header flex justify-between items-center mb-8">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">{{ t('context.title') }}</h1>
          <p class="text-gray-500 mt-1">{{ t('context.description') }}</p>
        </div>
        <BaseButton variant="primary" @click="navigateToCreate">
          {{ t('context.create') }}
        </BaseButton>
      </div>

      <div v-if="isLoading" class="loading-state text-center py-12">
        <div class="spinner spinner-lg mx-auto"></div>
        <p class="mt-4 text-gray-500">{{ t('common.loading') }}</p>
      </div>

      <div v-else-if="error" class="alert alert-error mb-6">
        {{ error }}
      </div>

      <div v-else-if="profileStore.contexts.length === 0" class="empty-state">
        <BaseCard class="text-center py-12">
          <div class="mx-auto w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4 text-2xl">
            📇
          </div>
          <h3 class="text-lg font-semibold text-gray-900 mb-2">No contexts yet</h3>
          <p class="text-gray-500 mb-6 max-w-md mx-auto">
            Create your first identity context to share different information with different applications.
          </p>
          <BaseButton variant="primary" @click="navigateToCreate">
            {{ t('context.create') }}
          </BaseButton>
        </BaseCard>
      </div>

      <div v-else class="contexts-grid grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div
          v-for="context in profileStore.contexts"
          :key="context.id"
          class="context-card-wrapper"
          role="button"
          tabindex="0"
          :aria-label="t('context.viewContext', { name: context.context_name })"
          @click="navigateToDetail(context.id)"
          @keydown.enter="navigateToDetail(context.id)"
          @keydown.space.prevent="navigateToDetail(context.id)"
        >
          <BaseCard class="h-full hover:shadow-md transition-shadow cursor-pointer border-l-4" :style="{ borderLeftColor: `var(--color-${CONTEXT_TYPE_META[context.context_type].color}-500)` }">
            <div class="flex justify-between items-start mb-4">
              <BaseBadge :variant="context.context_type">
                {{ CONTEXT_TYPE_META[context.context_type]?.label }}
              </BaseBadge>
              <BaseBadge v-if="!context.is_active" variant="warning">
                {{ t('context.inactive') }}
              </BaseBadge>
              <BaseBadge v-else variant="success" size="sm" class="opacity-0 group-hover:opacity-100 transition-opacity">
                Active
              </BaseBadge>
            </div>

            <h3 class="text-lg font-semibold text-gray-900 mb-2">{{ context.context_name }}</h3>
            
            <div class="space-y-2 text-sm text-gray-600">
              <div v-if="context.display_name_override" class="flex items-center gap-2">
                <span class="text-xs font-medium text-gray-400 uppercase w-12">Name</span>
                <span class="truncate">{{ context.display_name_override }}</span>
              </div>
              <div v-if="context.email_override" class="flex items-center gap-2">
                <span class="text-xs font-medium text-gray-400 uppercase w-12">Email</span>
                <span class="truncate">{{ context.email_override }}</span>
              </div>
              <div v-if="!context.display_name_override && !context.email_override" class="text-gray-400 italic">
                Inherits all fields
              </div>
            </div>
          </BaseCard>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.contexts-view {
  padding: var(--spacing-8) 0;
}

/* Utility classes */
.flex { display: flex; }
.justify-between { justify-content: space-between; }
.items-center { align-items: center; }
.items-start { align-items: flex-start; }
.mb-8 { margin-bottom: 2rem; }
.mb-6 { margin-bottom: 1.5rem; }
.mb-4 { margin-bottom: 1rem; }
.mb-2 { margin-bottom: 0.5rem; }
.mt-1 { margin-top: 0.25rem; }
.mt-4 { margin-top: 1rem; }
.mx-auto { margin-left: auto; margin-right: auto; }
.py-12 { padding-top: 3rem; padding-bottom: 3rem; }
.text-center { text-align: center; }
.text-2xl { font-size: 1.5rem; line-height: 2rem; }
.text-lg { font-size: 1.125rem; line-height: 1.75rem; }
.text-sm { font-size: 0.875rem; line-height: 1.25rem; }
.text-xs { font-size: 0.75rem; line-height: 1rem; }
.font-bold { font-weight: 700; }
.font-semibold { font-weight: 600; }
.font-medium { font-weight: 500; }
.text-gray-900 { color: var(--text-primary); }
.text-gray-600 { color: var(--text-secondary); }
.text-gray-500 { color: var(--text-secondary); }
.text-gray-400 { color: var(--text-tertiary); }
.bg-gray-100 { background-color: var(--bg-tertiary); }
.rounded-full { border-radius: 9999px; }
.w-16 { width: 4rem; }
.h-16 { height: 4rem; }
.h-full { height: 100%; }
.w-12 { width: 3rem; }
.max-w-md { max-width: 28rem; }
.grid { display: grid; }
.gap-6 { gap: 1.5rem; }
.gap-2 { gap: 0.5rem; }
.space-y-2 > * + * { margin-top: 0.5rem; }
.truncate { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.italic { font-style: italic; }
.border-l-4 { border-left-width: 4px; }
.hover\:shadow-md:hover { box-shadow: var(--shadow-md); }
.transition-shadow { transition: box-shadow 0.3s ease; }
.cursor-pointer { cursor: pointer; }

/* Keyboard accessibility */
.context-card-wrapper:focus-visible {
  outline: none;
}
.context-card-wrapper:focus-visible > :deep(.card) {
  box-shadow: 0 0 0 2px var(--bg-primary), 0 0 0 4px var(--color-primary-500);
}

@media (min-width: 768px) {
  .md\:grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (min-width: 1024px) {
  .lg\:grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
</style>
