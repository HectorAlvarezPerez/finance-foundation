"use client";

import { FormEvent, useEffect, useEffectEvent, useMemo, useRef, useState } from "react";
import { FolderTree, Info, Pencil, Plus, Trash2 } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { ActionMenu } from "@/components/ui/action-menu";
import { EmptyState } from "@/components/empty-state";
import { ListSkeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/page-header";
import { Modal } from "@/components/ui/modal";
import { useToast } from "@/components/ui/toast";
import { apiRequest } from "@/lib/api";
import type { Category, CategoryType, PaginatedResponse } from "@/lib/types";

type CategoryFormState = {
  name: string;
  type: CategoryType;
  color: string;
};

const defaultForm: CategoryFormState = {
  name: "",
  type: "expense",
  color: "#0c7c59",
};

const categoryColorOptions = [
  "#0c7c59", "#2563eb", "#7c3aed", "#db2777", "#dc2626",
  "#ea580c", "#ca8a04", "#16a34a", "#0891b2", "#64748b",
];

const categoryTypeLabels: Record<CategoryType, string> = {
  expense: "Gasto",
  income: "Ingreso",
  transfer: "Transferencia",
};

export default function CategoriesPage() {
  const { toast } = useToast();
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [form, setForm] = useState({ ...defaultForm });
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingCategoryId, setEditingCategoryId] = useState<string | null>(null);
  const [lockedType, setLockedType] = useState<CategoryType | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<{ open: boolean; category: Category | null }>({
    open: false,
    category: null,
  });

  async function loadCategories() {
    try {
      const response = await apiRequest<PaginatedResponse<Category>>("/categories?sort_by=name&sort_order=asc");
      setCategories(response.items);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No se pudieron cargar las categorías");
    } finally {
      setIsLoading(false);
    }
  }

  const loadCategoriesOnMount = useEffectEvent(async () => {
    await loadCategories();
  });

  useEffect(() => {
    void loadCategoriesOnMount();
  }, []);

  const expenseCategories = useMemo(
    () => categories.filter((category) => category.type === "expense"),
    [categories],
  );
  const incomeCategories = useMemo(
    () => categories.filter((category) => category.type === "income"),
    [categories],
  );
  const transferCategories = useMemo(
    () => categories.filter((category) => category.type === "transfer"),
    [categories],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    try {
      if (editingCategoryId) {
        await apiRequest<Category>(`/categories/${editingCategoryId}`, {
          method: "PATCH",
          body: JSON.stringify(form),
        });
        toast("Categoría actualizada", "success");
      } else {
        await apiRequest<Category>("/categories", {
          method: "POST",
          body: JSON.stringify(form),
        });
        toast("Categoría creada", "success");
      }

      setForm({ ...defaultForm });
      setEditingCategoryId(null);
      setLockedType(null);
      setIsDialogOpen(false);
      await loadCategories();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : editingCategoryId
            ? "No se pudo actualizar la categoría"
            : "No se pudo crear la categoría",
      );
    }
  }

  function openCreateDialog(type: CategoryType) {
    setError(null);
    setEditingCategoryId(null);
    setLockedType(type);
    setForm({ ...defaultForm, type });
    setIsDialogOpen(true);
  }

  function openEditDialog(category: Category) {
    setError(null);
    setEditingCategoryId(category.id);
    setLockedType(null); // allow type edit when editing
    setForm({
      name: category.name,
      type: category.type,
      color: category.color ?? defaultForm.color,
    });
    setIsDialogOpen(true);
  }

  async function handleDeleteConfirmed() {
    const category = confirmDelete.category;
    setConfirmDelete({ open: false, category: null });
    if (!category) {
      return;
    }

    setError(null);

    try {
      await apiRequest<void>(`/categories/${category.id}`, {
        method: "DELETE",
        skipJson: true,
      });
      toast(`Categoría "${category.name}" eliminada`, "success");
      await loadCategories();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No se pudo eliminar la categoría");
    }
  }

  const inputClasses = "w-full rounded-xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-4 py-2.5 outline-none transition-all focus:border-[var(--app-accent)] focus:shadow-[0_0_0_3px_var(--app-accent-soft)]";

  return (
    <div>
      <div className="relative">
        <PageHeader
          eyebrow="Categories"
          title="Categorías"
          description="Agrupa tus ingresos, gastos y transferencias con una taxonomía simple y útil."
        />
        {!isLoading && categories.length > 0 && (
          <span className="absolute right-0 top-0 inline-flex rounded-xl bg-[var(--app-muted-surface)] px-3 py-1.5 text-sm text-[var(--app-muted)]">
            {categories.length} categorías
          </span>
        )}
      </div>

      <div className="space-y-6">
        <ConfirmDialog
          open={confirmDelete.open}
          title="Eliminar categoría"
          description={`¿Quieres eliminar la categoría "${confirmDelete.category?.name ?? ""}"?`}
          onConfirm={() => void handleDeleteConfirmed()}
          onCancel={() => setConfirmDelete({ open: false, category: null })}
        />

        <Modal
          open={isDialogOpen}
          onClose={() => {
            setIsDialogOpen(false);
            setEditingCategoryId(null);
            setLockedType(null);
            setForm({ ...defaultForm });
          }}
          title={editingCategoryId ? "Editar categoría" : `Nueva categoría · ${categoryTypeLabels[form.type]}`}
          description={
            editingCategoryId
              ? "Ajusta nombre, tipo o color para mantener la taxonomía ordenada."
              : "Añade un nombre y elige el color que mejor identifique esta categoría."
          }
        >
          <form className="space-y-4" onSubmit={handleSubmit}>
            <input
              required
              aria-label="Nombre de la categoría"
              value={form.name}
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              placeholder="Nombre de la categoría"
              className={inputClasses}
            />

            {/* Type selector: visible only when editing (not locked) */}
            {lockedType === null ? (
              <select
                aria-label="Tipo de categoría"
                value={form.type}
                onChange={(event) => setForm((current) => ({ ...current, type: event.target.value as CategoryType }))}
                className={inputClasses}
              >
                <option value="expense">Gasto</option>
                <option value="income">Ingreso</option>
                <option value="transfer">Transferencia</option>
              </select>
            ) : (
              <div className="flex items-center gap-3 rounded-xl border border-[var(--app-border)] bg-[var(--app-muted-surface)] px-4 py-2.5">
                <span className="text-sm text-[var(--app-muted)]">Tipo</span>
                <span className="rounded-lg bg-[var(--app-accent-soft)] px-2.5 py-1 text-sm font-semibold text-[var(--app-accent)]">
                  {categoryTypeLabels[lockedType]}
                </span>
                <span className="ml-auto text-xs text-[var(--app-muted)]">bloqueado</span>
              </div>
            )}

            <div className="rounded-xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-4 py-3">
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-[var(--app-muted)]">Color</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {categoryColorOptions.map((color) => {
                  const isSelected = form.color === color;
                  return (
                    <button
                      key={color}
                      type="button"
                      onClick={() => setForm((current) => ({ ...current, color }))}
                      className={`h-8 w-8 rounded-full border-2 transition-all ${
                        isSelected
                          ? "scale-110 border-[var(--app-ink)] shadow-md"
                          : "border-transparent hover:scale-105"
                      }`}
                      style={{ backgroundColor: color }}
                      aria-label={`Seleccionar color ${color}`}
                      aria-pressed={isSelected}
                    />
                  );
                })}
              </div>
            </div>

            {error ? <p className="text-sm text-[var(--app-danger)]">{error}</p> : null}
            <button
              type="submit"
              className="inline-flex w-full items-center justify-center rounded-xl bg-[var(--app-accent)] px-4 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110"
            >
              {editingCategoryId ? "Guardar cambios" : "Crear categoría"}
            </button>
          </form>
        </Modal>

        {isLoading ? (
          <ListSkeleton rows={4} />
        ) : categories.length ? (
          <div className="space-y-6 animate-slideUp">
            {/* Top row: Income + Transfers side by side, equal height */}
            <div className="relative z-10 grid gap-6 lg:grid-cols-2">
              <CategorySection
                title="Ingresos"
                description="Nómina, bonus y otras entradas de dinero."
                type="income"
                categories={incomeCategories}
                onOpenCreate={openCreateDialog}
                onEditCategory={openEditDialog}
                onDeleteCategory={(category) => setConfirmDelete({ open: true, category })}
              />
              <CategorySection
                title="Transferencias"
                description="Movimientos entre tus propias cuentas."
                type="transfer"
                categories={transferCategories}
                onOpenCreate={openCreateDialog}
                onEditCategory={openEditDialog}
                onDeleteCategory={(category) => setConfirmDelete({ open: true, category })}
                showTransferInfo
              />
            </div>

            {/* Bottom: Expenses in 3 columns */}
            <CategorySection
              title="Gastos"
              description="Compras, ocio, vivienda y otros gastos recurrentes."
              type="expense"
              categories={expenseCategories}
              onOpenCreate={openCreateDialog}
              onEditCategory={openEditDialog}
              onDeleteCategory={(category) => setConfirmDelete({ open: true, category })}
              columns={3}
            />
          </div>
        ) : (
          <Card>
            <CardContent>
              <EmptyState
                title="No hay categorías todavía"
                description="Crea alguna categoría para poder clasificar presupuestos y transacciones."
                icon={FolderTree}
                actionLabel="Nueva categoría de gasto"
                onAction={() => openCreateDialog("expense")}
                variant="plain"
              />
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

/* ─── CategorySection ──────────────────────────────────────── */

function TransferInfoTooltip() {
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    function handleClick(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [isOpen]);

  return (
    <div ref={ref} className="relative inline-flex">
      <button
        type="button"
        aria-label="¿Qué es una categoría de transferencia?"
        onClick={() => setIsOpen((v) => !v)}
        className="flex h-5 w-5 items-center justify-center rounded-full text-[var(--app-muted)] transition-colors hover:text-[var(--app-accent)]"
      >
        <Info className="h-3.5 w-3.5" />
      </button>
      {isOpen && (
        <div className="animate-slideDown absolute left-1/2 top-7 z-[200] w-72 -translate-x-1/2 rounded-2xl border border-[var(--app-border)] bg-[var(--app-glass)] p-4 shadow-[var(--app-shadow-elevated)] backdrop-blur-xl">
          <p className="text-xs font-semibold text-[var(--app-ink)]">¿Qué es una transferencia?</p>
          <p className="mt-1.5 text-xs leading-relaxed text-[var(--app-muted)]">
            Las categorías de transferencia se usan para movimientos <strong className="text-[var(--app-ink)]">entre tus propias cuentas</strong>, como pasar dinero de una cuenta corriente a una de ahorro. No se contabilizan como ingreso ni gasto para no distorsionar tus estadísticas.
          </p>
        </div>
      )}
    </div>
  );
}

function CategorySection({
  title,
  description,
  type,
  categories,
  onOpenCreate,
  onEditCategory,
  onDeleteCategory,
  showTransferInfo = false,
  columns = 1,
}: {
  title: string;
  description: string;
  type: CategoryType;
  categories: Category[];
  onOpenCreate: (type: CategoryType) => void;
  onEditCategory: (category: Category) => void;
  onDeleteCategory: (category: Category) => void;
  showTransferInfo?: boolean;
  columns?: 1 | 3;
}) {
  return (
    <Card className="flex flex-col">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <CardTitle>{title}</CardTitle>
            {showTransferInfo && <TransferInfoTooltip />}
          </div>
          <p className="text-sm text-[var(--app-muted)]">{description}</p>
        </div>
        <button
          type="button"
          onClick={() => onOpenCreate(type)}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-xl bg-[var(--app-accent)] px-3 py-1.5 text-xs font-semibold text-white transition-all hover:brightness-110"
        >
          <Plus className="h-3.5 w-3.5" />
          Añadir
        </button>
      </CardHeader>
      <CardContent className="flex-1">
        {categories.length ? (
          <div
            className={`space-y-3 ${
              columns === 3
                ? "grid gap-3 space-y-0 sm:grid-cols-2 lg:grid-cols-3"
                : ""
            }`}
          >
            {categories.map((category, index) => (
              <CategoryRow
                key={category.id}
                category={category}
                index={index}
                onEdit={() => onEditCategory(category)}
                onDelete={() => onDeleteCategory(category)}
              />
            ))}
          </div>
        ) : (
          <EmptyState
            title={`Sin categorías de ${title.toLowerCase()}`}
            description="Pulsa «Nueva» para añadir la primera."
            variant="plain"
          />
        )}
      </CardContent>
    </Card>
  );
}

/* ─── CategoryRow ──────────────────────────────────────────── */

function CategoryRow({
  category,
  index = 0,
  onEdit,
  onDelete,
}: {
  category: Category;
  index?: number;
  onEdit?: () => void;
  onDelete?: () => void;
}) {
  const color = category.color ?? "#94a3b8";

  return (
    <div
      className={`animate-slideUp stagger-${Math.min(index + 1, 6)} relative overflow-hidden rounded-[var(--app-radius-xl)] border bg-[var(--app-panel-strong)] px-5 py-4 transition-all hover:z-10 hover:shadow-[var(--app-shadow)]`}
      style={{
        borderColor: `color-mix(in srgb, ${color} 25%, var(--app-border))`,
      }}
    >
      {/* Colour gradient band */}
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-full"
        style={{
          background: `linear-gradient(135deg, color-mix(in srgb, ${color} 14%, transparent) 0%, transparent 60%)`,
        }}
      />

      <div className="relative flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span
            className="h-3 w-3 shrink-0 rounded-full shadow-sm ring-2 ring-white/20"
            style={{ backgroundColor: color }}
          />
          <p className="text-sm font-semibold">{category.name}</p>
        </div>
        {onEdit && onDelete ? (
          <div className="relative z-20">
            <ActionMenu
              label={category.name}
              ariaLabel={`Acciones de categoría ${category.name}`}
              actions={[
                { label: "Editar", icon: <Pencil className="h-4 w-4" />, onClick: onEdit },
                { label: "Eliminar", icon: <Trash2 className="h-4 w-4" />, onClick: onDelete, danger: true },
              ]}
            />
          </div>
        ) : null}
      </div>
    </div>
  );
}
