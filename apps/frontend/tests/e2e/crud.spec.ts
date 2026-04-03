import { expect, test } from "@playwright/test";

import { loginWithDemo } from "./helpers";

const apiBaseUrl = "http://localhost:8000/api/v1";

async function deleteEntityByName(
  page: import("@playwright/test").Page,
  resource: "accounts" | "categories",
  name: string,
) {
  const deleted = await page.evaluate(
    async ({ apiBaseUrl, resource, name }) => {
      const listResponse = await fetch(`${apiBaseUrl}/${resource}?limit=100&sort_by=name&sort_order=asc`, {
        credentials: "include",
      });

      if (!listResponse.ok) {
        throw new Error(`No se pudo cargar ${resource}`);
      }

      const payload = (await listResponse.json()) as { items: { id: string; name: string }[] };
      const target = payload.items.find((item) => item.name === name);

      if (!target) {
        return false;
      }

      const deleteResponse = await fetch(`${apiBaseUrl}/${resource}/${target.id}`, {
        method: "DELETE",
        credentials: "include",
      });

      if (!deleteResponse.ok) {
        throw new Error(`No se pudo eliminar ${resource}`);
      }

      return true;
    },
    { apiBaseUrl, resource, name },
  );

  expect(deleted).toBeTruthy();
}

test.describe("CRUD principal", () => {
  test("permite crear, editar y limpiar cuentas, categorías, presupuestos y transacciones", async ({ page }) => {
    const suffix = Date.now().toString();
    const accountName = `Cuenta PW ${suffix}`;
    const accountNameUpdated = `Cuenta PW Edit ${suffix}`;
    const categoryName = `Categoria PW ${suffix}`;
    const categoryNameUpdated = `Categoria PW Edit ${suffix}`;
    const transactionName = `Movimiento PW ${suffix}`;
    const transactionNameUpdated = `Movimiento PW Edit ${suffix}`;

    await loginWithDemo(page);

    await page.goto("/app/accounts");
    await page.getByRole("button", { name: "Nueva cuenta" }).click();
    await page.getByLabel("Nombre de la cuenta").fill(accountName);
    await page.getByLabel("Banco").fill("Banco PW");
    await page.getByLabel("Tipo de cuenta").selectOption("other");
    await page.getByLabel("Divisa").fill("EUR");
    await page.getByLabel("Saldo inicial").fill("250");
    await page.getByRole("button", { name: "Crear cuenta" }).click();
    await expect(page.getByText(accountName, { exact: true })).toBeVisible();

    await page.getByLabel(`Acciones de cuenta ${accountName}`).click();
    await page.locator("div.animate-slideDown").last().getByRole("button", { name: "Editar" }).click();
    await page.getByLabel("Nombre de la cuenta").fill(accountNameUpdated);
    await page.getByRole("button", { name: "Guardar cambios" }).click();

    await page.goto("/app/categories");
    await page.getByRole("button", { name: "Nueva categoría" }).click();
    await page.getByLabel("Nombre de la categoría").fill(categoryName);
    await page.getByLabel("Tipo de categoría").selectOption("expense");
    await page.getByLabel("Seleccionar color #2563eb").click();
    await page.getByRole("button", { name: "Crear categoría" }).click();
    await expect(page.getByText(categoryName, { exact: true })).toBeVisible();

    await page.getByLabel(`Acciones de categoría ${categoryName}`).click();
    await page.locator("div.animate-slideDown").last().getByRole("button", { name: "Editar" }).click();
    await page.getByLabel("Nombre de la categoría").fill(categoryNameUpdated);
    await page.getByRole("button", { name: "Guardar cambios" }).click();

    await page.goto("/app/budgets");
    await page.getByRole("button", { name: "Nuevo presupuesto" }).click();
    await page.getByLabel("Categoría del presupuesto").selectOption({ label: categoryNameUpdated });
    await page.getByLabel("Año del presupuesto").fill(new Date().getFullYear().toString());
    await page.getByLabel("Mes del presupuesto").selectOption((new Date().getMonth() + 1).toString());
    await page.getByLabel("Divisa del presupuesto").fill("EUR");
    await page.getByLabel("Importe del presupuesto").fill("180");
    await page.getByRole("button", { name: "Crear presupuesto" }).click();
    await expect(page.getByText(categoryNameUpdated, { exact: true }).first()).toBeVisible();

    const budgetActionLabel = new RegExp(`Acciones de presupuesto ${categoryNameUpdated}`);
    await page.getByLabel(budgetActionLabel).first().click();
    await page.locator("div.animate-slideDown").last().getByRole("button", { name: "Editar" }).click();
    await page.getByLabel("Importe del presupuesto").fill("220");
    await page.getByRole("button", { name: "Guardar cambios" }).click();
    await expect(page.getByText(/220,00\s€/).first()).toBeVisible();

    await page.goto("/app/transactions");
    await page.getByRole("button", { name: "Nueva transacción" }).click();
    const accountSelect = page.getByLabel("Cuenta de la transacción");
    const accountValue = await accountSelect
      .locator("option")
      .filter({ hasText: accountNameUpdated })
      .first()
      .getAttribute("value");

    await accountSelect.selectOption(accountValue ?? "");
    await page.getByLabel("Categoría de la transacción").selectOption({ label: categoryNameUpdated });
    await page.getByLabel("Importe de la transacción").fill("-35.40");
    await page.getByLabel("Descripción de la transacción").fill(transactionName);
    await page.getByLabel("Notas de la transacción").fill("Creada desde Playwright");
    await page.getByRole("button", { name: "Crear transacción" }).click();
    await page.getByPlaceholder("Buscar").fill(transactionName);
    const transactionRow = page.getByRole("row", { name: new RegExp(transactionName) });
    await expect(transactionRow).toBeVisible();

    await transactionRow.getByLabel(`Acciones de transacción ${transactionName}`).click();
    await page.locator("div.animate-slideDown").last().getByRole("button", { name: "Editar" }).click();
    await page.getByLabel("Descripción de la transacción").fill(transactionNameUpdated);
    await page.getByRole("button", { name: "Guardar cambios" }).click();
    await page.getByPlaceholder("Buscar").fill(transactionNameUpdated);
    const updatedTransactionRow = page.getByRole("row", { name: new RegExp(transactionNameUpdated) });
    await expect(updatedTransactionRow).toBeVisible();

    await updatedTransactionRow.getByLabel(`Acciones de transacción ${transactionNameUpdated}`).click();
    await page.locator("div.animate-slideDown").last().getByRole("button", { name: "Eliminar" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Eliminar" }).click();
    await expect(updatedTransactionRow).toHaveCount(0);

    await page.goto("/app/budgets");
    await page.getByLabel(budgetActionLabel).first().click();
    await page.locator("div.animate-slideDown").last().getByRole("button", { name: "Eliminar" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Eliminar" }).click();

    await page.goto("/app/categories");
    await deleteEntityByName(page, "categories", categoryNameUpdated);

    await page.goto("/app/accounts");
    await deleteEntityByName(page, "accounts", accountNameUpdated);
  });
});
