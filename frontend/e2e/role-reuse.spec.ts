import { expect, test } from "@playwright/test";

test("a role title with an overlapping keyword reuses the existing role", async ({ request }) => {
  const first = await request.post("http://localhost:8000/sessions", {
    data: { role_title: "Software Engineer" },
  });
  expect(first.ok()).toBeTruthy();
  const firstBody = await first.json();

  const second = await request.post("http://localhost:8000/sessions", {
    data: { role_title: "Software Developer" },
  });
  expect(second.ok()).toBeTruthy();
  const secondBody = await second.json();

  expect(secondBody.role_id).toBe(firstBody.role_id);
});
