/**
 * Unit tests for context service.
 *
 * Tests verify correct API calls for context profile CRUD,
 * resolved profile fetching, and context avatar operations.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { contextService } from "@/services/context.service";
import api from "@/services/api";
import type {
  ContextProfileResponse,
  ResolvedProfileResponse,
  AvatarResponse,
  AvatarDeleteResponse,
} from "@/types";

vi.mock("@/services/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

const userId = "user-abc-123";
const contextId = "ctx-professional-1";

describe("contextService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("list", () => {
    it("should GET /profiles/{userId}/contexts", async () => {
      const mockContexts: ContextProfileResponse[] = [
        {
          id: contextId,
          context_type: "professional",
        } as unknown as ContextProfileResponse,
      ];

      vi.mocked(api.get).mockResolvedValue({ data: mockContexts });

      const result = await contextService.list(userId);

      expect(api.get).toHaveBeenCalledWith(`/profiles/${userId}/contexts`, {
        params: { include_inactive: true },
      });
      expect(result).toHaveLength(1);
      expect(result[0].context_type).toBe("professional");
    });
  });

  describe("get", () => {
    it("should GET /profiles/{userId}/contexts/{contextId}", async () => {
      const mockContext = {
        id: contextId,
        context_type: "professional",
      } as unknown as ContextProfileResponse;

      vi.mocked(api.get).mockResolvedValue({ data: mockContext });

      const result = await contextService.get(userId, contextId);

      expect(api.get).toHaveBeenCalledWith(
        `/profiles/${userId}/contexts/${contextId}`,
      );
      expect(result.id).toBe(contextId);
    });
  });

  describe("create", () => {
    it("should POST /profiles/{userId}/contexts", async () => {
      const mockContext = {
        id: "ctx-new",
        context_type: "social",
        display_name: "Casual Me",
      } as unknown as ContextProfileResponse;

      vi.mocked(api.post).mockResolvedValue({ data: mockContext });

      const data = {
        context_type: "social" as const,
        display_name: "Casual Me",
      };
      const result = await contextService.create(userId, data as any);

      expect(api.post).toHaveBeenCalledWith(
        `/profiles/${userId}/contexts`,
        data,
      );
      expect(result.display_name).toBe("Casual Me");
    });
  });

  describe("update", () => {
    it("should PATCH /profiles/{userId}/contexts/{contextId}", async () => {
      const updated = {
        id: contextId,
        display_name: "Dr. Chen",
      } as unknown as ContextProfileResponse;

      vi.mocked(api.patch).mockResolvedValue({ data: updated });

      const data = { display_name: "Dr. Chen" };
      const result = await contextService.update(
        userId,
        contextId,
        data as any,
      );

      expect(api.patch).toHaveBeenCalledWith(
        `/profiles/${userId}/contexts/${contextId}`,
        data,
      );
      expect(result.display_name).toBe("Dr. Chen");
    });

    it("should send null values for inherited fields", async () => {
      vi.mocked(api.patch).mockResolvedValue({ data: {} });

      const data = { display_name: null, bio: null };
      await contextService.update(userId, contextId, data as any);

      expect(api.patch).toHaveBeenCalledWith(
        `/profiles/${userId}/contexts/${contextId}`,
        { display_name: null, bio: null },
      );
    });
  });

  describe("delete", () => {
    it("should DELETE /profiles/{userId}/contexts/{contextId}", async () => {
      vi.mocked(api.delete).mockResolvedValue({});

      await contextService.delete(userId, contextId);

      expect(api.delete).toHaveBeenCalledWith(
        `/profiles/${userId}/contexts/${contextId}`,
      );
    });
  });

  describe("getResolved", () => {
    it("should GET /profiles/{userId}/contexts/{contextId}/resolved", async () => {
      const mockResolved: ResolvedProfileResponse = {
        user_id: userId,
        context_type: "professional",
        display_name: "Dr. Sarah Chen",
        email: "sarah.chen@hospital.org",
      } as unknown as ResolvedProfileResponse;

      vi.mocked(api.get).mockResolvedValue({ data: mockResolved });

      const result = await contextService.getResolved(userId, contextId);

      expect(api.get).toHaveBeenCalledWith(
        `/profiles/${userId}/contexts/${contextId}/resolved`,
      );
      expect(result.display_name).toBe("Dr. Sarah Chen");
    });
  });

  describe("uploadAvatar", () => {
    it("should POST multipart/form-data to context avatar endpoint", async () => {
      const mockResponse: AvatarResponse = {
        avatar_url: "/avatars/ctx-1.webp",
        thumbnail_url: "/avatars/ctx-1-thumb.webp",
      } as unknown as AvatarResponse;

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse });

      const file = new File(["pixels"], "avatar.jpg", { type: "image/jpeg" });
      const result = await contextService.uploadAvatar(userId, contextId, file);

      expect(api.post).toHaveBeenCalledWith(
        `/profiles/${userId}/contexts/${contextId}/avatar`,
        expect.any(FormData),
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      const callArgs = vi.mocked(api.post).mock.calls[0];
      const formData = callArgs[1] as FormData;
      expect(formData.get("file")).toBe(file);
      expect(result.avatar_url).toBe("/avatars/ctx-1.webp");
    });
  });

  describe("deleteAvatar", () => {
    it("should DELETE context avatar endpoint", async () => {
      const mockResponse: AvatarDeleteResponse = {
        message: "Context avatar deleted",
      } as unknown as AvatarDeleteResponse;

      vi.mocked(api.delete).mockResolvedValue({ data: mockResponse });

      const result = await contextService.deleteAvatar(userId, contextId);

      expect(api.delete).toHaveBeenCalledWith(
        `/profiles/${userId}/contexts/${contextId}/avatar`,
      );
      expect(result).toEqual(mockResponse);
    });
  });
});
