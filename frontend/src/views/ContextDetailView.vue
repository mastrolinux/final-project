<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useAuthStore, useProfileStore, useUiStore } from "@/stores";
import {
  contextService,
  oauthService,
  profileService,
  verificationService,
  getErrorMessage,
} from "@/services";
import {
  CONTEXT_TYPE_META,
  type ContextProfileResponse,
  type OAuthConsent,
  type ResolvedProfileResponse,
  type VerificationDocumentResponse,
} from "@/types";
import BaseCard from "@/components/common/BaseCard.vue";
import BaseButton from "@/components/common/BaseButton.vue";
import BaseBadge from "@/components/common/BaseBadge.vue";
import BaseInput from "@/components/common/BaseInput.vue";
import BaseModal from "@/components/common/BaseModal.vue";
import AvatarDisplay from "@/components/common/AvatarDisplay.vue";
import AvatarUpload from "@/components/profile/AvatarUpload.vue";
import ConsentCard from "@/components/oauth/ConsentCard.vue";
import AppBreadcrumb from "@/components/layout/AppBreadcrumb.vue";
import { DocumentArrowUpIcon } from "@heroicons/vue/24/outline";

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const profileStore = useProfileStore();
const uiStore = useUiStore();

const contextId = computed(() => route.params.id as string);
const context = ref<ContextProfileResponse | null>(null);
const resolvedProfile = ref<ResolvedProfileResponse | null>(null);
const isLoading = ref(true);
const isEditing = ref(false);
const isSaving = ref(false);
const isDeleting = ref(false);
const isUploadingAvatar = ref(false);
const error = ref<string | null>(null);
const showDeleteConfirm = ref(false);

// Connected apps (OAuth consents) state
const contextConsents = ref<OAuthConsent[]>([]);
const isLoadingConsents = ref(false);
const revokeTarget = ref<OAuthConsent | null>(null);
const isRevoking = ref(false);

const editForm = ref({
  context_name: "",
  display_name_override: "",
  email_override: "",
  phone_override: "",
  bio: "",
  is_active: true,
});

// Verification document state (legal/healthcare contexts only)
const requiresVerification = computed(
  () =>
    context.value?.context_type === "legal" ||
    context.value?.context_type === "healthcare",
);
const linkedDocument = ref<VerificationDocumentResponse | null>(null);
const isLoadingDocs = ref(false);
const docError = ref<string | null>(null);
const isUploadingDoc = ref(false);
const wantsReplace = ref(false);
const canUploadDocument = computed(
  () =>
    !linkedDocument.value ||
    context.value?.verification_status === "rejected" ||
    context.value?.verification_status === "expired" ||
    wantsReplace.value,
);

// Document picker state (link existing document)
const showDocPicker = ref(false);
const allUserDocs = ref<VerificationDocumentResponse[]>([]);
const isLoadingAllDocs = ref(false);
const isLinkingDoc = ref(false);
const availableDocuments = computed(() =>
  allUserDocs.value.filter((doc) => {
    if (linkedDocument.value && doc.id === linkedDocument.value.id) return false;
    if (doc.verification_status === "rejected") return false;
    if (doc.verification_status === "expired") return false;
    return true;
  }),
);

// Document upload form state
const docUploadFile = ref<File | null>(null);
const docUploadType = ref<"passport" | "national_id">("passport");
const docUploadExpiry = ref<string>("");
const docUploadDragOver = ref(false);

// Non-deprecated identity names for the "pick from names" chips
const availableNames = computed(() =>
  profileStore.identityNames.filter((n) => !n.is_deprecated),
);

function resolveNameValue(nameValue: Record<string, string>): string {
  const lang = navigator.language.split("-")[0];
  return (
    nameValue[lang] ?? nameValue["en"] ?? Object.values(nameValue)[0] ?? ""
  );
}

function pickName(resolved: string) {
  editForm.value.display_name_override = resolved;
}

onMounted(async () => {
  await loadContext();
  // Load identity names for the "pick from names" chips
  if (authStore.userId && profileStore.identityNames.length === 0) {
    try {
      const names = await profileService.getNames(authStore.userId);
      profileStore.setIdentityNames(names);
    } catch {
      // Non-critical: chips won't show, text input still works
    }
  }
});

async function loadContext() {
  if (!authStore.userId) return;

  isLoading.value = true;
  error.value = null;

  try {
    const [ctx, resolved] = await Promise.all([
      contextService.get(authStore.userId, contextId.value),
      contextService.getResolved(authStore.userId, contextId.value),
    ]);
    context.value = ctx;
    resolvedProfile.value = resolved;
    resetEditForm();

    // Load linked documents for verification-required contexts
    if (ctx.context_type === "legal" || ctx.context_type === "healthcare") {
      loadLinkedDocument();
    }

    // Load connected apps (non-blocking)
    loadContextConsents();
  } catch (err) {
    error.value = getErrorMessage(err);
  } finally {
    isLoading.value = false;
  }
}

async function loadContextConsents(): Promise<void> {
  if (!authStore.userId) return;
  isLoadingConsents.value = true;
  try {
    contextConsents.value = await oauthService.getContextConsents(
      authStore.userId,
      contextId.value,
    );
  } catch {
    // Non-critical: show empty state on failure
    contextConsents.value = [];
  } finally {
    isLoadingConsents.value = false;
  }
}

function handleRevokeClick(consent: OAuthConsent): void {
  revokeTarget.value = consent;
}

function cancelRevoke(): void {
  revokeTarget.value = null;
}

async function confirmRevoke(): Promise<void> {
  if (!revokeTarget.value) return;

  const target = revokeTarget.value;
  isRevoking.value = true;

  try {
    const userId = authStore.userId;
    if (!userId) throw new Error("User not authenticated");
    await oauthService.revokeConsent(target.client_id, userId);
    revokeTarget.value = null;
    uiStore.addNotification({
      type: "success",
      message: t("oauth.revokeSuccess", { client: target.client_name }),
    });
    await loadContextConsents();
  } catch (err) {
    uiStore.addNotification({
      type: "error",
      message: getErrorMessage(err),
    });
  } finally {
    isRevoking.value = false;
  }
}

function resetEditForm() {
  if (!context.value) return;
  editForm.value = {
    context_name: context.value.context_name,
    display_name_override: context.value.display_name_override || "",
    email_override: context.value.email_override || "",
    phone_override: context.value.phone_override || "",
    bio: context.value.bio || "",
    is_active: context.value.is_active,
  };
}

function startEditing() {
  resetEditForm();
  isEditing.value = true;
}

function cancelEditing() {
  isEditing.value = false;
  resetEditForm();
}

async function saveChanges() {
  if (!authStore.userId || !context.value) return;

  isSaving.value = true;
  error.value = null;

  try {
    const updatedContext = await contextService.update(
      authStore.userId,
      contextId.value,
      {
        context_name: editForm.value.context_name,
        display_name_override: editForm.value.display_name_override || null,
        email_override: editForm.value.email_override || null,
        phone_override: editForm.value.phone_override || null,
        bio: editForm.value.bio || null,
        is_active: editForm.value.is_active,
      },
    );
    context.value = updatedContext;

    // Reload resolved profile to reflect changes
    resolvedProfile.value = await contextService.getResolved(
      authStore.userId,
      contextId.value,
    );

    profileStore.updateContext(updatedContext);
    isEditing.value = false;
    uiStore.addNotification({
      type: "success",
      message: t("context.updateSuccess"),
    });
  } catch (err) {
    error.value = getErrorMessage(err);
  } finally {
    isSaving.value = false;
  }
}

async function deleteContext() {
  if (!authStore.userId) return;

  isDeleting.value = true;
  error.value = null;

  try {
    await contextService.delete(authStore.userId, contextId.value);
    profileStore.removeContext(contextId.value);
    uiStore.addNotification({
      type: "success",
      message: t("context.deleteSuccess"),
    });
    router.push({ name: "contexts" });
  } catch (err) {
    error.value = getErrorMessage(err);
    showDeleteConfirm.value = false;
  } finally {
    isDeleting.value = false;
  }
}

async function handleContextAvatarUpload(file: File) {
  if (!authStore.userId || !context.value) return;

  isUploadingAvatar.value = true;
  error.value = null;
  try {
    const result = await contextService.uploadAvatar(
      authStore.userId,
      contextId.value,
      file,
    );
    // Update local context ref
    context.value = {
      ...context.value,
      avatar_override_url: result.avatar_url,
      avatar_override_thumbnail_url: result.avatar_thumbnail_url,
    };
    // Update store
    profileStore.setContextAvatar(
      contextId.value,
      result.avatar_url,
      result.avatar_thumbnail_url,
    );
    // Reload resolved profile to reflect inheritance change
    resolvedProfile.value = await contextService.getResolved(
      authStore.userId,
      contextId.value,
    );
    uiStore.addNotification({
      type: "success",
      message: t("context.avatar.uploadSuccess"),
    });
  } catch (err) {
    error.value = getErrorMessage(err);
  } finally {
    isUploadingAvatar.value = false;
  }
}

async function handleContextAvatarRemove() {
  if (!authStore.userId || !context.value) return;

  isUploadingAvatar.value = true;
  error.value = null;
  try {
    await contextService.deleteAvatar(authStore.userId, contextId.value);
    context.value = {
      ...context.value,
      avatar_override_url: null,
      avatar_override_thumbnail_url: null,
    };
    profileStore.clearContextAvatar(contextId.value);
    resolvedProfile.value = await contextService.getResolved(
      authStore.userId,
      contextId.value,
    );
    uiStore.addNotification({
      type: "success",
      message: t("context.avatar.removeSuccess"),
    });
  } catch (err) {
    error.value = getErrorMessage(err);
  } finally {
    isUploadingAvatar.value = false;
  }
}

// --- Verification document management ---

async function loadLinkedDocument(): Promise<void> {
  if (!authStore.userId || !requiresVerification.value) return;

  isLoadingDocs.value = true;
  docError.value = null;

  try {
    const docs = await verificationService.getContextDocuments(
      authStore.userId,
      contextId.value,
    );
    linkedDocument.value = docs.length > 0 ? docs[0] : null;
  } catch (err) {
    docError.value = getErrorMessage(err);
  } finally {
    isLoadingDocs.value = false;
  }
}

function handleDocFileSelect(event: Event): void {
  const input = event.target as HTMLInputElement;
  if (input.files && input.files[0]) {
    validateAndSetFile(input.files[0]);
  }
}

function handleDocDrop(event: DragEvent): void {
  docUploadDragOver.value = false;
  if (event.dataTransfer?.files && event.dataTransfer.files[0]) {
    validateAndSetFile(event.dataTransfer.files[0]);
  }
}

function validateAndSetFile(file: File): void {
  const allowedTypes = ["application/pdf", "image/jpeg", "image/png"];
  if (!allowedTypes.includes(file.type)) {
    docError.value = t("verification.upload.invalidFormat");
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    docError.value = t("verification.upload.fileTooLarge");
    return;
  }
  docError.value = null;
  docUploadFile.value = file;
}

async function handleDocUpload(): Promise<void> {
  if (!authStore.userId || !docUploadFile.value || !docUploadExpiry.value)
    return;

  isUploadingDoc.value = true;
  docError.value = null;

  try {
    // Upload the document
    const uploaded = await verificationService.uploadDocument(
      authStore.userId,
      docUploadFile.value,
      docUploadType.value,
      docUploadExpiry.value,
    );

    // Auto-link to this context
    await verificationService.linkDocumentToContext(
      authStore.userId,
      contextId.value,
      uploaded.id,
    );

    // Reset form and reload context (status may change on resubmit)
    docUploadFile.value = null;
    docUploadType.value = "passport";
    docUploadExpiry.value = "";
    wantsReplace.value = false;
    await Promise.all([loadContext(), loadLinkedDocument()]);

    uiStore.addNotification({
      type: "success",
      message: t("verification.upload.success"),
    });
  } catch (err) {
    docError.value = getErrorMessage(err);
  } finally {
    isUploadingDoc.value = false;
  }
}

async function openDocPicker(): Promise<void> {
  if (!authStore.userId) return;

  showDocPicker.value = true;
  isLoadingAllDocs.value = true;

  try {
    allUserDocs.value = await verificationService.listDocuments(
      authStore.userId,
    );
  } catch (err) {
    docError.value = getErrorMessage(err);
    showDocPicker.value = false;
  } finally {
    isLoadingAllDocs.value = false;
  }
}

async function handleLinkExisting(documentId: string): Promise<void> {
  if (!authStore.userId) return;

  isLinkingDoc.value = true;
  docError.value = null;

  try {
    await verificationService.linkDocumentToContext(
      authStore.userId,
      contextId.value,
      documentId,
    );

    showDocPicker.value = false;
    wantsReplace.value = false;
    await Promise.all([loadContext(), loadLinkedDocument()]);

    uiStore.addNotification({
      type: "success",
      message: t("verification.upload.success"),
    });
  } catch (err) {
    docError.value = getErrorMessage(err);
  } finally {
    isLinkingDoc.value = false;
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
</script>

<template>
  <div class="page-view">
    <div class="container container-lg">
      <div class="page-header">
        <AppBreadcrumb />
      </div>

      <div v-if="isLoading" class="loading-container">
        <div class="spinner spinner-lg loading-spinner"></div>
        <p class="loading-text">{{ t("common.loading") }}</p>
      </div>

      <div v-else-if="error && !context" class="alert alert-error alert-spaced">
        {{ error }}
      </div>

      <template v-else-if="context">
        <div class="detail-grid">
          <!-- Main Content -->
          <div class="main-column">
            <!-- Context Header Card -->
            <BaseCard>
              <div class="context-header-row">
                <div>
                  <div class="context-badges">
                    <BaseBadge :variant="context.context_type" size="md">
                      {{ CONTEXT_TYPE_META[context.context_type]?.label }}
                    </BaseBadge>
                    <BaseBadge
                      v-if="context.verification_status === 'pending' && !context.has_linked_document"
                      variant="warning"
                      size="sm"
                    >
                      {{ t("context.verificationDocumentRequired") }}
                    </BaseBadge>
                    <BaseBadge
                      v-else-if="context.verification_status === 'pending' && context.has_linked_document"
                      variant="info"
                      size="sm"
                    >
                      {{ t("context.verificationAwaitingReview") }}
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
                    <BaseBadge
                      v-else-if="!context.is_active"
                      variant="warning"
                      size="sm"
                    >
                      {{ t("context.inactive") }}
                    </BaseBadge>
                  </div>
                  <h1 class="context-title">{{ context.context_name }}</h1>
                  <p class="context-meta">
                    Created
                    {{ new Date(context.created_at).toLocaleDateString() }}
                  </p>
                </div>
                <div v-if="!isEditing" class="action-buttons">
                  <BaseButton
                    variant="secondary"
                    size="sm"
                    @click="startEditing"
                  >
                    {{ t("common.edit") }}
                  </BaseButton>
                  <BaseButton
                    variant="danger"
                    size="sm"
                    @click="showDeleteConfirm = true"
                  >
                    {{ t("common.delete") }}
                  </BaseButton>
                </div>
              </div>
            </BaseCard>

            <!-- Resolved Profile Preview -->
            <BaseCard v-if="!isEditing && resolvedProfile">
              <template #header>
                <h2 class="card-heading">Resolved Profile</h2>
                <p class="resolved-subtitle">
                  What applications see when using this context
                </p>
              </template>

              <div class="fields-list">
                <div class="field-group">
                  <div class="field-header">
                    <label class="field-label-sm">Avatar</label>
                    <BaseBadge
                      v-if="context.avatar_override_url"
                      variant="info"
                      size="sm"
                      >Custom</BaseBadge
                    >
                  </div>
                  <AvatarDisplay
                    :src="resolvedProfile.avatar_url"
                    :name="resolvedProfile.display_name || ''"
                    size="lg"
                  />
                </div>

                <div class="field-group">
                  <div class="field-header">
                    <label class="field-label-sm">Display Name</label>
                    <BaseBadge
                      v-if="context.display_name_override"
                      variant="info"
                      size="sm"
                      >Custom</BaseBadge
                    >
                    <BaseBadge
                      v-else-if="resolvedProfile.display_name"
                      variant="neutral"
                      size="sm"
                      >Inherited</BaseBadge
                    >
                  </div>
                  <div class="field-value-text">
                    {{ resolvedProfile.display_name || "Not set" }}
                  </div>
                </div>

                <div class="field-group">
                  <div class="field-header">
                    <label class="field-label-sm">Email</label>
                    <BaseBadge
                      v-if="context.email_override"
                      variant="info"
                      size="sm"
                      >Custom</BaseBadge
                    >
                    <BaseBadge
                      v-else-if="resolvedProfile.email"
                      variant="neutral"
                      size="sm"
                      >Inherited</BaseBadge
                    >
                  </div>
                  <div class="field-value-text">
                    {{ resolvedProfile.email || "Not set" }}
                  </div>
                </div>

                <div class="field-group">
                  <div class="field-header">
                    <label class="field-label-sm">Phone</label>
                    <BaseBadge
                      v-if="context.phone_override"
                      variant="info"
                      size="sm"
                      >Custom</BaseBadge
                    >
                    <BaseBadge
                      v-else-if="resolvedProfile.phone"
                      variant="neutral"
                      size="sm"
                      >Inherited</BaseBadge
                    >
                  </div>
                  <div class="field-value-text">
                    {{ resolvedProfile.phone || "Not set" }}
                  </div>
                </div>

                <div class="field-group">
                  <div class="field-header">
                    <label class="field-label-sm">Bio</label>
                    <BaseBadge v-if="context.bio" variant="info" size="sm"
                      >Custom</BaseBadge
                    >
                    <BaseBadge
                      v-else-if="resolvedProfile.bio"
                      variant="neutral"
                      size="sm"
                      >Inherited</BaseBadge
                    >
                  </div>
                  <div class="field-value-bio">
                    {{ resolvedProfile.bio || "Not set" }}
                  </div>
                </div>
              </div>
            </BaseCard>

            <!-- Edit Form -->
            <BaseCard v-if="isEditing">
              <template #header>
                <h2 class="card-heading">Edit Context</h2>
              </template>

              <form @submit.prevent="saveChanges" class="edit-form">
                <BaseInput
                  v-model="editForm.context_name"
                  id="context_name"
                  :label="t('context.name')"
                  required
                />

                <div class="edit-divider">
                  <h3 class="overrides-heading">Overrides</h3>

                  <BaseInput
                    v-model="editForm.display_name_override"
                    id="display_name"
                    :label="t('context.displayNameOverride')"
                    :placeholder="t('context.optionalField')"
                  />

                  <div
                    v-if="availableNames.length > 0"
                    class="name-chips-section chips-spaced"
                  >
                    <span class="chips-label">{{
                      t("context.pickFromNames")
                    }}</span>
                    <div class="name-chips">
                      <button
                        v-for="name in availableNames"
                        :key="name.id"
                        type="button"
                        class="name-chip"
                        @click="pickName(resolveNameValue(name.name_value))"
                      >
                        <BaseBadge variant="primary" size="sm">{{
                          name.name_type
                        }}</BaseBadge>
                        <span class="chip-name-text">{{
                          resolveNameValue(name.name_value)
                        }}</span>
                      </button>
                    </div>
                  </div>

                  <BaseInput
                    v-model="editForm.email_override"
                    id="email"
                    type="email"
                    :label="t('context.emailOverride')"
                    :placeholder="t('context.inheritFromProfile')"
                  />

                  <BaseInput
                    v-model="editForm.phone_override"
                    id="phone"
                    type="tel"
                    :label="t('context.phoneOverride')"
                    :placeholder="t('context.inheritFromProfile')"
                  />

                  <div class="form-group textarea-group">
                    <label for="bio" class="textarea-label">{{
                      t("context.bio")
                    }}</label>
                    <textarea
                      id="bio"
                      v-model="editForm.bio"
                      rows="3"
                      class="textarea-field"
                      :placeholder="t('context.bioPlaceholder')"
                    ></textarea>
                  </div>

                  <div class="form-group avatar-override-group">
                    <label class="textarea-label">{{
                      t("context.avatar.override")
                    }}</label>
                    <AvatarUpload
                      :currentUrl="context?.avatar_override_url"
                      :name="
                        editForm.display_name_override ||
                        profileStore.displayName
                      "
                      :isUploading="isUploadingAvatar"
                      @upload="handleContextAvatarUpload"
                      @remove="handleContextAvatarRemove"
                    />
                  </div>
                </div>

                <div class="form-group">
                  <label class="checkbox-group">
                    <input
                      type="checkbox"
                      v-model="editForm.is_active"
                      class="checkbox-input"
                    />
                    <span class="checkbox-text">{{
                      t("context.isActive")
                    }}</span>
                  </label>
                </div>

                <div class="form-actions">
                  <BaseButton
                    variant="ghost"
                    @click="cancelEditing"
                    :disabled="isSaving"
                  >
                    {{ t("common.cancel") }}
                  </BaseButton>
                  <BaseButton type="submit" :loading="isSaving">
                    {{ t("common.save") }}
                  </BaseButton>
                </div>
              </form>
            </BaseCard>
          </div>

          <!-- Sidebar -->
          <div class="sidebar-column">
            <!-- Verification Documents (legal/healthcare only) -->
            <BaseCard v-if="requiresVerification" class="verification-card">
              <template #header>
                <div class="verification-header">
                  <h2 class="card-heading">
                    {{ t("context.verification.title") }}
                  </h2>
                  <BaseBadge
                    v-if="context.verification_status"
                    :variant="
                      context.verification_status === 'verified'
                        ? 'success'
                        : context.verification_status === 'rejected'
                          ? 'error'
                          : context.verification_status === 'under_review'
                            ? 'info'
                            : 'warning'
                    "
                    size="sm"
                  >
                    {{
                      t(`verification.status.${context.verification_status}`)
                    }}
                  </BaseBadge>
                </div>
              </template>

              <!-- Rejection reason -->
              <div
                v-if="
                  context.verification_status === 'rejected' &&
                  context.rejection_reason
                "
                class="rejection-banner"
              >
                <span class="rejection-label">
                  {{ t("verification.document.rejectionReason") }}
                </span>
                <p class="rejection-text">
                  {{ context.rejection_reason }}
                </p>
              </div>

              <!-- Document error -->
              <div v-if="docError" class="alert alert-error doc-alert">
                {{ docError }}
              </div>

              <!-- Loading documents -->
              <div v-if="isLoadingDocs" class="doc-loading">
                <div class="spinner spinner-sm"></div>
              </div>

              <!-- Linked document -->
              <div v-else-if="linkedDocument" class="doc-list">
                <div class="doc-item">
                  <div class="doc-item-top">
                    <BaseBadge variant="neutral" size="sm">
                      {{
                        t(
                          `verification.documentTypes.${linkedDocument.document_type === "national_id" ? "nationalId" : linkedDocument.document_type}`,
                        )
                      }}
                    </BaseBadge>
                    <span class="doc-size">
                      {{ formatFileSize(linkedDocument.file_size_bytes) }}
                    </span>
                  </div>
                  <span class="doc-filename">
                    {{ linkedDocument.original_filename }}
                  </span>
                  <div class="doc-item-actions">
                    <BaseButton
                      variant="ghost"
                      size="sm"
                      @click="wantsReplace = true"
                    >
                      {{ t("context.verification.replaceDocument") }}
                    </BaseButton>
                  </div>
                </div>
              </div>

              <!-- Empty documents state -->
              <p v-else class="doc-empty">
                {{ t("context.verification.noDocuments") }}
              </p>

              <!-- Upload or link section (visible when no doc linked, rejected, or replacing) -->
              <div v-if="canUploadDocument" class="doc-upload-section">
                <p
                  v-if="wantsReplace && context.verification_status === 'verified'"
                  class="doc-replace-warning"
                >
                  {{ t("context.verification.replaceDocumentWarning") }}
                </p>
                <div class="doc-section-header">
                  <h3 class="doc-section-title">
                    {{
                      linkedDocument
                        ? t("context.verification.replaceDocumentTitle")
                        : t("verification.upload.title")
                    }}
                  </h3>
                  <BaseButton
                    variant="ghost"
                    size="sm"
                    @click="openDocPicker"
                  >
                    {{ t("context.verification.linkExisting") }}
                  </BaseButton>
                </div>

                <div class="doc-upload-type">
                  <label class="doc-type-label" for="doc-type-select">
                    {{ t("verification.upload.documentType") }}
                  </label>
                  <select
                    id="doc-type-select"
                    v-model="docUploadType"
                    class="doc-type-select"
                  >
                    <option value="passport">
                      {{ t("verification.documentTypes.passport") }}
                    </option>
                    <option value="national_id">
                      {{ t("verification.documentTypes.nationalId") }}
                    </option>
                  </select>
                </div>

                <div class="doc-upload-type">
                  <label class="doc-type-label" for="doc-expiry-input">
                    {{ t("verification.upload.expiryDate") }}
                    <span class="doc-required">*</span>
                  </label>
                  <input
                    id="doc-expiry-input"
                    v-model="docUploadExpiry"
                    type="date"
                    class="doc-type-select"
                    :min="new Date().toISOString().split('T')[0]"
                  />
                  <p class="doc-expiry-hint">
                    {{ t("verification.upload.expiryDateHint") }}
                  </p>
                </div>

                <div
                  class="doc-dropzone"
                  :class="{ 'doc-dropzone-active': docUploadDragOver }"
                  @dragover.prevent="docUploadDragOver = true"
                  @dragleave="docUploadDragOver = false"
                  @drop.prevent="handleDocDrop"
                  @click="($refs.docFileInput as HTMLInputElement)?.click()"
                >
                  <input
                    ref="docFileInput"
                    type="file"
                    class="doc-file-input"
                    accept=".pdf,.jpg,.jpeg,.png"
                    @change="handleDocFileSelect"
                  />
                  <DocumentArrowUpIcon class="doc-dropzone-icon" />
                  <span v-if="docUploadFile" class="doc-dropzone-filename">
                    {{ docUploadFile.name }}
                  </span>
                  <span v-else class="doc-dropzone-text">
                    {{ t("verification.upload.dropZoneText") }}
                  </span>
                  <span class="doc-dropzone-hint">
                    {{ t("verification.upload.dropZoneHint") }}
                  </span>
                </div>

                <BaseButton
                  v-if="docUploadFile"
                  size="sm"
                  :loading="isUploadingDoc"
                  :disabled="!docUploadExpiry"
                  class="doc-upload-btn"
                  @click="handleDocUpload"
                >
                  {{ t("verification.upload.submit") }}
                </BaseButton>
              </div>

            </BaseCard>

            <!-- Connected Apps -->
            <BaseCard>
              <template #header>
                <h2 class="card-heading">{{ t("oauth.connectedApps") }}</h2>
              </template>

              <div v-if="isLoadingConsents" class="connected-loading">
                <div class="spinner spinner-sm"></div>
              </div>

              <div
                v-else-if="contextConsents.length === 0"
                class="connected-empty"
              >
                {{ t("oauth.noConnectedApps") }}
              </div>

              <div v-else class="connected-list">
                <ConsentCard
                  v-for="consent in contextConsents"
                  :key="consent.client_id"
                  :consent="consent"
                  @revoke="handleRevokeClick"
                />
              </div>
            </BaseCard>

            <!-- Inheritance Legend -->
            <BaseCard class="legend-card">
              <h3 class="legend-title">Field Inheritance</h3>
              <div class="legend-items">
                <div class="legend-row">
                  <BaseBadge variant="neutral" size="sm">Inherited</BaseBadge>
                  <span class="legend-desc"
                    >Value comes from your base profile</span
                  >
                </div>
                <div class="legend-row">
                  <BaseBadge variant="info" size="sm">Custom</BaseBadge>
                  <span class="legend-desc"
                    >Value is specific to this context</span
                  >
                </div>
                <div class="legend-row">
                  <span class="legend-no-badge">No badge</span>
                  <span class="legend-desc"
                    >Not set in base profile or this context</span
                  >
                </div>
              </div>
            </BaseCard>
          </div>
        </div>
      </template>

      <!-- Delete Confirmation Modal -->
      <BaseModal
        :isOpen="showDeleteConfirm"
        :title="t('context.deleteConfirmTitle')"
        @close="showDeleteConfirm = false"
      >
        <p class="modal-message">
          {{ t("context.deleteConfirmMessage") }}
        </p>
        <div class="delete-warning">
          <p class="delete-warning-text">
            <strong>Warning:</strong> Any applications using this context will
            lose access to your identity information.
          </p>
        </div>

        <template #footer>
          <div class="modal-actions">
            <BaseButton variant="ghost" @click="showDeleteConfirm = false">
              {{ t("common.cancel") }}
            </BaseButton>
            <BaseButton
              variant="danger"
              :loading="isDeleting"
              @click="deleteContext"
            >
              {{ t("common.delete") }}
            </BaseButton>
          </div>
        </template>
      </BaseModal>

      <!-- Revoke Consent Confirmation Modal -->
      <BaseModal
        :isOpen="!!revokeTarget"
        :title="t('oauth.revokeConfirmTitle')"
        @close="cancelRevoke"
      >
        <p class="modal-message">
          {{
            t("oauth.revokeConfirmMessage", {
              client: revokeTarget?.client_name,
            })
          }}
        </p>

        <template #footer>
          <div class="modal-actions">
            <BaseButton variant="ghost" @click="cancelRevoke">
              {{ t("common.cancel") }}
            </BaseButton>
            <BaseButton
              variant="danger"
              :loading="isRevoking"
              @click="confirmRevoke"
            >
              {{ t("oauth.revokeAccess") }}
            </BaseButton>
          </div>
        </template>
      </BaseModal>

      <!-- Document Picker Modal -->
      <BaseModal
        :isOpen="showDocPicker"
        :title="t('context.verification.linkExistingTitle')"
        @close="showDocPicker = false"
      >
        <div v-if="isLoadingAllDocs" class="doc-picker-loading">
          <div class="spinner spinner-sm"></div>
        </div>

        <div v-else-if="availableDocuments.length === 0" class="doc-picker-empty">
          {{ t("context.verification.noUnlinkedDocuments") }}
        </div>

        <div v-else class="doc-picker-list">
          <div
            v-for="doc in availableDocuments"
            :key="doc.id"
            class="doc-picker-item"
          >
            <div class="doc-picker-info">
              <div class="doc-picker-row">
                <BaseBadge variant="neutral" size="sm">
                  {{
                    t(
                      `verification.documentTypes.${doc.document_type === "national_id" ? "nationalId" : doc.document_type}`,
                    )
                  }}
                </BaseBadge>
                <BaseBadge
                  :variant="
                    doc.verification_status === 'verified'
                      ? 'success'
                      : doc.verification_status === 'pending'
                        ? 'warning'
                        : 'neutral'
                  "
                  size="sm"
                >
                  {{ t(`verification.status.${doc.verification_status}`) }}
                </BaseBadge>
              </div>
              <span class="doc-picker-filename">
                {{ doc.original_filename }}
              </span>
              <span class="doc-picker-meta">
                {{ formatFileSize(doc.file_size_bytes) }}
                <template v-if="doc.document_expiry_date">
                  &middot; Expires
                  {{
                    new Date(doc.document_expiry_date).toLocaleDateString(
                      undefined,
                      { year: "numeric", month: "short", day: "numeric" },
                    )
                  }}
                </template>
              </span>
            </div>
            <BaseButton
              variant="secondary"
              size="sm"
              :loading="isLinkingDoc"
              @click="handleLinkExisting(doc.id)"
            >
              {{ t("context.verification.linkExisting") }}
            </BaseButton>
          </div>
        </div>

        <template #footer>
          <div class="modal-actions">
            <BaseButton variant="ghost" @click="showDocPicker = false">
              {{ t("common.cancel") }}
            </BaseButton>
          </div>
        </template>
      </BaseModal>

    </div>
  </div>
</template>

<style scoped>
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

.alert-spaced {
  margin-bottom: var(--spacing-6);
}

/* Detail grid layout */
.detail-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--spacing-6);
}

@media (min-width: 1024px) {
  .detail-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.main-column {
  grid-column: 1;
}

@media (min-width: 1024px) {
  .main-column {
    grid-column: span 2 / span 2;
  }
}

.main-column > * + * {
  margin-top: var(--spacing-6);
}

.sidebar-column > * + * {
  margin-top: var(--spacing-6);
}

/* Context header */
.context-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.context-badges {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  margin-bottom: var(--spacing-2);
}

.context-title {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
}

.context-meta {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin-top: var(--spacing-1);
}

.action-buttons {
  display: flex;
  gap: var(--spacing-2);
}

/* Card elements */
.card-heading {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
}

.resolved-subtitle {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  font-weight: var(--font-weight-normal);
  margin-top: var(--spacing-1);
}

/* Field display */
.fields-list > * + * {
  margin-top: var(--spacing-4);
}

.field-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-1);
}

.field-label-sm {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
  text-transform: uppercase;
}

.field-value-text {
  color: var(--text-primary);
}

.field-value-bio {
  color: var(--text-primary);
  white-space: pre-wrap;
}

/* Edit form */
.edit-form > * + * {
  margin-top: var(--spacing-4);
}

.edit-divider {
  border-top: 1px solid var(--border-primary);
  margin-top: var(--spacing-4);
  margin-bottom: var(--spacing-4);
  padding-top: var(--spacing-4);
}

.overrides-heading {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  margin-bottom: var(--spacing-4);
}

/* Name chips (uses global .name-chips-section, .name-chips, .name-chip from components.css) */
.chips-spaced {
  margin-bottom: var(--spacing-4);
}

.chips-label {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

.chip-name-text {
  font-size: var(--font-size-sm);
}

/* Avatar override */
.avatar-override-group {
  margin-top: var(--spacing-4);
}

/* Textarea */
.textarea-group {
  margin-bottom: var(--spacing-4);
}

.textarea-label {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-1);
}

.textarea-field {
  display: block;
  width: 100%;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-secondary);
  box-shadow: var(--shadow-sm);
  padding: var(--spacing-2);
  font-size: var(--font-size-sm);
  background-color: var(--input-bg);
  color: var(--text-primary);
}

.textarea-field:focus {
  border-color: var(--color-primary-500);
  outline: none;
  box-shadow: 0 0 0 2px var(--color-primary-100);
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
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
}

/* Form actions */
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-3);
  padding-top: var(--spacing-4);
}

/* Sidebar - connected apps */
.connected-loading {
  display: flex;
  justify-content: center;
  padding: var(--spacing-4) 0;
}

.connected-empty {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  text-align: center;
  padding: var(--spacing-4) 0;
}

.connected-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

/* Sidebar - inheritance legend */
.legend-card {
  background-color: var(--bg-tertiary);
}

.legend-title {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  margin-bottom: var(--spacing-3);
}

.legend-items > * + * {
  margin-top: var(--spacing-3);
}

.legend-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.legend-desc {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

.legend-no-badge {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  font-style: italic;
}

/* Modal content */
.modal-message {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-4);
}

.delete-warning {
  background-color: var(--color-error-50);
  border: 1px solid #fee2e2;
  border-radius: var(--radius-md);
  padding: var(--spacing-3);
  margin-bottom: var(--spacing-4);
}

.delete-warning-text {
  font-size: var(--font-size-xs);
  color: #991b1b;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-3);
  width: 100%;
}

/* Verification documents sidebar card */
.verification-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.rejection-banner {
  background-color: var(--color-error-50);
  border: 1px solid var(--color-error-200);
  border-radius: var(--radius-md);
  padding: var(--spacing-3);
  margin-bottom: var(--spacing-4);
}

.rejection-label {
  display: block;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  color: var(--color-error-700);
  margin-bottom: var(--spacing-1);
}

.rejection-text {
  font-size: var(--font-size-sm);
  color: var(--color-error-600);
  margin: 0;
  line-height: 1.5;
}

.doc-alert {
  margin-bottom: var(--spacing-3);
  padding: var(--spacing-2) var(--spacing-3);
  font-size: var(--font-size-sm);
}

.doc-loading {
  display: flex;
  justify-content: center;
  padding: var(--spacing-4) 0;
}

.doc-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-4);
}

.doc-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
  padding: var(--spacing-3);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  background-color: var(--bg-primary);
}

.doc-item-top {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.doc-item-actions {
  display: flex;
  justify-content: flex-end;
}

.doc-filename {
  font-size: var(--font-size-xs);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-size {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.doc-empty {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  text-align: center;
  padding: var(--spacing-3) 0;
  margin-bottom: var(--spacing-4);
}

.doc-upload-section {
  border-top: 1px solid var(--border-primary);
  padding-top: var(--spacing-4);
}

.doc-section-title {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  margin: 0 0 var(--spacing-3) 0;
}

.doc-upload-type {
  margin-bottom: var(--spacing-3);
}

.doc-type-label {
  display: block;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-1);
}

.doc-required {
  color: var(--color-error-500);
}

.doc-expiry-hint {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  margin: var(--spacing-1) 0 0 0;
}

.doc-type-select {
  display: block;
  width: 100%;
  padding: var(--spacing-2) var(--spacing-3);
  border: 1px solid var(--border-secondary);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  background-color: var(--input-bg);
  color: var(--text-primary);
  font-family: inherit;
}

.doc-dropzone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-1);
  padding: var(--spacing-4) var(--spacing-3);
  border: 2px dashed var(--border-secondary);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition:
    border-color var(--transition-fast),
    background-color var(--transition-fast);
}

.doc-dropzone:hover,
.doc-dropzone-active {
  border-color: var(--color-primary-400);
  background-color: var(--color-primary-50);
}

.doc-file-input {
  display: none;
}

.doc-dropzone-icon {
  width: 24px;
  height: 24px;
  color: var(--text-tertiary);
}

.doc-dropzone-filename {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

.doc-dropzone-text {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  text-align: center;
}

.doc-dropzone-hint {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.doc-upload-btn {
  margin-top: var(--spacing-3);
  width: 100%;
}

/* Re-verification warning */
.doc-replace-warning {
  font-size: var(--font-size-sm);
  color: var(--color-warning-700);
  background-color: var(--color-warning-50);
  padding: var(--spacing-2) var(--spacing-3);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-3);
}

:global(.dark) .doc-replace-warning {
  color: var(--color-warning-400);
  background-color: rgba(234, 179, 8, 0.08);
}

/* Document section header (title + link button) */
.doc-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-3);
}

.doc-section-header .doc-section-title {
  margin: 0;
}

/* Document picker modal */
.doc-picker-loading {
  display: flex;
  justify-content: center;
  padding: var(--spacing-6) 0;
}

.doc-picker-empty {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  text-align: center;
  padding: var(--spacing-6) 0;
}

.doc-picker-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.doc-picker-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-3);
  padding: var(--spacing-3);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  background-color: var(--bg-primary);
}

.doc-picker-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
  min-width: 0;
  flex: 1;
}

.doc-picker-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.doc-picker-filename {
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-picker-meta {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

</style>
