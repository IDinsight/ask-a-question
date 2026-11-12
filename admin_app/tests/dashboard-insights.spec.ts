import { test, expect, type Page } from "@playwright/test";
import {
  makeInsights,
  makePerformanceRow,
  mockAuth,
  mockBackend,
} from "./helpers/mockApi";

/**
 * /dashboard?page=content-performance and ?page=query-topics against a mocked
 * backend (see helpers/mockApi.ts). Needs the dev server on :3000.
 */

async function open(
  page: Page,
  slug: string,
  heading: string,
  data: Parameters<typeof mockBackend>[1] = {},
) {
  await mockAuth(page);
  const api = await mockBackend(page, data);
  await page.goto(`/dashboard?page=${slug}`);
  await expect(page.getByRole("heading", { name: heading, level: 1 })).toBeVisible();
  return api;
}

const ROWS = Array.from({ length: 7 }, (_, i) =>
  makePerformanceRow(
    i + 1,
    `Card ${i + 1}`,
    [i, i + 1, i + 2, i, i + 3, i + 1, i + 2],
    {
      up: i,
      down: 7 - i,
    },
  ),
);

test.describe("content performance", () => {
  test("empty state matches the design and offers a longer range", async ({ page }) => {
    const api = await open(page, "content-performance", "Content performance");

    await expect(
      page.getByRole("heading", { name: "Top content, last 7 days" }),
    ).toBeVisible();
    await expect(page.getByText("No content sent in this period")).toBeVisible();
    await expect(page.getByText("No content performance yet")).toBeVisible();
    await expect(page.getByRole("button", { name: "Previous" })).toBeDisabled();
    await expect(page.locator('[class*="Mui"]')).toHaveCount(0);
    await page.screenshot({
      path: "test-results/performance-empty.png",
      fullPage: true,
    });

    await page.getByRole("button", { name: "Show last month" }).click();
    await expect(page.getByRole("button", { name: "Last month" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await expect
      .poll(() => api.requests.some((r) => r.path === "/dashboard/performance/month"))
      .toBe(true);
  });

  test("lists, sorts, searches and pages through content", async ({ page }) => {
    await open(page, "content-performance", "Content performance", {
      performance: ROWS,
    });

    // Default sort: daily average sent, highest first → Card 7 on top
    const firstTitle = page.locator("tbody tr").first().getByRole("button");
    await expect(firstTitle).toHaveText("Card 7");
    await expect(page.getByText("Page 1 of 2")).toBeVisible();
    await expect(page.locator(".recharts-line")).toHaveCount(5 + 5); // 5 chart lines + 5 sparklines

    // Sort by upvotes, then flip to ascending
    await page.getByRole("button", { name: "Upvotes" }).click();
    await expect(firstTitle).toHaveText("Card 7");
    await page.getByRole("button", { name: "Upvotes" }).click();
    await expect(firstTitle).toHaveText("Card 1");
    await expect(page.getByText(/Ordered by upvotes, lowest first/)).toBeVisible();

    await page.getByRole("button", { name: "Next", exact: true }).click();
    await expect(page.getByText("Page 2 of 2")).toBeVisible();

    // Search resets to page 1
    await page.getByRole("searchbox", { name: "Search content titles" }).fill("Card 3");
    await expect(page.getByText("Page 1 of 1")).toBeVisible();
    await expect(page.locator("tbody tr")).toHaveCount(1);
    await page.getByRole("searchbox", { name: "Search content titles" }).fill("zzz");
    await expect(page.getByText("No content titles match “zzz”.")).toBeVisible();
  });

  test("clicking a row opens the details drawer", async ({ page }) => {
    await open(page, "content-performance", "Content performance", {
      performance: ROWS,
    });

    await page.getByRole("button", { name: "Card 7" }).click();
    const drawer = page.getByRole("dialog");
    await expect(drawer.getByRole("heading", { name: "Card 7" })).toBeVisible();
    await expect(drawer.getByText("Summary for Card 7.")).toBeVisible();
    await expect(drawer.getByText("When should I go to the clinic?")).toBeVisible();
    await page.waitForTimeout(1600); // chart animation
    await page.screenshot({ path: "test-results/performance-drawer.png" });
  });
});

test.describe("query topics", () => {
  test("empty state matches the design", async ({ page }) => {
    await open(page, "query-topics", "Query topics");

    await expect(page.getByText("No topics yet.")).toBeVisible();
    await expect(page.getByText("Last run: Never")).toBeVisible();
    await expect(page.getByText("Discover what people ask about")).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Connect your chatbot" }),
    ).toHaveAttribute("href", "/integrations");
    await expect(
      page.getByRole("button", { name: "Expand topic visualization" }),
    ).toBeVisible();
    await expect(page.locator('[class*="Mui"]')).toHaveCount(0);
    await page.screenshot({ path: "test-results/topics-empty.png", fullPage: true });
  });

  test("run discovery polls until topics arrive, then topics can be browsed", async ({
    page,
  }) => {
    await open(page, "query-topics", "Query topics", {
      insightsAfterRefresh: makeInsights([
        {
          id: 1,
          name: "Clinic visits",
          queries: ["When is the clinic open?", "Do I need an appointment?"],
        },
        { id: 2, name: "Nutrition", queries: ["What should I eat?"] },
      ]),
    });

    await page.getByRole("button", { name: "Run discovery" }).click();
    await expect(page.getByText("Started topic discovery.")).toBeVisible(); // toast
    // Polling runs every 3s
    await expect(page.getByRole("button", { name: /Clinic visits/ })).toBeVisible({
      timeout: 10000,
    });
    await expect(page.getByRole("button", { name: /Clinic visits/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await expect(page.getByText("When is the clinic open?")).toBeVisible();
    await expect(page.getByRole("button", { name: "Rerun discovery" })).toBeVisible();

    await page.getByRole("button", { name: /Nutrition/ }).click();
    await expect(page.getByText("What should I eat?")).toBeVisible();
    await expect(page.getByText("People ask about nutrition.")).toBeVisible();
    await page.screenshot({ path: "test-results/topics-data.png", fullPage: true });
  });
});
