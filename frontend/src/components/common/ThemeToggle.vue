<script setup lang="ts">
import { computed } from "vue";
import { useUiStore, type Theme } from "@/stores";

const uiStore = useUiStore();

const currentTheme = computed(() => uiStore.theme);

function cycleTheme() {
  const themes: Theme[] = ["light", "dark", "system"];
  const currentIndex = themes.indexOf(currentTheme.value);
  const nextIndex = (currentIndex + 1) % themes.length;
  uiStore.setTheme(themes[nextIndex]);
}

const themeIcon = computed(() => {
  switch (currentTheme.value) {
    case "light":
      return "sun";
    case "dark":
      return "moon";
    case "system":
    default:
      return "system";
  }
});

const themeLabel = computed(() => {
  switch (currentTheme.value) {
    case "light":
      return "Light";
    case "dark":
      return "Dark";
    case "system":
    default:
      return "System";
  }
});
</script>

<template>
  <button
    class="theme-toggle"
    @click="cycleTheme"
    :title="`Theme: ${themeLabel} (click to change)`"
    :aria-label="`Current theme: ${themeLabel}. Click to cycle themes.`"
  >
    <!-- Sun icon for light mode -->
    <svg
      v-if="themeIcon === 'sun'"
      class="theme-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
    >
      <circle cx="12" cy="12" r="5" />
      <line x1="12" y1="1" x2="12" y2="3" />
      <line x1="12" y1="21" x2="12" y2="23" />
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
      <line x1="1" y1="12" x2="3" y2="12" />
      <line x1="21" y1="12" x2="23" y2="12" />
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
    </svg>

    <!-- Moon icon for dark mode -->
    <svg
      v-else-if="themeIcon === 'moon'"
      class="theme-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
    >
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>

    <!-- System icon (monitor) -->
    <svg
      v-else
      class="theme-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
    >
      <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
      <line x1="8" y1="21" x2="16" y2="21" />
      <line x1="12" y1="17" x2="12" y2="21" />
    </svg>
  </button>
</template>

<style scoped>
.theme-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: var(--spacing-2);
  background: transparent;
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.theme-toggle:hover {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
  border-color: var(--border-secondary);
}

.theme-toggle:focus-visible {
  outline: none;
  box-shadow:
    0 0 0 2px var(--bg-primary),
    0 0 0 4px var(--color-primary-500);
}

.theme-icon {
  width: 18px;
  height: 18px;
}
</style>
