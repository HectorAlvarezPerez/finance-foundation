"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowRight, BarChart2, CreditCard, PiggyBank, TrendingDown, TrendingUp, Wallet } from "lucide-react";

import { AmountValue } from "@/components/amount-value";
import { CategoryBadge } from "@/components/category-badge";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { DashboardSkeleton } from "@/components/ui/skeleton";
import { apiRequest } from "@/lib/api";
import { formatDate, formatMonthLabel } from "@/lib/format";
import type { Account, Budget, Category, InsightsSummary, PaginatedResponse, Transaction } from "@/lib/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type DashboardState = {
  accounts: PaginatedResponse<Account> | null;
  categories: PaginatedResponse<Category> | null;
  recentTransactions: PaginatedResponse<Transaction> | null;
  budgets: PaginatedResponse<Budget> | null;
  insights: InsightsSummary | null;
};

export default function DashboardPage() {
  const [state, setState] = useState<DashboardState>({
    accounts: null,
    categories: null,
    recentTransactions: null,
    budgets: null,
    insights: null,
  });
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const today = useMemo(() => new Date(), []);
  const currentYear = today.getFullYear();
  const currentMonth = today.getMonth() + 1;
  const currentMonthKey = `${currentYear}-${String(currentMonth).padStart(2, "0")}`;
  const currentMonthLabel = formatMonthLabel(currentYear, currentMonth);

  useEffect(() => {
    async function load() {
      try {
        const [accounts, categories, recentTransactions, budgets, insights] = await Promise.all([
          apiRequest<PaginatedResponse<Account>>("/accounts?limit=100"),
          apiRequest<PaginatedResponse<Category>>("/categories?limit=100"),
          apiRequest<PaginatedResponse<Transaction>>("/transactions?limit=100&sort_by=date&sort_order=desc"),
          apiRequest<PaginatedResponse<Budget>>(
            `/budgets?limit=100&year=${currentYear}&month=${currentMonth}&sort_by=amount&sort_order=desc`,
          ),
          apiRequest<InsightsSummary>("/insights/summary"),
        ]);
        setState({ accounts, categories, recentTransactions, budgets, insights });
      } catch (requestError) {
        setError(requestError instanceof Error ? requestError.message : "No se pudo cargar el dashboard");
      } finally {
        setIsLoading(false);
      }
    }

    void load();
  }, [currentMonth, currentYear]);

  const accountMap = new Map(state.accounts?.items.map((account) => [account.id, account]) ?? []);
  const categoryMap = new Map(state.categories?.items.map((category) => [category.id, category]) ?? []);
  const defaultCurrency = state.accounts?.items[0]?.currency ?? "EUR";

  const totals = useMemo(() => {
    const monthBucket = state.insights?.monthly_comparison.find((bucket) => bucket.month_key === currentMonthKey);
    const balanceByAccount = new Map(
      state.insights?.account_balances.map((account) => [account.account_id, Number(account.total)]) ?? [],
    );

    return {
      income: Number(monthBucket?.income ?? 0),
      expenses: Number(monthBucket?.expenses ?? 0),
      netWorth: (state.accounts?.items ?? []).reduce(
        (sum, account) => sum + (balanceByAccount.get(account.id) ?? 0),
        0,
      ),
      activeBudgetCount: state.budgets?.items.length ?? 0,
    };
  }, [currentMonthKey, state.accounts, state.budgets, state.insights]);

  const summary = [
    {
      label: "Patrimonio total",
      value: <AmountValue amount={totals.netWorth} currency={defaultCurrency} className="text-2xl" />,
      detail: `${state.accounts?.total ?? 0} cuentas`,
      icon: <Wallet className="h-5 w-5" />,
      accentClass: "text-[var(--app-accent)]",
      bgClass: "bg-[var(--app-accent-soft)]",
    },
    {
      label: "Ingresos del mes",
      value: <AmountValue amount={totals.income} currency={defaultCurrency} className="text-2xl" />,
      detail: currentMonthLabel,
      icon: <TrendingUp className="h-5 w-5" />,
      accentClass: "text-[var(--app-success)]",
      bgClass: "bg-[var(--app-success-soft)]",
    },
    {
      label: "Gastos del mes",
      value: <AmountValue amount={-totals.expenses} currency={defaultCurrency} className="text-2xl" />,
      detail: currentMonthLabel,
      icon: <TrendingDown className="h-5 w-5" />,
      accentClass: "text-[var(--app-danger)]",
      bgClass: "bg-[var(--app-danger-soft)]",
    },
    {
      label: "Presupuestos",
      value: String(totals.activeBudgetCount),
      detail: `Activos en ${currentMonthLabel}`,
      icon: <PiggyBank className="h-5 w-5" />,
      accentClass: "text-[var(--app-warning)]",
      bgClass: "bg-[var(--app-warning-soft)]",
    },
  ];

  return (
    <div>
      <PageHeader
        eyebrow="Dashboard"
        title="Resumen general"
        description="Una vista rápida de tus cuentas, actividad reciente y presupuestos del mes actual."
      />

      {error ? (
        <div className="animate-fadeIn mb-6 rounded-2xl bg-[var(--app-danger-soft)] px-4 py-3 text-sm text-[var(--app-danger)]">
          {error}
        </div>
      ) : null}

      {isLoading ? (
        <DashboardSkeleton />
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {summary.map((item, index) => (
              <Card key={item.label} className={`animate-slideUp stagger-${index + 1}`}>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-[var(--app-muted)]">{item.label}</CardTitle>
                  <div className={`flex h-8 w-8 items-center justify-center rounded-xl ${item.bgClass}`}>
                    <span className={item.accentClass}>{item.icon}</span>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{item.value}</div>
                  <p className="mt-1 text-xs text-[var(--app-muted)]">{item.detail}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="mt-8 grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
            <Card className="animate-slideUp stagger-5">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Últimas transacciones</CardTitle>
                <Link href="/app/transactions" className="inline-flex items-center gap-1 text-sm font-medium text-[var(--app-accent)] transition-colors hover:brightness-110">
                  Ver todas
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </CardHeader>
              <CardContent className="space-y-3">
                {state.recentTransactions?.items.length ? (
                  state.recentTransactions.items.slice(0, 8).map((transaction) => (
                    <div
                      key={transaction.id}
                      className="flex items-center justify-between gap-3 rounded-xl px-3 py-2 transition-colors hover:bg-[var(--app-muted-surface)]"
                    >
                      <div className="min-w-0 flex-1 space-y-0.5">
                        <p className="truncate text-sm font-medium">{transaction.description}</p>
                        <div className="flex items-center gap-2">
                          <p className="text-xs text-[var(--app-muted)]">
                            {accountMap.get(transaction.account_id)?.name ?? "Cuenta"}
                          </p>
                          <CategoryBadge category={categoryMap.get(transaction.category_id ?? "")} />
                        </div>
                      </div>
                      <div className="text-right shrink-0">
                        <AmountValue
                          amount={transaction.amount}
                          currency={transaction.currency}
                          className="text-sm"
                        />
                        <p className="mt-0.5 text-[11px] text-[var(--app-muted)]">{formatDate(transaction.date)}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <EmptyState
                    title="Aún no hay transacciones"
                    description="Crea tu primera transacción para ver tus movimientos aquí."
                    icon={CreditCard}
                    actionLabel="Crear transacción"
                    actionHref="/app/transactions"
                    variant="plain"
                  />
                )}
              </CardContent>
            </Card>

            <div className="space-y-6">
              <Card className="animate-slideUp stagger-6">
                <CardHeader className="flex flex-row items-center justify-between gap-4">
                  <CardTitle>Presupuestos activos</CardTitle>
                  <Link href="/app/budgets" className="text-sm font-medium text-[var(--app-accent)]">
                    Ver todos
                  </Link>
                </CardHeader>
                <CardContent className="space-y-3">
                  {state.budgets?.items.length ? (
                    state.budgets.items.slice(0, 3).map((budget) => (
                      <div
                        key={budget.id}
                        className="rounded-xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-4 py-3"
                      >
                        <CategoryBadge category={categoryMap.get(budget.category_id)} fallback="Categoría" />
                        <div className="mt-1.5 flex items-center justify-between gap-4 text-sm text-[var(--app-muted)]">
                          <span>{formatMonthLabel(budget.year, budget.month)}</span>
                          <AmountValue amount={budget.amount} currency={budget.currency} />
                        </div>
                      </div>
                    ))
                  ) : (
                    <EmptyState
                      title="Sin presupuestos"
                      description={`No hay presupuestos para ${currentMonthLabel}.`}
                      icon={PiggyBank}
                      actionLabel="Crear presupuesto"
                      actionHref="/app/budgets"
                      variant="plain"
                    />
                  )}
                </CardContent>
              </Card>

              <Card className="animate-slideUp stagger-6">
                <CardHeader>
                  <CardTitle>Acciones rápidas</CardTitle>
                  <CardDescription>Atajos para mantener el producto en movimiento.</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-2">
                  {[
                    {
                      href: "/app/transactions",
                      label: "Crear una transacción",
                      icon: <CreditCard className="h-4 w-4" />,
                      accentVar: "var(--app-accent)",
                      bgVar: "var(--app-accent-soft)",
                      borderVar: "var(--app-accent)",
                    },
                    {
                      href: "/app/budgets",
                      label: "Configurar presupuestos",
                      icon: <PiggyBank className="h-4 w-4" />,
                      accentVar: "var(--app-warning)",
                      bgVar: "var(--app-warning-soft)",
                      borderVar: "var(--app-warning)",
                    },
                    {
                      href: "/app/insights",
                      label: "Abrir análisis financiero",
                      icon: <BarChart2 className="h-4 w-4" />,
                      accentVar: "var(--app-success)",
                      bgVar: "var(--app-success-soft)",
                      borderVar: "var(--app-success)",
                    },
                  ].map((action) => (
                    <Link
                      key={action.href}
                      href={action.href}
                      style={{
                        borderLeftColor: action.borderVar,
                        // @ts-expect-error CSS custom property
                        "--action-accent": action.accentVar,
                        "--action-bg": action.bgVar,
                      }}
                      className="group flex items-center justify-between gap-3 rounded-xl border border-[var(--app-border)] border-l-[3px] px-4 py-3 text-sm font-medium transition-all hover:bg-[var(--action-bg,var(--app-accent-soft))] hover:border-[var(--app-border)]"
                    >
                      <span
                        className="flex items-center gap-3"
                        style={{ color: action.accentVar }}
                      >
                        <span
                          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg"
                          style={{ background: action.bgVar }}
                        >
                          {action.icon}
                        </span>
                        <span className="text-[var(--app-ink)]">{action.label}</span>
                      </span>
                      <ArrowRight
                        className="h-4 w-4 shrink-0 transition-transform group-hover:translate-x-0.5"
                        style={{ color: action.accentVar }}
                      />
                    </Link>
                  ))}
                </CardContent>
              </Card>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
