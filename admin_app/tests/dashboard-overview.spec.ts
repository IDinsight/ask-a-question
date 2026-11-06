import { test, expect, type Page } from "@playwright/test";
import { makeContent, makeOverview, mockAuth, mockBackend } from "./helpers/mockApi";

/**
 * /dashboard?page=overview, run against a mocked backend and a fake admin
 * login (see helpers/mockApi.ts). Needs the dev server on :3000.
 */

async function openOverview(page: Page, data: Parameters<typeof mockBackend>[1] = {}) {
  await mockAuth(page);
  const api = await mockBackend(page, data);
  await page.goto("/dashboard?page=overview");
  await expect(page.getByRole("heading", { name: "Overview", level: 1 })).toBeVisible();
  return api;
}

test.describe("dashboard overview", () => {
  test("empty workspace shows the setup checklist and empty charts", async ({ page }) => {
    await openOverview(page);

    await expect(page.getByRole("heading", { name: "Get set up" })).toBeVisible();
    await expect(page.getByText("1 of 4")).toBeVisible();
    await expect(page.getByRole("link", { name: "View integrations" })).toHaveAttribute(
      "href",
      "/integrations",
    );
    await expect(page.getByText("No change data yet")).toHaveCount(5);
    await expect(page.getByText("No queries in this period")).toBeVisible();
    await expect(page.getByText(/Busy hours and days show up here/)).toBeVisible();
    await expect(page.getByText("Nothing has been sent yet.")).toBeVisible();
    await expect(page.locator('[class*="Mui"]')).toHaveCount(0);

    await page.screenshot({ path: "test-results/overview-empty.png", fullPage: true });
    await page
      .locator("section", { has: page.getByRole("heading", { name: "Queries over time" }) })
      .locator("..")
      .screenshot({ path: "test-results/overview-empty-charts.png" });
  });

  test("checklist marks content as done once content exists", async ({ page }) => {
    await openOverview(page, { contents: [makeContent(1)] });
    await expect(page.getByText("2 of 4")).toBeVisible();
  });

  test("with data: stat cards, chart, heatmap and table, no checklist", async ({ page }) => {
    await openOverview(page, {
      overview: makeOverview({
        queriesPerDay: 6,
        topContent: [
          {
            title: "Antenatal visits",
            query_count: 31,
            positive_votes: 8,
            negative_votes: 2,
            last_updated: "2026-10-20T10:00:00Z",
          },
          {
            title: "[DELETED] Old card",
            query_count: 4,
            positive_votes: 0,
            negative_votes: 0,
            last_updated: "2026-09-01T10:00:00Z",
          },
        ],
      }),
    });

    await expect(page.getByRole("heading", { name: "Get set up" })).toHaveCount(0);
    await expect(page.getByText("42", { exact: true })).toBeVisible();
    await expect(page.getByText("+25.0%")).toBeVisible();
    await expect(page.getByText("No queries in this period")).toHaveCount(0);
    // Recharts draws one rect per bar segment: 7 days × 3 series
    await expect(page.locator(".recharts-bar-rectangle")).toHaveCount(21);
    await expect(page.getByRole("img", { name: /80% upvotes, 20% downvotes/ })).toBeVisible();
    await expect(page.getByText("[DELETED] Old card")).toBeVisible();

    await page.waitForTimeout(1600); // let Recharts finish its grow-in animation
    await page.screenshot({ path: "test-results/overview-data.png", fullPage: true });
    await page
      .locator("section", { has: page.getByRole("heading", { name: "Queries over time" }) })
      .locator("..")
      .screenshot({ path: "test-results/overview-data-charts.png" });
    await page
      .locator("section", { has: page.getByRole("heading", { name: "Most sent content" }) })
      .screenshot({ path: "test-results/overview-data-table.png" });
  });

  test("time range buttons refetch with the chosen period", async ({ page }) => {
    const api = await openOverview(page);
    const last7 = page.getByRole("button", { name: "Last 7 days" });
    await expect(last7).toHaveAttribute("aria-pressed", "true");

    await page.getByRole("button", { name: "Last month" }).click();
    await expect(page.getByRole("button", { name: "Last month" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await expect
      .poll(() => api.requests.some((r) => r.path === "/dashboard/overview/month"))
      .toBe(true);
  });

  test("Custom opens the date dialog and applies a range", async ({ page }) => {
    const api = await openOverview(page);

    await page.getByRole("button", { name: "Custom", exact: true }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByText("Custom date range")).toBeVisible();
    await expect(dialog.getByRole("button", { name: "Apply" })).toBeDisabled();

    // Pick the 3rd and 10th of the first visible month
    const month = dialog.locator("table").first();
    await month.getByRole("button", { name: /\b3(rd)?\b/ }).first().click();
    await month.getByRole("button", { name: /\b10(th)?\b/ }).first().click();
    await expect(dialog.getByText("(8 days)")).toBeVisible();
    await dialog.getByRole("button", { name: "Apply" }).click();

    await expect(dialog).toBeHidden();
    await expect(page.getByRole("button", { name: "Custom", exact: true })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await expect(page.getByRole("button", { name: "Edit custom date range" })).toBeVisible();
    await expect
      .poll(() => api.requests.some((r) => r.path === "/dashboard/overview/custom"))
      .toBe(true);
  });
});
