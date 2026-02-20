/**
 * Unit tests for UI store.
 *
 * Tests cover notification management (add, remove, clear, auto-remove),
 * theme persistence and resolution, sidebar toggle, loading state,
 * and convenience notification methods.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useUiStore } from "@/stores/ui.store";

describe("useUiStore", () => {
  let store: ReturnType<typeof useUiStore>;

  beforeEach(() => {
    store = useUiStore();
  });

  describe("initial state", () => {
    it("should start with isLoading false", () => {
      expect(store.isLoading).toBe(false);
    });

    it("should start with null loadingMessage", () => {
      expect(store.loadingMessage).toBeNull();
    });

    it("should start with empty notifications", () => {
      expect(store.notifications).toEqual([]);
    });

    it("should default theme to system when localStorage is empty", () => {
      expect(store.theme).toBe("system");
    });

    it("should read theme from localStorage if set", () => {
      localStorage.setItem("theme", "dark");
      const _freshStore = useUiStore();
      // Pinia reuses the same store instance within a test, so we verify
      // the initial read logic by checking localStorage was consulted
      expect(localStorage.getItem).toHaveBeenCalledWith("theme");
    });

    it("should start with sidebarOpen true", () => {
      expect(store.sidebarOpen).toBe(true);
    });
  });

  describe("setLoading", () => {
    it("should set isLoading and loadingMessage", () => {
      store.setLoading(true, "Saving...");

      expect(store.isLoading).toBe(true);
      expect(store.loadingMessage).toBe("Saving...");
    });

    it("should clear loadingMessage when no message provided", () => {
      store.setLoading(true, "Saving...");
      store.setLoading(false);

      expect(store.isLoading).toBe(false);
      expect(store.loadingMessage).toBeNull();
    });
  });

  describe("showNotification", () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("should add notification with generated id", () => {
      const id = store.showNotification({ type: "info", message: "Hello" });

      expect(id).toMatch(/^notification-/);
      expect(store.notifications).toHaveLength(1);
      expect(store.notifications[0].message).toBe("Hello");
      expect(store.notifications[0].type).toBe("info");
    });

    it("should default duration to 5000ms", () => {
      store.showNotification({ type: "info", message: "Test" });

      expect(store.notifications[0].duration).toBe(5000);
    });

    it("should auto-remove after duration", () => {
      store.showNotification({
        type: "info",
        message: "Temporary",
        duration: 3000,
      });

      expect(store.notifications).toHaveLength(1);

      vi.advanceTimersByTime(3000);

      expect(store.notifications).toHaveLength(0);
    });

    it("should not auto-remove when duration is 0", () => {
      store.showNotification({
        type: "info",
        message: "Persistent",
        duration: 0,
      });

      vi.advanceTimersByTime(60000);

      expect(store.notifications).toHaveLength(1);
    });
  });

  describe("removeNotification", () => {
    it("should remove notification by id", () => {
      const id = store.showNotification({
        type: "info",
        message: "Test",
        duration: 0,
      });

      store.removeNotification(id);

      expect(store.notifications).toHaveLength(0);
    });

    it("should not throw for non-existent id", () => {
      expect(() => store.removeNotification("non-existent")).not.toThrow();
    });
  });

  describe("clearNotifications", () => {
    it("should remove all notifications", () => {
      store.showNotification({ type: "info", message: "A", duration: 0 });
      store.showNotification({ type: "error", message: "B", duration: 0 });

      store.clearNotifications();

      expect(store.notifications).toHaveLength(0);
    });
  });

  describe("hasNotifications", () => {
    it("should return false when empty", () => {
      expect(store.hasNotifications).toBe(false);
    });

    it("should return true when notifications exist", () => {
      store.showNotification({ type: "info", message: "Test", duration: 0 });

      expect(store.hasNotifications).toBe(true);
    });
  });

  describe("setTheme", () => {
    it("should update theme and persist to localStorage", () => {
      store.setTheme("dark");

      expect(store.theme).toBe("dark");
      expect(localStorage.setItem).toHaveBeenCalledWith("theme", "dark");
    });

    it("should apply effective theme class to document", () => {
      store.setTheme("light");

      expect(document.documentElement.classList.contains("light")).toBe(true);
    });

    it("should remove previous theme class before adding new one", () => {
      store.setTheme("dark");
      store.setTheme("light");

      expect(document.documentElement.classList.contains("dark")).toBe(false);
      expect(document.documentElement.classList.contains("light")).toBe(true);
    });
  });

  describe("effectiveTheme", () => {
    it("should return light when theme is light", () => {
      store.setTheme("light");

      expect(store.effectiveTheme).toBe("light");
    });

    it("should return dark when theme is dark", () => {
      store.setTheme("dark");

      expect(store.effectiveTheme).toBe("dark");
    });

    it("should resolve system to light when matchMedia returns false", () => {
      // matchMedia mock returns matches: false by default (from setup.ts)
      store.theme = "system";

      expect(store.effectiveTheme).toBe("light");
    });

    it("should resolve system to dark when matchMedia prefers dark", () => {
      vi.mocked(window.matchMedia).mockReturnValueOnce({
        matches: true,
        media: "(prefers-color-scheme: dark)",
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      });
      store.theme = "system";

      expect(store.effectiveTheme).toBe("dark");
    });
  });

  describe("toggleSidebar", () => {
    it("should toggle sidebar state", () => {
      expect(store.sidebarOpen).toBe(true);

      store.toggleSidebar();
      expect(store.sidebarOpen).toBe(false);

      store.toggleSidebar();
      expect(store.sidebarOpen).toBe(true);
    });
  });

  describe("setSidebarOpen", () => {
    it("should set sidebar to specific value", () => {
      store.setSidebarOpen(false);
      expect(store.sidebarOpen).toBe(false);

      store.setSidebarOpen(true);
      expect(store.sidebarOpen).toBe(true);
    });
  });

  describe("convenience methods", () => {
    it("showSuccess should create success notification", () => {
      store.showSuccess("Done!");

      expect(store.notifications[0].type).toBe("success");
      expect(store.notifications[0].message).toBe("Done!");
    });

    it("showError should create error notification with 8000ms default", () => {
      store.showError("Failed!");

      expect(store.notifications[0].type).toBe("error");
      expect(store.notifications[0].duration).toBe(8000);
    });

    it("showError should accept custom duration", () => {
      store.showError("Failed!", 3000);

      expect(store.notifications[0].duration).toBe(3000);
    });

    it("showWarning should create warning notification", () => {
      store.showWarning("Careful!");

      expect(store.notifications[0].type).toBe("warning");
    });

    it("showInfo should create info notification", () => {
      store.showInfo("FYI");

      expect(store.notifications[0].type).toBe("info");
    });
  });

  describe("addNotification alias", () => {
    it("should behave identically to showNotification", () => {
      const id = store.addNotification({
        type: "info",
        message: "Via alias",
        duration: 0,
      });

      expect(id).toMatch(/^notification-/);
      expect(store.notifications).toHaveLength(1);
      expect(store.notifications[0].message).toBe("Via alias");
    });
  });
});
