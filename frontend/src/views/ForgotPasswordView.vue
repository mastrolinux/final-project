<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { authService, getErrorMessage } from '@/services'

const { t } = useI18n()

const email = ref('')
const isLoading = ref(false)
const isSuccess = ref(false)
const error = ref<string | null>(null)

async function handleSubmit() {
  if (!email.value) return

  isLoading.value = true
  error.value = null

  try {
    await authService.requestPasswordReset(email.value)
    isSuccess.value = true
  } catch (err) {
    error.value = getErrorMessage(err)
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="forgot-password-view">
    <div class="container container-sm">
      <div class="card">
        <div class="card-body">
          <div v-if="isSuccess" class="success-state text-center">
            <div class="success-icon">✉</div>
            <h1>{{ t('auth.checkYourEmail') }}</h1>
            <p class="text-secondary">{{ t('auth.resetEmailSent') }}</p>
            <router-link to="/login" class="btn btn-outline mt-4">
              {{ t('auth.backToLogin') }}
            </router-link>
          </div>

          <template v-else>
            <h1 class="form-title">{{ t('auth.forgotPassword') }}</h1>
            <p class="form-description">{{ t('auth.forgotPasswordMessage') }}</p>

            <form @submit.prevent="handleSubmit" class="auth-form">
              <div v-if="error" class="alert alert-error">
                {{ error }}
              </div>

              <div class="form-group">
                <label for="email" class="form-label">{{ t('auth.email') }}</label>
                <input
                  id="email"
                  v-model="email"
                  type="email"
                  class="form-input"
                  :placeholder="t('auth.emailPlaceholder')"
                  required
                  autocomplete="email"
                />
              </div>

              <button type="submit" class="btn btn-primary btn-block" :disabled="isLoading">
                {{ isLoading ? t('common.sending') : t('auth.sendResetLink') }}
              </button>

              <div class="form-footer">
                <router-link to="/login" class="link">
                  {{ t('auth.backToLogin') }}
                </router-link>
              </div>
            </form>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.forgot-password-view {
  padding: var(--spacing-8) 0;
  min-height: 60vh;
  display: flex;
  align-items: center;
}

.success-state {
  padding: var(--spacing-4);
}

.success-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background-color: var(--color-primary-100);
  color: var(--color-primary-600);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto var(--spacing-4);
  font-size: var(--font-size-2xl);
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

.form-footer {
  text-align: center;
  margin-top: var(--spacing-2);
}
</style>
