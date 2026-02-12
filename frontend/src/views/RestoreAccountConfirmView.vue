<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { authService, getErrorMessage } from '@/services'
import axios from 'axios'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const token = ref('')
const password = ref('')
const confirmPassword = ref('')
const isLoading = ref(false)
const isSuccess = ref(false)
const error = ref<string | null>(null)
const validationError = ref<string | null>(null)
const errorType = ref<string | null>(null)
const isOAuthUser = ref(false)
const showPasswordForm = ref(false)

onMounted(async () => {
  token.value = (route.query.token as string) || ''
  if (!token.value) {
    error.value = t('auth.restore.invalidTokenMessage')
    errorType.value = 'INVALID_RESTORATION_TOKEN'
    return
  }

  // Try to restore without password first (for OAuth users)
  // If it's an email/password user, we'll get PASSWORD_REQUIRED error
  await attemptOAuthRestore()
})

async function attemptOAuthRestore() {
  isLoading.value = true
  error.value = null

  try {
    // Attempt restoration without password (for OAuth users)
    await authService.confirmAccountRestoration(token.value)
    isSuccess.value = true
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.data?.detail) {
      const detail = err.response.data.detail
      if (typeof detail === 'object' && detail.code) {
        if (detail.code === 'PASSWORD_REQUIRED') {
          // This is an email/password user, show password form
          showPasswordForm.value = true
        } else if (detail.code === 'ACCOUNT_PERMANENTLY_DELETED') {
          errorType.value = detail.code
          error.value = t('auth.restore.permanentlyDeletedMessage')
        } else if (detail.code === 'INVALID_RESTORATION_TOKEN') {
          errorType.value = detail.code
          error.value = t('auth.restore.invalidTokenMessage')
        } else {
          error.value = detail.detail || getErrorMessage(err)
        }
      } else {
        error.value = getErrorMessage(err)
      }
    } else {
      error.value = getErrorMessage(err)
    }
  } finally {
    isLoading.value = false
  }
}

function validatePassword(): boolean {
  validationError.value = null

  if (password.value.length < 8) {
    validationError.value = t('auth.passwordTooShort')
    return false
  }

  if (password.value !== confirmPassword.value) {
    validationError.value = t('auth.passwordsDoNotMatch')
    return false
  }

  return true
}

async function handleSubmit() {
  if (!validatePassword()) return

  isLoading.value = true
  error.value = null
  errorType.value = null

  try {
    await authService.confirmAccountRestoration(token.value, password.value)
    isSuccess.value = true
  } catch (err) {
    // Parse structured error responses from backend
    if (axios.isAxiosError(err) && err.response?.data?.detail) {
      const detail = err.response.data.detail
      if (typeof detail === 'object' && detail.code) {
        errorType.value = detail.code
        if (detail.code === 'ACCOUNT_PERMANENTLY_DELETED') {
          error.value = t('auth.restore.permanentlyDeletedMessage')
        } else if (detail.code === 'INVALID_RESTORATION_TOKEN') {
          error.value = t('auth.restore.invalidTokenMessage')
        } else {
          error.value = detail.detail || getErrorMessage(err)
        }
      } else {
        error.value = getErrorMessage(err)
      }
    } else {
      error.value = getErrorMessage(err)
    }
  } finally {
    isLoading.value = false
  }
}

function goToLogin() {
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="restore-confirm-view">
    <div class="container container-sm">
      <div class="card">
        <div class="card-body">
          <!-- Success state -->
          <div v-if="isSuccess" class="success-state text-center">
            <div class="success-icon">&#x2713;</div>
            <h1>{{ t('auth.restore.confirmSuccess') }}</h1>
            <p class="text-secondary">{{ t('auth.restore.confirmSuccessMessage') }}</p>
            <button class="btn btn-primary mt-4" @click="goToLogin">
              {{ t('auth.goToLogin') }}
            </button>
          </div>

          <!-- Permanently deleted state -->
          <template v-else-if="errorType === 'ACCOUNT_PERMANENTLY_DELETED'">
            <div class="error-state text-center">
              <div class="error-icon">!</div>
              <h1>{{ t('auth.restore.permanentlyDeleted') }}</h1>
              <p class="text-secondary">{{ t('auth.restore.permanentlyDeletedMessage') }}</p>
              <router-link to="/register" class="btn btn-primary mt-4">
                {{ t('auth.register') }}
              </router-link>
            </div>
          </template>

          <!-- Invalid/missing token state -->
          <template v-else-if="!token || errorType === 'INVALID_RESTORATION_TOKEN'">
            <div class="error-state text-center">
              <div class="error-icon">!</div>
              <h1>{{ t('auth.restore.invalidToken') }}</h1>
              <p class="text-secondary">{{ t('auth.restore.invalidTokenMessage') }}</p>
              <router-link to="/restore-account" class="btn btn-outline mt-4">
                {{ t('auth.restore.requestNewToken') }}
              </router-link>
            </div>
          </template>

          <!-- Loading state -->
          <template v-else-if="isLoading && !showPasswordForm">
            <div class="loading-state text-center">
              <div class="spinner-large"></div>
              <h2>{{ t('auth.restore.restoring') }}</h2>
              <p class="text-secondary">{{ t('auth.restore.restoringMessage') }}</p>
            </div>
          </template>

          <!-- Password form (only for email/password users) -->
          <template v-else-if="showPasswordForm">
            <h1 class="form-title">{{ t('auth.restore.confirmTitle') }}</h1>
            <p class="form-description">{{ t('auth.restore.confirmDescription') }}</p>

            <form @submit.prevent="handleSubmit" class="auth-form">
              <div v-if="error" class="alert alert-error">
                {{ error }}
              </div>

              <div v-if="validationError" class="alert alert-warning">
                {{ validationError }}
              </div>

              <div class="form-group">
                <label for="password" class="form-label">{{ t('auth.newPassword') }}</label>
                <input
                  id="password"
                  v-model="password"
                  type="password"
                  class="form-input"
                  :placeholder="t('auth.passwordPlaceholder')"
                  required
                  minlength="8"
                  autocomplete="new-password"
                />
                <p class="form-hint">Minimum 8 characters with uppercase, lowercase, and number</p>
              </div>

              <div class="form-group">
                <label for="confirm-password" class="form-label">{{
                  t('auth.confirmPassword')
                }}</label>
                <input
                  id="confirm-password"
                  v-model="confirmPassword"
                  type="password"
                  class="form-input"
                  :placeholder="t('auth.confirmPasswordPlaceholder')"
                  required
                  autocomplete="new-password"
                />
              </div>

              <button type="submit" class="btn btn-primary btn-block" :disabled="isLoading">
                {{ isLoading ? t('common.saving') : t('auth.restore.title') }}
              </button>
            </form>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.restore-confirm-view {
  padding: var(--spacing-8) 0;
  min-height: 60vh;
  display: flex;
  align-items: center;
}

.success-state,
.error-state {
  padding: var(--spacing-4);
}

.success-icon,
.error-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto var(--spacing-4);
  font-size: var(--font-size-2xl);
}

.success-icon {
  background-color: var(--color-success-100);
  color: var(--color-success-600);
}

.error-icon {
  background-color: var(--color-error-100);
  color: var(--color-error-600);
}

.form-title {
  font-size: var(--font-size-xl);
  margin-bottom: var(--spacing-2);
}

.form-description {
  color: var(--text-secondary);
  margin-bottom: var(--spacing-6);
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.loading-state {
  padding: var(--spacing-6) var(--spacing-4);
}

.spinner-large {
  display: inline-block;
  width: 48px;
  height: 48px;
  border: 4px solid var(--color-gray-200);
  border-top-color: var(--color-primary-500);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: var(--spacing-4);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
