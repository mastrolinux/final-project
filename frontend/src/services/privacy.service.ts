/**
 * Privacy service.
 * Provides GDPR Article 15 data export, Article 17 deletion request,
 * and deletion status for the authenticated user.
 */

import api from './api'
import type { DataExportResponse, DeletionRequestResponse, DeletionStatusResponse } from '@/types'

export default {
  /**
   * Export all personal data for the current user (GDPR Art. 15).
   * Returns a structured JSON document with profile, names, contexts,
   * authentication metadata, OAuth consents, and GDPR information.
   */
  async exportUserData(): Promise<DataExportResponse> {
    const response = await api.get<DataExportResponse>('/privacy/export')
    return response.data
  },

  /**
   * Request soft deletion of the authenticated user's account (GDPR Art. 17).
   * Initiates a 30-day grace period before permanent purge.
   */
  async requestDeletion(): Promise<DeletionRequestResponse> {
    const response = await api.post<DeletionRequestResponse>('/privacy/deletion-request')
    return response.data
  },

  /**
   * Check the deletion status of the authenticated user's account.
   * Returns 'active', 'scheduled' (with dates), or 'purged'.
   */
  async getDeletionStatus(): Promise<DeletionStatusResponse> {
    const response = await api.get<DeletionStatusResponse>('/privacy/deletion-status')
    return response.data
  }
}
