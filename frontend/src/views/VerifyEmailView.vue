<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useAuthStore } from "@/stores";
import { authService, getErrorMessage } from "@/services";

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const isLoading = ref(false);
const isVerified = ref(false);
const error = ref<string | null>(null);
const isResending = ref(false);
const resendSuccess = ref(false);

onMounted(async () => {
  const token = route.query.token as string;
  if (token) {
    await verifyEmail(token);
  }
});

async function verifyEmail(token: string) {
  isLoading.value = true;
  error.value = null;

  try {
    await authService.verifyEmail(token);
    isVerified.value = true;
    authStore.setEmailVerified(true);
  } catch (err) {
    error.value = getErrorMessage(err);
  } finally {
    isLoading.value = false;
  }
}

async function resendVerification() {
  if (!authStore.userEmail) return;

  isResending.value = true;
  error.value = null;
  resendSuccess.value = false;

  try {
    await authService.resendVerificationEmail(authStore.userEmail);
    resendSuccess.value = true;
  } catch (err) {
    error.value = getErrorMessage(err);
  } finally {
    isResending.value = false;
  }
}

function goToProfile() {
  router.push({ name: "profile" });
}
</script>

<template>
  <div class="verify-email-view">
    <div class="container container-sm">
      <div class="card">
        <div class="card-body text-center">
          <div v-if="isLoading" class="loading-state">
            <div class="spinner"></div>
            <p>{{ t("auth.verifyingEmail") }}</p>
          </div>

          <div v-else-if="isVerified" class="success-state">
            <div class="success-icon">✓</div>
            <h1>{{ t("auth.emailVerified") }}</h1>
            <p class="text-secondary">{{ t("auth.emailVerifiedMessage") }}</p>
            <button class="btn btn-primary mt-4" @click="goToProfile">
              {{ t("auth.goToProfile") }}
            </button>
          </div>

          <div v-else-if="error" class="error-state">
            <div class="error-icon">!</div>
            <h1>{{ t("auth.verificationFailed") }}</h1>
            <p class="text-secondary">{{ error }}</p>
          </div>

          <div v-else class="pending-state">
            <div class="pending-icon">✉</div>
            <h1>{{ t("auth.verifyYourEmail") }}</h1>
            <p class="text-secondary">{{ t("auth.verifyEmailMessage") }}</p>

            <div v-if="resendSuccess" class="alert alert-success mt-4">
              {{ t("auth.verificationEmailSent") }}
            </div>

            <button
              v-if="authStore.userEmail"
              class="btn btn-outline mt-4"
              :disabled="isResending"
              @click="resendVerification"
            >
              {{
                isResending ? t("common.sending") : t("auth.resendVerification")
              }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.verify-email-view {
  padding: var(--spacing-8) 0;
  min-height: 60vh;
  display: flex;
  align-items: center;
}

.loading-state,
.success-state,
.error-state,
.pending-state {
  padding: var(--spacing-8);
}

.success-icon,
.error-icon,
.pending-icon {
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

.pending-icon {
  background-color: var(--color-primary-100);
  color: var(--color-primary-600);
}

h1 {
  font-size: var(--font-size-xl);
  margin-bottom: var(--spacing-2);
}
</style>
