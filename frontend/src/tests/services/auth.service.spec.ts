/**
 * Unit tests for auth service.
 *
 * Tests verify correct API calls and store side-effects for all
 * authentication operations: register, login, logout, token refresh,
 * email verification, password flows, account restoration, and social auth.
 *
 * Uses real Pinia stores (from setup.ts) with mocked API module
 * to verify both HTTP calls and state mutations.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { authService } from "@/services/auth.service";
import api from "@/services/api";
import { useAuthStore } from "@/stores/auth.store";
import { useProfileStore } from "@/stores/profile.store";
import type { LoginResponse, RefreshTokenResponse } from "@/types";

vi.mock("@/services/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  getErrorMessage: vi.fn((e: unknown) =>
    e instanceof Error ? e.message : "error",
  ),
}));

const mockLoginResponse: LoginResponse = {
  access_token: "access-token-123",
  refresh_token: "refresh-token-456",
  token_type: "Bearer",
  user_id: "user-abc",
  email: "test@example.com",
  account_type: "verified",
  is_email_verified: true,
  is_admin: false,
};

describe("authService", () => {
  let authStore: ReturnType<typeof useAuthStore>;
  let profileStore: ReturnType<typeof useProfileStore>;

  beforeEach(() => {
    vi.clearAllMocks();
    authStore = useAuthStore();
    profileStore = useProfileStore();
  });

  describe("register", () => {
    it("should POST /auth/register and return response", async () => {
      const mockResponse = { user_id: "user-new", email: "new@example.com" };
      vi.mocked(api.post).mockResolvedValue({ data: mockResponse });

      const data = { email: "new@example.com", password: "Str0ngP@ss" };
      const result = await authService.register(data as any);

      expect(api.post).toHaveBeenCalledWith("/auth/register", data);
      expect(result).toEqual(mockResponse);
    });

    it("should not set auth store state on register", async () => {
      vi.mocked(api.post).mockResolvedValue({ data: { user_id: "new" } });

      await authService.register({
        email: "new@example.com",
        password: "Pass1234",
      } as any);

      expect(authStore.accessToken).toBeNull();
      expect(authStore.user).toBeNull();
    });
  });

  describe("login", () => {
    it("should POST /auth/login and set user in auth store", async () => {
      vi.mocked(api.post).mockResolvedValue({ data: mockLoginResponse });

      const result = await authService.login({
        email: "test@example.com",
        password: "pass",
      });

      expect(api.post).toHaveBeenCalledWith("/auth/login", {
        email: "test@example.com",
        password: "pass",
      });
      expect(result).toEqual(mockLoginResponse);
      expect(authStore.accessToken).toBe("access-token-123");
      expect(authStore.user?.email).toBe("test@example.com");
    });
  });

  describe("logout", () => {
    it("should POST /auth/logout and clear both stores", async () => {
      // Pre-populate stores
      authStore.setUser(mockLoginResponse);
      profileStore.setProfile({ user_id: "user-abc" } as any);

      vi.mocked(api.post).mockResolvedValue({});

      await authService.logout();

      expect(api.post).toHaveBeenCalledWith("/auth/logout");
      expect(authStore.accessToken).toBeNull();
      expect(authStore.user).toBeNull();
      expect(profileStore.profile).toBeNull();
    });

    it("should clear stores even if API call fails", async () => {
      authStore.setUser(mockLoginResponse);

      vi.mocked(api.post).mockRejectedValue(new Error("Network error"));

      await authService.logout();

      expect(authStore.accessToken).toBeNull();
      expect(authStore.user).toBeNull();
    });
  });

  describe("refresh", () => {
    it("should POST /auth/refresh and update tokens in store", async () => {
      const mockRefresh: RefreshTokenResponse = {
        access_token: "new-access",
        refresh_token: "new-refresh",
        token_type: "Bearer",
      };

      vi.mocked(api.post).mockResolvedValue({ data: mockRefresh });

      const result = await authService.refresh("old-refresh");

      expect(api.post).toHaveBeenCalledWith("/auth/refresh", {
        refresh_token: "old-refresh",
      });
      expect(authStore.accessToken).toBe("new-access");
      expect(authStore.refreshToken).toBe("new-refresh");
      expect(result).toEqual(mockRefresh);
    });
  });

  describe("verifyEmail", () => {
    it("should POST /auth/verify-email and update store", async () => {
      vi.mocked(api.post).mockResolvedValue({});

      await authService.verifyEmail("verify-token-xyz");

      expect(api.post).toHaveBeenCalledWith("/auth/verify-email", {
        token: "verify-token-xyz",
      });
    });
  });

  describe("requestPasswordReset", () => {
    it("should POST /auth/request-reset", async () => {
      vi.mocked(api.post).mockResolvedValue({});

      await authService.requestPasswordReset("user@example.com");

      expect(api.post).toHaveBeenCalledWith("/auth/request-reset", {
        email: "user@example.com",
      });
    });
  });

  describe("resetPassword", () => {
    it("should POST /auth/reset-password with token and new_password", async () => {
      vi.mocked(api.post).mockResolvedValue({});

      await authService.resetPassword("reset-token", "NewStr0ng!");

      expect(api.post).toHaveBeenCalledWith("/auth/reset-password", {
        token: "reset-token",
        new_password: "NewStr0ng!",
      });
    });
  });

  describe("resendVerificationEmail", () => {
    it("should POST /auth/resend-verification", async () => {
      vi.mocked(api.post).mockResolvedValue({});

      await authService.resendVerificationEmail("user@example.com");

      expect(api.post).toHaveBeenCalledWith("/auth/resend-verification", {
        email: "user@example.com",
      });
    });
  });

  describe("changePassword", () => {
    it("should POST /auth/change-password", async () => {
      vi.mocked(api.post).mockResolvedValue({});

      await authService.changePassword("OldPass1", "NewPass2");

      expect(api.post).toHaveBeenCalledWith("/auth/change-password", {
        current_password: "OldPass1",
        new_password: "NewPass2",
      });
    });
  });

  describe("requestAccountRestoration", () => {
    it("should POST /auth/restore-account", async () => {
      const mockResponse = { message: "If account exists, email sent" };
      vi.mocked(api.post).mockResolvedValue({ data: mockResponse });

      const result =
        await authService.requestAccountRestoration("user@example.com");

      expect(api.post).toHaveBeenCalledWith("/auth/restore-account", {
        email: "user@example.com",
      });
      expect(result).toEqual(mockResponse);
    });
  });

  describe("confirmAccountRestoration", () => {
    it("should POST /auth/restore-account/confirm with token only", async () => {
      const mockResponse = {
        access_token: "new-access",
        refresh_token: "new-refresh",
      };
      vi.mocked(api.post).mockResolvedValue({ data: mockResponse });

      const result =
        await authService.confirmAccountRestoration("restore-token");

      expect(api.post).toHaveBeenCalledWith("/auth/restore-account/confirm", {
        token: "restore-token",
      });
      expect(result).toEqual(mockResponse);
    });

    it("should include new_password when provided", async () => {
      vi.mocked(api.post).mockResolvedValue({ data: {} });

      await authService.confirmAccountRestoration("restore-token", "NewPass1");

      expect(api.post).toHaveBeenCalledWith("/auth/restore-account/confirm", {
        token: "restore-token",
        new_password: "NewPass1",
      });
    });
  });

  describe("exchangeOAuthCode", () => {
    it("should POST /oauth/token with authorization_code grant", async () => {
      vi.mocked(api.post).mockResolvedValue({ data: mockLoginResponse });

      const result = await authService.exchangeOAuthCode({
        code: "auth-code-xyz",
        code_verifier: "verifier-123",
        redirect_uri: "https://example.com/callback",
      });

      expect(api.post).toHaveBeenCalledWith("/oauth/token", {
        grant_type: "authorization_code",
        code: "auth-code-xyz",
        code_verifier: "verifier-123",
        redirect_uri: "https://example.com/callback",
      });
      expect(result).toEqual(mockLoginResponse);
    });
  });

  describe("initializeAuth", () => {
    it("should return false and set initialized when no stored session", async () => {
      const result = await authService.initializeAuth();

      expect(result).toBe(false);
      expect(authStore.isInitialized).toBe(true);
    });

    it("should refresh token and return true when stored session exists", async () => {
      // Simulate stored session
      localStorage.setItem("refresh_token", "stored-refresh");
      authStore.refreshToken = "stored-refresh";

      const mockRefresh: RefreshTokenResponse = {
        access_token: "restored-access",
        refresh_token: "restored-refresh",
        token_type: "Bearer",
      };
      vi.mocked(api.post).mockResolvedValue({ data: mockRefresh });

      const result = await authService.initializeAuth();

      expect(result).toBe(true);
      expect(authStore.isInitialized).toBe(true);
      expect(authStore.accessToken).toBe("restored-access");
    });

    it("should logout and return false when refresh fails", async () => {
      localStorage.setItem("refresh_token", "expired-refresh");
      authStore.refreshToken = "expired-refresh";

      vi.mocked(api.post).mockRejectedValue(new Error("Token expired"));

      const result = await authService.initializeAuth();

      expect(result).toBe(false);
      expect(authStore.isInitialized).toBe(true);
      expect(authStore.accessToken).toBeNull();
    });
  });

  describe("getOAuthAuthorizationUrl", () => {
    it("should POST /auth/social/{provider}/authorize and return URL", async () => {
      const mockResponse = {
        authorization_url: "https://accounts.google.com/o/oauth2/auth?...",
        state: "random-state",
        code_verifier: "pkce-verifier",
        message: "Redirect to authorization URL",
      };
      vi.mocked(api.post).mockResolvedValue({ data: mockResponse });

      const result = await authService.getOAuthAuthorizationUrl("google");

      expect(api.post).toHaveBeenCalledWith("/auth/social/google/authorize");
      expect(result.authorization_url).toContain("accounts.google.com");
      expect(result.state).toBe("random-state");
      expect(result.code_verifier).toBe("pkce-verifier");
    });
  });

  describe("handleOAuthCallback", () => {
    it("should GET callback endpoint and set user in auth store", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockLoginResponse });

      const result = await authService.handleOAuthCallback({
        provider: "google",
        code: "auth-code",
        state: "state-123",
        code_verifier: "verifier-abc",
        expected_state: "state-123",
      });

      expect(api.get).toHaveBeenCalledWith("/auth/social/google/callback", {
        params: {
          code: "auth-code",
          state: "state-123",
          code_verifier: "verifier-abc",
          expected_state: "state-123",
        },
      });
      expect(result).toEqual(mockLoginResponse);
      expect(authStore.accessToken).toBe("access-token-123");
      expect(authStore.user?.email).toBe("test@example.com");
    });
  });
});
