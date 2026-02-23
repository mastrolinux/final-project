/**
 * Context service for managing context profiles.
 *
 * Context profiles enable identity context separation:
 * - Professional, Social, Legal, Healthcare, Family, Custom types
 * - Override specific fields (null = inherit from base profile)
 * - Resolved endpoint merges base + context with inheritance engine
 */

import api from "./api";
import type {
  ContextProfileResponse,
  ContextProfileCreate,
  ContextProfileUpdate,
  ResolvedProfileResponse,
  AvatarResponse,
  AvatarDeleteResponse,
} from "@/types";

export const contextService = {
  /**
   * Get all context profiles for a user.
   */
  async list(userId: string): Promise<ContextProfileResponse[]> {
    const response = await api.get<ContextProfileResponse[]>(
      `/profiles/${userId}/contexts`,
      { params: { include_inactive: true } },
    );
    return response.data;
  },

  /**
   * Get a specific context profile (raw, with overrides only).
   */
  async get(
    userId: string,
    contextId: string,
  ): Promise<ContextProfileResponse> {
    const response = await api.get<ContextProfileResponse>(
      `/profiles/${userId}/contexts/${contextId}`,
    );
    return response.data;
  },

  /**
   * Create a new context profile.
   *
   * Note: Pseudonymous accounts cannot create legal or healthcare contexts.
   * This restriction is enforced by the backend and returns 403.
   */
  async create(
    userId: string,
    data: ContextProfileCreate,
  ): Promise<ContextProfileResponse> {
    const response = await api.post<ContextProfileResponse>(
      `/profiles/${userId}/contexts`,
      data,
    );
    return response.data;
  },

  /**
   * Update a context profile.
   *
   * Set fields to null to inherit from base profile.
   * Set fields to explicit values to override.
   */
  async update(
    userId: string,
    contextId: string,
    data: ContextProfileUpdate,
  ): Promise<ContextProfileResponse> {
    const response = await api.patch<ContextProfileResponse>(
      `/profiles/${userId}/contexts/${contextId}`,
      data,
    );
    return response.data;
  },

  /**
   * Delete a context profile (soft delete).
   */
  async delete(userId: string, contextId: string): Promise<void> {
    await api.delete(`/profiles/${userId}/contexts/${contextId}`);
  },

  /**
   * Get resolved profile for a specific context.
   *
   * Returns merged profile with:
   * - Base profile fields as defaults
   * - Context overrides applied (non-null values)
   * - Multilingual name resolution based on Accept-Language header
   *
   * Returns 410 Gone if context has expired (valid_to < now).
   */
  async getResolved(
    userId: string,
    contextId: string,
  ): Promise<ResolvedProfileResponse> {
    const response = await api.get<ResolvedProfileResponse>(
      `/profiles/${userId}/contexts/${contextId}/resolved`,
    );
    return response.data;
  },

  /**
   * Upload or replace a context-specific avatar override.
   * When set, this avatar takes precedence over the base avatar
   * in resolved profiles.
   */
  async uploadAvatar(
    userId: string,
    contextId: string,
    file: File,
  ): Promise<AvatarResponse> {
    const formData = new FormData();
    formData.append("file", file);
    const response = await api.post<AvatarResponse>(
      `/profiles/${userId}/contexts/${contextId}/avatar`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
    return response.data;
  },

  /**
   * Delete a context-specific avatar override.
   * After deletion, the resolved profile returns null for avatar fields.
   */
  async deleteAvatar(
    userId: string,
    contextId: string,
  ): Promise<AvatarDeleteResponse> {
    const response = await api.delete<AvatarDeleteResponse>(
      `/profiles/${userId}/contexts/${contextId}/avatar`,
    );
    return response.data;
  },
};

export default contextService;
