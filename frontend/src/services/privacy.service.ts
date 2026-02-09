/**
 * Privacy service.
 * Provides GDPR Article 15 data export for the authenticated user.
 */

import api from './api'
import type { DataExportResponse } from '@/types'

export default {
  /**
   * Export all personal data for the current user (GDPR Art. 15).
   * Returns a structured JSON document with profile, names, contexts,
   * authentication metadata, OAuth consents, and GDPR information.
   */
  async exportUserData(): Promise<DataExportResponse> {
    const response = await api.get<DataExportResponse>('/privacy/export')
    return response.data
  }
}
