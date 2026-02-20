/**
 * Unit tests for admin OAuth service.
 *
 * Tests verify correct API calls for OAuth client CRUD operations
 * and scope listing. All endpoints require admin privileges.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import adminOAuthService from "@/services/admin-oauth.service";
import api from "@/services/api";
import type {
  OAuthClientCreateResponse,
  OAuthClientResponse,
  OAuthClientListResponse,
  ScopeListResponse,
} from "@/types";

vi.mock("@/services/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

describe("adminOAuthService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("createClient", () => {
    it("should POST /admin/oauth/clients and return client with secret", async () => {
      const mockResponse: OAuthClientCreateResponse = {
        client_id: "new-client-id",
        client_name: "Test App",
        client_secret: "plaintext-secret-shown-once",
        redirect_uris: ["https://example.com/callback"],
      } as unknown as OAuthClientCreateResponse;

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse });

      const data = {
        client_name: "Test App",
        redirect_uris: ["https://example.com/callback"],
        grant_types: ["authorization_code"],
        scope: "openid profile:read:basic",
      };

      const result = await adminOAuthService.createClient(data as any);

      expect(api.post).toHaveBeenCalledWith("/admin/oauth/clients", data);
      expect(result.client_secret).toBe("plaintext-secret-shown-once");
    });
  });

  describe("listClients", () => {
    it("should GET /admin/oauth/clients with default pagination", async () => {
      const mockResponse: OAuthClientListResponse = {
        clients: [],
        total: 0,
        page: 1,
        page_size: 20,
      } as unknown as OAuthClientListResponse;

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      const result = await adminOAuthService.listClients();

      expect(api.get).toHaveBeenCalledWith("/admin/oauth/clients", {
        params: { page: 1, page_size: 20, include_inactive: false },
      });
      expect(result).toEqual(mockResponse);
    });

    it("should pass custom pagination and includeInactive params", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { clients: [], total: 0 } });

      await adminOAuthService.listClients(3, 10, true);

      expect(api.get).toHaveBeenCalledWith("/admin/oauth/clients", {
        params: { page: 3, page_size: 10, include_inactive: true },
      });
    });
  });

  describe("getClient", () => {
    it("should GET /admin/oauth/clients/{id}", async () => {
      const mockClient: OAuthClientResponse = {
        client_id: "client-abc",
        client_name: "My App",
        is_active: true,
      } as unknown as OAuthClientResponse;

      vi.mocked(api.get).mockResolvedValue({ data: mockClient });

      const result = await adminOAuthService.getClient("client-abc");

      expect(api.get).toHaveBeenCalledWith("/admin/oauth/clients/client-abc");
      expect(result.client_name).toBe("My App");
    });
  });

  describe("updateClient", () => {
    it("should PATCH /admin/oauth/clients/{id}", async () => {
      const mockClient: OAuthClientResponse = {
        client_id: "client-abc",
        client_name: "Updated App",
      } as unknown as OAuthClientResponse;

      vi.mocked(api.patch).mockResolvedValue({ data: mockClient });

      const updates = { client_name: "Updated App" };
      const result = await adminOAuthService.updateClient(
        "client-abc",
        updates as any,
      );

      expect(api.patch).toHaveBeenCalledWith(
        "/admin/oauth/clients/client-abc",
        updates,
      );
      expect(result.client_name).toBe("Updated App");
    });
  });

  describe("deleteClient", () => {
    it("should DELETE /admin/oauth/clients/{id}", async () => {
      vi.mocked(api.delete).mockResolvedValue({});

      await adminOAuthService.deleteClient("client-abc");

      expect(api.delete).toHaveBeenCalledWith(
        "/admin/oauth/clients/client-abc",
      );
    });
  });

  describe("fetchScopes", () => {
    it("should GET /oauth/scopes", async () => {
      const mockScopes: ScopeListResponse = {
        scopes: [
          {
            scope_name: "openid",
            description: "Basic identity",
            is_sensitive: false,
          },
          {
            scope_name: "profile:read:basic",
            description: "Name and type",
            is_sensitive: false,
          },
        ],
      } as unknown as ScopeListResponse;

      vi.mocked(api.get).mockResolvedValue({ data: mockScopes });

      const result = await adminOAuthService.fetchScopes();

      expect(api.get).toHaveBeenCalledWith("/oauth/scopes");
      expect(result).toEqual(mockScopes);
    });
  });
});
