<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { authService, getErrorMessage } from '@/services'
import GoogleLoginButton from '@/components/auth/GoogleLoginButton.vue'
import axios from 'axios'

const router = useRouter()
const route = useRoute()
const { t } = useI18n()

const emailInput = ref<HTMLInputElement | null>(null)
const email = ref('')
const password = ref('')
const isLoading = ref(false)
const error = ref<string | null>(null)

// Account deleted state (403 with ACCOUNT_DELETED)
const accountDeleted = ref<{
  deletionScheduledAt: string
  permanentDeletionDate: string
  recoveryInfo: string
} | null>(null)

onMounted(() => {
  emailInput.value?.focus()
})

function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

async function handleSubmit() {
  error.value = null
  accountDeleted.value = null
  isLoading.value = true

  try {
    await authService.login({ email: email.value, password: password.value })

    // Redirect to intended destination or profile
    const redirect = route.query.redirect as string
    router.push(redirect || { name: 'profile' })
  } catch (err) {
    // Handle 403 ACCOUNT_DELETED structured response
    if (
      axios.isAxiosError(err) &&
      err.response?.status === 403 &&
      err.response?.data?.detail?.code === 'ACCOUNT_DELETED'
    ) {
      const detail = err.response.data.detail
      accountDeleted.value = {
        deletionScheduledAt: detail.deletion_scheduled_at,
        permanentDeletionDate: detail.permanent_deletion_date,
        recoveryInfo: detail.recovery_info
      }
    } else {
      error.value = getErrorMessage(err)
    }
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
          <h1>{{ t('auth.login') }}</h1>
          <p class="text-secondary">{{ t('app.tagline') }}</p>
        </div>

        <!-- Account deleted card -->
        <div v-if="accountDeleted" class="deleted-account-card">
          <div class="deleted-icon">!</div>
          <h2>{{ t('auth.restore.accountDeleted') }}</h2>
          <p class="text-secondary">
            {{ t('auth.restore.accountDeletedMessage', { date: formatDate(accountDeleted.permanentDeletionDate) }) }}
          </p>
          <p class="text-secondary mt-2">{{ t('auth.restore.recoveryInstructions') }}</p>
          <router-link to="/restore-account" class="btn btn-primary mt-4">
            {{ t('auth.restore.restoreMyAccount') }}
          </router-link>
          <button class="btn btn-outline mt-2" @click="accountDeleted = null">
            {{ t('auth.restore.backToLogin') }}
          </button>
        </div>

        <template v-else>
          <!-- Social Login Options -->
          <div class="social-login-section">
            <GoogleLoginButton @error="error = $event" />
            <div class="divider">
              <span>{{ t('auth.orContinueWith') }}</span>
            </div>
          </div>

          <form @submit.prevent="handleSubmit">
            <div v-if="error" class="alert alert-error mb-4">
              {{ error }}
            </div>

            <div class="form-group">
              <label for="email">{{ t('auth.email') }}</label>
              <input
                id="email"
                ref="emailInput"
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
                autocomplete="current-password"
                :disabled="isLoading"
              />
            </div>

            <button type="submit" class="btn btn-primary btn-block" :disabled="isLoading">
              <span v-if="isLoading" class="spinner spinner-sm"></span>
              {{ t('auth.signIn') }}
            </button>

            <div class="form-help-link">
              <router-link to="/forgot-password" class="text-sm text-secondary">
                {{ t('auth.forgotPassword') }}
              </router-link>
            </div>
          </form>

          <div class="auth-footer">
            <p class="text-secondary text-sm">
              {{ t('auth.noAccount') }}
              <router-link to="/register">{{ t('auth.register') }}</router-link>
            </p>
          </div>
        </template>
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

.form-help-link {
  text-align: center;
  margin-top: var(--spacing-4);
}

.form-help-link a:hover {
  color: var(--color-primary-600);
}

.auth-footer {
  margin-top: var(--spacing-6);
  text-align: center;
}

.deleted-account-card {
  text-align: center;
  padding: var(--spacing-4);
}

.deleted-account-card h2 {
  font-size: var(--font-size-lg);
  margin-bottom: var(--spacing-2);
}

.deleted-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background-color: var(--color-warning-100);
  color: var(--color-warning-600);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto var(--spacing-4);
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
}

.deleted-account-card .btn {
  display: block;
  width: 100%;
}

.social-login-section {
  margin-bottom: var(--spacing-6);
}

.divider {
  display: flex;
  align-items: center;
  margin: var(--spacing-6) 0;
  color: var(--color-gray-500);
  font-size: var(--font-size-sm);
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background-color: var(--color-gray-300);
}

.divider span {
  padding: 0 var(--spacing-4);
}
</style>
