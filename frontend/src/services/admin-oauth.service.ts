/**
 * Admin OAuth client management service.
 * Provides CRUD operations for OAuth clients (admin only).
 */

import api from "./api";
import type {
  OAuthClientCreate,
  OAuthClientUpdate,
  OAuthClientResponse,
  OAuthClientCreateResponse,
  OAuthClientListResponse,
  ScopeListResponse,
} from "@/types";

export default {
  /**
   * Create a new OAuth client.
   * Returns the client details including the plain text secret (shown only once).
   */
  async createClient(
    data: OAuthClientCreate,
  ): Promise<OAuthClientCreateResponse> {
    const response = await api.post<OAuthClientCreateResponse>(
      "/admin/oauth/clients",
      data,
    );
    return response.data;
  },

  /**
   * Get a paginated list of OAuth clients.
   */
  async listClients(
    page: number = 1,
    pageSize: number = 20,
    includeInactive: boolean = false,
  ): Promise<OAuthClientListResponse> {
    const response = await api.get<OAuthClientListResponse>(
      "/admin/oauth/clients",
      {
        params: {
          page,
          page_size: pageSize,
          include_inactive: includeInactive,
        },
      },
    );
    return response.data;
  },

  /**
   * Get a single OAuth client by ID.
   */
  async getClient(clientId: string): Promise<OAuthClientResponse> {
    const response = await api.get<OAuthClientResponse>(
      `/admin/oauth/clients/${clientId}`,
    );
    return response.data;
  },

  /**
   * Update an OAuth client.
   */
  async updateClient(
    clientId: string,
    data: OAuthClientUpdate,
  ): Promise<OAuthClientResponse> {
    const response = await api.patch<OAuthClientResponse>(
      `/admin/oauth/clients/${clientId}`,
      data,
    );
    return response.data;
  },

  /**
   * Delete (soft delete) an OAuth client.
   */
  async deleteClient(clientId: string): Promise<void> {
    await api.delete(`/admin/oauth/clients/${clientId}`);
  },

  /**
   * Fetch available OAuth scopes.
   * This is a public endpoint, not admin-specific.
   */
  async fetchScopes(): Promise<ScopeListResponse> {
    const response = await api.get<ScopeListResponse>("/oauth/scopes");
    return response.data;
  },
};
