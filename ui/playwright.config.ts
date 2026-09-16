import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright configuration for Benchmark-Tavily UI tests
 * Tests run against Docker container at http://localhost:8080
 */
export default defineConfig({
	testDir: "./tests",
	testMatch: "**/*.spec.ts",
	fullyParallel: true,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 1 : 0,
	workers: process.env.CI ? 1 : undefined,

	// Timeout settings
	timeout: 30 * 1000,
	expect: { timeout: 5 * 1000 },

	// Reporter configuration
	reporter: [["html"], ["list"], ["json", { outputFile: "test-results.json" }]],

	use: {
		// Base URL for the running Docker container (overridable for local
		// runs against a container mapped to a different host port)
		baseURL: process.env.PLAYWRIGHT_TEST_BASE_URL ?? "http://localhost:8080",

		// Navigation timeout
		navigationTimeout: 30 * 1000,

		// Screenshot and video on failure
		screenshot: "only-on-failure",
		video: "retain-on-failure",

		// Track all network activity
		trace: "on-first-retry",
	},

	projects: [
		{
			name: "chromium",
			use: {
				...devices["Desktop Chrome"],
				headless: process.env.HEADLESS !== "false",
			},
		},
	],

	// Global setup timeout
	globalTimeout: 5 * 60 * 1000,

	// Web server configuration (optional for local development)
	// Uncomment if running tests without Docker container
	// webServer: {
	//   command: 'pnpm dev',
	//   url: 'http://localhost:8080',
	//   reuseExistingServer: !process.env.CI,
	//   timeout: 120000,
	// },
});
