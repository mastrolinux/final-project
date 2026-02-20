/**
 * Vitest setup file.
 * Configures global test utilities and mocks.
 */

import { config } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, vi } from "vitest";

// Create fresh Pinia instance for each test
beforeEach(() => {
  setActivePinia(createPinia());
});

// Mock matchMedia for components that use media queries
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: vi.fn((index: number) => Object.keys(store)[index] ?? null),
  };
})();

Object.defineProperty(window, "localStorage", {
  value: localStorageMock,
});

// Mock sessionStorage
const sessionStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: vi.fn((index: number) => Object.keys(store)[index] ?? null),
  };
})();

Object.defineProperty(window, "sessionStorage", {
  value: sessionStorageMock,
});

// Configure Vue Test Utils globally
config.global.stubs = {
  // Stub router-link and router-view by default
  RouterLink: {
    template: "<a><slot /></a>",
  },
  RouterView: {
    template: "<div><slot /></div>",
  },
};

// Clear all mocks after each test
beforeEach(() => {
  vi.clearAllMocks();
  localStorageMock.clear();
  sessionStorageMock.clear();
});
