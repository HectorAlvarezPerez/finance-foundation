"use client";

import { FormEvent, useEffect, useEffectEvent, useMemo, useRef, useState } from "react";
import { GripVertical, MoreVertical, Pencil, PiggyBank, Plus, Receipt, Trash2 } from "lucide-react";

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
import { formatDate, formatMonthLabel, formatMonthName } from "@/lib/format";
import type {
  Budget,
  BudgetBatchDeleteResponse,
  Category,
  PaginatedResponse,
  Transaction,
} from "@/lib/types";

type BudgetSpendItem = {
  category_id: string;
  month: number;
  spent: string;
};

type BudgetSpendResponse = {
  year: number;
  items: BudgetSpendItem[];
};

type SortMode =
  | "manual"
  | "usage_desc"
  | "usage_asc"
  | "amount_desc"
  | "amount_asc"
  | "spent_desc"
  | "name_asc";

type PageSize = number | "all";

const SORT_OPTIONS: { value: SortMode; label: string }[] = [
  { value: "manual", label: "Orden manual" },
  { value: "usage_desc", label: "% usado (mayor primero)" },
  { value: "usage_asc", label: "% usado (menor primero)" },
  { value: "amount_desc", label: "Importe (mayor primero)" },
  { value: "amount_asc", label: "Importe (menor primero)" },
  { value: "spent_desc", label: "Gastado (mayor primero)" },
  { value: "name_asc", label: "Nombre (A-Z)" },
];

const PAGE_SIZE_OPTIONS = [10, 25, 50] as const;
const PAGE_SIZE_STORAGE_KEY = "budgets-page-size";

type BudgetFormState = {
  category_id: string;
  period_type: "monthly" | "annual";
  currency: string;
  amount: string;
};

type BudgetCard = {
  id: string;
  category_id: string;
  period_type: "monthly" | "annual";
  currency: string;
  amount: string;
  position: number;
  amountNumber: number;
  spent: number;
  remaining: number;
  usagePercent: number;
  statusLabel: string;
  tone: "ok" | "warning" | "danger";
  category?: Category;
};

const MONTH_OPTIONS = Array.from({ length: 12 }, (_, index) => ({
  value: String(index + 1),
  label: formatMonthName(index + 1),
}));

function getBudgetPeriodLabel(budget: Pick<Budget, "period_type">): string {
  return budget.period_type === "annual" ? "Anual (todo el año)" : "Mensual (cada mes)";
}

export default function BudgetsPage() {
  const { toast } = useToast();
  const { settings } = useSettings();
  const currentYear = new Date().getFullYear();
  const currentMonth = new Date().getMonth() + 1;
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [spendItems, setSpendItems] = useState<BudgetSpendItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedYear, setSelectedYear] = useState(String(currentYear));
  const [selectedMonth, setSelectedMonth] = useState(String(currentMonth));
  const [periodFilter, setPeriodFilter] = useState<"all" | "monthly" | "annual">("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [sortMode, setSortMode] = useState<SortMode>("manual");
  const [pageSize, setPageSize] = useState<PageSize>(10);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [confirmBatchDelete, setConfirmBatchDelete] = useState(false);
  const [breakdownBudget, setBreakdownBudget] = useState<BudgetCard | null>(null);
  const [breakdownTransactions, setBreakdownTransactions] = useState<Transaction[]>([]);
  const [isBreakdownLoading, setIsBreakdownLoading] = useState(false);
  const [draggingId, setDraggingId] = useState<string | null>(null);
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
    period_type: "monthly",
    currency: settings?.default_currency || "EUR",
    amount: "",
  });
  const categoryMap = useMemo(
    () => new Map(categories.map((category) => [category.id, category])),
    [categories],
  );

  useEffect(() => {
    const stored = window.localStorage.getItem(PAGE_SIZE_STORAGE_KEY);
    if (stored === "all") {
      setPageSize("all");
    } else if (stored && PAGE_SIZE_OPTIONS.some((option) => option === Number(stored))) {
      setPageSize(Number(stored));
    }
  }, []);

  async function loadAll(year: string) {
    try {
      const [budgetsResponse, categoriesResponse, spendResponse] = await Promise.all([
        apiRequest<PaginatedResponse<Budget>>("/budgets?limit=100&sort_by=position&sort_order=asc"),
        apiRequest<PaginatedResponse<Category>>("/categories?limit=100&category_type=expense&sort_by=name&sort_order=asc"),
        apiRequest<BudgetSpendResponse>(`/budgets/spend?year=${year}`),
      ]);

      setBudgets(budgetsResponse.items);
      setCategories(categoriesResponse.items);
      setSpendItems(spendResponse.items);
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No se pudieron cargar los presupuestos");
    } finally {
      setIsLoading(false);
    }
  }

  const loadBudgetsOnYear = useEffectEvent(async () => {
    await loadAll(selectedYear);
  });

  useEffect(() => {
    void loadBudgetsOnYear();
  }, [selectedYear]);

  useEffect(() => {
    setPage(1);
  }, [selectedYear, selectedMonth, periodFilter, categoryFilter, sortMode, pageSize]);

  // Spend per category derived from /budgets/spend for the selected year:
  // monthlySpent covers the selected month, ytdSpent the months up to and
  // including it, and annualSpent the whole year.
  const spentByCategory = useMemo(() => {
    const monthlySpent = new Map<string, number>();
    const ytdSpent = new Map<string, number>();
    const annualSpent = new Map<string, number>();
    const month = Number(selectedMonth);

    spendItems.forEach((item) => {
      const spent = Number(item.spent);
      if (!Number.isFinite(spent)) return;
      annualSpent.set(item.category_id, (annualSpent.get(item.category_id) ?? 0) + spent);
      if (item.month <= month) {
        ytdSpent.set(item.category_id, (ytdSpent.get(item.category_id) ?? 0) + spent);
      }
      if (item.month === month) {
        monthlySpent.set(item.category_id, (monthlySpent.get(item.category_id) ?? 0) + spent);
      }
    });

    return { monthlySpent, ytdSpent, annualSpent };
  }, [spendItems, selectedMonth]);

  // Cards for every budget (unfiltered) so KPIs stay stable across filters.
  const allBudgetCards = useMemo(() => {
    return budgets.map((budget) => {
      const amount = Number(budget.amount);
      const spent =
        budget.period_type === "annual"
          ? spentByCategory.annualSpent.get(budget.category_id) ?? 0
          : spentByCategory.monthlySpent.get(budget.category_id) ?? 0;
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
    });
  }, [budgets, categoryMap, spentByCategory]);

  const budgetCards = useMemo(() => {
    const filtered = allBudgetCards.filter(
      (budget) =>
        (periodFilter === "all" || budget.period_type === periodFilter) &&
        (categoryFilter === "all" || budget.category_id === categoryFilter),
    );

    const compare = (left: BudgetCard, right: BudgetCard): number => {
      switch (sortMode) {
        case "usage_desc":
          return right.usagePercent - left.usagePercent;
        case "usage_asc":
          return left.usagePercent - right.usagePercent;
        case "amount_desc":
          return right.amountNumber - left.amountNumber;
        case "amount_asc":
          return left.amountNumber - right.amountNumber;
        case "spent_desc":
          return right.spent - left.spent;
        case "name_asc":
          return (left.category?.name ?? "").localeCompare(right.category?.name ?? "", "es");
        default:
          return 0;
      }
    };

    return filtered.sort((left, right) => {
      const delta = compare(left, right);
      // Stable tiebreak (and manual order) by persisted position.
      return delta !== 0 ? delta : left.position - right.position;
    });
  }, [allBudgetCards, periodFilter, categoryFilter, sortMode]);

  const budgetCategories = useMemo(() => {
    const idsWithBudget = new Set(budgets.map((budget) => budget.category_id));
    return categories.filter((category) => idsWithBudget.has(category.id));
  }, [budgets, categories]);

  // KPIs are computed over ALL budgets, not the filtered view.
  const summary = useMemo(() => {
    let budgetedMonthly = 0;
    let budgetedAnnual = 0;
    let spentPeriod = 0;
    let monthlySpentTotal = 0;
    let ytdAndAnnualSpent = 0;

    allBudgetCards.forEach((budget) => {
      if (budget.period_type === "monthly") {
        const monthlySpent = spentByCategory.monthlySpent.get(budget.category_id) ?? 0;
        budgetedMonthly += budget.amountNumber;
        budgetedAnnual += budget.amountNumber * 12;
        spentPeriod += monthlySpent;
        monthlySpentTotal += monthlySpent;
        ytdAndAnnualSpent += spentByCategory.ytdSpent.get(budget.category_id) ?? 0;
      } else {
        const annualSpent = spentByCategory.annualSpent.get(budget.category_id) ?? 0;
        budgetedAnnual += budget.amountNumber;
        spentPeriod += annualSpent;
        ytdAndAnnualSpent += annualSpent;
      }
    });

    return {
      budgetedMonthly,
      budgetedAnnual,
      spentPeriod,
      availableMonth: budgetedMonthly - monthlySpentTotal,
      availableYear: budgetedAnnual - ytdAndAnnualSpent,
    };
  }, [allBudgetCards, spentByCategory]);

  const effectivePageSize = pageSize === "all" ? Math.max(budgetCards.length, 1) : pageSize;

  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(budgetCards.length / effectivePageSize));
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [budgetCards.length, page, effectivePageSize]);

  const visibleBudgetCards =
    pageSize === "all"
      ? budgetCards
      : budgetCards.slice((page - 1) * effectivePageSize, page * effectivePageSize);

  function handlePageSizeChange(value: string) {
    setPageSize(value === "all" ? "all" : Number(value));
    setPage(1);
    window.localStorage.setItem(PAGE_SIZE_STORAGE_KEY, value);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const body = JSON.stringify({
      category_id: form.category_id,
      period_type: form.period_type,
      currency: form.currency,
      amount: form.amount,
    });

    try {
      if (editingBudgetId) {
        await apiRequest<Budget>(`/budgets/${editingBudgetId}`, { method: "PATCH", body });
        toast("Presupuesto actualizado", "success");
      } else {
        await apiRequest<Budget>("/budgets", { method: "POST", body });
        toast(form.period_type === "annual" ? "Presupuesto anual creado" : "Presupuesto mensual creado", "success");
      }

      setEditingBudgetId(null);
      setForm({
        category_id: "",
        period_type: "monthly",
        currency: settings?.default_currency || "EUR",
        amount: "",
      });
      setIsDialogOpen(false);
      await loadAll(selectedYear);
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
      period_type: "monthly",
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
      period_type: budget.period_type,
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
    setConfirmDelete({ open: false, budgetId: null, label: "" });
    setError(null);

    try {
      await apiRequest<void>(`/budgets/${budgetId}`, {
        method: "DELETE",
        skipJson: true,
      });
      toast("Presupuesto eliminado", "success");
      await loadAll(selectedYear);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No se pudo eliminar el presupuesto");
    }
  }

  function toggleSelect(budgetId: string) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(budgetId)) {
        next.delete(budgetId);
      } else {
        next.add(budgetId);
      }
      return next;
    });
  }

  async function handleBatchDelete() {
    const ids = Array.from(selectedIds);
    setConfirmBatchDelete(false);
    if (!ids.length) {
      return;
    }
    setError(null);

    try {
      const result = await apiRequest<BudgetBatchDeleteResponse>("/budgets/batch-delete", {
        method: "POST",
        body: JSON.stringify({ budget_ids: ids }),
      });
      toast(`${result.deleted_count} presupuesto(s) eliminado(s)`, "success");
      setSelectedIds(new Set());
      await loadAll(selectedYear);
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "No se pudieron eliminar los presupuestos",
      );
    }
  }

  async function handleReorderDrop(targetId: string) {
    const sourceId = draggingId;
    setDraggingId(null);
    if (!sourceId || sourceId === targetId) {
      return;
    }
    const reordered = [...budgets];
    const fromIndex = reordered.findIndex((budget) => budget.id === sourceId);
    const toIndex = reordered.findIndex((budget) => budget.id === targetId);
    if (fromIndex < 0 || toIndex < 0) {
      return;
    }
    const [moved] = reordered.splice(fromIndex, 1);
    reordered.splice(toIndex, 0, moved);
    setBudgets(reordered.map((budget, index) => ({ ...budget, position: index })));

    try {
      await apiRequest<void>("/budgets/reorder", {
        method: "POST",
        body: JSON.stringify({ budget_ids: reordered.map((budget) => budget.id) }),
        skipJson: true,
      });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No se pudo reordenar");
      await loadAll(selectedYear);
    }
  }

  async function openBreakdown(budget: BudgetCard) {
    const year = Number(selectedYear);
    const month = Number(selectedMonth);
    const paddedMonth = String(month).padStart(2, "0");
    const dateFrom =
      budget.period_type === "annual" ? `${year}-01-01` : `${year}-${paddedMonth}-01`;
    const dateTo =
      budget.period_type === "annual"
        ? `${year}-12-31`
        : `${year}-${paddedMonth}-${String(new Date(year, month, 0).getDate()).padStart(2, "0")}`;

    setBreakdownBudget(budget);
    setBreakdownTransactions([]);
    setIsBreakdownLoading(true);

    try {
      const response = await apiRequest<PaginatedResponse<Transaction>>(
        `/transactions?limit=100&category_id=${budget.category_id}&date_from=${dateFrom}&date_to=${dateTo}&sort_by=date&sort_order=desc`,
      );
      setBreakdownTransactions(response.items.filter((transaction) => Number(transaction.amount) < 0));
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "No se pudieron cargar las transacciones",
      );
    } finally {
      setIsBreakdownLoading(false);
    }
  }

  const inputClasses = "w-full rounded-xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-4 py-2.5 outline-none transition-all focus:border-[var(--app-accent)] focus:shadow-[0_0_0_3px_var(--app-accent-soft)]";

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Presupuestos"
        title="Control de presupuestos"
        description="Define un objetivo mensual o anual por categoría una sola vez; se reaplica a cada periodo automáticamente."
      />

      <div className="flex flex-col items-start justify-between gap-2.5 sm:flex-row sm:items-center">
        <div className="flex flex-wrap items-center gap-2.5">
          <label className="text-xs font-medium uppercase tracking-[0.08em] text-[var(--app-muted)]" htmlFor="budget-month">Periodo</label>
          <select
            id="budget-month"
            aria-label="Mes del periodo"
            value={selectedMonth}
            onChange={(event) => setSelectedMonth(event.target.value)}
            className="rounded-xl border border-[var(--app-border)] bg-[var(--app-panel)] px-3.5 py-2 text-sm outline-none transition-all focus:border-[var(--app-accent)]"
          >
            {MONTH_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
          <select
            id="budget-year"
            aria-label="Año del periodo"
            value={selectedYear}
            onChange={(event) => setSelectedYear(event.target.value)}
            className="rounded-xl border border-[var(--app-border)] bg-[var(--app-panel)] px-3.5 py-2 text-sm outline-none transition-all focus:border-[var(--app-accent)]"
          >
            {[currentYear - 1, currentYear, currentYear + 1].map((year) => (
              <option key={year} value={String(year)}>{year}</option>
            ))}
          </select>

          <div className="inline-flex rounded-xl border border-[var(--app-border)] bg-[var(--app-panel)] p-0.5" role="group" aria-label="Filtrar por periodicidad">
            {(
              [
                { value: "all", label: "Todos" },
                { value: "monthly", label: "Mensuales" },
                { value: "annual", label: "Anuales" },
              ] as const
            ).map((option) => (
              <button
                key={option.value}
                type="button"
                aria-pressed={periodFilter === option.value}
                onClick={() => setPeriodFilter(option.value)}
                className={`rounded-[10px] px-3 py-1.5 text-xs font-medium transition-all ${
                  periodFilter === option.value
                    ? "bg-[var(--app-accent)] text-white"
                    : "text-[var(--app-muted)] hover:text-[var(--app-ink)]"
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>

          <select
            id="budget-category-filter"
            aria-label="Filtrar por categoría"
            value={categoryFilter}
            onChange={(event) => setCategoryFilter(event.target.value)}
            className="rounded-xl border border-[var(--app-border)] bg-[var(--app-panel)] px-3.5 py-2 text-sm outline-none transition-all focus:border-[var(--app-accent)]"
          >
            <option value="all">Todas las categorías</option>
            {budgetCategories.map((category) => (
              <option key={category.id} value={category.id}>{category.name}</option>
            ))}
          </select>

          <select
            id="budget-sort"
            aria-label="Ordenar presupuestos"
            value={sortMode}
            onChange={(event) => setSortMode(event.target.value as SortMode)}
            className="rounded-xl border border-[var(--app-border)] bg-[var(--app-panel)] px-3.5 py-2 text-sm outline-none transition-all focus:border-[var(--app-accent)]"
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
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
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : (
        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <SummaryCard title="Presupuestado / mes" value={summary.budgetedMonthly} currency={settings?.default_currency || "EUR"} tone="neutral" />
          <SummaryCard title="Presupuestado / año" value={summary.budgetedAnnual} currency={settings?.default_currency || "EUR"} tone="neutral" />
          <SummaryCard title="Gastado (periodo)" value={summary.spentPeriod} currency={settings?.default_currency || "EUR"} tone="danger" />
          <SummaryCard title="Disponible del mes" value={summary.availableMonth} currency={settings?.default_currency || "EUR"} tone={summary.availableMonth >= 0 ? "success" : "danger"} />
          <SummaryCard title="Disponible del año" value={summary.availableYear} currency={settings?.default_currency || "EUR"} tone={summary.availableYear >= 0 ? "success" : "danger"} />
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
            ? "Ajusta el objetivo del presupuesto y su periodicidad."
            : "Un presupuesto mensual se reaplica cada mes; uno anual cubre todo el año, sin tener que crearlo de nuevo."
        }
      >
        <form className="space-y-4" onSubmit={handleSubmit}>
          <select required aria-label="Categoría del presupuesto" value={form.category_id} onChange={(event) => setForm((current) => ({ ...current, category_id: event.target.value }))} className={inputClasses}>
            <option value="">Selecciona categoría</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>{category.name}</option>
            ))}
          </select>
          <select aria-label="Periodicidad del presupuesto" value={form.period_type} onChange={(event) => setForm((current) => ({ ...current, period_type: event.target.value as BudgetFormState["period_type"] }))} className={inputClasses}>
            <option value="monthly">Mensual (se repite cada mes)</option>
            <option value="annual">Anual (todo el año)</option>
          </select>
          <div className="grid gap-4 sm:grid-cols-2">
            <input required aria-label="Divisa del presupuesto" value={form.currency} maxLength={3} onChange={(event) => setForm((current) => ({ ...current, currency: event.target.value.toUpperCase() }))} className={`${inputClasses} uppercase`} />
            <input required aria-label="Importe del presupuesto" value={form.amount} onChange={(event) => setForm((current) => ({ ...current, amount: event.target.value }))} placeholder="120.00" className={inputClasses} />
          </div>
          {error ? <p className="text-sm text-[var(--app-danger)]">{error}</p> : null}
          <button type="submit" className="inline-flex w-full items-center justify-center rounded-xl bg-[var(--app-accent)] px-4 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110">
            {editingBudgetId ? "Guardar cambios" : "Crear presupuesto"}
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

      <ConfirmDialog
        open={confirmBatchDelete}
        title="Eliminar presupuestos"
        description={`¿Eliminar ${selectedIds.size} presupuesto(s) seleccionado(s)? Esta acción no se puede deshacer.`}
        onConfirm={() => void handleBatchDelete()}
        onCancel={() => setConfirmBatchDelete(false)}
      />

      <Modal
        open={breakdownBudget !== null}
        onClose={() => setBreakdownBudget(null)}
        title={`Desglose · ${breakdownBudget?.category?.name ?? "Categoría"}`}
        description={
          breakdownBudget
            ? breakdownBudget.period_type === "annual"
              ? `Gastos del año ${selectedYear}`
              : `Gastos de ${formatMonthLabel(Number(selectedYear), Number(selectedMonth))}`
            : ""
        }
      >
        {breakdownBudget ? (
          isBreakdownLoading ? (
            <p className="py-6 text-center text-sm text-[var(--app-muted)]">Cargando transacciones…</p>
          ) : breakdownTransactions.length ? (
            <div className="space-y-3">
              <div className="max-h-80 space-y-1.5 overflow-y-auto pr-1">
                {breakdownTransactions.map((transaction) => (
                  <div
                    key={transaction.id}
                    className="flex items-center justify-between gap-3 rounded-xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-3.5 py-2.5"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-[var(--app-ink)]">{transaction.description}</p>
                      <p className="text-xs text-[var(--app-muted)]">{formatDate(transaction.date)}</p>
                    </div>
                    <AmountValue
                      amount={Number(transaction.amount)}
                      currency={transaction.currency}
                      className="shrink-0 text-sm font-semibold"
                    />
                  </div>
                ))}
              </div>
              <div className="flex items-center justify-between border-t border-[var(--app-border)] pt-3 text-sm font-semibold">
                <span className="text-[var(--app-muted)]">Total gastado</span>
                <AmountValue amount={breakdownBudget.spent} currency={breakdownBudget.currency} />
              </div>
            </div>
          ) : (
            <p className="py-6 text-center text-sm text-[var(--app-muted)]">
              No hay transacciones en este periodo para esta categoría.
            </p>
          )
        ) : null}
      </Modal>

      {isLoading ? (
        <ListSkeleton rows={4} />
      ) : (
        <Card className="animate-slideUp">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg">Presupuestos</CardTitle>
              <p className="mt-1 text-xs text-[var(--app-muted)]">
                Gastado de los mensuales en {formatMonthLabel(Number(selectedYear), Number(selectedMonth))};
                de los anuales en {selectedYear}.
              </p>
            </div>
            <div className="rounded-full bg-[var(--app-muted-surface)] px-2.5 py-1 text-xs text-[var(--app-muted)]">
              {budgetCards.length} total
            </div>
          </CardHeader>
          <CardContent>
            {budgetCards.length ? (
              <>
                {selectedIds.size > 0 ? (
                  <div className="mb-3 flex items-center justify-between rounded-xl border border-[var(--app-accent)] bg-[var(--app-accent-soft)] px-4 py-2.5 text-sm">
                    <span className="font-medium text-[var(--app-accent)]">
                      {selectedIds.size} seleccionado(s)
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setSelectedIds(new Set())}
                        className="rounded-lg px-2.5 py-1 text-xs text-[var(--app-muted)] transition-all hover:text-[var(--app-ink)]"
                      >
                        Cancelar
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirmBatchDelete(true)}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--app-danger)] px-3 py-1.5 text-xs font-medium text-white transition-all hover:brightness-110"
                      >
                        <Trash2 className="h-3.5 w-3.5" /> Eliminar seleccionados
                      </button>
                    </div>
                  </div>
                ) : null}
                <div className="grid gap-3 lg:grid-cols-2">
                  {visibleBudgetCards.map((budget, index) => (
                    <BudgetStatusCard
                      key={budget.id}
                      budget={budget}
                      index={index}
                      selected={selectedIds.has(budget.id)}
                      isDragging={draggingId === budget.id}
                      dragEnabled={sortMode === "manual"}
                      onDragStartCard={() => setDraggingId(budget.id)}
                      onDropCard={() => void handleReorderDrop(budget.id)}
                      onToggleSelect={() => toggleSelect(budget.id)}
                      onEdit={() => openEditDialog(budget)}
                      onBreakdown={() => void openBreakdown(budget)}
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
                {pageSize !== "all" ? (
                  <PaginationControls page={page} pageSize={effectivePageSize} total={budgetCards.length} onPageChange={setPage} className="mt-5" />
                ) : null}
                <div className="mt-3 flex justify-end">
                  <label className="flex items-center gap-2 text-sm text-[var(--app-muted)]">
                    <span>Por página</span>
                    <select
                      aria-label="Presupuestos por página"
                      value={pageSize === "all" ? "all" : String(pageSize)}
                      onChange={(event) => handlePageSizeChange(event.target.value)}
                      className="rounded-xl border border-[var(--app-border)] bg-[var(--app-panel)] px-3 py-2 text-sm outline-none transition-all focus:border-[var(--app-accent)]"
                    >
                      {PAGE_SIZE_OPTIONS.map((option) => (
                        <option key={option} value={String(option)}>{option}</option>
                      ))}
                      <option value="all">Todos</option>
                    </select>
                  </label>
                </div>
              </>
            ) : (
              <EmptyState
                title="No hay presupuestos todavía"
                description="Crea un objetivo mensual o anual por categoría y verás aquí el progreso del periodo."
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
  selected,
  isDragging,
  dragEnabled,
  onDragStartCard,
  onDropCard,
  onToggleSelect,
  onEdit,
  onBreakdown,
  onDelete,
}: {
  budget: BudgetCard;
  index: number;
  selected: boolean;
  isDragging: boolean;
  dragEnabled: boolean;
  onDragStartCard: () => void;
  onDropCard: () => void;
  onToggleSelect: () => void;
  onEdit: () => void;
  onBreakdown: () => void;
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
      draggable={dragEnabled}
      onDragStart={dragEnabled ? onDragStartCard : undefined}
      onDragOver={dragEnabled ? (event) => event.preventDefault() : undefined}
      onDrop={dragEnabled ? onDropCard : undefined}
      className={`animate-slideUp stagger-${Math.min(index + 1, 6)} relative overflow-hidden rounded-2xl border bg-[var(--app-panel)] transition-shadow hover:shadow-[var(--app-shadow-elevated)] hover:z-10 ${dragEnabled ? "cursor-grab active:cursor-grabbing" : ""} ${selected ? "border-[var(--app-accent)] ring-2 ring-[var(--app-accent)]" : "border-[var(--app-border)]"} ${isDragging ? "opacity-50" : ""}`}
    >
      {/* Colored gradient top band */}
      <div className={`absolute inset-x-0 top-0 h-24 bg-gradient-to-b ${gradientClass} pointer-events-none`} />

      <div className="relative">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 px-5 pt-5 pb-3">
          <div className="flex items-start gap-2.5">
            {dragEnabled ? (
              <GripVertical className="mt-0.5 h-4 w-4 shrink-0 text-[var(--app-muted)]" aria-hidden="true" />
            ) : null}
            <input
              type="checkbox"
              checked={selected}
              onChange={onToggleSelect}
              aria-label={`Seleccionar presupuesto ${budget.category?.name ?? "Categoría"}`}
              className="mt-1 h-4 w-4 shrink-0 cursor-pointer accent-[var(--app-accent)]"
            />
            <div className="space-y-0.5">
              <p className="text-[11px] uppercase tracking-[0.1em] text-[var(--app-muted)]">
                {getBudgetPeriodLabel(budget)}
              </p>
              <h3 className="text-base font-semibold text-[var(--app-ink)]">
                {budget.category?.name ?? "Categoría"}
              </h3>
            </div>
          </div>
          <div className="flex items-center gap-2 pt-0.5">
            <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${statusBadgeClass}`}>
              {budget.statusLabel}
            </span>
            <BudgetActionsMenu
              label={`${budget.category?.name ?? "Categoría"} ${getBudgetPeriodLabel(budget)}`}
              onEdit={onEdit}
              onBreakdown={onBreakdown}
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
  onBreakdown,
  onDelete,
}: {
  label: string;
  onEdit: () => void;
  onBreakdown: () => void;
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
          <button type="button" onClick={() => runAndClose(onBreakdown)} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-all hover:bg-[var(--app-muted-surface)]">
            <Receipt className="h-4 w-4" /> Ver transacciones
          </button>
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
