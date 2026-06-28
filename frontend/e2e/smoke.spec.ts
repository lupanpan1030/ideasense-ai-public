import { expect, test, type Page } from "@playwright/test";

const assertNoHorizontalOverflow = async (page: Page) => {
  const metrics = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));

  expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.clientWidth + 1);
};

test.describe("public entry points", () => {
  test("loads the English marketing page and reaches login", async ({
    page,
    isMobile,
  }) => {
    await page.goto("/en");

    await expect(page).toHaveTitle(/IdeaSense AI/);
    await expect(
      page.getByRole("heading", { name: "Validate before you build." })
    ).toBeVisible();

    if (isMobile) {
      await page.goto("/en/login");
    } else {
      const loginLink = page.getByRole("link", { name: "Login" });
      await expect(loginLink).toBeVisible();
      await Promise.all([
        page.waitForURL(/\/(?:en\/)?login$/, { timeout: 15_000 }),
        loginLink.click(),
      ]);
    }

    await expect(page).toHaveURL(/\/(?:en\/)?login$/);
    await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
    await expect(page.getByLabel("Work email")).toBeVisible();
    await expect(
      page.getByRole("textbox", { name: "Password" })
    ).toBeVisible();
  });

  test("keeps critical public pages within the mobile viewport", async ({ page }) => {
    await page.goto("/en");
    await assertNoHorizontalOverflow(page);

    await page.goto("/en/login");
    await assertNoHorizontalOverflow(page);
    await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  });
});
