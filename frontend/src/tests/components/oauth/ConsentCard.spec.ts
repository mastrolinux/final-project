/**
 * Unit tests for ConsentCard component.
 *
 * Tests verify client name/id display, scope badges, granted date,
 * context binding, expiry display, and revoke button emission.
 */

import { describe, it, expect, vi } from "vitest";
import { mount } from "@vue/test-utils";
import ConsentCard from "@/components/oauth/ConsentCard.vue";
import type { OAuthConsent } from "@/types";

// Mock vue-i18n
vi.mock("vue-i18n", () => ({
  useI18n: () => ({
    t: (key: string) => key,
    locale: { value: "en" },
  }),
}));

// Stub heroicon and child components
const stubs = {
  TrashIcon: { template: '<svg class="trash-icon" />' },
};

const baseConsent: OAuthConsent = {
  client_id: "client-abc-123",
  client_name: "Test Application",
  granted_scopes: ["openid", "profile:read:basic", "contexts:legal:read"],
  granted_at: "2026-01-15T10:00:00Z",
  expires_at: null,
  context_profile_id: null,
  consent_method: "explicit",
} as OAuthConsent;

describe("ConsentCard", () => {
  const mountCard = (props: Record<string, unknown> = {}) =>
    mount(ConsentCard, {
      props: { consent: baseConsent, ...props },
      global: { stubs },
    });

  it("should display client name", () => {
    const wrapper = mountCard();

    expect(wrapper.find(".consent-client-name").text()).toBe(
      "Test Application",
    );
  });

  it("should display client id", () => {
    const wrapper = mountCard();

    expect(wrapper.find(".consent-client-id").text()).toBe("client-abc-123");
  });

  it("should render scope badges", () => {
    const wrapper = mountCard();

    const badges = wrapper.findAll(".scope-badges .badge");
    expect(badges).toHaveLength(3);
    expect(badges[0].text()).toBe("openid");
    expect(badges[1].text()).toBe("profile:read:basic");
    expect(badges[2].text()).toBe("contexts:legal:read");
  });

  it("should display granted date", () => {
    const wrapper = mountCard();

    expect(wrapper.text()).toContain("oauth.grantedOn");
    // Formatted date should contain Jan 2026
    expect(wrapper.text()).toContain("Jan");
  });

  it("should display context profile id when bound", () => {
    const consentWithContext = {
      ...baseConsent,
      context_profile_id: "ctx-work-456",
    };

    const wrapper = mountCard({ consent: consentWithContext });

    expect(wrapper.text()).toContain("oauth.boundToContext");
    expect(wrapper.text()).toContain("ctx-work-456");
  });

  it("should not display context binding when null", () => {
    const wrapper = mountCard();

    expect(wrapper.text()).not.toContain("oauth.boundToContext");
  });

  it("should display expiry date when present", () => {
    const consentWithExpiry = {
      ...baseConsent,
      expires_at: "2027-01-15T10:00:00Z",
    };

    const wrapper = mountCard({ consent: consentWithExpiry });

    expect(wrapper.text()).toContain("oauth.expiresOn");
  });

  it("should not display expiry when null", () => {
    const wrapper = mountCard();

    expect(wrapper.text()).not.toContain("oauth.expiresOn");
  });

  it("should emit revoke event on button click", async () => {
    const wrapper = mountCard();

    await wrapper.find(".consent-actions button").trigger("click");

    const emitted = wrapper.emitted("revoke");
    expect(emitted).toBeTruthy();
    expect(emitted![0][0]).toEqual(baseConsent);
  });
});
