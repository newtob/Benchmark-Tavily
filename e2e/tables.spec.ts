import { expect, test } from "@playwright/test";

// Asserts the summary tab (default) shows scaled averages and no raw
// per-page rows, and the pages tab shows the full detail table.
// See specs/tavily-benchmark-app.md §11.

test.describe("summary tab (default view)", () => {
  test("shows scaled averages and no per-page rows", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByTestId("summary-panel")).toBeVisible();
    await expect(page.getByTestId("web-content-table")).not.toBeVisible();

    for (const testId of [
      "summary-claude-search",
      "summary-tavily-extract",
      "summary-tinyfish-fetch",
    ]) {
      const card = page.getByTestId(testId);
      await expect(card).toBeVisible();
      const text = (await card.textContent()) ?? "";
      expect(text).toMatch(/\d+\s*tok/);
      expect(text).toMatch(/\$\d/);
    }

    // The headline question is answered: exactly one method is flagged.
    await expect(page.getByTestId("most-efficient")).toHaveCount(1);

    // The page explains what the numbers represent.
    await expect(page.getByText(/1000 pages/i)).toBeVisible();
  });
});

test.describe("pages tab", () => {
  test("reveals the detail table with method columns and rows", async ({
    page,
  }) => {
    await page.goto("/");
    await page.getByTestId("tab-searches").click();

    await expect(page.getByTestId("summary-panel")).not.toBeVisible();

    await expect(page.getByTestId("web-content-table")).toBeVisible();
    for (const col of [
      "col-claude-search",
      "col-tavily-extract",
      "col-tinyfish-fetch",
    ]) {
      await expect(page.getByTestId(col)).toBeVisible();
    }

    const rows = page.getByTestId("web-content-row");
    await expect(rows.first()).toBeVisible();
    expect(await rows.count()).toBeGreaterThanOrEqual(9);
    const firstRowText = (await rows.first().textContent()) ?? "";
    expect(firstRowText).toMatch(/\d+\s*tok/);
    expect(firstRowText).toMatch(/\$\d/);
  });
});
