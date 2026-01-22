/**
 * Unit tests for OAuth service.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import oauthService from '@/services/oauth.service'
import api from '@/services/api'
import type { ConsentDetailsResponse, OAuthConsent } from '@/types'

// Mock the API module
vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn()
  }
}))

describe('oauthService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getConsentDetails', () => {
    it('should fetch consent details with query params', async () => {
      const mockResponse: ConsentDetailsResponse = {
        client: {
          client_id: 'test-client',
          client_name: 'Test App',
          is_verified: true
        },
        scopes: [
          { id: 'openid', name: 'OpenID', description: 'Basic identity', is_default: true },
          { id: 'profile:read:basic', name: 'Basic Profile', description: 'Name and account type', is_default: true }
        ],
        request: {
          client_id: 'test-client',
          response_type: 'code',
          redirect_uri: 'https://example.com/callback',
          scope: 'openid profile:read:basic',
          state: 'abc123'
        }
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const params = {
        client_id: 'test-client',
        response_type: 'code',
        redirect_uri: 'https://example.com/callback',
        scope: 'openid profile:read:basic',
        state: 'abc123'
      }

      const result = await oauthService.getConsentDetails(params)

      expect(api.get).toHaveBeenCalledWith('/oauth/authorize', {
        params,
        headers: { Accept: 'application/json' }
      })
      expect(result).toEqual(mockResponse)
    })
  })

  describe('submitConsent', () => {
    it('should submit allow decision and return redirect URL', async () => {
      const mockResponse = { redirect_to: 'https://example.com/callback?code=xyz&state=abc123' }
      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const result = await oauthService.submitConsent({
        client_id: 'test-client',
        scope: 'openid profile:read:basic',
        state: 'abc123',
        redirect_uri: 'https://example.com/callback',
        response_type: 'code',
        decision: 'allow',
        context_id: 'context-123'
      })

      expect(api.post).toHaveBeenCalledWith('/oauth/consent', expect.objectContaining({
        client_id: 'test-client',
        decision: 'allow',
        context_id: 'context-123'
      }))
      expect(result.redirect_to).toBe('https://example.com/callback?code=xyz&state=abc123')
    })

    it('should submit deny decision', async () => {
      const mockResponse = { redirect_to: 'https://example.com/callback?error=access_denied&state=abc123' }
      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const result = await oauthService.submitConsent({
        client_id: 'test-client',
        scope: 'openid',
        state: 'abc123',
        redirect_uri: 'https://example.com/callback',
        response_type: 'code',
        decision: 'deny'
      })

      expect(api.post).toHaveBeenCalledWith('/oauth/consent', expect.objectContaining({
        decision: 'deny'
      }))
      expect(result.redirect_to).toContain('error=access_denied')
    })
  })

  describe('getConsents', () => {
    it('should fetch list of granted consents', async () => {
      const mockConsents: OAuthConsent[] = [
        {
          client: {
            client_id: 'app-1',
            client_name: 'App One',
            is_verified: true
          },
          scopes: ['openid', 'profile:read:basic'],
          created_at: '2026-01-15T10:00:00Z',
          updated_at: '2026-01-15T10:00:00Z'
        },
        {
          client: {
            client_id: 'app-2',
            client_name: 'App Two',
            is_verified: false
          },
          scopes: ['openid'],
          created_at: '2026-01-10T08:00:00Z',
          updated_at: '2026-01-10T08:00:00Z',
          context_id: 'context-456'
        }
      ]

      vi.mocked(api.get).mockResolvedValue({ data: mockConsents })

      const result = await oauthService.getConsents()

      expect(api.get).toHaveBeenCalledWith('/oauth/consents')
      expect(result).toHaveLength(2)
      expect(result[0].client.client_name).toBe('App One')
    })
  })

  describe('revokeConsent', () => {
    it('should revoke consent for a specific client', async () => {
      vi.mocked(api.delete).mockResolvedValue({})

      await oauthService.revokeConsent('app-1')

      expect(api.delete).toHaveBeenCalledWith('/oauth/consents/app-1')
    })
  })
})
