"use client";

import { FormEvent, Suspense, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import useSWR from "swr";
import { Copy, CreditCard, Pencil, Plus, Trash2, X } from "lucide-react";

import { AmountValue } from "@/components/amount-value";
import { CategoryBadge } from "@/components/category-badge";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Modal } from "@/components/ui/modal";
import { PaginationControls } from "@/components/ui/pagination-controls";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { ActionMenu } from "@/components/ui/action-menu";
import { ListSkeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";
import { apiRequest } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { Account, Category, PaginatedResponse, Transaction } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const fetcher = <T,>(url: string) => apiRequest<T>(url);

type TransactionFilters = {
  account_id: string;
  category_id: string;
  category_type: "" | "income" | "expense" | "transfer";
  year: string;
  month: string;
  search: string;
};

type TransactionEditorMode = "create" | "edit" | "duplicate";

function parseCategoryType(
  value: string | null,
): TransactionFilters["category_type"] {
  return value === "income" || value === "expense" || value === "transfer" ? value : "";
}

export default function TransactionsPage() {
  return (
    <Suspense fallback={<ListSkeleton rows={10} />}>
      <TransactionsContent />
    </Suspense>
  );
}

function TransactionsContent() {
  const { toast } = useToast();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const page = Number(searchParams.get("page")) || 1;
  const filters: TransactionFilters = {
    account_id: searchParams.get("account_id") || "",
    category_id: searchParams.get("category_id") || "",
    category_type: parseCategoryType(searchParams.get("category_type")),
    year: searchParams.get("year") || "",
    month: searchParams.get("month") || "",
    search: searchParams.get("search") || "",
  };

  const pageSize = 20;
  const transactionQuery = buildTransactionQuery(filters, page, pageSize);

  const { data: transData, mutate: mutateTrans } = useSWR<PaginatedResponse<Transaction>>(`/transactions?${transactionQuery}`, fetcher, { keepPreviousData: true });
  const { data: accData } = useSWR<PaginatedResponse<Account>>("/accounts?limit=100&sort_by=name&sort_order=asc", fetcher);
  const { data: catData } = useSWR<PaginatedResponse<Category>>("/categories?limit=100&sort_by=name&sort_order=asc", fetcher);

  const transactions = transData?.items || [];
  const totalTransactions = transData?.total || 0;
  const accounts = accData?.items || [];
  const categories = catData?.items || [];
  const isLoading = !transData || !accData || !catData;
  const error = null;

  const [form, setForm] = useState(defaultTransactionForm());
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [editorMode, setEditorMode] = useState<TransactionEditorMode>("create");
  const [editingTransactionId, setEditingTransactionId] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<{ open: boolean; ids: string[] }>({ open: false, ids: [] });

  const accountMap = new Map(accounts.map((account) => [account.id, account]));
  const categoryMap = new Map(categories.map((category) => [category.id, category]));
  const selectedCount = selectedIds.length;
  const allVisibleSelected = transactions.length > 0 && transactions.every((transaction) => selectedIds.includes(transaction.id));

  const yearOptions = useMemo(() => {
    const currentYear = new Date().getFullYear();
    return Array.from({ length: 4 }, (_, index) => String(currentYear - index));
  }, []);

  function updateFilter(key: keyof TransactionFilters, value: string) {
    const params = new URLSearchParams(searchParams);
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    params.set("page", "1");
    router.replace(`${pathname}?${params.toString()}`);
  }

  function handleSearch(value: string) {
    const params = new URLSearchParams(searchParams);
    if (value) {
      params.set("search", value);
    } else {
      params.delete("search");
    }
    params.set("page", "1");
    router.replace(`${pathname}?${params.toString()}`);
  }

  function handlePageChange(newPage: number) {
    const params = new URLSearchParams(searchParams);
    params.set("page", newPage.toString());
    router.replace(`${pathname}?${params.toString()}`);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    try {
      const payload = {
        ...form,
        category_id: form.category_id || null,
      };

      if (editorMode === "edit" && editingTransactionId) {
        await apiRequest<Transaction>(`/transactions/${editingTransactionId}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
        toast("Transacción actualizada", "success");
      } else {
        await apiRequest<Transaction>("/transactions", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        toast(editorMode === "duplicate" ? "Copia creada" : "Transacción creada", "success");
      }

      setForm((current) => defaultTransactionForm(current.currency, current.account_id));
      setEditorMode("create");
      setEditingTransactionId(null);
      setIsDialogOpen(false);
      await mutateTrans();
    } catch (requestError) {
      toast(requestError instanceof Error ? requestError.message : "Error al guardar", "error");
    }
  }

  function handleOpenCreate() {
    setEditorMode("create");
    setEditingTransactionId(null);
    setForm(defaultTransactionForm(form.currency, form.account_id));
    setIsDialogOpen(true);
  }

  function handleOpenEdit(transaction: Transaction) {
    setEditorMode("edit");
    setEditingTransactionId(transaction.id);
    setForm(transactionToForm(transaction));
    setIsDialogOpen(true);
  }

  function handleOpenDuplicate(transaction: Transaction) {
    setEditorMode("duplicate");
    setEditingTransactionId(null);
    setForm(transactionToForm(transaction));
    setIsDialogOpen(true);
  }

  function toggleSelection(transactionId: string) {
    setSelectedIds((current) =>
      current.includes(transactionId)
        ? current.filter((id) => id !== transactionId)
        : [...current, transactionId],
    );
  }

  function toggleSelectAll() {
    setSelectedIds((current) =>
      allVisibleSelected ? current.filter((id) => !transactions.some((transaction) => transaction.id === id)) : [...current, ...transactions.map((t) => t.id).filter(id => !current.includes(id))],
    );
  }

  async function handleDeleteConfirmed() {
    const ids = confirmDelete.ids;
    setConfirmDelete({ open: false, ids: [] });

    try {
      await Promise.all(
        ids.map((transactionId) =>
          apiRequest<void>(`/transactions/${transactionId}`, {
            method: "DELETE",
            skipJson: true,
          }),
        ),
      );
      setSelectedIds((current) => current.filter((id) => !ids.includes(id)));
      toast(ids.length === 1 ? "Transacción eliminada" : `${ids.length} transacciones eliminadas`, "success");
      await mutateTrans();
    } catch (requestError) {
      toast(requestError instanceof Error ? requestError.message : "Error al eliminar", "error");
    }
  }

  const inputClasses = "w-full rounded-xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-4 py-2.5 outline-none transition-all focus:border-[var(--app-accent)] focus:shadow-[0_0_0_3px_var(--app-accent-soft)]";

  return (
    <div>
      <PageHeader
        eyebrow="Transactions"
        title="Transacciones"
        description="Consulta y registra tus movimientos en un solo lugar."
      />

      <div className="space-y-6">
        <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
          <div className="inline-flex rounded-xl bg-[var(--app-muted-surface)] px-3 py-1.5 text-sm text-[var(--app-muted)]">
            {totalTransactions} resultados
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {selectedCount ? (
              <button
                type="button"
                onClick={() => setConfirmDelete({ open: true, ids: selectedIds })}
                className="inline-flex items-center gap-2 rounded-xl bg-[var(--app-danger-soft)] px-4 py-2.5 text-sm font-semibold text-[var(--app-danger)] transition-all hover:brightness-110"
              >
                <Trash2 className="h-4 w-4" />
                Eliminar seleccionadas ({selectedCount})
              </button>
            ) : null}
            <button
              type="button"
              onClick={handleOpenCreate}
              className="inline-flex items-center gap-2 rounded-xl bg-[var(--app-accent)] px-4 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110"
            >
              <Plus className="h-4 w-4" />
              Nueva transacción
            </button>
          </div>
        </div>

        <ConfirmDialog
          open={confirmDelete.open}
          title="Eliminar transacciones"
          description={
            confirmDelete.ids.length === 1
              ? "¿Quieres eliminar esta transacción? Esta acción no se puede deshacer."
              : `¿Quieres eliminar ${confirmDelete.ids.length} transacciones? Esta acción no se puede deshacer.`
          }
          onConfirm={() => void handleDeleteConfirmed()}
          onCancel={() => setConfirmDelete({ open: false, ids: [] })}
        />

        <Modal
          open={isDialogOpen}
          onClose={() => {
            setIsDialogOpen(false);
            setEditorMode("create");
            setEditingTransactionId(null);
          }}
          title={
            editorMode === "edit"
              ? "Editar transacción"
              : editorMode === "duplicate"
                ? "Duplicar transacción"
                : "Nueva transacción"
          }
          description={
            editorMode === "edit"
              ? "Actualiza la información y guarda los cambios."
              : editorMode === "duplicate"
                ? "Partimos de una transacción existente para crear una nueva."
                : "Añade un ingreso, gasto o movimiento y actualiza el dashboard al instante."
          }
        >
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="grid gap-4 sm:grid-cols-2">
              <select
                required
                aria-label="Cuenta de la transacción"
                value={form.account_id}
                onChange={(event) =>
                  setForm((current) => ({ ...current, account_id: event.target.value }))
                }
                className={inputClasses}
              >
                <option value="">Selecciona cuenta</option>
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name} · {account.currency}
                  </option>
                ))}
              </select>

              <select
                aria-label="Categoría de la transacción"
                value={form.category_id}
                onChange={(event) =>
                  setForm((current) => ({ ...current, category_id: event.target.value }))
                }
                className={inputClasses}
              >
                <option value="">Sin categoría</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              <input required aria-label="Fecha de la transacción" type="date" value={form.date} onChange={(event) => setForm((current) => ({ ...current, date: event.target.value }))} className={inputClasses} />
              <input required aria-label="Importe de la transacción" value={form.amount} onChange={(event) => setForm((current) => ({ ...current, amount: event.target.value }))} placeholder="48.90" className={inputClasses} />
              <input required aria-label="Divisa de la transacción" value={form.currency} maxLength={3} onChange={(event) => setForm((current) => ({ ...current, currency: event.target.value.toUpperCase() }))} className={`${inputClasses} uppercase`} />
            </div>
            <input required aria-label="Descripción de la transacción" value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} placeholder="Descripción" className={inputClasses} />
            <textarea aria-label="Notas de la transacción" value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} rows={3} placeholder="Notas" className={inputClasses} />
            {error ? <p className="text-sm text-[var(--app-danger)]">{error}</p> : null}
            <button
              type="submit"
              className="inline-flex w-full items-center justify-center rounded-xl bg-[var(--app-accent)] px-4 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110"
            >
              {editorMode === "edit"
                ? "Guardar cambios"
                : editorMode === "duplicate"
                  ? "Crear copia"
                  : "Crear transacción"}
            </button>
          </form>
        </Modal>

        {/* ─── Filters ─── */}
        <div className="animate-fadeIn overflow-hidden rounded-2xl border border-[var(--app-border)] bg-[var(--app-panel-strong)]">
          <div className="flex items-stretch">
            <div className="flex shrink-0 items-center border-r border-[var(--app-border)] bg-[var(--app-muted-surface)] px-4 text-xs font-semibold text-[var(--app-muted)]">
              Filtros
            </div>
            <div className="min-w-0 flex-1 p-2">
              <div className="flex flex-nowrap items-center gap-1 overflow-x-auto pb-1">
                <FilterSelect value={filters.account_id} onChange={(v) => updateFilter("account_id", v)} placeholder="Cuenta" options={accounts.map((a) => ({ value: a.id, label: a.name }))} />
                <FilterSelect value={filters.category_id} onChange={(v) => updateFilter("category_id", v)} placeholder="Categoría" options={categories.map((c) => ({ value: c.id, label: c.name }))} />
                <FilterSelect value={filters.category_type} onChange={(v) => updateFilter("category_type", v)} placeholder="Tipo" options={[{ value: "expense", label: "Gasto" }, { value: "income", label: "Ingreso" }, { value: "transfer", label: "Transferencia" }]} minWidth="92px" />
                <FilterSelect value={filters.year} onChange={(v) => updateFilter("year", v)} placeholder="Año" options={yearOptions.map((y) => ({ value: y, label: y }))} minWidth="86px" />
                <FilterSelect value={filters.month} onChange={(v) => updateFilter("month", v)} placeholder="Mes" options={monthOptions.map((m) => ({ value: m.value, label: m.label }))} minWidth="86px" />
                <div className="min-w-[150px] shrink-0">
                  <input
                    value={filters.search}
                    onChange={(event) => handleSearch(event.target.value)}
                    placeholder="Buscar"
                    className="h-8 w-full rounded-lg border border-[var(--app-border)] bg-[var(--app-panel)] px-2 text-xs outline-none transition-all focus:border-[var(--app-accent)]"
                  />
                </div>
              </div>
            </div>
            <div className="flex shrink-0 items-center px-2">
              <button
                type="button"
                onClick={() => router.replace(pathname)}
                className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-[var(--app-danger)] transition-all hover:bg-[var(--app-danger-soft)]"
                aria-label="Limpiar filtros"
                title="Limpiar filtros"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>

        {/* ─── Transactions list ─── */}
        {isLoading ? (
          <ListSkeleton rows={6} />
        ) : (
          <Card className="animate-slideUp">
            <CardHeader>
              <CardTitle>Últimas transacciones</CardTitle>
            </CardHeader>
            <CardContent>
              {transactions.length ? (
                <>
                  {/* Mobile cards */}
                  <div className="space-y-3 md:hidden">
                    {transactions.map((transaction) => (
                      <article
                        key={transaction.id}
                        className="rounded-2xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] p-4 transition-colors hover:bg-[var(--app-muted-surface)]"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0 space-y-1">
                            <label className="inline-flex items-center gap-2 text-xs text-[var(--app-muted)]">
                              <input
                                type="checkbox"
                                checked={selectedIds.includes(transaction.id)}
                                onChange={() => toggleSelection(transaction.id)}
                              />
                              Seleccionar
                            </label>
                            <p className="font-medium">{transaction.description}</p>
                            <p className="text-sm text-[var(--app-muted)]">
                              {accountMap.get(transaction.account_id)?.name ?? "Cuenta desconocida"}
                            </p>
                            <CategoryBadge category={categoryMap.get(transaction.category_id ?? "")} />
                          </div>
                          <div className="flex items-start gap-2">
                            <AmountValue
                              amount={transaction.amount}
                              currency={transaction.currency}
                              className="shrink-0 text-sm"
                            />
                            <ActionMenu
                              label={transaction.description}
                              ariaLabel={`Acciones de transacción ${transaction.description}`}
                              actions={[
                                { label: "Editar", icon: <Pencil className="h-4 w-4" />, onClick: () => handleOpenEdit(transaction) },
                                { label: "Duplicar", icon: <Copy className="h-4 w-4" />, onClick: () => handleOpenDuplicate(transaction) },
                                { label: "Eliminar", icon: <Trash2 className="h-4 w-4" />, onClick: () => setConfirmDelete({ open: true, ids: [transaction.id] }), danger: true },
                              ]}
                            />
                          </div>
                        </div>
                        <div className="mt-3 flex flex-wrap items-center gap-2">
                          <span className="text-xs text-[var(--app-muted)]">{formatDate(transaction.date)}</span>
                        </div>
                        {transaction.notes ? (
                          <p className="mt-3 text-xs text-[var(--app-muted)]">{transaction.notes}</p>
                        ) : null}
                      </article>
                    ))}
                  </div>

                  {/* Desktop table */}
                  <div className="hidden md:block">
                    <Table className="table-fixed">
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-12">
                            <input type="checkbox" checked={allVisibleSelected} onChange={toggleSelectAll} aria-label="Seleccionar todas" />
                          </TableHead>
                          <TableHead className="w-[34%]">Descripción</TableHead>
                          <TableHead className="w-[18%]">Cuenta</TableHead>
                          <TableHead className="w-[18%]">Categoría</TableHead>
                          <TableHead className="w-[12%]">Fecha</TableHead>
                          <TableHead className="w-[18%] text-right">Importe</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {transactions.map((transaction) => (
                          <TableRow key={transaction.id}>
                            <TableCell>
                              <input type="checkbox" checked={selectedIds.includes(transaction.id)} onChange={() => toggleSelection(transaction.id)} aria-label={`Seleccionar ${transaction.description}`} />
                            </TableCell>
                            <TableCell>
                              <div className="space-y-1 overflow-hidden">
                                <p className="truncate font-medium">{transaction.description}</p>
                                {transaction.notes ? (
                                  <p className="truncate text-xs text-[var(--app-muted)]">{transaction.notes}</p>
                                ) : null}
                              </div>
                            </TableCell>
                            <TableCell className="truncate">{accountMap.get(transaction.account_id)?.name ?? "Cuenta desconocida"}</TableCell>
                            <TableCell><CategoryBadge category={categoryMap.get(transaction.category_id ?? "")} /></TableCell>
                            <TableCell className="whitespace-nowrap">{formatDate(transaction.date)}</TableCell>
                            <TableCell className="text-right">
                              <div className="flex items-center justify-end gap-2">
                                <AmountValue amount={transaction.amount} currency={transaction.currency} />
                                <ActionMenu
                                  label={transaction.description}
                                  ariaLabel={`Acciones de transacción ${transaction.description}`}
                                  actions={[
                                    { label: "Editar", icon: <Pencil className="h-4 w-4" />, onClick: () => handleOpenEdit(transaction) },
                                    { label: "Duplicar", icon: <Copy className="h-4 w-4" />, onClick: () => handleOpenDuplicate(transaction) },
                                    { label: "Eliminar", icon: <Trash2 className="h-4 w-4" />, onClick: () => setConfirmDelete({ open: true, ids: [transaction.id] }), danger: true },
                                  ]}
                                />
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>

                  <div className="mt-6">
                    <PaginationControls page={page} pageSize={pageSize} total={totalTransactions} onPageChange={handlePageChange} />
                  </div>
                </>
              ) : (
                <EmptyState
                  title="Aún no hay transacciones"
                  description="Crea la primera para empezar a poblar el dashboard."
                  icon={CreditCard}
                  actionLabel="Nueva transacción"
                  onAction={handleOpenCreate}
                  variant="plain"
                />
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

function FilterSelect({
  value,
  onChange,
  placeholder,
  options,
  minWidth = "120px",
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  options: { value: string; label: string }[];
  minWidth?: string;
}) {
  return (
    <div className="shrink-0" style={{ minWidth }}>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-8 w-full rounded-lg border border-[var(--app-border)] bg-[var(--app-panel)] px-2 text-xs outline-none transition-all focus:border-[var(--app-accent)]"
      >
        <option value="">{placeholder}</option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </div>
  );
}

function transactionToForm(transaction: Transaction) {
  return {
    account_id: transaction.account_id,
    category_id: transaction.category_id ?? "",
    date: transaction.date,
    amount: String(transaction.amount),
    currency: transaction.currency,
    description: transaction.description,
    notes: transaction.notes ?? "",
  };
}

function defaultTransactionForm(currency = "EUR", accountId = "") {
  return {
    account_id: accountId,
    category_id: "",
    date: new Date().toISOString().slice(0, 10),
    amount: "",
    currency,
    description: "",
    notes: "",
  };
}

const monthOptions = [
  { value: "1", label: "Enero" }, { value: "2", label: "Febrero" }, { value: "3", label: "Marzo" },
  { value: "4", label: "Abril" }, { value: "5", label: "Mayo" }, { value: "6", label: "Junio" },
  { value: "7", label: "Julio" }, { value: "8", label: "Agosto" }, { value: "9", label: "Septiembre" },
  { value: "10", label: "Octubre" }, { value: "11", label: "Noviembre" }, { value: "12", label: "Diciembre" },
];

function buildTransactionQuery(filters: TransactionFilters, page: number, pageSize: number) {
  const offset = (page - 1) * pageSize;
  const params = new URLSearchParams({
    limit: String(pageSize),
    offset: String(offset),
    sort_by: "date",
    sort_order: "desc",
  });

  if (filters.account_id) params.set("account_id", filters.account_id);
  if (filters.category_id) params.set("category_id", filters.category_id);
  if (filters.category_type) params.set("category_type", filters.category_type);
  if (filters.search.trim()) params.set("search", filters.search.trim());

  const year = Number(filters.year || new Date().getFullYear());
  if (filters.year) {
    const month = filters.month ? Number(filters.month) : undefined;
    const dateFrom = new Date(year, month ? month - 1 : 0, 1);
    const dateTo = month ? new Date(year, month, 0) : new Date(year, 11, 31);
    params.set("date_from", toDateInputValue(dateFrom));
    params.set("date_to", toDateInputValue(dateTo));
  } else if (filters.month) {
    const month = Number(filters.month);
    const currentYear = new Date().getFullYear();
    params.set("date_from", toDateInputValue(new Date(currentYear, month - 1, 1)));
    params.set("date_to", toDateInputValue(new Date(currentYear, month, 0)));
  }

  return params.toString();
}

function toDateInputValue(value: Date) {
  return value.toISOString().slice(0, 10);
}
