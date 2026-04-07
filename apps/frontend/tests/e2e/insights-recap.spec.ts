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
        headline: `${headlinePrefix} dining dominated the month`,
        subheadline: "The biggest slice of spend came from food and casual lunches.",
        body: "The visual stack shows where the category concentrated and how much of the month it took.",
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
        headline: `${headlinePrefix} had one standout moment`,
        subheadline: "A single charge carried the most weight in the story.",
        body: "This card highlights the transaction that moved the month the most.",
        facts: [
          { label: "Merchant", value: "Apple Store", tone: "neutral" },
          { label: "Date", value: "12 Mar", tone: "accent" },
        ],
        visual: {
          kind: "biggest_moment",
          amount: -245.0,
          date_label: "12 Mar 2026",
          merchant: "Apple Store",
          description: "One larger purchase changed the shape of the month.",
        },
      },
      {
        id: `${headlinePrefix}-3`,
        kind: "month_comparison",
        headline: `${headlinePrefix} moved up versus February`,
        subheadline: "March nudged the line higher, but not by a huge margin.",
        body: "Comparison keeps the recap grounded in a real trend instead of a single number.",
        facts: [
          { label: "Delta", value: "+€42.00", tone: "positive" },
        ],
        visual: {
          kind: "month_comparison",
          current_amount: 1800,
          previous_amount: 1758,
          delta: 42,
          current_label: "Mar 2026",
          previous_label: "Feb 2026",
          current_color: "#0071e3",
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
  await expect(page.getByRole("button", { name: "Play monthly recap" })).toBeVisible();
  await expect(page.getByLabel("Month")).toHaveValue("2026-03");

  await page.getByRole("button", { name: "Play monthly recap" }).click();

  const dialog = page.getByRole("dialog", { name: /Monthly recap/i });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("heading", { name: /Original dining dominated the month/i })).toBeVisible();

  await dialog.getByRole("button", { name: "Next story" }).click();
  await expect(dialog.getByRole("heading", { name: /Original had one standout moment/i })).toBeVisible();

  await dialog.getByRole("button", { name: "Close recap" }).click();
  await expect(dialog).not.toBeVisible();

  await page.getByRole("button", { name: "Regenerate" }).click();
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("heading", { name: /Fresh dining dominated the month/i })).toBeVisible();
});
