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
   * Get list of all granted consents.
   */
  async getConsents(): Promise<OAuthConsent[]> {
    const response = await api.get<OAuthConsent[]>('/oauth/consents')
    return response.data
  },

  /**
   * Revoke a specific consent.
   */
  async revokeConsent(clientId: string): Promise<void> {
    await api.delete(`/oauth/consents/${clientId}`)
  }
}
