import { expect, test } from "@playwright/test";

// Asserts the summary tab (default) shows scaled averages and no raw
// per-search rows, and the searches tab shows the full detail tables.
// See specs/tavily-benchmark-app.md §11.

test.describe("summary tab (default view)", () => {
  test("shows scaled averages and no per-search rows", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByTestId("summary-panel")).toBeVisible();
    await expect(page.getByTestId("tool-call-table")).not.toBeVisible();
    await expect(page.getByTestId("web-content-table")).not.toBeVisible();

    for (const testId of [
      "summary-raw-tool-call",
      "summary-mcp",
      "summary-claude-search",
      "summary-tavily-extract",
    ]) {
      const card = page.getByTestId(testId);
      await expect(card).toBeVisible();
      const text = (await card.textContent()) ?? "";
      expect(text).toMatch(/\d+\s*tok/);
      expect(text).toMatch(/\$\d/);
    }

    // The page explains what the numbers represent.
    await expect(page.getByText(/1000 searches/i)).toBeVisible();
  });
});

test.describe("searches tab", () => {
  test("reveals both detail tables with method columns and rows", async ({
    page,
  }) => {
    await page.goto("/");
    await page.getByTestId("tab-searches").click();

    await expect(page.getByTestId("summary-panel")).not.toBeVisible();

    const toolCallTable = page.getByTestId("tool-call-table");
    await expect(toolCallTable).toBeVisible();
    await expect(page.getByTestId("col-raw")).toBeVisible();
    await expect(page.getByTestId("col-mcp")).toBeVisible();

    const toolCallRows = page.getByTestId("tool-call-row");
    await expect(toolCallRows.first()).toBeVisible();
    expect(await toolCallRows.count()).toBeGreaterThan(0);
    const firstToolCallRowText =
      (await toolCallRows.first().textContent()) ?? "";
    expect(firstToolCallRowText).toMatch(/\d+\s*tok/);
    expect(firstToolCallRowText).toMatch(/\$\d/);

    const webContentTable = page.getByTestId("web-content-table");
    await expect(webContentTable).toBeVisible();
    await expect(page.getByTestId("col-claude-search")).toBeVisible();
    await expect(page.getByTestId("col-tavily-extract")).toBeVisible();

    const webContentRows = page.getByTestId("web-content-row");
    await expect(webContentRows.first()).toBeVisible();
    expect(await webContentRows.count()).toBeGreaterThan(0);
    const firstWebContentRowText =
      (await webContentRows.first().textContent()) ?? "";
    expect(firstWebContentRowText).toMatch(/\d+\s*tok/);
    expect(firstWebContentRowText).toMatch(/\$\d/);
  });
});
