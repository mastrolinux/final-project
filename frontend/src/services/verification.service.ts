/**
 * Verification service for user-facing document operations.
 *
 * Handles document upload (multipart/form-data), status retrieval,
 * document listing, and context-document linking for the authenticated user.
 */

import api from "./api";
import type {
  VerificationDocumentResponse,
  VerificationStatusResponse,
} from "@/types";

export default {
  /**
   * Upload an identity document for verification.
   *
   * Documents are uploaded as standalone entities. To associate a
   * document with a context, call linkDocumentToContext after upload.
   */
  async uploadDocument(
    userId: string,
    file: File,
    documentType: string,
    documentExpiryDate: string,
  ): Promise<VerificationDocumentResponse> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("document_type", documentType);
    formData.append("document_expiry_date", documentExpiryDate);

    const response = await api.post<VerificationDocumentResponse>(
      `/profiles/${userId}/verification-documents`,
      formData,
      {
        headers: { "Content-Type": "multipart/form-data" },
      },
    );
    return response.data;
  },

  /**
   * Get the current verification status for a user.
   */
  async getVerificationStatus(
    userId: string,
  ): Promise<VerificationStatusResponse> {
    const response = await api.get<VerificationStatusResponse>(
      `/profiles/${userId}/verification-status`,
    );
    return response.data;
  },

  /**
   * List all verification documents for a user.
   */
  async listDocuments(userId: string): Promise<VerificationDocumentResponse[]> {
    const response = await api.get<VerificationDocumentResponse[]>(
      `/profiles/${userId}/verification-documents`,
    );
    return response.data;
  },

  /**
   * List documents linked to a specific context profile.
   */
  async getContextDocuments(
    userId: string,
    contextId: string,
  ): Promise<VerificationDocumentResponse[]> {
    const response = await api.get<VerificationDocumentResponse[]>(
      `/profiles/${userId}/contexts/${contextId}/documents`,
    );
    return response.data;
  },

  /**
   * Link an existing document to a context profile.
   *
   * Both the document and context must belong to the user,
   * and the context must require verification (legal/healthcare).
   */
  async linkDocumentToContext(
    userId: string,
    contextId: string,
    documentId: string,
  ): Promise<void> {
    await api.post(
      `/profiles/${userId}/contexts/${contextId}/documents/${documentId}`,
    );
  },

  /**
   * Remove the link between a document and a context profile.
   *
   * The document itself is not deleted, only the association.
   */
  async unlinkDocumentFromContext(
    userId: string,
    contextId: string,
    documentId: string,
  ): Promise<void> {
    await api.delete(
      `/profiles/${userId}/contexts/${contextId}/documents/${documentId}`,
    );
  },

  /**
   * Download the decrypted content of an owned verification document.
   *
   * Returns a Blob that can be displayed inline (images) or embedded
   * in an iframe (PDFs). Only the document owner can access this.
   */
  async downloadDocument(
    userId: string,
    documentId: string,
  ): Promise<Blob> {
    const response = await api.get(
      `/profiles/${userId}/verification-documents/${documentId}/download`,
      { responseType: "blob" },
    );
    return response.data;
  },
};
