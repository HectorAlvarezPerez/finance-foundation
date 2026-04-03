import { expect, Page } from "@playwright/test";

async function waitForAppShell(page: Page) {
  await expect
    .poll(() => page.url(), {
      timeout: 30000,
      message: "La app no terminó de redirigir al área autenticada",
    })
    .toMatch(/\/app(?:$|[/?#])/);

  await expect(page.getByRole("heading", { name: "Resumen general" })).toBeVisible({ timeout: 15000 });
}

async function waitForAuthScreen(page: Page, path: "/login" | "/register") {
  const targetHeading = path === "/login" ? "Bienvenido de nuevo" : "Crea tu cuenta";

  for (let attempt = 0; attempt < 5; attempt += 1) {
    await page.goto(path, { waitUntil: "domcontentloaded" });
    try {
      await expect(page.getByRole("heading", { name: targetHeading })).toBeVisible({ timeout: 8000 });
      return;
    } catch {
      await page.waitForTimeout(1500);
    }
  }

  await expect(page.getByRole("heading", { name: targetHeading })).toBeVisible({ timeout: 10000 });
}

export async function loginWithDemo(page: Page) {
  await waitForAuthScreen(page, "/login");
  await page.getByRole("button", { name: "Probar modo demo" }).click();
  await waitForAppShell(page);
}

export async function registerUser(page: Page, suffix = Date.now().toString()) {
  const email = `playwright-${suffix}@example.com`;

  await waitForAuthScreen(page, "/register");
  const nameInput = page.getByPlaceholder("Tu nombre");
  const emailInput = page.getByLabel("Email");
  const passwordInput = page.getByPlaceholder("Mínimo 8 caracteres");

  await nameInput.click();
  await nameInput.fill("");
  await nameInput.pressSequentially("Playwright User");
  await expect(nameInput).toHaveValue("Playwright User");
  await emailInput.fill(email);
  await expect(emailInput).toHaveValue(email);
  await passwordInput.fill("Playwright123");
  await expect(passwordInput).toHaveValue("Playwright123");
  await page.getByRole("button", { name: "Crear cuenta" }).click();
  await waitForAppShell(page);

  return { email };
}
