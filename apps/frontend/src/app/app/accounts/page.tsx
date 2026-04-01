"use client";

import { FormEvent, useEffect, useEffectEvent, useRef, useState } from "react";
import { MoreVertical, Pencil, Plus, Trash2, Wallet } from "lucide-react";

import { AmountValue } from "@/components/amount-value";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/empty-state";
import { ListSkeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/page-header";
import { Modal } from "@/components/ui/modal";
import { PaginationControls } from "@/components/ui/pagination-controls";
import { useToast } from "@/components/ui/toast";
import { apiRequest } from "@/lib/api";
import type { Account, AccountType, PaginatedResponse, Transaction } from "@/lib/types";

type AccountFormState = {
  name: string;
  bank_name: string;
  type: AccountType;
  currency: string;
  initial_balance: string;
};

const defaultForm: AccountFormState = {
  name: "",
  bank_name: "",
  type: "checking",
  currency: "EUR",
  initial_balance: "",
};

const accountTypeLabels: Record<AccountType, string> = {
  checking: "Cuenta principal",
  savings: "Ahorro",
  shared: "Compartida",
  other: "Otra",
};

export default function AccountsPage() {
  const { toast } = useToast();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [form, setForm] = useState({ ...defaultForm });
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingAccountId, setEditingAccountId] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<{ open: boolean; account: Account | null }>({ open: false, account: null });
  const [page, setPage] = useState(1);
  const pageSize = 6;

  async function loadAccounts() {
    try {
      const [accountsResponse, transactionsResponse] = await Promise.all([
        apiRequest<PaginatedResponse<Account>>("/accounts?sort_by=name&sort_order=asc&limit=100"),
        apiRequest<PaginatedResponse<Transaction>>("/transactions?limit=100"),
      ]);

      setAccounts(accountsResponse.items);
      setTransactions(transactionsResponse.items);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No se pudieron cargar las cuentas");
    } finally {
      setIsLoading(false);
    }
  }

  const loadAccountsOnMount = useEffectEvent(async () => {
    await loadAccounts();
  });

  useEffect(() => {
    void loadAccountsOnMount();
  }, []);

  const balances = new Map<string, number>();

  transactions.forEach((transaction) => {
    balances.set(
      transaction.account_id,
      (balances.get(transaction.account_id) ?? 0) + Number(transaction.amount),
    );
  });

  const paginatedAccounts = accounts.slice((page - 1) * pageSize, page * pageSize);

  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(accounts.length / pageSize));
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [accounts.length, page]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    try {
      const payload = {
        name: form.name,
        bank_name: form.bank_name.trim() || null,
        type: form.type,
        currency: form.currency.trim().toUpperCase(),
      };

      if (editingAccountId) {
        await apiRequest<Account>(`/accounts/${editingAccountId}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
        toast("Cuenta actualizada", "success");
      } else {
        await apiRequest<Account>("/accounts", {
          method: "POST",
          body: JSON.stringify({
            ...payload,
            initial_balance: form.initial_balance.trim() || "0.00",
          }),
        });
        toast("Cuenta creada", "success");
      }

      setForm({ ...defaultForm });
      setEditingAccountId(null);
      setIsDialogOpen(false);
      await loadAccounts();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : editingAccountId
            ? "No se pudo editar la cuenta"
            : "No se pudo crear la cuenta",
      );
    }
  }

  function openCreateDialog() {
    setError(null);
    setEditingAccountId(null);
    setForm({ ...defaultForm });
    setIsDialogOpen(true);
  }

  function openEditDialog(account: Account) {
    setError(null);
    setEditingAccountId(account.id);
    setForm({
      name: account.name,
      bank_name: account.bank_name ?? "",
      type: account.type,
      currency: account.currency,
      initial_balance: "",
    });
    setIsDialogOpen(true);
  }

  async function handleDeleteConfirmed() {
    const account = confirmDelete.account;
    setConfirmDelete({ open: false, account: null });
    if (!account) return;

    setError(null);

    try {
      await apiRequest<void>(`/accounts/${account.id}`, {
        method: "DELETE",
        skipJson: true,
      });
      toast(`Cuenta "${account.name}" eliminada`, "success");
      await loadAccounts();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No se pudo eliminar la cuenta");
    }
  }

  const inputClasses = "w-full rounded-xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-4 py-2.5 outline-none transition-all focus:border-[var(--app-accent)] focus:shadow-[0_0_0_3px_var(--app-accent-soft)]";

  return (
    <div>
      <PageHeader
        eyebrow="Accounts"
        title="Cuentas"
        description="Organiza tus cuentas y separa el dinero por contexto de uso."
      />

      <div className="space-y-6">
        <div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
          <div className="inline-flex rounded-xl bg-[var(--app-muted-surface)] px-3 py-1.5 text-sm text-[var(--app-muted)]">
            {accounts.length} total
          </div>
          <button
            type="button"
            onClick={openCreateDialog}
            className="inline-flex items-center gap-2 rounded-xl bg-[var(--app-accent)] px-4 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110"
          >
            <Plus className="h-4 w-4" />
            Nueva cuenta
          </button>
        </div>

        <ConfirmDialog
          open={confirmDelete.open}
          title="Eliminar cuenta"
          description={`¿Quieres eliminar la cuenta "${confirmDelete.account?.name ?? ""}"? También se eliminarán sus transacciones asociadas.`}
          onConfirm={() => void handleDeleteConfirmed()}
          onCancel={() => setConfirmDelete({ open: false, account: null })}
        />

        <Modal
          open={isDialogOpen}
          onClose={() => {
            setIsDialogOpen(false);
            setEditingAccountId(null);
            setForm({ ...defaultForm });
          }}
          title={editingAccountId ? "Editar cuenta" : "Nueva cuenta"}
          description={
            editingAccountId
              ? "Actualiza el nombre, banco o divisa de la cuenta."
              : "Añade una cuenta para organizar mejor tus movimientos."
          }
        >
          <form className="space-y-4" onSubmit={handleSubmit}>
            <input required aria-label="Nombre de la cuenta" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} placeholder="Nombre de la cuenta" className={inputClasses} />
            <input aria-label="Banco" value={form.bank_name} onChange={(event) => setForm((current) => ({ ...current, bank_name: event.target.value }))} placeholder="Banco (opcional)" className={inputClasses} />
            <div className="grid gap-4 sm:grid-cols-2">
              <select
                aria-label="Tipo de cuenta"
                value={form.type}
                onChange={(event) => setForm((current) => ({ ...current, type: event.target.value as AccountType }))}
                className={inputClasses}
              >
                <option value="checking">{accountTypeLabels.checking}</option>
                <option value="savings">{accountTypeLabels.savings}</option>
                <option value="shared">{accountTypeLabels.shared}</option>
                <option value="other">{accountTypeLabels.other}</option>
              </select>
              <input required aria-label="Divisa" value={form.currency} onChange={(event) => setForm((current) => ({ ...current, currency: event.target.value.toUpperCase() }))} maxLength={3} placeholder="EUR" className={`${inputClasses} uppercase`} />
            </div>
            {editingAccountId ? null : (
              <input aria-label="Saldo inicial" value={form.initial_balance} onChange={(event) => setForm((current) => ({ ...current, initial_balance: event.target.value }))} inputMode="decimal" placeholder="Saldo inicial (opcional)" className={inputClasses} />
            )}
            {error ? <p className="text-sm text-[var(--app-danger)]">{error}</p> : null}
            <button type="submit" className="inline-flex w-full items-center justify-center rounded-xl bg-[var(--app-accent)] px-4 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110">
              {editingAccountId ? "Guardar cambios" : "Crear cuenta"}
            </button>
          </form>
        </Modal>

        {isLoading ? (
          <ListSkeleton rows={3} />
        ) : (
          <Card className="animate-slideUp">
            <CardHeader>
              <CardTitle>Listado</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {accounts.length ? (
                paginatedAccounts.map((account, index) => (
                  <div
                    key={account.id}
                    className={`animate-slideUp stagger-${Math.min(index + 1, 6)} relative overflow-visible rounded-[var(--app-radius-xl)] border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-5 py-4 transition-all hover:z-10 hover:bg-[var(--app-muted-surface)] hover:shadow-[var(--app-shadow)]`}
                  >
                    <div className="grid gap-4 sm:grid-cols-[minmax(0,1.45fr)_minmax(0,0.8fr)_auto] sm:items-center">
                      <div className="min-w-0 space-y-2">
                        <p className="truncate text-base font-semibold">{account.name}</p>
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-sm text-[var(--app-muted)]">
                          <span>{accountTypeLabels[account.type]}</span>
                          <span>{account.currency}</span>
                          {account.bank_name ? (
                            <span>
                              Banco:{" "}
                              <span className="font-medium text-[var(--app-text)]">
                                {account.bank_name}
                              </span>
                            </span>
                          ) : null}
                        </div>
                      </div>
                      <div className="min-w-0 rounded-2xl bg-[var(--app-panel)] px-4 py-3 text-sm">
                        <p className="text-xs uppercase tracking-[0.16em] text-[var(--app-muted)]">Saldo</p>
                        <div className="mt-2 text-lg font-semibold">
                          <AmountValue amount={balances.get(account.id) ?? 0} currency={account.currency} />
                        </div>
                      </div>
                      <div className="relative z-20 flex justify-end self-start sm:self-center">
                        <AccountActionsMenu
                          label={account.name}
                          onEdit={() => openEditDialog(account)}
                          onDelete={() => setConfirmDelete({ open: true, account })}
                        />
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <EmptyState
                  title="No hay cuentas todavía"
                  description="Crea la primera cuenta para empezar a registrar transacciones y presupuestos."
                  icon={Wallet}
                  actionLabel="Nueva cuenta"
                  onAction={openCreateDialog}
                  variant="plain"
                />
              )}

              <PaginationControls
                page={page}
                pageSize={pageSize}
                total={accounts.length}
                onPageChange={setPage}
              />
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

function AccountActionsMenu({
  label,
  onEdit,
  onDelete,
}: {
  label: string;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

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
      <button type="button" onClick={() => setIsOpen((c) => !c)} className="rounded-lg p-1 text-[var(--app-muted)] transition-all hover:bg-[var(--app-muted-surface)]" aria-label={`Acciones de cuenta ${label}`}>
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
