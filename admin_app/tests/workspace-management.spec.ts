import { test, expect, type Page } from "@playwright/test";
import { makeUser, mockAuth, mockBackend } from "./helpers/mockApi";

/**
 * /workspace-management against a mocked backend and a fake login
 * (see helpers/mockApi.ts). Needs the dev server on :3000.
 */

const USERS = [
  makeUser(1, "test-admin", "admin"),
  makeUser(2, "amina", "read_only"),
  makeUser(3, "brian", "admin"),
];

async function openWorkspace(
  page: Page,
  { role = "admin" as "admin" | "read_only", users = USERS } = {},
) {
  await mockAuth(page, { role });
  const api = await mockBackend(page, { users });
  await page.goto("/workspace-management");
  return api;
}

test.describe("workspace management", () => {
  test("lists users with no MUI on the page", async ({ page }) => {
    await openWorkspace(page);

    await expect(
      page.getByRole("heading", { name: "Test workspace", level: 1 }),
    ).toBeVisible();
    const list = page.getByRole("list").filter({ hasText: "amina" });
    // The current admin is always first
    await expect(list.getByRole("listitem").first()).toContainText("test-admin");
    await expect(list.getByRole("listitem").first()).toContainText("(You)");
    await expect(list.getByRole("listitem")).toHaveCount(3);
    await expect(page.locator('[class*="Mui"]')).toHaveCount(0);
    await page.screenshot({ path: "test-results/workspace.png", fullPage: true });
  });

  test("read-only users see access denied", async ({ page }) => {
    await openWorkspace(page, { role: "read_only" });
    await expect(page.getByText("Access denied")).toBeVisible();
  });

  test("creates a user and shows their recovery codes once", async ({ page }) => {
    const api = await openWorkspace(page);
    await page.getByRole("button", { name: "Create new user" }).click();

    const dialog = page.getByRole("dialog", { name: "Create a user" });
    await dialog.getByLabel("Username").fill("chidi");
    await dialog.getByLabel("Password", { exact: true }).fill("secret-1");
    await dialog.getByLabel("Confirm password").fill("secret-1");
    await dialog.getByLabel("Role").selectOption("admin");
    await page.screenshot({ path: "test-results/workspace-create.png" });
    await dialog.getByRole("button", { name: "Create user" }).click();

    const codes = page.getByRole("dialog", { name: "User created" });
    await expect(codes.getByText("code-1111")).toBeVisible();
    await expect(page.getByText("User successfully created")).toBeVisible(); // toast
    expect(
      api.users.find((u) => u.username === "chidi")?.user_workspaces[0].user_role,
    ).toBe("admin");
    await codes.getByRole("button", { name: "Close" }).first().click();
    await expect(page.getByText("chidi")).toBeVisible();
  });

  test("password mismatch is caught before sending", async ({ page }) => {
    const api = await openWorkspace(page);
    await page.getByRole("button", { name: "Create new user" }).click();
    const dialog = page.getByRole("dialog", { name: "Create a user" });
    await dialog.getByLabel("Username").fill("chidi");
    await dialog.getByLabel("Password", { exact: true }).fill("one");
    await dialog.getByLabel("Confirm password").fill("two");
    await dialog.getByRole("button", { name: "Create user" }).click();
    await expect(dialog.getByText("Passwords do not match.")).toBeVisible();
    expect(api.requests.some((r) => r.method === "POST" && r.path === "/user/")).toBe(
      false,
    );
  });

  test("adds an existing user after verifying them", async ({ page }) => {
    const api = await openWorkspace(page);
    await page.getByRole("button", { name: "Add existing user" }).click();
    const dialog = page.getByRole("dialog", { name: "Add an existing user" });
    await expect(
      dialog.getByRole("button", { name: "Add to workspace" }),
    ).toBeDisabled();

    await dialog.getByLabel("Username").fill("outsider");
    await dialog.getByRole("button", { name: "Verify" }).click();
    await expect(dialog.getByText("Verified")).toBeVisible();
    await dialog.getByRole("button", { name: "Add to workspace" }).click();

    await expect(page.getByText("User successfully added")).toBeVisible();
    expect(
      api.requests.some((r) => r.path === "/user/add-existing-user-to-workspace"),
    ).toBe(true);
  });

  test("edits a user's role and removes a user", async ({ page }) => {
    const api = await openWorkspace(page);

    await page.getByText("amina").hover();
    await page.getByRole("button", { name: "Edit amina" }).click();
    const dialog = page.getByRole("dialog", { name: "Edit user" });
    await expect(dialog.getByLabel("Username")).toBeDisabled();
    await dialog.getByLabel("Role").selectOption("admin");
    await dialog.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText("User successfully edited")).toBeVisible();
    expect(
      api.users.find((u) => u.username === "amina")?.user_workspaces[0].user_role,
    ).toBe("admin");

    await page.getByText("brian").hover();
    await page.getByRole("button", { name: "Remove brian from workspace" }).click();
    await page.getByRole("alertdialog").getByRole("button", { name: "Remove" }).click();
    await expect(page.getByText("User removed successfully")).toBeVisible();
    await expect(page.getByText("brian")).toHaveCount(0);
  });

  test("you can't remove the only admin", async ({ page }) => {
    await openWorkspace(page, {
      users: [makeUser(1, "test-admin", "admin"), makeUser(2, "amina")],
    });
    await page.getByText("test-admin").first().hover();
    await page
      .getByRole("button", { name: "Remove test-admin from workspace" })
      .click();
    await page.getByRole("alertdialog").getByRole("button", { name: "Remove" }).click();
    await expect(
      page.getByText("You cannot remove the only admin from the workspace"),
    ).toBeVisible();
  });

  test("rename dialog: Cancel doesn't submit, Save sends the new name", async ({
    page,
  }) => {
    const api = await openWorkspace(page);
    await page.getByRole("button", { name: "Rename workspace" }).click();
    const dialog = page.getByRole("dialog", { name: "Rename workspace" });
    await expect(dialog.getByLabel("Workspace name")).toHaveValue("Test workspace");

    await dialog.getByRole("button", { name: "Cancel" }).click();
    await expect(dialog).toBeHidden();
    expect(
      api.requests.some((r) => r.method === "PUT" && r.path === "/workspace/1"),
    ).toBe(false);

    await page.getByRole("button", { name: "Rename workspace" }).click();
    await dialog.getByLabel("Workspace name").fill("");
    await dialog.getByRole("button", { name: "Save" }).click();
    await expect(dialog.getByText("Please enter a workspace name")).toBeVisible();
    await dialog.getByLabel("Workspace name").fill("Clinic team");
    await dialog.getByRole("button", { name: "Save" }).click();
    await expect
      .poll(
        () =>
          api.requests.find((r) => r.method === "PUT" && r.path === "/workspace/1")
            ?.body,
      )
      .toEqual({ workspace_name: "Clinic team" });
  });
});
