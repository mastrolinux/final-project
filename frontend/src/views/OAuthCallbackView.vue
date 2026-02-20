<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useAuthStore, useUiStore } from "@/stores";
import { authService, getErrorMessage } from "@/services";

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const uiStore = useUiStore();

const isProcessing = ref(true);
const error = ref<string | null>(null);

onMounted(async () => {
  await handleCallback();
});

async function handleCallback() {
  const code = route.query.code as string;
  const state = route.query.state as string;
  const errorParam = route.query.error as string;
  const errorDescription = route.query.error_description as string;

  // Check for OAuth error response
  if (errorParam) {
    error.value =
      errorDescription || t(`oauth.errors.${errorParam}`, errorParam);
    isProcessing.value = false;
    return;
  }

  // Validate required parameters
  if (!code) {
    error.value = t("oauth.errors.missingCode");
    isProcessing.value = false;
    return;
  }

  // Retrieve and validate state from session storage
  const storedState = sessionStorage.getItem("oauth_state");
  const storedCodeVerifier = sessionStorage.getItem("oauth_code_verifier");
  const storedRedirectUri = sessionStorage.getItem("oauth_redirect_uri");

  if (state && storedState && state !== storedState) {
    error.value = t("oauth.errors.stateMismatch");
    isProcessing.value = false;
    return;
  }

  try {
    // Exchange authorization code for tokens
    const response = await authService.exchangeOAuthCode({
      code,
      code_verifier: storedCodeVerifier || undefined,
      redirect_uri:
        storedRedirectUri || window.location.origin + "/oauth/callback",
    });

    // Store authentication data
    authStore.setTokens(response.access_token, response.refresh_token);
    authStore.setUser(response);

    // Clean up session storage
    sessionStorage.removeItem("oauth_state");
    sessionStorage.removeItem("oauth_code_verifier");
    sessionStorage.removeItem("oauth_redirect_uri");

    // Redirect to intended destination or profile
    const redirectTo =
      sessionStorage.getItem("oauth_redirect_to") || "/profile";
    sessionStorage.removeItem("oauth_redirect_to");

    uiStore.addNotification({
      type: "success",
      message: t("auth.loginSuccess"),
    });

    router.push(redirectTo);
  } catch (err) {
    error.value = getErrorMessage(err);
    isProcessing.value = false;
  }
}

function goToLogin() {
  router.push({ name: "login" });
}
</script>

<template>
  <div class="oauth-callback-view">
    <div class="container container-sm">
      <div class="card">
        <div class="card-body text-center">
          <div v-if="isProcessing" class="processing-state">
            <div class="spinner spinner-lg"></div>
            <h1>{{ t("oauth.processing") }}</h1>
            <p class="text-secondary">{{ t("oauth.processingMessage") }}</p>
          </div>

          <div v-else-if="error" class="error-state">
            <div class="error-icon">!</div>
            <h1>{{ t("oauth.authenticationFailed") }}</h1>
            <p class="text-secondary">{{ error }}</p>
            <button class="btn btn-primary mt-4" @click="goToLogin">
              {{ t("auth.tryAgain") }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.oauth-callback-view {
  padding: var(--spacing-8) 0;
  min-height: 60vh;
  display: flex;
  align-items: center;
}

.processing-state,
.error-state {
  padding: var(--spacing-8);
}

.spinner-lg {
  width: 48px;
  height: 48px;
  margin: 0 auto var(--spacing-6);
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
  font-size: var(--font-size-2xl);
  font-weight: bold;
}

h1 {
  font-size: var(--font-size-xl);
  margin-bottom: var(--spacing-2);
}
</style>
