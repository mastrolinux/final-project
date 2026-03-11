<script setup lang="ts">
import { ref } from "vue";
import { useProfileStore } from "@/stores";
import { profileService, getErrorMessage } from "@/services";
import type { IdentityName, NameType } from "@/types";
import BaseButton from "@/components/common/BaseButton.vue";
import BaseInput from "@/components/common/BaseInput.vue";
import BaseSelect from "@/components/common/BaseSelect.vue";
import BaseBadge from "@/components/common/BaseBadge.vue";
import BaseModal from "@/components/common/BaseModal.vue";

const profileStore = useProfileStore();

const isAdding = ref(false);
const isSaving = ref(false);
const isDeleting = ref(false);
const error = ref<string | null>(null);
const editingId = ref<string | null>(null);
const showDeleteConfirm = ref(false);
const deleteId = ref<string | null>(null);

const nameTypes: { label: string; value: NameType }[] = [
  { label: "Full Name", value: "full_name" },
  { label: "Given Name", value: "given" },
  { label: "Family Name", value: "family" },
  { label: "Preferred Name", value: "preferred" },
  { label: "Legal Name", value: "legal" },
  { label: "Patronymic", value: "patronymic" },
  { label: "Nickname", value: "custom" },
];

const languageOptions = [
  { label: "English (en)", value: "en" },
  { label: "Chinese (zh)", value: "zh" },
  { label: "Spanish (es)", value: "es" },
  { label: "Arabic (ar)", value: "ar" },
  { label: "Italian (it)", value: "it" },
  { label: "Indonesian (id)", value: "id" },
];

const form = ref({
  name_type: "preferred" as NameType,
  language: "en",
  value: "",
  is_primary: false,
});

function resetForm() {
  form.value = {
    name_type: "preferred",
    language: "en",
    value: "",
    is_primary: false,
  };
  editingId.value = null;
  error.value = null;
}

function startAdding() {
  resetForm();
  isAdding.value = true;
}

function startEditing(name: IdentityName) {
  const lang = Object.keys(name.name_value)[0] || "en";
  const val = Object.values(name.name_value)[0] || "";

  form.value = {
    name_type: name.name_type,
    language: lang,
    value: val,
    is_primary: name.is_primary,
  };
  editingId.value = name.id;
  isAdding.value = true;
}

function confirmDelete(id: string) {
  deleteId.value = id;
  showDeleteConfirm.value = true;
}

async function saveName() {
  if (!profileStore.profile) return;

  isSaving.value = true;
  error.value = null;

  try {
    const nameValue = { [form.value.language]: form.value.value };

    if (editingId.value) {
      // Update
      const updated = await profileService.updateName(
        profileStore.profile.user_id,
        editingId.value,
        {
          name_type: form.value.name_type,
          name_value: nameValue,
          is_primary: form.value.is_primary,
        },
      );
      // If this name became primary, un-mark others locally
      if (form.value.is_primary) {
        profileStore.identityNames.forEach((n) => {
          if (n.id !== editingId.value) n.is_primary = false;
        });
      }
      profileStore.updateIdentityName(editingId.value, updated);
    } else {
      // Create
      const created = await profileService.addName(
        profileStore.profile.user_id,
        {
          name_type: form.value.name_type,
          name_value: nameValue,
          is_primary: form.value.is_primary,
        },
      );
      // If the new name is primary, un-mark existing ones locally
      if (form.value.is_primary) {
        profileStore.identityNames.forEach((n) => {
          n.is_primary = false;
        });
      }
      profileStore.addIdentityName(created);
    }
    isAdding.value = false;
    resetForm();
  } catch (err) {
    error.value = getErrorMessage(err);
  } finally {
    isSaving.value = false;
  }
}

async function deleteName() {
  if (!profileStore.profile || !deleteId.value) return;

  isDeleting.value = true;

  try {
    await profileService.deleteName(
      profileStore.profile.user_id,
      deleteId.value,
    );
    // Refresh names from server to ensure sync, or filter local state
    const names = await profileService.getNames(profileStore.profile.user_id);
    profileStore.setIdentityNames(names);
    showDeleteConfirm.value = false;
    deleteId.value = null;
  } catch (err) {
    // error handling
    console.error(err);
  } finally {
    isDeleting.value = false;
  }
}
</script>

<template>
  <div class="identity-name-manager">
    <div class="manager-header">
      <h3 class="manager-title">Identity Names</h3>
      <BaseButton
        variant="secondary"
        size="sm"
        @click="startAdding"
        v-if="!isAdding"
      >
        + Add Name
      </BaseButton>
    </div>

    <!-- Auto-primary hint -->
    <div v-if="profileStore.autoPromotedPrimary" class="auto-primary-hint">
      <p class="hint-text">
        No name was marked as primary, so the first name was selected
        automatically. Edit any name and check "Set as primary display name" to
        choose a different one.
      </p>
    </div>

    <!-- List -->
    <div v-if="!isAdding" class="names-list">
      <div v-if="profileStore.identityNames.length === 0" class="empty-names">
        No additional names defined.
      </div>

      <div
        v-for="name in profileStore.identityNames"
        :key="name.id"
        class="name-card"
      >
        <div>
          <div class="name-info">
            <span class="name-display">
              {{ Object.values(name.name_value)[0] }}
            </span>
            <BaseBadge variant="primary" size="sm">{{
              name.name_type
            }}</BaseBadge>
            <BaseBadge v-if="name.is_primary" variant="success" size="sm"
              >Primary</BaseBadge
            >
          </div>
          <div class="name-lang">
            {{ Object.keys(name.name_value)[0] }}
          </div>
        </div>
        <div class="name-actions">
          <BaseButton variant="ghost" size="sm" @click="startEditing(name)">
            Edit
          </BaseButton>
          <BaseButton variant="ghost" size="sm" @click="confirmDelete(name.id)">
            Delete
          </BaseButton>
        </div>
      </div>
    </div>

    <!-- Add/Edit Form -->
    <div v-else class="name-form">
      <h4 class="name-form-title">
        {{ editingId ? "Edit Name" : "Add New Name" }}
      </h4>

      <form @submit.prevent="saveName" class="name-form-fields">
        <BaseSelect
          v-model="form.name_type"
          id="name_type"
          label="Type"
          :options="nameTypes"
          required
        />

        <div class="form-grid">
          <div class="form-col-narrow">
            <BaseSelect
              v-model="form.language"
              id="name_lang"
              label="Language"
              :options="languageOptions"
              required
            />
          </div>
          <div class="form-col-wide">
            <BaseInput
              v-model="form.value"
              id="name_value"
              label="Name"
              placeholder="Enter name"
              required
            />
          </div>
        </div>

        <div class="form-group">
          <label class="checkbox-group">
            <input
              type="checkbox"
              v-model="form.is_primary"
              class="checkbox-input"
            />
            <span class="checkbox-text">Set as primary display name</span>
          </label>
        </div>

        <div v-if="error" class="form-error-text">{{ error }}</div>

        <div class="form-buttons">
          <BaseButton variant="ghost" size="sm" @click="isAdding = false"
            >Cancel</BaseButton
          >
          <BaseButton type="submit" size="sm" :loading="isSaving"
            >Save</BaseButton
          >
        </div>
      </form>
    </div>

    <!-- Delete Modal -->
    <BaseModal
      :isOpen="showDeleteConfirm"
      title="Delete Name"
      @close="showDeleteConfirm = false"
    >
      <p class="modal-message">Are you sure you want to delete this name?</p>
      <template #footer>
        <div class="modal-buttons">
          <BaseButton variant="ghost" @click="showDeleteConfirm = false"
            >Cancel</BaseButton
          >
          <BaseButton variant="danger" :loading="isDeleting" @click="deleteName"
            >Delete</BaseButton
          >
        </div>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
/* Header */
.manager-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-4);
}

.manager-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

/* Auto-primary hint */
.auto-primary-hint {
  padding: var(--spacing-2) var(--spacing-3);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-primary);
  background-color: var(--bg-secondary);
  margin-bottom: var(--spacing-3);
}

.hint-text {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

/* Names list */
.names-list > * + * {
  margin-top: var(--spacing-3);
}

.empty-names {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  font-style: italic;
}

/* Name card */
.name-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-3);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  background-color: var(--bg-secondary);
}

.name-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-1);
}

.name-display {
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

.name-lang {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  text-transform: uppercase;
}

/* Action buttons */
.name-actions {
  display: flex;
  gap: var(--spacing-2);
}


/* Add/Edit form */
.name-form {
  background-color: var(--bg-tertiary);
  padding: var(--spacing-4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-primary);
}

.name-form-title {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  margin-bottom: var(--spacing-3);
}

.name-form-fields > * + * {
  margin-top: var(--spacing-3);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--spacing-3);
}

.form-col-narrow {
  grid-column: span 1 / span 1;
}

.form-col-wide {
  grid-column: span 2 / span 2;
}

/* Checkbox */
.checkbox-group {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  cursor: pointer;
}

.checkbox-input {
  border-radius: var(--radius-sm);
  border-color: var(--border-secondary);
  color: var(--color-primary-600);
}

.checkbox-text {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

/* Form error */
.form-error-text {
  font-size: var(--font-size-sm);
  color: var(--color-error-600);
}

/* Form buttons */
.form-buttons {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-2);
  margin-top: var(--spacing-4);
}

/* Modal content */
.modal-message {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-4);
}

.modal-buttons {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-2);
  width: 100%;
}
</style>
