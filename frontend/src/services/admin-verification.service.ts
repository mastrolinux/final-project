/**
 * Admin verification service for document review operations.
 *
 * Provides endpoints for listing pending documents, viewing details,
 * and approving or rejecting verification submissions.
 */

import api from "./api";
import type {
  AdminVerificationListItem,
  AdminVerificationReview,
  VerificationDocumentResponse,
} from "@/types";

export default {
  /**
   * List documents awaiting admin review (pending or under_review).
   */
  async listPendingDocuments(
    limit: number = 50,
    offset: number = 0,
  ): Promise<AdminVerificationListItem[]> {
    const response = await api.get<AdminVerificationListItem[]>(
      "/admin/verifications/pending",
      {
        params: { limit, offset },
      },
    );
    return response.data;
  },

  /**
   * Get full details of a single verification document.
   */
  async getDocument(documentId: string): Promise<VerificationDocumentResponse> {
    const response = await api.get<VerificationDocumentResponse>(
      `/admin/verifications/${documentId}`,
    );
    return response.data;
  },

  /**
   * Approve or reject a verification document.
   */
  async reviewDocument(
    documentId: string,
    review: AdminVerificationReview,
  ): Promise<VerificationDocumentResponse> {
    const response = await api.patch<VerificationDocumentResponse>(
      `/admin/verifications/${documentId}`,
      review,
    );
    return response.data;
  },
};
