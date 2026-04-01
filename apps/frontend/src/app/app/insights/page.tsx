"use client";

import { useEffect, useMemo, useRef, useState } from "react";
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
import { ListSkeleton } from "@/components/ui/skeleton";
import { apiRequest } from "@/lib/api";
import { formatCurrency, formatMonthLabel } from "@/lib/format";
import type { InsightsSummary } from "@/lib/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const chartPalette = {
  success: "#34C759",
  danger: "#FF6B6B",
  accent: "#4F8CFF",
  muted: "#8E8E93",
};

export default function InsightsPage() {
  const [summary, setSummary] = useState<InsightsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const nextSummary = await apiRequest<InsightsSummary>("/insights/summary");
        setSummary(nextSummary);
        setError(null);
      } catch (requestError) {
        setError(requestError instanceof Error ? requestError.message : "No se pudo cargar el análisis");
      } finally {
        setIsLoading(false);
      }
    }

    void load();
  }, []);

  const today = new Date();
  const currentMonthKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;
  const periodLabel = formatMonthLabel(today.getFullYear(), today.getMonth() + 1);

  const analytics = useMemo(() => {
    const currentMonthBucket = summary?.monthly_comparison.find(
      (bucket) => bucket.month_key === currentMonthKey,
    );

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
    };
  }, [currentMonthKey, summary]);

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
      title: "Transacciones totales",
      value: String(analytics.transactionCount),
      description: "Movimientos analizados",
      icon: <CreditCard className="h-5 w-5" />,
      accentClass: "text-[var(--app-muted)]",
      bgClass: "bg-[var(--app-muted-surface)]",
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

      {error ? (
        <div className="animate-fadeIn rounded-2xl bg-[var(--app-danger-soft)] px-4 py-3 text-sm text-[var(--app-danger)]">
          {error}
        </div>
      ) : null}

      {isLoading ? (
        <ListSkeleton rows={4} />
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
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

          <div className="grid gap-6 xl:grid-cols-2">
            <Card className="min-w-0 animate-slideUp stagger-5">
              <CardHeader>
                <CardTitle>Gasto por categoría</CardTitle>
                <CardDescription>Top categorías ordenadas por volumen total de gasto.</CardDescription>
              </CardHeader>
              <CardContent className="min-w-0">
                {analytics.topCategories.length ? (
                  <ChartFrame>
                    <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                      <BarChart
                        data={analytics.topCategories.map((category) => ({
                          name: category.name,
                          total: category.total,
                          fill: category.color,
                        }))}
                        layout="vertical"
                        margin={{ top: 4, right: 16, left: 8, bottom: 4 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--app-border)" horizontal={false} />
                        <XAxis
                          type="number"
                          tick={{ fill: "var(--app-muted)", fontSize: 12 }}
                          tickFormatter={(value) => compactCurrency(Number(value))}
                        />
                        <YAxis
                          type="category"
                          dataKey="name"
                          width={90}
                          tick={{ fill: "var(--app-ink)", fontSize: 12 }}
                        />
                        <Tooltip
                          cursor={{ fill: "var(--app-muted-surface)" }}
                          formatter={(value) => [formatCurrency(Number(value ?? 0), "EUR"), "Gasto"]}
                          contentStyle={tooltipStyle}
                        />
                        <Bar dataKey="total" radius={[0, 8, 8, 0]}>
                          {analytics.topCategories.map((category) => (
                            <Cell key={category.categoryId} fill={withOpacity(category.color, 0.72)} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </ChartFrame>
                ) : (
                  <p className="text-sm text-[var(--app-muted)]">
                    Aún no hay suficiente actividad para mostrar categorías con gasto.
                  </p>
                )}
              </CardContent>
            </Card>

            <Card className="min-w-0 animate-slideUp stagger-5">
              <CardHeader>
                <CardTitle>Comparación mensual</CardTitle>
                <CardDescription>Ingresos y gastos de los últimos meses con datos reales.</CardDescription>
              </CardHeader>
              <CardContent className="min-w-0">
                {analytics.monthlyComparison.length ? (
                  <ChartFrame>
                    <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                      <BarChart data={analytics.monthlyComparison} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--app-border)" />
                        <XAxis dataKey="month" tick={{ fill: "var(--app-muted)", fontSize: 12 }} />
                        <YAxis tick={{ fill: "var(--app-muted)", fontSize: 12 }} tickFormatter={(value) => compactCurrency(Number(value))} />
                        <Tooltip
                          formatter={(value, name) => [
                            formatCurrency(Number(value ?? 0), "EUR"),
                            name === "income" ? "Ingresos" : "Gastos",
                          ]}
                          contentStyle={tooltipStyle}
                        />
                        <Legend
                          formatter={(value: string) => (value === "income" ? "Ingresos" : "Gastos")}
                          wrapperStyle={{ fontSize: 12 }}
                        />
                        <Bar dataKey="income" name="income" fill={chartPalette.success} radius={[8, 8, 0, 0]} />
                        <Bar dataKey="expenses" name="expenses" fill={chartPalette.danger} radius={[8, 8, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </ChartFrame>
                ) : (
                  <p className="text-sm text-[var(--app-muted)]">
                    No hay suficiente histórico para comparar meses.
                  </p>
                )}
              </CardContent>
            </Card>
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
                        <YAxis tick={{ fill: "var(--app-muted)", fontSize: 12 }} tickFormatter={(value) => compactCurrency(Number(value))} />
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
                          <XAxis type="number" tick={{ fill: "var(--app-muted)", fontSize: 12 }} tickFormatter={(value) => compactCurrency(Number(value))} />
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
                        <div key={account.accountId} className="flex items-center justify-between rounded-xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-4 py-3 transition-colors hover:bg-[var(--app-muted-surface)]">
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
    </div>
  );
}

const tooltipStyle: React.CSSProperties = {
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
  children: React.ReactNode;
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
