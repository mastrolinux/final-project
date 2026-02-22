/**
 * Verification service for user-facing document operations.
 *
 * Handles document upload (multipart/form-data), status retrieval,
 * and document listing for the authenticated user.
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
   * Sends the file as multipart/form-data with the document_type field.
   */
  async uploadDocument(
    userId: string,
    file: File,
    documentType: string,
  ): Promise<VerificationDocumentResponse> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("document_type", documentType);

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
};
