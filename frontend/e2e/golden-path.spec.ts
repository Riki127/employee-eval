import { expect, test } from "@playwright/test";

test("employee completes assessment and sees a verdict", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("role-title-input").fill("Software Engineer");
  await page.getByTestId("start-button").click();

  for (let i = 0; i < 5; i++) {
    await expect(page.getByTestId("question-text")).toBeVisible();
    await page
      .getByTestId("answer-input")
      .fill(
        "This is a detailed example answer describing a specific situation, the actions I took, and the outcome I achieved."
      );
    await page.getByTestId("submit-answer-button").click();
  }

  await expect(page.getByTestId("verdict")).toBeVisible();
  await expect(page.getByTestId("rationale")).toBeVisible();
  await expect(page.getByTestId("recommendation")).toBeVisible();
});
