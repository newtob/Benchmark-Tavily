import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // e2e/ holds Playwright specs, run via `just e2e`/`just e2e-full` — not
    // Vitest. Vitest's default include glob would otherwise also match
    // e2e/*.spec.ts and fail trying to run them as Vitest tests.
    exclude: ["**/node_modules/**", "**/.git/**", "e2e/**", "apps/*/build/**"],
  },
});
