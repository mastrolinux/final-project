<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { oauthService, contextService, getErrorMessage } from '@/services'
import { useAuthStore, useProfileStore } from '@/stores'
import type { OAuthClient, OAuthScope, ConsentRequestParams } from '@/types'
import ScopeDisplay from '@/components/oauth/ScopeDisplay.vue'
import ContextSelector from '@/components/oauth/ContextSelector.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseCard from '@/components/common/BaseCard.vue'

const route = useRoute()
const { t } = useI18n()
const authStore = useAuthStore()
const profileStore = useProfileStore()

const isLoading = ref(true)
const isSubmitting = ref(false)
const error = ref<string | null>(null)

const client = ref<OAuthClient | null>(null)
const scopes = ref<OAuthScope[]>([])
const requestParams = ref<ConsentRequestParams | null>(null)
const selectedContextId = ref<string | null>(null)

const hasContexts = computed(() => profileStore.contexts.length > 0)

onMounted(async () => {
  // Validate required parameters
  const { client_id, response_type, redirect_uri, scope, state } = route.query

  if (!client_id || !response_type || !redirect_uri || !scope || !state) {
    error.value = t('oauth.errors.invalid_request')
    isLoading.value = false
    return
  }

  try {
    // 1. Fetch consent details (client info, scopes)
    // We pass all query params to the backend
    const details = await oauthService.getConsentDetails(route.query as Record<string, string>)
    
    client.value = details.client
    scopes.value = details.scopes
    requestParams.value = details.request

    // 2. Fetch user contexts if not already loaded
    const userId = authStore.userId
    if (userId) {
      if (profileStore.contexts.length === 0) {
        const contexts = await contextService.list(userId)
        profileStore.setContexts(contexts)
      }
      
      // Default to first active context or none
      const activeContexts = profileStore.contexts.filter(c => c.is_active)
      if (activeContexts.length > 0) {
        selectedContextId.value = activeContexts[0].id
      }
    }
  } catch (err) {
    error.value = getErrorMessage(err)
  } finally {
    isLoading.value = false
  }
})

async function handleDecision(decision: 'allow' | 'deny') {
  if (!requestParams.value) return

  isSubmitting.value = true
  error.value = null

  try {
    const response = await oauthService.submitConsent({
      client_id: requestParams.value.client_id,
      scope: requestParams.value.scope,
      state: requestParams.value.state,
      redirect_uri: requestParams.value.redirect_uri,
      response_type: requestParams.value.response_type,
      code_challenge: requestParams.value.code_challenge,
      code_challenge_method: requestParams.value.code_challenge_method,
      nonce: requestParams.value.nonce,
      decision,
      context_id: decision === 'allow' ? (selectedContextId.value || undefined) : undefined
    })

    // Redirect user back to the application
    window.location.href = response.redirect_to
  } catch (err) {
    error.value = getErrorMessage(err)
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="oauth-consent-view">
    <div class="container container-sm">
      <!-- Loading State -->
      <div v-if="isLoading" class="loading-state">
        <div class="spinner"></div>
        <p>{{ t('common.loading') }}</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="error-state">
        <BaseCard class="border-error">
          <div class="text-center">
            <h2 class="text-error mb-2">{{ t('oauth.authenticationFailed') }}</h2>
            <p>{{ error }}</p>
            <button class="btn btn-secondary mt-4" @click="$router.push('/')">
              {{ t('common.backToHome') }}
            </button>
          </div>
        </BaseCard>
      </div>

      <!-- Consent Form -->
      <div v-else-if="client" class="consent-form">
        <div class="client-header text-center mb-6">
          <div class="client-logo mb-4" v-if="client.logo_uri">
            <img :src="client.logo_uri" :alt="client.client_name" />
          </div>
          <div class="client-logo-placeholder mb-4" v-else>
            {{ client.client_name.charAt(0).toUpperCase() }}
          </div>
          
          <h1 class="text-xl font-bold mb-2">
            {{ t('oauth.clientWantsAccess', { client: client.client_name }) }}
          </h1>
          
          <div v-if="client.is_first_party" class="badge badge-success inline-flex items-center gap-1">
            <span class="w-2 h-2 rounded-full bg-green-500"></span>
            {{ t('oauth.firstParty') }}
          </div>
        </div>

        <BaseCard class="mb-6">
          <h3 class="font-semibold mb-4">{{ t('oauth.scopes') }}</h3>
          <ScopeDisplay :scopes="scopes" />
        </BaseCard>

        <BaseCard class="mb-6" v-if="hasContexts">
          <h3 class="font-semibold mb-2">{{ t('oauth.selectContext') }}</h3>
          <p class="text-sm text-secondary mb-4">{{ t('oauth.selectContextDescription') }}</p>
          <ContextSelector 
            :contexts="profileStore.contexts" 
            v-model="selectedContextId" 
          />
        </BaseCard>

        <div class="actions flex gap-4">
          <BaseButton 
            variant="secondary" 
            class="flex-1" 
            @click="handleDecision('deny')"
            :disabled="isSubmitting"
          >
            {{ t('oauth.deny') }}
          </BaseButton>
          
          <BaseButton 
            variant="primary" 
            class="flex-1" 
            @click="handleDecision('allow')"
            :loading="isSubmitting"
          >
            {{ t('oauth.authorize') }}
          </BaseButton>
        </div>
        
        <div class="text-center mt-6 text-xs text-secondary">
          <p v-if="client.client_uri">
            <a :href="client.client_uri" target="_blank" class="link">{{ t('oauth.visitClientWebsite') }}</a>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.oauth-consent-view {
  min-height: 100vh;
  display: flex;
  align-items: center;
  padding: var(--spacing-4) 0;
  background-color: var(--bg-secondary);
}

.client-logo {
  width: 80px;
  height: 80px;
  margin: 0 auto;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background-color: white;
  box-shadow: var(--shadow-sm);
}

.client-logo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.client-logo-placeholder {
  width: 80px;
  height: 80px;
  margin: 0 auto;
  border-radius: var(--radius-lg);
  background-color: var(--color-primary-100);
  color: var(--color-primary-600);
  font-size: 32px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-sm);
}

.loading-state {
  text-align: center;
  padding: var(--spacing-8);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-gray-200);
  border-top-color: var(--color-primary-600);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto var(--spacing-4);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.border-error {
  border-color: var(--color-error-200);
}

.text-error {
  color: var(--color-error-600);
}

.link {
  color: var(--text-secondary);
  text-decoration: underline;
}

.link:hover {
  color: var(--color-primary-600);
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-2) var(--spacing-4);
  border-radius: var(--radius-md);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary {
  background-color: white;
  color: var(--color-gray-700);
  border: 1px solid var(--color-gray-300);
}

.btn-secondary:hover {
  background-color: var(--color-gray-50);
}
</style>
