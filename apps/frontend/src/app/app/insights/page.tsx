"use client";

import { useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { CreditCard, TrendingDown, TrendingUp, Wallet } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { AmountValue } from "@/components/amount-value";
import { CashFlowChart } from "@/components/insights/cash-flow-chart";
import { CategoryTreemap } from "@/components/insights/category-treemap";
import { CumulativePacingChart } from "@/components/insights/cumulative-pacing-chart";
import { MonthlyRecapLauncher } from "@/components/insights/monthly-recap-launcher";
import { MonthlyRecapOverlay } from "@/components/insights/monthly-recap-overlay";
import { ListSkeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { apiRequest } from "@/lib/api";
import { formatCurrency, formatMonthLabel } from "@/lib/format";
import type {
  InsightsMonthlyRecap,
  InsightsMonthlyRecapRegenerateRequest,
  InsightsRecapMonth,
  InsightsSummaryWithRecapMonths,
} from "@/lib/types";

const chartPalette = {
  success: "#34C759",
  danger: "#FF6B6B",
  accent: "#4F8CFF",
  muted: "#8E8E93",
};

export default function InsightsPage() {
  const { toast } = useToast();
  const [summary, setSummary] = useState<InsightsSummaryWithRecapMonths | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedMonthKey, setSelectedMonthKey] = useState("");
  const [recap, setRecap] = useState<InsightsMonthlyRecap | null>(null);
  const [recapError, setRecapError] = useState<string | null>(null);
  const [isRecapLoading, setIsRecapLoading] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [isRecapOpen, setIsRecapOpen] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const nextSummary = await apiRequest<InsightsSummaryWithRecapMonths>("/insights/summary");
        setSummary(nextSummary);
        setSummaryError(null);
      } catch (requestError) {
        setSummaryError(requestError instanceof Error ? requestError.message : "No se pudo cargar el análisis");
      } finally {
        setIsLoading(false);
      }
    }

    void load();
  }, []);

  const currentMonthKey = useMemo(() => {
    const today = new Date();
    return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;
  }, []);

  const periodLabel = useMemo(() => {
    const today = new Date();
    return formatMonthLabel(today.getFullYear(), today.getMonth() + 1);
  }, []);

  const recapMonths = useMemo(() => normalizeRecapMonths(summary), [summary]);

  useEffect(() => {
    if (!recapMonths.length) {
      setSelectedMonthKey("");
      return;
    }

    setSelectedMonthKey((current) => {
      if (current && recapMonths.some((month) => month.monthKey === current)) {
        return current;
      }

      return recapMonths[recapMonths.length - 1]?.monthKey ?? "";
    });
  }, [recapMonths]);

  const analytics = useMemo(() => {
    const monthlyComparison = summary?.monthly_comparison ?? [];
    const currentMonthBucket =
      monthlyComparison.find((bucket) => bucket.month_key === currentMonthKey) ??
      monthlyComparison[monthlyComparison.length - 1];

    return {
      income: Number(currentMonthBucket?.income ?? 0),
      expenses: Number(currentMonthBucket?.expenses ?? 0),
      balance: Number(summary?.balance ?? 0),
      transactionCount: summary?.transaction_count ?? 0,
      topCategories:
        summary?.top_categories.map((category) => ({
          categoryId: category.category_id ?? `missing-${category.name}`,
          total: Number(category.total),
          name: category.name,
          color: category.color,
        })) ?? [],
      monthlyComparison:
        summary?.monthly_comparison.map((bucket) => ({
          month: bucket.month_label,
          income: Number(bucket.income),
          expenses: Number(bucket.expenses),
          net: Number(bucket.net),
          transactions: bucket.transactions,
        })) ?? [],
      accountBalances:
        summary?.account_balances.map((account) => ({
          accountId: account.account_id,
          name: account.name,
          total: Number(account.total),
          currency: account.currency,
        })) ?? [],
      dailyPacing:
        summary?.daily_pacing?.map((item) => ({
          day: item.day,
          current_month_cumulative: item.current_month_cumulative ? Number(item.current_month_cumulative) : null,
          previous_month_cumulative: item.previous_month_cumulative ? Number(item.previous_month_cumulative) : null,
        })) ?? [],
      expenseCategories:
        summary?.expense_categories?.map((category) => ({
          name: category.name,
          value: Number(category.total),
          fill: category.color,
        })) ?? [],
      savingsRate: summary?.savings_rate ?? 0,
    };
  }, [currentMonthKey, summary]);

  async function loadMonthlyRecap(forceRegenerate: boolean) {
    if (!selectedMonthKey) {
      const message = "Selecciona un mes antes de generar el recap.";
      setRecapError(message);
      toast(message, "error");
      return;
    }

    setRecapError(null);

    if (forceRegenerate) {
      setIsRegenerating(true);
    } else {
      setIsRecapLoading(true);
    }

    try {
      const nextRecap = forceRegenerate
        ? await apiRequest<InsightsMonthlyRecap>("/insights/monthly-recap/regenerate", {
            method: "POST",
            body: JSON.stringify({ month_key: selectedMonthKey } satisfies InsightsMonthlyRecapRegenerateRequest),
          })
        : await apiRequest<InsightsMonthlyRecap>(
            `/insights/monthly-recap?month_key=${encodeURIComponent(selectedMonthKey)}`,
          );

      setRecap(nextRecap);
      setIsRecapOpen(true);

      if (forceRegenerate) {
        toast(`Recap regenerated for ${nextRecap.month_label}`, "success");
      } else if (nextRecap.is_stale) {
        toast("Opened cached recap. Regenerate to refresh it.", "info");
      }
    } catch (requestError) {
      const message =
        requestError instanceof Error ? requestError.message : "No se pudo generar el recap";
      setRecapError(message);
      toast(message, "error");
    } finally {
      if (forceRegenerate) {
        setIsRegenerating(false);
      } else {
        setIsRecapLoading(false);
      }
    }
  }

  const metricCards = [
    {
      title: "Balance total",
      value: <AmountValue amount={analytics.balance} currency="EUR" className="text-2xl" />,
      description: `${analytics.accountBalances.length} cuentas`,
      icon: <Wallet className="h-5 w-5" />,
      accentClass: "text-[var(--app-accent)]",
      bgClass: "bg-[var(--app-accent-soft)]",
    },
    {
      title: "Ingresos",
      value: <AmountValue amount={analytics.income} currency="EUR" className="text-2xl" />,
      description: periodLabel,
      icon: <TrendingUp className="h-5 w-5" />,
      accentClass: "text-[var(--app-success)]",
      bgClass: "bg-[var(--app-success-soft)]",
    },
    {
      title: "Gastos",
      value: <AmountValue amount={-analytics.expenses} currency="EUR" className="text-2xl" />,
      description: periodLabel,
      icon: <TrendingDown className="h-5 w-5" />,
      accentClass: "text-[var(--app-danger)]",
      bgClass: "bg-[var(--app-danger-soft)]",
    },
    {
      title: "Transacciones",
      value: String(analytics.transactionCount),
      description: "Movimientos",
      icon: <CreditCard className="h-5 w-5" />,
      accentClass: "text-[var(--app-muted)]",
      bgClass: "bg-[var(--app-muted-surface)]",
    },
    {
      title: "Tasa de ahorro",
      value: `${analytics.savingsRate}%`,
      description: "Porcentaje mensual",
      icon: <TrendingUp className="h-5 w-5" />,
      accentClass: "text-[var(--app-accent)]",
      bgClass: "bg-[var(--app-accent-soft)]",
    },
    {
      title: "Salud Financiera",
      value: analytics.savingsRate >= 20 ? "Excelente" : analytics.savingsRate >= 10 ? "Buena" : "Mejorable",
      description: "Basado en ahorro",
      icon: <CreditCard className="h-5 w-5" />,
      accentClass: analytics.savingsRate >= 10 ? "text-[var(--app-success)]" : "text-[var(--app-danger)]",
      bgClass: analytics.savingsRate >= 10 ? "bg-[var(--app-success-soft)]" : "bg-[var(--app-danger-soft)]",
    },
  ];

  return (
    <div className="space-y-6">
      <header className="animate-slideUp">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--app-accent)]">
          Análisis
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Análisis financiero</h1>
        <p className="mt-2 text-sm text-[var(--app-muted)]">
          Resumen analítico de balances, categorías y tendencias sobre tus movimientos.
        </p>
      </header>

      {summaryError ? (
        <div className="animate-fadeIn rounded-2xl bg-[var(--app-danger-soft)] px-4 py-3 text-sm text-[var(--app-danger)]">
          {summaryError}
        </div>
      ) : null}

      {isLoading ? (
        <ListSkeleton rows={4} />
      ) : (
        <>
          <div className="grid gap-4 xl:grid-cols-2 xl:items-start">
            <MonthlyRecapLauncher
              compact
              months={recapMonths}
              selectedMonthKey={selectedMonthKey}
              onSelectedMonthKeyChange={setSelectedMonthKey}
              onPlay={() => void loadMonthlyRecap(false)}
              onRegenerate={() => void loadMonthlyRecap(true)}
              isLoading={isRecapLoading || isRegenerating}
              recap={recap}
              error={recapError}
            />

            <div className="grid gap-4 md:grid-cols-3">
              {metricCards.map((item, index) => (
                <Card key={item.title} className={`animate-slideUp stagger-${index + 1}`}>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-[var(--app-muted)]">{item.title}</CardTitle>
                    <div className={`flex h-8 w-8 items-center justify-center rounded-xl ${item.bgClass}`}>
                      <span className={item.accentClass}>{item.icon}</span>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{item.value}</div>
                    <p className="text-xs text-[var(--app-muted)]">{item.description}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          <div className="animate-slideUp stagger-4">
            <CumulativePacingChart data={analytics.dailyPacing} />
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <CategoryTreemap data={analytics.expenseCategories} />
            <CashFlowChart data={analytics.monthlyComparison} />
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
            <Card className="min-w-0 animate-slideUp stagger-6">
              <CardHeader>
                <CardTitle>Tendencia mensual</CardTitle>
                <CardDescription>Evolución del balance neto y número de movimientos por mes.</CardDescription>
              </CardHeader>
              <CardContent className="min-w-0">
                {analytics.monthlyComparison.length ? (
                  <ChartFrame>
                    <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                      <LineChart data={analytics.monthlyComparison} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--app-border)" />
                        <XAxis dataKey="month" tick={{ fill: "var(--app-muted)", fontSize: 12 }} />
                        <YAxis
                          tick={{ fill: "var(--app-muted)", fontSize: 12 }}
                          tickFormatter={(value) => compactCurrency(Number(value))}
                        />
                        <Tooltip
                          formatter={(value, name) => [
                            name === "transactions"
                              ? String(Number(value ?? 0))
                              : formatCurrency(Number(value ?? 0), "EUR"),
                            name === "net" ? "Neto" : "Movimientos",
                          ]}
                          contentStyle={tooltipStyle}
                        />
                        <Line
                          type="monotone"
                          dataKey="net"
                          stroke={chartPalette.accent}
                          strokeWidth={3}
                          dot={{ r: 3, fill: chartPalette.accent, stroke: chartPalette.accent }}
                          activeDot={{ r: 5, fill: chartPalette.accent, stroke: chartPalette.accent }}
                          name="net"
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </ChartFrame>
                ) : (
                  <p className="text-sm text-[var(--app-muted)]">
                    Crea más actividad para ver la tendencia temporal.
                  </p>
                )}
              </CardContent>
            </Card>

            <Card className="min-w-0 animate-slideUp stagger-6">
              <CardHeader>
                <CardTitle>Saldos por cuenta</CardTitle>
                <CardDescription>Balance agregado actual por cuenta activa.</CardDescription>
              </CardHeader>
              <CardContent className="min-w-0 space-y-4">
                {analytics.accountBalances.length ? (
                  <>
                    <ChartFrame heightClassName="h-[240px] sm:h-[280px]">
                      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                        <BarChart
                          data={analytics.accountBalances}
                          layout="vertical"
                          margin={{ top: 4, right: 16, left: 8, bottom: 4 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="var(--app-border)" horizontal={false} />
                          <XAxis
                            type="number"
                            tick={{ fill: "var(--app-muted)", fontSize: 12 }}
                            tickFormatter={(value) => compactCurrency(Number(value))}
                          />
                          <YAxis type="category" dataKey="name" width={90} tick={{ fill: "var(--app-ink)", fontSize: 12 }} />
                          <Tooltip
                            formatter={(value, _name, item) => [
                              formatCurrency(Number(value ?? 0), String(item.payload.currency ?? "EUR")),
                              "Saldo",
                            ]}
                            contentStyle={tooltipStyle}
                          />
                          <Bar dataKey="total" radius={[0, 8, 8, 0]}>
                            {analytics.accountBalances.map((account) => (
                              <Cell
                                key={account.accountId}
                                fill={
                                  account.total > 0
                                    ? chartPalette.success
                                    : account.total < 0
                                      ? chartPalette.danger
                                      : chartPalette.muted
                                }
                              />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </ChartFrame>

                    <div className="space-y-3">
                      {analytics.accountBalances.map((account) => (
                        <div
                          key={account.accountId}
                          className="flex items-center justify-between rounded-xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-4 py-3 transition-colors hover:bg-[var(--app-muted-surface)]"
                        >
                          <span className="text-sm font-medium">{account.name}</span>
                          <AmountValue amount={account.total} currency={account.currency} />
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <p className="text-sm text-[var(--app-muted)]">
                    Sin movimientos suficientes para calcular saldos.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}

      {isRecapOpen && recap ? (
        <MonthlyRecapOverlay
          key={recap.source_fingerprint ?? recap.generated_at ?? recap.month_key}
          open={isRecapOpen}
          recap={recap}
          onClose={() => setIsRecapOpen(false)}
        />
      ) : null}
    </div>
  );
}

function normalizeRecapMonths(summary: InsightsSummaryWithRecapMonths | null): InsightsRecapMonth[] {
  const explicitMonths = summary?.available_recap_months;
  const rawMonths =
    explicitMonths && explicitMonths.length > 0 ? explicitMonths : summary?.monthly_comparison ?? [];
  const monthMap = new Map<string, InsightsRecapMonth>();

  for (const month of rawMonths) {
    const normalized = normalizeRecapMonth(month);

    if (normalized) {
      monthMap.set(normalized.monthKey, normalized);
    }
  }

  return Array.from(monthMap.values()).sort((left, right) => left.monthKey.localeCompare(right.monthKey));
}

function normalizeRecapMonth(
  month: InsightsRecapMonth | { month_key: string; month_label?: string } | string,
): InsightsRecapMonth | null {
  if (typeof month === "string") {
    const label = formatMonthKeyLabel(month);
    return {
      monthKey: month,
      label,
      month_key: month,
      month_label: label,
    };
  }

  if ("monthKey" in month && typeof month.monthKey === "string") {
    const label =
      "label" in month && typeof month.label === "string"
        ? month.label
        : formatMonthKeyLabel(month.monthKey);

    return {
      monthKey: month.monthKey,
      label,
      month_key: month.monthKey,
      month_label: label,
    };
  }

  if ("month_key" in month && typeof month.month_key === "string") {
    const label =
      "month_label" in month && typeof month.month_label === "string"
        ? month.month_label
        : formatMonthKeyLabel(month.month_key);

    return {
      monthKey: month.month_key,
      label,
      month_key: month.month_key,
      month_label: label,
    };
  }

  return null;
}

function formatMonthKeyLabel(monthKey: string) {
  const match = monthKey.match(/^(\d{4})-(\d{2})$/);
  if (!match) {
    return monthKey;
  }

  return formatMonthLabel(Number(match[1]), Number(match[2]));
}

const tooltipStyle: CSSProperties = {
  backgroundColor: "var(--app-panel)",
  border: "1px solid var(--app-border)",
  borderRadius: "12px",
  padding: "8px 12px",
  boxShadow: "var(--app-shadow-elevated)",
  fontSize: "13px",
};

function ChartFrame({
  children,
  heightClassName = "h-[260px] sm:h-[320px]",
}: {
  children: ReactNode;
  heightClassName?: string;
}) {
  const frameRef = useRef<HTMLDivElement | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const node = frameRef.current;

    if (!node) {
      return;
    }

    const updateReadiness = () => {
      const { width, height } = node.getBoundingClientRect();
      setIsReady(width > 0 && height > 0);
    };

    updateReadiness();

    const observer = new ResizeObserver(() => {
      updateReadiness();
    });

    observer.observe(node);
    window.requestAnimationFrame(updateReadiness);

    return () => {
      observer.disconnect();
    };
  }, []);

  return (
    <div ref={frameRef} className={`min-h-[240px] w-full min-w-0 ${heightClassName}`}>
      {isReady ? children : null}
    </div>
  );
}

function compactCurrency(value: number) {
  if (!Number.isFinite(value)) {
    return "";
  }

  if (Math.abs(value) >= 1000) {
    return `${Math.round(value / 1000)}k`;
  }

  return String(Math.round(value));
}

function withOpacity(color: string, alpha: number) {
  const normalized = color.replace("#", "");

  if (normalized.length !== 6) {
    return `rgba(148, 163, 184, ${alpha})`;
  }

  const value = Number.parseInt(normalized, 16);
  const red = (value >> 16) & 255;
  const green = (value >> 8) & 255;
  const blue = value & 255;

  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}
