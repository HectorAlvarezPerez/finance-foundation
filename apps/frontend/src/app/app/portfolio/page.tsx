"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MoreVertical, Pencil, Plus, RefreshCw, Trash2, TrendingUp } from "lucide-react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { AmountValue } from "@/components/amount-value";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { CardSkeleton, ListSkeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/page-header";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Modal } from "@/components/ui/modal";
import { useToast } from "@/components/ui/toast";
import { useSettings } from "@/components/settings-provider";
import { apiRequest } from "@/lib/api";
import type { PortfolioHolding, PortfolioSummary, PriceRefreshResponse } from "@/lib/types";

const ASSET_TYPE_LABELS: Record<string, string> = {
  index_fund: "Fondo indexado",
  bond_fund: "Fondo de bonos",
  crypto: "Cripto",
  stock: "Acción",
  gold: "Oro",
  etf: "ETF",
};

const ASSET_TYPE_OPTIONS = Object.entries(ASSET_TYPE_LABELS).map(([value, label]) => ({
  value,
  label,
}));

// Deshabilitado hasta tener la API key de precios (Twelve Data). Poner a true para reactivar.
const PRICE_REFRESH_ENABLED = false;

const ALLOCATION_PALETTE = [
  "#6366f1",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#06b6d4",
  "#a855f7",
  "#ec4899",
  "#84cc16",
];

type HoldingFormState = {
  asset_name: string;
  asset_symbol: string;
  asset_type: string;
  quantity: string;
  average_buy_price: string;
  currency: string;
};

const emptyForm = (currency: string): HoldingFormState => ({
  asset_name: "",
  asset_symbol: "",
  asset_type: "etf",
  quantity: "",
  average_buy_price: "",
  currency,
});

export default function PortfolioPage() {
  const { toast } = useToast();
  const { settings } = useSettings();
  const defaultCurrency = settings?.default_currency || "EUR";

  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<HoldingFormState>(emptyForm(defaultCurrency));

  const [priceModal, setPriceModal] = useState<{ id: string; name: string; value: string } | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<{ id: string; name: string } | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await apiRequest<PortfolioSummary>("/portfolio/summary");
      setSummary(data);
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No se pudo cargar la cartera");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const holdings = useMemo(() => summary?.holdings ?? [], [summary]);

  const totals = useMemo(() => {
    const value = Number(summary?.total_value ?? 0);
    const invested = Number(summary?.total_invested ?? 0);
    const pnl = Number(summary?.total_unrealized_pnl ?? 0);
    const pnlPct = invested > 0 ? (pnl / invested) * 100 : 0;
    return { value, invested, pnl, pnlPct };
  }, [summary]);

  const allocationData = useMemo(
    () =>
      holdings
        .filter((holding) => holding.allocation_pct > 0)
        .map((holding, index) => ({
          name: holding.asset_name,
          value: holding.allocation_pct,
          fill: ALLOCATION_PALETTE[index % ALLOCATION_PALETTE.length],
        })),
    [holdings],
  );

  const byType = useMemo(() => {
    const totalsByType = new Map<string, number>();
    holdings.forEach((holding) => {
      totalsByType.set(
        holding.asset_type,
        (totalsByType.get(holding.asset_type) ?? 0) + holding.allocation_pct,
      );
    });
    return [...totalsByType.entries()]
      .map(([type, pct]) => ({ type, pct }))
      .sort((left, right) => right.pct - left.pct);
  }, [holdings]);

  async function handleRefreshPrices() {
    setIsRefreshing(true);
    setError(null);
    try {
      const result = await apiRequest<PriceRefreshResponse>("/portfolio/prices/refresh", {
        method: "POST",
      });
      const updated = result.updated.length;
      const failed = result.failed.length;
      if (updated > 0) {
        toast(`Precios actualizados: ${updated}${failed ? ` · ${failed} sin actualizar` : ""}`, "success");
      } else if (failed > 0) {
        toast(`No se pudo actualizar ningún precio (${failed})`, "error");
      } else {
        toast("No hay activos con símbolo para actualizar", "success");
      }
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No se pudieron actualizar los precios");
    } finally {
      setIsRefreshing(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const body = JSON.stringify({
      asset_name: form.asset_name,
      asset_symbol: form.asset_symbol.trim() ? form.asset_symbol.trim().toUpperCase() : null,
      asset_type: form.asset_type,
      quantity: form.quantity,
      average_buy_price: form.average_buy_price,
      currency: form.currency,
    });

    try {
      if (editingId) {
        await apiRequest(`/portfolio/holdings/${editingId}`, { method: "PATCH", body });
        toast("Inversión actualizada", "success");
      } else {
        await apiRequest("/portfolio/holdings", { method: "POST", body });
        toast("Inversión añadida", "success");
      }
      setIsDialogOpen(false);
      setEditingId(null);
      setForm(emptyForm(defaultCurrency));
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No se pudo guardar la inversión");
    }
  }

  function openCreate() {
    setEditingId(null);
    setError(null);
    setForm(emptyForm(defaultCurrency));
    setIsDialogOpen(true);
  }

  function openEdit(holding: PortfolioHolding) {
    setEditingId(holding.id);
    setError(null);
    setForm({
      asset_name: holding.asset_name,
      asset_symbol: holding.asset_symbol ?? "",
      asset_type: holding.asset_type,
      quantity: String(holding.quantity),
      average_buy_price: String(holding.average_buy_price),
      currency: holding.currency,
    });
    setIsDialogOpen(true);
  }

  async function handlePriceSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!priceModal) {
      return;
    }
    setError(null);
    try {
      await apiRequest(`/portfolio/holdings/${priceModal.id}/price`, {
        method: "POST",
        body: JSON.stringify({ price: priceModal.value }),
      });
      toast("Precio actualizado", "success");
      setPriceModal(null);
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No se pudo actualizar el precio");
    }
  }

  async function handleDeleteConfirmed() {
    if (!confirmDelete) {
      return;
    }
    const id = confirmDelete.id;
    setConfirmDelete(null);
    try {
      await apiRequest(`/portfolio/holdings/${id}`, { method: "DELETE", skipJson: true });
      toast("Inversión eliminada", "success");
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No se pudo eliminar la inversión");
    }
  }

  const inputClasses =
    "w-full rounded-xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-4 py-2.5 outline-none transition-all focus:border-[var(--app-accent)] focus:shadow-[0_0_0_3px_var(--app-accent-soft)]";

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Inversiones"
        title="Tu cartera"
        description="Cuánto tienes en cada activo, qué porcentaje representa de tu cartera y cuánto ha ganado o perdido."
      />

      <div className="flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={() => void handleRefreshPrices()}
          disabled={!PRICE_REFRESH_ENABLED || isRefreshing}
          title={
            PRICE_REFRESH_ENABLED
              ? undefined
              : "Disponible cuando se configure la API key de precios"
          }
          className="inline-flex items-center gap-2 rounded-xl border border-[var(--app-border)] bg-[var(--app-panel)] px-3.5 py-2 text-sm font-medium text-[var(--app-foreground)] transition-all hover:border-[var(--app-accent)] hover:text-[var(--app-accent)] disabled:cursor-not-allowed disabled:opacity-60"
        >
          <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
          {!PRICE_REFRESH_ENABLED
            ? "Actualizar precios (pronto)"
            : isRefreshing
              ? "Actualizando..."
              : "Actualizar precios"}
        </button>
        <button
          type="button"
          onClick={openCreate}
          className="inline-flex items-center gap-2 rounded-xl bg-[var(--app-accent)] px-3.5 py-2 text-sm font-medium text-white transition-all hover:brightness-110"
        >
          <Plus className="h-4 w-4" />
          Nueva inversión
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
          <SummaryCard title={`Valor total (${defaultCurrency})`} value={totals.value} currency={defaultCurrency} tone="neutral" />
          <SummaryCard title={`Invertido (${defaultCurrency})`} value={totals.invested} currency={defaultCurrency} tone="neutral" />
          <SummaryCard
            title={`Ganancia / Pérdida (${defaultCurrency})${totals.invested > 0 ? ` · ${totals.pnlPct >= 0 ? "+" : ""}${totals.pnlPct.toFixed(1)}%` : ""}`}
            value={totals.pnl}
            currency={defaultCurrency}
            tone={totals.pnl >= 0 ? "success" : "danger"}
            signed
          />
        </section>
      )}

      {!isLoading && holdings.length ? (
        <Card className="animate-slideUp">
          <CardHeader>
            <CardTitle className="text-lg">Distribución</CardTitle>
            <p className="mt-1 text-xs text-[var(--app-muted)]">
              Peso de cada activo y por tipo, sobre el valor total ({defaultCurrency}).
            </p>
          </CardHeader>
          <CardContent>
            <div className="grid items-center gap-6 md:grid-cols-2">
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={allocationData}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={55}
                      outerRadius={85}
                      paddingAngle={2}
                      stroke="none"
                    >
                      {allocationData.map((entry) => (
                        <Cell key={entry.name} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-3">
                <p className="text-xs font-medium uppercase tracking-[0.14em] text-[var(--app-muted)]">
                  Por tipo de activo
                </p>
                {byType.map((entry) => (
                  <div key={entry.type} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium text-[var(--app-ink)]">
                        {ASSET_TYPE_LABELS[entry.type] ?? entry.type}
                      </span>
                      <span className="tabular-nums text-[var(--app-muted)]">
                        {entry.pct.toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-[color-mix(in_srgb,var(--app-muted-surface)_80%,transparent)]">
                      <div
                        className="h-2 rounded-full bg-[var(--app-accent)]"
                        style={{ width: `${Math.min(Math.max(entry.pct, 0), 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <Modal
        open={isDialogOpen}
        onClose={() => {
          setIsDialogOpen(false);
          setEditingId(null);
        }}
        title={editingId ? "Editar inversión" : "Nueva inversión"}
        description="El precio actual se actualiza por separado desde cada activo."
      >
        <form className="space-y-4" onSubmit={handleSubmit}>
          <input
            required
            aria-label="Nombre del activo"
            value={form.asset_name}
            onChange={(event) => setForm((current) => ({ ...current, asset_name: event.target.value }))}
            placeholder="Nombre del activo (p. ej. Vanguard All-World)"
            className={inputClasses}
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <input
              aria-label="Símbolo del activo"
              value={form.asset_symbol}
              onChange={(event) => setForm((current) => ({ ...current, asset_symbol: event.target.value }))}
              placeholder="Símbolo (VWCE, BTC...)"
              className={`${inputClasses} uppercase`}
            />
            <select
              aria-label="Tipo de activo"
              value={form.asset_type}
              onChange={(event) => setForm((current) => ({ ...current, asset_type: event.target.value }))}
              className={inputClasses}
            >
              {ASSET_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <input
              required
              aria-label="Cantidad"
              value={form.quantity}
              onChange={(event) => setForm((current) => ({ ...current, quantity: event.target.value }))}
              placeholder="Cantidad"
              className={inputClasses}
            />
            <input
              required
              aria-label="Precio medio de compra"
              value={form.average_buy_price}
              onChange={(event) => setForm((current) => ({ ...current, average_buy_price: event.target.value }))}
              placeholder="Precio medio de compra"
              className={inputClasses}
            />
          </div>
          <input
            required
            aria-label="Divisa"
            value={form.currency}
            maxLength={3}
            onChange={(event) => setForm((current) => ({ ...current, currency: event.target.value.toUpperCase() }))}
            className={`${inputClasses} uppercase`}
          />
          {error ? <p className="text-sm text-[var(--app-danger)]">{error}</p> : null}
          <button
            type="submit"
            className="inline-flex w-full items-center justify-center rounded-xl bg-[var(--app-accent)] px-4 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110"
          >
            {editingId ? "Guardar cambios" : "Añadir inversión"}
          </button>
        </form>
      </Modal>

      <Modal
        open={priceModal !== null}
        onClose={() => setPriceModal(null)}
        title="Actualizar precio actual"
        description={priceModal ? `Precio actual de ${priceModal.name}` : ""}
      >
        <form className="space-y-4" onSubmit={handlePriceSubmit}>
          <input
            required
            autoFocus
            aria-label="Precio actual"
            value={priceModal?.value ?? ""}
            onChange={(event) =>
              setPriceModal((current) => (current ? { ...current, value: event.target.value } : current))
            }
            placeholder="Precio actual por unidad"
            className={inputClasses}
          />
          {error ? <p className="text-sm text-[var(--app-danger)]">{error}</p> : null}
          <button
            type="submit"
            className="inline-flex w-full items-center justify-center rounded-xl bg-[var(--app-accent)] px-4 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110"
          >
            Guardar precio
          </button>
        </form>
      </Modal>

      <ConfirmDialog
        open={confirmDelete !== null}
        title="Eliminar inversión"
        description={`¿Eliminar ${confirmDelete?.name ?? "esta inversión"}? Esta acción no se puede deshacer.`}
        onConfirm={() => void handleDeleteConfirmed()}
        onCancel={() => setConfirmDelete(null)}
      />

      {isLoading ? (
        <ListSkeleton rows={4} />
      ) : holdings.length ? (
        <Card className="animate-slideUp">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg">Activos</CardTitle>
              <p className="mt-1 text-xs text-[var(--app-muted)]">
                Valor actual basado en el último precio que hayas introducido.
              </p>
            </div>
            <div className="rounded-full bg-[var(--app-muted-surface)] px-2.5 py-1 text-xs text-[var(--app-muted)]">
              {holdings.length} activos
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {holdings.map((holding, index) => (
              <HoldingRow
                key={holding.id}
                holding={holding}
                index={index}
                currency={defaultCurrency}
                onEdit={() => openEdit(holding)}
                onUpdatePrice={() =>
                  setPriceModal({
                    id: holding.id,
                    name: holding.asset_name,
                    value: holding.current_price ? String(holding.current_price) : "",
                  })
                }
                onDelete={() => setConfirmDelete({ id: holding.id, name: holding.asset_name })}
              />
            ))}
          </CardContent>
        </Card>
      ) : (
        <EmptyState
          title="Aún no tienes inversiones"
          description="Añade tu primer activo y registra su precio actual para ver el valor y el peso en tu cartera."
          icon={TrendingUp}
          actionLabel="Nueva inversión"
          onAction={openCreate}
          variant="plain"
        />
      )}
    </div>
  );
}

function SummaryCard({
  title,
  value,
  currency,
  tone,
  signed,
}: {
  title: string;
  value: number;
  currency: string;
  tone: "neutral" | "success" | "danger";
  signed?: boolean;
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
          {signed && value > 0 ? "+" : ""}
          <AmountValue amount={value} currency={currency} className="![color:inherit]" />
        </p>
      </CardContent>
    </Card>
  );
}

function HoldingRow({
  holding,
  index,
  currency,
  onEdit,
  onUpdatePrice,
  onDelete,
}: {
  holding: PortfolioHolding;
  index: number;
  currency: string;
  onEdit: () => void;
  onUpdatePrice: () => void;
  onDelete: () => void;
}) {
  const pnl = holding.unrealized_pnl !== null ? Number(holding.unrealized_pnl) : null;
  const value = holding.current_value !== null ? Number(holding.current_value) : null;
  const allocationWidth = `${Math.min(Math.max(holding.allocation_pct, 0), 100)}%`;

  return (
    <div
      className={`animate-slideUp stagger-${Math.min(index + 1, 6)} rounded-2xl border border-[var(--app-border)] bg-[var(--app-panel)] p-4`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-base font-semibold text-[var(--app-ink)]">{holding.asset_name}</h3>
            {holding.asset_symbol ? (
              <span className="rounded-md bg-[var(--app-muted-surface)] px-1.5 py-0.5 text-[11px] font-medium text-[var(--app-muted)]">
                {holding.asset_symbol}
              </span>
            ) : null}
            {holding.currency !== currency ? (
              <span
                className="rounded-md bg-[var(--app-warning-soft)] px-1.5 py-0.5 text-[11px] font-medium text-[var(--app-warning)]"
                title={`Este activo está en ${holding.currency}; el total se convierte a ${currency} si tienes un tipo de cambio`}
              >
                en {holding.currency}
              </span>
            ) : null}
          </div>
          <p className="mt-0.5 text-xs text-[var(--app-muted)]">
            {ASSET_TYPE_LABELS[holding.asset_type] ?? holding.asset_type} ·{" "}
            {holding.quantity} uds · coste medio{" "}
            <AmountValue amount={Number(holding.average_buy_price)} currency={holding.currency} className="!text-[var(--app-muted)]" />
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <div className="text-right">
            <p className="text-sm font-semibold text-[var(--app-ink)]">
              {value !== null ? (
                <AmountValue amount={value} currency={holding.currency} className="!text-[var(--app-ink)]" />
              ) : (
                <span className="text-[var(--app-muted)]">Sin precio</span>
              )}
            </p>
            {pnl !== null ? (
              <p className={`text-xs font-medium ${pnl >= 0 ? "text-[var(--app-success)]" : "text-[var(--app-danger)]"}`}>
                {pnl >= 0 ? "+" : ""}
                <AmountValue amount={pnl} currency={holding.currency} className="![color:inherit]" />
              </p>
            ) : null}
          </div>
          <HoldingActionsMenu
            label={holding.asset_name}
            onEdit={onEdit}
            onUpdatePrice={onUpdatePrice}
            onDelete={onDelete}
          />
        </div>
      </div>

      <div className="mt-3 flex items-center gap-3">
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-[color-mix(in_srgb,var(--app-muted-surface)_80%,transparent)]">
          <div
            className="h-2 rounded-full bg-[var(--app-accent)] transition-[width] duration-700 ease-out"
            style={{ width: allocationWidth }}
          />
        </div>
        <span className="shrink-0 text-xs font-semibold text-[var(--app-muted)] tabular-nums">
          {holding.allocation_pct.toFixed(1)}% de la cartera
        </span>
      </div>
    </div>
  );
}

function HoldingActionsMenu({
  label,
  onEdit,
  onUpdatePrice,
  onDelete,
}: {
  label: string;
  onEdit: () => void;
  onUpdatePrice: () => void;
  onDelete: () => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [menuPos, setMenuPos] = useState<{ top: number; right: number } | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    function handleClick(event: MouseEvent) {
      if (
        menuRef.current &&
        !menuRef.current.contains(event.target as Node) &&
        triggerRef.current &&
        !triggerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setIsOpen(false);
    }

    function handleScroll() {
      setIsOpen(false);
    }

    document.addEventListener("click", handleClick);
    document.addEventListener("keydown", handleKeyDown);
    window.addEventListener("scroll", handleScroll, true);
    return () => {
      document.removeEventListener("click", handleClick);
      document.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("scroll", handleScroll, true);
    };
  }, [isOpen]);

  function openMenu() {
    if (!triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    setMenuPos({
      top: rect.bottom + 4,
      right: window.innerWidth - rect.right,
    });
    setIsOpen(true);
  }

  function runAndClose(action: () => void) {
    action();
    setIsOpen(false);
  }

  return (
    <div>
      <button
        ref={triggerRef}
        type="button"
        onClick={openMenu}
        className="rounded-lg p-1 text-[var(--app-muted)] transition-all hover:bg-[var(--app-muted-surface)]"
        aria-label={`Acciones de inversión ${label}`}
      >
        <MoreVertical className="h-4 w-4" />
      </button>
      {isOpen && menuPos ? (
        <div
          ref={menuRef}
          className="animate-slideDown fixed z-[200] min-w-48 rounded-xl border border-[var(--app-border)] bg-[var(--app-glass)] p-1 shadow-[var(--app-shadow-elevated)] backdrop-blur-xl"
          style={{ top: menuPos.top, right: menuPos.right }}
        >
          <button type="button" onClick={() => runAndClose(onUpdatePrice)} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-all hover:bg-[var(--app-muted-surface)]">
            <RefreshCw className="h-4 w-4" /> Actualizar precio
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
