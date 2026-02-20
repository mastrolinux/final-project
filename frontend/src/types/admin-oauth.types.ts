/**
 * Admin OAuth client management types matching backend schemas.
 * @see backend/src/schemas/oauth.py
 */

import type { ContextType } from "./context.types";

export type TokenEndpointAuthMethod =
  | "none"
  | "client_secret_post"
  | "client_secret_basic";

/**
 * Request payload for creating a new OAuth client.
 */
export interface OAuthClientCreate {
  client_id: string;
  client_name: string;
  client_description?: string;
  client_uri?: string;
  logo_uri?: string;
  redirect_uris: string[];
  allowed_scopes?: string[];
  default_context_type?: ContextType;
  is_confidential?: boolean;
  is_first_party?: boolean;
  client_secret?: string;
}

/**
 * Request payload for updating an OAuth client.
 * All fields are optional.
 */
export interface OAuthClientUpdate {
  client_name?: string;
  client_description?: string | null;
  client_uri?: string | null;
  logo_uri?: string | null;
  redirect_uris?: string[];
  allowed_scopes?: string[];
  default_context_type?: ContextType | null;
  is_active?: boolean;
  is_first_party?: boolean;
  client_secret?: string;
}

/**
 * OAuth client response (does NOT include secret).
 */
export interface OAuthClientResponse {
  client_id: string;
  client_name: string;
  client_description: string | null;
  client_uri: string | null;
  logo_uri: string | null;
  redirect_uris: string[];
  allowed_scopes: string[];
  default_context_type: ContextType | null;
  is_confidential: boolean;
  is_active: boolean;
  is_first_party: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * Response when creating a new OAuth client.
 * Includes the plain text client_secret, shown only once.
 */
export interface OAuthClientCreateResponse {
  client_id: string;
  client_name: string;
  client_description: string | null;
  client_uri: string | null;
  logo_uri: string | null;
  redirect_uris: string[];
  allowed_scopes: string[];
  default_context_type: ContextType | null;
  is_confidential: boolean;
  is_active: boolean;
  is_first_party: boolean;
  created_at: string;
  client_secret: string | null;
}

/**
 * Paginated list of OAuth clients.
 */
export interface OAuthClientListResponse {
  clients: OAuthClientResponse[];
  total: number;
  page: number;
  page_size: number;
}

/**
 * OAuth scope information.
 */
export interface ScopeInfo {
  scope_name: string;
  description: string;
  required_context_type: ContextType | null;
  is_sensitive: boolean;
}

/**
 * List of available OAuth scopes.
 */
export interface ScopeListResponse {
  scopes: ScopeInfo[];
}
