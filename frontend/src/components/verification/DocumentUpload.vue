<script setup lang="ts">
/**
 * Document upload widget for identity verification.
 *
 * Validates file type (PDF, JPEG, PNG) and size (10 MB) before emitting
 * the selected file and document type to the parent for API submission.
 * Includes document type selection and optional expiry date input.
 */
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import BaseButton from "@/components/common/BaseButton.vue";
import BaseSelect from "@/components/common/BaseSelect.vue";
import { DocumentArrowUpIcon, DocumentIcon } from "@heroicons/vue/24/outline";
import type { DocumentType } from "@/types";

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
const ACCEPTED_TYPES = ["application/pdf", "image/jpeg", "image/png"];
const ACCEPTED_EXTENSIONS = ".pdf,.jpg,.jpeg,.png";

withDefaults(
  defineProps<{
    isUploading?: boolean;
  }>(),
  {
    isUploading: false,
  },
);

const emit = defineEmits<{
  (
    e: "upload",
    payload: { file: File; documentType: DocumentType; expiryDate: string },
  ): void;
}>();

const { t } = useI18n();

const fileInputRef = ref<HTMLInputElement | null>(null);
const selectedFile = ref<File | null>(null);
const documentType = ref<DocumentType>("passport");
const expiryDate = ref<string>("");
const validationError = ref<string | null>(null);
const isDragging = ref(false);

const documentTypeOptions = computed(() => [
  {
    value: "passport",
    label: t("verification.documentTypes.passport"),
  },
  {
    value: "national_id",
    label: t("verification.documentTypes.nationalId"),
  },
]);

const fileSizeFormatted = computed(() => {
  if (!selectedFile.value) return "";
  const bytes = selectedFile.value.size;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
});

function openFilePicker() {
  fileInputRef.value?.click();
}

function validateFile(file: File): boolean {
  validationError.value = null;

  if (!ACCEPTED_TYPES.includes(file.type)) {
    validationError.value = t("verification.upload.invalidFormat");
    return false;
  }

  if (file.size > MAX_FILE_SIZE) {
    validationError.value = t("verification.upload.fileTooLarge");
    return false;
  }

  return true;
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;

  if (validateFile(file)) {
    selectedFile.value = file;
  } else {
    input.value = "";
  }
}

function handleDragOver(event: DragEvent) {
  event.preventDefault();
  isDragging.value = true;
}

function handleDragLeave() {
  isDragging.value = false;
}

function handleDrop(event: DragEvent) {
  event.preventDefault();
  isDragging.value = false;

  const file = event.dataTransfer?.files?.[0];
  if (!file) return;

  if (validateFile(file)) {
    selectedFile.value = file;
  }
}

function clearFile() {
  selectedFile.value = null;
  expiryDate.value = "";
  validationError.value = null;
  if (fileInputRef.value) {
    fileInputRef.value.value = "";
  }
}

function handleSubmit() {
  if (!selectedFile.value || !expiryDate.value) return;
  emit("upload", {
    file: selectedFile.value,
    documentType: documentType.value,
    expiryDate: expiryDate.value,
  });
}
</script>

<template>
  <div class="document-upload">
    <div class="upload-form-field">
      <label class="field-label">
        {{ t("verification.upload.documentType") }}
      </label>
      <BaseSelect
        id="document-type"
        :model-value="documentType"
        :options="documentTypeOptions"
        :disabled="isUploading"
        @update:model-value="documentType = $event as DocumentType"
      />
    </div>

    <div class="upload-form-field">
      <label class="field-label" for="expiry-date">
        {{ t("verification.upload.expiryDate") }}
        <span class="required">*</span>
      </label>
      <input
        id="expiry-date"
        v-model="expiryDate"
        type="date"
        class="form-input"
        :min="new Date().toISOString().split('T')[0]"
        :disabled="isUploading"
      />
      <p class="field-hint">
        {{ t("verification.upload.expiryDateHint") }}
      </p>
    </div>

    <!-- Drop zone / file picker -->
    <div
      v-if="!selectedFile"
      class="drop-zone"
      :class="{ 'drop-zone-active': isDragging }"
      @dragover="handleDragOver"
      @dragleave="handleDragLeave"
      @drop="handleDrop"
      @click="openFilePicker"
    >
      <input
        ref="fileInputRef"
        type="file"
        :accept="ACCEPTED_EXTENSIONS"
        class="sr-only"
        @change="handleFileChange"
      />
      <DocumentArrowUpIcon class="drop-zone-icon" />
      <p class="drop-zone-text">
        {{ t("verification.upload.dropZoneText") }}
      </p>
      <p class="drop-zone-hint">
        {{ t("verification.upload.dropZoneHint") }}
      </p>
    </div>

    <!-- Selected file preview -->
    <div v-else class="file-preview">
      <div class="file-info">
        <DocumentIcon class="file-icon" />
        <div class="file-details">
          <span class="file-name">{{ selectedFile.name }}</span>
          <span class="file-size">{{ fileSizeFormatted }}</span>
        </div>
      </div>
      <div class="file-actions">
        <BaseButton
          variant="ghost"
          size="sm"
          :disabled="isUploading"
          @click="clearFile"
        >
          {{ t("verification.upload.changeFile") }}
        </BaseButton>
      </div>
    </div>

    <!-- Validation error -->
    <p v-if="validationError" class="form-error upload-error">
      {{ validationError }}
    </p>

    <!-- Submit -->
    <BaseButton
      v-if="selectedFile"
      :loading="isUploading"
      :disabled="!selectedFile || !expiryDate"
      @click="handleSubmit"
    >
      {{ t("verification.upload.submit") }}
    </BaseButton>
  </div>
</template>

<style scoped>
.document-upload {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

.upload-form-field {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.field-label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

.field-label .required {
  color: var(--color-error-500);
}

.field-hint {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  margin: 0;
}

.form-input {
  width: 100%;
  padding: var(--spacing-2) var(--spacing-3);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  background-color: var(--bg-primary);
}

.form-input:focus {
  outline: none;
  border-color: var(--color-primary-500);
  box-shadow: 0 0 0 2px var(--color-primary-100);
}

/* Drop zone */
.drop-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-10) var(--spacing-6);
  border: 2px dashed var(--border-primary);
  border-radius: var(--radius-lg);
  background-color: var(--bg-secondary);
  cursor: pointer;
  transition:
    border-color var(--transition-fast),
    background-color var(--transition-fast);
}

.drop-zone:hover {
  border-color: var(--color-primary-400);
  background-color: var(--color-primary-50);
}

.drop-zone-active {
  border-color: var(--color-primary-500);
  background-color: var(--color-primary-50);
}

:global(.dark) .drop-zone:hover,
:global(.dark) .drop-zone-active {
  background-color: rgba(59, 130, 246, 0.08);
}

.drop-zone-icon {
  width: 40px;
  height: 40px;
  color: var(--text-tertiary);
  margin-bottom: var(--spacing-3);
}

.drop-zone-text {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  margin: 0 0 var(--spacing-1) 0;
}

.drop-zone-hint {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  margin: 0;
}

/* File preview */
.file-preview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-3) var(--spacing-4);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  background-color: var(--bg-secondary);
}

.file-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  min-width: 0;
}

.file-icon {
  width: 24px;
  height: 24px;
  color: var(--color-primary-500);
  flex-shrink: 0;
}

.file-details {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.file-name {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-size {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.file-actions {
  flex-shrink: 0;
}

.upload-error {
  margin: 0;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
</style>
