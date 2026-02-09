<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { getErrorMessage } from '@/services'
import privacyService from '@/services/privacy.service'
import type { DataExportResponse } from '@/types'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseBadge from '@/components/common/BaseBadge.vue'
import { ArrowDownTrayIcon } from '@heroicons/vue/24/outline'
import AppBreadcrumb from '@/components/layout/AppBreadcrumb.vue'

const { t } = useI18n()

const exportData = ref<DataExportResponse | null>(null)
const rawJson = ref<string>('')
const isLoading = ref(true)
const isDownloading = ref(false)
const error = ref<string | null>(null)

async function loadExport() {
  isLoading.value = true
  error.value = null
  try {
    const data = await privacyService.exportUserData()
    exportData.value = data
    rawJson.value = JSON.stringify(data, null, 2)
  } catch (err) {
    error.value = getErrorMessage(err)
  } finally {
    isLoading.value = false
  }
}

function downloadJson() {
  if (!rawJson.value) return
  isDownloading.value = true
  try {
    const blob = new Blob([rawJson.value], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    const timestamp = new Date().toISOString().slice(0, 10)
    link.href = url
    link.download = `identity-data-export-${timestamp}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  } finally {
    isDownloading.value = false
  }
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return t('privacy.values.notSet')
  return new Date(dateStr).toLocaleString()
}

function formatBool(val: boolean): string {
  return val ? t('privacy.values.yes') : t('privacy.values.no')
}

/** Map name_value JSONB to readable string. */
function formatNameValue(val: Record<string, string>): string {
  return Object.entries(val)
    .map(([lang, name]) => `${lang}: ${name}`)
    .join(', ')
}

onMounted(loadExport)
</script>

<template>
  <div class="export-view">
    <div class="container container-lg">
      <AppBreadcrumb />

      <!-- Header -->
      <div class="page-header export-header">
        <div>
          <h1 class="page-title">{{ t('privacy.title') }}</h1>
          <p class="page-description">{{ t('privacy.description') }}</p>
        </div>
        <BaseButton
          v-if="exportData"
          variant="primary"
          @click="downloadJson"
          :disabled="isDownloading"
        >
          <ArrowDownTrayIcon class="btn-icon" />
          {{ isDownloading ? t('privacy.downloading') : t('privacy.downloadJson') }}
        </BaseButton>
      </div>

      <!-- Loading -->
      <div v-if="isLoading" class="loading-state">
        <div class="spinner spinner-lg"></div>
        <p class="loading-text">{{ t('common.loading') }}</p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="alert alert-error">{{ error }}</div>

      <!-- Export content -->
      <template v-else-if="exportData">
        <!-- Export metadata bar -->
        <div class="export-meta-bar">
          <span class="meta-item">
            <span class="meta-label">{{ t('privacy.exportedAt') }}:</span>
            {{ formatDate(exportData.export_metadata.exported_at) }}
          </span>
          <span class="meta-item">
            <span class="meta-label">{{ t('privacy.formatVersion') }}:</span>
            {{ exportData.export_metadata.format_version }}
          </span>
          <span class="meta-item">
            <span class="meta-label">{{ t('privacy.legalBasis') }}:</span>
            {{ exportData.export_metadata.legal_basis }}
          </span>
        </div>

        <!-- Profile Section -->
        <details class="export-section" open>
          <summary class="section-summary section-profile">
            <h2>{{ t('privacy.sections.profile') }}</h2>
          </summary>
          <div class="section-body">
            <div class="fields-grid">
              <div class="field-item">
                <span class="field-label">{{ t('privacy.profile.userId') }}</span>
                <code class="field-value field-value-mono">{{ exportData.profile.user_id }}</code>
              </div>
              <div class="field-item">
                <span class="field-label">{{ t('privacy.profile.accountType') }}</span>
                <span class="field-value">
                  <BaseBadge :variant="exportData.profile.account_type === 'verified' ? 'success' : 'neutral'" size="sm">
                    {{ exportData.profile.account_type }}
                  </BaseBadge>
                </span>
              </div>
              <div class="field-item">
                <span class="field-label">{{ t('privacy.profile.legalName') }}</span>
                <span class="field-value">{{ exportData.profile.legal_name || t('privacy.values.notSet') }}</span>
              </div>
              <div class="field-item">
                <span class="field-label">{{ t('privacy.profile.primaryEmail') }}</span>
                <span class="field-value">{{ exportData.profile.primary_email }}</span>
              </div>
              <div class="field-item">
                <span class="field-label">{{ t('privacy.profile.primaryPhone') }}</span>
                <span class="field-value">{{ exportData.profile.primary_phone || t('privacy.values.notSet') }}</span>
              </div>
              <div class="field-item">
                <span class="field-label">{{ t('privacy.profile.preferredLanguage') }}</span>
                <span class="field-value">{{ exportData.profile.preferred_language }}</span>
              </div>
              <div class="field-item">
                <span class="field-label">{{ t('privacy.profile.createdAt') }}</span>
                <span class="field-value">{{ formatDate(exportData.profile.created_at) }}</span>
              </div>
              <div class="field-item">
                <span class="field-label">{{ t('privacy.profile.updatedAt') }}</span>
                <span class="field-value">{{ formatDate(exportData.profile.updated_at) }}</span>
              </div>
            </div>
          </div>
        </details>

        <!-- Identity Names Section -->
        <details class="export-section">
          <summary class="section-summary section-names">
            <h2>
              {{ t('privacy.sections.identityNames') }}
              <span class="section-count">{{ exportData.identity_names.length }}</span>
            </h2>
          </summary>
          <div class="section-body">
            <div v-if="exportData.identity_names.length === 0" class="section-empty">
              {{ t('privacy.values.notSet') }}
            </div>
            <div v-else class="name-cards">
              <div
                v-for="name in exportData.identity_names"
                :key="name.id"
                class="name-card"
                :class="{ 'name-card-deprecated': name.is_deprecated }"
              >
                <div class="name-card-header">
                  <BaseBadge variant="primary" size="sm">{{ name.name_type }}</BaseBadge>
                  <BaseBadge v-if="name.is_primary" variant="success" size="sm">{{ t('privacy.names.primary') }}</BaseBadge>
                  <BaseBadge v-if="name.is_deprecated" variant="warning" size="sm">{{ t('privacy.names.deprecated') }}</BaseBadge>
                </div>
                <div class="name-card-value">{{ formatNameValue(name.name_value) }}</div>
                <div class="name-card-meta">
                  <span>{{ t('privacy.names.visibility') }}: {{ name.visibility_level }}</span>
                </div>
              </div>
            </div>
          </div>
        </details>

        <!-- Context Profiles Section -->
        <details class="export-section">
          <summary class="section-summary section-contexts">
            <h2>
              {{ t('privacy.sections.contextProfiles') }}
              <span class="section-count">{{ exportData.context_profiles.length }}</span>
            </h2>
          </summary>
          <div class="section-body">
            <div v-if="exportData.context_profiles.length === 0" class="section-empty">
              {{ t('privacy.values.notSet') }}
            </div>
            <div v-else class="context-cards">
              <div
                v-for="ctx in exportData.context_profiles"
                :key="ctx.id"
                class="context-card-export"
              >
                <div class="context-card-header">
                  <BaseBadge :variant="(ctx.context_type as any)" size="sm">{{ ctx.context_type }}</BaseBadge>
                  <BaseBadge
                    :variant="ctx.is_active ? 'success' : 'neutral'"
                    size="sm"
                  >
                    {{ ctx.is_active ? t('privacy.contexts.active') : t('privacy.contexts.inactive') }}
                  </BaseBadge>
                </div>
                <h3 class="context-card-name">{{ ctx.context_name }}</h3>
                <div class="context-card-fields">
                  <div v-if="ctx.display_name_override" class="field-inline">
                    <span class="field-label-sm">{{ t('privacy.contexts.displayName') }}:</span>
                    {{ ctx.display_name_override }}
                  </div>
                  <div v-if="ctx.email_override" class="field-inline">
                    <span class="field-label-sm">{{ t('privacy.contexts.email') }}:</span>
                    {{ ctx.email_override }}
                  </div>
                  <div v-if="ctx.phone_override" class="field-inline">
                    <span class="field-label-sm">{{ t('privacy.contexts.phone') }}:</span>
                    {{ ctx.phone_override }}
                  </div>
                  <div v-if="ctx.bio" class="field-inline">
                    <span class="field-label-sm">{{ t('privacy.contexts.bio') }}:</span>
                    {{ ctx.bio }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </details>

        <!-- Authentication Section -->
        <details class="export-section">
          <summary class="section-summary section-auth">
            <h2>{{ t('privacy.sections.authentication') }}</h2>
          </summary>
          <div class="section-body">
            <div v-if="!exportData.authentication" class="section-empty">
              {{ t('privacy.auth.noAuthData') }}
            </div>
            <div v-else class="fields-grid">
              <div class="field-item">
                <span class="field-label">{{ t('privacy.auth.email') }}</span>
                <span class="field-value">{{ exportData.authentication.email }}</span>
              </div>
              <div class="field-item">
                <span class="field-label">{{ t('privacy.auth.emailVerified') }}</span>
                <span class="field-value">
                  <BaseBadge :variant="exportData.authentication.is_email_verified ? 'success' : 'warning'" size="sm">
                    {{ formatBool(exportData.authentication.is_email_verified) }}
                  </BaseBadge>
                </span>
              </div>
              <div class="field-item">
                <span class="field-label">{{ t('privacy.auth.lastLogin') }}</span>
                <span class="field-value">{{ formatDate(exportData.authentication.last_login_at) }}</span>
              </div>
              <div class="field-item">
                <span class="field-label">{{ t('privacy.auth.passwordChanged') }}</span>
                <span class="field-value">{{ formatDate(exportData.authentication.password_changed_at) }}</span>
              </div>
              <div class="field-item">
                <span class="field-label">{{ t('privacy.auth.isAdmin') }}</span>
                <span class="field-value">{{ formatBool(exportData.authentication.is_admin) }}</span>
              </div>
              <div class="field-item">
                <span class="field-label">{{ t('privacy.auth.createdAt') }}</span>
                <span class="field-value">{{ formatDate(exportData.authentication.created_at) }}</span>
              </div>
            </div>
          </div>
        </details>

        <!-- OAuth Consents Section -->
        <details class="export-section">
          <summary class="section-summary section-consents">
            <h2>
              {{ t('privacy.sections.oauthConsents') }}
              <span class="section-count">{{ exportData.oauth_consents.length }}</span>
            </h2>
          </summary>
          <div class="section-body">
            <div v-if="exportData.oauth_consents.length === 0" class="section-empty">
              {{ t('privacy.consents.noConsents') }}
            </div>
            <div v-else class="consent-cards">
              <div
                v-for="consent in exportData.oauth_consents"
                :key="consent.id"
                class="consent-card"
              >
                <div class="consent-card-header">
                  <code class="consent-client-id">{{ consent.client_id }}</code>
                  <BaseBadge
                    :variant="consent.withdrawn_at ? 'error' : 'success'"
                    size="sm"
                  >
                    {{ consent.withdrawn_at ? 'Withdrawn' : 'Active' }}
                  </BaseBadge>
                </div>
                <div class="consent-card-fields">
                  <div class="field-inline">
                    <span class="field-label-sm">{{ t('privacy.consents.scopes') }}:</span>
                    <span class="scopes-list">
                      <code v-for="scope in consent.granted_scopes" :key="scope" class="scope-tag">{{ scope }}</code>
                    </span>
                  </div>
                  <div class="field-inline">
                    <span class="field-label-sm">{{ t('privacy.consents.method') }}:</span>
                    {{ consent.consent_method }}
                  </div>
                  <div class="field-inline">
                    <span class="field-label-sm">{{ t('privacy.consents.grantedAt') }}:</span>
                    {{ formatDate(consent.granted_at) }}
                  </div>
                  <div v-if="consent.withdrawn_at" class="field-inline">
                    <span class="field-label-sm">{{ t('privacy.consents.withdrawnAt') }}:</span>
                    {{ formatDate(consent.withdrawn_at) }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </details>

        <!-- GDPR Information Section -->
        <details class="export-section">
          <summary class="section-summary section-gdpr">
            <h2>{{ t('privacy.sections.gdprInfo') }}</h2>
          </summary>
          <div class="section-body gdpr-body">
            <!-- Processing Purposes -->
            <div class="gdpr-block">
              <h3>{{ t('privacy.gdpr.processingPurposes') }}</h3>
              <ul class="gdpr-list">
                <li v-for="(purpose, i) in exportData.gdpr_metadata.processing_purposes" :key="i">
                  {{ purpose }}
                </li>
              </ul>
            </div>

            <!-- Retention Periods -->
            <div class="gdpr-block">
              <h3>{{ t('privacy.gdpr.retentionPeriods') }}</h3>
              <div class="retention-grid">
                <div
                  v-for="(period, key) in exportData.gdpr_metadata.retention_periods"
                  :key="key"
                  class="retention-item"
                >
                  <span class="retention-key">{{ key.replace(/_/g, ' ') }}</span>
                  <span class="retention-value">{{ period }}</span>
                </div>
              </div>
            </div>

            <!-- Data Subject Rights -->
            <div class="gdpr-block">
              <h3>{{ t('privacy.gdpr.dataSubjectRights') }}</h3>
              <ul class="gdpr-list">
                <li v-for="(right, i) in exportData.gdpr_metadata.data_subject_rights" :key="i">
                  {{ right }}
                </li>
              </ul>
            </div>

            <!-- Data Sources -->
            <div class="gdpr-block">
              <h3>{{ t('privacy.gdpr.dataSources') }}</h3>
              <ul class="gdpr-list">
                <li v-for="(source, i) in exportData.gdpr_metadata.data_sources" :key="i">
                  {{ source }}
                </li>
              </ul>
            </div>

            <!-- Recipients -->
            <div class="gdpr-block">
              <h3>{{ t('privacy.gdpr.recipients') }}</h3>
              <ul class="gdpr-list">
                <li v-for="(recipient, i) in exportData.gdpr_metadata.recipients_or_categories" :key="i">
                  {{ recipient }}
                </li>
              </ul>
            </div>

            <!-- Automated Decision-Making -->
            <div class="gdpr-block">
              <h3>{{ t('privacy.gdpr.automatedDecisions') }}</h3>
              <p>{{ exportData.gdpr_metadata.automated_decision_making }}</p>
            </div>
          </div>
        </details>
      </template>
    </div>
  </div>
</template>

<style scoped>
.export-view {
  padding: var(--spacing-8) 0;
}

/* Header */
.export-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-4);
  flex-wrap: wrap;
}

.btn-icon {
  width: 18px;
  height: 18px;
  margin-right: var(--spacing-1);
}

/* Export metadata bar */
.export-meta-bar {
  display: flex;
  align-items: center;
  gap: var(--spacing-6);
  padding: var(--spacing-3) var(--spacing-4);
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  margin-bottom: var(--spacing-6);
  flex-wrap: wrap;
  font-size: var(--font-size-sm);
}

.meta-item {
  color: var(--text-secondary);
}

.meta-label {
  color: var(--text-tertiary);
  font-weight: var(--font-weight-medium);
}

/* Loading state */
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

/* Sections (collapsible) */
.export-section {
  margin-bottom: var(--spacing-4);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  background-color: var(--bg-primary);
  overflow: hidden;
}

.section-summary {
  display: flex;
  align-items: center;
  padding: var(--spacing-4) var(--spacing-5);
  cursor: pointer;
  user-select: none;
  border-left: 4px solid var(--color-gray-300);
  transition: background-color var(--transition-fast);
}

.section-summary:hover {
  background-color: var(--bg-tertiary);
}

.section-summary h2 {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  margin: 0;
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.section-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 var(--spacing-2);
  border-radius: var(--radius-full);
  background-color: var(--bg-tertiary);
  color: var(--text-secondary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
}

/* Section accent colors */
.section-profile { border-left-color: var(--color-primary-500); }
.section-names { border-left-color: var(--color-info-500); }
.section-contexts { border-left-color: #a855f7; }
.section-auth { border-left-color: var(--color-success-500); }
.section-consents { border-left-color: #f59e0b; }
.section-gdpr { border-left-color: var(--color-gray-500); }

.section-body {
  padding: var(--spacing-5);
  border-top: 1px solid var(--border-primary);
}

.section-empty {
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
  font-style: italic;
  padding: var(--spacing-2) 0;
}

/* Fields grid (profile, auth) */
.fields-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-4);
}

.field-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.field-label {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  font-weight: var(--font-weight-medium);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.field-value {
  font-size: var(--font-size-sm);
  color: var(--text-primary);
}

.field-value-mono {
  font-family: monospace;
  font-size: var(--font-size-xs);
  word-break: break-all;
}

/* Name cards */
.name-cards {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.name-card {
  padding: var(--spacing-3) var(--spacing-4);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  background-color: var(--bg-secondary);
}

.name-card-deprecated {
  opacity: 0.7;
  border-style: dashed;
}

.name-card-header {
  display: flex;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-2);
  flex-wrap: wrap;
}

.name-card-value {
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  margin-bottom: var(--spacing-1);
}

.name-card-meta {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

/* Context cards */
.context-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-3);
}

.context-card-export {
  padding: var(--spacing-3) var(--spacing-4);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  background-color: var(--bg-secondary);
}

.context-card-header {
  display: flex;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-2);
  flex-wrap: wrap;
}

.context-card-name {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  margin: 0 0 var(--spacing-2) 0;
}

.context-card-fields {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.field-inline {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.field-label-sm {
  color: var(--text-tertiary);
  font-weight: var(--font-weight-medium);
}

/* Consent cards */
.consent-cards {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.consent-card {
  padding: var(--spacing-3) var(--spacing-4);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  background-color: var(--bg-secondary);
}

.consent-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-2);
  flex-wrap: wrap;
  gap: var(--spacing-2);
}

.consent-client-id {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  background-color: var(--bg-tertiary);
  padding: var(--spacing-1) var(--spacing-2);
  border-radius: var(--radius-sm);
}

.consent-card-fields {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.scopes-list {
  display: inline-flex;
  gap: var(--spacing-1);
  flex-wrap: wrap;
}

.scope-tag {
  font-size: var(--font-size-xs);
  background-color: var(--bg-tertiary);
  color: var(--text-secondary);
  padding: 1px var(--spacing-2);
  border-radius: var(--radius-sm);
}

/* GDPR section */
.gdpr-body {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6);
}

.gdpr-block h3 {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin: 0 0 var(--spacing-2) 0;
}

.gdpr-block p {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin: 0;
}

.gdpr-list {
  margin: 0;
  padding-left: var(--spacing-5);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.retention-grid {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.retention-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--spacing-2) var(--spacing-3);
  background-color: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.retention-key {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  text-transform: capitalize;
}

.retention-value {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

/* Responsive */
@media (max-width: 768px) {
  .export-header {
    flex-direction: column;
    align-items: stretch;
  }

  .export-meta-bar {
    flex-direction: column;
    gap: var(--spacing-2);
  }

  .fields-grid {
    grid-template-columns: 1fr;
  }

  .context-cards {
    grid-template-columns: 1fr;
  }
}
</style>
