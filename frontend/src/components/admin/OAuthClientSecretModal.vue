<script setup lang="ts">
import { ref } from 'vue'
import BaseModal from '@/components/common/BaseModal.vue'
import BaseButton from '@/components/common/BaseButton.vue'
import { ClipboardDocumentIcon, CheckIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/outline'

const props = defineProps<{
  isOpen: boolean
  clientId: string
  clientSecret: string | null
}>()

const emit = defineEmits<{
  close: []
}>()

const copied = ref(false)

async function copySecret(): Promise<void> {
  if (!props.clientSecret) return

  try {
    await navigator.clipboard.writeText(props.clientSecret)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy secret:', err)
  }
}

function handleClose(): void {
  emit('close')
}
</script>

<template>
  <BaseModal :is-open="isOpen" title="Client Created Successfully" @close="handleClose">
    <div class="secret-modal-content">
      <div class="warning-banner">
        <ExclamationTriangleIcon class="warning-icon" />
        <div class="warning-text">
          <strong>Important:</strong> The client secret is shown only once.
          Copy and store it securely before closing this dialog.
        </div>
      </div>

      <div class="secret-section">
        <label class="secret-label">Client ID</label>
        <code class="secret-value">{{ clientId }}</code>
      </div>

      <div v-if="clientSecret" class="secret-section">
        <label class="secret-label">Client Secret</label>
        <div class="secret-row">
          <code class="secret-value secret-value-monospace">{{ clientSecret }}</code>
          <button
            type="button"
            class="copy-btn"
            :class="{ copied }"
            @click="copySecret"
          >
            <CheckIcon v-if="copied" class="copy-icon" />
            <ClipboardDocumentIcon v-else class="copy-icon" />
            {{ copied ? 'Copied!' : 'Copy' }}
          </button>
        </div>
      </div>

      <p v-else class="no-secret-note">
        This is a public client and does not have a client secret.
      </p>
    </div>

    <template #footer>
      <BaseButton variant="primary" @click="handleClose">
        I have saved the secret
      </BaseButton>
    </template>
  </BaseModal>
</template>

<style scoped>
.secret-modal-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.warning-banner {
  display: flex;
  gap: var(--spacing-3);
  padding: var(--spacing-3) var(--spacing-4);
  background-color: var(--color-warning-50);
  border: 1px solid var(--color-warning-200);
  border-radius: var(--radius-md);
  color: var(--color-warning-800);
}

.warning-icon {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  color: var(--color-warning-500);
}

.warning-text {
  font-size: var(--font-size-sm);
  line-height: 1.5;
}

.secret-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.secret-label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
}

.secret-value {
  display: block;
  padding: var(--spacing-2) var(--spacing-3);
  background-color: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  word-break: break-all;
}

.secret-value-monospace {
  font-family: var(--font-family-mono);
}

.secret-row {
  display: flex;
  gap: var(--spacing-2);
  align-items: stretch;
}

.secret-row .secret-value {
  flex: 1;
}

.copy-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-1);
  padding: var(--spacing-2) var(--spacing-3);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-primary-600);
  background-color: var(--color-primary-50);
  border: 1px solid var(--color-primary-200);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.copy-btn:hover {
  background-color: var(--color-primary-100);
  border-color: var(--color-primary-300);
}

.copy-btn.copied {
  background-color: var(--color-success-50);
  border-color: var(--color-success-200);
  color: var(--color-success-700);
}

.copy-icon {
  width: 16px;
  height: 16px;
}

.no-secret-note {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  font-style: italic;
}
</style>
