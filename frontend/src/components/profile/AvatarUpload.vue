<script setup lang="ts">
/**
 * Avatar upload widget with file validation, local preview, and action buttons.
 *
 * Validates file size (5 MB) and MIME type (JPEG, PNG, WebP) before displaying
 * a preview. Emits upload/remove events to let the parent coordinate with the API.
 */
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import AvatarDisplay from "@/components/common/AvatarDisplay.vue";
import BaseButton from "@/components/common/BaseButton.vue";

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MB
const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];

const props = withDefaults(
  defineProps<{
    /** Current avatar URL (null when no avatar is set). */
    currentUrl?: string | null;
    /** Display name for the initials fallback. */
    name?: string;
    /** Whether an upload operation is in progress. */
    isUploading?: boolean;
    /**
     * When true, selecting a file emits @upload immediately without a
     * confirmation step.  Use this in forms where the actual upload is
     * deferred until the parent submits (e.g. context creation).
     */
    deferred?: boolean;
  }>(),
  {
    currentUrl: null,
    name: "",
    isUploading: false,
    deferred: false,
  },
);

const emit = defineEmits<{
  (e: "upload", file: File): void;
  (e: "remove"): void;
}>();

const { t } = useI18n();

const fileInputRef = ref<HTMLInputElement | null>(null);
const previewUrl = ref<string | null>(null);
const selectedFile = ref<File | null>(null);
const validationError = ref<string | null>(null);

const displayUrl = computed(() => previewUrl.value || props.currentUrl);
const hasAvatar = computed(() => !!props.currentUrl);
const hasPreview = computed(() => !!previewUrl.value);

function openFilePicker() {
  fileInputRef.value?.click();
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;

  // Reset previous state
  validationError.value = null;
  clearPreview();

  // Validate MIME type
  if (!ACCEPTED_TYPES.includes(file.type)) {
    validationError.value = t("profile.avatar.invalidFormat");
    input.value = "";
    return;
  }

  // Validate file size
  if (file.size > MAX_FILE_SIZE) {
    validationError.value = t("profile.avatar.fileTooLarge");
    input.value = "";
    return;
  }

  // Show local preview
  selectedFile.value = file;
  previewUrl.value = URL.createObjectURL(file);

  // In deferred mode, emit immediately so the parent can store
  // the file for upload after form submission.
  if (props.deferred) {
    emit("upload", file);
  }
}

function confirmUpload() {
  if (selectedFile.value) {
    emit("upload", selectedFile.value);
    // Clear preview after emitting (parent handles success/error)
    clearPreview();
  }
}

function cancelPreview() {
  clearPreview();
  if (fileInputRef.value) {
    fileInputRef.value.value = "";
  }
}

function clearPreview() {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value);
  }
  previewUrl.value = null;
  selectedFile.value = null;
}

function handleDeferredRemove() {
  clearPreview();
  if (fileInputRef.value) {
    fileInputRef.value.value = "";
  }
  emit("remove");
}

function handleRemove() {
  emit("remove");
}
</script>

<template>
  <div class="avatar-upload">
    <div class="avatar-upload-preview">
      <div class="avatar-upload-image-wrapper">
        <AvatarDisplay :src="displayUrl" :name="name" size="xl" />
        <div v-if="isUploading" class="avatar-upload-overlay">
          <div class="spinner spinner-sm"></div>
        </div>
      </div>
    </div>

    <div class="avatar-upload-controls">
      <!-- Hidden file input -->
      <input
        ref="fileInputRef"
        type="file"
        accept=".jpg,.jpeg,.png,.webp"
        class="sr-only"
        @change="handleFileChange"
      />

      <!-- Validation error -->
      <p v-if="validationError" class="form-error avatar-upload-error">
        {{ validationError }}
      </p>

      <!-- Preview mode (deferred): file already emitted, allow change/remove -->
      <template v-if="hasPreview && deferred && !isUploading">
        <div class="avatar-upload-actions">
          <BaseButton variant="secondary" size="sm" @click="openFilePicker">
            {{ t("profile.avatar.change") }}
          </BaseButton>
          <BaseButton variant="ghost" size="sm" @click="handleDeferredRemove">
            {{ t("profile.avatar.remove") }}
          </BaseButton>
        </div>
      </template>

      <!-- Preview mode (immediate): confirm or cancel before API call -->
      <template v-else-if="hasPreview && !isUploading">
        <div class="avatar-upload-actions">
          <BaseButton size="sm" @click="confirmUpload">
            {{ t("profile.avatar.upload") }}
          </BaseButton>
          <BaseButton variant="ghost" size="sm" @click="cancelPreview">
            {{ t("common.cancel") }}
          </BaseButton>
        </div>
      </template>

      <!-- Normal mode: change or remove -->
      <template v-else-if="!isUploading">
        <div class="avatar-upload-actions">
          <BaseButton variant="secondary" size="sm" @click="openFilePicker">
            {{
              hasAvatar
                ? t("profile.avatar.change")
                : t("profile.avatar.upload")
            }}
          </BaseButton>
          <BaseButton
            v-if="hasAvatar"
            variant="ghost"
            size="sm"
            @click="handleRemove"
          >
            {{ t("profile.avatar.remove") }}
          </BaseButton>
        </div>
      </template>

      <!-- Uploading state -->
      <template v-else>
        <p class="avatar-upload-status">{{ t("profile.avatar.uploading") }}</p>
      </template>
    </div>
  </div>
</template>

<style scoped>
.avatar-upload {
  display: flex;
  align-items: center;
  gap: var(--spacing-5);
}

.avatar-upload-preview {
  flex-shrink: 0;
}

.avatar-upload-image-wrapper {
  position: relative;
}

.avatar-upload-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(0, 0, 0, 0.4);
  border-radius: var(--radius-full);
}

.avatar-upload-controls {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.avatar-upload-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.avatar-upload-error {
  margin: 0;
}

.avatar-upload-status {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
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
