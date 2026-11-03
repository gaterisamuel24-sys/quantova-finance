/// <reference types="vitest/config" />
import { defineConfig, loadEnv, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

import { buildContentSecurityPolicy } from "./src/lib/csp.js";

/**
 * Production builds get the Content Security Policy as a <meta> tag in index.html, and as
 * dist/content-security-policy.txt for the web server to send as a header (Phase 8; a
 * header can also forbid framing, which a meta tag cannot). The dev server is left alone:
 * hot reloading needs an inline script that the strict policy would block.
 */
function contentSecurityPolicy(apiBaseUrl: string): Plugin {
  const policy = buildContentSecurityPolicy(apiBaseUrl);
  return {
    name: "quantova-content-security-policy",
    apply: "build",
    transformIndexHtml: () => [
      {
        tag: "meta",
        attrs: { "http-equiv": "Content-Security-Policy", content: policy },
        injectTo: "head-prepend",
      },
    ],
    generateBundle() {
      this.emitFile({
        type: "asset",
        fileName: "content-security-policy.txt",
        source: `${policy}; frame-ancestors 'none'\n`,
      });
    },
  };
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "VITE_");
  return {
    plugins: [react(), tailwindcss(), contentSecurityPolicy(env.VITE_API_BASE_URL ?? "")],
    server: {
      port: 5173,
      strictPort: true,
      proxy: {
        // Forward /api requests to the FastAPI dev server.
        "/api": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      },
    },
    test: {
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
    },
  };
});
