import { test, expect, type Page } from "@playwright/test";
import {
  makeUrgencyRule,
  mockAuth,
  mockBackend,
  type MockUrgencyRule,
} from "./helpers/mockApi";

/**
 * /urgency-rules, run against a mocked backend and a fake login
 * (see helpers/mockApi.ts). Needs the dev server on :3000.
 */

const RULES = [
  makeUrgencyRule(1, "Bleeding during pregnancy"),
  makeUrgencyRule(2, "Fever above 39 degrees"),
];

/** Open /urgency-rules and wait for the page heading. */
async function openRulesPage(
  page: Page,
  {
    rules = RULES,
    role = "admin" as "admin" | "read_only",
  }: { rules?: MockUrgencyRule[]; role?: "admin" | "read_only" } = {},
) {
  await mockAuth(page, { role });
  const api = await mockBackend(page, { urgencyRules: rules });
  await page.goto("/urgency-rules");
  await expect(
    page.getByRole("heading", { name: "Urgency detection", level: 1 }),
  ).toBeVisible();
  return api;
}

test.describe("urgency rules page", () => {
  test("empty state matches the design and has no MUI", async ({ page }) => {
    await openRulesPage(page, { rules: [] });

    await expect(page.getByText("No urgency rules yet")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Create your first rule" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "How urgency detection works" }),
    ).toBeVisible();
    // Nothing to test without rules
    await expect(page.getByRole("button", { name: "Test rules" })).toBeDisabled();
    await expect(page.locator('[class*="Mui"]')).toHaveCount(0);

    await page.screenshot({
      path: "test-results/urgency-rules-empty.png",
      fullPage: true,
    });
  });

  test("lists rules with their last-updated time", async ({ page }) => {
    await openRulesPage(page);

    await expect(page.getByText("Bleeding during pregnancy")).toBeVisible();
    await expect(page.getByText("Fever above 39 degrees")).toBeVisible();
    await expect(page.getByText(/Last updated:/)).toHaveCount(2);
    await expect(page.locator('[class*="Mui"]')).toHaveCount(0);

    await page.screenshot({
      path: "test-results/urgency-rules-list.png",
      fullPage: true,
    });
  });

  test("creates a rule from the empty state with Enter", async ({ page }) => {
    const api = await openRulesPage(page, { rules: [] });

    await page.getByRole("button", { name: "Create your first rule" }).click();
    const input = page.getByRole("textbox", { name: "Rule 1" });
    await expect(input).toBeFocused();
    await input.fill("Severe headache");
    await input.press("Enter");

    await expect(page.getByText("Severe headache")).toBeVisible();
    await expect(page.getByText(/Last updated:/)).toBeVisible();
    expect(api.urgencyRules.map((r) => r.urgency_rule_text)).toEqual([
      "Severe headache",
    ]);
  });

  test("Escape discards a new unsaved rule", async ({ page }) => {
    const api = await openRulesPage(page);

    await page.getByRole("button", { name: "New rule" }).click();
    const input = page.getByRole("textbox", { name: "Rule 3" });
    await input.fill("Never saved");
    await input.press("Escape");

    await expect(input).toHaveCount(0);
    await expect(page.getByText("#3")).toHaveCount(0);
    expect(api.urgencyRules).toHaveLength(2);
  });

  test("edits a rule with the save button and cancels on blur", async ({ page }) => {
    const api = await openRulesPage(page);

    // Edit via the hover action, save with the send button
    await page.getByText("Fever above 39 degrees").hover();
    await page.getByRole("button", { name: "Edit rule 2" }).click();
    const input = page.getByRole("textbox", { name: "Rule 2" });
    await input.fill("Fever above 40 degrees");
    await page.getByRole("button", { name: "Save rule" }).click();
    await expect(page.getByText("Fever above 40 degrees")).toBeVisible();
    expect(api.urgencyRules[1].urgency_rule_text).toBe("Fever above 40 degrees");

    // Double-click to edit, then click away: the change is dropped
    await page.getByText("Bleeding during pregnancy").dblclick();
    const input1 = page.getByRole("textbox", { name: "Rule 1" });
    await input1.fill("Changed but not saved");
    await page.getByRole("heading", { name: "Urgency detection", level: 1 }).click();
    await expect(page.getByText("Bleeding during pregnancy")).toBeVisible();
    expect(api.urgencyRules[0].urgency_rule_text).toBe("Bleeding during pregnancy");
  });

  test("deletes a rule", async ({ page }) => {
    const api = await openRulesPage(page);

    await page.getByText("Bleeding during pregnancy").hover();
    await page.getByRole("button", { name: "Delete rule 1" }).click();

    await expect(page.getByText("Bleeding during pregnancy")).toHaveCount(0);
    expect(api.urgencyRules.map((r) => r.urgency_rule_id)).toEqual([2]);
  });

  test("shows an error toast when saving fails", async ({ page }) => {
    await openRulesPage(page);
    // Override the mocked POST with a server error
    await page.route("**/urgency-rules/", (route) =>
      route.request().method() === "POST"
        ? route.fulfill({
            status: 500,
            headers: { "Access-Control-Allow-Origin": "*" },
            body: JSON.stringify({ detail: "boom" }),
          })
        : route.fallback(),
    );

    await page.getByRole("button", { name: "New rule" }).click();
    const input = page.getByRole("textbox", { name: "Rule 3" });
    await input.fill("Will fail");
    await input.press("Enter");

    await expect(page.locator('[data-slot="toast"]')).toBeVisible();
  });

  test("read-only users can't add or edit rules", async ({ page }) => {
    await openRulesPage(page, { role: "read_only" });

    await expect(page.getByRole("button", { name: "New rule" })).toBeDisabled();
    await page.getByText("Bleeding during pregnancy").hover();
    await expect(page.getByRole("button", { name: "Edit rule 1" })).toHaveCount(0);
  });

  test("test panel classifies a message", async ({ page }) => {
    await openRulesPage(page);

    await page.getByRole("button", { name: "Test rules" }).click();
    await expect(
      page.getByRole("heading", { name: "Test Urgency Detection" }),
    ).toBeVisible();
    await expect(page.getByText("Test your rules")).toBeVisible();

    const question = page.getByRole("textbox", { name: "Question" });
    await question.fill("There is bleeding");
    await question.press("Enter");
    await expect(page.getByText("Urgent", { exact: true })).toBeVisible();
    await expect(page.getByText("Matched Rule", { exact: true })).toBeVisible();

    await question.fill("All good");
    await question.press("Enter");
    await expect(page.getByText("Not urgent")).toBeVisible();

    // Raw response dialog
    await page.getByRole("button", { name: "<json>" }).click();
    await expect(page.getByRole("dialog")).toContainText('"is_urgent": false');

    await page.screenshot({
      path: "test-results/urgency-rules-test-panel.png",
      fullPage: true,
    });
  });
});
