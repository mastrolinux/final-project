<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { getErrorMessage } from '@/services'
import auditService from '@/services/audit.service'
import type { AuditLogEntry } from '@/types'
import AuditLogCard from '@/components/audit/AuditLogCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseSelect from '@/components/common/BaseSelect.vue'
import BaseEmptyState from '@/components/common/BaseEmptyState.vue'

const { t } = useI18n()

const entries = ref<AuditLogEntry[]>([])
const total = ref(0)
const isLoading = ref(true)
const error = ref<string | null>(null)

// Pagination
const limit = ref(20)
const offset = ref(0)

// Filters
const eventTypeFilter = ref('')
const resourceTypeFilter = ref('')

const totalPages = computed(() => Math.ceil(total.value / limit.value))
const currentPage = computed(() => Math.floor(offset.value / limit.value) + 1)

const eventTypeOptions = [
  { value: '', label: t('audit.filters.allEvents') },
  { value: 'auth.login.success', label: t('audit.events.loginSuccess') },
  { value: 'auth.login.failure', label: t('audit.events.loginFailure') },
  { value: 'auth.logout', label: t('audit.events.logout') },
  { value: 'auth.register', label: t('audit.events.register') },
  { value: 'auth.email_verification', label: t('audit.events.emailVerification') },
  { value: 'auth.password_change', label: t('audit.events.passwordChange') },
  { value: 'auth.password_reset_request', label: t('audit.events.passwordResetRequest') },
  { value: 'auth.password_reset', label: t('audit.events.passwordReset') },
  { value: 'profile.create', label: t('audit.events.profileCreate') },
  { value: 'profile.update', label: t('audit.events.profileUpdate') },
  { value: 'profile.delete', label: t('audit.events.profileDelete') },
  { value: 'context.create', label: t('audit.events.contextCreate') },
  { value: 'context.update', label: t('audit.events.contextUpdate') },
  { value: 'context.delete', label: t('audit.events.contextDelete') },
  { value: 'consent.grant', label: t('audit.events.consentGrant') },
  { value: 'consent.withdraw', label: t('audit.events.consentWithdraw') },
  { value: 'oauth.token.revoke', label: t('audit.events.tokenRevoke') }
]

const resourceTypeOptions = [
  { value: '', label: t('audit.filters.allResources') },
  { value: 'auth_user', label: t('audit.resources.authUser') },
  { value: 'profile', label: t('audit.resources.profile') },
  { value: 'context', label: t('audit.resources.context') },
  { value: 'oauth_consent', label: t('audit.resources.oauthConsent') },
  { value: 'oauth_token', label: t('audit.resources.oauthToken') },
  { value: 'oauth_client', label: t('audit.resources.oauthClient') }
]

async function loadEntries() {
  isLoading.value = true
  error.value = null
  try {
    const response = await auditService.getMyAuditTrail({
      limit: limit.value,
      offset: offset.value,
      event_type: eventTypeFilter.value || undefined,
      resource_type: resourceTypeFilter.value || undefined
    })
    entries.value = response.entries
    total.value = response.total
  } catch (err) {
    error.value = getErrorMessage(err)
  } finally {
    isLoading.value = false
  }
}

function applyFilters() {
  offset.value = 0
  loadEntries()
}

function goToPage(page: number) {
  offset.value = (page - 1) * limit.value
  loadEntries()
}

onMounted(loadEntries)
</script>

<template>
  <div class="audit-trail-view">
    <div class="container container-lg">
      <div class="page-header">
        <div>
          <h1 class="page-title">{{ t('audit.title') }}</h1>
          <p class="page-description">{{ t('audit.description') }}</p>
        </div>
      </div>

      <!-- Filters -->
      <div class="filters-bar">
        <div class="filter-group">
          <BaseSelect
            id="event_type_filter"
            :model-value="eventTypeFilter"
            :options="eventTypeOptions"
            :label="t('audit.filters.eventType')"
            @update:model-value="(val: string | number) => { eventTypeFilter = String(val); applyFilters() }"
          />
        </div>
        <div class="filter-group">
          <BaseSelect
            id="resource_type_filter"
            :model-value="resourceTypeFilter"
            :options="resourceTypeOptions"
            :label="t('audit.filters.resourceType')"
            @update:model-value="(val: string | number) => { resourceTypeFilter = String(val); applyFilters() }"
          />
        </div>
      </div>

      <!-- Loading -->
      <div v-if="isLoading" class="loading-state">
        <div class="spinner spinner-lg"></div>
        <p class="loading-text">{{ t('common.loading') }}</p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="alert alert-error">{{ error }}</div>

      <!-- Empty -->
      <BaseEmptyState
        v-else-if="entries.length === 0"
        :title="t('audit.empty.title')"
        :description="t('audit.empty.description')"
      />

      <!-- Entries List -->
      <template v-else>
        <div class="entries-list">
          <AuditLogCard
            v-for="entry in entries"
            :key="entry.log_id"
            :entry="entry"
          />
        </div>

        <!-- Pagination -->
        <div v-if="totalPages > 1" class="pagination">
          <BaseButton
            variant="secondary"
            size="sm"
            :disabled="currentPage <= 1"
            @click="goToPage(currentPage - 1)"
          >
            {{ t('audit.pagination.previous') }}
          </BaseButton>
          <span class="pagination-info">
            {{ t('audit.pagination.page', { current: currentPage, total: totalPages }) }}
          </span>
          <BaseButton
            variant="secondary"
            size="sm"
            :disabled="currentPage >= totalPages"
            @click="goToPage(currentPage + 1)"
          >
            {{ t('audit.pagination.next') }}
          </BaseButton>
        </div>

        <p class="total-info">
          {{ t('audit.pagination.showing', { count: entries.length, total: total }) }}
        </p>
      </template>
    </div>
  </div>
</template>

<style scoped>
.audit-trail-view {
  padding: var(--spacing-8) 0;
}

.filters-bar {
  display: flex;
  align-items: flex-end;
  gap: var(--spacing-4);
  padding: var(--spacing-4);
  background-color: var(--bg-secondary);
  border-radius: var(--radius-lg);
  margin-bottom: var(--spacing-6);
  flex-wrap: wrap;
}

.filter-group {
  flex: 1;
  min-width: 200px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-4);
  padding: var(--spacing-12);
}

.loading-text {
  color: var(--text-secondary);
}

.entries-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-4);
  margin-top: var(--spacing-6);
}

.pagination-info {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.total-info {
  text-align: center;
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  margin-top: var(--spacing-2);
}
</style>
