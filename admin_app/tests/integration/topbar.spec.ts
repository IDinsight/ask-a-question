import { test, expect } from "@playwright/test";
import { mockAuth, mockBackend } from "./helpers/mockApi";

/**
 * The top bar (breadcrumb + search button) on every signed-in page.
 * Runs against a mocked backend; needs the dev server on :3000.
 */

const PAGES: { url: string; trail: string[] }[] = [
  { url: "/content", trail: ["Question answering"] },
  { url: "/content/edit", trail: ["Question answering", "Add content"] },
  { url: "/urgency-rules", trail: ["Urgency detection"] },
  { url: "/dashboard?page=overview", trail: ["Overview"] },
  {
    url: "/dashboard?page=content-performance",
    trail: ["Content performance"],
  },
  { url: "/dashboard?page=query-topics", trail: ["Query topics"] },
  { url: "/integrations", trail: ["Integrations"] },
  { url: "/workspace-management", trail: ["Manage workspace"] },
];

test.describe("top bar", () => {
  for (const { url, trail } of PAGES) {
    test(`breadcrumb on ${url}`, async ({ page }) => {
      await mockAuth(page);
      await mockBackend(page);
      await page.goto(url);

      const crumb = page.getByRole("navigation", { name: "breadcrumb" });
      await expect(crumb.getByRole("listitem").first()).toHaveText(
        "Test workspace",
      );
      // The last crumb is the current page
      await expect(crumb.locator('[aria-current="page"]')).toHaveText(
        trail[trail.length - 1],
      );
      if (trail.length > 1) {
        await expect(
          crumb.getByRole("link", { name: trail[0] }),
        ).toHaveAttribute("href", "/content");
      }
      await expect(
        page.getByRole("button", { name: "Search or jump to a page" }),
      ).toBeVisible();
    });
  }

  test("screenshots: desktop and phone", async ({ page }) => {
    await mockAuth(page);
    await mockBackend(page);
    await page.goto("/dashboard?page=query-topics");
    await expect(
      page.getByRole("navigation", { name: "breadcrumb" }),
    ).toBeVisible();
    await page.screenshot({ path: "test-results/topbar-desktop.png" });

    await page.setViewportSize({ width: 390, height: 844 });
    await expect(
      page.getByRole("button", { name: "Toggle Sidebar" }),
    ).toBeVisible();
    await page.screenshot({ path: "test-results/topbar-phone.png" });
  });
});
