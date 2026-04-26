"use client";

import { FormEvent, useEffect, useEffectEvent, useRef, useState } from "react";
import {
  Building2,
  ChevronLeft,
  ChevronRight,
  CreditCard,
  MoreVertical,
  Pencil,
  PiggyBank,
  Plus,
  Trash2,
  Users,
  Wallet,
  Home,
  Car,
  Briefcase,
  ShoppingCart,
  Coins,
  Plane,
  Smartphone,
  GraduationCap,
} from "lucide-react";

import { AmountValue } from "@/components/amount-value";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { EmptyState } from "@/components/empty-state";
import { ListSkeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/page-header";
import { Modal } from "@/components/ui/modal";
import { useToast } from "@/components/ui/toast";
import { useSettings } from "@/components/settings-provider";
import { apiRequest } from "@/lib/api";
import type { Account, AccountType, PaginatedResponse, Transaction, Settings } from "@/lib/types";

type AccountFormState = {
  name: string;
  bank_name: string;
  type: AccountType;
  currency: string;
  initial_balance: string;
  color?: string | null;
  icon?: string | null;
};

const defaultForm: AccountFormState = {
  name: "",
  bank_name: "",
  type: "checking",
  currency: "EUR",
  initial_balance: "",
  color: "#1d1d1f",
  icon: "credit-card",
};

const ACCOUNT_COLORS = [
  "#0071e3", "#ff3b30", "#34c759", "#ff9f0a", "#af52de",
  "#5856d6", "#ff2d55", "#1d1d1f", "#86868b", "#00c7be"
];

const ACCOUNT_ICONS: Record<string, React.ElementType> = {
  "credit-card": CreditCard,
  "piggy-bank": PiggyBank,
  "home": Home,
  "car": Car,
  "briefcase": Briefcase,
  "shopping-cart": ShoppingCart,
  "coins": Coins,
  "plane": Plane,
  "smartphone": Smartphone,
  "graduation-cap": GraduationCap,
};

const accountTypeLabels: Record<AccountType, string> = {
  checking: "Cuenta principal",
  savings: "Ahorro",
  brokerage: "Inversión",
  shared: "Compartida",
  other: "Otra",
};

const accountTypeIcons: Record<AccountType, typeof CreditCard> = {
  checking: CreditCard,
  savings: PiggyBank,
  brokerage: Briefcase,
  shared: Users,
  other: Wallet,
};

const accountTypeGradients: Record<AccountType, { from: string; to: string; glow: string }> = {
  checking: {
    from: "hsl(220, 45%, 32%)",
    to: "hsl(245, 38%, 44%)",
    glow: "rgba(50, 70, 140, 0.35)",
  },
  savings: {
    from: "hsl(185, 40%, 30%)",
    to: "hsl(165, 35%, 40%)",
    glow: "rgba(40, 120, 110, 0.35)",
  },
  brokerage: {
    from: "hsl(34, 55%, 32%)",
    to: "hsl(14, 58%, 46%)",
    glow: "rgba(170, 105, 50, 0.35)",
  },
  shared: {
    from: "hsl(260, 35%, 36%)",
    to: "hsl(285, 30%, 46%)",
    glow: "rgba(95, 65, 140, 0.35)",
  },
  other: {
    from: "hsl(215, 18%, 34%)",
    to: "hsl(210, 20%, 46%)",
    glow: "rgba(70, 85, 110, 0.35)",
  },
};

export default function AccountsPage() {
  const { toast } = useToast();
  const { settings } = useSettings();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [form, setForm] = useState({ ...defaultForm, currency: settings?.default_currency || "EUR" });
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingAccountId, setEditingAccountId] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<{ open: boolean; account: Account | null }>({ open: false, account: null });
  const [activeIndex, setActiveIndex] = useState(0);
  const [isTransitioning, setIsTransitioning] = useState(false);

  async function loadAccounts() {
    try {
      const [accountsResponse, transactionsResponse] = await Promise.all([
        apiRequest<PaginatedResponse<Account>>("/accounts?sort_by=name&sort_order=asc&limit=100"),
        apiRequest<PaginatedResponse<Transaction>>("/transactions?limit=1000"),
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

  useEffect(() => {
    if (activeIndex >= accounts.length && accounts.length > 0) {
      setActiveIndex(accounts.length - 1);
    }
  }, [accounts.length, activeIndex]);

  // direction: +1 = next, -1 = prev — used to compute wrap-around visual offset
  const [navDirection, setNavDirection] = useState<number>(0);

  function navigateTo(index: number, direction?: number) {
    if (isTransitioning || index === activeIndex) return;
    setNavDirection(direction ?? (index > activeIndex ? 1 : -1));
    setIsTransitioning(true);
    setActiveIndex(index);
    setTimeout(() => setIsTransitioning(false), 450);
  }

  function navigatePrev() {
    if (accounts.length === 0) return;
    const next = activeIndex === 0 ? accounts.length - 1 : activeIndex - 1;
    navigateTo(next, -1);
  }

  function navigateNext() {
    if (accounts.length === 0) return;
    const next = activeIndex === accounts.length - 1 ? 0 : activeIndex + 1;
    navigateTo(next, 1);
  }

  /**
   * Compute the shortest circular offset from the active card.
   * When wrapping (e.g. last→first), the offset is +1 instead of -(n-1),
   * producing a smooth single-step slide in the correct direction.
   */
  function circularOffset(index: number): number {
    const n = accounts.length;
    if (n <= 1) return index - activeIndex;
    let diff = index - activeIndex;
    // Normalise to [-n/2, +n/2]
    if (diff > n / 2) diff -= n;
    if (diff < -n / 2) diff += n;
    return diff;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    try {
      const payload = {
        name: form.name,
        bank_name: form.bank_name.trim() || null,
        type: form.type,
        currency: form.currency.trim().toUpperCase(),
        color: form.color || null,
        icon: form.icon || null,
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

      setForm({ ...defaultForm, currency: settings?.default_currency || "EUR" });
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
    setForm({ ...defaultForm, currency: settings?.default_currency || "EUR" });
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
      color: account.color ?? defaultForm.color,
      icon: account.icon ?? defaultForm.icon,
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

  const activeAccount = accounts[activeIndex] ?? null;

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
            <select
              aria-label="Tipo de cuenta"
              value={form.type}
              onChange={(event) => setForm((current) => ({ ...current, type: event.target.value as AccountType }))}
              className={inputClasses}
            >
              <option value="checking">{accountTypeLabels.checking}</option>
              <option value="savings">{accountTypeLabels.savings}</option>
              <option value="brokerage">{accountTypeLabels.brokerage}</option>
              <option value="shared">{accountTypeLabels.shared}</option>
              <option value="other">{accountTypeLabels.other}</option>
            </select>
            {editingAccountId ? null : (
              <input aria-label="Saldo inicial" value={form.initial_balance} onChange={(event) => setForm((current) => ({ ...current, initial_balance: event.target.value }))} inputMode="decimal" placeholder="Saldo inicial (opcional)" className={inputClasses} />
            )}

            <div className="rounded-xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-4 py-3">
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-[var(--app-muted)]">Icono de la cuenta</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {Object.entries(ACCOUNT_ICONS).map(([key, IconCmp]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setForm((current) => ({ ...current, icon: key }))}
                    className={`flex h-8 w-8 items-center justify-center rounded-full text-lg transition-transform ${
                      form.icon === key
                        ? "scale-110 bg-[var(--app-surface)] shadow-[var(--app-shadow)] ring-2 ring-[var(--app-accent)] ring-offset-1 text-[var(--app-accent)]"
                        : "hover:scale-110 hover:bg-[var(--app-surface)] hover:shadow-sm text-[var(--app-muted)]"
                    }`}
                  >
                    <IconCmp className="h-4 w-4" strokeWidth={1.8} />
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-4 py-3">
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-[var(--app-muted)]">Color de la tarjeta</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {ACCOUNT_COLORS.map((color) => (
                  <button
                    key={color}
                    type="button"
                    onClick={() => setForm((current) => ({ ...current, color }))}
                    className={`h-8 w-8 rounded-full shadow-sm transition-transform ${
                      form.color === color ? "scale-110 ring-2 ring-[var(--app-accent)] ring-offset-2" : "hover:scale-110"
                    }`}
                    style={{ backgroundColor: color }}
                    aria-label={`Seleccionar color ${color}`}
                  />
                ))}
              </div>
            </div>

            {error ? <p className="text-sm text-[var(--app-danger)]">{error}</p> : null}
            <button type="submit" className="inline-flex w-full items-center justify-center rounded-xl bg-[var(--app-accent)] px-4 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110">
              {editingAccountId ? "Guardar cambios" : "Crear cuenta"}
            </button>
          </form>
        </Modal>

        {isLoading ? (
          <ListSkeleton rows={3} />
        ) : accounts.length === 0 ? (
          <div className="animate-slideUp">
            <EmptyState
              title="No hay cuentas todavía"
              description="Crea la primera cuenta para empezar a registrar transacciones y presupuestos."
              icon={Wallet}
              actionLabel="Nueva cuenta"
              onAction={openCreateDialog}
              variant="plain"
            />
          </div>
        ) : (
          <div className="animate-slideUp">
            {/* Wallet Carousel */}
            <div className="wallet-stage">
              {/* Navigation arrows */}
              {accounts.length > 1 && (
                <>
                  <button
                    type="button"
                    onClick={navigatePrev}
                    className="wallet-nav wallet-nav--prev"
                    aria-label="Cuenta anterior"
                    disabled={isTransitioning}
                  >
                    <ChevronLeft className="h-5 w-5" />
                  </button>
                  <button
                    type="button"
                    onClick={navigateNext}
                    className="wallet-nav wallet-nav--next"
                    aria-label="Cuenta siguiente"
                    disabled={isTransitioning}
                  >
                    <ChevronRight className="h-5 w-5" />
                  </button>
                </>
              )}

              {/* Cards Stack */}
              <div className="wallet-carousel">
                {accounts.map((account, index) => {
                  const offset = circularOffset(index);
                  const absOffset = Math.abs(offset);
                  const isActive = index === activeIndex;
                  const gradient = accountTypeGradients[account.type];
                  const Icon = accountTypeIcons[account.type];
                  const balance = balances.get(account.id) ?? 0;

                  // Cards beyond ±2 circular positions are hidden
                  if (absOffset > 2) return null;

                  const cardStyle: React.CSSProperties = {
                    "--card-from": account.color || gradient.from,
                    "--card-to": account.color || gradient.to,
                    "--card-glow": account.color ? "rgba(0,0,0,0.15)" : gradient.glow,
                    transform: isActive
                      ? "translateX(0) scale(1) rotateY(0deg)"
                      : `translateX(${offset * 70}%) scale(${1 - absOffset * 0.1}) rotateY(${offset * -8}deg)`,
                    zIndex: 10 - absOffset,
                    opacity: isActive ? 1 : Math.max(0.3, 1 - absOffset * 0.35),
                    filter: isActive ? "none" : `blur(${absOffset * 1.5}px)`,
                    pointerEvents: "auto",
                  } as React.CSSProperties;

                  return (
                    <div
                      key={account.id}
                      className={`wallet-card ${isActive ? "wallet-card--active" : ""}`}
                      style={cardStyle}
                      onClick={() => !isActive && navigateTo(index)}
                    >
                      {/* Card shine overlay */}
                      <div className="wallet-card__shine" />

                      {/* Card content */}
                      <div className="wallet-card__content">
                        {/* Top section: Icon + Type + Actions */}
                        <div className="wallet-card__header">
                          <div className="wallet-card__icon-wrap">
                            {(() => {
                              if (account.icon && ACCOUNT_ICONS[account.icon]) {
                                const CustomIcon = ACCOUNT_ICONS[account.icon];
                                return <CustomIcon className="h-5 w-5" strokeWidth={1.8} />;
                              }
                              return <Icon className="h-5 w-5" strokeWidth={1.8} />;
                            })()}
                          </div>
                          {isActive && (
                            <AccountActionsMenu
                              label={account.name}
                              onEdit={() => openEditDialog(account)}
                              onDelete={() => setConfirmDelete({ open: true, account })}
                            />
                          )}
                        </div>

                        {/* Type badge */}
                        <div className="wallet-card__type">
                          {accountTypeLabels[account.type]}
                        </div>

                        {/* Spacer */}
                        <div className="flex-1" />

                        {/* Bank / Currency */}
                        <div className="wallet-card__meta">
                          {account.bank_name && (
                            <div className="wallet-card__bank">
                              <Building2 className="h-3.5 w-3.5 opacity-60" />
                              <span>{account.bank_name}</span>
                            </div>
                          )}
                          <div className="wallet-card__currency">{account.currency}</div>
                        </div>

                        {/* Account name */}
                        <div className="wallet-card__name">{account.name}</div>

                        {/* Balance */}
                        <div className="wallet-card__balance">
                          <span className="wallet-card__balance-label">Saldo</span>
                          <span className="wallet-card__balance-value">
                            <AmountValue amount={balance} currency={account.currency} className="!text-white !text-2xl" />
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Dots */}
              {accounts.length > 1 && (
                <div className="wallet-dots">
                  {accounts.map((account, index) => (
                    <button
                      key={account.id}
                      type="button"
                      onClick={() => navigateTo(index)}
                      className={`wallet-dot ${index === activeIndex ? "wallet-dot--active" : ""}`}
                      aria-label={`Ir a ${account.name}`}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Account detail info below the wallet */}
            {activeAccount && (
              <div className="wallet-detail animate-fadeIn" key={activeAccount.id}>
                <div className="wallet-detail__grid">
                  <DetailCard label="Tipo" value={accountTypeLabels[activeAccount.type]} />
                  <DetailCard label="Divisa" value={activeAccount.currency} />
                  <DetailCard label="Banco" value={activeAccount.bank_name || "—"} />
                  <DetailCard
                    label="Saldo"
                    value={
                      <AmountValue
                        amount={balances.get(activeAccount.id) ?? 0}
                        currency={activeAccount.currency}
                      />
                    }
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <style>{`
        /* ─── Wallet Stage ─────────────────────────────────────── */
        .wallet-stage {
          position: relative;
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 0.75rem 0 0.5rem;
          perspective: 1200px;
        }

        /* ─── Navigation Arrows ────────────────────────────────── */
        .wallet-nav {
          position: absolute;
          top: 50%;
          transform: translateY(-70%);
          z-index: 30;
          display: flex;
          align-items: center;
          justify-content: center;
          width: 44px;
          height: 44px;
          border-radius: 50%;
          border: 1px solid var(--app-border);
          background: var(--app-glass);
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          color: var(--app-text);
          cursor: pointer;
          transition: all 250ms cubic-bezier(0.25, 0.1, 0.25, 1);
          box-shadow: var(--app-shadow);
        }
        .wallet-nav:hover {
          background: var(--app-panel-strong);
          box-shadow: var(--app-shadow-elevated);
          transform: translateY(-70%) scale(1.08);
        }
        .wallet-nav:active {
          transform: translateY(-70%) scale(0.95);
        }
        .wallet-nav:disabled {
          opacity: 0.4;
          pointer-events: none;
        }
        .wallet-nav--prev {
          left: 0;
        }
        .wallet-nav--next {
          right: 0;
        }
        @media (min-width: 768px) {
          .wallet-nav--prev {
            left: 1rem;
          }
          .wallet-nav--next {
            right: 1rem;
          }
        }

        /* ─── Carousel Container ──────────────────────────────── */
        .wallet-carousel {
          position: relative;
          width: 220px;
          height: 280px;
          transform-style: preserve-3d;
        }
        @media (min-width: 640px) {
          .wallet-carousel {
            width: 240px;
            height: 310px;
          }
        }

        /* ─── Individual Card ─────────────────────────────────── */
        .wallet-card {
          position: absolute;
          inset: 0;
          border-radius: 24px;
          overflow: hidden;
          cursor: pointer;
          transition:
            transform 450ms cubic-bezier(0.34, 1.56, 0.64, 1),
            opacity 400ms cubic-bezier(0.25, 0.1, 0.25, 1),
            filter 400ms cubic-bezier(0.25, 0.1, 0.25, 1),
            box-shadow 400ms cubic-bezier(0.25, 0.1, 0.25, 1);

          background: linear-gradient(
            165deg,
            var(--card-from) 0%,
            var(--card-to) 100%
          );
          box-shadow:
            0 4px 24px var(--card-glow),
            0 1px 3px rgba(0, 0, 0, 0.08),
            inset 0 1px 0 rgba(255, 255, 255, 0.15);
        }
        .wallet-card--active {
          box-shadow:
            0 8px 48px var(--card-glow),
            0 2px 8px rgba(0, 0, 0, 0.1),
            inset 0 1px 0 rgba(255, 255, 255, 0.2);
        }
        .wallet-card--active:hover {
          transform: translateX(0) scale(1.02) rotateY(0deg) !important;
        }

        /* Card shine */
        .wallet-card__shine {
          position: absolute;
          inset: 0;
          background: linear-gradient(
            135deg,
            rgba(255, 255, 255, 0.18) 0%,
            rgba(255, 255, 255, 0.05) 40%,
            transparent 60%,
            rgba(255, 255, 255, 0.03) 100%
          );
          pointer-events: none;
          z-index: 1;
        }

        /* Card content */
        .wallet-card__content {
          position: relative;
          z-index: 2;
          display: flex;
          flex-direction: column;
          height: 100%;
          padding: 1.1rem 1.25rem;
          color: white;
        }

        /* Card header */
        .wallet-card__header {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
        }

        /* Card icon */
        .wallet-card__icon-wrap {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 36px;
          height: 36px;
          border-radius: 11px;
          background: rgba(255, 255, 255, 0.18);
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
        }

        /* Card type */
        .wallet-card__type {
          margin-top: 0.5rem;
          font-size: 0.7rem;
          font-weight: 500;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          opacity: 0.7;
        }

        /* Card meta */
        .wallet-card__meta {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 0.25rem;
        }
        .wallet-card__bank {
          display: flex;
          align-items: center;
          gap: 0.35rem;
          font-size: 0.8rem;
          opacity: 0.8;
        }
        .wallet-card__currency {
          font-size: 0.8rem;
          font-weight: 600;
          letter-spacing: 0.05em;
          opacity: 0.8;
          background: rgba(255, 255, 255, 0.15);
          padding: 0.15rem 0.5rem;
          border-radius: 6px;
        }

        /* Card name */
        .wallet-card__name {
          font-size: 1rem;
          font-weight: 700;
          margin-top: 0.3rem;
          line-height: 1.3;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        /* Card balance */
        .wallet-card__balance {
          margin-top: 0.5rem;
          padding: 0.6rem 0.75rem;
          border-radius: 14px;
          background: rgba(255, 255, 255, 0.12);
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
        }
        .wallet-card__balance-label {
          display: block;
          font-size: 0.65rem;
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.15em;
          opacity: 0.7;
          margin-bottom: 0.15rem;
        }
        .wallet-card__balance-value {
          display: block;
          font-size: 1.25rem;
          font-weight: 700;
          letter-spacing: -0.02em;
        }

        /* ─── Dots ────────────────────────────────────────────── */
        .wallet-dots {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          margin-top: 0.75rem;
        }
        .wallet-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          border: none;
          padding: 0;
          background: var(--app-muted);
          opacity: 0.3;
          cursor: pointer;
          transition: all 300ms cubic-bezier(0.25, 0.1, 0.25, 1);
        }
        .wallet-dot:hover {
          opacity: 0.6;
          transform: scale(1.2);
        }
        .wallet-dot--active {
          width: 24px;
          border-radius: 4px;
          background: var(--app-accent);
          opacity: 1;
        }

        /* ─── Detail Section ──────────────────────────────────── */
        .wallet-detail {
          margin-top: 0.75rem;
        }
        .wallet-detail__grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 0.75rem;
        }
        @media (min-width: 640px) {
          .wallet-detail__grid {
            grid-template-columns: repeat(4, 1fr);
          }
        }

        .wallet-detail-card {
          padding: 1rem 1.15rem;
          border-radius: var(--app-radius-xl);
          background: var(--app-panel-strong);
          border: 1px solid var(--app-border);
          transition: all 250ms cubic-bezier(0.25, 0.1, 0.25, 1);
        }
        .wallet-detail-card:hover {
          background: var(--app-muted-surface);
          box-shadow: var(--app-shadow);
        }
        .wallet-detail-card__label {
          font-size: 0.7rem;
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.14em;
          color: var(--app-muted);
          margin-bottom: 0.35rem;
        }
        .wallet-detail-card__value {
          font-size: 0.95rem;
          font-weight: 600;
          color: var(--app-text);
        }
      `}</style>
    </div>
  );
}

/* ─── Detail Card ─────────────────────────────────────────── */
function DetailCard({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="wallet-detail-card">
      <div className="wallet-detail-card__label">{label}</div>
      <div className="wallet-detail-card__value">{value}</div>
    </div>
  );
}

/* ─── Account Actions Menu ────────────────────────────────── */
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
      <button
        type="button"
        onClick={() => setIsOpen((c) => !c)}
        className="rounded-lg p-1.5 text-white/70 transition-all hover:bg-white/15 hover:text-white"
        aria-label={`Acciones de cuenta ${label}`}
      >
        <MoreVertical className="h-4 w-4" />
      </button>
      {isOpen ? (
        <div className="animate-slideDown absolute right-0 z-[80] mt-1 min-w-40 rounded-xl border border-white/15 bg-black/60 p-1 shadow-[var(--app-shadow-elevated)] backdrop-blur-xl">
          <button type="button" onClick={() => runAndClose(onEdit)} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-white/90 transition-all hover:bg-white/15">
            <Pencil className="h-4 w-4" /> Editar
          </button>
          <button type="button" onClick={() => runAndClose(onDelete)} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-red-400 transition-all hover:bg-red-500/15">
            <Trash2 className="h-4 w-4" /> Eliminar
          </button>
        </div>
      ) : null}
    </div>
  );
}
