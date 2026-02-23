/**
 * Admin verification service for context review operations.
 *
 * Provides endpoints for listing pending contexts, viewing context
 * details with linked documents, and approving or rejecting
 * verification submissions.
 */

import api from "./api";
import type {
  AdminContextVerificationItem,
  AdminContextVerificationDetail,
  AdminVerificationReview,
} from "@/types";

export default {
  /**
   * List contexts awaiting admin review (pending or under_review).
   */
  async listPendingContexts(
    limit: number = 50,
    offset: number = 0,
  ): Promise<AdminContextVerificationItem[]> {
    const response = await api.get<AdminContextVerificationItem[]>(
      "/admin/verifications/contexts/pending",
      {
        params: { limit, offset },
      },
    );
    return response.data;
  },

  /**
   * Get full details of a context verification request with linked documents.
   */
  async getContextVerification(
    contextId: string,
  ): Promise<AdminContextVerificationDetail> {
    const response = await api.get<AdminContextVerificationDetail>(
      `/admin/verifications/contexts/${contextId}`,
    );
    return response.data;
  },

  /**
   * Approve or reject a context verification request.
   */
  async reviewContext(
    contextId: string,
    review: AdminVerificationReview,
  ): Promise<AdminContextVerificationDetail> {
    const response = await api.patch<AdminContextVerificationDetail>(
      `/admin/verifications/contexts/${contextId}`,
      review,
    );
    return response.data;
  },

  /**
   * Download the decrypted verification document for admin review.
   *
   * Returns a Blob containing the original document bytes.
   */
  async downloadDocument(documentId: string): Promise<Blob> {
    const response = await api.get(
      `/admin/verifications/${documentId}/download`,
      {
        responseType: "blob",
      },
    );
    return response.data;
  },
};
