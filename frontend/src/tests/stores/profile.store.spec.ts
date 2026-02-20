/**
 * Unit tests for profile store.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useProfileStore } from "@/stores/profile.store";
import type {
  ProfileResponse,
  ContextProfileResponse,
  IdentityName,
  ResolvedProfileResponse,
} from "@/types";

const makeContext = (
  overrides: Partial<ContextProfileResponse> = {},
): ContextProfileResponse =>
  ({
    id: "ctx-1",
    user_id: "user-123",
    context_type: "professional",
    context_name: "Work",
    display_name_override: null,
    email_override: null,
    phone_override: null,
    bio: null,
    is_active: true,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    deleted_at: null,
    valid_from: "2024-01-01T00:00:00Z",
    valid_to: null,
    ...overrides,
  }) as ContextProfileResponse;

describe("useProfileStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  describe("initial state", () => {
    it("should have null profile initially", () => {
      const store = useProfileStore();
      expect(store.profile).toBeNull();
    });

    it("should have empty contexts array initially", () => {
      const store = useProfileStore();
      expect(store.contexts).toEqual([]);
    });

    it("should have null active context ID initially", () => {
      const store = useProfileStore();
      expect(store.activeContextId).toBeNull();
    });

    it("should not be loading initially", () => {
      const store = useProfileStore();
      expect(store.isLoading).toBe(false);
    });
  });

  describe("setProfile", () => {
    it("should set profile data", () => {
      const store = useProfileStore();
      const profile: ProfileResponse = {
        id: "profile-123",
        user_id: "user-123",
        account_type: "verified",
        primary_email: "test@example.com",
        primary_phone: null,
        preferred_language: "en",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
        deleted_at: null,
      };

      store.setProfile(profile);

      expect(store.profile).toEqual(profile);
      expect(store.hasProfile).toBe(true);
    });
  });

  describe("setContexts", () => {
    it("should set contexts array", () => {
      const store = useProfileStore();
      const contexts: ContextProfileResponse[] = [
        {
          id: "ctx-1",
          user_id: "user-123",
          context_type: "professional",
          context_name: "Work",
          display_name_override: null,
          email_override: "work@example.com",
          phone_override: null,
          bio: null,
          is_active: true,
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
          deleted_at: null,
          valid_from: "2024-01-01T00:00:00Z",
          valid_to: null,
        },
      ];

      store.setContexts(contexts);

      expect(store.contexts).toEqual(contexts);
      expect(store.hasContexts).toBe(true);
    });
  });

  describe("addContext", () => {
    it("should add a context to the array", () => {
      const store = useProfileStore();
      const context: ContextProfileResponse = {
        id: "ctx-1",
        user_id: "user-123",
        context_type: "social",
        context_name: "Social Media",
        display_name_override: "Nickname",
        email_override: null,
        phone_override: null,
        bio: "My social profile",
        is_active: true,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
        deleted_at: null,
        valid_from: "2024-01-01T00:00:00Z",
        valid_to: null,
      };

      store.addContext(context);

      expect(store.contexts).toHaveLength(1);
      expect(store.contexts[0]).toEqual(context);
    });
  });

  describe("updateContext", () => {
    it("should update an existing context", () => {
      const store = useProfileStore();
      const original: ContextProfileResponse = {
        id: "ctx-1",
        user_id: "user-123",
        context_type: "professional",
        context_name: "Work",
        display_name_override: null,
        email_override: null,
        phone_override: null,
        bio: null,
        is_active: true,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
        deleted_at: null,
        valid_from: "2024-01-01T00:00:00Z",
        valid_to: null,
      };

      store.setContexts([original]);

      const updated: ContextProfileResponse = {
        ...original,
        context_name: "Updated Work",
        bio: "Professional context",
        updated_at: "2024-01-02T00:00:00Z",
      };

      store.updateContext(updated);

      expect(store.contexts[0].context_name).toBe("Updated Work");
      expect(store.contexts[0].bio).toBe("Professional context");
    });

    it("should not modify array if context not found", () => {
      const store = useProfileStore();
      const context: ContextProfileResponse = {
        id: "ctx-1",
        user_id: "user-123",
        context_type: "professional",
        context_name: "Work",
        display_name_override: null,
        email_override: null,
        phone_override: null,
        bio: null,
        is_active: true,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
        deleted_at: null,
        valid_from: "2024-01-01T00:00:00Z",
        valid_to: null,
      };

      store.setContexts([context]);

      const nonExistent: ContextProfileResponse = {
        ...context,
        id: "ctx-999",
        context_name: "Nonexistent",
      };

      store.updateContext(nonExistent);

      expect(store.contexts).toHaveLength(1);
      expect(store.contexts[0].context_name).toBe("Work");
    });
  });

  describe("removeContext", () => {
    it("should remove a context by ID", () => {
      const store = useProfileStore();
      const contexts: ContextProfileResponse[] = [
        {
          id: "ctx-1",
          user_id: "user-123",
          context_type: "professional",
          context_name: "Work",
          display_name_override: null,
          email_override: null,
          phone_override: null,
          bio: null,
          is_active: true,
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
          deleted_at: null,
          valid_from: "2024-01-01T00:00:00Z",
          valid_to: null,
        },
        {
          id: "ctx-2",
          user_id: "user-123",
          context_type: "social",
          context_name: "Social",
          display_name_override: null,
          email_override: null,
          phone_override: null,
          bio: null,
          is_active: true,
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
          deleted_at: null,
          valid_from: "2024-01-01T00:00:00Z",
          valid_to: null,
        },
      ];

      store.setContexts(contexts);
      store.removeContext("ctx-1");

      expect(store.contexts).toHaveLength(1);
      expect(store.contexts[0].id).toBe("ctx-2");
    });
  });

  describe("clearProfile", () => {
    it("should clear all profile data", () => {
      const store = useProfileStore();

      store.setProfile({
        id: "profile-123",
        user_id: "user-123",
        account_type: "verified",
        primary_email: "test@example.com",
        primary_phone: null,
        preferred_language: "en",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
        deleted_at: null,
      });

      store.setContexts([
        {
          id: "ctx-1",
          user_id: "user-123",
          context_type: "professional",
          context_name: "Work",
          display_name_override: null,
          email_override: null,
          phone_override: null,
          bio: null,
          is_active: true,
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
          deleted_at: null,
          valid_from: "2024-01-01T00:00:00Z",
          valid_to: null,
        },
      ]);

      store.setActiveContext("ctx-1");

      store.clearProfile();

      expect(store.profile).toBeNull();
      expect(store.contexts).toEqual([]);
      expect(store.activeContextId).toBeNull();
    });
  });

  describe("auto-primary identity name", () => {
    const makeName = (overrides: Partial<IdentityName> = {}): IdentityName => ({
      id: "name-1",
      identity_id: "user-123",
      name_type: "preferred",
      name_value: { en: "Test User" },
      is_primary: false,
      is_deprecated: false,
      visibility_level: "public",
      context_id: null,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
      ...overrides,
    });

    it("should auto-promote first non-deprecated name when none is primary", () => {
      const store = useProfileStore();
      const names = [
        makeName({ id: "n1", name_value: { en: "First" } }),
        makeName({ id: "n2", name_value: { en: "Second" } }),
      ];

      store.setIdentityNames(names);

      expect(store.identityNames[0].is_primary).toBe(true);
      expect(store.identityNames[1].is_primary).toBe(false);
      expect(store.autoPromotedPrimary).toBe(true);
    });

    it("should not auto-promote if a primary already exists", () => {
      const store = useProfileStore();
      const names = [
        makeName({ id: "n1", name_value: { en: "First" } }),
        makeName({ id: "n2", name_value: { en: "Second" }, is_primary: true }),
      ];

      store.setIdentityNames(names);

      expect(store.identityNames[0].is_primary).toBe(false);
      expect(store.identityNames[1].is_primary).toBe(true);
      expect(store.autoPromotedPrimary).toBe(false);
    });

    it("should skip deprecated names when auto-promoting", () => {
      const store = useProfileStore();
      const names = [
        makeName({
          id: "n1",
          name_value: { en: "Deprecated" },
          is_deprecated: true,
        }),
        makeName({ id: "n2", name_value: { en: "Active" } }),
      ];

      store.setIdentityNames(names);

      expect(store.identityNames[0].is_primary).toBe(false);
      expect(store.identityNames[1].is_primary).toBe(true);
      expect(store.autoPromotedPrimary).toBe(true);
    });

    it("should not auto-promote if all names are deprecated", () => {
      const store = useProfileStore();
      const names = [
        makeName({ id: "n1", is_deprecated: true }),
        makeName({ id: "n2", is_deprecated: true }),
      ];

      store.setIdentityNames(names);

      expect(store.identityNames.every((n) => !n.is_primary)).toBe(true);
      expect(store.autoPromotedPrimary).toBe(false);
    });

    it("should clear autoPromotedPrimary on clearProfile", () => {
      const store = useProfileStore();
      store.setIdentityNames([makeName()]);
      expect(store.autoPromotedPrimary).toBe(true);

      store.clearProfile();
      expect(store.autoPromotedPrimary).toBe(false);
    });
  });

  describe("activeContext", () => {
    it("should return the active context", () => {
      const store = useProfileStore();
      const contexts: ContextProfileResponse[] = [
        {
          id: "ctx-1",
          user_id: "user-123",
          context_type: "professional",
          context_name: "Work",
          display_name_override: null,
          email_override: null,
          phone_override: null,
          bio: null,
          is_active: true,
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
          deleted_at: null,
          valid_from: "2024-01-01T00:00:00Z",
          valid_to: null,
        },
        {
          id: "ctx-2",
          user_id: "user-123",
          context_type: "social",
          context_name: "Social",
          display_name_override: null,
          email_override: null,
          phone_override: null,
          bio: null,
          is_active: true,
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
          deleted_at: null,
          valid_from: "2024-01-01T00:00:00Z",
          valid_to: null,
        },
      ];

      store.setContexts(contexts);
      store.setActiveContext("ctx-2");

      expect(store.activeContext?.context_name).toBe("Social");
    });

    it("should return null if no active context", () => {
      const store = useProfileStore();
      expect(store.activeContext).toBeNull();
    });
  });

  describe("activeContexts", () => {
    it("should return only active contexts", () => {
      const store = useProfileStore();
      store.setContexts([
        makeContext({ id: "ctx-1", is_active: true }),
        makeContext({ id: "ctx-2", is_active: false }),
        makeContext({ id: "ctx-3", is_active: true }),
      ] as ContextProfileResponse[]);

      expect(store.activeContexts).toHaveLength(2);
      expect(store.activeContexts.map((c) => c.id)).toEqual(["ctx-1", "ctx-3"]);
    });
  });

  describe("displayName", () => {
    it("should return resolved profile display_name when available", () => {
      const store = useProfileStore();
      store.setResolvedProfile({
        display_name: "Dr. Sarah Chen",
      } as ResolvedProfileResponse);

      expect(store.displayName).toBe("Dr. Sarah Chen");
    });

    it("should fall back to primary name value for browser language", () => {
      const store = useProfileStore();
      store.setIdentityNames([
        {
          id: "n1",
          identity_id: "user-123",
          name_type: "preferred",
          name_value: { en: "English Name", it: "Nome Italiano" },
          is_primary: true,
          is_deprecated: false,
          visibility_level: "public",
          context_id: null,
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
        } as IdentityName,
      ]);

      // navigator.language defaults to 'en-US' in happy-dom, so lang = 'en'
      expect(store.displayName).toBe("English Name");
    });

    it("should fall back to en when browser language not available", () => {
      const store = useProfileStore();
      // Set a primary name that only has 'en' key
      store.setIdentityNames([
        {
          id: "n1",
          identity_id: "user-123",
          name_type: "preferred",
          name_value: { en: "Fallback English" },
          is_primary: true,
          is_deprecated: false,
          visibility_level: "public",
          context_id: null,
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
        } as IdentityName,
      ]);

      expect(store.displayName).toBe("Fallback English");
    });

    it("should fall back to email when no names and no resolved profile", () => {
      const store = useProfileStore();
      store.setProfile({
        id: "p1",
        user_id: "u1",
        account_type: "verified",
        primary_email: "fallback@test.com",
        primary_phone: null,
        preferred_language: "en",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
        deleted_at: null,
      } as ProfileResponse);

      expect(store.displayName).toBe("fallback@test.com");
    });

    it("should return empty string when no profile, no names, no resolved", () => {
      const store = useProfileStore();
      expect(store.displayName).toBe("");
    });
  });

  describe("removeContext clearing active context", () => {
    it("should clear activeContextId and resolvedProfile when removing the active context", () => {
      const store = useProfileStore();
      store.setContexts([
        makeContext({ id: "ctx-1" }),
      ] as ContextProfileResponse[]);
      store.setActiveContext("ctx-1");
      store.setResolvedProfile({
        display_name: "Test",
      } as ResolvedProfileResponse);

      store.removeContext("ctx-1");

      expect(store.activeContextId).toBeNull();
      expect(store.resolvedProfile).toBeNull();
      expect(store.contexts).toHaveLength(0);
    });

    it("should not clear activeContextId when removing a non-active context", () => {
      const store = useProfileStore();
      store.setContexts([
        makeContext({ id: "ctx-1" }),
        makeContext({ id: "ctx-2" }),
      ] as ContextProfileResponse[]);
      store.setActiveContext("ctx-1");

      store.removeContext("ctx-2");

      expect(store.activeContextId).toBe("ctx-1");
      expect(store.contexts).toHaveLength(1);
    });
  });

  describe("setProfileAvatar", () => {
    it("should update avatar URLs on profile", () => {
      const store = useProfileStore();
      store.setProfile({
        id: "p1",
        user_id: "u1",
        account_type: "verified",
        primary_email: "test@test.com",
        primary_phone: null,
        preferred_language: "en",
        avatar_url: null,
        avatar_thumbnail_url: null,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
        deleted_at: null,
      } as ProfileResponse);

      store.setProfileAvatar("/avatar.webp", "/thumb.webp");

      expect(store.profile!.avatar_url).toBe("/avatar.webp");
      expect(store.profile!.avatar_thumbnail_url).toBe("/thumb.webp");
    });

    it("should do nothing when profile is null", () => {
      const store = useProfileStore();
      store.setProfileAvatar("/avatar.webp", "/thumb.webp");
      expect(store.profile).toBeNull();
    });
  });

  describe("clearProfileAvatar", () => {
    it("should set avatar URLs to null", () => {
      const store = useProfileStore();
      store.setProfile({
        id: "p1",
        user_id: "u1",
        account_type: "verified",
        primary_email: "test@test.com",
        primary_phone: null,
        preferred_language: "en",
        avatar_url: "/avatar.webp",
        avatar_thumbnail_url: "/thumb.webp",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
        deleted_at: null,
      } as ProfileResponse);

      store.clearProfileAvatar();

      expect(store.profile!.avatar_url).toBeNull();
      expect(store.profile!.avatar_thumbnail_url).toBeNull();
    });

    it("should do nothing when profile is null", () => {
      const store = useProfileStore();
      store.clearProfileAvatar();
      expect(store.profile).toBeNull();
    });
  });

  describe("setContextAvatar", () => {
    it("should update avatar override URLs on a context", () => {
      const store = useProfileStore();
      store.setContexts([
        makeContext({ id: "ctx-1" }),
      ] as ContextProfileResponse[]);

      store.setContextAvatar("ctx-1", "/ctx-avatar.webp", "/ctx-thumb.webp");

      expect(store.contexts[0].avatar_override_url).toBe("/ctx-avatar.webp");
      expect(store.contexts[0].avatar_override_thumbnail_url).toBe(
        "/ctx-thumb.webp",
      );
    });

    it("should do nothing for non-existent context", () => {
      const store = useProfileStore();
      store.setContexts([
        makeContext({ id: "ctx-1" }),
      ] as ContextProfileResponse[]);

      store.setContextAvatar("ctx-999", "/avatar.webp", "/thumb.webp");

      expect(store.contexts[0].avatar_override_url).toBeUndefined();
    });
  });

  describe("clearContextAvatar", () => {
    it("should set context avatar override URLs to null", () => {
      const store = useProfileStore();
      const ctx = makeContext({ id: "ctx-1" }) as ContextProfileResponse;
      ctx.avatar_override_url = "/old.webp";
      ctx.avatar_override_thumbnail_url = "/old-thumb.webp";
      store.setContexts([ctx]);

      store.clearContextAvatar("ctx-1");

      expect(store.contexts[0].avatar_override_url).toBeNull();
      expect(store.contexts[0].avatar_override_thumbnail_url).toBeNull();
    });

    it("should do nothing for non-existent context", () => {
      const store = useProfileStore();
      store.setContexts([
        makeContext({ id: "ctx-1" }),
      ] as ContextProfileResponse[]);

      store.clearContextAvatar("ctx-999");

      expect(store.contexts).toHaveLength(1);
    });
  });

  describe("addIdentityName", () => {
    it("should push a name to the array", () => {
      const store = useProfileStore();
      const name: IdentityName = {
        id: "n1",
        identity_id: "u1",
        name_type: "preferred",
        name_value: { en: "Test" },
        is_primary: false,
        is_deprecated: false,
        visibility_level: "public",
        context_id: null,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      } as IdentityName;

      store.addIdentityName(name);

      expect(store.identityNames).toHaveLength(1);
      expect(store.identityNames[0].id).toBe("n1");
    });
  });

  describe("updateIdentityName", () => {
    it("should update matching name by id", () => {
      const store = useProfileStore();
      store.setIdentityNames([
        {
          id: "n1",
          identity_id: "u1",
          name_type: "preferred",
          name_value: { en: "Original" },
          is_primary: true,
          is_deprecated: false,
          visibility_level: "public",
          context_id: null,
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
        } as IdentityName,
      ]);

      store.updateIdentityName("n1", { name_value: { en: "Updated" } });

      expect(store.identityNames[0].name_value.en).toBe("Updated");
    });

    it("should do nothing for non-existent name", () => {
      const store = useProfileStore();
      store.setIdentityNames([
        {
          id: "n1",
          identity_id: "u1",
          name_type: "preferred",
          name_value: { en: "Original" },
          is_primary: true,
          is_deprecated: false,
          visibility_level: "public",
          context_id: null,
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
        } as IdentityName,
      ]);

      store.updateIdentityName("n999", { name_value: { en: "Nope" } });

      expect(store.identityNames[0].name_value.en).toBe("Original");
    });
  });

  describe("setLoading and setError", () => {
    it("should set loading state", () => {
      const store = useProfileStore();
      store.setLoading(true);
      expect(store.isLoading).toBe(true);
      store.setLoading(false);
      expect(store.isLoading).toBe(false);
    });

    it("should set error state", () => {
      const store = useProfileStore();
      store.setError("Something failed");
      expect(store.error).toBe("Something failed");
      store.setError(null);
      expect(store.error).toBeNull();
    });
  });
});
