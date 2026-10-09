import { expect, test } from "@playwright/test";

const password = "piste-ready-2026";

test("manual analysis journey", async ({ page, browser }) => {
  const email = `coach-${Date.now()}@example.com`;
  await page.goto("/register", { waitUntil: "networkidle" });
  await page.getByLabel("Name").fill("Camille Moreau");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByLabel("Organization").fill("Salle Lumiere");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
  await expect(page.getByRole("heading", { name: "The salle" })).toBeVisible();

  await page.goto("/clubs");
  await page.getByLabel("Club name").fill("Cercle d'escrime");
  await page.getByLabel("City").fill("Lyon");
  await page.getByRole("button", { name: "Create club" }).click();
  await expect(page.getByText("Cercle d'escrime")).toBeVisible();

  await page.goto("/athletes");
  await page.getByLabel("Name").fill("Left Fencer");
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await page.getByLabel("Name").fill("Right Fencer");
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.getByRole("link", { name: /Left Fencer/ })).toBeVisible();

  await page.goto("/bouts");
  await expect(page.getByRole("combobox", { name: "Left" }).locator("option", { hasText: "Right Fencer" }).first()).toBeAttached();
  await page.getByRole("combobox", { name: "Left", exact: true }).selectOption({ label: "Left Fencer" });
  await page.getByRole("combobox", { name: "Right", exact: true }).selectOption({ label: "Right Fencer" });
  await page.getByLabel("Date").fill("2026-10-08");
  await page.getByRole("button", { name: "Create", exact: true }).click();
  await expect(page.getByRole("link", { name: /Left Fencer/ })).toBeVisible();

  await page.goto("/videos/upload");
  await expect(page.getByLabel("Bout").locator("option")).toHaveCount(2);
  await page.getByLabel("Title").fill("Poule clip");
  await page.getByLabel("Athlete").selectOption({ label: "Left Fencer" });
  await page.getByLabel("Bout").selectOption({ index: 1 });
  await page.getByLabel("Video file").setInputFiles("/tmp/fi-media/sample.mp4");
  await page.getByRole("button", { name: "Upload and process" }).click();
  await expect(page.getByText("ready")).toBeVisible({ timeout: 60_000 });
  const videoUrl = page.url();

  await page.getByLabel("Actor").selectOption({ label: "Left Fencer" });
  await page.getByRole("button", { name: "Save validated annotation" }).click();
  await expect(page.getByText("attack · no_touch")).toBeVisible();
  await page.getByRole("button", { name: "Touch left" }).click();
  await expect(page.getByText("1").first()).toBeVisible();

  await page.goto("/performance");
  await page.getByRole("combobox").selectOption({ label: "Left Fencer" });
  await expect(page.getByText("Touches scored")).toBeVisible();
  await expect(page.getByText("1").first()).toBeVisible();

  await page.goto("/reports");
  await page.getByLabel("Athlete").selectOption({ label: "Left Fencer" });
  await page.getByRole("button", { name: "Generate PDF" }).click();
  await expect(page.getByRole("link", { name: "Download the latest report" })).toBeVisible();

  await page.goto("/datasets");
  await expect(page.getByText("MFAD", { exact: true })).toBeVisible();
  await page.goto("/models");
  await expect(page.getByText("experimental").first()).toBeVisible();
  await page.goto("/coach");
  await page.getByRole("combobox").selectOption({ label: "Left Fencer" });
  await expect(page.getByText(/No drill is suggested|Validated/)).toBeVisible();
  await page.goto("/training");
  await expect(page.getByText("Exercise library")).toBeVisible();
  await page.goto("/privacy");
  await expect(page.getByRole("button", { name: "Export my data" })).toBeVisible();

  const other = await browser.newPage();
  await other.goto("/register", { waitUntil: "networkidle" });
  await other.getByLabel("Name").fill("Other Coach");
  await other.getByLabel("Email").fill(`other-${Date.now()}@example.com`);
  await other.getByLabel("Password").fill(password);
  await other.getByLabel("Organization").fill("Other Club");
  await other.getByRole("button", { name: "Create account" }).click();
  await expect(other).toHaveURL(/\/dashboard/);
  const response = await other.goto(videoUrl);
  expect(response?.status()).toBeLessThan(500);
  await expect(other.getByText("Video not found")).toBeVisible();
});
