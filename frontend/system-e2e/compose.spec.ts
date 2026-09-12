import { expect, test } from "@playwright/test";

const experimentName = "Compose browser smoke";

test("runs a live resilience experiment through the Compose stack", async ({
  page,
}) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "Resilience, measured." }),
  ).toBeVisible();
  await expect(page.getByText("Connected")).toBeVisible();

  const response = await page.request.get("/");
  expect(response.headers()["x-content-type-options"]).toBe("nosniff");
  expect(response.headers()["x-frame-options"]).toBe("DENY");
  expect(response.headers()["referrer-policy"]).toBe("no-referrer");

  await page.getByRole("link", { name: "New experiment" }).first().click();
  await page.getByLabel("Experiment name").fill(experimentName);
  await page.getByLabel("Requests per phase").fill("5");
  await page.getByLabel("Interval between requests").fill("250");
  await page.getByRole("button", { name: "Run resilience experiment" }).click();

  await expect(page).toHaveURL(/\/experiments\/[0-9a-f-]+\/live$/);
  await expect(page.getByText("Live request feed")).toBeVisible();
  await expect(page.getByText("Live", { exact: true })).toBeVisible();

  await expect(page).toHaveURL(/\/experiments\/[0-9a-f-]+$/, {
    timeout: 30_000,
  });
  await expect(
    page.getByRole("heading", { name: experimentName }),
  ).toBeVisible();
  await expect(page.getByText("Contract passed")).toBeVisible();

  await page.getByRole("link", { name: "Back to overview" }).click();
  await expect(page.getByText(experimentName).first()).toBeVisible();
});
