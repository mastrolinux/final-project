/**
 * Unit tests for OAuth service.
 *
 * Tests verify correct API calls and response handling for the OAuth
 * consent flow endpoints, including the user_id query parameter
 * required by the backend.
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
    it('should fetch consent details with query params and JSON accept header', async () => {
      const mockResponse: ConsentDetailsResponse = {
        client: {
          client_id: 'test-client',
          client_name: 'Test App',
          is_first_party: false
        },
        scopes: [
          { scope_name: 'openid', description: 'Basic identity', is_sensitive: false },
          { scope_name: 'profile:read:basic', description: 'Name and account type', is_sensitive: false }
        ],
        request: {
          client_id: 'test-client',
          response_type: 'code',
          redirect_uri: 'https://example.com/callback',
          scope: 'openid profile:read:basic',
          state: 'abc123',
          code_challenge: 'challenge-value',
          code_challenge_method: 'S256'
        },
        requires_consent: true
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
        code_challenge: 'challenge-value',
        code_challenge_method: 'S256',
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
        code_challenge: 'challenge-value',
        code_challenge_method: 'S256',
        decision: 'deny'
      })

      expect(api.post).toHaveBeenCalledWith('/oauth/consent', expect.objectContaining({
        decision: 'deny'
      }))
      expect(result.redirect_to).toContain('error=access_denied')
    })
  })

  describe('getConsents', () => {
    it('should fetch list of granted consents with user_id param', async () => {
      const mockConsents: OAuthConsent[] = [
        {
          id: 'consent-1',
          user_id: 'user-abc',
          client_id: 'app-1',
          client_name: 'App One',
          granted_scopes: ['openid', 'profile:read:basic'],
          granted_at: '2026-01-15T10:00:00Z',
          is_active: true
        },
        {
          id: 'consent-2',
          user_id: 'user-abc',
          client_id: 'app-2',
          client_name: 'App Two',
          granted_scopes: ['openid'],
          context_profile_id: 'context-456',
          granted_at: '2026-01-10T08:00:00Z',
          is_active: true
        }
      ]

      vi.mocked(api.get).mockResolvedValue({
        data: { consents: mockConsents, total: 2 }
      })

      const result = await oauthService.getConsents('user-abc')

      expect(api.get).toHaveBeenCalledWith('/oauth/consents', {
        params: { user_id: 'user-abc' }
      })
      expect(result).toHaveLength(2)
      expect(result[0].client_name).toBe('App One')
      expect(result[1].context_profile_id).toBe('context-456')
    })

    it('should return empty array when no consents exist', async () => {
      vi.mocked(api.get).mockResolvedValue({
        data: { consents: [], total: 0 }
      })

      const result = await oauthService.getConsents('user-xyz')

      expect(result).toHaveLength(0)
    })
  })

  describe('revokeConsent', () => {
    it('should revoke consent for a specific client with user_id param', async () => {
      vi.mocked(api.delete).mockResolvedValue({})

      await oauthService.revokeConsent('app-1', 'user-abc')

      expect(api.delete).toHaveBeenCalledWith('/oauth/consents/app-1', {
        params: { user_id: 'user-abc' }
      })
    })
  })
})
