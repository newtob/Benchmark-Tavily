import { expect, test } from "@playwright/test";

/**
 * Smoke tests for Benchmark-Tavily application
 * Tests UI rendering, data loading, tab switching, and model selection
 */

test.describe("Benchmark-Tavily UI", () => {
	test("renders benchmark table with data", async ({ page }) => {
		// Navigate to the home page
		await page.goto("/");

		// Wait for the comparison group to be visible
		const comparisonGroups = page.locator("[data-testid=comparison-group]");
		await comparisonGroups.first().waitFor({ state: "visible" });

		// Assert that at least one comparison group exists
		const count = await comparisonGroups.count();
		expect(count).toBeGreaterThan(0);
	});

	test("shows 'Most efficient' badge on winner card", async ({ page }) => {
		// Navigate to the home page
		await page.goto("/");

		// Wait for the winner badge to be visible
		const winnerBadge = page.locator("[data-testid=winner-badge]");
		await winnerBadge.first().waitFor({ state: "visible", timeout: 10000 });

		// Assert that the badge contains the expected text
		await expect(winnerBadge.first()).toContainText("MOST EFFICIENT");
	});

	test("switches between Summary and Searches tabs", async ({ page }) => {
		// Navigate to the home page
		await page.goto("/");

		// Wait for the Summary tab to be visible and active
		const summaryTab = page.locator("[data-testid=tab-summary]");
		await summaryTab.waitFor({ state: "visible" });

		// Verify Summary tab is active (aria-selected="true")
		await expect(summaryTab).toHaveAttribute("aria-selected", "true");

		// Click on Searches tab
		const searchesTab = page.locator("[data-testid=tab-searches]");
		await searchesTab.click();

		// Wait for the Searches panel placeholder to be visible
		const searchesPlaceholder = page.locator("[data-testid=searches-placeholder]");
		await searchesPlaceholder.waitFor({ state: "visible", timeout: 10000 });

		// Verify Searches tab is now active
		await expect(searchesTab).toHaveAttribute("aria-selected", "true");

		// Verify Summary tab is no longer active
		await expect(summaryTab).toHaveAttribute("aria-selected", "false");
	});

	test("includes 'Tavily' in rendered content", async ({ page }) => {
		// Navigate to the home page
		await page.goto("/");

		// This is a fully client-rendered SPA (adapter-static with a SPA
		// fallback, no prerendering) - use an auto-retrying assertion so we
		// don't race the initial hydration/fetch.
		await expect(page.locator("body")).toContainText("Tavily", { timeout: 10000 });
	});

	test("loads data from API", async ({ page }) => {
		// Navigate to the home page
		await page.goto("/");

		// Wait for comparison groups to be rendered
		const comparisonGroups = page.locator("[data-testid=comparison-group]");
		await comparisonGroups.first().waitFor({ state: "visible" });

		// Verify at least one comparison group exists
		const groupCount = await comparisonGroups.count();
		expect(groupCount).toBeGreaterThan(0);

		// Verify benchmark items (cards) are rendered
		const benchmarkItems = page.locator("[data-testid=benchmark-item]");
		const itemCount = await benchmarkItems.count();
		expect(itemCount).toBeGreaterThan(0);

		// Verify costs are displayed (look for $ symbol or numeric values)
		const firstItem = benchmarkItems.first();
		const itemText = await firstItem.textContent();
		expect(itemText).toMatch(/\$\d+\.\d{2}|[0-9,]+\s*tok/);
	});

	test("model selector works", async ({ page }) => {
		// Navigate to the home page
		await page.goto("/");

		// Wait for initial data to load
		const benchmarkItems = page.locator("[data-testid=benchmark-item]");
		await benchmarkItems.first().waitFor({ state: "visible" });

		// The model selector is a native <select> - use selectOption, not click+text
		// (native <select> dropdowns are OS-rendered and not reliably clickable in headless mode).
		const modelSelector = page.locator("[data-testid=model-selector]");
		await expect(modelSelector).toBeVisible();

		await modelSelector.selectOption({ label: "Haiku 4.5" });

		// Verify new data is rendered after the model change
		await benchmarkItems.first().waitFor({ state: "visible" });
		const updatedFirstItemText = await benchmarkItems.first().textContent();
		expect(updatedFirstItemText).toBeTruthy();
	});

	test("page loads without errors", async ({ page }) => {
		// Collect any console errors
		const errors: string[] = [];
		page.on("console", (msg) => {
			if (msg.type() === "error") {
				errors.push(msg.text());
			}
		});

		// Navigate to the home page
		await page.goto("/");

		// Wait for the page to stabilize
		await page.waitForLoadState("networkidle");

		// Assert no critical errors were logged
		const criticalErrors = errors.filter(
			(err) => !err.includes("favicon") && !err.includes("source-map"),
		);
		expect(criticalErrors).toEqual([]);
	});

	test("page renders without 404 errors", async ({ page }) => {
		// Track failed requests
		const failedRequests: string[] = [];
		page.on("response", (response) => {
			if (response.status() >= 400 && !response.url().includes("favicon")) {
				failedRequests.push(`${response.status()}: ${response.url()}`);
			}
		});

		// Navigate to the home page
		await page.goto("/");

		// Wait for page to fully load
		await page.waitForLoadState("networkidle");

		// Assert no critical 404/500 errors (favicon 404s are acceptable)
		const criticalFailures = failedRequests.filter((req) => !req.includes("favicon"));
		expect(criticalFailures).toEqual([]);
	});
});
