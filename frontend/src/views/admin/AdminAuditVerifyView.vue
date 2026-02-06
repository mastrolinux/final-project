<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { getErrorMessage } from '@/services'
import auditService from '@/services/audit.service'
import type { AuditIntegrityResponse } from '@/types'
import BaseCard from '@/components/common/BaseCard.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseInput from '@/components/common/BaseInput.vue'
import {
  ArrowLeftIcon,
  ShieldCheckIcon,
  ExclamationTriangleIcon
} from '@heroicons/vue/24/outline'

const router = useRouter()
const { t } = useI18n()

const verifyLimit = ref('1000')
const isVerifying = ref(false)
const error = ref<string | null>(null)
const result = ref<AuditIntegrityResponse | null>(null)
const hasRun = ref(false)

async function runVerification() {
  const limitNum = parseInt(verifyLimit.value, 10)
  if (isNaN(limitNum) || limitNum < 1 || limitNum > 10000) {
    error.value = t('audit.verify.limitError')
    return
  }

  isVerifying.value = true
  error.value = null
  result.value = null
  hasRun.value = false

  try {
    result.value = await auditService.verifyIntegrity(limitNum)
    hasRun.value = true
  } catch (err) {
    error.value = getErrorMessage(err)
  } finally {
    isVerifying.value = false
  }
}

function goBack() {
  router.push({ name: 'admin-oauth-clients' })
}
</script>

<template>
  <div class="admin-audit-verify-view">
    <div class="container container-lg">
      <button type="button" class="back-link" @click="goBack">
        <ArrowLeftIcon class="back-icon" />
        {{ t('audit.verify.backToAdmin') }}
      </button>

      <div class="page-header">
        <h1 class="page-title">{{ t('audit.verify.title') }}</h1>
        <p class="page-description">{{ t('audit.verify.description') }}</p>
      </div>

      <!-- Verification Controls -->
      <BaseCard>
        <div class="verify-controls">
          <div class="control-row">
            <BaseInput
              v-model="verifyLimit"
              id="verify_limit"
              type="number"
              :label="t('audit.verify.entriesLabel')"
              :hint="t('audit.verify.entriesHint')"
              class="limit-input"
            />
            <BaseButton
              variant="primary"
              :loading="isVerifying"
              @click="runVerification"
            >
              {{ isVerifying ? t('audit.verify.verifying') : t('audit.verify.runButton') }}
            </BaseButton>
          </div>
        </div>
      </BaseCard>

      <!-- Error -->
      <div v-if="error" class="alert alert-error result-alert">{{ error }}</div>

      <!-- Results -->
      <BaseCard v-if="hasRun && result" class="result-card">
        <div class="result-content">
          <div class="result-icon-wrapper" :class="result.is_valid ? 'result-valid' : 'result-invalid'">
            <ShieldCheckIcon v-if="result.is_valid" class="result-icon" />
            <ExclamationTriangleIcon v-else class="result-icon" />
          </div>

          <h2 class="result-title" :class="result.is_valid ? 'text-success' : 'text-error'">
            {{ result.is_valid ? t('audit.verify.chainValid') : t('audit.verify.chainInvalid') }}
          </h2>

          <div class="result-meta">
            <div class="result-stat">
              <span class="stat-label">{{ t('audit.verify.entriesVerified') }}</span>
              <span class="stat-value">{{ result.entries_verified }}</span>
            </div>
          </div>

          <div v-if="result.error_message" class="error-details">
            <h3 class="error-details-title">{{ t('audit.verify.errorDetails') }}</h3>
            <pre class="error-details-content">{{ result.error_message }}</pre>
          </div>

          <p v-if="result.is_valid" class="result-explanation">
            {{ t('audit.verify.validExplanation', { count: result.entries_verified }) }}
          </p>
          <p v-else class="result-explanation result-explanation-error">
            {{ t('audit.verify.invalidExplanation') }}
          </p>
        </div>
      </BaseCard>
    </div>
  </div>
</template>

<style scoped>
.admin-audit-verify-view {
  padding: var(--spacing-8) 0;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-2);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--spacing-1) 0;
  margin-bottom: var(--spacing-4);
  transition: color var(--transition-fast);
}

.back-link:hover {
  color: var(--text-primary);
}

.back-icon {
  width: 16px;
  height: 16px;
}

.verify-controls {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.control-row {
  display: flex;
  align-items: flex-end;
  gap: var(--spacing-4);
}

.limit-input {
  flex: 1;
  max-width: 200px;
}

.result-alert {
  margin-top: var(--spacing-4);
}

.result-card {
  margin-top: var(--spacing-4);
}

.result-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: var(--spacing-4);
  padding: var(--spacing-4) 0;
}

.result-icon-wrapper {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
}

.result-icon {
  width: 36px;
  height: 36px;
}

.result-valid {
  background-color: var(--color-success-50);
  color: var(--color-success-600);
}

.result-invalid {
  background-color: var(--color-error-50);
  color: var(--color-error-600);
}

.result-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  margin: 0;
}

.text-success {
  color: var(--color-success-700);
}

.text-error {
  color: var(--color-error-700);
}

.result-meta {
  display: flex;
  gap: var(--spacing-8);
}

.result-stat {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.stat-label {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
}

.stat-value {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
}

.error-details {
  width: 100%;
  text-align: left;
  margin-top: var(--spacing-2);
}

.error-details-title {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-error-700);
  margin: 0 0 var(--spacing-2);
}

.error-details-content {
  padding: var(--spacing-3);
  background-color: var(--color-error-50);
  border: 1px solid var(--color-error-200, var(--border-primary));
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  font-family: var(--font-family-mono);
  color: var(--color-error-800);
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.result-explanation {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  max-width: 480px;
  margin: 0;
}

.result-explanation-error {
  color: var(--color-error-700);
}
</style>
