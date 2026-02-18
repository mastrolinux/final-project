/**
 * Unit tests for audit service.
 *
 * Tests verify correct API calls for fetching user audit trails
 * (with and without filters) and admin integrity verification.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import auditService from '@/services/audit.service'
import api from '@/services/api'
import type { AuditTrailResponse, AuditIntegrityResponse } from '@/types'

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn()
  }
}))

describe('auditService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getMyAuditTrail', () => {
    it('should GET /audit/me without filters when none provided', async () => {
      const mockResponse: AuditTrailResponse = {
        entries: [],
        total: 0,
        page: 1,
        page_size: 50
      } as unknown as AuditTrailResponse

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await auditService.getMyAuditTrail()

      expect(api.get).toHaveBeenCalledWith('/audit/me', {
        params: undefined
      })
      expect(result).toEqual(mockResponse)
    })

    it('should pass filter parameters when provided', async () => {
      const mockResponse: AuditTrailResponse = {
        entries: [{ id: 'entry-1' }],
        total: 1,
        page: 1,
        page_size: 20
      } as unknown as AuditTrailResponse

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const filter = { page: 2, page_size: 20, operation: 'login' as const }
      const result = await auditService.getMyAuditTrail(filter)

      expect(api.get).toHaveBeenCalledWith('/audit/me', {
        params: filter
      })
      expect(result.total).toBe(1)
    })
  })

  describe('verifyIntegrity', () => {
    it('should GET /audit/verify with default limit of 1000', async () => {
      const mockResponse: AuditIntegrityResponse = {
        is_valid: true,
        entries_checked: 1000,
        errors: []
      } as unknown as AuditIntegrityResponse

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await auditService.verifyIntegrity()

      expect(api.get).toHaveBeenCalledWith('/audit/verify', {
        params: { limit: 1000 }
      })
      expect(result).toEqual(mockResponse)
    })

    it('should pass custom limit', async () => {
      const mockResponse: AuditIntegrityResponse = {
        is_valid: true,
        entries_checked: 500,
        errors: []
      } as unknown as AuditIntegrityResponse

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      await auditService.verifyIntegrity(500)

      expect(api.get).toHaveBeenCalledWith('/audit/verify', {
        params: { limit: 500 }
      })
    })
  })
})
