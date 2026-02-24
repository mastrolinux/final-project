<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import { useAuthStore, useProfileStore } from "@/stores";
import { contextService, getErrorMessage } from "@/services";
import BaseCard from "@/components/common/BaseCard.vue";
import BaseButton from "@/components/common/BaseButton.vue";
import BaseBadge from "@/components/common/BaseBadge.vue";
import { CONTEXT_TYPE_META } from "@/types";

const { t } = useI18n();
const router = useRouter();
const authStore = useAuthStore();
const profileStore = useProfileStore();

const isLoading = ref(true);
const error = ref<string | null>(null);

onMounted(async () => {
  if (!authStore.userId) return;

  try {
    const contexts = await contextService.list(authStore.userId);
    profileStore.setContexts(contexts);
  } catch (err) {
    error.value = getErrorMessage(err);
  } finally {
    isLoading.value = false;
  }
});

const navigateToCreate = () => {
  router.push({ name: "context-create" });
};

const navigateToDetail = (id: string) => {
  router.push({ name: "context-detail", params: { id } });
};
</script>

<template>
  <div class="page-view">
    <div class="container container-lg">
      <div class="contexts-header">
        <div>
          <h1 class="page-title">{{ t("context.title") }}</h1>
          <p class="page-description">{{ t("context.description") }}</p>
        </div>
        <BaseButton variant="primary" @click="navigateToCreate">
          {{ t("context.create") }}
        </BaseButton>
      </div>

      <div v-if="isLoading" class="loading-container">
        <div class="spinner spinner-lg loading-spinner"></div>
        <p class="loading-text">{{ t("common.loading") }}</p>
      </div>

      <div v-else-if="error" class="alert alert-error alert-spaced">
        {{ error }}
      </div>

      <div v-else-if="profileStore.contexts.length === 0" class="empty-state">
        <BaseCard class="empty-card">
          <div class="empty-icon">📇</div>
          <h3 class="empty-title">No contexts yet</h3>
          <p class="empty-description">
            Create your first identity context to share different information
            with different applications.
          </p>
          <BaseButton variant="primary" @click="navigateToCreate">
            {{ t("context.create") }}
          </BaseButton>
        </BaseCard>
      </div>

      <div v-else class="contexts-grid">
        <div
          v-for="context in profileStore.contexts"
          :key="context.id"
          class="context-card-wrapper"
          role="button"
          tabindex="0"
          :aria-label="t('context.viewContext', { name: context.context_name })"
          @click="navigateToDetail(context.id)"
          @keydown.enter="navigateToDetail(context.id)"
          @keydown.space.prevent="navigateToDetail(context.id)"
        >
          <BaseCard
            class="context-card-item"
            :style="{
              borderLeftColor: `var(--color-${CONTEXT_TYPE_META[context.context_type].color}-500)`,
            }"
          >
            <div class="card-badges">
              <BaseBadge :variant="context.context_type">
                {{ CONTEXT_TYPE_META[context.context_type]?.label }}
              </BaseBadge>
              <div class="badge-group">
                <BaseBadge
                  v-if="context.verification_status === 'pending'"
                  variant="warning"
                  size="sm"
                >
                  {{ t("context.verificationPending") }}
                </BaseBadge>
                <BaseBadge
                  v-else-if="context.verification_status === 'verified'"
                  variant="success"
                  size="sm"
                >
                  {{ t("context.verificationVerified") }}
                </BaseBadge>
                <BaseBadge
                  v-else-if="context.verification_status === 'rejected'"
                  variant="error"
                  size="sm"
                >
                  {{ t("context.verificationRejected") }}
                </BaseBadge>
                <BaseBadge
                  v-else-if="context.verification_status === 'expired'"
                  variant="warning"
                  size="sm"
                >
                  {{ t("context.verificationExpired") }}
                </BaseBadge>
                <BaseBadge v-else-if="!context.is_active" variant="warning" size="sm">
                  {{ t("context.inactive") }}
                </BaseBadge>
                <BaseBadge v-else variant="success" size="sm"> Active </BaseBadge>
              </div>
            </div>

            <h3 class="card-title">{{ context.context_name }}</h3>

            <div class="override-list">
              <div v-if="context.display_name_override" class="override-row">
                <span class="override-label">Name</span>
                <span class="override-value">{{
                  context.display_name_override
                }}</span>
              </div>
              <div v-if="context.email_override" class="override-row">
                <span class="override-label">Email</span>
                <span class="override-value">{{ context.email_override }}</span>
              </div>
              <div
                v-if="!context.display_name_override && !context.email_override"
                class="override-fallback"
              >
                Inherits all fields
              </div>
            </div>
          </BaseCard>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Page header */
.contexts-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-8);
}

/* Loading state */
.loading-container {
  text-align: center;
  padding: var(--spacing-12) 0;
}

.loading-spinner {
  margin-left: auto;
  margin-right: auto;
}

.loading-text {
  margin-top: var(--spacing-4);
  color: var(--text-secondary);
}

/* Alert spacing */
.alert-spaced {
  margin-bottom: var(--spacing-6);
}

/* Empty state */
.empty-card {
  text-align: center;
  padding: var(--spacing-12) 0;
}

.empty-icon {
  margin: 0 auto var(--spacing-4);
  width: 4rem;
  height: 4rem;
  background-color: var(--bg-tertiary);
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-2xl);
}

.empty-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin-bottom: var(--spacing-2);
}

.empty-description {
  color: var(--text-secondary);
  margin-bottom: var(--spacing-6);
  max-width: 28rem;
  margin-left: auto;
  margin-right: auto;
}

/* Contexts grid */
.contexts-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--spacing-6);
}

@media (min-width: 768px) {
  .contexts-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 1024px) {
  .contexts-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

/* Context card */
.context-card-wrapper:focus-visible {
  outline: none;
}

.context-card-wrapper:focus-visible > :deep(.card) {
  box-shadow:
    0 0 0 2px var(--bg-primary),
    0 0 0 4px var(--color-primary-500);
}

.context-card-item {
  height: 100%;
  cursor: pointer;
  border-left-width: 4px;
  transition: box-shadow var(--transition-normal);
}

.context-card-item:hover {
  box-shadow: var(--shadow-md);
}

.card-badges {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--spacing-4);
}

.badge-group {
  display: flex;
  gap: var(--spacing-1);
}

.card-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin-bottom: var(--spacing-2);
}

/* Override fields */
.override-list {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.override-list > * + * {
  margin-top: var(--spacing-2);
}

.override-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.override-label {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  color: var(--text-tertiary);
  text-transform: uppercase;
  width: 3rem;
}

.override-value {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.override-fallback {
  color: var(--text-tertiary);
  font-style: italic;
}
</style>
