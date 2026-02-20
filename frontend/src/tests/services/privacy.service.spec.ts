/**
 * Unit tests for privacy service.
 *
 * Tests verify correct API calls for GDPR Article 15 data export,
 * Article 17 deletion request, and deletion status queries.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import privacyService from "@/services/privacy.service";
import api from "@/services/api";
import type {
  DataExportResponse,
  DeletionRequestResponse,
  DeletionStatusResponse,
} from "@/types";

vi.mock("@/services/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("privacyService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("exportUserData", () => {
    it("should GET /privacy/export and return structured data", async () => {
      const mockExport: DataExportResponse = {
        metadata: {
          exported_at: "2026-02-18T10:00:00Z",
          format_version: "1.0",
          user_id: "user-123",
        },
        profile: {
          user_id: "user-123",
          account_type: "verified",
          email: "test@example.com",
        },
        identity_names: [],
        context_profiles: [],
        authentication: {
          email: "test@example.com",
          is_email_verified: true,
          created_at: "2026-01-01T00:00:00Z",
        },
        oauth_consents: [],
        gdpr: {
          data_controller: "Identity API",
          processing_purposes: ["identity_management"],
          retention_policy: "30 days after deletion request",
        },
      } as unknown as DataExportResponse;

      vi.mocked(api.get).mockResolvedValue({ data: mockExport });

      const result = await privacyService.exportUserData();

      expect(api.get).toHaveBeenCalledWith("/privacy/export");
      expect(result).toEqual(mockExport);
    });
  });

  describe("requestDeletion", () => {
    it("should POST /privacy/deletion-request and return response", async () => {
      const mockResponse: DeletionRequestResponse = {
        status: "scheduled",
        deletion_scheduled_at: "2026-02-18T10:00:00Z",
        permanent_deletion_date: "2026-03-20T10:00:00Z",
      };

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse });

      const result = await privacyService.requestDeletion();

      expect(api.post).toHaveBeenCalledWith("/privacy/deletion-request");
      expect(result.status).toBe("scheduled");
      expect(result.permanent_deletion_date).toBe("2026-03-20T10:00:00Z");
    });
  });

  describe("getDeletionStatus", () => {
    it("should GET /privacy/deletion-status and return active status", async () => {
      const mockResponse: DeletionStatusResponse = {
        status: "active",
      } as DeletionStatusResponse;

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      const result = await privacyService.getDeletionStatus();

      expect(api.get).toHaveBeenCalledWith("/privacy/deletion-status");
      expect(result.status).toBe("active");
    });

    it("should return scheduled status with dates", async () => {
      const mockResponse: DeletionStatusResponse = {
        status: "scheduled",
        deletion_scheduled_at: "2026-02-18T10:00:00Z",
        permanent_deletion_date: "2026-03-20T10:00:00Z",
      } as DeletionStatusResponse;

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      const result = await privacyService.getDeletionStatus();

      expect(result.status).toBe("scheduled");
    });
  });
});
