/**
 * Unit tests for BaseSkeleton component.
 *
 * Tests verify variant classes, custom dimensions via style,
 * rounded modifier, and aria-hidden attribute.
 */

import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import BaseSkeleton from "@/components/common/BaseSkeleton.vue";

describe("BaseSkeleton", () => {
  it("should apply default variant class (text)", () => {
    const wrapper = mount(BaseSkeleton);

    expect(wrapper.classes()).toContain("skeleton");
    expect(wrapper.classes()).toContain("skeleton-text");
  });

  it("should apply avatar variant class", () => {
    const wrapper = mount(BaseSkeleton, {
      props: { variant: "avatar" },
    });

    expect(wrapper.classes()).toContain("skeleton-avatar");
  });

  it("should apply card variant class", () => {
    const wrapper = mount(BaseSkeleton, {
      props: { variant: "card" },
    });

    expect(wrapper.classes()).toContain("skeleton-card");
  });

  it("should apply custom width and height via style", () => {
    const wrapper = mount(BaseSkeleton, {
      props: { width: "200px", height: "40px" },
    });

    const style = wrapper.attributes("style");
    expect(style).toContain("width: 200px");
    expect(style).toContain("height: 40px");
  });

  it("should apply rounded class when rounded prop is true", () => {
    const wrapper = mount(BaseSkeleton, {
      props: { rounded: true },
    });

    expect(wrapper.classes()).toContain("skeleton-rounded");
  });

  it("should not apply rounded class by default", () => {
    const wrapper = mount(BaseSkeleton);

    expect(wrapper.classes()).not.toContain("skeleton-rounded");
  });

  it("should have aria-hidden attribute", () => {
    const wrapper = mount(BaseSkeleton);

    expect(wrapper.attributes("aria-hidden")).toBe("true");
  });

  it("should render as a div element", () => {
    const wrapper = mount(BaseSkeleton);

    expect(wrapper.element.tagName).toBe("DIV");
  });
});
