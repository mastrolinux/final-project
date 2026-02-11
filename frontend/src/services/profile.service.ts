/**
 * Profile service for managing base profiles and identity names.
 */

import api from './api'
import type {
  ProfileResponse,
  ProfileCreate,
  ProfileUpdate,
  IdentityName,
  IdentityNameCreate,
  ResolvedBaseProfile,
  AvatarResponse,
  AvatarDeleteResponse
} from '@/types'

export const profileService = {
  /**
   * Create a new profile.
   */
  async create(data: ProfileCreate): Promise<ProfileResponse> {
    const response = await api.post<ProfileResponse>('/profiles', data)
    return response.data
  },

  /**
   * Get profile by user ID.
   */
  async get(userId: string): Promise<ProfileResponse> {
    const response = await api.get<ProfileResponse>(`/profiles/${userId}`)
    return response.data
  },

  /**
   * Update profile fields.
   */
  async update(userId: string, data: ProfileUpdate): Promise<ProfileResponse> {
    const response = await api.patch<ProfileResponse>(`/profiles/${userId}`, data)
    return response.data
  },

  /**
   * Soft delete profile (30-day retention).
   */
  async delete(userId: string): Promise<void> {
    await api.delete(`/profiles/${userId}`)
  },

  /**
   * Get resolved base profile with multilingual name resolution.
   * Respects Accept-Language header for name fallback.
   */
  async getResolved(userId: string): Promise<ResolvedBaseProfile> {
    const response = await api.get<ResolvedBaseProfile>(`/profiles/${userId}/resolved`)
    return response.data
  },

  /**
   * Get all identity names for a user.
   */
  async getNames(userId: string): Promise<IdentityName[]> {
    const response = await api.get<IdentityName[]>(`/profiles/${userId}/names`)
    return response.data
  },

  /**
   * Add a new identity name.
   */
  async addName(userId: string, data: IdentityNameCreate): Promise<IdentityName> {
    const response = await api.post<IdentityName>(`/profiles/${userId}/names`, data)
    return response.data
  },

  /**
   * Update an identity name.
   */
  async updateName(
    userId: string,
    nameId: string,
    data: Partial<IdentityNameCreate>
  ): Promise<IdentityName> {
    const response = await api.patch<IdentityName>(`/profiles/${userId}/names/${nameId}`, data)
    return response.data
  },

  /**
   * Delete an identity name.
   */
  async deleteName(userId: string, nameId: string): Promise<void> {
    await api.delete(`/profiles/${userId}/names/${nameId}`)
  },

  /**
   * Upload or replace the base profile avatar.
   * Sends file as multipart/form-data. Backend processes it to 400x400 avatar
   * and 80x80 thumbnail in WebP format.
   */
  async uploadAvatar(userId: string, file: File): Promise<AvatarResponse> {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post<AvatarResponse>(
      `/profiles/${userId}/avatar`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
    return response.data
  },

  /**
   * Delete the base profile avatar.
   * After deletion, the profile reverts to text-based initials.
   */
  async deleteAvatar(userId: string): Promise<AvatarDeleteResponse> {
    const response = await api.delete<AvatarDeleteResponse>(`/profiles/${userId}/avatar`)
    return response.data
  }
}

export default profileService
