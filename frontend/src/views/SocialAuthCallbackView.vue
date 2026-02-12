<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { authService, getErrorMessage } from '@/services'
import { useUiStore } from '@/stores'
import axios from 'axios'

const router = useRouter()
const route = useRoute()
const { t } = useI18n()
const uiStore = useUiStore()

const isProcessing = ref(true)
const error = ref<string | null>(null)
const accountLinkingRequired = ref(false)

onMounted(async () => {
  try {
    // Extract OAuth callback parameters from URL
    const code = route.query.code as string
    const state = route.query.state as string

    // Retrieve stored PKCE values from sessionStorage
    const storedCodeVerifier = sessionStorage.getItem('social_oauth_code_verifier')
    const storedState = sessionStorage.getItem('social_oauth_state')

    // Validate required parameters
    if (!code || !state) {
      error.value = t('auth.social.invalidCallback')
      isProcessing.value = false
      return
    }

    if (!storedCodeVerifier || !storedState) {
      error.value = t('auth.social.sessionExpired')
      isProcessing.value = false
      return
    }

    // Extract provider from path (e.g., /auth/social/google/callback)
    const provider = route.params.provider as string
    if (!provider) {
      error.value = t('auth.social.missingProvider')
      isProcessing.value = false
      return
    }

    // Exchange authorization code for tokens
    await authService.handleOAuthCallback({
      provider,
      code,
      state,
      code_verifier: storedCodeVerifier,
      expected_state: storedState
    })

    // Clear stored OAuth session data
    sessionStorage.removeItem('social_oauth_code_verifier')
    sessionStorage.removeItem('social_oauth_state')

    // Show success notification
    uiStore.addNotification({
      type: 'success',
      message: t('auth.social.loginSuccess')
    })

    // Redirect to intended destination or profile
    const redirect = sessionStorage.getItem('social_oauth_redirect')
    sessionStorage.removeItem('social_oauth_redirect')
    router.push(redirect || { name: 'profile' })
  } catch (err) {
    isProcessing.value = false

    // Handle account linking error (409 CONFLICT)
    if (
      axios.isAxiosError(err) &&
      err.response?.status === 409 &&
      err.response?.data?.detail?.code === 'account_linking_required'
    ) {
      accountLinkingRequired.value = true
      error.value = err.response.data.detail.message
    } else {
      error.value = getErrorMessage(err)
    }

    // Clear OAuth session data on error
    sessionStorage.removeItem('social_oauth_code_verifier')
    sessionStorage.removeItem('social_oauth_state')
  }
})
</script>

<template>
  <div class="auth-layout">
    <div class="auth-card card">
      <div class="card-body">
        <div v-if="isProcessing" class="processing-state">
          <div class="spinner-large"></div>
          <h2>{{ t('auth.social.completing') }}</h2>
          <p class="text-secondary">{{ t('auth.social.processingMessage') }}</p>
        </div>

        <div v-else-if="accountLinkingRequired" class="error-state">
          <div class="error-icon warning">!</div>
          <h2>{{ t('auth.social.accountLinkingRequired') }}</h2>
          <p class="text-secondary">{{ error }}</p>
          <div class="actions">
            <router-link to="/login" class="btn btn-primary">
              {{ t('auth.social.signInWithPassword') }}
            </router-link>
            <p class="text-secondary text-sm mt-4">
              {{ t('auth.social.accountLinkingInfo') }}
            </p>
          </div>
        </div>

        <div v-else class="error-state">
          <div class="error-icon">×</div>
          <h2>{{ t('auth.social.authenticationFailed') }}</h2>
          <p class="text-secondary">{{ error }}</p>
          <router-link to="/login" class="btn btn-primary mt-4">
            {{ t('auth.social.backToLogin') }}
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.processing-state,
.error-state {
  text-align: center;
  padding: var(--spacing-6) var(--spacing-4);
}

.processing-state h2,
.error-state h2 {
  margin: var(--spacing-4) 0 var(--spacing-2);
  font-size: var(--font-size-xl);
}

.spinner-large {
  display: inline-block;
  width: 48px;
  height: 48px;
  border: 4px solid var(--color-gray-200);
  border-top-color: var(--color-primary-500);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background-color: var(--color-error-100);
  color: var(--color-error-600);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto var(--spacing-4);
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
}

.error-icon.warning {
  background-color: var(--color-warning-100);
  color: var(--color-warning-600);
}

.actions {
  margin-top: var(--spacing-6);
}

.actions .btn {
  min-width: 200px;
}
</style>
