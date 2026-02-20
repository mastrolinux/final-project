<script setup lang="ts">
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import type { OAuthScope } from "@/types";
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ChevronDownIcon,
  ChevronUpIcon,
} from "@heroicons/vue/24/outline";

const props = withDefaults(
  defineProps<{
    scopes: OAuthScope[];
    selectable?: boolean;
    selectedScopes?: string[];
    expandable?: boolean;
  }>(),
  {
    selectable: false,
    selectedScopes: () => [],
    expandable: false,
  },
);

const emit = defineEmits<{
  "update:selectedScopes": [scopes: string[]];
}>();

const { t } = useI18n();

/**
 * Mapping from scope name to the specific fields it grants access to.
 * Derived from backend oauth_service.py SCOPE_FIELDS dict.
 */
const SCOPE_FIELDS: Record<string, string[]> = {
  openid: ["User identifier (sub)"],
  "profile:read:basic": ["Display name", "Preferred name", "Account type"],
  "profile:read:email": ["Email address", "Email verification status"],
  "profile:read:phone": ["Phone number", "Phone verification status"],
  "profile:read:full": [
    "Display name",
    "Email",
    "Phone",
    "Bio",
    "Avatar",
    "Account type",
  ],
  "contexts:read": ["Context type", "Context name"],
  "contexts:professional:read": [
    "Professional credentials",
    "Organization",
    "Website",
  ],
  "contexts:social:read": ["Social handles", "Interests"],
  "contexts:legal:read": ["Legal name", "Government ID reference"],
  "contexts:healthcare:read": [
    "Healthcare provider",
    "Medical record reference",
  ],
  email: ["Email address"],
  phone: ["Phone number"],
  offline_access: ["Long-lived refresh token"],
};

/** The openid scope is always required per OIDC specification. */
const REQUIRED_SCOPES = new Set(["openid"]);

const expandedScopes = ref<Set<string>>(new Set());

function isRequired(scopeName: string): boolean {
  return REQUIRED_SCOPES.has(scopeName);
}

function isSelected(scopeName: string): boolean {
  return props.selectedScopes.includes(scopeName);
}

function toggleScope(scopeName: string): void {
  if (isRequired(scopeName)) return;
  const current = [...props.selectedScopes];
  const index = current.indexOf(scopeName);
  if (index >= 0) {
    current.splice(index, 1);
  } else {
    current.push(scopeName);
  }
  emit("update:selectedScopes", current);
}

function toggleExpand(scopeName: string): void {
  const expanded = new Set(expandedScopes.value);
  if (expanded.has(scopeName)) {
    expanded.delete(scopeName);
  } else {
    expanded.add(scopeName);
  }
  expandedScopes.value = expanded;
}

function isExpanded(scopeName: string): boolean {
  return expandedScopes.value.has(scopeName);
}

function getFields(scopeName: string): string[] {
  return SCOPE_FIELDS[scopeName] || [];
}
</script>

<template>
  <div class="scope-list">
    <div v-for="scope in scopes" :key="scope.scope_name" class="scope-item">
      <div class="scope-row">
        <!-- Checkbox for selectable mode -->
        <div v-if="selectable" class="scope-checkbox">
          <input
            type="checkbox"
            :checked="isSelected(scope.scope_name)"
            :disabled="isRequired(scope.scope_name)"
            @change="toggleScope(scope.scope_name)"
          />
        </div>

        <!-- Icon -->
        <div class="scope-icon">
          <ExclamationTriangleIcon
            v-if="scope.is_sensitive"
            class="icon text-warning"
          />
          <CheckCircleIcon v-else class="icon text-success" />
        </div>

        <!-- Content -->
        <div
          class="scope-content"
          :class="{ clickable: expandable }"
          @click="expandable ? toggleExpand(scope.scope_name) : undefined"
        >
          <h4 class="scope-name">{{ scope.scope_name }}</h4>
          <p class="scope-description">{{ scope.description }}</p>
        </div>

        <!-- Badges -->
        <div class="scope-badges">
          <span
            v-if="selectable && isRequired(scope.scope_name)"
            class="badge badge-primary"
          >
            {{ t("oauth.requiredScope") }}
          </span>
          <span v-if="scope.is_sensitive" class="badge badge-warning">
            Sensitive
          </span>
        </div>

        <!-- Expand chevron -->
        <div
          v-if="expandable && getFields(scope.scope_name).length > 0"
          class="scope-expand"
          @click="toggleExpand(scope.scope_name)"
        >
          <ChevronUpIcon
            v-if="isExpanded(scope.scope_name)"
            class="chevron-icon"
          />
          <ChevronDownIcon v-else class="chevron-icon" />
        </div>
      </div>

      <!-- Expanded detail panel -->
      <div
        v-if="expandable && isExpanded(scope.scope_name)"
        class="scope-detail"
      >
        <p class="detail-label">{{ t("oauth.scopeFields") }}:</p>
        <ul class="detail-fields">
          <li
            v-for="field in getFields(scope.scope_name)"
            :key="field"
            class="detail-field"
          >
            {{ field }}
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
.scope-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.scope-item {
  background-color: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  overflow: hidden;
}

.scope-row {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-3);
  padding: var(--spacing-3);
}

.scope-checkbox {
  flex-shrink: 0;
  margin-top: 2px;
}

.scope-checkbox input[type="checkbox"] {
  width: 16px;
  height: 16px;
  accent-color: var(--color-primary-600);
  cursor: pointer;
}

.scope-checkbox input[type="checkbox"]:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.scope-icon {
  flex-shrink: 0;
  margin-top: 2px;
}

.icon {
  width: 20px;
  height: 20px;
}

.text-success {
  color: var(--color-success-600);
}

.text-warning {
  color: var(--color-warning-600);
}

.scope-content {
  flex: 1;
}

.scope-content.clickable {
  cursor: pointer;
}

.scope-name {
  font-size: var(--font-size-sm);
  font-weight: 600;
  margin: 0 0 2px 0;
  color: var(--text-primary);
}

.scope-description {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.4;
}

.scope-badges {
  display: flex;
  gap: var(--spacing-2);
  flex-shrink: 0;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 6px;
  border-radius: 9999px;
  font-size: 10px;
  font-weight: 500;
  background-color: var(--color-gray-100);
  color: var(--color-gray-700);
}

.badge-warning {
  background-color: var(--color-warning-100);
  color: var(--color-warning-700);
}

.badge-primary {
  background-color: var(--color-primary-100);
  color: var(--color-primary-700);
}

.scope-expand {
  flex-shrink: 0;
  cursor: pointer;
  padding: var(--spacing-1);
  border-radius: var(--radius-sm);
}

.scope-expand:hover {
  background-color: var(--bg-tertiary);
}

.chevron-icon {
  width: 16px;
  height: 16px;
  color: var(--text-tertiary);
}

.scope-detail {
  padding: 0 var(--spacing-3) var(--spacing-3);
  border-top: 1px solid var(--border-color);
  margin-top: 0;
  padding-top: var(--spacing-3);
  margin-left: var(--spacing-3);
  margin-right: var(--spacing-3);
}

.detail-label {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  margin: 0 0 var(--spacing-2) 0;
}

.detail-fields {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.detail-field {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  padding-left: var(--spacing-3);
  position: relative;
}

.detail-field::before {
  content: "";
  position: absolute;
  left: 0;
  top: 50%;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background-color: var(--text-tertiary);
  transform: translateY(-50%);
}
</style>
