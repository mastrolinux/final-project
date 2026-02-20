<script setup lang="ts">
import { onMounted, computed, watch } from "vue";
import { useAuthStore, useUiStore } from "@/stores";
import { authService } from "@/services";
import AppHeader from "@/components/layout/AppHeader.vue";
import AppNotifications from "@/components/layout/AppNotifications.vue";

const authStore = useAuthStore();
const uiStore = useUiStore();

const isLoading = computed(() => !authStore.isInitialized);

// Reactively update theme class when effectiveTheme changes
watch(
  () => uiStore.effectiveTheme,
  (newTheme, oldTheme) => {
    const root = document.documentElement;
    if (oldTheme) {
      root.classList.remove(oldTheme);
    }
    root.classList.add(newTheme);
  },
  { immediate: true },
);

onMounted(async () => {
  // Initialize authentication state
  if (authStore.hasStoredSession()) {
    await authService.initializeAuth();
  } else {
    authStore.setInitialized(true);
  }
});
</script>

<template>
  <div class="app-layout">
    <AppHeader v-if="authStore.isInitialized" />

    <main class="app-main">
      <div v-if="isLoading" class="loading-screen">
        <div class="spinner spinner-lg"></div>
        <p class="mt-4 text-secondary">{{ $t("common.loading") }}</p>
      </div>

      <router-view v-else class="app-content" />
    </main>

    <AppNotifications />
  </div>
</template>

<style scoped>
.loading-screen {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: calc(100vh - var(--header-height));
}
</style>
