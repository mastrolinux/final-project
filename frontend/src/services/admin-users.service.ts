/**
 * Admin user management service.
 * Provides operations for managing soft-deleted user accounts (admin only).
 */

import api from "./api";
import type {
  SoftDeletedUserListResponse,
  PurgeExpiredResponse,
} from "@/types";

export default {
  /**
   * Get a paginated list of soft-deleted users.
   */
  async listSoftDeletedUsers(
    page: number = 1,
    pageSize: number = 20,
  ): Promise<SoftDeletedUserListResponse> {
    const response = await api.get<SoftDeletedUserListResponse>(
      "/admin/users/soft-deleted",
      {
        params: {
          page,
          page_size: pageSize,
        },
      },
    );
    return response.data;
  },

  /**
   * Permanently purge all expired soft-deleted user accounts.
   * This is irreversible.
   */
  async purgeExpiredUsers(): Promise<PurgeExpiredResponse> {
    const response = await api.post<PurgeExpiredResponse>(
      "/admin/users/purge-expired",
    );
    return response.data;
  },
};
