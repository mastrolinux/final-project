<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore, useUiStore } from '@/stores'
import { authService, getErrorMessage } from '@/services'
import { setLocale, SUPPORTED_LOCALES, LOCALE_NAMES, type SupportedLocale } from '@/locales'

const { t, locale } = useI18n()
const authStore = useAuthStore()
const uiStore = useUiStore()

const currentLocale = computed({
  get: () => locale.value as SupportedLocale,
  set: (value: SupportedLocale) => {
    setLocale(value)
    uiStore.addNotification({
      type: 'success',
      message: t('settings.languageChanged')
    })
  }
})

const currentTheme = computed({
  get: () => uiStore.theme,
  set: (value: 'light' | 'dark' | 'system') => {
    uiStore.setTheme(value)
    uiStore.addNotification({
      type: 'success',
      message: t('settings.themeChanged')
    })
  }
})

// Password change form
const passwordForm = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})
const isChangingPassword = ref(false)
const passwordError = ref<string | null>(null)
const passwordSuccess = ref(false)

async function handlePasswordChange() {
  passwordError.value = null
  passwordSuccess.value = false

  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    passwordError.value = t('auth.passwordsDoNotMatch')
    return
  }

  if (passwordForm.value.newPassword.length < 8) {
    passwordError.value = t('auth.passwordTooShort')
    return
  }

  isChangingPassword.value = true

  try {
    await authService.changePassword(
      passwordForm.value.currentPassword,
      passwordForm.value.newPassword
    )
    passwordSuccess.value = true
    passwordForm.value = {
      currentPassword: '',
      newPassword: '',
      confirmPassword: ''
    }
    uiStore.addNotification({
      type: 'success',
      message: t('settings.passwordChanged')
    })
  } catch (err) {
    passwordError.value = getErrorMessage(err)
  } finally {
    isChangingPassword.value = false
  }
}

// Account deletion
const showDeleteConfirm = ref(false)
const deleteConfirmation = ref('')
const isDeleting = ref(false)
const deleteError = ref<string | null>(null)

const canDelete = computed(() => deleteConfirmation.value === 'DELETE')

async function handleDeleteAccount() {
  if (!canDelete.value) return

  isDeleting.value = true
  deleteError.value = null

  try {
    await authService.deleteAccount()
    authStore.logout()
  } catch (err) {
    deleteError.value = getErrorMessage(err)
  } finally {
    isDeleting.value = false
  }
}
</script>

<template>
  <div class="settings-view">
    <div class="container container-lg">
      <div class="page-header">
        <h1 class="page-title">{{ t('settings.title') }}</h1>
        <p class="page-description">{{ t('settings.description') }}</p>
      </div>

      <!-- Appearance Settings -->
      <section class="settings-section card">
        <div class="card-header">
          <h2>{{ t('settings.appearance') }}</h2>
        </div>
        <div class="card-body">
          <div class="setting-row">
            <div class="setting-info">
              <h3>{{ t('settings.language') }}</h3>
              <p>{{ t('settings.languageDescription') }}</p>
            </div>
            <select v-model="currentLocale" class="form-select">
              <option v-for="loc in SUPPORTED_LOCALES" :key="loc" :value="loc">
                {{ LOCALE_NAMES[loc] }}
              </option>
            </select>
          </div>

          <div class="setting-row">
            <div class="setting-info">
              <h3>{{ t('settings.theme') }}</h3>
              <p>{{ t('settings.themeDescription') }}</p>
            </div>
            <select v-model="currentTheme" class="form-select">
              <option value="system">{{ t('settings.themeSystem') }}</option>
              <option value="light">{{ t('settings.themeLight') }}</option>
              <option value="dark">{{ t('settings.themeDark') }}</option>
            </select>
          </div>
        </div>
      </section>

      <!-- Security Settings -->
      <section class="settings-section card">
        <div class="card-header">
          <h2>{{ t('settings.security') }}</h2>
        </div>
        <div class="card-body">
          <div class="setting-block">
            <h3>{{ t('settings.changePassword') }}</h3>
            <p class="text-secondary mb-4">{{ t('settings.changePasswordDescription') }}</p>

            <form @submit.prevent="handlePasswordChange" class="password-form">
              <div v-if="passwordError" class="alert alert-error">
                {{ passwordError }}
              </div>

              <div v-if="passwordSuccess" class="alert alert-success">
                {{ t('settings.passwordChanged') }}
              </div>

              <div class="form-group">
                <label for="current-password" class="form-label">{{
                  t('settings.currentPassword')
                }}</label>
                <input
                  id="current-password"
                  v-model="passwordForm.currentPassword"
                  type="password"
                  class="form-input"
                  required
                  autocomplete="current-password"
                />
              </div>

              <div class="form-group">
                <label for="new-password" class="form-label">{{ t('settings.newPassword') }}</label>
                <input
                  id="new-password"
                  v-model="passwordForm.newPassword"
                  type="password"
                  class="form-input"
                  required
                  minlength="8"
                  autocomplete="new-password"
                />
              </div>

              <div class="form-group">
                <label for="confirm-new-password" class="form-label">{{
                  t('auth.confirmPassword')
                }}</label>
                <input
                  id="confirm-new-password"
                  v-model="passwordForm.confirmPassword"
                  type="password"
                  class="form-input"
                  required
                  autocomplete="new-password"
                />
              </div>

              <button type="submit" class="btn btn-primary" :disabled="isChangingPassword">
                {{ isChangingPassword ? t('common.saving') : t('settings.updatePassword') }}
              </button>
            </form>
          </div>
        </div>
      </section>

      <!-- Account Information -->
      <section class="settings-section card">
        <div class="card-header">
          <h2>{{ t('settings.account') }}</h2>
        </div>
        <div class="card-body">
          <div class="setting-row">
            <div class="setting-info">
              <h3>{{ t('common.email') }}</h3>
              <p>{{ authStore.userEmail }}</p>
            </div>
            <span
              :class="[
                'badge',
                authStore.isEmailVerified ? 'badge-success' : 'badge-warning'
              ]"
            >
              {{ authStore.isEmailVerified ? t('auth.verified') : t('auth.unverified') }}
            </span>
          </div>

          <div class="setting-row">
            <div class="setting-info">
              <h3>{{ t('settings.accountType') }}</h3>
              <p>{{ t(`account.types.${authStore.accountType}`) }}</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Danger Zone -->
      <section class="settings-section card card-danger">
        <div class="card-header">
          <h2>{{ t('settings.dangerZone') }}</h2>
        </div>
        <div class="card-body">
          <div class="setting-row">
            <div class="setting-info">
              <h3>{{ t('settings.deleteAccount') }}</h3>
              <p>{{ t('settings.deleteAccountWarning') }}</p>
            </div>
            <button class="btn btn-danger-outline" @click="showDeleteConfirm = true">
              {{ t('settings.deleteAccount') }}
            </button>
          </div>
        </div>
      </section>

      <!-- Delete confirmation modal -->
      <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="showDeleteConfirm = false">
        <div class="modal">
          <div class="modal-header">
            <h2>{{ t('settings.deleteAccountConfirmTitle') }}</h2>
          </div>
          <div class="modal-body">
            <p class="mb-4">{{ t('settings.deleteAccountConfirmMessage') }}</p>

            <div v-if="deleteError" class="alert alert-error mb-4">
              {{ deleteError }}
            </div>

            <div class="form-group">
              <label class="form-label">{{ t('settings.typeDeleteToConfirm') }}</label>
              <input
                v-model="deleteConfirmation"
                type="text"
                class="form-input"
                placeholder="DELETE"
              />
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-outline" @click="showDeleteConfirm = false">
              {{ t('common.cancel') }}
            </button>
            <button
              class="btn btn-danger"
              :disabled="!canDelete || isDeleting"
              @click="handleDeleteAccount"
            >
              {{ isDeleting ? t('common.deleting') : t('settings.permanentlyDelete') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-view {
  padding: var(--spacing-8) 0;
}

.settings-section {
  margin-bottom: var(--spacing-6);
}

.card-header h2 {
  font-size: var(--font-size-lg);
  margin: 0;
}

.setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-4) 0;
  border-bottom: 1px solid var(--border-color);
}

.setting-row:last-child {
  border-bottom: none;
}

.setting-info h3 {
  font-size: var(--font-size-base);
  margin-bottom: var(--spacing-1);
}

.setting-info p {
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  margin: 0;
}

.setting-block {
  padding: var(--spacing-4) 0;
}

.setting-block h3 {
  font-size: var(--font-size-base);
  margin-bottom: var(--spacing-1);
}

.password-form {
  max-width: 400px;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.form-select {
  padding: var(--spacing-2) var(--spacing-3);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background-color: var(--bg-primary);
  color: var(--text-primary);
  min-width: 150px;
}

.card-danger {
  border-color: var(--color-error-200);
}

.card-danger .card-header {
  background-color: var(--color-error-50);
  color: var(--color-error-700);
}

.btn-danger-outline {
  color: var(--color-error-600);
  border-color: var(--color-error-300);
}

.btn-danger-outline:hover {
  background-color: var(--color-error-50);
}

.btn-danger {
  background-color: var(--color-error-600);
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background-color: var(--color-error-700);
}

/* Modal styles */
.modal-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  max-width: 450px;
  width: 90%;
}

.modal-header {
  padding: var(--spacing-4) var(--spacing-6);
  border-bottom: 1px solid var(--border-color);
}

.modal-header h2 {
  font-size: var(--font-size-lg);
  margin: 0;
}

.modal-body {
  padding: var(--spacing-6);
}

.modal-footer {
  padding: var(--spacing-4) var(--spacing-6);
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-2);
}
</style>
