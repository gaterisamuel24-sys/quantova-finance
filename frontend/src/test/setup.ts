import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// Reset the DOM and any stubbed globals (like fetch) after every test,
// so tests can never leak state into each other.
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
