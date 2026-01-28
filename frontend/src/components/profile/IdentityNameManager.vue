<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useProfileStore } from '@/stores'
import { profileService, getErrorMessage } from '@/services'
import type { IdentityName, NameType } from '@/types'
import BaseButton from '@/components/common/BaseButton.vue'
import BaseInput from '@/components/common/BaseInput.vue'
import BaseSelect from '@/components/common/BaseSelect.vue'
import BaseBadge from '@/components/common/BaseBadge.vue'
import BaseModal from '@/components/common/BaseModal.vue'

const { t } = useI18n()
const profileStore = useProfileStore()

const isAdding = ref(false)
const isSaving = ref(false)
const isDeleting = ref(false)
const error = ref<string | null>(null)
const editingId = ref<string | null>(null)
const showDeleteConfirm = ref(false)
const deleteId = ref<string | null>(null)

const nameTypes: { label: string; value: NameType }[] = [
  { label: 'Given Name', value: 'given' },
  { label: 'Family Name', value: 'family' },
  { label: 'Preferred Name', value: 'preferred' },
  { label: 'Legal Name', value: 'legal' },
  { label: 'Nickname', value: 'custom' } // Mapping custom to nickname for UI simplicity if needed, or keep custom
]

const languageOptions = [
  { label: 'English (en)', value: 'en' },
  { label: 'Chinese (zh)', value: 'zh' },
  { label: 'Spanish (es)', value: 'es' },
  { label: 'Arabic (ar)', value: 'ar' }
]

const form = ref({
  name_type: 'preferred' as NameType,
  language: 'en',
  value: '',
  is_primary: false
})

function resetForm() {
  form.value = {
    name_type: 'preferred',
    language: 'en',
    value: '',
    is_primary: false
  }
  editingId.value = null
  error.value = null
}

function startAdding() {
  resetForm()
  isAdding.value = true
}

function startEditing(name: IdentityName) {
  const lang = Object.keys(name.name_value)[0] || 'en'
  const val = Object.values(name.name_value)[0] || ''
  
  form.value = {
    name_type: name.name_type,
    language: lang,
    value: val,
    is_primary: name.is_primary
  }
  editingId.value = name.id
  isAdding.value = true
}

function confirmDelete(id: string) {
  deleteId.value = id
  showDeleteConfirm.value = true
}

async function saveName() {
  if (!profileStore.profile) return

  isSaving.value = true
  error.value = null

  try {
    const nameValue = { [form.value.language]: form.value.value }
    
    if (editingId.value) {
      // Update
      const updated = await profileService.updateName(profileStore.profile.user_id, editingId.value, {
        name_type: form.value.name_type,
        name_value: nameValue,
        is_primary: form.value.is_primary
      })
      profileStore.updateIdentityName(editingId.value, updated)
    } else {
      // Create
      const created = await profileService.addName(profileStore.profile.user_id, {
        name_type: form.value.name_type,
        name_value: nameValue,
        is_primary: form.value.is_primary
      })
      profileStore.addIdentityName(created)
    }
    isAdding.value = false
    resetForm()
  } catch (err) {
    error.value = getErrorMessage(err)
  } finally {
    isSaving.value = false
  }
}

async function deleteName() {
  if (!profileStore.profile || !deleteId.value) return

  isDeleting.value = true
  
  try {
    await profileService.deleteName(profileStore.profile.user_id, deleteId.value)
    // Refresh names from server to ensure sync, or filter local state
    const names = await profileService.getNames(profileStore.profile.user_id)
    profileStore.setIdentityNames(names)
    showDeleteConfirm.value = false
    deleteId.value = null
  } catch (err) {
    // error handling
    console.error(err)
  } finally {
    isDeleting.value = false
  }
}
</script>

<template>
  <div class="identity-name-manager">
    <div class="flex justify-between items-center mb-4">
      <h3 class="text-lg font-medium text-gray-900">Identity Names</h3>
      <BaseButton variant="secondary" size="sm" @click="startAdding" v-if="!isAdding">
        + Add Name
      </BaseButton>
    </div>

    <!-- List -->
    <div v-if="!isAdding" class="space-y-3">
      <div v-if="profileStore.identityNames.length === 0" class="text-sm text-gray-500 italic">
        No additional names defined.
      </div>
      
      <div
        v-for="name in profileStore.identityNames"
        :key="name.id"
        class="flex items-center justify-between p-3 border border-gray-200 rounded-lg bg-white"
      >
        <div>
          <div class="flex items-center gap-2 mb-1">
            <span class="font-medium text-gray-900">
              {{ Object.values(name.name_value)[0] }}
            </span>
            <BaseBadge variant="primary" size="sm">{{ name.name_type }}</BaseBadge>
            <BaseBadge v-if="name.is_primary" variant="success" size="sm">Primary</BaseBadge>
          </div>
          <div class="text-xs text-gray-500 uppercase">
            {{ Object.keys(name.name_value)[0] }}
          </div>
        </div>
        <div class="flex gap-2">
          <button class="text-gray-400 hover:text-primary-600" @click="startEditing(name)">
            <span class="sr-only">Edit</span>
            ✏️
          </button>
          <button class="text-gray-400 hover:text-red-600" @click="confirmDelete(name.id)">
            <span class="sr-only">Delete</span>
            🗑️
          </button>
        </div>
      </div>
    </div>

    <!-- Add/Edit Form -->
    <div v-else class="bg-gray-50 p-4 rounded-lg border border-gray-200">
      <h4 class="text-sm font-medium text-gray-900 mb-3">
        {{ editingId ? 'Edit Name' : 'Add New Name' }}
      </h4>
      
      <form @submit.prevent="saveName" class="space-y-3">
        <BaseSelect
          v-model="form.name_type"
          id="name_type"
          label="Type"
          :options="nameTypes"
          required
        />
        
        <div class="grid grid-cols-3 gap-3">
          <div class="col-span-1">
            <BaseSelect
              v-model="form.language"
              id="name_lang"
              label="Language"
              :options="languageOptions"
              required
            />
          </div>
          <div class="col-span-2">
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
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" v-model="form.is_primary" class="rounded border-gray-300 text-primary-600" />
            <span class="text-sm text-gray-700">Set as primary display name</span>
          </label>
        </div>

        <div v-if="error" class="text-sm text-red-600">{{ error }}</div>

        <div class="flex justify-end gap-2 mt-4">
          <BaseButton variant="ghost" size="sm" @click="isAdding = false">Cancel</BaseButton>
          <BaseButton type="submit" size="sm" :loading="isSaving">Save</BaseButton>
        </div>
      </form>
    </div>

    <!-- Delete Modal -->
    <BaseModal
      :isOpen="showDeleteConfirm"
      title="Delete Name"
      @close="showDeleteConfirm = false"
    >
      <p class="text-sm text-gray-500 mb-4">Are you sure you want to delete this name?</p>
      <template #footer>
        <div class="flex justify-end gap-2 w-full">
          <BaseButton variant="ghost" @click="showDeleteConfirm = false">Cancel</BaseButton>
          <BaseButton variant="danger" :loading="isDeleting" @click="deleteName">Delete</BaseButton>
        </div>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* Utility classes with dark mode support */
.flex { display: flex; }
.items-center { align-items: center; }
.justify-between { justify-content: space-between; }
.justify-end { justify-content: flex-end; }
.gap-2 { gap: 0.5rem; }
.gap-3 { gap: 0.75rem; }
.mb-1 { margin-bottom: 0.25rem; }
.mb-3 { margin-bottom: 0.75rem; }
.mb-4 { margin-bottom: 1rem; }
.mt-4 { margin-top: 1rem; }
.p-3 { padding: 0.75rem; }
.p-4 { padding: 1rem; }
.space-y-3 > * + * { margin-top: 0.75rem; }
.grid { display: grid; }
.grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.col-span-1 { grid-column: span 1 / span 1; }
.col-span-2 { grid-column: span 2 / span 2; }
.w-full { width: 100%; }
.border { border-width: 1px; }
.rounded-lg { border-radius: 0.5rem; }
.rounded { border-radius: 0.25rem; }
.cursor-pointer { cursor: pointer; }
.italic { font-style: italic; }
.uppercase { text-transform: uppercase; }

/* Typography - dark mode aware */
.text-lg { font-size: 1.125rem; line-height: 1.75rem; }
.text-sm { font-size: 0.875rem; line-height: 1.25rem; }
.text-xs { font-size: 0.75rem; line-height: 1rem; }
.font-medium { font-weight: 500; }
.text-gray-900 { color: var(--text-primary); }
.text-gray-700 { color: var(--text-secondary); }
.text-gray-500 { color: var(--text-secondary); }
.text-gray-400 { color: var(--text-tertiary); }
.text-red-600 { color: var(--color-error-600); }

/* Backgrounds - dark mode aware */
.bg-white { background-color: var(--bg-secondary); }
.bg-gray-50 { background-color: var(--bg-secondary); }
.border-gray-200 { border-color: var(--border-primary); }
.border-gray-300 { border-color: var(--border-secondary); }

/* Interactive states */
.hover\:text-primary-600:hover { color: var(--color-primary-600); }
.hover\:text-red-600:hover { color: var(--color-error-600); }
</style>
