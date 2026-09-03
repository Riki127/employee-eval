import { expect, test } from "@playwright/test";

test("answering a completed session returns 409", async ({ page, request }) => {
  await page.goto("/");
  await page.getByTestId("role-title-input").fill("Software Engineer");

  const [startResponse] = await Promise.all([
    page.waitForResponse((res) => res.url().endsWith("/sessions") && res.request().method() === "POST"),
    page.getByTestId("start-button").click(),
  ]);
  const { session_id: sessionId } = await startResponse.json();

  for (let i = 0; i < 5; i++) {
    await expect(page.getByTestId("question-text")).toBeVisible();
    await page.getByTestId("answer-input").fill("A detailed answer with specific, concrete examples of my work.");
    await page.getByTestId("submit-answer-button").click();
  }
  await expect(page.getByTestId("verdict")).toBeVisible();

  const res = await request.post(`http://localhost:8000/sessions/${sessionId}/answer`, {
    data: { answer: "late answer" },
  });
  expect(res.status()).toBe(409);
});
