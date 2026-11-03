import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

import { tokenStore } from "../lib/api/token-store";

// jsdom does not implement matchMedia; provide a minimal "light system theme" stand-in.
if (!window.matchMedia) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }),
  });
}

// Reset the DOM, stubbed globals, storage and session after every test.
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
  tokenStore.clear();
  document.documentElement.className = "";
});
