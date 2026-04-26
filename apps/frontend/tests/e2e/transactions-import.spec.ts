import { expect, test } from "@playwright/test";

import { loginWithDemo } from "./helpers";

const apiBaseUrl = "http://localhost:8000/api/v1";

function buildImportAnalysisResponse(accountId: string) {
  return {
    source_type: "csv",
    columns: ["Fecha", "Importe", "Merchant"],
    sample_rows: [
      {
        Fecha: "11/03/2026",
        Importe: "-12.40",
        Merchant: "Mercadona Valencia",
      },
      {
        Fecha: "11/03/2026",
        Importe: "-12.40",
        Merchant: "Mercadona Valencia",
      },
    ],
    suggested_mapping: {
      date: "Fecha",
      amount: "Importe",
      description: "Merchant",
      category: null,
      notes: null,
    },
    total_rows: 2,
    message: null,
    account_id: accountId,
  };
}

function buildImportPreviewResponse(accountId: string, suggestedCategoryId: string, suggestedCategoryName: string) {
  return {
    source_type: "csv",
    account_id: accountId,
    account_currency: "EUR",
    imported_count: 2,
    rows: [
      {
        source_row_number: 1,
        account_id: accountId,
        category_id: suggestedCategoryId,
        category_label: null,
        category_suggestion_label: suggestedCategoryName,
        category_suggestion_source: "history",
        category_suggestion_confidence: 0.93,
        category_is_suggested: true,
        date: "2026-03-11",
        amount: "-12.40",
        currency: "EUR",
        description: "Mercadona Valencia",
        notes: null,
        validation_errors: [],
      },
      {
        source_row_number: 2,
        account_id: accountId,
        category_id: suggestedCategoryId,
        category_label: null,
        category_suggestion_label: suggestedCategoryName,
        category_suggestion_source: "history",
        category_suggestion_confidence: 0.93,
        category_is_suggested: true,
        date: "2026-03-11",
        amount: "-12.40",
        currency: "EUR",
        description: "Mercadona Valencia",
        notes: null,
        validation_errors: [],
      },
    ],
  };
}

async function createEntity<T>(
  page: import("@playwright/test").Page,
  resource: "accounts" | "categories",
  payload: Record<string, unknown>,
) {
  return page.evaluate(
    async ({ apiBaseUrl, resource, payload }) => {
      const response = await fetch(`${apiBaseUrl}/${resource}`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`No se pudo crear ${resource}`);
      }

      return (await response.json()) as T;
    },
    { apiBaseUrl, resource, payload },
  );
}

async function deleteEntityByName(
  page: import("@playwright/test").Page,
  resource: "accounts" | "categories",
  name: string,
) {
  await page.evaluate(
    async ({ apiBaseUrl, resource, name }) => {
      const listResponse = await fetch(
        `${apiBaseUrl}/${resource}?limit=100&sort_by=name&sort_order=asc`,
        {
          credentials: "include",
        },
      );

      if (!listResponse.ok) {
        throw new Error(`No se pudo cargar ${resource}`);
      }

      const payload = (await listResponse.json()) as { items: { id: string; name: string }[] };
      const target = payload.items.find((item) => item.name === name);
      if (!target) {
        return;
      }

      const deleteResponse = await fetch(`${apiBaseUrl}/${resource}/${target.id}`, {
        method: "DELETE",
        credentials: "include",
      });

      if (!deleteResponse.ok) {
        throw new Error(`No se pudo eliminar ${resource}`);
      }
    },
    { apiBaseUrl, resource, name },
  );
}

test("mantiene la categoría sugerida editable durante la revisión de importación", async ({
  page,
}) => {
  const suffix = Date.now().toString();
  const accountName = `Cuenta Import ${suffix}`;
  const suggestedCategoryName = `Supermercado ${suffix}`;
  const alternateCategoryName = `Transporte ${suffix}`;

  await loginWithDemo(page);

  const account = await createEntity<{ id: string }>(page, "accounts", {
    name: accountName,
    type: "checking",
    currency: "EUR",
  });
  const suggestedCategory = await createEntity<{ id: string }>(page, "categories", {
    name: suggestedCategoryName,
    type: "expense",
    color: "#22c55e",
    icon: "shopping-cart",
  });
  await createEntity<{ id: string }>(page, "categories", {
    name: alternateCategoryName,
    type: "expense",
    color: "#0ea5e9",
    icon: "bus",
  });

  await page.route("**/api/v1/transactions/import/analyze", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        source_type: "csv",
        columns: ["Fecha", "Importe", "Merchant"],
        sample_rows: [
          {
            Fecha: "11/03/2026",
            Importe: "-12.40",
            Merchant: "Mercadona Valencia",
          },
        ],
        suggested_mapping: {
          date: "Fecha",
          amount: "Importe",
          description: "Merchant",
          category: null,
          notes: null,
        },
        total_rows: 1,
        message: null,
      }),
    });
  });

  await page.route("**/api/v1/transactions/import/preview", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 700));
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        source_type: "csv",
        account_id: account.id,
        account_currency: "EUR",
        imported_count: 1,
        rows: [
          {
            source_row_number: 1,
            account_id: account.id,
            category_id: suggestedCategory.id,
            category_label: null,
            category_suggestion_label: suggestedCategoryName,
            category_suggestion_source: "history",
            category_suggestion_confidence: 0.93,
            category_is_suggested: true,
            date: "2026-03-11",
            amount: "-12.40",
            currency: "EUR",
            description: "Mercadona Valencia",
            notes: null,
            validation_errors: [],
          },
        ],
      }),
    });
  });

  await page.goto("/app/transactions");
  await page.getByRole("button", { name: "Import transactions" }).click();
  const importDialog = page.getByRole("dialog", { name: "Importar transacciones" });
  await importDialog.getByRole("combobox").selectOption({ label: `${accountName} · EUR` });
  await importDialog.locator('input[type="file"]').setInputFiles({
    name: "transactions.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("Fecha,Importe,Merchant\n11/03/2026,-12.40,Mercadona Valencia\n"),
  });

  await expect(
    importDialog.getByRole("checkbox", {
      name: /^Categorizar automáticamente las transacciones con IA/,
    }),
  ).not.toBeVisible();
  await page.getByRole("button", { name: /Siguiente: mapear columnas/i }).click();
  await expect(
    importDialog.getByRole("checkbox", {
      name: /^Categorizar automáticamente las transacciones con IA/,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Preparar revisión" }).click();

  await expect(
    importDialog.getByRole("button", { name: "Classifying transactions by category" }),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/app\/transactions(?:\?|$)/);
  await expect(page.getByText("Revisión temporal de importación")).toBeVisible();

  const reviewRow = page.getByRole("row", { name: /Mercadona Valencia/ });
  const categorySelect = reviewRow.locator("select");
  await expect(categorySelect).toHaveValue(suggestedCategory.id);
  await expect(
    reviewRow.getByText(/Categoría sugerida por historial: .*Puedes cambiarla o dejarla vacía\./),
  ).toBeVisible();

  await categorySelect.selectOption({ label: alternateCategoryName });
  await expect(categorySelect).toHaveValue(/.+/);
  await categorySelect.selectOption("");
  await expect(categorySelect).toHaveValue("");
  await expect(page.getByRole("button", { name: "Importar listas" })).toBeEnabled();

  await deleteEntityByName(page, "categories", suggestedCategoryName);
  await deleteEntityByName(page, "categories", alternateCategoryName);
  await deleteEntityByName(page, "accounts", accountName);
});

test("recupera la revisión temporal tras recargar y bloquea iniciar una segunda importación sin decidir", async ({
  page,
}) => {
  const suffix = Date.now().toString();
  const accountName = `Cuenta Persistencia ${suffix}`;
  const suggestedCategoryName = `Comida ${suffix}`;

  await loginWithDemo(page);

  const account = await createEntity<{ id: string }>(page, "accounts", {
    name: accountName,
    type: "checking",
    currency: "EUR",
  });
  const suggestedCategory = await createEntity<{ id: string }>(page, "categories", {
    name: suggestedCategoryName,
    type: "expense",
    color: "#22c55e",
    icon: "shopping-cart",
  });

  await page.route("**/api/v1/transactions/import/analyze", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(buildImportAnalysisResponse(account.id)),
    });
  });

  await page.route("**/api/v1/transactions/import/preview", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(
        buildImportPreviewResponse(account.id, suggestedCategory.id, suggestedCategoryName),
      ),
    });
  });

  await page.goto("/app/transactions");
  await page.getByRole("button", { name: "Import transactions" }).click();
  const importDialog = page.getByRole("dialog", { name: "Importar transacciones" });
  await importDialog.getByRole("combobox").selectOption({ label: `${accountName} · EUR` });
  await importDialog.locator('input[type="file"]').setInputFiles({
    name: "transactions.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "Fecha,Importe,Merchant\n11/03/2026,-12.40,Mercadona Valencia\n11/03/2026,-12.40,Mercadona Valencia\n",
    ),
  });

  await page.getByRole("button", { name: /Siguiente: mapear columnas/i }).click();
  await page.getByRole("button", { name: "Preparar revisión" }).click();
  await expect(page.getByText("Revisión temporal de importación")).toBeVisible();

  await page.reload();
  await expect(page.getByText("Se ha recuperado una revisión de importación pendiente")).toBeVisible();
  await expect(page.getByText("Revisión temporal de importación")).toBeVisible();

  await page.getByRole("button", { name: "Import transactions" }).click();
  const replaceDialog = page.getByRole("dialog", { name: "Descartar revisión pendiente" });
  await expect(replaceDialog).toBeVisible();
  await replaceDialog.getByRole("button", { name: "Cancelar" }).click();
  await expect(replaceDialog).not.toBeVisible();
  await expect(page.getByText("Revisión temporal de importación")).toBeVisible();

  await deleteEntityByName(page, "categories", suggestedCategoryName);
  await deleteEntityByName(page, "accounts", accountName);
});

test("permite editar y descartar filas antes de confirmar la importación", async ({ page }) => {
  const suffix = Date.now().toString();
  const accountName = `Cuenta Confirmación ${suffix}`;
  const suggestedCategoryName = `Comida ${suffix}`;
  const alternateCategoryName = `Transporte ${suffix}`;
  let commitPayload: unknown = null;

  await loginWithDemo(page);

  const account = await createEntity<{ id: string }>(page, "accounts", {
    name: accountName,
    type: "checking",
    currency: "EUR",
  });
  const suggestedCategory = await createEntity<{ id: string }>(page, "categories", {
    name: suggestedCategoryName,
    type: "expense",
    color: "#22c55e",
    icon: "shopping-cart",
  });
  const alternateCategory = await createEntity<{ id: string }>(page, "categories", {
    name: alternateCategoryName,
    type: "expense",
    color: "#0ea5e9",
    icon: "bus",
  });

  await page.route("**/api/v1/transactions/import/analyze", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(buildImportAnalysisResponse(account.id)),
    });
  });

  await page.route("**/api/v1/transactions/import/preview", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(
        buildImportPreviewResponse(account.id, suggestedCategory.id, suggestedCategoryName),
      ),
    });
  });

  await page.route("**/api/v1/transactions/import/commit", async (route) => {
    commitPayload = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        imported_count: 1,
        skipped_duplicates: 0,
      }),
    });
  });

  await page.goto("/app/transactions");
  await page.getByRole("button", { name: "Import transactions" }).click();
  const importDialog = page.getByRole("dialog", { name: "Importar transacciones" });
  await importDialog.getByRole("combobox").selectOption({ label: `${accountName} · EUR` });
  await importDialog.locator('input[type="file"]').setInputFiles({
    name: "transactions.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "Fecha,Importe,Merchant\n11/03/2026,-12.40,Mercadona Valencia\n11/03/2026,-12.40,Mercadona Valencia\n",
    ),
  });

  await page.getByRole("button", { name: /Siguiente: mapear columnas/i }).click();
  await page.getByRole("button", { name: "Preparar revisión" }).click();
  await expect(page.getByText("Revisión temporal de importación")).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Reembolso" })).toHaveCount(0);

  const reviewRows = page.locator("table tbody tr");
  await reviewRows.nth(0).locator("select").selectOption(alternateCategory.id);
  await reviewRows.nth(1).getByRole("button", { name: "Descartar fila 2" }).click();

  await page.getByRole("button", { name: "Importar listas" }).click();
  await expect(page.getByText("Revisión temporal de importación")).not.toBeVisible();

  expect(commitPayload).toMatchObject({
    items: [
      {
        account_id: account.id,
        category_id: alternateCategory.id,
        description: "Mercadona Valencia",
      },
    ],
  });
  expect((commitPayload as { items: Array<Record<string, unknown>> }).items[0]).not.toHaveProperty(
    "is_refund",
  );

  await deleteEntityByName(page, "categories", suggestedCategoryName);
  await deleteEntityByName(page, "categories", alternateCategoryName);
  await deleteEntityByName(page, "accounts", accountName);
});

test("muestra cuántos duplicados se omiten al confirmar la importación", async ({ page }) => {
  const suffix = Date.now().toString();
  const accountName = `Cuenta Duplicados ${suffix}`;
  const suggestedCategoryName = `Comida ${suffix}`;

  await loginWithDemo(page);

  const account = await createEntity<{ id: string }>(page, "accounts", {
    name: accountName,
    type: "checking",
    currency: "EUR",
  });
  const suggestedCategory = await createEntity<{ id: string }>(page, "categories", {
    name: suggestedCategoryName,
    type: "expense",
    color: "#22c55e",
    icon: "shopping-cart",
  });

  await page.route("**/api/v1/transactions/import/analyze", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(buildImportAnalysisResponse(account.id)),
    });
  });

  await page.route("**/api/v1/transactions/import/preview", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(
        buildImportPreviewResponse(account.id, suggestedCategory.id, suggestedCategoryName),
      ),
    });
  });

  await page.route("**/api/v1/transactions/import/commit", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        imported_count: 1,
        skipped_duplicates: 1,
      }),
    });
  });

  await page.goto("/app/transactions");
  await page.getByRole("button", { name: "Import transactions" }).click();
  const importDialog = page.getByRole("dialog", { name: "Importar transacciones" });
  await importDialog.getByRole("combobox").selectOption({ label: `${accountName} · EUR` });
  await importDialog.locator('input[type="file"]').setInputFiles({
    name: "transactions.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "Fecha,Importe,Merchant\n11/03/2026,-12.40,Mercadona Valencia\n11/03/2026,-12.40,Mercadona Valencia\n",
    ),
  });

  await page.getByRole("button", { name: /Siguiente: mapear columnas/i }).click();
  await page.getByRole("button", { name: "Preparar revisión" }).click();
  await page.getByRole("button", { name: "Importar listas" }).click();

  await expect(
    page.getByText("1 transacciones añadidas y 1 duplicadas omitidas"),
  ).toBeVisible();

  await deleteEntityByName(page, "categories", suggestedCategoryName);
  await deleteEntityByName(page, "accounts", accountName);
});
