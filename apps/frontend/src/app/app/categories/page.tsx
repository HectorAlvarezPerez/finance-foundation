"use client";

import { FormEvent, useEffect, useEffectEvent, useMemo, useState } from "react";
import { FolderTree, Pencil, Plus, Trash2 } from "lucide-react";

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

  function openCreateDialog() {
    setError(null);
    setEditingCategoryId(null);
    setForm({ ...defaultForm });
    setIsDialogOpen(true);
  }

  function openEditDialog(category: Category) {
    setError(null);
    setEditingCategoryId(category.id);
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
      <PageHeader
        eyebrow="Categories"
        title="Categorías"
        description="Agrupa tus ingresos, gastos y transferencias con una taxonomía simple y útil."
      />

      <div className="space-y-6">
        <div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
          <div className="inline-flex rounded-xl bg-[var(--app-muted-surface)] px-3 py-1.5 text-sm text-[var(--app-muted)]">
            {categories.length} total
          </div>
          <button
            type="button"
            onClick={openCreateDialog}
            className="inline-flex items-center gap-2 rounded-xl bg-[var(--app-accent)] px-4 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110"
          >
            <Plus className="h-4 w-4" />
            Nueva categoría
          </button>
        </div>

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
            setForm({ ...defaultForm });
          }}
          title={editingCategoryId ? "Editar categoría" : "Nueva categoría"}
          description={
            editingCategoryId
              ? "Ajusta nombre, tipo o color para mantener la taxonomía ordenada."
              : "Crea una categoría para clasificar mejor ingresos, gastos o transferencias."
          }
        >
          <form className="space-y-4" onSubmit={handleSubmit}>
            <input required aria-label="Nombre de la categoría" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} placeholder="Nombre de la categoría" className={inputClasses} />
            <div className="grid gap-4 sm:grid-cols-2">
              <select aria-label="Tipo de categoría" value={form.type} onChange={(event) => setForm((current) => ({ ...current, type: event.target.value as CategoryType }))} className={inputClasses}>
                <option value="expense">Gasto</option>
                <option value="income">Ingreso</option>
                <option value="transfer">Transferencia</option>
              </select>
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
            </div>
            {error ? <p className="text-sm text-[var(--app-danger)]">{error}</p> : null}
            <button type="submit" className="inline-flex w-full items-center justify-center rounded-xl bg-[var(--app-accent)] px-4 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110">
              {editingCategoryId ? "Guardar cambios" : "Crear categoría"}
            </button>
          </form>
        </Modal>

        {isLoading ? (
          <ListSkeleton rows={4} />
        ) : categories.length ? (
          <div className="space-y-6 animate-slideUp">
            <div className="grid gap-6 lg:grid-cols-2">
              <CategoryColumn
                title="Gastos"
                description="Categorías para compras, ocio, vivienda y otros gastos."
                categories={expenseCategories}
                onEditCategory={openEditDialog}
                onDeleteCategory={(category) => setConfirmDelete({ open: true, category })}
              />
              <CategoryColumn
                title="Ingresos"
                description="Categorías para nómina, bonus y otras entradas de dinero."
                categories={incomeCategories}
                onEditCategory={openEditDialog}
                onDeleteCategory={(category) => setConfirmDelete({ open: true, category })}
              />
            </div>

            {transferCategories.length ? (
              <Card>
                <CardHeader>
                  <CardTitle>Transferencias</CardTitle>
                  <p className="text-sm text-[var(--app-muted)]">Movimientos entre cuentas o traspasos internos.</p>
                </CardHeader>
                <CardContent className="max-h-[min(60vh,32rem)] space-y-3 overflow-y-auto pr-2">
                  {transferCategories.map((category, index) => (
                    <CategoryRow
                      key={category.id}
                      category={category}
                      index={index}
                      onEdit={() => openEditDialog(category)}
                      onDelete={() => setConfirmDelete({ open: true, category })}
                    />
                  ))}
                </CardContent>
              </Card>
            ) : null}

          </div>
        ) : (
          <Card>
            <CardContent>
              <EmptyState
                title="No hay categorías todavía"
                description="Crea alguna categoría para poder clasificar presupuestos y transacciones."
                icon={FolderTree}
                actionLabel="Nueva categoría"
                onAction={openCreateDialog}
                variant="plain"
              />
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

function CategoryColumn({
  title,
  description,
  categories,
  onEditCategory,
  onDeleteCategory,
}: {
  title: string;
  description: string;
  categories: Category[];
  onEditCategory?: (category: Category) => void;
  onDeleteCategory?: (category: Category) => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <p className="text-sm text-[var(--app-muted)]">{description}</p>
      </CardHeader>
      <CardContent className="max-h-[min(70vh,42rem)] space-y-3 overflow-y-auto pr-2">
        {categories.length ? (
          categories.map((category, index) => (
            <CategoryRow
              key={category.id}
              category={category}
              index={index}
              onEdit={onEditCategory ? () => onEditCategory(category) : undefined}
              onDelete={onDeleteCategory ? () => onDeleteCategory(category) : undefined}
            />
          ))
        ) : (
          <EmptyState
            title={`Sin categorías de ${title.toLowerCase()}`}
            description="Puedes añadirlas desde el botón de nueva categoría."
            variant="plain"
          />
        )}
      </CardContent>
    </Card>
  );
}

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
  return (
    <div
      className={`animate-slideUp stagger-${Math.min(index + 1, 6)} relative overflow-visible rounded-[var(--app-radius-xl)] border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-5 py-4 transition-all hover:z-10 hover:bg-[var(--app-muted-surface)] hover:shadow-[var(--app-shadow)]`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <span
            className="mt-1 h-4 w-4 rounded-full shadow-sm"
            style={{ backgroundColor: category.color ?? "#94a3b8" }}
          />
          <div className="space-y-1">
            <p className="text-base font-semibold">{category.name}</p>
            <p className="text-sm text-[var(--app-muted)]">{categoryTypeLabels[category.type]}</p>
          </div>
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
