import { expect, test } from "@playwright/test";

test.describe("Finance Foundation navigation", () => {
  test("permite registrarse y navegar por las pantallas principales", async ({ page }) => {
    const uniqueEmail = `playwright-${Date.now()}@example.com`;

    await page.goto("/register");

    await expect(page.getByRole("heading", { name: "Crea tu cuenta" })).toBeVisible();
    await page.getByLabel("Nombre").fill("Playwright User");
    await page.getByLabel("Email").fill(uniqueEmail);
    await page.getByPlaceholder("Mínimo 8 caracteres").fill("Playwright123");
    await page.getByRole("button", { name: "Crear cuenta" }).click();

    await page.waitForURL("**/app", { timeout: 45000 });
    await expect(page.getByRole("heading", { name: "Resumen general" })).toBeVisible();

    await page.getByRole("link", { name: "Cuentas" }).click();
    await expect(page).toHaveURL(/\/app\/accounts$/);
    await expect(page.getByRole("heading", { name: "Cuentas" })).toBeVisible();

    await page.getByRole("link", { name: "Categorías" }).click();
    await expect(page).toHaveURL(/\/app\/categories$/);
    await expect(page.getByRole("heading", { name: "Categorías" })).toBeVisible();

    await page.getByRole("link", { name: "Presupuestos" }).click();
    await expect(page).toHaveURL(/\/app\/budgets$/);
    await expect(page.getByRole("heading", { name: "Control de presupuestos" })).toBeVisible();

    await page.getByRole("link", { name: "Análisis" }).click();
    await expect(page).toHaveURL(/\/app\/insights$/);
    await expect(page.getByRole("heading", { name: "Análisis financiero" })).toBeVisible();
  });
});
