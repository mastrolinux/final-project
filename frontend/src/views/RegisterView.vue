<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { authService, getErrorMessage } from "@/services";
import { useUiStore } from "@/stores";
import type { AccountType } from "@/types";
import axios from "axios";
import GoogleLoginButton from "@/components/auth/GoogleLoginButton.vue";

const { t } = useI18n();
const uiStore = useUiStore();

const preferredNameInput = ref<HTMLInputElement | null>(null);
const email = ref("");
const password = ref("");
const confirmPassword = ref("");
const preferredName = ref("");
const accountType = ref<AccountType>("unverified");
const isLoading = ref(false);
const error = ref<string | null>(null);
const success = ref(false);

// Account recoverable state (409 with ACCOUNT_RECOVERABLE)
const accountRecoverable = ref<{
  permanentDeletionDate: string;
} | null>(null);

onMounted(() => {
  preferredNameInput.value?.focus();
});

function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

async function handleSubmit() {
  error.value = null;
  accountRecoverable.value = null;

  if (password.value !== confirmPassword.value) {
    error.value = "Passwords do not match";
    return;
  }

  isLoading.value = true;

  try {
    await authService.register({
      email: email.value,
      password: password.value,
      preferred_name: preferredName.value,
      account_type: accountType.value,
    });

    success.value = true;
    uiStore.showSuccess(t("auth.registerSuccessToast"));
  } catch (err) {
    // Handle 409 ACCOUNT_RECOVERABLE structured response
    if (
      axios.isAxiosError(err) &&
      err.response?.status === 409 &&
      err.response?.data?.detail?.code === "ACCOUNT_RECOVERABLE"
    ) {
      const detail = err.response.data.detail;
      accountRecoverable.value = {
        permanentDeletionDate: detail.permanent_deletion_date,
      };
    } else {
      error.value = getErrorMessage(err);
    }
  } finally {
    isLoading.value = false;
  }
}
</script>

<template>
  <div class="auth-layout">
    <div class="auth-card card">
      <div class="card-body">
        <div class="auth-header">
          <h1>{{ t("auth.register") }}</h1>
          <p class="text-secondary" v-html="t('app.tagline')"></p>
        </div>

        <!-- Account recoverable card -->
        <div v-if="accountRecoverable" class="recoverable-card">
          <div class="recoverable-icon">!</div>
          <h2>{{ t("auth.restore.accountRecoverable") }}</h2>
          <p class="text-secondary">
            {{
              t("auth.restore.accountRecoverableMessage", {
                date: formatDate(accountRecoverable.permanentDeletionDate),
              })
            }}
          </p>
          <router-link to="/restore-account" class="btn btn-primary mt-4">
            {{ t("auth.restore.restoreAccount") }}
          </router-link>
          <button
            class="btn btn-outline mt-2"
            @click="accountRecoverable = null"
          >
            {{ t("auth.restore.backToLogin") }}
          </button>
        </div>

        <div v-else-if="success" class="alert alert-success">
          <p><strong>{{ t("auth.registerSuccessTitle") }}</strong></p>
          <p>{{ t("auth.registerSuccessMessage") }}</p>
          <router-link to="/login" class="btn btn-primary mt-4">
            {{ t("auth.signIn") }}
          </router-link>
        </div>

        <template v-else>
          <!-- Social registration section -->
          <div class="social-register-section">
            <GoogleLoginButton @error="error = $event" />
            <div class="divider">
              <span>{{ t("auth.orContinueWith") }}</span>
            </div>
          </div>

          <form @submit.prevent="handleSubmit">
            <div v-if="error" class="alert alert-error mb-4">
              {{ error }}
            </div>

            <div class="form-group">
              <label for="preferredName">{{ t("auth.preferredName") }}</label>
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
              <label for="email">{{ t("auth.email") }}</label>
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
              <label for="password">{{ t("auth.password") }}</label>
              <input
                id="password"
                v-model="password"
                type="password"
                required
                minlength="8"
                autocomplete="new-password"
                :disabled="isLoading"
              />
              <p class="form-hint">
                Minimum 8 characters. Avoid common passwords.
              </p>
            </div>

            <div class="form-group">
              <label for="confirmPassword">{{
                t("auth.confirmPassword")
              }}</label>
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
              <label>{{ t("auth.accountType.label") }}</label>
              <div class="radio-group">
                <label class="radio-label">
                  <input
                    type="radio"
                    v-model="accountType"
                    value="unverified"
                    :disabled="isLoading"
                  />
                  <div class="radio-content">
                    <span>{{ t("auth.accountType.unverified") }}</span>
                    <small class="radio-description">{{ t("auth.accountType.unverifiedDescription") }}</small>
                  </div>
                </label>
                <label class="radio-label">
                  <input
                    type="radio"
                    v-model="accountType"
                    value="pseudonymous"
                    :disabled="isLoading"
                  />
                  <div class="radio-content">
                    <span>{{ t("auth.accountType.pseudonymous") }}</span>
                    <small class="radio-description">{{ t("auth.accountType.pseudonymousDescription") }}</small>
                  </div>
                </label>
              </div>
            </div>

            <button
              type="submit"
              class="btn btn-primary btn-block"
              :disabled="isLoading"
            >
              <span v-if="isLoading" class="spinner spinner-sm"></span>
              {{ t("auth.createAccount") }}
            </button>
          </form>

          <div class="auth-footer">
            <p class="text-secondary text-sm">
              {{ t("auth.hasAccount") }}
              <router-link to="/login">{{ t("auth.login") }}</router-link>
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

.social-register-section {
  margin-bottom: var(--spacing-6);
}

.divider {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  height: auto;
  background-color: transparent;
  margin: var(--spacing-6) 0;
  color: var(--color-gray-500);
  font-size: var(--font-size-sm);
}

.divider::before,
.divider::after {
  content: "";
  flex: 1;
  border-bottom: 1px solid var(--color-gray-300);
}

.divider span {
  padding: 0 var(--spacing-3);
  white-space: nowrap;
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
  align-items: flex-start;
  gap: var(--spacing-2);
  cursor: pointer;
  font-weight: var(--font-weight-normal);
  margin-bottom: 0;
  padding: var(--spacing-2);
  border-radius: var(--radius-md);
  transition: background-color var(--transition-fast);
}

.radio-content {
  display: flex;
  flex-direction: column;
}

.radio-description {
  display: block;
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  margin-top: 2px;
}

.radio-label:hover {
  background-color: var(--bg-secondary);
}

.radio-label:focus-within {
  outline: 2px solid var(--color-primary-500);
  outline-offset: -2px;
}

.radio-label input[type="radio"] {
  width: auto;
  margin-top: 3px;
  accent-color: var(--color-primary-600);
}

.recoverable-card {
  text-align: center;
  padding: var(--spacing-4);
}

.recoverable-card h2 {
  font-size: var(--font-size-lg);
  margin-bottom: var(--spacing-2);
}

.recoverable-icon {
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
  font-weight: var(--font-weight-bold);
}

.recoverable-card .btn {
  display: block;
  width: 100%;
}
</style>
