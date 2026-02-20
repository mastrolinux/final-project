/**
 * Unit tests for AvatarDisplay component.
 *
 * Tests verify image vs initials rendering, initial computation
 * from name prop, and size class application.
 */

import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import AvatarDisplay from "@/components/common/AvatarDisplay.vue";

describe("AvatarDisplay", () => {
  it("should render img when src is provided", () => {
    const wrapper = mount(AvatarDisplay, {
      props: { src: "/avatar.webp", name: "John Doe" },
    });

    const img = wrapper.find("img");
    expect(img.exists()).toBe(true);
    expect(img.attributes("src")).toBe("/avatar.webp");
    expect(img.attributes("alt")).toBe("John Doe avatar");
  });

  it("should render initials when src is null", () => {
    const wrapper = mount(AvatarDisplay, {
      props: { src: null, name: "John Doe" },
    });

    expect(wrapper.find("img").exists()).toBe(false);
    expect(wrapper.find(".avatar-display-initials").text()).toBe("JD");
  });

  it("should render initials when src is not provided", () => {
    const wrapper = mount(AvatarDisplay, {
      props: { name: "Sarah Chen" },
    });

    expect(wrapper.find(".avatar-display-initials").text()).toBe("SC");
  });

  it("should default to U for empty name", () => {
    const wrapper = mount(AvatarDisplay, {
      props: { name: "" },
    });

    expect(wrapper.find(".avatar-display-initials").text()).toBe("U");
  });

  it("should truncate initials to 2 characters", () => {
    const wrapper = mount(AvatarDisplay, {
      props: { name: "Juan Carlos Rivera Garcia" },
    });

    expect(wrapper.find(".avatar-display-initials").text()).toBe("JC");
  });

  it("should handle single-word name", () => {
    const wrapper = mount(AvatarDisplay, {
      props: { name: "Sukarno" },
    });

    expect(wrapper.find(".avatar-display-initials").text()).toBe("S");
  });

  it("should apply correct size class for sm", () => {
    const wrapper = mount(AvatarDisplay, {
      props: { size: "sm" },
    });

    expect(wrapper.find(".avatar-display").classes()).toContain(
      "avatar-display-sm",
    );
  });

  it("should apply correct size class for xl", () => {
    const wrapper = mount(AvatarDisplay, {
      props: { size: "xl" },
    });

    expect(wrapper.find(".avatar-display").classes()).toContain(
      "avatar-display-xl",
    );
  });

  it("should default to md size", () => {
    const wrapper = mount(AvatarDisplay);

    expect(wrapper.find(".avatar-display").classes()).toContain(
      "avatar-display-md",
    );
  });

  it("should set alt to Avatar when no name provided", () => {
    const wrapper = mount(AvatarDisplay, {
      props: { src: "/photo.webp" },
    });

    expect(wrapper.find("img").attributes("alt")).toBe("Avatar");
  });
});
