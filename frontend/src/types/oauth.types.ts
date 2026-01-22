export interface OAuthClient {
  client_id: string
  client_name: string
  client_uri?: string
  logo_uri?: string
  tos_uri?: string
  policy_uri?: string
  is_verified: boolean
}

export interface OAuthScope {
  id: string
  name: string
  description: string
  is_default: boolean
  is_required?: boolean
}

export interface OAuthConsent {
  client: OAuthClient
  scopes: string[]
  created_at: string
  updated_at: string
  context_id?: string
}

export interface ConsentRequestParams {
  client_id: string
  response_type: string
  redirect_uri: string
  scope: string
  state: string
  code_challenge?: string
  code_challenge_method?: string
  nonce?: string
}

export interface ConsentDetailsResponse {
  client: OAuthClient
  scopes: OAuthScope[]
  request: ConsentRequestParams
}

export interface ConsentDecisionRequest {
  client_id: string
  scope: string
  state: string
  redirect_uri: string
  response_type: string
  code_challenge?: string
  code_challenge_method?: string
  nonce?: string
  decision: 'allow' | 'deny'
  context_id?: string
}

export interface ConsentDecisionResponse {
  redirect_to: string
}
