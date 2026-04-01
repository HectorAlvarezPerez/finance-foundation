import { expect, test } from "@playwright/test";

import { loginWithDemo, registerUser } from "./helpers";

test.describe("Auth flows", () => {
  test("permite iniciar sesión con el modo demo", async ({ page }) => {
    await loginWithDemo(page);
  });

  test("permite registrarse, cerrar sesión y volver a iniciar sesión", async ({ page }) => {
    const suffix = Date.now().toString();
    const { email } = await registerUser(page, `login-${suffix}`);
    await page.getByRole("button", { name: "Cerrar sesión" }).click();
    await page.waitForURL("**/login*", { timeout: 15000 });

    await page.getByLabel("Email").fill(email);
    await page.getByPlaceholder("••••••••").fill("Playwright123");
    await page.getByRole("button", { name: "Entrar" }).click();

    await page.waitForURL("**/app", { timeout: 15000 });
    await expect(page.getByRole("heading", { name: "Resumen general" })).toBeVisible();
  });

  test("permite eliminar la cuenta desde ajustes", async ({ page }) => {
    await registerUser(page, `delete-${Date.now()}`);

    await page.goto("/app/settings");
    await expect(page.getByRole("heading", { name: "Preferencias" })).toBeVisible();

    await page.getByRole("button", { name: "Eliminar cuenta" }).first().click();
    await page.getByRole("dialog", { name: "Eliminar cuenta" }).getByRole("button", { name: "Eliminar cuenta" }).click();

    await page.waitForURL("**/login*", { timeout: 15000 });
    await expect(page.getByRole("heading", { name: "Bienvenido de nuevo" })).toBeVisible();
  });
});
