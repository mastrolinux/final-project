<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { authService, getErrorMessage } from "@/services";

const { t } = useI18n();
const route = useRoute();
const router = useRouter();

const token = ref("");
const password = ref("");
const confirmPassword = ref("");
const isLoading = ref(false);
const isSuccess = ref(false);
const error = ref<string | null>(null);
const validationError = ref<string | null>(null);

onMounted(() => {
  token.value = (route.query.token as string) || "";
  if (!token.value) {
    error.value = t("auth.invalidResetToken");
  }
});

function validatePassword(): boolean {
  validationError.value = null;

  if (password.value.length < 8) {
    validationError.value = t("auth.passwordTooShort");
    return false;
  }

  if (password.value !== confirmPassword.value) {
    validationError.value = t("auth.passwordsDoNotMatch");
    return false;
  }

  return true;
}

async function handleSubmit() {
  if (!validatePassword()) return;

  isLoading.value = true;
  error.value = null;

  try {
    await authService.resetPassword(token.value, password.value);
    isSuccess.value = true;
  } catch (err) {
    error.value = getErrorMessage(err);
  } finally {
    isLoading.value = false;
  }
}

function goToLogin() {
  router.push({ name: "login" });
}
</script>

<template>
  <div class="reset-password-view">
    <div class="container container-sm">
      <div class="card">
        <div class="card-body">
          <div v-if="isSuccess" class="success-state text-center">
            <div class="success-icon">✓</div>
            <h1>{{ t("auth.passwordReset") }}</h1>
            <p class="text-secondary">{{ t("auth.passwordResetSuccess") }}</p>
            <button class="btn btn-primary mt-4" @click="goToLogin">
              {{ t("auth.goToLogin") }}
            </button>
          </div>

          <template v-else-if="!token">
            <div class="error-state text-center">
              <div class="error-icon">!</div>
              <h1>{{ t("auth.invalidLink") }}</h1>
              <p class="text-secondary">{{ t("auth.invalidResetToken") }}</p>
              <router-link to="/forgot-password" class="btn btn-outline mt-4">
                {{ t("auth.requestNewLink") }}
              </router-link>
            </div>
          </template>

          <template v-else>
            <h1 class="form-title">{{ t("auth.resetPassword") }}</h1>
            <p class="form-description">{{ t("auth.resetPasswordMessage") }}</p>

            <form @submit.prevent="handleSubmit" class="auth-form">
              <div v-if="error" class="alert alert-error">
                {{ error }}
              </div>

              <div v-if="validationError" class="alert alert-warning">
                {{ validationError }}
              </div>

              <div class="form-group">
                <label for="password" class="form-label">{{
                  t("auth.newPassword")
                }}</label>
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
              </div>

              <div class="form-group">
                <label for="confirm-password" class="form-label">{{
                  t("auth.confirmPassword")
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

              <button
                type="submit"
                class="btn btn-primary btn-block"
                :disabled="isLoading"
              >
                {{ isLoading ? t("common.saving") : t("auth.resetPassword") }}
              </button>
            </form>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.reset-password-view {
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
</style>
