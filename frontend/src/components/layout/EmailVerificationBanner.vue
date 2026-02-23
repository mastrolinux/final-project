<script setup lang="ts">
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import { useAuthStore } from "@/stores";
import { authService } from "@/services";

const { t } = useI18n();
const authStore = useAuthStore();

const isResending = ref(false);
const resendSuccess = ref(false);

async function handleResend() {
  if (!authStore.userEmail) return;
  isResending.value = true;
  resendSuccess.value = false;
  try {
    await authService.resendVerificationEmail(authStore.userEmail);
    resendSuccess.value = true;
  } catch {
    // Error already handled by API interceptor
  } finally {
    isResending.value = false;
  }
}
</script>

<template>
  <div
    v-if="authStore.isAuthenticated && !authStore.isEmailVerified"
    class="verification-banner"
    role="alert"
  >
    <div class="banner-content">
      <span class="banner-message">
        {{ t("auth.emailVerificationBanner") }}
      </span>
      <button
        class="banner-action"
        :disabled="isResending || resendSuccess"
        @click="handleResend"
      >
        {{
          resendSuccess
            ? t("auth.emailVerificationBannerResent")
            : isResending
              ? t("common.sending")
              : t("auth.emailVerificationBannerResend")
        }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.verification-banner {
  background-color: var(--color-warning-50);
  border-bottom: 1px solid var(--color-warning-200);
  padding: var(--spacing-2) var(--spacing-4);
}

.banner-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-3);
  max-width: var(--container-lg);
  margin: 0 auto;
  flex-wrap: wrap;
}

.banner-message {
  font-size: var(--font-size-sm);
  color: var(--color-warning-800);
}

.banner-action {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-warning-700);
  background: none;
  border: 1px solid var(--color-warning-300);
  border-radius: var(--radius-md);
  padding: var(--spacing-1) var(--spacing-3);
  cursor: pointer;
  font-family: inherit;
  transition:
    background-color var(--transition-fast),
    border-color var(--transition-fast);
  white-space: nowrap;
}

.banner-action:hover:not(:disabled) {
  background-color: var(--color-warning-100);
  border-color: var(--color-warning-400);
}

.banner-action:disabled {
  opacity: 0.7;
  cursor: default;
}
</style>
