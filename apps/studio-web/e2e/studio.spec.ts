import { test, expect } from "@playwright/test";

/**
 * Requires SPWS_API pointing at a running studio-api with seeded meaning index.
 * Python pytest Playwright suite is the primary CI path; this is the D013 Node twin.
 */
test("five workspaces textual flow", async ({ page }) => {
  const api = process.env.SPWS_API || "http://127.0.0.1:8000";
  await page.addInitScript((url) => localStorage.setItem("SPWS_API", url), api);
  await page.goto("/");

  const poem =
    "The wind along the meadow path\n" +
    "Turns every blade of grass to gold,\n" +
    "And in the quiet after rain\n" +
    "The earth remembers stories old.";

  await page.fill("#draft", poem);
  await page.click('[data-testid="btn-load"]');
  await expect(page.locator('[data-testid="sum-import"]')).toContainText("Loaded");

  await page.click('[data-tab="analysis"]');
  await page.click('[data-testid="btn-analyse"]');
  await expect(page.locator('[data-testid="sum-analysis"]')).toContainText("problem", {
    timeout: 60000,
  });

  await page.click('[data-tab="plan"]');
  await page.click('[data-testid="btn-plan-create"]');
  await expect(page.locator('[data-testid="sum-plan"]')).toContainText("Plan id");
  await page.click('[data-testid="btn-plan-confirm"]');
  await expect(page.locator('[data-testid="sum-plan"]')).toContainText("Confirmed: true");

  await page.click('[data-tab="candidates"]');
  await page.click('[data-testid="btn-propose"]');
  await page.waitForSelector('[data-testid="btn-accept-0"]', { timeout: 90000 });
  await page.click('[data-testid="btn-accept-0"]');
  await expect(page.locator('[data-testid="sum-candidates"]')).toContainText("accept", {
    timeout: 60000,
  });

  await page.click('[data-tab="export"]');
  await page.click('[data-testid="btn-refresh-export"]');
  const exportText = await page.locator('[data-testid="sum-export"]').innerText();
  expect(exportText.trim().length).toBeGreaterThan(0);
});
