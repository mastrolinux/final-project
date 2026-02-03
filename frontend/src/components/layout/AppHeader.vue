<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore, useProfileStore } from '@/stores'
import { authService } from '@/services'
import ThemeToggle from '@/components/common/ThemeToggle.vue'

const router = useRouter()
const { t } = useI18n()
const authStore = useAuthStore()
const profileStore = useProfileStore()

const isAuthenticated = computed(() => authStore.isAuthenticated)
const isAdmin = computed(() => authStore.isAdmin)
const displayName = computed(() => profileStore.displayName || authStore.user?.email || '')

async function handleLogout() {
  await authService.logout()
  router.push({ name: 'home' })
}
</script>

<template>
  <header class="app-header">
    <div class="header-left">
      <router-link to="/" class="logo">
        <span class="logo-text">{{ t('app.name') }}</span>
      </router-link>
    </div>

    <nav class="header-nav" v-if="isAuthenticated">
      <router-link to="/profile" class="nav-link">
        {{ t('nav.profile') }}
      </router-link>
      <router-link to="/contexts" class="nav-link">
        {{ t('nav.contexts') }}
      </router-link>
      <router-link to="/settings" class="nav-link">
        {{ t('nav.settings') }}
      </router-link>
      <router-link v-if="isAdmin" to="/admin/oauth/clients" class="nav-link nav-link-admin">
        Admin
      </router-link>
    </nav>

    <div class="header-right">
      <ThemeToggle />
      <template v-if="isAuthenticated">
        <div class="user-menu">
          <span class="user-name">{{ displayName }}</span>
          <button class="btn btn-ghost btn-sm" @click="handleLogout">
            {{ t('nav.logout') }}
          </button>
        </div>
      </template>
      <template v-else>
        <router-link to="/login" class="btn btn-ghost btn-sm">
          {{ t('nav.login') }}
        </router-link>
        <router-link to="/register" class="btn btn-primary btn-sm">
          {{ t('nav.register') }}
        </router-link>
      </template>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-4);
}

.header-left {
  display: flex;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  text-decoration: none;
  color: var(--text-primary);
}

.logo-text {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
}

.header-nav {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
}

.nav-link {
  padding: var(--spacing-2) var(--spacing-3);
  color: var(--text-secondary);
  text-decoration: none;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.nav-link:hover {
  color: var(--text-primary);
  background-color: var(--bg-tertiary);
  text-decoration: none;
}

.nav-link.router-link-active {
  color: var(--color-primary-600);
  background-color: var(--color-primary-50);
}

.nav-link-admin {
  color: var(--color-warning-700);
  font-weight: var(--font-weight-medium);
}

.nav-link-admin:hover {
  color: var(--color-warning-800);
  background-color: var(--color-warning-50);
}

.nav-link-admin.router-link-active {
  color: var(--color-warning-800);
  background-color: var(--color-warning-100);
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.user-menu {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.user-name {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

@media (max-width: 768px) {
  .header-nav {
    display: none;
  }

  .user-name {
    display: none;
  }
}
</style>
