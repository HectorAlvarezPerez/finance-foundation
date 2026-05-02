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

async function deleteAccountById(page: import("@playwright/test").Page, accountId: string) {
  await page.evaluate(
    async ({ apiBaseUrl, accountId }) => {
      const response = await fetch(`${apiBaseUrl}/accounts/${accountId}`, {
        method: "DELETE",
        credentials: "include",
      });

      if (!response.ok && response.status !== 404) {
        throw new Error("No se pudo eliminar la cuenta de prueba");
      }
    },
    { apiBaseUrl, accountId },
  );
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
    await page.getByLabel("Saldo inicial").fill("250");
    await page.getByRole("button", { name: "Crear cuenta" }).click();
    await expect(page.getByRole("button", { name: `Ir a ${accountName}` })).toBeVisible();

    await page.getByRole("button", { name: `Ir a ${accountName}` }).click();
    await page.getByLabel(`Acciones de cuenta ${accountName}`).click();
    await page.getByRole("button", { name: "Editar" }).last().click();
    const accountDialog = page.getByRole("dialog", { name: /Editar cuenta/i });
    await expect(accountDialog).toBeVisible();
    await accountDialog.getByLabel("Nombre de la cuenta").fill(accountNameUpdated);
    await accountDialog.getByRole("button", { name: "Guardar cambios" }).click();

    await page.goto("/app/categories");
    await page.getByRole("button", { name: "Añadir" }).first().click();
    await page.getByLabel("Nombre de la categoría").fill(categoryName);
    await page.getByLabel("Seleccionar color #2563eb").click();
    await page.getByRole("button", { name: "Crear categoría" }).click();
    await expect(page.getByText(categoryName, { exact: true })).toBeVisible();

    await page.getByLabel(`Acciones de categoría ${categoryName}`).click();
    await page.locator("div.animate-slideDown").last().getByRole("button", { name: "Editar" }).click();
    await page.getByLabel("Nombre de la categoría").fill(categoryNameUpdated);
    await page.getByLabel("Tipo de categoría").selectOption("expense");
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

  test("permite mover varias transacciones seleccionadas a otra cuenta", async ({ page }) => {
    const suffix = Date.now().toString();
    const sourceAccountName = `Cuenta origen lote ${suffix}`;
    const targetAccountName = `Cuenta destino lote ${suffix}`;
    const firstTransactionName = `Movimiento lote A ${suffix}`;
    const secondTransactionName = `Movimiento lote B ${suffix}`;
    let sourceAccountId = "";
    let targetAccountId = "";

    await loginWithDemo(page);

    try {
      const setup = await page.evaluate(
        async ({
          apiBaseUrl,
          sourceAccountName,
          targetAccountName,
          firstTransactionName,
          secondTransactionName,
        }) => {
          async function createAccount(name: string) {
            const response = await fetch(`${apiBaseUrl}/accounts`, {
              method: "POST",
              credentials: "include",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                name,
                bank_name: "Banco PW",
                type: "other",
                currency: "EUR",
                initial_balance: "0.00",
              }),
            });

            if (!response.ok) {
              throw new Error(`No se pudo crear la cuenta ${name}`);
            }

            return (await response.json()) as { id: string };
          }

          async function createTransaction(accountId: string, description: string, amount: string) {
            const response = await fetch(`${apiBaseUrl}/transactions`, {
              method: "POST",
              credentials: "include",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                account_id: accountId,
                category_id: null,
                date: new Date().toISOString().slice(0, 10),
                amount,
                currency: "EUR",
                description,
                notes: null,
              }),
            });

            if (!response.ok) {
              throw new Error(`No se pudo crear la transacción ${description}`);
            }
          }

          const sourceAccount = await createAccount(sourceAccountName);
          const targetAccount = await createAccount(targetAccountName);
          await createTransaction(sourceAccount.id, firstTransactionName, "-11.00");
          await createTransaction(sourceAccount.id, secondTransactionName, "-22.00");

          return {
            sourceAccountId: sourceAccount.id,
            targetAccountId: targetAccount.id,
          };
        },
        {
          apiBaseUrl,
          sourceAccountName,
          targetAccountName,
          firstTransactionName,
          secondTransactionName,
        },
      );

      sourceAccountId = setup.sourceAccountId;
      targetAccountId = setup.targetAccountId;

      await page.goto(`/app/transactions?search=${encodeURIComponent(`Movimiento lote ${suffix}`)}`);

      const firstTransactionRow = page.getByRole("row", {
        name: new RegExp(firstTransactionName),
      });
      const secondTransactionRow = page.getByRole("row", {
        name: new RegExp(secondTransactionName),
      });

      await expect(firstTransactionRow).toContainText(sourceAccountName);
      await expect(secondTransactionRow).toContainText(sourceAccountName);
      await firstTransactionRow.getByLabel(`Seleccionar ${firstTransactionName}`).check();
      await secondTransactionRow.getByLabel(`Seleccionar ${secondTransactionName}`).check();

      await page.getByRole("button", { name: "Mover a cuenta (2)" }).click();
      const moveDialog = page.getByRole("dialog", { name: "Mover transacciones" });
      await expect(moveDialog).toBeVisible();
      await moveDialog
        .getByLabel("Cuenta destino para las transacciones seleccionadas")
        .selectOption(targetAccountId);
      await moveDialog.getByRole("button", { name: "Mover selección" }).click();

      await expect(firstTransactionRow).toContainText(targetAccountName);
      await expect(secondTransactionRow).toContainText(targetAccountName);
      await expect(page.getByRole("button", { name: "Mover a cuenta (2)" })).toHaveCount(0);
    } finally {
      if (sourceAccountId) {
        await deleteAccountById(page, sourceAccountId);
      }
      if (targetAccountId) {
        await deleteAccountById(page, targetAccountId);
      }
    }
  });

  test("permite crear una transferencia de salida con importe negativo", async ({ page }) => {
    const suffix = Date.now().toString();
    const accountName = `Cuenta transferencia ${suffix}`;
    const transactionName = `Transferencia salida ${suffix}`;
    let accountId = "";

    await loginWithDemo(page);

    try {
      const account = await page.evaluate(
        async ({ apiBaseUrl, accountName }) => {
          const response = await fetch(`${apiBaseUrl}/accounts`, {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              name: accountName,
              bank_name: "Banco PW",
              type: "other",
              currency: "EUR",
              initial_balance: "0.00",
            }),
          });

          if (!response.ok) {
            throw new Error("No se pudo crear la cuenta de transferencia");
          }

          return (await response.json()) as { id: string };
        },
        { apiBaseUrl, accountName },
      );
      accountId = account.id;

      await page.goto("/app/transactions");
      await page.getByLabel("Seleccionar tipo de transacción").click();
      await page.locator("div.animate-slideDown").last().getByRole("button", { name: "Transferencia" }).click();
      await page.getByLabel("Cuenta de la transacción").selectOption(accountId);
      await page.getByLabel("Transferencia de salida").click();
      await page.getByLabel("Importe de la transacción").fill("15.00");
      await page.getByLabel("Descripción de la transacción").fill(transactionName);
      await page.getByRole("button", { name: "Crear transacción" }).click();

      await page.getByPlaceholder("Buscar").fill(transactionName);
      const transactionRow = page.getByRole("row", { name: new RegExp(transactionName) });
      await expect(transactionRow).toBeVisible();
      await expect(transactionRow).toContainText(/-15,00\s*€/);
    } finally {
      if (accountId) {
        await deleteAccountById(page, accountId);
      }
    }
  });
});
