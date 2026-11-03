import { cleanup, configure } from "@testing-library/react";
import { afterEach, vi } from "vitest";

import { tokenStore } from "../lib/api/token-store";

// findBy* queries wait up to 5 s (default 1 s). Passing tests still finish as soon as the
// element appears; this only prevents false failures on a busy machine or CI runner.
configure({ asyncUtilTimeout: 5000 });

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
