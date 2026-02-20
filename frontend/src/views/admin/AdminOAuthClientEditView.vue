<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { adminOAuthService, getErrorMessage } from "@/services";
import type { OAuthClientResponse, OAuthClientUpdate } from "@/types";
import BaseCard from "@/components/common/BaseCard.vue";
import OAuthClientForm from "@/components/admin/OAuthClientForm.vue";
import AppBreadcrumb from "@/components/layout/AppBreadcrumb.vue";

const router = useRouter();
const route = useRoute();

const client = ref<OAuthClientResponse | null>(null);
const isLoading = ref(true);
const isSaving = ref(false);
const error = ref<string | null>(null);
const saveError = ref<string | null>(null);

const clientId = route.params.clientId as string;

onMounted(async () => {
  try {
    client.value = await adminOAuthService.getClient(clientId);
  } catch (err) {
    error.value = getErrorMessage(err);
  } finally {
    isLoading.value = false;
  }
});

async function handleSubmit(data: OAuthClientUpdate): Promise<void> {
  isSaving.value = true;
  saveError.value = null;

  try {
    await adminOAuthService.updateClient(clientId, data);
    router.push({ name: "admin-oauth-clients" });
  } catch (err) {
    saveError.value = getErrorMessage(err);
  } finally {
    isSaving.value = false;
  }
}

function handleCancel(): void {
  router.push({ name: "admin-oauth-clients" });
}
</script>

<template>
  <div class="admin-oauth-client-edit-view">
    <div class="container container-lg">
      <AppBreadcrumb />

      <div class="page-header">
        <h1 class="page-title">Edit OAuth Client</h1>
        <p class="page-description">
          Update the configuration for this OAuth client.
        </p>
      </div>

      <div v-if="isLoading" class="loading-state">
        <div class="spinner spinner-lg"></div>
        <p class="loading-text">Loading client...</p>
      </div>

      <div v-else-if="error" class="alert alert-error">
        {{ error }}
      </div>

      <template v-else-if="client">
        <div v-if="saveError" class="alert alert-error">
          {{ saveError }}
        </div>

        <BaseCard>
          <OAuthClientForm
            mode="edit"
            :initial-data="client"
            :is-loading="isSaving"
            @submit="handleSubmit"
            @cancel="handleCancel"
          />
        </BaseCard>
      </template>
    </div>
  </div>
</template>

<style scoped>
.admin-oauth-client-edit-view {
  padding: var(--spacing-8) 0;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--spacing-12) 0;
}

.loading-text {
  margin-top: var(--spacing-4);
  color: var(--text-tertiary);
}

.alert-error {
  padding: var(--spacing-4);
  background-color: var(--color-error-50);
  border: 1px solid var(--color-error-200);
  border-radius: var(--radius-md);
  color: var(--color-error-700);
  margin-bottom: var(--spacing-6);
}
</style>
