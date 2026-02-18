/**
 * Unit tests for profile service.
 *
 * Tests verify correct API calls for base profile CRUD,
 * identity name management, and avatar upload/delete operations.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { profileService } from '@/services/profile.service'
import api from '@/services/api'
import type {
  ProfileResponse,
  IdentityName,
  ResolvedBaseProfile,
  AvatarResponse,
  AvatarDeleteResponse
} from '@/types'

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn()
  }
}))

const userId = 'user-abc-123'

describe('profileService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('create', () => {
    it('should POST /profiles with data', async () => {
      const mockProfile: ProfileResponse = {
        user_id: userId,
        account_type: 'verified',
        email: 'test@example.com'
      } as unknown as ProfileResponse

      vi.mocked(api.post).mockResolvedValue({ data: mockProfile })

      const data = { account_type: 'verified' as const }
      const result = await profileService.create(data as any)

      expect(api.post).toHaveBeenCalledWith('/profiles', data)
      expect(result.user_id).toBe(userId)
    })
  })

  describe('get', () => {
    it('should GET /profiles/{userId}', async () => {
      const mockProfile = { user_id: userId } as ProfileResponse

      vi.mocked(api.get).mockResolvedValue({ data: mockProfile })

      const result = await profileService.get(userId)

      expect(api.get).toHaveBeenCalledWith(`/profiles/${userId}`)
      expect(result.user_id).toBe(userId)
    })
  })

  describe('update', () => {
    it('should PATCH /profiles/{userId}', async () => {
      const updated = { user_id: userId, email: 'new@example.com' } as ProfileResponse

      vi.mocked(api.patch).mockResolvedValue({ data: updated })

      const data = { email: 'new@example.com' }
      const result = await profileService.update(userId, data)

      expect(api.patch).toHaveBeenCalledWith(`/profiles/${userId}`, data)
      expect(result.email).toBe('new@example.com')
    })
  })

  describe('delete', () => {
    it('should DELETE /profiles/{userId}', async () => {
      vi.mocked(api.delete).mockResolvedValue({})

      await profileService.delete(userId)

      expect(api.delete).toHaveBeenCalledWith(`/profiles/${userId}`)
    })
  })

  describe('getResolved', () => {
    it('should GET /profiles/{userId}/resolved', async () => {
      const mockResolved = {
        user_id: userId,
        full_name: 'Test User'
      } as unknown as ResolvedBaseProfile

      vi.mocked(api.get).mockResolvedValue({ data: mockResolved })

      const result = await profileService.getResolved(userId)

      expect(api.get).toHaveBeenCalledWith(`/profiles/${userId}/resolved`)
      expect(result).toEqual(mockResolved)
    })
  })

  describe('getNames', () => {
    it('should GET /profiles/{userId}/names', async () => {
      const mockNames: IdentityName[] = [
        { id: 'name-1', name_type: 'given', name_data: { en: 'Sarah' } } as unknown as IdentityName
      ]

      vi.mocked(api.get).mockResolvedValue({ data: mockNames })

      const result = await profileService.getNames(userId)

      expect(api.get).toHaveBeenCalledWith(`/profiles/${userId}/names`)
      expect(result).toHaveLength(1)
    })
  })

  describe('addName', () => {
    it('should POST /profiles/{userId}/names', async () => {
      const newName = { id: 'name-2', name_type: 'family' } as unknown as IdentityName

      vi.mocked(api.post).mockResolvedValue({ data: newName })

      const data = { name_type: 'family' as const, name_data: { en: 'Chen' } }
      const result = await profileService.addName(userId, data as any)

      expect(api.post).toHaveBeenCalledWith(`/profiles/${userId}/names`, data)
      expect(result.id).toBe('name-2')
    })
  })

  describe('updateName', () => {
    it('should PATCH /profiles/{userId}/names/{nameId}', async () => {
      const updated = { id: 'name-1', name_data: { en: 'Sarah', zh: 'Chen' } } as unknown as IdentityName

      vi.mocked(api.patch).mockResolvedValue({ data: updated })

      const data = { name_data: { en: 'Sarah', zh: 'Chen' } }
      const result = await profileService.updateName(userId, 'name-1', data as any)

      expect(api.patch).toHaveBeenCalledWith(`/profiles/${userId}/names/name-1`, data)
      expect(result).toEqual(updated)
    })
  })

  describe('deleteName', () => {
    it('should DELETE /profiles/{userId}/names/{nameId}', async () => {
      vi.mocked(api.delete).mockResolvedValue({})

      await profileService.deleteName(userId, 'name-1')

      expect(api.delete).toHaveBeenCalledWith(`/profiles/${userId}/names/name-1`)
    })
  })

  describe('uploadAvatar', () => {
    it('should POST multipart/form-data to /profiles/{userId}/avatar', async () => {
      const mockResponse: AvatarResponse = {
        avatar_url: '/avatars/user-abc-123.webp',
        thumbnail_url: '/avatars/user-abc-123-thumb.webp'
      } as unknown as AvatarResponse

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const file = new File(['pixels'], 'photo.png', { type: 'image/png' })
      const result = await profileService.uploadAvatar(userId, file)

      expect(api.post).toHaveBeenCalledWith(
        `/profiles/${userId}/avatar`,
        expect.any(FormData),
        { headers: { 'Content-Type': 'multipart/form-data' } }
      )
      // Verify FormData contains the file
      const callArgs = vi.mocked(api.post).mock.calls[0]
      const formData = callArgs[1] as FormData
      expect(formData.get('file')).toBe(file)
      expect(result.avatar_url).toBe('/avatars/user-abc-123.webp')
    })
  })

  describe('deleteAvatar', () => {
    it('should DELETE /profiles/{userId}/avatar', async () => {
      const mockResponse: AvatarDeleteResponse = {
        message: 'Avatar deleted'
      } as unknown as AvatarDeleteResponse

      vi.mocked(api.delete).mockResolvedValue({ data: mockResponse })

      const result = await profileService.deleteAvatar(userId)

      expect(api.delete).toHaveBeenCalledWith(`/profiles/${userId}/avatar`)
      expect(result).toEqual(mockResponse)
    })
  })
})
