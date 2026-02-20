/**
 * Unit tests for AppNotifications component.
 *
 * Tests verify rendering from UI store, notification type classes,
 * close button behavior, and empty state.
 */

import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import AppNotifications from "@/components/layout/AppNotifications.vue";
import { useUiStore } from "@/stores/ui.store";

describe("AppNotifications", () => {
  it("should render nothing when no notifications", () => {
    const wrapper = mount(AppNotifications);

    expect(wrapper.findAll(".notification")).toHaveLength(0);
  });

  it("should render notifications from UI store", () => {
    const store = useUiStore();
    store.showNotification({ type: "success", message: "Saved!", duration: 0 });
    store.showNotification({ type: "error", message: "Failed!", duration: 0 });

    const wrapper = mount(AppNotifications);

    const notifications = wrapper.findAll('[role="alert"]');
    expect(notifications).toHaveLength(2);
    expect(notifications[0].text()).toContain("Saved!");
    expect(notifications[1].text()).toContain("Failed!");
  });

  it("should apply correct class for notification type", () => {
    const store = useUiStore();
    store.showNotification({
      type: "warning",
      message: "Warning!",
      duration: 0,
    });

    const wrapper = mount(AppNotifications);

    const notification = wrapper.find('[role="alert"]');
    expect(notification.classes()).toContain("notification-warning");
  });

  it("should remove notification on close click", async () => {
    const store = useUiStore();
    store.showNotification({ type: "info", message: "Info", duration: 0 });

    const wrapper = mount(AppNotifications);

    expect(store.notifications).toHaveLength(1);

    await wrapper.find(".notification-close").trigger("click");

    expect(store.notifications).toHaveLength(0);
  });

  it("should have aria-live polite on container", () => {
    const wrapper = mount(AppNotifications);

    expect(
      wrapper.find(".notifications-container").attributes("aria-live"),
    ).toBe("polite");
  });
});
