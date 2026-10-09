import { expect, test } from "@playwright/test";

const password = "piste-ready-2026";

test("federation pilot journey", async ({ page }) => {
  const email = `dt-${Date.now()}@example.com`;
  await page.goto("/register", { waitUntil: "networkidle" });
  await page.getByLabel("Name").fill("Directoire Technique");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByLabel("Organization").fill("Ligue Essai");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/dashboard/);

  const fencers = ["Ava Solo", "Ben Piste", "Cleo Masque", "Dan Fleuret"];
  await page.goto("/athletes");
  for (const [index, name] of fencers.entries()) {
    await page.getByLabel("Name").fill(name);
    await page.getByLabel("License no.").fill(`E2E-${Date.now()}-${index}`);
    if (index < 2) {
      await page.getByLabel("Birth year").fill("2013");
      await page.getByLabel("Category").selectOption("u15");
    }
    await page.getByRole("button", { name: "Add", exact: true }).click();
    await expect(page.getByRole("link", { name: new RegExp(name) })).toBeVisible();
  }

  await page.getByRole("link", { name: /Ava Solo/ }).click();
  await expect(page.getByText("Minor — guardian consent missing")).toBeVisible();
  await page.getByLabel("Guardian name").fill("Parent Solo");
  await page.getByLabel("Note (where/when signed)").fill("desk, today");
  await page.getByRole("button", { name: "Record grant" }).click();
  await expect(page.getByText("Minor — guardian consent recorded")).toBeVisible({ timeout: 15_000 });

  await page.goto("/competitions");
  await page.getByLabel("Name").fill("E2E Cup");
  await page.getByRole("button", { name: "Create", exact: true }).click();
  await page.getByRole("link", { name: /E2E Cup/ }).click();

  for (const name of fencers) {
    await expect(page.locator('select[name="athlete"] option', { hasText: name }).first()).toBeAttached();
    await page.locator('select[name="athlete"]').selectOption({ label: name });
    await page.getByRole("button", { name: "Enter", exact: true }).click();
    await expect(page.getByText("Entry added.")).toBeVisible();
  }

  await page.getByLabel("Group size").fill("4");
  await page.getByRole("button", { name: "Draw poules" }).click();
  await expect(page.getByText("Poule sheet drawn.")).toBeVisible();
  await expect(page.getByRole("cell", { name: "Ava Solo" }).first()).toBeVisible();

  await page.getByRole("button", { name: "Draw DE" }).click();
  await expect(page.getByText("DE draw created.")).toBeVisible();
  await expect(page.getByText("vs").first()).toBeVisible();
});
