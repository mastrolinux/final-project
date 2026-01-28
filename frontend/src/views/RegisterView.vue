<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { authService, getErrorMessage } from '@/services'
import { useUiStore } from '@/stores'
import type { AccountType } from '@/types'

const { t } = useI18n()
const uiStore = useUiStore()

const preferredNameInput = ref<HTMLInputElement | null>(null)
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const preferredName = ref('')
const accountType = ref<AccountType>('unverified')
const isLoading = ref(false)
const error = ref<string | null>(null)
const success = ref(false)

onMounted(() => {
  preferredNameInput.value?.focus()
})

async function handleSubmit() {
  error.value = null

  if (password.value !== confirmPassword.value) {
    error.value = 'Passwords do not match'
    return
  }

  isLoading.value = true

  try {
    await authService.register({
      email: email.value,
      password: password.value,
      preferred_name: preferredName.value,
      account_type: accountType.value
    })

    success.value = true
    uiStore.showSuccess('Account created! Please check your email to verify your account.')
  } catch (err) {
    error.value = getErrorMessage(err)
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="auth-layout">
    <div class="auth-card card">
      <div class="card-body">
        <div class="auth-header">
          <h1>{{ t('auth.register') }}</h1>
          <p class="text-secondary">{{ t('app.tagline') }}</p>
        </div>

        <div v-if="success" class="alert alert-success">
          <p><strong>Account created successfully!</strong></p>
          <p>Please check your email to verify your account.</p>
          <router-link to="/login" class="btn btn-primary mt-4">
            {{ t('auth.signIn') }}
          </router-link>
        </div>

        <form v-else @submit.prevent="handleSubmit">
          <div v-if="error" class="alert alert-error mb-4">
            {{ error }}
          </div>

          <div class="form-group">
            <label for="preferredName">{{ t('auth.preferredName') }}</label>
            <input
              id="preferredName"
              ref="preferredNameInput"
              v-model="preferredName"
              type="text"
              required
              autocomplete="name"
              :disabled="isLoading"
            />
          </div>

          <div class="form-group">
            <label for="email">{{ t('auth.email') }}</label>
            <input
              id="email"
              v-model="email"
              type="email"
              required
              autocomplete="email"
              :disabled="isLoading"
            />
          </div>

          <div class="form-group">
            <label for="password">{{ t('auth.password') }}</label>
            <input
              id="password"
              v-model="password"
              type="password"
              required
              minlength="8"
              autocomplete="new-password"
              :disabled="isLoading"
            />
            <p class="form-hint">Minimum 8 characters with uppercase, lowercase, and number</p>
          </div>

          <div class="form-group">
            <label for="confirmPassword">{{ t('auth.confirmPassword') }}</label>
            <input
              id="confirmPassword"
              v-model="confirmPassword"
              type="password"
              required
              autocomplete="new-password"
              :disabled="isLoading"
            />
          </div>

          <div class="form-group">
            <label>{{ t('auth.accountType.label') }}</label>
            <div class="radio-group">
              <label class="radio-label">
                <input type="radio" v-model="accountType" value="unverified" :disabled="isLoading" />
                <span>{{ t('auth.accountType.unverified') }}</span>
              </label>
              <label class="radio-label">
                <input
                  type="radio"
                  v-model="accountType"
                  value="pseudonymous"
                  :disabled="isLoading"
                />
                <span>{{ t('auth.accountType.pseudonymous') }}</span>
              </label>
            </div>
          </div>

          <button type="submit" class="btn btn-primary btn-block" :disabled="isLoading">
            <span v-if="isLoading" class="spinner spinner-sm"></span>
            {{ t('auth.createAccount') }}
          </button>
        </form>

        <div class="auth-footer" v-if="!success">
          <p class="text-secondary text-sm">
            {{ t('auth.hasAccount') }}
            <router-link to="/login">{{ t('auth.login') }}</router-link>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-header {
  text-align: center;
  margin-bottom: var(--spacing-8);
}

.auth-header h1 {
  margin-bottom: var(--spacing-3);
}

.btn-block {
  width: 100%;
}

.auth-footer {
  margin-top: var(--spacing-6);
  text-align: center;
}

.radio-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.radio-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  cursor: pointer;
  font-weight: var(--font-weight-normal);
  margin-bottom: 0;
  padding: var(--spacing-2);
  border-radius: var(--radius-md);
  transition: background-color var(--transition-fast);
}

.radio-label:hover {
  background-color: var(--bg-secondary);
}

.radio-label:focus-within {
  outline: 2px solid var(--color-primary-500);
  outline-offset: -2px;
}

.radio-label input[type='radio'] {
  width: auto;
  accent-color: var(--color-primary-600);
}
</style>
