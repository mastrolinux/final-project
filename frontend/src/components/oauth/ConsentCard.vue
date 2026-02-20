<script setup lang="ts">
import type { OAuthConsent } from "@/types";
import { useI18n } from "vue-i18n";
import BaseCard from "@/components/common/BaseCard.vue";
import BaseBadge from "@/components/common/BaseBadge.vue";
import BaseButton from "@/components/common/BaseButton.vue";
import { TrashIcon } from "@heroicons/vue/24/outline";

defineProps<{
  consent: OAuthConsent;
}>();

const emit = defineEmits<{
  revoke: [consent: OAuthConsent];
}>();

const { t, locale } = useI18n();

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString(locale.value, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}
</script>

<template>
  <BaseCard>
    <div class="consent-card">
      <div class="consent-header">
        <div class="consent-info">
          <h3 class="consent-client-name">{{ consent.client_name }}</h3>
          <code class="consent-client-id">{{ consent.client_id }}</code>
        </div>
        <div class="consent-badges">
          <BaseBadge variant="success" size="sm">
            {{ t("context.active") }}
          </BaseBadge>
        </div>
      </div>

      <div class="consent-scopes">
        <span class="scopes-label">{{ t("oauth.grantedScopes") }}</span>
        <div class="scope-badges">
          <BaseBadge
            v-for="scope in consent.granted_scopes"
            :key="scope"
            variant="neutral"
            size="sm"
          >
            {{ scope }}
          </BaseBadge>
        </div>
      </div>

      <div class="consent-meta">
        <div v-if="consent.context_profile_id" class="meta-item">
          <span class="meta-label">{{ t("oauth.boundToContext") }}:</span>
          <span class="meta-value">{{ consent.context_profile_id }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">{{ t("oauth.grantedOn") }}:</span>
          <span class="meta-value">{{ formatDate(consent.granted_at) }}</span>
        </div>
        <div v-if="consent.expires_at" class="meta-item">
          <span class="meta-label">{{ t("oauth.expiresOn") }}:</span>
          <span class="meta-value">{{ formatDate(consent.expires_at) }}</span>
        </div>
      </div>

      <div class="consent-actions">
        <BaseButton variant="danger" size="sm" @click="emit('revoke', consent)">
          <TrashIcon class="icon" />
          {{ t("oauth.revokeAccess") }}
        </BaseButton>
      </div>
    </div>
  </BaseCard>
</template>

<style scoped>
.consent-card {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.consent-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-4);
  flex-wrap: wrap;
}

.consent-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.consent-client-name {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin: 0;
}

.consent-client-id {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  background-color: var(--bg-tertiary);
  padding: var(--spacing-1) var(--spacing-2);
  border-radius: var(--radius-sm);
}

.consent-badges {
  display: flex;
  gap: var(--spacing-2);
  flex-wrap: wrap;
}

.consent-scopes {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.scopes-label {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
}

.scope-badges {
  display: flex;
  gap: var(--spacing-2);
  flex-wrap: wrap;
}

.consent-meta {
  display: flex;
  gap: var(--spacing-6);
  flex-wrap: wrap;
  padding-top: var(--spacing-2);
  border-top: 1px solid var(--border-primary);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.meta-label {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
}

.meta-value {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

.consent-actions {
  display: flex;
  gap: var(--spacing-2);
  padding-top: var(--spacing-2);
}

.icon {
  width: 16px;
  height: 16px;
  margin-right: var(--spacing-1);
}
</style>
