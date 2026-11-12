import { test, expect, type Page } from "@playwright/test";

import type { AuthenticationDetails } from "@/client";
import { SESSION_COOKIE } from "@/utils/sessionCookie";
import { makeContent, mockAuth, mockBackend } from "./helpers/mockApi";

/**
 * Access tokens are short-lived; src/lib/api/session.ts swaps the refresh
 * token for a new pair (POST /refresh) just before one expires. These run
 * against the mocked backend (helpers/mockApi.ts). Tokens are placeholders.
 */

/** Seed a session whose access token expires in 5 seconds. */
async function seedExpiringSession(page: Page) {
  await mockAuth(page);
  await page.addInitScript(() => {
    window.localStorage.setItem("token", "[OLD_TOKEN]");
    window.localStorage.setItem("refreshToken", "[REFRESH_TOKEN]");
    window.localStorage.setItem("tokenExpiresAt", String(Date.now() + 5_000));
  });
}

const refreshed: AuthenticationDetails = {
  access_level: "fullaccess",
  access_token: "[NEW_TOKEN]",
  expires_in: 1800,
  refresh_token: "[NEW_REFRESH_TOKEN]",
  token_type: "bearer",
  user_role: "admin",
  username: "test-admin",
  workspace_name: "Test workspace",
};

test.describe("session refresh", () => {
  test("refreshes an expiring token once, then calls the API with the new one", async ({
    page,
  }) => {
    await seedExpiringSession(page);
    await mockBackend(page, {
      contents: [makeContent(1, { content_title: "Antenatal" })],
    });

    // Registered after mockBackend, so these win for /refresh.
    const refreshBodies: unknown[] = [];
    await page.route("**/bff/refresh", async (route) => {
      refreshBodies.push(route.request().postDataJSON());
      await route.fulfill({ json: refreshed });
    });
    const contentAuth = page.waitForRequest(
      (r) =>
        new URL(r.url()).pathname === "/bff/content/" && r.method() === "GET",
    );

    await page.goto("/content");

    expect((await contentAuth).headers()["authorization"]).toBe(
      "Bearer [NEW_TOKEN]",
    );
    await expect(page.getByText("Antenatal")).toBeVisible();
    // Several queries start at once, but a refresh token works only once.
    expect(refreshBodies).toEqual([{ refresh_token: "[REFRESH_TOKEN]" }]);
    expect(
      await page.evaluate(() => localStorage.getItem("refreshToken")),
    ).toBe("[NEW_REFRESH_TOKEN]");
  });

  test("a refused refresh token sends the user to /login", async ({ page }) => {
    await seedExpiringSession(page);
    await mockBackend(page);
    await page.route("**/bff/refresh", (route) =>
      route.fulfill({ status: 401, json: { detail: "Invalid refresh token" } }),
    );

    await page.goto("/content");

    await expect(page).toHaveURL(/\/login\?sourcePage=%2Fcontent$/);
    // The signed-in cookie is gone, so the proxy now keeps protected pages
    // behind /login. (localStorage can't be checked here: mockAuth's init
    // script re-seeds it on every navigation, including this one.)
    const cookies = await page.context().cookies();
    expect(cookies.find((c) => c.name === SESSION_COOKIE)).toBeUndefined();
  });
});
