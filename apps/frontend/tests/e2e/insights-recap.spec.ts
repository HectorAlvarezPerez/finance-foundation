import { expect, test } from "@playwright/test";

import { loginWithDemo } from "./helpers";

function buildRecap(monthLabel: string, headlinePrefix: string, generatedAt: string, sourceFingerprint: string) {
  return {
    month_key: "2026-03",
    month_label: monthLabel,
    status: "ready",
    generated_at: generatedAt,
    source_fingerprint: sourceFingerprint,
    is_stale: false,
    stories: [
      {
        id: `${headlinePrefix}-1`,
        kind: "top_category",
        headline: `${headlinePrefix} comida dominó el mes`,
        subheadline: "La porción más grande del gasto llegó desde la comida del día a día.",
        body: "La composición visual muestra dónde se concentró la categoría y cuánto peso tuvo en el mes.",
        facts: [
          { label: "Share", value: "34%", tone: "accent" },
          { label: "Amount", value: "€345.20", tone: "neutral" },
        ],
        visual: {
          kind: "top_category",
          category_name: "Comida",
          category_color: "#f97316",
          amount: 345.2,
          share: 34,
          series: [
            { label: "Comida", value: 345.2, color: "#f97316" },
            { label: "Transporte", value: 120, color: "#0ea5e9" },
          ],
        },
      },
      {
        id: `${headlinePrefix}-2`,
        kind: "biggest_moment",
        headline: `${headlinePrefix} tuvo un momento muy marcado`,
        subheadline: "Un único cargo arrastró gran parte del relato del mes.",
        body: "Esta story destaca la transacción que más movió el mes.",
        facts: [
          { label: "Merchant", value: "Apple Store", tone: "neutral" },
          { label: "Date", value: "12 Mar", tone: "accent" },
        ],
        visual: {
          kind: "biggest_moment",
          amount: -245.0,
          date_label: "12 Mar 2026",
          merchant: "Apple Store",
          description: "Una compra más grande cambió la forma del mes.",
        },
      },
      {
        id: `${headlinePrefix}-3`,
        kind: "month_comparison",
        headline: `${headlinePrefix} cerró igual que febrero`,
        subheadline: "El gasto total quedó estable frente al mes anterior.",
        body: "La comparativa mantiene el recap anclado en una tendencia real y no en una sola cifra.",
        facts: [
          { label: "Delta", value: "0,00 EUR", tone: "positive" },
        ],
        visual: {
          kind: "month_comparison",
          current_amount: "2062,50",
          previous_amount: "2.062,50",
          delta: "0,00",
          current_label: "Mar 2026",
          previous_label: "Feb 2026",
          current_color: "orange-500",
          previous_color: "rgba(255,255,255,0.34)",
        },
      },
    ],
  };
}

test("muestra y regenera el recap mensual en Insights", async ({ page }) => {
  await loginWithDemo(page);

  await page.route("**/api/v1/insights/summary", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        income: "3200.00",
        expenses: "1450.00",
        balance: "1750.00",
        transaction_count: 24,
        top_categories: [
          {
            category_id: "cat-1",
            name: "Comida",
            color: "#f97316",
            total: "345.20",
          },
        ],
        monthly_comparison: [
          {
            month_key: "2026-02",
            month_label: "feb 26",
            income: "3100.00",
            expenses: "1400.00",
            net: "1700.00",
            transactions: 20,
          },
          {
            month_key: "2026-03",
            month_label: "mar 26",
            income: "3200.00",
            expenses: "1450.00",
            net: "1750.00",
            transactions: 24,
          },
        ],
        account_balances: [
          {
            account_id: "acc-1",
            name: "Cuenta principal",
            currency: "EUR",
            total: "1750.00",
          },
        ],
        available_recap_months: [
          { month_key: "2026-02", month_label: "febrero 2026" },
          { month_key: "2026-03", month_label: "marzo 2026" },
        ],
      }),
    });
  });

  await page.route("**/api/v1/insights/monthly-recap**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (request.method() === "POST" && url.pathname.endsWith("/regenerate")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(buildRecap("marzo 2026", "Fresh", "2026-04-05T10:20:00.000Z", "fingerprint-fresh")),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(buildRecap("marzo 2026", "Original", "2026-04-05T10:00:00.000Z", "fingerprint-original")),
    });
  });

  await page.goto("/app/insights");

  await expect(page.getByRole("heading", { name: "Análisis financiero" })).toBeVisible();
  const openRecapButton = page.getByRole("button", { name: /Ver recap( mensual)?/i });
  await expect(openRecapButton).toBeVisible();
  await expect(page.getByLabel("Mes")).toHaveValue("2026-03");

  await openRecapButton.click();

  const dialog = page.getByRole("dialog", { name: /Recap mensual/i });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("heading", { name: /Original comida dominó el mes/i })).toBeVisible();

  await dialog.getByRole("button", { name: "Siguiente story" }).click();
  await expect(dialog.getByRole("heading", { name: /Original tuvo un momento muy marcado/i })).toBeVisible();

  await dialog.getByRole("button", { name: "Siguiente story" }).click();
  await expect(dialog.getByRole("heading", { name: /Original cerró igual que febrero/i })).toBeVisible();
  await expect(dialog.getByText("0,00 €")).toBeVisible();
  const activeBarBackgroundImage = await dialog
    .getByTestId("comparison-bar-active")
    .evaluate((element) => getComputedStyle(element).backgroundImage);
  expect(activeBarBackgroundImage).not.toBe("none");

  await dialog.getByRole("button", { name: "Cerrar recap" }).click();
  await expect(dialog).not.toBeVisible();

  await page.getByRole("button", { name: "Regenerar" }).click();
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("heading", { name: /Fresh comida dominó el mes/i })).toBeVisible();
});
