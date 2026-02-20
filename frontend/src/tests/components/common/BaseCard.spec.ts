/**
 * Unit tests for BaseCard component.
 *
 * Tests verify default slot, header/footer slot rendering,
 * and noPadding prop behavior.
 */

import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import BaseCard from "@/components/common/BaseCard.vue";

describe("BaseCard", () => {
  it("should render default slot content", () => {
    const wrapper = mount(BaseCard, {
      slots: { default: "Card body content" },
    });

    expect(wrapper.find(".card-body").text()).toBe("Card body content");
  });

  it("should render header slot when provided", () => {
    const wrapper = mount(BaseCard, {
      slots: {
        header: "Card Header",
        default: "Body",
      },
    });

    expect(wrapper.find(".card-header").exists()).toBe(true);
    expect(wrapper.find(".card-header").text()).toBe("Card Header");
  });

  it("should not render header when slot is empty", () => {
    const wrapper = mount(BaseCard, {
      slots: { default: "Body" },
    });

    expect(wrapper.find(".card-header").exists()).toBe(false);
  });

  it("should render footer slot when provided", () => {
    const wrapper = mount(BaseCard, {
      slots: {
        default: "Body",
        footer: "Card Footer",
      },
    });

    expect(wrapper.find(".card-footer").exists()).toBe(true);
    expect(wrapper.find(".card-footer").text()).toBe("Card Footer");
  });

  it("should not render footer when slot is empty", () => {
    const wrapper = mount(BaseCard, {
      slots: { default: "Body" },
    });

    expect(wrapper.find(".card-footer").exists()).toBe(false);
  });

  it("should apply p-0 class when noPadding is true", () => {
    const wrapper = mount(BaseCard, {
      props: { noPadding: true },
      slots: { default: "Body" },
    });

    expect(wrapper.find(".card-body").classes()).toContain("p-0");
  });

  it("should not apply p-0 class by default", () => {
    const wrapper = mount(BaseCard, {
      slots: { default: "Body" },
    });

    expect(wrapper.find(".card-body").classes()).not.toContain("p-0");
  });
});
