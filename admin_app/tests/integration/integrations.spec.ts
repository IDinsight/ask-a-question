import { test, expect, type Page } from "@playwright/test";
import { mockAuth, mockBackend } from "./helpers/mockApi";

/**
 * /integrations against a mocked backend and a fake login
 * (see helpers/mockApi.ts). Needs the dev server on :3000.
 */

async function openIntegrations(
  page: Page,
  {
    role = "admin",
    workspace = {},
  }: {
    role?: "admin" | "read_only";
    workspace?: Parameters<typeof mockBackend>[1] extends infer T
      ? T extends { workspace?: infer W }
        ? W
        : never
      : never;
  } = {},
) {
  await mockAuth(page, { role });
  const api = await mockBackend(page, { workspace });
  await page.goto("/integrations");
  await expect(
    page.getByRole("heading", { name: "Integrations", level: 1 }),
  ).toBeVisible();
  return api;
}

test.describe("integrations page", () => {
  test("matches the design and has no MUI", async ({ page }) => {
    await openIntegrations(page);

    await expect(page.getByText("aD5KZ")).toBeVisible();
    await expect(page.getByText("Active", { exact: true })).toBeVisible();
    await expect(page.getByText("Last updated Nov 6, 2026 at 09:35")).toBeVisible();
    await expect(page.getByText("100 requests")).toBeVisible();
    for (const name of ["Typebot", "Turn", "Glific", "REST API"]) {
      await expect(
        page.getByRole("button", { name: `${name}: view setup guide` }),
      ).toBeVisible();
    }
    await expect(page.locator('[class*="Mui"]')).toHaveCount(0);
    // Every logo image should actually load
    await expect
      .poll(() =>
        page
          .locator("ul img")
          .evaluateAll((imgs) =>
            imgs.every(
              (img) =>
                (img as HTMLImageElement).complete &&
                (img as HTMLImageElement).naturalWidth > 0,
            ),
          ),
      )
      .toBe(true);
    await page.screenshot({ path: "test-results/integrations.png", fullPage: true });
  });

  test("regenerating asks first, then shows the new key once", async ({ page }) => {
    const api = await openIntegrations(page);

    await page.getByRole("button", { name: "Regenerate key" }).click();
    const confirm = page.getByRole("alertdialog");
    await expect(confirm).toContainText("aD5KZ");

    // Cancel does nothing
    await confirm.getByRole("button", { name: "Cancel" }).click();
    await expect(confirm).toBeHidden();
    expect(api.requests.some((r) => r.path === "/workspace/rotate-key")).toBe(false);

    await page.getByRole("button", { name: "Regenerate key" }).click();
    await page
      .getByRole("alertdialog")
      .getByRole("button", { name: "Generate new key" })
      .click();

    const dialog = page.getByRole("dialog", { name: "Save your new key" });
    await expect(dialog.getByRole("textbox", { name: "New API key" })).toHaveValue(
      /^NEWKEY/,
    );
    await page.context().grantPermissions(["clipboard-read", "clipboard-write"]);
    await dialog.getByRole("button", { name: "Copy" }).click();
    await expect(dialog.getByRole("button", { name: "Copied" })).toBeVisible();
    await dialog.getByRole("button", { name: "Close" }).first().click();

    // Card refetches and shows the new key's start
    await expect(page.getByText("NEWKE")).toBeVisible();
  });

  test("a workspace without a key gets a Generate button", async ({ page }) => {
    await openIntegrations(page, {
      workspace: {
        api_key_first_characters: null,
        api_key_updated_datetime_utc: null,
        api_daily_quota: null,
      },
    });
    await expect(page.getByText("doesn’t have an API key yet")).toBeVisible();
    await expect(page.getByText("No daily limit")).toBeVisible();
    await page.getByRole("button", { name: "Generate key" }).click();
    await expect(page.getByRole("dialog", { name: "Save your new key" })).toBeVisible();
  });

  test("read-only users don't see the key card", async ({ page }) => {
    await openIntegrations(page, { role: "read_only" });
    await expect(page.getByRole("heading", { name: "Daily API limit" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Workspace API key" })).toHaveCount(
      0,
    );
  });

  test("a connection card opens its setup guide", async ({ page }) => {
    await openIntegrations(page);
    await page.getByRole("button", { name: "Turn: view setup guide" }).click();
    const dialog = page.getByRole("dialog", { name: /Turn setup guide/ });
    await expect(
      dialog.getByRole("link", { name: "Open Turn Playbook" }),
    ).toHaveAttribute("href", /whatsapp\.turn\.io/);
    await page.waitForTimeout(400); // dialog open animation
    await page.screenshot({ path: "test-results/integrations-turn.png" });
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
  });
});
