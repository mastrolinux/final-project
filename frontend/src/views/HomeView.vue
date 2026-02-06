<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores'

const { t } = useI18n()
const authStore = useAuthStore()
</script>

<template>
  <div class="home-view">
    <div class="container container-lg">
      <div class="hero">
        <h1 class="hero-title">{{ t('app.name') }}</h1>
        <p class="hero-tagline">{{ t('app.tagline') }}</p>

        <div class="hero-actions" v-if="!authStore.isAuthenticated">
          <router-link to="/register" class="btn btn-primary btn-lg">
            {{ t('auth.createAccount') }}
          </router-link>
          <router-link to="/login" class="btn btn-secondary btn-lg">
            {{ t('auth.signIn') }}
          </router-link>
        </div>

        <div class="hero-actions" v-else>
          <router-link to="/profile" class="btn btn-primary btn-lg">
            {{ t('nav.profile') }}
          </router-link>
          <router-link to="/contexts" class="btn btn-secondary btn-lg">
            {{ t('nav.contexts') }}
          </router-link>
        </div>
      </div>

      <div class="features">
        <div class="feature-card card">
          <div class="card-body">
            <h3>Multi-Context Identity</h3>
            <p>Manage different identity contexts for professional, social, legal, and personal use.</p>
          </div>
        </div>

        <div class="feature-card card">
          <div class="card-body">
            <h3>Cultural Name Support</h3>
            <p>Support for diverse naming conventions including multilingual names and cultural patterns.</p>
          </div>
        </div>

        <div class="feature-card card">
          <div class="card-body">
            <h3>Privacy-First Design</h3>
            <p>Built with privacy-by-design principles inspired by GDPR and data protection standards.</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-view {
  padding: var(--spacing-8) 0;
}

.hero {
  text-align: center;
  margin-bottom: var(--spacing-16);
}

.hero-title {
  font-size: var(--font-size-4xl);
  margin-bottom: var(--spacing-4);
}

.hero-tagline {
  font-size: var(--font-size-xl);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-8);
}

.hero-actions {
  display: flex;
  justify-content: center;
  gap: var(--spacing-4);
  flex-wrap: wrap;
}

.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--spacing-6);
}

.feature-card h3 {
  margin-bottom: var(--spacing-2);
  font-size: var(--font-size-lg);
}

.feature-card p {
  color: var(--text-secondary);
}
</style>
