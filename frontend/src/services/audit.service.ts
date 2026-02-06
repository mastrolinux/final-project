/**
 * Audit log service.
 * Provides access to the user audit trail and admin integrity verification.
 */

import api from './api'
import type { AuditTrailResponse, AuditTrailFilter, AuditIntegrityResponse } from '@/types'

export default {
  /**
   * Fetch the current user's audit trail with optional filters.
   * Available to any authenticated user (data subject access right).
   */
  async getMyAuditTrail(filter?: AuditTrailFilter): Promise<AuditTrailResponse> {
    const response = await api.get<AuditTrailResponse>('/audit/me', {
      params: filter
    })
    return response.data
  },

  /**
   * Verify hash chain integrity of audit logs.
   * Admin-only endpoint.
   */
  async verifyIntegrity(limit: number = 1000): Promise<AuditIntegrityResponse> {
    const response = await api.get<AuditIntegrityResponse>('/audit/verify', {
      params: { limit }
    })
    return response.data
  }
}
