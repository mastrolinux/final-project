import api from './api'
import type {
  ConsentDetailsResponse,
  ConsentDecisionRequest,
  ConsentDecisionResponse,
  OAuthConsent
} from '@/types'

export default {
  /**
   * Get details for the consent screen (client info, scopes).
   * Calls the authorize endpoint with JSON accept header to get data instead of HTML.
   */
  async getConsentDetails(params: Record<string, string>): Promise<ConsentDetailsResponse> {
    const response = await api.get<ConsentDetailsResponse>('/oauth/authorize', {
      params,
      headers: {
        Accept: 'application/json'
      }
    })
    return response.data
  },

  /**
   * Submit the user's consent decision (allow or deny).
   */
  async submitConsent(data: ConsentDecisionRequest): Promise<ConsentDecisionResponse> {
    const response = await api.post<ConsentDecisionResponse>('/oauth/consent', data)
    return response.data
  },

  /**
   * Get list of all granted consents for a user.
   * Backend returns ConsentListResponse: { consents: [...], total: N }
   */
  async getConsents(userId: string): Promise<OAuthConsent[]> {
    const response = await api.get<{ consents: OAuthConsent[]; total: number }>(
      '/oauth/consents',
      { params: { user_id: userId } }
    )
    return response.data.consents
  },

  /**
   * Revoke a specific consent (GDPR Art. 7(3) withdrawal).
   * Revokes all tokens for the user-client pair.
   */
  async revokeConsent(clientId: string, userId: string): Promise<void> {
    await api.delete(`/oauth/consents/${clientId}`, {
      params: { user_id: userId }
    })
  }
}
