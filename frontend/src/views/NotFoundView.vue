<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

<template>
  <div class="not-found-view">
    <div class="container container-sm text-center">
      <div class="error-code">404</div>
      <h1>{{ t('errors.pageNotFound') }}</h1>
      <p class="text-secondary">{{ t('errors.pageNotFoundMessage') }}</p>
      <router-link to="/" class="btn btn-primary mt-6">
        {{ t('common.backToHome') }}
      </router-link>
    </div>
  </div>
</template>

<style scoped>
.not-found-view {
  padding: var(--spacing-8) 0;
  min-height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.error-code {
  font-size: 8rem;
  font-weight: 700;
  line-height: 1;
  color: var(--color-primary-200);
  margin-bottom: var(--spacing-4);
}

h1 {
  font-size: var(--font-size-2xl);
  margin-bottom: var(--spacing-2);
}
</style>
