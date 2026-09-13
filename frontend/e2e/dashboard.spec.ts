import { expect, test } from "@playwright/test";

import { mkdir } from "node:fs/promises";

async function screenshot(page: import("@playwright/test").Page, name: string) {
  await mkdir("artifacts", { recursive: true });
  await page.screenshot({
    path: `artifacts/${name}.png`,
    fullPage: true,
    caret: "initial",
  });
}

test("dashboard shows persisted experiment history", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "Resilience, measured." }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Checkout resilience" }),
  ).toBeVisible();
  await expect(page.getByText("Connected")).toBeVisible();

  await screenshot(page, "overview");
});

test("runs an experiment and renders its persisted result", async ({
  page,
}) => {
  await page.goto("/experiments/new");

  await page.getByLabel("Experiment name").fill("Search API recovery");
  await page.getByRole("button", { name: "Run resilience experiment" }).click();

  await expect(page).toHaveURL(
    /\/experiments\/22222222-2222-4222-8222-222222222222\/live$/,
  );
  await expect(page.getByText("Live request feed")).toBeVisible();
  await expect(page.getByText("Fault applied")).toBeVisible();
  await expect(page.getByText("Live", { exact: true })).toBeVisible();
  await expect(page.getByText("200 · success").first()).toBeVisible();
  await screenshot(page, "live-experiment");

  await expect(page).toHaveURL(
    /\/experiments\/22222222-2222-4222-8222-222222222222$/,
  );
  await expect(
    page.getByRole("heading", { name: "Search API recovery" }),
  ).toBeVisible();
  await expect(page.getByText("Contract passed")).toBeVisible();

  await screenshot(page, "result");
});

test("experiment builder stays usable on a narrow viewport", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/experiments/new");

  await expect(
    page.getByRole("heading", {
      name: "Design the failure before it happens.",
    }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "Overview" })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Run resilience experiment" }),
  ).toBeVisible();

  await screenshot(page, "mobile-builder");
});
