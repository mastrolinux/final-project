<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { ChevronRightIcon } from "@heroicons/vue/20/solid";

export interface BreadcrumbItem {
  label: string;
  to?: string;
}

const { t } = useI18n();
const route = useRoute();

const breadcrumbs = computed<BreadcrumbItem[]>(() => {
  const meta = route.meta.breadcrumb as
    | { parent: string; parentLabel: string; currentLabel?: string }
    | undefined;

  if (!meta) return [];

  const items: BreadcrumbItem[] = [
    { label: t(meta.parentLabel), to: meta.parent },
  ];

  const currentLabel = meta.currentLabel
    ? t(meta.currentLabel)
    : (route.meta.title as string);
  if (currentLabel) {
    items.push({ label: currentLabel });
  }

  return items;
});

const hasBreadcrumbs = computed(() => breadcrumbs.value.length > 0);
</script>

<template>
  <nav v-if="hasBreadcrumbs" class="breadcrumb" aria-label="Breadcrumb">
    <ol class="breadcrumb-list">
      <li
        v-for="(item, index) in breadcrumbs"
        :key="index"
        class="breadcrumb-item"
      >
        <router-link v-if="item.to" :to="item.to" class="breadcrumb-link">
          {{ item.label }}
        </router-link>
        <span v-else class="breadcrumb-current" aria-current="page">
          {{ item.label }}
        </span>
        <ChevronRightIcon
          v-if="index < breadcrumbs.length - 1"
          class="breadcrumb-separator"
          aria-hidden="true"
        />
      </li>
    </ol>
  </nav>
</template>

<style scoped>
.breadcrumb {
  margin-bottom: var(--spacing-4);
}

.breadcrumb-list {
  display: flex;
  align-items: center;
  list-style: none;
  padding: 0;
  margin: 0;
  gap: var(--spacing-1);
}

.breadcrumb-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  font-size: var(--font-size-sm);
}

.breadcrumb-link {
  color: var(--text-secondary);
  text-decoration: none;
  transition: color var(--transition-fast);
}

.breadcrumb-link:hover {
  color: var(--color-primary-600);
}

.breadcrumb-current {
  color: var(--text-primary);
  font-weight: var(--font-weight-medium);
}

.breadcrumb-separator {
  width: 14px;
  height: 14px;
  color: var(--text-tertiary);
  flex-shrink: 0;
}
</style>
