import { test, expect, type Page } from "@playwright/test";
import { makeContent, makeTag, mockAuth, mockBackend } from "./helpers/mockApi";

/**
 * /content and /content/edit, run against a mocked backend and a fake
 * admin login (see helpers/mockApi.ts). Needs the dev server on :3000;
 * playwright.config.ts reuses one that's already running.
 */

const TAGS = [makeTag(1, "Maternal health"), makeTag(2, "Nutrition")];

const CONTENTS = [
  makeContent(1, { content_title: "Antenatal visits", content_tags: [1] }),
  makeContent(2, {
    content_title: "Breastfeeding basics",
    content_tags: [1, 2],
  }),
  makeContent(3, {
    content_title: "Healthy diet in pregnancy",
    content_tags: [2],
  }),
];

/** Open /content as an admin and wait for the cards to load. */
async function openContentPage(
  page: Page,
  data = { tags: TAGS, contents: CONTENTS },
) {
  await mockAuth(page);
  const api = await mockBackend(page, data);
  await page.goto("/content");
  await expect(
    page.getByRole("heading", { name: "Question Answering" }),
  ).toBeVisible();
  return api;
}

test.describe("content page", () => {
  test("renders with shadcn components and no MUI", async ({ page }) => {
    await openContentPage(page);

    await expect(
      page.getByRole("button", { name: /Open content #1/ }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Open content #3/ }),
    ).toBeVisible();

    // MUI components carry "Mui*" class names; none should be on the page.
    await expect(page.locator('[class*="Mui"]')).toHaveCount(0);

    await page.screenshot({
      path: "test-results/content-page.png",
      fullPage: true,
    });
  });

  test("New is a link and the arrow opens the import menu", async ({
    page,
  }) => {
    await openContentPage(page);

    const group = page.getByRole("group", { name: "Add content" });
    await expect(group).toBeVisible();

    // "New" goes to the editor.
    await expect(group.getByRole("button", { name: "New" })).toHaveAttribute(
      "href",
      "/content/edit",
    );

    // The arrow opens a menu with the two import options.
    const arrow = group.getByRole("button", {
      name: "Import or generate cards",
    });
    await arrow.click();
    const csvItem = page.getByRole("menuitem", {
      name: "Import cards from CSV",
    });
    await expect(csvItem).toBeVisible();
    await expect(
      page.getByRole("menuitem", { name: "Generate cards from PDF" }),
    ).toBeVisible();

    // toBeVisible() passes even for a popup stuck invisible at (0, 0), which
    // is what happened when the trigger lost its ref on React 18. Check the
    // menu actually sits just below the arrow and isn't transparent.
    const menu = page.getByRole("menu");
    await expect(menu.locator("..")).not.toHaveCSS("opacity", "0");
    const arrowBox = (await arrow.boundingBox())!;
    const menuBox = (await menu.boundingBox())!;
    expect(menuBox.y).toBeGreaterThanOrEqual(arrowBox.y + arrowBox.height);
    expect(menuBox.y).toBeLessThan(arrowBox.y + arrowBox.height + 20);
    // Right-aligned with the arrow (align="end").
    expect(
      Math.abs(menuBox.x + menuBox.width - (arrowBox.x + arrowBox.width)),
    ).toBeLessThan(2);

    await page.screenshot({
      path: "test-results/add-content-menu.png",
      animations: "disabled",
    });

    // Choosing CSV opens the import dialog.
    await csvItem.click();
    await expect(
      page.getByRole("dialog", { name: "Import new content from CSV" }),
    ).toBeVisible();
  });

  test("clicking New opens the add content page", async ({ page }) => {
    await openContentPage(page);
    await page
      .getByRole("group", { name: "Add content" })
      .getByRole("button", { name: "New" })
      .click();
    await expect(page).toHaveURL(/\/content\/edit$/);
    await expect(
      page.getByRole("heading", { name: "Add content" }),
    ).toBeVisible();
  });

  test("the PDF option opens the PDF dialog", async ({ page }) => {
    await openContentPage(page);
    await page
      .getByRole("button", { name: "Import or generate cards" })
      .click();
    await page
      .getByRole("menuitem", { name: "Generate cards from PDF" })
      .click();
    await expect(
      page.getByRole("dialog", { name: "Generate new content from PDF" }),
    ).toBeVisible();
  });

  test("shows an empty state when there is no content", async ({ page }) => {
    await openContentPage(page, { tags: [], contents: [] });
    await expect(page.getByText("No content yet")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Add content" }),
    ).toHaveAttribute("href", "/content/edit");
  });

  test("search with no matches shows the no-match empty state", async ({
    page,
  }) => {
    await openContentPage(page);
    await page
      .getByRole("searchbox", { name: "Search content" })
      .fill("zzz no match");
    await expect(page.getByText("No matching content")).toBeVisible();
  });

  test("tag filter narrows the cards", async ({ page }) => {
    await openContentPage(page);

    await page.getByRole("combobox", { name: "Filter by tag" }).click();
    await page.getByRole("option", { name: "Maternal health" }).click();
    await page.keyboard.press("Escape");

    await expect(
      page.getByRole("button", { name: /Open content #1/ }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Open content #2/ }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Open content #3/ }),
    ).toHaveCount(0);
  });

  test("bulk delete needs the word delete before it runs", async ({ page }) => {
    const api = await openContentPage(page);

    await page.getByRole("checkbox", { name: "Select content #1" }).click();
    await expect(page.getByText("1 selected")).toBeVisible();
    await page.getByRole("button", { name: "Delete", exact: true }).click();

    const dialog = page.getByRole("alertdialog", { name: "Confirm deletion" });
    const confirm = dialog.getByRole("button", { name: "Delete items" });
    await expect(confirm).toBeDisabled();

    await dialog.getByLabel(/Type delete to confirm/).fill("delete");
    await confirm.click();

    await expect(
      page.getByText("Successfully deleted 1 content"),
    ).toBeVisible();
    expect(api.requests).toContainEqual(
      // Deleting archives the content via PATCH.
      expect.objectContaining({ method: "PATCH", path: "/content/1" }),
    );
  });

  test("clicking a card opens it in a dialog", async ({ page }) => {
    await openContentPage(page);
    await page.getByRole("button", { name: /Open content #2/ }).click();
    const dialog = page.getByRole("dialog", { name: "Content #2" });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText("Breastfeeding basics")).toBeVisible();
  });
});

test.describe("edit content page", () => {
  test("creates a new tag from the tag picker", async ({ page }) => {
    await mockAuth(page);
    const api = await mockBackend(page, { tags: TAGS, contents: CONTENTS });
    await page.goto("/content/edit");

    const tagInput = page.getByRole("combobox", { name: "Tags (optional)" });
    await tagInput.click();
    await tagInput.fill("Vaccines");
    await page.getByRole("option", { name: 'Create "Vaccines"' }).click();

    // The new tag is saved to the API and shown as a chip.
    await expect
      .poll(() => api.tags.map((t) => t.tag_name))
      .toContain("Vaccines");
    await expect(
      page.locator('[data-slot="combobox-chip"]', { hasText: "Vaccines" }),
    ).toBeVisible();
  });

  test("the delete icon on a tag asks to delete it instead of selecting it", async ({
    page,
  }) => {
    await mockAuth(page);
    const api = await mockBackend(page, { tags: TAGS, contents: CONTENTS });
    await page.goto("/content/edit");

    await page.getByRole("combobox", { name: "Tags (optional)" }).click();
    await page.getByRole("button", { name: "Delete tag Nutrition" }).click();

    const dialog = page.getByRole("alertdialog", {
      name: 'Delete tag "Nutrition"?',
    });
    await expect(dialog).toBeVisible();
    // The tag must not have been added as a chip by the same click.
    await expect(
      page.locator('[data-slot="combobox-chip"]', { hasText: "Nutrition" }),
    ).toHaveCount(0);

    await dialog.getByRole("button", { name: "Delete" }).click();
    await expect
      .poll(() => api.tags.map((t) => t.tag_name))
      .not.toContain("Nutrition");
  });

  test("save stays disabled until something changes, then validates", async ({
    page,
  }) => {
    await mockAuth(page);
    await mockBackend(page, { tags: TAGS, contents: CONTENTS });
    await page.goto("/content/edit");

    const save = page.getByRole("button", { name: "Save" });
    await expect(save).toBeDisabled();

    // Title only: saving should flag the empty content field.
    await page.getByLabel("Title").fill("A new card");
    await save.click();
    await expect(page.getByText("Content should not be empty")).toBeVisible();
  });
});
