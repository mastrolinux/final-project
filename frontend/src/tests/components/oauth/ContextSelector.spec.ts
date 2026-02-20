/**
 * Unit tests for ContextSelector component.
 *
 * Tests verify context card rendering, selected state styling,
 * emit on click, override vs inherited display, and check icon visibility.
 */

import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import ContextSelector from "@/components/oauth/ContextSelector.vue";
import type { ContextProfileResponse } from "@/types";

// Stub heroicon
const iconStubs = {
  CheckIcon: { template: '<svg class="check-icon" />' },
};

const mockContexts: ContextProfileResponse[] = [
  {
    id: "ctx-1",
    context_name: "Work",
    context_type: "professional",
    display_name_override: "Dr. Sarah Chen",
    email_override: "sarah@work.com",
    phone_override: null,
    bio_override: null,
    visibility: "public",
    is_primary: true,
    valid_from: "2026-01-01",
    valid_to: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "ctx-2",
    context_name: "Social",
    context_type: "social",
    display_name_override: null,
    email_override: null,
    phone_override: null,
    bio_override: null,
    visibility: "private",
    is_primary: false,
    valid_from: "2026-01-01",
    valid_to: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
] as unknown as ContextProfileResponse[];

describe("ContextSelector", () => {
  const mountComponent = (props: Record<string, unknown> = {}) =>
    mount(ContextSelector, {
      props: { contexts: mockContexts, modelValue: null, ...props },
      global: { stubs: iconStubs },
    });

  it("should render a card for each context", () => {
    const wrapper = mountComponent();

    const cards = wrapper.findAll(".context-card");
    expect(cards).toHaveLength(2);
  });

  it("should display context name and type", () => {
    const wrapper = mountComponent();

    const cards = wrapper.findAll(".context-card");
    expect(cards[0].find(".context-name").text()).toBe("Work");
    expect(cards[0].find(".context-type").text()).toBe("professional");
    expect(cards[1].find(".context-name").text()).toBe("Social");
    expect(cards[1].find(".context-type").text()).toBe("social");
  });

  it("should show override values when present", () => {
    const wrapper = mountComponent();

    const details = wrapper.findAll(".context-card")[0].findAll(".detail");
    expect(details[0].text()).toBe("Dr. Sarah Chen");
    expect(details[1].text()).toBe("sarah@work.com");
  });

  it("should show inherited placeholders when overrides are null", () => {
    const wrapper = mountComponent();

    const details = wrapper.findAll(".context-card")[1].findAll(".detail");
    expect(details[0].text()).toBe("Inherited Name");
    expect(details[1].text()).toBe("Inherited Email");
  });

  it("should apply selected class to matching context", () => {
    const wrapper = mountComponent({ modelValue: "ctx-1" });

    const cards = wrapper.findAll(".context-card");
    expect(cards[0].classes()).toContain("selected");
    expect(cards[1].classes()).not.toContain("selected");
  });

  it("should show check icon only for selected context", () => {
    const wrapper = mountComponent({ modelValue: "ctx-2" });

    const cards = wrapper.findAll(".context-card");
    expect(cards[0].find(".check-icon").exists()).toBe(false);
    expect(cards[1].find(".check-icon").exists()).toBe(true);
  });

  it("should emit update:modelValue when card clicked", async () => {
    const wrapper = mountComponent();

    await wrapper.findAll(".context-card")[1].trigger("click");

    const emitted = wrapper.emitted("update:modelValue");
    expect(emitted).toBeTruthy();
    expect(emitted![0][0]).toBe("ctx-2");
  });

  it("should not show check icon when no context is selected", () => {
    const wrapper = mountComponent({ modelValue: null });

    expect(wrapper.findAll(".check-icon")).toHaveLength(0);
  });
});
