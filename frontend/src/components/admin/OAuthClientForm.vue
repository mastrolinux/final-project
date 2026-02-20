<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import type {
  OAuthClientCreate,
  OAuthClientUpdate,
  OAuthClientResponse,
  ScopeInfo,
} from "@/types";
import { adminOAuthService } from "@/services";
import BaseInput from "@/components/common/BaseInput.vue";
import BaseButton from "@/components/common/BaseButton.vue";
import { PlusIcon, XMarkIcon } from "@heroicons/vue/24/outline";

const props = withDefaults(
  defineProps<{
    mode: "create" | "edit";
    initialData?: OAuthClientResponse;
    isLoading?: boolean;
  }>(),
  {
    isLoading: false,
  },
);

const emit = defineEmits<{
  submit: [data: OAuthClientCreate | OAuthClientUpdate];
  cancel: [];
}>();

// Default scopes for new clients (OIDC standard + basic profile)
const DEFAULT_SCOPES = ["openid", "profile:read:basic"];

// Form state
const clientId = ref("");
const clientName = ref("");
const clientDescription = ref("");
const clientUri = ref("");
const redirectUris = ref<string[]>([""]);
const selectedScopes = ref<string[]>([]);
const isConfidential = ref(false);
const isFirstParty = ref(false);
const isActive = ref(true);

// Available scopes from backend
const availableScopes = ref<ScopeInfo[]>([]);
const scopesLoading = ref(true);
const scopesError = ref<string | null>(null);

// Validation errors
const errors = ref<Record<string, string>>({});

// Fetch available scopes on mount
onMounted(async () => {
  try {
    const response = await adminOAuthService.fetchScopes();
    availableScopes.value = response.scopes;

    // Pre-select default scopes for new clients
    if (props.mode === "create" && selectedScopes.value.length === 0) {
      selectedScopes.value = DEFAULT_SCOPES.filter((scope: string) =>
        response.scopes.some((s: ScopeInfo) => s.scope_name === scope),
      );
    }
  } catch (err) {
    scopesError.value = "Failed to load available scopes";
    console.error("Failed to fetch scopes:", err);
  } finally {
    scopesLoading.value = false;
  }
});

// Initialize form with existing data for edit mode
watch(
  () => props.initialData,
  (data) => {
    if (data && props.mode === "edit") {
      clientId.value = data.client_id;
      clientName.value = data.client_name;
      clientDescription.value = data.client_description || "";
      clientUri.value = data.client_uri || "";
      redirectUris.value =
        data.redirect_uris.length > 0 ? [...data.redirect_uris] : [""];
      selectedScopes.value = [...data.allowed_scopes];
      isConfidential.value = data.is_confidential;
      isFirstParty.value = data.is_first_party;
      isActive.value = data.is_active;
    }
  },
  { immediate: true },
);

function toggleScope(scopeName: string): void {
  const index = selectedScopes.value.indexOf(scopeName);
  if (index === -1) {
    selectedScopes.value.push(scopeName);
  } else {
    selectedScopes.value.splice(index, 1);
  }
}

function isScopeSelected(scopeName: string): boolean {
  return selectedScopes.value.includes(scopeName);
}

const isCreateMode = computed(() => props.mode === "create");

function addRedirectUri(): void {
  redirectUris.value.push("");
}

function removeRedirectUri(index: number): void {
  if (redirectUris.value.length > 1) {
    redirectUris.value.splice(index, 1);
  }
}

function validate(): boolean {
  errors.value = {};

  if (isCreateMode.value && !clientId.value.trim()) {
    errors.value.clientId = "Client ID is required";
  } else if (isCreateMode.value && !/^[a-zA-Z0-9_-]+$/.test(clientId.value)) {
    errors.value.clientId =
      "Client ID can only contain letters, numbers, underscores, and hyphens";
  }

  if (!clientName.value.trim()) {
    errors.value.clientName = "Client name is required";
  }

  const validUris = redirectUris.value.filter((uri) => uri.trim());
  if (validUris.length === 0) {
    errors.value.redirectUris = "At least one redirect URI is required";
  } else {
    for (const uri of validUris) {
      try {
        new URL(uri);
      } catch {
        errors.value.redirectUris = "All redirect URIs must be valid URLs";
        break;
      }
    }
  }

  return Object.keys(errors.value).length === 0;
}

function handleSubmit(): void {
  if (!validate()) return;

  const validUris = redirectUris.value.filter((uri) => uri.trim());

  if (isCreateMode.value) {
    const data: OAuthClientCreate = {
      client_id: clientId.value.trim(),
      client_name: clientName.value.trim(),
      client_description: clientDescription.value.trim() || undefined,
      client_uri: clientUri.value.trim() || undefined,
      redirect_uris: validUris,
      allowed_scopes:
        selectedScopes.value.length > 0 ? [...selectedScopes.value] : undefined,
      is_confidential: isConfidential.value,
      is_first_party: isFirstParty.value,
    };
    emit("submit", data);
  } else {
    const data: OAuthClientUpdate = {
      client_name: clientName.value.trim(),
      client_description: clientDescription.value.trim() || null,
      client_uri: clientUri.value.trim() || null,
      redirect_uris: validUris,
      allowed_scopes: [...selectedScopes.value],
      is_first_party: isFirstParty.value,
      is_active: isActive.value,
    };
    emit("submit", data);
  }
}
</script>

<template>
  <form class="oauth-client-form" @submit.prevent="handleSubmit">
    <BaseInput
      v-if="isCreateMode"
      id="client-id"
      v-model="clientId"
      label="Client ID"
      placeholder="my-app-client"
      hint="Unique identifier for the client (letters, numbers, hyphens, underscores)"
      :error="errors.clientId"
      :disabled="isLoading"
      required
    />

    <div v-else class="form-group">
      <label class="form-label">Client ID</label>
      <code class="readonly-value">{{ initialData?.client_id }}</code>
    </div>

    <BaseInput
      id="client-name"
      v-model="clientName"
      label="Client Name"
      placeholder="My Application"
      hint="Display name shown on consent screen"
      :error="errors.clientName"
      :disabled="isLoading"
      required
    />

    <BaseInput
      id="client-description"
      v-model="clientDescription"
      label="Description"
      placeholder="A brief description of your application"
      :disabled="isLoading"
    />

    <BaseInput
      id="client-uri"
      v-model="clientUri"
      label="Homepage URL"
      type="url"
      placeholder="https://example.com"
      :disabled="isLoading"
    />

    <div class="form-group">
      <label class="form-label">
        Redirect URIs
        <span class="text-error" aria-hidden="true">*</span>
      </label>
      <div class="redirect-uris">
        <div
          v-for="(_uri, index) in redirectUris"
          :key="index"
          class="redirect-uri-row"
        >
          <input
            v-model="redirectUris[index]"
            type="url"
            class="form-input"
            :class="{ 'has-error': errors.redirectUris }"
            placeholder="https://example.com/callback"
            :disabled="isLoading"
          />
          <button
            v-if="redirectUris.length > 1"
            type="button"
            class="btn-icon"
            :disabled="isLoading"
            @click="removeRedirectUri(index)"
          >
            <XMarkIcon class="icon" />
          </button>
        </div>
        <button
          type="button"
          class="add-uri-btn"
          :disabled="isLoading"
          @click="addRedirectUri"
        >
          <PlusIcon class="icon" />
          Add Redirect URI
        </button>
      </div>
      <p v-if="errors.redirectUris" class="form-error" role="alert">
        {{ errors.redirectUris }}
      </p>
      <p v-else class="form-hint">
        Exact match required for OAuth 2.1 security
      </p>
    </div>

    <div class="form-group">
      <label class="form-label">Allowed Scopes</label>
      <div v-if="scopesLoading" class="scopes-loading">
        Loading available scopes...
      </div>
      <div v-else-if="scopesError" class="scopes-error">
        {{ scopesError }}
      </div>
      <div v-else class="scopes-grid">
        <label
          v-for="scope in availableScopes"
          :key="scope.scope_name"
          class="scope-checkbox"
          :class="{ 'scope-sensitive': scope.is_sensitive }"
        >
          <input
            type="checkbox"
            :checked="isScopeSelected(scope.scope_name)"
            :disabled="isLoading"
            @change="toggleScope(scope.scope_name)"
          />
          <span class="scope-info">
            <span class="scope-name">{{ scope.scope_name }}</span>
            <span class="scope-description">{{ scope.description }}</span>
          </span>
        </label>
      </div>
      <p class="form-hint">
        Select the scopes this client is allowed to request
      </p>
    </div>

    <div class="checkbox-group">
      <label class="checkbox-label">
        <input
          v-model="isConfidential"
          type="checkbox"
          :disabled="isLoading || !isCreateMode"
        />
        <span>Confidential Client</span>
      </label>
      <p class="checkbox-hint">
        Server-side applications that can securely store secrets
      </p>
    </div>

    <div class="checkbox-group">
      <label class="checkbox-label">
        <input v-model="isFirstParty" type="checkbox" :disabled="isLoading" />
        <span>First Party Application</span>
      </label>
      <p class="checkbox-hint">First-party apps can skip the consent screen</p>
    </div>

    <div v-if="!isCreateMode" class="checkbox-group">
      <label class="checkbox-label">
        <input v-model="isActive" type="checkbox" :disabled="isLoading" />
        <span>Active</span>
      </label>
      <p class="checkbox-hint">
        Inactive clients cannot be used for new authorizations
      </p>
    </div>

    <div class="form-actions">
      <BaseButton
        variant="secondary"
        type="button"
        :disabled="isLoading"
        @click="emit('cancel')"
      >
        Cancel
      </BaseButton>
      <BaseButton variant="primary" type="submit" :loading="isLoading">
        {{ isCreateMode ? "Create Client" : "Save Changes" }}
      </BaseButton>
    </div>
  </form>
</template>

<style scoped>
.oauth-client-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.form-group {
  margin-bottom: 0;
}

.form-label {
  display: block;
  margin-bottom: var(--spacing-1);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

.readonly-value {
  display: block;
  padding: var(--spacing-2) var(--spacing-3);
  font-size: var(--font-size-base);
  background-color: var(--bg-tertiary);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
}

.redirect-uris {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.redirect-uri-row {
  display: flex;
  gap: var(--spacing-2);
}

.redirect-uri-row .form-input {
  flex: 1;
  padding: var(--spacing-2) var(--spacing-3);
  font-size: var(--font-size-base);
  color: var(--text-primary);
  background-color: var(--input-bg);
  border: 1px solid var(--input-border);
  border-radius: var(--radius-md);
  transition:
    border-color var(--transition-fast),
    box-shadow var(--transition-fast);
}

.redirect-uri-row .form-input:focus {
  border-color: var(--color-primary-500);
  outline: 0;
  box-shadow: 0 0 0 2px var(--color-primary-100);
}

.redirect-uri-row .form-input.has-error {
  border-color: var(--color-error-500);
}

.btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  padding: 0;
  background-color: transparent;
  border: 1px solid var(--border-secondary);
  border-radius: var(--radius-md);
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-icon:hover:not(:disabled) {
  background-color: var(--color-error-50);
  border-color: var(--color-error-200);
  color: var(--color-error-600);
}

.btn-icon:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.add-uri-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-1);
  padding: var(--spacing-2) var(--spacing-3);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-primary-600);
  background-color: transparent;
  border: 1px dashed var(--color-primary-300);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  align-self: flex-start;
}

.add-uri-btn:hover:not(:disabled) {
  background-color: var(--color-primary-50);
  border-color: var(--color-primary-400);
}

.add-uri-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.icon {
  width: 16px;
  height: 16px;
}

.form-error {
  margin-top: var(--spacing-1);
  font-size: var(--font-size-sm);
  color: var(--color-error-600);
}

.form-hint {
  margin-top: var(--spacing-1);
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
}

.text-error {
  color: var(--color-error-600);
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  accent-color: var(--color-primary-600);
  cursor: pointer;
}

.checkbox-label input[type="checkbox"]:disabled {
  cursor: not-allowed;
}

.checkbox-hint {
  margin-left: 26px;
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-3);
  padding-top: var(--spacing-4);
  border-top: 1px solid var(--border-primary);
  margin-top: var(--spacing-4);
}

.scopes-loading,
.scopes-error {
  padding: var(--spacing-3);
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  background-color: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.scopes-error {
  color: var(--color-error-600);
  background-color: var(--color-error-50);
}

.scopes-grid {
  display: grid;
  gap: var(--spacing-2);
  max-height: 300px;
  overflow-y: auto;
  padding: var(--spacing-3);
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
}

.scope-checkbox {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-2);
  padding: var(--spacing-2);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.scope-checkbox:hover {
  background-color: var(--bg-tertiary);
}

.scope-checkbox input[type="checkbox"] {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  margin-top: 2px;
  accent-color: var(--color-primary-600);
  cursor: pointer;
}

.scope-checkbox input[type="checkbox"]:disabled {
  cursor: not-allowed;
}

.scope-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.scope-name {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  font-family: var(--font-mono, monospace);
}

.scope-description {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  line-height: 1.4;
}

.scope-sensitive .scope-name {
  color: var(--color-warning-700);
}

.scope-sensitive .scope-name::after {
  content: " (sensitive)";
  font-weight: var(--font-weight-normal);
  font-size: var(--font-size-xs);
}
</style>
