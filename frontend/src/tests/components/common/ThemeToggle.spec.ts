/**
 * Unit tests for ThemeToggle component.
 *
 * Tests verify icon rendering per theme, cycle behavior on click,
 * and integration with the UI store.
 */

import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import ThemeToggle from "@/components/common/ThemeToggle.vue";
import { useUiStore } from "@/stores/ui.store";

describe("ThemeToggle", () => {
  it("should render sun icon for light theme", () => {
    const store = useUiStore();
    store.setTheme("light");

    const wrapper = mount(ThemeToggle);

    // Sun icon has a circle element
    expect(wrapper.find("circle").exists()).toBe(true);
    expect(wrapper.attributes("title")).toContain("Light");
  });

  it("should render moon icon for dark theme", () => {
    const store = useUiStore();
    store.setTheme("dark");

    const wrapper = mount(ThemeToggle);

    // Moon icon has a path element but no circle
    expect(wrapper.find("path").exists()).toBe(true);
    expect(wrapper.find("circle").exists()).toBe(false);
    expect(wrapper.attributes("title")).toContain("Dark");
  });

  it("should render system icon for system theme", () => {
    const store = useUiStore();
    store.theme = "system";

    const wrapper = mount(ThemeToggle);

    // System icon has a rect element
    expect(wrapper.find("rect").exists()).toBe(true);
    expect(wrapper.attributes("title")).toContain("System");
  });

  it("should cycle theme on click: light -> dark -> system -> light", async () => {
    const store = useUiStore();
    store.setTheme("light");

    const wrapper = mount(ThemeToggle);

    await wrapper.trigger("click");
    expect(store.theme).toBe("dark");

    await wrapper.trigger("click");
    expect(store.theme).toBe("system");

    await wrapper.trigger("click");
    expect(store.theme).toBe("light");
  });

  it("should have accessible aria-label", () => {
    const store = useUiStore();
    store.setTheme("dark");

    const wrapper = mount(ThemeToggle);

    expect(wrapper.attributes("aria-label")).toContain("Dark");
    expect(wrapper.attributes("aria-label")).toContain("Click to cycle");
  });
});
