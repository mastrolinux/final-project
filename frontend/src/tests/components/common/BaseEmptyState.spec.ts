/**
 * Unit tests for BaseEmptyState component.
 *
 * Tests verify title, description, icon slot, and action slot rendering.
 */

import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import BaseEmptyState from "@/components/common/BaseEmptyState.vue";

describe("BaseEmptyState", () => {
  it("should render title", () => {
    const wrapper = mount(BaseEmptyState, {
      props: { title: "No items found" },
    });

    expect(wrapper.find(".empty-state-title").text()).toBe("No items found");
  });

  it("should render description when provided", () => {
    const wrapper = mount(BaseEmptyState, {
      props: { title: "Empty", description: "Try creating a new item." },
    });

    expect(wrapper.find(".empty-state-description").text()).toBe(
      "Try creating a new item.",
    );
  });

  it("should not render description when not provided", () => {
    const wrapper = mount(BaseEmptyState, {
      props: { title: "Empty" },
    });

    expect(wrapper.find(".empty-state-description").exists()).toBe(false);
  });

  it("should render icon slot when provided", () => {
    const wrapper = mount(BaseEmptyState, {
      props: { title: "Empty" },
      slots: { icon: '<svg class="test-icon" />' },
    });

    expect(wrapper.find(".empty-state-icon").exists()).toBe(true);
    expect(wrapper.find(".test-icon").exists()).toBe(true);
  });

  it("should not render icon container when no icon slot", () => {
    const wrapper = mount(BaseEmptyState, {
      props: { title: "Empty" },
    });

    expect(wrapper.find(".empty-state-icon").exists()).toBe(false);
  });

  it("should render action slot when provided", () => {
    const wrapper = mount(BaseEmptyState, {
      props: { title: "Empty" },
      slots: { action: "<button>Create</button>" },
    });

    expect(wrapper.find(".empty-state-action").exists()).toBe(true);
    expect(wrapper.find("button").text()).toBe("Create");
  });

  it("should not render action container when no action slot", () => {
    const wrapper = mount(BaseEmptyState, {
      props: { title: "Empty" },
    });

    expect(wrapper.find(".empty-state-action").exists()).toBe(false);
  });
});
