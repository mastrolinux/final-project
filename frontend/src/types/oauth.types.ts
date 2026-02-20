/**
 * OAuth 2.1 Authorization Flow Types
 *
 * Types matching backend schemas for OAuth consent flow.
 * @see backend/src/schemas/oauth.py
 */

/**
 * Client information for consent screen display.
 * Matches backend ConsentClientInfo schema.
 */
export interface OAuthClient {
  client_id: string;
  client_name: string;
  client_description?: string | null;
  client_uri?: string | null;
  logo_uri?: string | null;
  is_first_party: boolean;
}

/**
 * Scope information for consent screen display.
 * Matches backend ConsentScopeInfo schema.
 */
export interface OAuthScope {
  scope_name: string;
  description: string;
  is_sensitive: boolean;
  required_context_type?: string | null;
}

/**
 * User's granted consent record.
 */
export interface OAuthConsent {
  id: string;
  user_id: string;
  client_id: string;
  client_name: string;
  granted_scopes: string[];
  context_profile_id?: string | null;
  granted_at: string;
  expires_at?: string | null;
  withdrawn_at?: string | null;
  is_active: boolean;
}

/**
 * Authorization request parameters echoed back for consent flow.
 * Matches backend ConsentRequestInfo schema.
 */
export interface ConsentRequestParams {
  client_id: string;
  response_type: string;
  redirect_uri: string;
  scope: string;
  state?: string | null;
  code_challenge: string;
  code_challenge_method: string;
  nonce?: string | null;
  context_type?: string | null;
}

/**
 * Response for authorization consent screen.
 * Matches backend AuthorizationConsentResponse schema.
 */
export interface ConsentDetailsResponse {
  client: OAuthClient;
  scopes: OAuthScope[];
  request: ConsentRequestParams;
  requires_consent: boolean;
}

/**
 * Request body for consent decision submission.
 * Matches backend ConsentDecisionRequestBody schema.
 */
export interface ConsentDecisionRequest {
  client_id: string;
  scope: string;
  state?: string | null;
  redirect_uri: string;
  response_type: string;
  code_challenge: string;
  code_challenge_method: string;
  nonce?: string | null;
  decision: "allow" | "deny";
  context_id?: string | null;
  remember?: boolean;
}

/**
 * Response after consent decision processing.
 * Matches backend ConsentDecisionResponseBody schema.
 */
export interface ConsentDecisionResponse {
  redirect_to: string;
}
