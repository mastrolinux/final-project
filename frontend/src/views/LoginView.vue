<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { authService, getErrorMessage } from '@/services'

const router = useRouter()
const route = useRoute()
const { t } = useI18n()

const emailInput = ref<HTMLInputElement | null>(null)
const email = ref('')
const password = ref('')
const isLoading = ref(false)
const error = ref<string | null>(null)

onMounted(() => {
  emailInput.value?.focus()
})

async function handleSubmit() {
  error.value = null
  isLoading.value = true

  try {
    await authService.login({ email: email.value, password: password.value })

    // Redirect to intended destination or profile
    const redirect = route.query.redirect as string
    router.push(redirect || { name: 'profile' })
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
          <h1>{{ t('auth.login') }}</h1>
          <p class="text-secondary">{{ t('app.tagline') }}</p>
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
</style>
