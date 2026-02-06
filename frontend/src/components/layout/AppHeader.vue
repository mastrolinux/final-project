<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore, useProfileStore } from '@/stores'
import { authService } from '@/services'
import ThemeToggle from '@/components/common/ThemeToggle.vue'
import { ChevronDownIcon } from '@heroicons/vue/24/outline'

const router = useRouter()
const { t } = useI18n()
const authStore = useAuthStore()
const profileStore = useProfileStore()

const isAuthenticated = computed(() => authStore.isAuthenticated)
const isAdmin = computed(() => authStore.isAdmin)
const displayName = computed(() => profileStore.displayName || authStore.user?.email || '')

const adminMenuOpen = ref(false)
const adminMenuRef = ref<HTMLElement | null>(null)

function toggleAdminMenu() {
  adminMenuOpen.value = !adminMenuOpen.value
}

function closeAdminMenu() {
  adminMenuOpen.value = false
}

function handleClickOutside(event: MouseEvent) {
  if (adminMenuRef.value && !adminMenuRef.value.contains(event.target as Node)) {
    adminMenuOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

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
      <router-link to="/audit" class="nav-link">
        {{ t('nav.audit') }}
      </router-link>

      <!-- Admin dropdown -->
      <div v-if="isAdmin" ref="adminMenuRef" class="admin-dropdown">
        <button
          class="nav-link nav-link-admin admin-trigger"
          :class="{ 'admin-trigger-open': adminMenuOpen }"
          @click="toggleAdminMenu"
        >
          {{ t('nav.admin') }}
          <ChevronDownIcon class="chevron-icon" :class="{ 'chevron-open': adminMenuOpen }" />
        </button>
        <Transition name="dropdown">
          <div v-if="adminMenuOpen" class="admin-menu">
            <router-link
              to="/admin/oauth/clients"
              class="admin-menu-item"
              @click="closeAdminMenu"
            >
              {{ t('nav.adminOAuthClients') }}
            </router-link>
            <router-link
              to="/admin/audit/verify"
              class="admin-menu-item"
              @click="closeAdminMenu"
            >
              {{ t('nav.adminAuditVerify') }}
            </router-link>
          </div>
        </Transition>
      </div>
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

/* Admin dropdown */
.admin-dropdown {
  position: relative;
}

.admin-trigger {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-1);
  cursor: pointer;
  border: none;
  background: none;
  font-size: inherit;
  font-family: inherit;
}

.admin-trigger-open {
  color: var(--color-warning-800);
  background-color: var(--color-warning-50);
}

.chevron-icon {
  width: 14px;
  height: 14px;
  transition: transform var(--transition-fast);
}

.chevron-open {
  transform: rotate(180deg);
}

.admin-menu {
  position: absolute;
  top: calc(100% + var(--spacing-1));
  left: 0;
  min-width: 180px;
  background-color: var(--bg-primary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding: var(--spacing-1);
  z-index: var(--z-dropdown);
  display: flex;
  flex-direction: column;
}

.admin-menu-item {
  display: block;
  padding: var(--spacing-2) var(--spacing-3);
  color: var(--text-secondary);
  text-decoration: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.admin-menu-item:hover {
  color: var(--color-warning-800);
  background-color: var(--color-warning-50);
  text-decoration: none;
}

.admin-menu-item.router-link-active {
  color: var(--color-warning-800);
  background-color: var(--color-warning-100);
  font-weight: var(--font-weight-medium);
}

/* Dropdown transition */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity var(--transition-fast), transform var(--transition-fast);
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
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
