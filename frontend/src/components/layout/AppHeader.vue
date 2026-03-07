<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { useAuthStore, useProfileStore } from "@/stores";
import { authService } from "@/services";
import ThemeToggle from "@/components/common/ThemeToggle.vue";
import AvatarDisplay from "@/components/common/AvatarDisplay.vue";
import {
  ChevronDownIcon,
  Bars3Icon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";

const router = useRouter();
const route = useRoute();
const { t } = useI18n();
const authStore = useAuthStore();
const profileStore = useProfileStore();

const isAuthenticated = computed(() => authStore.isAuthenticated);
const isAdmin = computed(() => authStore.isAdmin);
const displayName = computed(
  () => profileStore.displayName || authStore.user?.email || "",
);

const adminMenuOpen = ref(false);
const adminMenuRef = ref<HTMLElement | null>(null);

const settingsMenuOpen = ref(false);
const settingsMenuRef = ref<HTMLElement | null>(null);

const mobileMenuOpen = ref(false);
const mobileAdminOpen = ref(false);
const mobileSettingsOpen = ref(false);

function toggleAdminMenu() {
  adminMenuOpen.value = !adminMenuOpen.value;
}

function closeAdminMenu() {
  adminMenuOpen.value = false;
}

function toggleSettingsMenu() {
  settingsMenuOpen.value = !settingsMenuOpen.value;
}

function closeSettingsMenu() {
  settingsMenuOpen.value = false;
}

function toggleMobileSettings() {
  mobileSettingsOpen.value = !mobileSettingsOpen.value;
}

function toggleMobileMenu() {
  mobileMenuOpen.value = !mobileMenuOpen.value;
  if (!mobileMenuOpen.value) {
    mobileAdminOpen.value = false;
    mobileSettingsOpen.value = false;
  }
}

function closeMobileMenu() {
  mobileMenuOpen.value = false;
  mobileAdminOpen.value = false;
  mobileSettingsOpen.value = false;
}

function toggleMobileAdmin() {
  mobileAdminOpen.value = !mobileAdminOpen.value;
}

function handleClickOutside(event: MouseEvent) {
  if (
    adminMenuRef.value &&
    !adminMenuRef.value.contains(event.target as Node)
  ) {
    adminMenuOpen.value = false;
  }
  if (
    settingsMenuRef.value &&
    !settingsMenuRef.value.contains(event.target as Node)
  ) {
    settingsMenuOpen.value = false;
  }
}

function handleEscape(event: KeyboardEvent) {
  if (event.key === "Escape" && mobileMenuOpen.value) {
    closeMobileMenu();
  }
}

// Close mobile menu on route change
watch(
  () => route.fullPath,
  () => {
    closeMobileMenu();
  },
);

// Prevent body scroll when mobile menu is open
watch(mobileMenuOpen, (open) => {
  document.body.style.overflow = open ? "hidden" : "";
});

onMounted(() => {
  document.addEventListener("click", handleClickOutside);
  document.addEventListener("keydown", handleEscape);
});

onUnmounted(() => {
  document.removeEventListener("click", handleClickOutside);
  document.removeEventListener("keydown", handleEscape);
  document.body.style.overflow = "";
});

async function handleLogout() {
  closeMobileMenu();
  await authService.logout();
  router.push({ name: "home" });
}
</script>

<template>
  <header class="app-header">
    <div class="header-left">
      <router-link to="/" class="logo">
        <img src="/cobi_logo.svg" :alt="t('app.name')" class="logo-img" />
      </router-link>
    </div>

    <nav class="header-nav" v-if="isAuthenticated">
      <router-link to="/profile" class="nav-link">
        {{ t("nav.profile") }}
      </router-link>
      <router-link to="/contexts" class="nav-link">
        {{ t("nav.contexts") }}
      </router-link>
      <router-link
        v-if="authStore.accountType !== 'pseudonymous'"
        to="/documents"
        class="nav-link"
      >
        {{ t("nav.documents") }}
      </router-link>
      <!-- Settings dropdown -->
      <div ref="settingsMenuRef" class="settings-dropdown">
        <button
          class="nav-link settings-trigger"
          :class="{ 'settings-trigger-open': settingsMenuOpen }"
          @click="toggleSettingsMenu"
        >
          {{ t("nav.settings") }}
          <ChevronDownIcon
            class="chevron-icon"
            :class="{ 'chevron-open': settingsMenuOpen }"
          />
        </button>
        <Transition name="dropdown">
          <div v-if="settingsMenuOpen" class="settings-menu">
            <router-link
              to="/settings"
              class="settings-menu-item"
              @click="closeSettingsMenu"
            >
              {{ t("nav.settingsGeneral") }}
            </router-link>
            <router-link
              to="/settings/consents"
              class="settings-menu-item"
              @click="closeSettingsMenu"
            >
              {{ t("nav.connectedApps") }}
            </router-link>
            <router-link
              to="/settings/data-export"
              class="settings-menu-item"
              @click="closeSettingsMenu"
            >
              {{ t("nav.dataExport") }}
            </router-link>
          </div>
        </Transition>
      </div>
      <router-link to="/audit" class="nav-link">
        {{ t("nav.audit") }}
      </router-link>

      <!-- Admin dropdown -->
      <div v-if="isAdmin" ref="adminMenuRef" class="admin-dropdown">
        <button
          class="nav-link nav-link-admin admin-trigger"
          :class="{ 'admin-trigger-open': adminMenuOpen }"
          @click="toggleAdminMenu"
        >
          {{ t("nav.admin") }}
          <ChevronDownIcon
            class="chevron-icon"
            :class="{ 'chevron-open': adminMenuOpen }"
          />
        </button>
        <Transition name="dropdown">
          <div v-if="adminMenuOpen" class="admin-menu">
            <router-link
              to="/admin/oauth/clients"
              class="admin-menu-item"
              @click="closeAdminMenu"
            >
              {{ t("nav.adminOAuthClients") }}
            </router-link>
            <router-link
              to="/admin/audit/verify"
              class="admin-menu-item"
              @click="closeAdminMenu"
            >
              {{ t("nav.adminAuditVerify") }}
            </router-link>
            <router-link
              to="/admin/users/soft-deleted"
              class="admin-menu-item"
              @click="closeAdminMenu"
            >
              {{ t("nav.adminSoftDeletedUsers") }}
            </router-link>
            <router-link
              to="/admin/verifications"
              class="admin-menu-item"
              @click="closeAdminMenu"
            >
              {{ t("nav.adminVerifications") }}
            </router-link>
          </div>
        </Transition>
      </div>
    </nav>

    <div class="header-right">
      <ThemeToggle />
      <template v-if="isAuthenticated">
        <div class="user-menu">
          <AvatarDisplay
            v-if="profileStore.profile?.avatar_thumbnail_url"
            :src="profileStore.profile.avatar_thumbnail_url"
            :name="displayName"
            size="sm"
          />
          <span class="user-name">{{ displayName }}</span>
          <button class="btn btn-ghost btn-sm" @click="handleLogout">
            {{ t("nav.logout") }}
          </button>
        </div>
      </template>
      <template v-else>
        <router-link to="/login" class="btn btn-ghost btn-sm">
          {{ t("nav.login") }}
        </router-link>
        <router-link to="/register" class="btn btn-primary btn-sm">
          {{ t("nav.register") }}
        </router-link>
      </template>

      <!-- Mobile hamburger button -->
      <button
        class="mobile-menu-btn"
        @click="toggleMobileMenu"
        :aria-label="mobileMenuOpen ? 'Close menu' : 'Open menu'"
        :aria-expanded="mobileMenuOpen"
      >
        <Transition name="icon-swap" mode="out-in">
          <Bars3Icon v-if="!mobileMenuOpen" class="mobile-menu-icon" />
          <XMarkIcon v-else class="mobile-menu-icon" />
        </Transition>
      </button>
    </div>

    <!-- Mobile drawer overlay -->
    <Transition name="overlay">
      <div
        v-if="mobileMenuOpen"
        class="mobile-overlay"
        @click="closeMobileMenu"
      />
    </Transition>

    <!-- Mobile drawer panel -->
    <Transition name="drawer">
      <nav
        v-if="mobileMenuOpen"
        class="mobile-drawer"
        role="navigation"
        aria-label="Mobile navigation"
      >
        <div class="mobile-drawer-header">
          <img src="/cobi_logo.svg" :alt="t('app.name')" class="mobile-drawer-logo" />
          <button
            class="mobile-close-btn"
            @click="closeMobileMenu"
            aria-label="Close menu"
          >
            <XMarkIcon class="mobile-menu-icon" />
          </button>
        </div>

        <div class="mobile-drawer-body" v-if="isAuthenticated">
          <div class="mobile-nav-section">
            <router-link to="/profile" class="mobile-nav-link">
              {{ t("nav.profile") }}
            </router-link>
            <router-link to="/contexts" class="mobile-nav-link">
              {{ t("nav.contexts") }}
            </router-link>
            <router-link
              v-if="authStore.accountType !== 'pseudonymous'"
              to="/documents"
              class="mobile-nav-link"
            >
              {{ t("nav.documents") }}
            </router-link>
            <!-- Settings section (mobile) -->
            <button
              class="mobile-nav-link mobile-settings-trigger"
              @click="toggleMobileSettings"
            >
              <span>{{ t("nav.settings") }}</span>
              <ChevronDownIcon
                class="chevron-icon"
                :class="{ 'chevron-open': mobileSettingsOpen }"
              />
            </button>
            <Transition name="expand">
              <div v-if="mobileSettingsOpen" class="mobile-settings-items">
                <router-link
                  to="/settings"
                  class="mobile-nav-link mobile-nav-sub"
                >
                  {{ t("nav.settingsGeneral") }}
                </router-link>
                <router-link
                  to="/settings/consents"
                  class="mobile-nav-link mobile-nav-sub"
                >
                  {{ t("nav.connectedApps") }}
                </router-link>
                <router-link
                  to="/settings/data-export"
                  class="mobile-nav-link mobile-nav-sub"
                >
                  {{ t("nav.dataExport") }}
                </router-link>
              </div>
            </Transition>
            <router-link to="/audit" class="mobile-nav-link">
              {{ t("nav.audit") }}
            </router-link>
          </div>

          <!-- Admin section (mobile) -->
          <div v-if="isAdmin" class="mobile-nav-section mobile-admin-section">
            <button
              class="mobile-nav-link mobile-admin-trigger"
              @click="toggleMobileAdmin"
            >
              <span>{{ t("nav.admin") }}</span>
              <ChevronDownIcon
                class="chevron-icon"
                :class="{ 'chevron-open': mobileAdminOpen }"
              />
            </button>
            <Transition name="expand">
              <div v-if="mobileAdminOpen" class="mobile-admin-items">
                <router-link
                  to="/admin/oauth/clients"
                  class="mobile-nav-link mobile-nav-sub"
                >
                  {{ t("nav.adminOAuthClients") }}
                </router-link>
                <router-link
                  to="/admin/audit/verify"
                  class="mobile-nav-link mobile-nav-sub"
                >
                  {{ t("nav.adminAuditVerify") }}
                </router-link>
                <router-link
                  to="/admin/users/soft-deleted"
                  class="mobile-nav-link mobile-nav-sub"
                >
                  {{ t("nav.adminSoftDeletedUsers") }}
                </router-link>
                <router-link
                  to="/admin/verifications"
                  class="mobile-nav-link mobile-nav-sub"
                >
                  {{ t("nav.adminVerifications") }}
                </router-link>
              </div>
            </Transition>
          </div>
        </div>

        <div class="mobile-drawer-body" v-else>
          <div class="mobile-nav-section">
            <router-link to="/login" class="mobile-nav-link">
              {{ t("nav.login") }}
            </router-link>
            <router-link to="/register" class="mobile-nav-link">
              {{ t("nav.register") }}
            </router-link>
          </div>
        </div>

        <div class="mobile-drawer-footer" v-if="isAuthenticated">
          <div class="mobile-user-info">
            <AvatarDisplay
              :src="profileStore.profile?.avatar_thumbnail_url"
              :name="displayName"
              size="sm"
            />
            <span class="mobile-user-name">{{ displayName }}</span>
          </div>
          <button class="mobile-logout-btn" @click="handleLogout">
            {{ t("nav.logout") }}
          </button>
        </div>
      </nav>
    </Transition>
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

.logo-img {
  height: 40px;
  width: auto;
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
  color: var(--admin-text);
  font-weight: var(--font-weight-medium);
}

.nav-link-admin:hover {
  color: var(--admin-text-hover);
  background-color: var(--admin-bg);
}

/* Settings dropdown */
.settings-dropdown {
  position: relative;
}

.settings-trigger {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-1);
  cursor: pointer;
  border: none;
  background: none;
  font-size: inherit;
  font-family: inherit;
}

.settings-trigger-open {
  color: var(--color-primary-600);
  background-color: var(--color-primary-50);
}

.settings-menu {
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

.settings-menu-item {
  display: block;
  padding: var(--spacing-2) var(--spacing-3);
  color: var(--text-secondary);
  text-decoration: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.settings-menu-item:hover {
  color: var(--text-primary);
  background-color: var(--bg-tertiary);
  text-decoration: none;
}

.settings-menu-item.router-link-active {
  color: var(--color-primary-600);
  background-color: var(--color-primary-50);
  font-weight: var(--font-weight-medium);
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
  color: var(--admin-text-hover);
  background-color: var(--admin-bg);
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
  color: var(--admin-text-hover);
  background-color: var(--admin-bg-hover);
  text-decoration: none;
}

.admin-menu-item.router-link-active {
  color: var(--admin-text-hover);
  background-color: var(--admin-bg-active);
  font-weight: var(--font-weight-medium);
}

/* Dropdown transition */
.dropdown-enter-active,
.dropdown-leave-active {
  transition:
    opacity var(--transition-fast),
    transform var(--transition-fast);
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

/* ============================================
   Mobile menu
   ============================================ */

.mobile-menu-btn {
  display: none;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  padding: 0;
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  background-color: var(--bg-secondary);
  color: var(--text-primary);
  cursor: pointer;
  transition:
    background-color var(--transition-fast),
    border-color var(--transition-fast);
}

.mobile-menu-btn:hover {
  background-color: var(--bg-tertiary);
  border-color: var(--border-secondary);
}

.mobile-menu-icon {
  width: 22px;
  height: 22px;
}

/* Icon swap transition */
.icon-swap-enter-active,
.icon-swap-leave-active {
  transition:
    opacity 100ms ease,
    transform 100ms ease;
}

.icon-swap-enter-from {
  opacity: 0;
  transform: rotate(-90deg) scale(0.8);
}

.icon-swap-leave-to {
  opacity: 0;
  transform: rotate(90deg) scale(0.8);
}

/* Overlay */
.mobile-overlay {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.4);
  z-index: var(--z-modal-backdrop);
  backdrop-filter: blur(2px);
}

.overlay-enter-active,
.overlay-leave-active {
  transition: opacity var(--transition-normal);
}

.overlay-enter-from,
.overlay-leave-to {
  opacity: 0;
}

/* Drawer panel */
.mobile-drawer {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: min(320px, 85vw);
  background-color: var(--bg-secondary);
  z-index: var(--z-modal);
  display: flex;
  flex-direction: column;
  box-shadow: -8px 0 24px rgba(0, 0, 0, 0.12);
  overflow-y: auto;
  overscroll-behavior: contain;
}

.drawer-enter-active,
.drawer-leave-active {
  transition: transform var(--transition-slow);
}

.drawer-enter-from,
.drawer-leave-to {
  transform: translateX(100%);
}

/* Drawer header */
.mobile-drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-4) var(--spacing-5);
  border-bottom: 1px solid var(--border-primary);
  flex-shrink: 0;
}

.mobile-drawer-logo {
  height: 32px;
  width: auto;
}

.mobile-close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  border: none;
  border-radius: var(--radius-md);
  background-color: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition:
    background-color var(--transition-fast),
    color var(--transition-fast);
}

.mobile-close-btn:hover {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
}

/* Drawer body */
.mobile-drawer-body {
  flex: 1;
  padding: var(--spacing-3) var(--spacing-3);
  overflow-y: auto;
}

.mobile-nav-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.mobile-nav-section + .mobile-nav-section {
  margin-top: var(--spacing-3);
  padding-top: var(--spacing-3);
  border-top: 1px solid var(--border-primary);
}

.mobile-nav-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-3) var(--spacing-4);
  color: var(--text-secondary);
  text-decoration: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  border: none;
  background: none;
  width: 100%;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
  transition:
    color var(--transition-fast),
    background-color var(--transition-fast);
}

.mobile-nav-link:hover {
  color: var(--text-primary);
  background-color: var(--bg-tertiary);
  text-decoration: none;
}

.mobile-nav-link.router-link-active {
  color: var(--color-primary-600);
  background-color: var(--color-primary-50);
}

.mobile-settings-trigger {
  color: var(--text-secondary);
}

.mobile-settings-items {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
  overflow: hidden;
}

.mobile-admin-trigger {
  color: var(--admin-text);
}

.mobile-admin-trigger:hover {
  color: var(--admin-text-hover);
  background-color: var(--admin-bg);
}

.mobile-admin-items {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
  overflow: hidden;
}

.mobile-nav-sub {
  padding-left: var(--spacing-8);
  font-size: var(--font-size-sm);
}

.mobile-nav-sub.router-link-active {
  color: var(--admin-text-hover);
  background-color: var(--admin-bg-active);
}

/* Expand transition for admin subitems */
.expand-enter-active,
.expand-leave-active {
  transition:
    max-height var(--transition-normal),
    opacity var(--transition-normal);
  max-height: 200px;
}

.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  opacity: 0;
}

/* Drawer footer */
.mobile-drawer-footer {
  padding: var(--spacing-4) var(--spacing-5);
  border-top: 1px solid var(--border-primary);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-3);
  flex-shrink: 0;
}

.mobile-user-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  min-width: 0;
}

.mobile-user-name {
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mobile-logout-btn {
  padding: var(--spacing-2) var(--spacing-3);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  background: none;
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  font-family: inherit;
  cursor: pointer;
  white-space: nowrap;
  transition:
    color var(--transition-fast),
    background-color var(--transition-fast),
    border-color var(--transition-fast);
}

.mobile-logout-btn:hover {
  color: var(--color-error-700);
  background-color: var(--color-error-50);
  border-color: var(--color-error-500);
}

/* ============================================
   Responsive breakpoint
   ============================================ */

@media (max-width: 768px) {
  .header-nav {
    display: none;
  }

  .user-name {
    display: none;
  }

  .user-menu .btn {
    display: none;
  }

  .header-right > .btn {
    display: none;
  }

  .mobile-menu-btn {
    display: flex;
  }
}
</style>
