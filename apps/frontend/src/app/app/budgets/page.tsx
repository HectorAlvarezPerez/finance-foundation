"use client";

import { FormEvent, useEffect, useEffectEvent, useMemo, useRef, useState } from "react";
import { MoreVertical, Pencil, PiggyBank, Plus, Trash2 } from "lucide-react";

import { AmountValue } from "@/components/amount-value";
import { CategoryBadge } from "@/components/category-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { ListSkeleton, CardSkeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/page-header";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Modal } from "@/components/ui/modal";
import { PaginationControls } from "@/components/ui/pagination-controls";
import { useToast } from "@/components/ui/toast";
import { useSettings } from "@/components/settings-provider";
import { apiRequest } from "@/lib/api";
import { formatMonthLabel } from "@/lib/format";
import type {
  Budget,
  BudgetBulkCreateResponse,
  Category,
  PaginatedResponse,
  Transaction,
} from "@/lib/types";

type BudgetFormState = {
  category_id: string;
  year: string;
  scope: "single" | "year" | "annual";
  month: string;
  currency: string;
  amount: string;
};

const MONTH_OPTIONS = Array.from({ length: 12 }, (_, index) => ({
  value: String(index + 1),
  label: formatMonthLabel(2026, index + 1),
}));

function getBudgetPeriodLabel(budget: Pick<Budget, "period_type" | "year" | "month">): string {
  if (budget.period_type === "annual") {
    return `Anual ${budget.year}`;
  }

  return formatMonthLabel(budget.year, budget.month ?? 1);
}

function getBudgetSpendKey(budget: Pick<Budget, "category_id" | "period_type" | "year" | "month">): string {
  if (budget.period_type === "annual") {
    return `${budget.category_id}-${budget.year}-annual`;
  }

  return `${budget.category_id}-${budget.year}-monthly-${budget.month ?? 1}`;
}

export default function BudgetsPage() {
  const { toast } = useToast();
  const { settings } = useSettings();
  const currentYear = new Date().getFullYear();
  const currentMonth = new Date().getMonth() + 1;
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedYear, setSelectedYear] = useState(String(currentYear));
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingBudgetId, setEditingBudgetId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [confirmDelete, setConfirmDelete] = useState<{ open: boolean; budgetId: string | null; label: string }>({
    open: false,
    budgetId: null,
    label: "",
  });
  const [form, setForm] = useState<BudgetFormState>({
    category_id: "",
    year: String(currentYear),
    scope: "single",
    month: String(currentMonth),
    currency: settings?.default_currency || "EUR",
    amount: "",
  });
  const pageSize = 8;

  const categoryMap = useMemo(
    () => new Map(categories.map((category) => [category.id, category])),
    [categories],
  );

  async function loadAll(year: string) {
    try {
      const [budgetsResponse, categoriesResponse, transactionsResponse] = await Promise.all([
        apiRequest<PaginatedResponse<Budget>>(`/budgets?limit=100&year=${year}&sort_by=month&sort_order=asc`),
        apiRequest<PaginatedResponse<Category>>("/categories?limit=100&category_type=expense&sort_by=name&sort_order=asc"),
        apiRequest<PaginatedResponse<Transaction>>(
          `/transactions?limit=100&category_type=expense&date_from=${year}-01-01&date_to=${year}-12-31&sort_by=date&sort_order=desc`,
        ),
      ]);

      setBudgets(budgetsResponse.items);
      setCategories(categoriesResponse.items);
      setTransactions(transactionsResponse.items);
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No se pudieron cargar los presupuestos");
    } finally {
      setIsLoading(false);
    }
  }

  const loadBudgetsOnMount = useEffectEvent(async () => {
    await loadAll(selectedYear);
  });

  useEffect(() => {
    void loadBudgetsOnMount();
  }, [selectedYear]);

  useEffect(() => {
    setPage(1);
  }, [selectedYear]);

  const budgetCards = useMemo(() => {
    const spentByBudgetKey = new Map<string, number>();

    transactions.forEach((transaction) => {
      if (!transaction.category_id) return;
      const amount = Number(transaction.amount);
      if (amount >= 0) return;
      const transactionDate = new Date(transaction.date);
      const monthlyKey = `${transaction.category_id}-${transactionDate.getFullYear()}-monthly-${transactionDate.getMonth() + 1}`;
      const annualKey = `${transaction.category_id}-${transactionDate.getFullYear()}-annual`;
      spentByBudgetKey.set(monthlyKey, (spentByBudgetKey.get(monthlyKey) ?? 0) + Math.abs(amount));
      spentByBudgetKey.set(annualKey, (spentByBudgetKey.get(annualKey) ?? 0) + Math.abs(amount));
    });

    return budgets
      .map((budget) => {
        const amount = Number(budget.amount);
        const key = getBudgetSpendKey(budget);
        const spent = spentByBudgetKey.get(key) ?? 0;
        const remaining = amount - spent;
        const usageRatio = amount > 0 ? spent / amount : 0;
        const usagePercent = usageRatio * 100;
        const category = categoryMap.get(budget.category_id);

        let statusLabel = "OK";
        let tone = "ok" as "ok" | "warning" | "danger";

        if (usagePercent > 100) {
          statusLabel = "Superado";
          tone = "danger";
        } else if (usagePercent >= 85) {
          statusLabel = "Al límite";
          tone = "warning";
        }

        return { ...budget, amountNumber: amount, spent, remaining, usagePercent, statusLabel, tone, category };
      })
      .sort((left, right) => {
        if (left.period_type !== right.period_type) return left.period_type === "annual" ? -1 : 1;
        if ((left.month ?? 0) !== (right.month ?? 0)) return (left.month ?? 0) - (right.month ?? 0);
        return (left.category?.name ?? "").localeCompare(right.category?.name ?? "", "es");
      });
  }, [budgets, categoryMap, transactions]);

  const summary = useMemo(() => {
    const totalBudgeted = budgetCards.reduce((sum, item) => sum + item.amountNumber, 0);
    const totalSpent = budgetCards.reduce((sum, item) => sum + item.spent, 0);
    const totalAvailable = totalBudgeted - totalSpent;
    return { totalBudgeted, totalSpent, totalAvailable };
  }, [budgetCards]);

  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(budgetCards.length / pageSize));
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [budgetCards.length, page, pageSize]);

  const visibleBudgetCards = budgetCards.slice((page - 1) * pageSize, page * pageSize);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    try {
      if (editingBudgetId) {
        await apiRequest<Budget>(`/budgets/${editingBudgetId}`, {
          method: "PATCH",
          body: JSON.stringify({
            category_id: form.category_id,
            year: Number(form.year),
            period_type: form.scope === "annual" ? "annual" : "monthly",
            month: form.scope === "annual" ? null : Number(form.month),
            currency: form.currency,
            amount: form.amount,
          }),
        });
        toast("Presupuesto actualizado", "success");
      } else if (form.scope === "annual") {
        await apiRequest<Budget>("/budgets", {
          method: "POST",
          body: JSON.stringify({
            category_id: form.category_id,
            year: Number(form.year),
            period_type: "annual",
            month: null,
            currency: form.currency,
            amount: form.amount,
          }),
        });
        toast("Presupuesto anual creado", "success");
      } else if (form.scope === "year") {
        await apiRequest<BudgetBulkCreateResponse>("/budgets/bulk", {
          method: "POST",
          body: JSON.stringify({
            category_id: form.category_id,
            year: Number(form.year),
            months: MONTH_OPTIONS.map((option) => Number(option.value)),
            currency: form.currency,
            amount: form.amount,
          }),
        });
        toast("Presupuestos anuales creados", "success");
      } else {
        await apiRequest<Budget>("/budgets", {
          method: "POST",
          body: JSON.stringify({
            category_id: form.category_id,
            year: Number(form.year),
            period_type: "monthly",
            month: Number(form.month),
            currency: form.currency,
            amount: form.amount,
          }),
        });
        toast("Presupuesto creado", "success");
      }

      setSelectedYear(form.year);
      setEditingBudgetId(null);
      setForm({
        category_id: "",
        year: form.year,
        scope: "single",
        month: String(currentMonth),
        currency: settings?.default_currency || "EUR",
        amount: "",
      });
      setIsDialogOpen(false);
      await loadAll(form.year);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : editingBudgetId
            ? "No se pudo actualizar el presupuesto"
            : "No se pudo crear el presupuesto",
      );
    }
  }

  function openCreateDialog() {
    setEditingBudgetId(null);
    setError(null);
    setForm({
      category_id: "",
      year: selectedYear,
      scope: "single",
      month: String(currentMonth),
      currency: settings?.default_currency || "EUR",
      amount: "",
    });
    setIsDialogOpen(true);
  }

  function openEditDialog(budget: (typeof budgetCards)[number]) {
    setEditingBudgetId(budget.id);
    setError(null);
    setForm({
      category_id: budget.category_id,
      year: String(budget.year),
      scope: budget.period_type === "annual" ? "annual" : "single",
      month: String(budget.month ?? currentMonth),
      currency: budget.currency,
      amount: String(budget.amount),
    });
    setIsDialogOpen(true);
  }

  async function handleDeleteConfirmed() {
    if (!confirmDelete.budgetId) {
      return;
    }

    const budgetId = confirmDelete.budgetId;
    const year = selectedYear;
    setConfirmDelete({ open: false, budgetId: null, label: "" });
    setError(null);

    try {
      await apiRequest<void>(`/budgets/${budgetId}`, {
        method: "DELETE",
        skipJson: true,
      });
      toast("Presupuesto eliminado", "success");
      await loadAll(year);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No se pudo eliminar el presupuesto");
    }
  }

  const inputClasses = "w-full rounded-xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-4 py-2.5 outline-none transition-all focus:border-[var(--app-accent)] focus:shadow-[0_0_0_3px_var(--app-accent-soft)]";

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Presupuestos"
        title="Control de presupuestos"
        description="Sigue el gasto real frente a objetivos mensuales y anuales con una vista mucho más clara y útil."
      />

      <div className="flex flex-col items-start justify-between gap-2.5 sm:flex-row sm:items-center">
        <div className="flex items-center gap-2.5">
          <label className="text-xs font-medium uppercase tracking-[0.08em] text-[var(--app-muted)]" htmlFor="budget-year">Año</label>
          <select
            id="budget-year"
            value={selectedYear}
            onChange={(event) => {
              setSelectedYear(event.target.value);
              setForm((current) => ({ ...current, year: event.target.value }));
            }}
            className="rounded-xl border border-[var(--app-border)] bg-[var(--app-panel)] px-3.5 py-2 text-sm outline-none transition-all focus:border-[var(--app-accent)]"
          >
            {[currentYear - 1, currentYear, currentYear + 1].map((year) => (
              <option key={year} value={String(year)}>{year}</option>
            ))}
          </select>
        </div>

        <button
          type="button"
          onClick={openCreateDialog}
          className="inline-flex items-center gap-2 rounded-xl bg-[var(--app-accent)] px-3.5 py-2 text-sm font-medium text-white transition-all hover:brightness-110"
        >
          <Plus className="h-4 w-4" />
          Nuevo presupuesto
        </button>
      </div>

      {isLoading ? (
        <div className="grid gap-4 lg:grid-cols-3">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : (
        <section className="grid gap-3 lg:grid-cols-3">
          <SummaryCard title="Total presupuestado" value={summary.totalBudgeted} currency={settings?.default_currency || "EUR"} tone="neutral" />
          <SummaryCard title="Total gastado" value={summary.totalSpent} currency={settings?.default_currency || "EUR"} tone="danger" />
          <SummaryCard title="Disponible" value={summary.totalAvailable} currency={settings?.default_currency || "EUR"} tone={summary.totalAvailable >= 0 ? "success" : "danger"} />
        </section>
      )}

      <Modal
        open={isDialogOpen}
        onClose={() => {
          setIsDialogOpen(false);
          setEditingBudgetId(null);
        }}
        title={editingBudgetId ? "Editar presupuesto" : "Nuevo presupuesto"}
        description={
          editingBudgetId
            ? "Ajusta el objetivo del presupuesto y deja el resto alineado con tu planificación."
            : "Puedes crearlo para un mes concreto, para todo el año mes a mes o como objetivo anual único."
        }
      >
        <form className="space-y-4" onSubmit={handleSubmit}>
          <select required aria-label="Categoría del presupuesto" value={form.category_id} onChange={(event) => setForm((current) => ({ ...current, category_id: event.target.value }))} className={inputClasses}>
            <option value="">Selecciona categoría</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>{category.name}</option>
            ))}
          </select>
          <div className="grid gap-4 sm:grid-cols-2">
            <input required aria-label="Año del presupuesto" type="number" min={2000} max={2100} value={form.year} onChange={(event) => setForm((current) => ({ ...current, year: event.target.value }))} className={inputClasses} />
            <select aria-label="Alcance del presupuesto" disabled={!!editingBudgetId} value={form.scope} onChange={(event) => setForm((current) => ({ ...current, scope: event.target.value as BudgetFormState["scope"] }))} className={`${inputClasses} disabled:cursor-not-allowed disabled:opacity-60`}>
              <option value="single">Un mes concreto</option>
              <option value="year">Todos los meses del año</option>
              <option value="annual">Total anual</option>
            </select>
          </div>
          {form.scope === "single" ? (
            <select aria-label="Mes del presupuesto" value={form.month} onChange={(event) => setForm((current) => ({ ...current, month: event.target.value }))} className={inputClasses}>
              {MONTH_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          ) : form.scope === "year" ? (
            <div className="rounded-xl bg-[var(--app-accent-soft)] px-4 py-3 text-sm text-[var(--app-accent)]">
              Se crearán 12 presupuestos, uno para cada mes del año seleccionado.
            </div>
          ) : (
            <div className="rounded-xl bg-[var(--app-accent-soft)] px-4 py-3 text-sm text-[var(--app-accent)]">
              Se creará un único presupuesto anual para todo el año seleccionado.
            </div>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <input required aria-label="Divisa del presupuesto" value={form.currency} maxLength={3} onChange={(event) => setForm((current) => ({ ...current, currency: event.target.value.toUpperCase() }))} className={`${inputClasses} uppercase`} />
            <input required aria-label="Importe del presupuesto" value={form.amount} onChange={(event) => setForm((current) => ({ ...current, amount: event.target.value }))} placeholder="120.00" className={inputClasses} />
          </div>
          {error ? <p className="text-sm text-[var(--app-danger)]">{error}</p> : null}
          <button type="submit" className="inline-flex w-full items-center justify-center rounded-xl bg-[var(--app-accent)] px-4 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110">
            {editingBudgetId
              ? "Guardar cambios"
              : form.scope === "year"
                ? "Crear presupuestos mensuales"
                : form.scope === "annual"
                  ? "Crear presupuesto anual"
                  : "Crear presupuesto"}
          </button>
        </form>
      </Modal>

      <ConfirmDialog
        open={confirmDelete.open}
        title="Eliminar presupuesto"
        description={`¿Quieres eliminar el presupuesto de ${confirmDelete.label}? Esta acción no se puede deshacer.`}
        onConfirm={() => void handleDeleteConfirmed()}
        onCancel={() => setConfirmDelete({ open: false, budgetId: null, label: "" })}
      />

      {isLoading ? (
        <ListSkeleton rows={4} />
      ) : (
        <Card className="animate-slideUp">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg">Presupuestos de {selectedYear}</CardTitle>
              <p className="mt-1 text-xs text-[var(--app-muted)]">Cada tarjeta compara presupuesto y gasto real del mes.</p>
            </div>
            <div className="rounded-full bg-[var(--app-muted-surface)] px-2.5 py-1 text-xs text-[var(--app-muted)]">
              {budgetCards.length} total
            </div>
          </CardHeader>
          <CardContent>
            {budgetCards.length ? (
              <>
                <div className="grid gap-3 lg:grid-cols-2">
                  {visibleBudgetCards.map((budget, index) => (
                    <BudgetStatusCard
                      key={budget.id}
                      budget={budget}
                      index={index}
                      onEdit={() => openEditDialog(budget)}
                      onDelete={() =>
                        setConfirmDelete({
                          open: true,
                          budgetId: budget.id,
                          label: `${budget.category?.name ?? "Categoría"} · ${getBudgetPeriodLabel(budget)}`,
                        })
                      }
                    />
                  ))}
                </div>
                <PaginationControls page={page} pageSize={pageSize} total={budgetCards.length} onPageChange={setPage} className="mt-5" />
              </>
            ) : (
              <EmptyState
                title="No hay presupuestos todavía"
                description="Crea uno para un mes, para todo el año o como objetivo anual y empezarás a ver el progreso aquí."
                icon={PiggyBank}
                actionLabel="Nuevo presupuesto"
                onAction={openCreateDialog}
                variant="plain"
              />
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function SummaryCard({
  title,
  value,
  currency,
  tone,
}: {
  title: string;
  value: number;
  currency: string;
  tone: "neutral" | "success" | "danger";
}) {
  const toneClass =
    tone === "danger"
      ? "text-[var(--app-danger)]"
      : tone === "success"
        ? "text-[var(--app-success)]"
        : "text-[var(--app-ink)]";

  return (
    <Card className="animate-slideUp">
      <CardHeader className="pb-2.5">
        <CardTitle className="text-xs font-medium uppercase tracking-[0.14em] text-[var(--app-muted)]">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className={`text-2xl font-semibold sm:text-[1.75rem] ${toneClass}`}>
          <AmountValue amount={value} currency={currency} className="![color:inherit]" />
        </p>
      </CardContent>
    </Card>
  );
}

function BudgetStatusCard({
  budget,
  index,
  onEdit,
  onDelete,
}: {
  budget: {
    id: string;
    category_id: string;
    period_type: "monthly" | "annual";
    year: number;
    month: number | null;
    currency: string;
    amount: string;
    amountNumber: number;
    spent: number;
    remaining: number;
    usagePercent: number;
    statusLabel: string;
    tone: "ok" | "warning" | "danger";
    category?: Category;
  };
  index: number;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const gradientClass =
    budget.tone === "danger"
      ? "from-[color-mix(in_srgb,var(--app-danger)_18%,transparent)] to-transparent"
      : budget.tone === "warning"
        ? "from-[color-mix(in_srgb,var(--app-warning)_16%,transparent)] to-transparent"
        : "from-[color-mix(in_srgb,var(--app-success)_14%,transparent)] to-transparent";

  const accentColor =
    budget.tone === "danger"
      ? "var(--app-danger)"
      : budget.tone === "warning"
        ? "var(--app-warning)"
        : "var(--app-success)";

  const progressClass =
    budget.tone === "danger"
      ? "bg-[var(--app-danger)]"
      : budget.tone === "warning"
        ? "bg-[var(--app-warning)]"
        : "bg-[var(--app-success)]";

  const statusBadgeClass =
    budget.tone === "danger"
      ? "border-[color-mix(in_srgb,var(--app-danger)_30%,transparent)] text-[var(--app-danger)] bg-[color-mix(in_srgb,var(--app-danger-soft)_55%,transparent)]"
      : budget.tone === "warning"
        ? "border-[color-mix(in_srgb,var(--app-warning)_35%,transparent)] text-[var(--app-warning)] bg-[color-mix(in_srgb,var(--app-warning-soft)_55%,transparent)]"
        : "border-[var(--app-border)] text-[var(--app-success)] bg-[color-mix(in_srgb,var(--app-success-soft)_55%,transparent)]";

  const footerClass = budget.remaining < 0 ? "text-[var(--app-danger)]" : "text-[var(--app-success)]";
  const progressWidth = `${Math.min(Math.max(budget.usagePercent, 0), 100)}%`;

  return (
    <div
      className={`animate-slideUp stagger-${Math.min(index + 1, 6)} relative overflow-hidden rounded-2xl border border-[var(--app-border)] bg-[var(--app-panel)] transition-shadow hover:shadow-[var(--app-shadow-elevated)] hover:z-10`}
    >
      {/* Colored gradient top band */}
      <div className={`absolute inset-x-0 top-0 h-24 bg-gradient-to-b ${gradientClass} pointer-events-none`} />

      <div className="relative">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 px-5 pt-5 pb-3">
          <div className="space-y-0.5">
            <p className="text-[11px] uppercase tracking-[0.1em] text-[var(--app-muted)]">
              {getBudgetPeriodLabel(budget)}
            </p>
            <h3 className="text-base font-semibold text-[var(--app-ink)]">
              {budget.category?.name ?? "Categoría"}
            </h3>
          </div>
          <div className="flex items-center gap-2 pt-0.5">
            <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${statusBadgeClass}`}>
              {budget.statusLabel}
            </span>
            <BudgetActionsMenu
              label={`${budget.category?.name ?? "Categoría"} ${getBudgetPeriodLabel(budget)}`}
              onEdit={onEdit}
              onDelete={onDelete}
            />
          </div>
        </div>

        {/* Big usage number + amounts row */}
        <div className="flex items-end justify-between gap-4 px-5 pb-4">
          <div>
            <p
              className="text-4xl font-black leading-none tabular-nums"
              style={{ color: accentColor }}
            >
              {budget.usagePercent.toFixed(0)}
              <span className="text-xl font-semibold">%</span>
            </p>
            <p className="mt-1 text-[11px] text-[var(--app-muted)]">usado</p>
          </div>
          <div className="grid grid-cols-2 gap-x-6 text-right">
            <div>
              <p className="text-[10px] uppercase tracking-[0.08em] text-[var(--app-muted)]">Presupuesto</p>
              <p className="mt-0.5 text-sm font-semibold text-[var(--app-ink)]">
                <AmountValue amount={budget.amountNumber} currency={budget.currency} className="!text-[var(--app-ink)]" />
              </p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-[0.08em] text-[var(--app-muted)]">Gastado</p>
              <p className="mt-0.5 text-sm font-semibold text-[var(--app-ink)]">
                <AmountValue amount={budget.spent} currency={budget.currency} className="!text-[var(--app-ink)]" />
              </p>
            </div>
          </div>
        </div>

        {/* Progress bar */}
        <div className="px-5 pb-4">
          <div className="h-2.5 overflow-hidden rounded-full bg-[color-mix(in_srgb,var(--app-muted-surface)_80%,transparent)]">
            <div
              className={`h-2.5 rounded-full transition-[width] duration-700 ease-out ${progressClass}`}
              style={{ width: progressWidth, animation: "progressFill 800ms ease-out" }}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-[var(--app-border)] px-5 py-3">
          <p className={`text-sm font-semibold ${footerClass}`}>
            {budget.remaining < 0 ? "Excedido" : "Disponible"}:{" "}
            <AmountValue amount={Math.abs(budget.remaining)} currency={budget.currency} className="![color:inherit]" />
          </p>
          <CategoryBadge category={budget.category} fallback="Categoría" variant="inline" />
        </div>
      </div>
    </div>
  );
}


function BudgetActionsMenu({
  label,
  onEdit,
  onDelete,
}: {
  label: string;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    function handleClick(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }

    document.addEventListener("click", handleClick);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("click", handleClick);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  function runAndClose(action: () => void) {
    action();
    setIsOpen(false);
  }

  return (
    <div ref={menuRef} className="relative z-30">
      <button
        type="button"
        onClick={() => setIsOpen((current) => !current)}
        className="rounded-lg p-1 text-[var(--app-muted)] transition-all hover:bg-[var(--app-muted-surface)]"
        aria-label={`Acciones de presupuesto ${label}`}
      >
        <MoreVertical className="h-4 w-4" />
      </button>
      {isOpen ? (
        <div className="animate-slideDown absolute right-0 z-[80] mt-1 min-w-40 rounded-xl border border-[var(--app-border)] bg-[var(--app-glass)] p-1 shadow-[var(--app-shadow-elevated)] backdrop-blur-xl">
          <button type="button" onClick={() => runAndClose(onEdit)} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-all hover:bg-[var(--app-muted-surface)]">
            <Pencil className="h-4 w-4" /> Editar
          </button>
          <button type="button" onClick={() => runAndClose(onDelete)} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-[var(--app-danger)] transition-all hover:bg-[var(--app-danger-soft)]">
            <Trash2 className="h-4 w-4" /> Eliminar
          </button>
        </div>
      ) : null}
    </div>
  );
}
