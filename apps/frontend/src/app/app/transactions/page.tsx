"use client";

import { FormEvent, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import useSWR from "swr";
import {
  AlertCircle,
  ArrowLeftRight,
  Check,
  ChevronDown,
  Copy,
  CreditCard,
  FileSpreadsheet,
  FileUp,
  LoaderCircle,
  Pencil,
  Plus,
  TrendingDown,
  TrendingUp,
  Trash2,
  Upload,
  X,
} from "lucide-react";

import { AmountValue } from "@/components/amount-value";
import { CategoryBadge } from "@/components/category-badge";
import { EmptyState } from "@/components/empty-state";
import { ErrorScreen } from "@/components/error-screen";
import { PageHeader } from "@/components/page-header";
import { ActionMenu } from "@/components/ui/action-menu";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSettings } from "@/components/settings-provider";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Modal } from "@/components/ui/modal";
import { PaginationControls } from "@/components/ui/pagination-controls";
import { ListSkeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { apiRequest } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { Account, Category, PaginatedResponse, Transaction } from "@/lib/types";

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
type TransactionKind = "expense" | "income" | "transfer";

type TransactionImportMapping = {
  date: string;
  amount: string;
  description: string;
  category: string;
  notes: string;
};

type TransactionImportAnalysis = {
  source_type: "csv" | "excel" | "pdf";
  columns: string[];
  sample_rows: Array<Record<string, string>>;
  suggested_mapping: TransactionImportMapping;
  total_rows: number;
  message?: string | null;
};

type TransactionImportPreviewRow = {
  id: string;
  sourceRowNumber: number;
  accountId: string;
  categoryId: string;
  categoryLabel: string;
  categorySuggestionLabel: string;
  categorySuggestionSource: string;
  categoryIsSuggested: boolean;
  date: string;
  amount: string;
  currency: string;
  description: string;
  notes: string;
  validationErrors: string[];
};

type TransactionImportPreview = {
  sourceType: "csv" | "excel" | "pdf";
  accountId: string;
  accountCurrency: string;
  importedCount: number;
  rows: TransactionImportPreviewRow[];
};

type TransactionImportFileMeta = {
  name: string;
  size: number;
};

type PersistedImportDialogState = {
  isOpen: boolean;
  accountId: string;
  analysis: TransactionImportAnalysis | null;
  mapping: TransactionImportMapping;
  step: 1 | 2;
  fileMeta: TransactionImportFileMeta | null;
};

const IMPORT_PREVIEW_STORAGE_KEY = "transactions-import-preview-v1";
const IMPORT_DIALOG_STORAGE_KEY = "transactions-import-dialog-v1";

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

  const {
    data: transData,
    error: transError,
    mutate: mutateTrans,
  } = useSWR<PaginatedResponse<Transaction>>(
    `/transactions?${transactionQuery}`,
    fetcher,
    { keepPreviousData: true },
  );
  const { data: accData, error: accError } = useSWR<PaginatedResponse<Account>>(
    "/accounts?limit=100&sort_by=name&sort_order=asc",
    fetcher,
  );
  const { data: catData, error: catError } = useSWR<PaginatedResponse<Category>>(
    "/categories?limit=100&sort_by=name&sort_order=asc",
    fetcher,
  );

  const transactions = transData?.items || [];
  const totalTransactions = transData?.total || 0;
  const accounts = accData?.items || [];
  const categories = catData?.items || [];
  const isLoading = !transData || !accData || !catData;
  const loadError = transError || accError || catError;

  const { settings } = useSettings();

  useEffect(() => {
    if (settings) {
      setImportAutoCategorize(!!settings.auto_categorize);
    }
  }, [settings]);

  const [form, setForm] = useState(() => defaultTransactionForm(settings?.default_currency || "EUR"));
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [editorMode, setEditorMode] = useState<TransactionEditorMode>("create");
  const [editingTransactionId, setEditingTransactionId] = useState<string | null>(null);
  const [transactionKind, setTransactionKind] = useState<TransactionKind>("expense");
  const [isTypePickerOpen, setIsTypePickerOpen] = useState(false);
  const typePickerRef = useRef<HTMLDivElement | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<{ open: boolean; ids: string[] }>({
    open: false,
    ids: [],
  });

  const [isImportDialogOpen, setIsImportDialogOpen] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importFileMeta, setImportFileMeta] = useState<TransactionImportFileMeta | null>(null);
  const [importAccountId, setImportAccountId] = useState("");
  const [importAnalysis, setImportAnalysis] = useState<TransactionImportAnalysis | null>(null);
  const [importMapping, setImportMapping] = useState<TransactionImportMapping>(defaultImportMapping());
  const [importPreview, setImportPreview] = useState<TransactionImportPreview | null>(null);
  const [isAnalyzingImport, setIsAnalyzingImport] = useState(false);
  const [isPreparingPreview, setIsPreparingPreview] = useState(false);
  const [isConfirmingImport, setIsConfirmingImport] = useState(false);
  const [importStep, setImportStep] = useState<1 | 2>(1);
  const [isDragging, setIsDragging] = useState(false);
  const [isReplaceImportDialogOpen, setIsReplaceImportDialogOpen] = useState(false);
  const [importAutoCategorize, setImportAutoCategorize] = useState<boolean>(true);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const accountMap = new Map(accounts.map((account) => [account.id, account]));
  const categoryMap = new Map(categories.map((category) => [category.id, category]));
  const selectedCount = selectedIds.length;

  // Close type picker on outside click
  useEffect(() => {
    if (!isTypePickerOpen) return;
    function onDown(e: MouseEvent) {
      if (typePickerRef.current && !typePickerRef.current.contains(e.target as Node)) {
        setIsTypePickerOpen(false);
      }
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [isTypePickerOpen]);

  // Filtered categories for the selected transaction kind
  const kindCategories = useMemo(
    () => categories.filter((c) => c.type === transactionKind),
    [categories, transactionKind],
  );
  const allVisibleSelected =
    transactions.length > 0 &&
    transactions.every((transaction) => selectedIds.includes(transaction.id));

  const reviewStats = useMemo(() => {
    if (!importPreview) {
      return { readyCount: 0, reviewCount: 0 };
    }

    return importPreview.rows.reduce(
      (acc, row) => {
        if (row.validationErrors.length === 0) {
          acc.readyCount += 1;
        } else {
          acc.reviewCount += 1;
        }
        return acc;
      },
      { readyCount: 0, reviewCount: 0 },
    );
  }, [importPreview]);

  const yearOptions = useMemo(() => {
    const currentYear = new Date().getFullYear();
    return Array.from({ length: 4 }, (_, index) => String(currentYear - index));
  }, []);

  useEffect(() => {
    const storedPreview = window.sessionStorage.getItem(IMPORT_PREVIEW_STORAGE_KEY);
    if (storedPreview) {
      try {
        const parsedPreview = JSON.parse(storedPreview) as TransactionImportPreview;
        setImportPreview({
          ...parsedPreview,
          rows: parsedPreview.rows.map((row) => normalizeImportPreviewRow(row)),
        });
        toast("Se ha recuperado una revisión de importación pendiente", "info");
      } catch {
        window.sessionStorage.removeItem(IMPORT_PREVIEW_STORAGE_KEY);
      }
    }

    const storedDialog = window.sessionStorage.getItem(IMPORT_DIALOG_STORAGE_KEY);
    if (!storedDialog) {
      return;
    }

    try {
      const dialogState = JSON.parse(storedDialog) as PersistedImportDialogState;
      setIsImportDialogOpen(dialogState.isOpen);
      setImportAccountId(dialogState.accountId);
      setImportAnalysis(dialogState.analysis);
      setImportMapping(dialogState.mapping);
      setImportStep(dialogState.step);
      setImportFileMeta(dialogState.fileMeta);
      if (dialogState.isOpen) {
        toast("Se ha recuperado el borrador del flujo de importación", "info");
      }
    } catch {
      window.sessionStorage.removeItem(IMPORT_DIALOG_STORAGE_KEY);
    }
  }, [toast]);

  useEffect(() => {
    if (importPreview) {
      window.sessionStorage.setItem(IMPORT_PREVIEW_STORAGE_KEY, JSON.stringify(importPreview));
      return;
    }

    window.sessionStorage.removeItem(IMPORT_PREVIEW_STORAGE_KEY);
  }, [importPreview]);

  useEffect(() => {
    const shouldPersistDialog =
      isImportDialogOpen ||
      importAnalysis !== null ||
      importStep !== 1 ||
      importAccountId !== "" ||
      importFileMeta !== null;

    if (!shouldPersistDialog) {
      window.sessionStorage.removeItem(IMPORT_DIALOG_STORAGE_KEY);
      return;
    }

    const dialogState: PersistedImportDialogState = {
      isOpen: isImportDialogOpen,
      accountId: importAccountId,
      analysis: importAnalysis,
      mapping: importMapping,
      step: importStep,
      fileMeta: importFileMeta,
    };
    window.sessionStorage.setItem(IMPORT_DIALOG_STORAGE_KEY, JSON.stringify(dialogState));
  }, [importAccountId, importAnalysis, importFileMeta, importMapping, importStep, isImportDialogOpen]);

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
      // Apply sign based on kind only for fresh creations.
      // For duplicate/edit, preserve the exact user-entered sign/value.
      const rawAmount = parseFloat(form.amount.replace(",", "."));
      const normalizedAmount =
        editorMode === "create"
          ? transactionKind === "expense"
            ? -Math.abs(rawAmount)
            : Math.abs(rawAmount)
          : form.amount;

      const payload = {
        ...form,
        amount: String(normalizedAmount),
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
        toast(
          editorMode === "duplicate" ? "Copia creada" : "Transacción creada",
          "success",
        );
      }

      setForm((current) => defaultTransactionForm(settings?.default_currency || "EUR", current.account_id));
      setEditorMode("create");
      setEditingTransactionId(null);
      setIsDialogOpen(false);
      await mutateTrans();
    } catch (requestError) {
      toast(requestError instanceof Error ? requestError.message : "Error al guardar", "error");
    }
  }

  function handleOpenCreate(kind: TransactionKind) {
    setTransactionKind(kind);
    setEditorMode("create");
    setEditingTransactionId(null);
    setForm(defaultTransactionForm(settings?.default_currency || "EUR", form.account_id));
    setIsTypePickerOpen(false);
    setIsDialogOpen(true);
  }

  function handleOpenImport() {
    if (!accounts.length) {
      toast("Necesitas al menos una cuenta antes de importar transacciones", "error");
      return;
    }

    if (importPreview) {
      setIsReplaceImportDialogOpen(true);
      return;
    }

    setIsImportDialogOpen(true);
    setImportAccountId((current) => current || filters.account_id || accounts[0]?.id || "");
  }

  function handleConfirmReplaceImport() {
    setImportPreview(null);
    setIsReplaceImportDialogOpen(false);
    setIsImportDialogOpen(true);
    setImportAccountId((current) => current || filters.account_id || accounts[0]?.id || "");
  }

  function resetImportDialog() {
    setIsImportDialogOpen(false);
    setImportFile(null);
    setImportFileMeta(null);
    setImportAnalysis(null);
    setImportMapping(defaultImportMapping());
    setIsAnalyzingImport(false);
    setIsPreparingPreview(false);
    setImportStep(1);
    setIsDragging(false);
  }

  function handleFileDrop(droppedFile: File) {
    const validExtensions = [".csv", ".xlsx", ".xlsm", ".xltx", ".xltm", ".pdf"];
    const extension = droppedFile.name.slice(droppedFile.name.lastIndexOf(".")).toLowerCase();
    if (!validExtensions.includes(extension)) {
      toast("Formato no soportado. Usa CSV, Excel o PDF.", "error");
      return;
    }
    void handleImportFileChange(droppedFile);
  }

  function removeImportFile() {
    setImportFile(null);
    setImportFileMeta(null);
    setImportAnalysis(null);
    setImportMapping(defaultImportMapping());
    setImportStep(1);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  async function handleImportFileChange(file: File | null) {
    setImportFile(file);
    setImportFileMeta(file ? { name: file.name, size: file.size } : null);
    setImportAnalysis(null);
    setImportMapping(defaultImportMapping());

    if (!file) {
      return;
    }

    setIsAnalyzingImport(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const analysis = await apiRequest<TransactionImportAnalysis>("/transactions/import/analyze", {
        method: "POST",
        body: formData,
      });
      setImportAnalysis(analysis);
      setImportMapping({
        date: analysis.suggested_mapping.date || "",
        amount: analysis.suggested_mapping.amount || "",
        description: analysis.suggested_mapping.description || "",
        category: analysis.suggested_mapping.category || "",
        notes: analysis.suggested_mapping.notes || "",
      });
      if (analysis.message) {
        toast(analysis.message, "success");
      }
    } catch (requestError) {
      toast(
        requestError instanceof Error ? requestError.message : "No se pudo analizar el archivo",
        "error",
      );
    } finally {
      setIsAnalyzingImport(false);
    }
  }

  async function handlePrepareImportPreview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!importFile) {
      toast("Vuelve a seleccionar el archivo para continuar con la importación", "error");
      return;
    }

    if (!importAccountId) {
      toast("Selecciona la cuenta de destino para las transacciones importadas", "error");
      return;
    }

    setIsPreparingPreview(true);
    try {
      const formData = new FormData();
      formData.append("file", importFile);
      formData.append("account_id", importAccountId);
      formData.append("mapping", JSON.stringify(importMapping));
      formData.append("auto_categorize", String(importAutoCategorize));

      const response = await apiRequest<{
        source_type: "csv" | "excel" | "pdf";
        account_id: string;
        account_currency: string;
        imported_count: number;
        skipped_duplicates: number;
        rows: Array<{
          source_row_number: number;
          account_id: string;
          category_id: string | null;
          category_label: string | null;
          category_suggestion_label: string | null;
          category_suggestion_source: string | null;
          category_is_suggested: boolean;
          date: string | null;
          amount: string | null;
          currency: string;
          description: string | null;
          notes: string | null;
          validation_errors: string[];
        }>;
      }>("/transactions/import/preview", {
        method: "POST",
        body: formData,
      });

      setImportPreview({
        sourceType: response.source_type,
        accountId: response.account_id,
        accountCurrency: response.account_currency,
        importedCount: response.imported_count,
        rows: response.rows.map((row) =>
          normalizeImportPreviewRow({
            id: `import-${row.source_row_number}-${crypto.randomUUID()}`,
            sourceRowNumber: row.source_row_number,
            accountId: row.account_id,
            categoryId: row.category_id ?? "",
            categoryLabel: row.category_label ?? "",
            categorySuggestionLabel: row.category_suggestion_label ?? "",
            categorySuggestionSource: row.category_suggestion_source ?? "",
            categoryIsSuggested: row.category_is_suggested,
            date: row.date ?? "",
            amount: row.amount ?? "",
            currency: row.currency,
            description: row.description ?? "",
            notes: row.notes ?? "",
            validationErrors: row.validation_errors,
          }),
        ),
      });

      resetImportDialog();
      toast("Preview de importación preparado", "success");
    } catch (requestError) {
      toast(
        requestError instanceof Error
          ? requestError.message
          : "No se pudo preparar la revisión de la importación",
        "error",
      );
    } finally {
      setIsPreparingPreview(false);
    }
  }

  function updateImportRow(
    rowId: string,
    updater: (row: TransactionImportPreviewRow) => TransactionImportPreviewRow,
  ) {
    setImportPreview((current) => {
      if (!current) {
        return current;
      }
      return {
        ...current,
        rows: current.rows.map((row) =>
          row.id === rowId ? normalizeImportPreviewRow(updater(row)) : row,
        ),
      };
    });
  }

  function discardImportRow(rowId: string) {
    setImportPreview((current) => {
      if (!current) {
        return current;
      }
      return {
        ...current,
        rows: current.rows.filter((row) => row.id !== rowId),
      };
    });
  }

  async function handleConfirmImport() {
    if (!importPreview) {
      return;
    }

    const readyRows = importPreview.rows.filter((row) => row.validationErrors.length === 0);
    if (!readyRows.length) {
      toast("No hay filas listas para importar todavía", "error");
      return;
    }

    setIsConfirmingImport(true);
    try {
      const payload = {
        items: readyRows.map((row) => ({
          source_row_number: row.sourceRowNumber,
          account_id: row.accountId,
          category_id: row.categoryId || null,
          date: row.date,
          amount: row.amount,
          currency: row.currency,
          description: row.description,
          notes: row.notes || null,
        })),
      };

      const response = await apiRequest<{
        imported_count: number;
        skipped_duplicates: number;
      }>("/transactions/import/commit", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      const remainingRows = importPreview.rows.filter((row) => row.validationErrors.length > 0);
      setImportPreview(
        remainingRows.length
          ? { ...importPreview, rows: remainingRows, importedCount: remainingRows.length }
          : null,
      );
      await mutateTrans();
      if (response.skipped_duplicates) {
        toast(
          `${response.imported_count} transacciones añadidas y ${response.skipped_duplicates} duplicadas omitidas`,
          "success",
        );
      } else {
        toast(`${response.imported_count} transacciones añadidas`, "success");
      }
    } catch (requestError) {
      toast(
        requestError instanceof Error ? requestError.message : "No se pudieron importar las filas",
        "error",
      );
    } finally {
      setIsConfirmingImport(false);
    }
  }

  function handleOpenEdit(transaction: Transaction) {
    setEditorMode("edit");
    setEditingTransactionId(transaction.id);
    setForm(transactionToForm(transaction));
    setIsDialogOpen(true);
  }

  function handleOpenDuplicate(transaction: Transaction) {
    const sourceKind = inferTransactionKind(transaction, categoryMap);
    setTransactionKind(sourceKind);
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
      allVisibleSelected
        ? current.filter((id) => !transactions.some((transaction) => transaction.id === id))
        : [...current, ...transactions.map((t) => t.id).filter((id) => !current.includes(id))],
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
      toast(
        ids.length === 1 ? "Transacción eliminada" : `${ids.length} transacciones eliminadas`,
        "success",
      );
      await mutateTrans();
    } catch (requestError) {
      toast(requestError instanceof Error ? requestError.message : "Error al eliminar", "error");
    }
  }

  const inputClasses =
    "w-full rounded-xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-4 py-2.5 outline-none transition-all focus:border-[var(--app-accent)] focus:shadow-[0_0_0_3px_var(--app-accent-soft)]";

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
              onClick={handleOpenImport}
              className="inline-flex items-center gap-2 rounded-xl border border-[var(--app-border)] bg-[var(--app-panel)] px-4 py-2.5 text-sm font-semibold text-[var(--app-foreground)] transition-all hover:border-[var(--app-accent)] hover:text-[var(--app-accent)]"
            >
              <FileUp className="h-4 w-4" />
              Import transactions
            </button>
            <div ref={typePickerRef} className="relative">
              <div className="inline-flex rounded-xl bg-[var(--app-accent)] shadow-sm transition-all hover:brightness-110">
                <button
                  type="button"
                  onClick={() => handleOpenCreate("expense")}
                  className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-semibold text-white rounded-l-xl outline-none"
                >
                  <Plus className="h-4 w-4" />
                  Nueva transacción
                </button>
                <div className="my-1.5 w-[1px] bg-white/20" />
                <button
                  type="button"
                  onClick={() => setIsTypePickerOpen((v) => !v)}
                  className="inline-flex items-center justify-center px-2 text-white rounded-r-xl outline-none"
                  aria-label="Seleccionar tipo de transacción"
                >
                  <ChevronDown className="h-4 w-4" />
                </button>
              </div>
              {isTypePickerOpen && (
                <div className="animate-slideDown absolute right-0 top-full z-50 mt-2 w-52 overflow-hidden rounded-2xl border border-[var(--app-border)] bg-[var(--app-glass)] shadow-[var(--app-shadow-elevated)] backdrop-blur-xl">
                  {([
                    { kind: "expense" as const, label: "Gasto", icon: <TrendingDown className="h-4 w-4" />, color: "var(--app-danger)", bg: "var(--app-danger-soft)" },
                    { kind: "income" as const, label: "Ingreso", icon: <TrendingUp className="h-4 w-4" />, color: "var(--app-success)", bg: "var(--app-success-soft)" },
                    { kind: "transfer" as const, label: "Transferencia", icon: <ArrowLeftRight className="h-4 w-4" />, color: "var(--app-accent)", bg: "var(--app-accent-soft)" },
                  ] as const).map((opt) => (
                    <button
                      key={opt.kind}
                      type="button"
                      onClick={() => handleOpenCreate(opt.kind)}
                      className="flex w-full items-center gap-3 px-4 py-3 text-sm font-medium transition-colors hover:bg-[var(--app-muted-surface)]"
                    >
                      <span
                        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg"
                        style={{ background: opt.bg, color: opt.color }}
                      >
                        {opt.icon}
                      </span>
                      {opt.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
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

        <ConfirmDialog
          open={isReplaceImportDialogOpen}
          title="Descartar revisión pendiente"
          description="Ya tienes una revisión temporal sin confirmar. Si sigues, se descartará ese borrador y empezarás una nueva importación."
          confirmLabel="Descartar y continuar"
          onConfirm={handleConfirmReplaceImport}
          onCancel={() => setIsReplaceImportDialogOpen(false)}
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
                : (
                  <div className="flex items-center gap-2">
                    <span>Nueva transacción</span>
                    {(() => {
                      const kinds = [
                        { kind: "expense" as const, label: "Gasto", icon: <TrendingDown className="h-3.5 w-3.5" />, color: "var(--app-danger)", bg: "var(--app-danger-soft)" },
                        { kind: "income" as const, label: "Ingreso", icon: <TrendingUp className="h-3.5 w-3.5" />, color: "var(--app-success)", bg: "var(--app-success-soft)" },
                        { kind: "transfer" as const, label: "Transferencia", icon: <ArrowLeftRight className="h-3.5 w-3.5" />, color: "var(--app-accent)", bg: "var(--app-accent-soft)" },
                      ] as const;
                      const active = kinds.find((k) => k.kind === transactionKind)!;
                      return (
                        <span
                          className="flex items-center gap-1.5 rounded-lg px-2 py-0.5 text-xs font-semibold"
                          style={{ background: active.bg, color: active.color }}
                        >
                          {active.icon}
                          {active.label}
                        </span>
                      );
                    })()}
                  </div>
                )
          }
          description={
            editorMode === "edit"
              ? "Actualiza la información y guarda los cambios."
              : editorMode === "duplicate"
                ? "Partimos de una transacción existente para crear una nueva."
                : transactionKind === "expense"
                  ? "El importe se registrará como negativo automáticamente."
                  : transactionKind === "income"
                    ? "El importe se registrará como positivo automáticamente."
                    : "Movimiento entre tus propias cuentas."
          }
        >
          <form className="space-y-4" onSubmit={handleSubmit}>

            <div className="grid gap-4 sm:grid-cols-2">
              <select
                required
                aria-label="Cuenta de la transacción"
                value={form.account_id}
                onChange={(event) => {
                  const nextAccountId = event.target.value;
                  const nextAccountCurrency =
                    accounts.find((account) => account.id === nextAccountId)?.currency ?? form.currency;
                  setForm((current) => ({
                    ...current,
                    account_id: nextAccountId,
                    currency: nextAccountCurrency,
                  }));
                }}
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
                {(editorMode === "create" ? kindCategories : categories).map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <input
                required
                aria-label="Fecha de la transacción"
                type="date"
                value={form.date}
                onChange={(event) => setForm((current) => ({ ...current, date: event.target.value }))}
                className={inputClasses}
              />
              {/* Amount: user enters positive value; sign applied from kind on submit */}
              <div className="relative">
                <span
                  className="absolute left-4 top-1/2 -translate-y-1/2 text-sm font-bold"
                  style={{ color: transactionKind === "expense" ? "var(--app-danger)" : transactionKind === "income" ? "var(--app-success)" : "var(--app-accent)" }}
                >
                  {editorMode === "create" ? (transactionKind === "expense" ? "−" : "+") : ""}
                </span>
                <input
                  required
                  aria-label="Importe de la transacción"
                  value={form.amount}
                  onChange={(event) => setForm((current) => ({ ...current, amount: event.target.value }))}
                  placeholder="48.90"
                  className={`${inputClasses} pl-8`}
                />
              </div>
            </div>

            <input
              required
              aria-label="Descripción de la transacción"
              value={form.description}
              onChange={(event) =>
                setForm((current) => ({ ...current, description: event.target.value }))
              }
              placeholder="Descripción"
              className={inputClasses}
            />
            <textarea
              aria-label="Notas de la transacción"
              value={form.notes}
              onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
              rows={2}
              placeholder="Notas (opcional)"
              className={inputClasses}
            />
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

        <Modal
          open={isImportDialogOpen}
          onClose={resetImportDialog}
          title="Importar transacciones"
          description="Sube un archivo, revisa el mapeo y prepara las transacciones."
          dialogClassName="w-[min(96vw,1200px)] max-w-none"
        >
          <form className="px-1 sm:px-2" onSubmit={handlePrepareImportPreview}>
            {/* ── Stepper ── */}
            <div className="mb-8 flex items-center justify-center gap-0">
              {[
                { step: 1 as const, label: "Sube archivo" },
                { step: 2 as const, label: "Mapea columnas" },
              ].map(({ step, label }, idx) => {
                const isActive = importStep === step;
                const isCompleted = importStep > step;
                return (
                  <div key={step} className="flex items-center gap-0">
                    <div className="flex items-center gap-2.5">
                      <div
                        className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold transition-all duration-300 ${
                          isCompleted
                            ? "bg-[var(--app-accent)] text-white shadow-[0_0_0_4px_var(--app-accent-soft)]"
                            : isActive
                              ? "bg-[var(--app-accent)] text-white shadow-[0_0_0_4px_var(--app-accent-soft)]"
                              : "bg-[var(--app-muted-surface)] text-[var(--app-muted)]"
                        }`}
                      >
                        {isCompleted ? <Check className="h-3.5 w-3.5" /> : step}
                      </div>
                      <span
                        className={`text-sm font-medium transition-colors duration-300 ${
                          isActive || isCompleted
                            ? "text-[var(--app-foreground)]"
                            : "text-[var(--app-muted)]"
                        }`}
                      >
                        {label}
                      </span>
                    </div>
                    {idx < 1 ? (
                      <div
                        className={`mx-4 h-px w-12 transition-colors duration-300 ${
                          isCompleted
                            ? "bg-[var(--app-accent)]"
                            : "bg-[var(--app-border)]"
                        }`}
                      />
                    ) : null}
                  </div>
                );
              })}
            </div>

            {/* ── Step 1: Upload ── */}
            {importStep === 1 ? (
              <div className="animate-fadeIn space-y-5">
                {/* Account selector */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-[var(--app-foreground)]">
                    Cuenta de destino
                  </label>
                  <select
                    required
                    value={importAccountId}
                    onChange={(event) => setImportAccountId(event.target.value)}
                    className={inputClasses}
                  >
                    <option value="">Selecciona cuenta</option>
                    {accounts.map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.name} · {account.currency}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="import-auto-categorize"
                    checked={importAutoCategorize}
                    onChange={(e) => setImportAutoCategorize(e.target.checked)}
                    className="h-4 w-4 rounded border-[var(--app-border)] bg-[var(--app-panel)] text-[var(--app-accent)] focus:ring-[var(--app-accent)] outline-none"
                  />
                  <label htmlFor="import-auto-categorize" className="text-sm font-medium text-[var(--app-foreground)]">
                    Categorizar automáticamente las transacciones con IA
                  </label>
                </div>

                {/* Hidden file input */}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,.xlsx,.xlsm,.xltx,.xltm,.pdf"
                  className="hidden"
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) handleFileDrop(file);
                  }}
                />

                {/* Drag-and-drop zone OR file chip */}
                {!importFile ? (
                  <div className="space-y-4">
                    {importFileMeta ? (
                      <div className="rounded-2xl border border-[var(--app-border)] bg-[var(--app-muted-surface)] px-4 py-3 text-sm text-[var(--app-muted)]">
                        <p className="font-medium text-[var(--app-foreground)]">
                          Archivo recuperado: {importFileMeta.name}
                        </p>
                        <p className="mt-1 text-xs">
                          Por seguridad, vuelve a seleccionarlo antes de preparar la revisión.
                        </p>
                      </div>
                    ) : null}
                    <div
                      onDragOver={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setIsDragging(true);
                      }}
                      onDragLeave={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setIsDragging(false);
                      }}
                      onDrop={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setIsDragging(false);
                        const file = e.dataTransfer.files[0];
                        if (file) handleFileDrop(file);
                      }}
                      onClick={() => fileInputRef.current?.click()}
                      className={`group flex cursor-pointer flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed px-6 py-12 text-center transition-all duration-300 ${
                        isDragging
                          ? "border-[var(--app-accent)] bg-[var(--app-accent-soft)] scale-[1.01]"
                          : "border-[var(--app-border)] bg-[var(--app-muted-surface)] hover:border-[var(--app-accent)] hover:bg-[var(--app-accent-soft)]"
                      }`}
                    >
                      <div
                        className={`flex h-14 w-14 items-center justify-center rounded-2xl transition-all duration-300 ${
                          isDragging
                            ? "bg-[var(--app-accent)] text-white scale-110"
                            : "bg-[var(--app-panel)] text-[var(--app-muted)] group-hover:bg-[var(--app-accent)] group-hover:text-white"
                        }`}
                      >
                        <Upload className="h-6 w-6" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[var(--app-foreground)]">
                          {isDragging
                            ? "Suelta el archivo aquí"
                            : "Arrastra tu archivo aquí"}
                        </p>
                        <p className="mt-1 text-xs text-[var(--app-muted)]">
                          o haz clic para seleccionar
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="rounded-lg bg-[var(--app-panel)] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--app-muted)]">
                          CSV
                        </span>
                        <span className="rounded-lg bg-[var(--app-panel)] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--app-muted)]">
                          Excel
                        </span>
                        <span className="rounded-lg bg-[var(--app-panel)] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--app-muted)]">
                          PDF
                        </span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="animate-fadeIn">
                    {/* File chip */}
                    <div className="flex items-center gap-3 rounded-2xl border border-[var(--app-border)] bg-[var(--app-panel)] px-4 py-3">
                      <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-[var(--app-accent-soft)] text-[var(--app-accent)]">
                        <FileSpreadsheet className="h-5 w-5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-[var(--app-foreground)]">
                          {importFile.name}
                        </p>
                        <p className="text-xs text-[var(--app-muted)]">
                          {formatFileSize(importFile.size)}
                        </p>
                      </div>
                      {isAnalyzingImport ? (
                        <div className="flex items-center gap-2 text-xs text-[var(--app-accent)]">
                          <LoaderCircle className="h-4 w-4 animate-spin" />
                          Analizando…
                        </div>
                      ) : importAnalysis ? (
                        <div className="flex items-center gap-2">
                          <div className="flex items-center gap-1.5 text-xs text-[var(--app-accent)]">
                            <Check className="h-3.5 w-3.5" />
                            {importAnalysis.total_rows} filas · {importAnalysis.source_type.toUpperCase()}
                          </div>
                        </div>
                      ) : null}
                      <button
                        type="button"
                        onClick={removeImportFile}
                        className="flex-shrink-0 rounded-lg p-1.5 text-[var(--app-muted)] transition-all hover:bg-[var(--app-danger-soft)] hover:text-[var(--app-danger)]"
                        aria-label="Quitar archivo"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>

                  </div>
                )}

                {/* Next step button */}
                {importAnalysis && importAnalysis.sample_rows.length ? (
                  <button
                    type="button"
                    onClick={() => setImportStep(2)}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-[var(--app-accent)] px-4 py-3 text-sm font-semibold text-white transition-all hover:brightness-110"
                  >
                    Siguiente: mapear columnas
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                    </svg>
                  </button>
                ) : null}
              </div>
            ) : null}

            {/* ── Step 2: Mapping + Preview ── */}
            {importStep === 2 && importAnalysis ? (
              <div className="animate-fadeIn space-y-5">
                {/* Back button */}
                <button
                  type="button"
                  onClick={() => setImportStep(1)}
                  className="inline-flex items-center gap-1.5 text-sm text-[var(--app-muted)] transition-colors hover:text-[var(--app-foreground)]"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M11 17l-5-5m0 0l5-5m-5 5h12" />
                  </svg>
                  Volver al archivo
                </button>

                {/* File summary */}
                <div className="flex items-center gap-3 rounded-xl bg-[var(--app-muted-surface)] px-4 py-3">
                  <FileSpreadsheet className="h-4 w-4 flex-shrink-0 text-[var(--app-accent)]" />
                  <span className="truncate text-sm text-[var(--app-foreground)]">
                    {importFile?.name ?? importFileMeta?.name ?? "Archivo pendiente"}
                  </span>
                  <span className="text-xs text-[var(--app-muted)]">
                    · {importAnalysis.total_rows} filas · {importAnalysis.source_type.toUpperCase()}
                  </span>
                </div>

                {!importFile ? (
                  <div className="rounded-xl border border-[var(--app-border)] bg-[var(--app-muted-surface)] px-4 py-3 text-sm text-[var(--app-muted)]">
                    Vuelve al paso anterior y selecciona el archivo otra vez para preparar la revisión.
                  </div>
                ) : null}

                <div className="grid gap-6 xl:grid-cols-[minmax(0,420px)_minmax(0,1fr)] xl:items-start">
                  {/* Mapping section */}
                  <div className="space-y-3">
                    <div>
                      <p className="text-sm font-semibold text-[var(--app-foreground)]">Mapeo de columnas</p>
                      <p className="mt-0.5 text-xs text-[var(--app-muted)]">
                        {importAnalysis.source_type === "pdf"
                          ? "Leemos el PDF con OCR y proponemos los campos base. Podrás corregir cualquier fila en el paso de revisión."
                          : "Asigna cada campo a la columna correspondiente del archivo."}
                      </p>
                    </div>
                    {importAnalysis.columns.length ? (
                      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                        <ImportMappingSelect
                          label="Fecha"
                          value={importMapping.date}
                          options={importAnalysis.columns}
                          disabled={importAnalysis.source_type === "pdf"}
                          onChange={(value) =>
                            setImportMapping((current) => ({ ...current, date: value }))
                          }
                        />
                        <ImportMappingSelect
                          label="Importe"
                          value={importMapping.amount}
                          options={importAnalysis.columns}
                          disabled={importAnalysis.source_type === "pdf"}
                          onChange={(value) =>
                            setImportMapping((current) => ({ ...current, amount: value }))
                          }
                        />
                        <ImportMappingSelect
                          label="Descripción"
                          value={importMapping.description}
                          options={importAnalysis.columns}
                          disabled={importAnalysis.source_type === "pdf"}
                          onChange={(value) =>
                            setImportMapping((current) => ({ ...current, description: value }))
                          }
                        />
                        <ImportMappingSelect
                          label="Categoría"
                          value={importMapping.category}
                          options={importAnalysis.columns}
                          disabled={importAnalysis.source_type === "pdf"}
                          onChange={(value) =>
                            setImportMapping((current) => ({ ...current, category: value }))
                          }
                        />
                        <ImportMappingSelect
                          label="Notas"
                          value={importMapping.notes}
                          options={importAnalysis.columns}
                          disabled={importAnalysis.source_type === "pdf"}
                          onChange={(value) =>
                            setImportMapping((current) => ({ ...current, notes: value }))
                          }
                        />
                      </div>
                    ) : null}
                  </div>

                  {/* Sample data preview */}
                  {importAnalysis.sample_rows.length ? (
                    <div className="space-y-3 xl:min-w-0">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-semibold text-[var(--app-foreground)]">Vista previa</p>
                        <span className="text-xs text-[var(--app-muted)]">
                          {Math.min(importAnalysis.sample_rows.length, 3)} filas de ejemplo
                        </span>
                      </div>
                      <div className="overflow-x-auto rounded-xl border border-[var(--app-border)]">
                        <table className="min-w-full text-left text-xs">
                          <thead className="bg-[var(--app-muted-surface)] text-[var(--app-muted)]">
                            <tr>
                              {importAnalysis.columns.map((column) => (
                                <th key={column} className="px-4 py-2.5 font-medium">
                                  {column}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {importAnalysis.sample_rows.slice(0, 3).map((row, index) => (
                              <tr key={index} className="border-t border-[var(--app-border)] align-top">
                                {importAnalysis.columns.map((column) => (
                                  <td key={column} className="min-w-[140px] px-4 py-2.5 text-[var(--app-foreground)]">
                                    {row[column] || "—"}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ) : null}
                </div>

                {/* Submit button */}
                {isPreparingPreview ? (
                  <div className="rounded-xl border border-[var(--app-border)] bg-[var(--app-muted-surface)] px-4 py-3 text-sm text-[var(--app-muted)]">
                    <span className="font-medium text-[var(--app-foreground)]">
                      Classifying transactions by category
                    </span>
                    <span className="block text-xs">
                      Estamos preparando la revisión y dejando cada sugerencia editable antes de confirmar.
                    </span>
                  </div>
                ) : null}
                <button
                  type="submit"
                  disabled={isPreparingPreview || !importFile}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-[var(--app-accent)] px-4 py-3 text-sm font-semibold text-white transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isPreparingPreview ? (
                    <LoaderCircle className="h-4 w-4 animate-spin" />
                  ) : (
                    <Check className="h-4 w-4" />
                  )}
                  {isPreparingPreview
                    ? "Classifying transactions by category"
                    : !importFile
                      ? "Vuelve a seleccionar el archivo"
                      : "Preparar revisión"}
                </button>
              </div>
            ) : null}
          </form>
        </Modal>

        {importPreview ? (
          <Card className="animate-slideUp border-[var(--app-accent-soft)]">
            <CardHeader className="gap-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="space-y-1">
                  <CardTitle>Revisión temporal de importación</CardTitle>
                  <p className="text-sm text-[var(--app-muted)]">
                    Las filas nuevas todavía no se han guardado. Revísalas, edítalas o descarta
                    las que no quieras importar. Si ves una categoría sugerida, puedes cambiarla
                    o dejarla vacía antes de confirmar.
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge className="border-[var(--app-border)] bg-[var(--app-muted-surface)] text-[var(--app-muted)]">
                    {reviewStats.readyCount} listas
                  </Badge>
                  {reviewStats.reviewCount ? (
                    <Badge className="border-transparent bg-[var(--app-danger-soft)] text-[var(--app-danger)]">
                      {reviewStats.reviewCount} por revisar
                    </Badge>
                  ) : null}
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => void handleConfirmImport()}
                  disabled={!reviewStats.readyCount || isConfirmingImport}
                  className="inline-flex items-center gap-2 rounded-xl bg-[var(--app-accent)] px-4 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isConfirmingImport ? (
                    <LoaderCircle className="h-4 w-4 animate-spin" />
                  ) : (
                    <Check className="h-4 w-4" />
                  )}
                  Importar listas
                </button>
                <button
                  type="button"
                  onClick={() => setImportPreview(null)}
                  className="inline-flex items-center gap-2 rounded-xl border border-[var(--app-border)] bg-[var(--app-panel)] px-4 py-2.5 text-sm font-semibold text-[var(--app-foreground)] transition-all hover:border-[var(--app-danger)] hover:text-[var(--app-danger)]"
                >
                  <Trash2 className="h-4 w-4" />
                  Descartar revisión
                </button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-xl bg-[var(--app-muted-surface)] px-4 py-3 text-sm text-[var(--app-muted)]">
                Cuenta de destino:{" "}
                <span className="font-medium text-[var(--app-foreground)]">
                  {accountMap.get(importPreview.accountId)?.name ?? "Cuenta seleccionada"}
                </span>
              </div>

              <div className="space-y-3 md:hidden">
                {importPreview.rows.map((row) => (
                  <ImportReviewCard
                    key={row.id}
                    row={row}
                    categories={categories}
                    onChange={updateImportRow}
                    onDiscard={discardImportRow}
                  />
                ))}
              </div>

              <div className="hidden md:block">
                <Table className="table-fixed">
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[10%]">Fila</TableHead>
                      <TableHead className="w-[14%]">Fecha</TableHead>
                      <TableHead className="w-[18%]">Importe</TableHead>
                      <TableHead className="w-[24%]">Descripción</TableHead>
                      <TableHead className="w-[22%]">Categoría</TableHead>
                      <TableHead className="w-[16%]">Estado</TableHead>
                      <TableHead className="w-[6%] text-right">Acción</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {importPreview.rows.map((row) => (
                      <TableRow key={row.id}>
                        <TableCell className="text-xs text-[var(--app-muted)]">
                          #{row.sourceRowNumber}
                        </TableCell>
                        <TableCell>
                          <input
                            type="date"
                            value={row.date}
                            onChange={(event) =>
                              updateImportRow(row.id, (current) => ({
                                ...current,
                                date: event.target.value,
                              }))
                            }
                            className="h-9 w-full rounded-lg border border-[var(--app-border)] bg-[var(--app-panel)] px-2 text-sm outline-none transition-all focus:border-[var(--app-accent)]"
                          />
                        </TableCell>
                        <TableCell>
                          <div className="space-y-1">
                            <div className="flex items-center gap-2 rounded-lg border border-[var(--app-border)] bg-[var(--app-panel)] px-2">
                              <input
                                value={row.amount}
                                onChange={(event) =>
                                  updateImportRow(row.id, (current) => ({
                                    ...current,
                                    amount: event.target.value,
                                  }))
                                }
                                className="h-9 w-full bg-transparent text-sm outline-none"
                              />
                              <span className="text-xs text-[var(--app-muted)]">{row.currency}</span>
                            </div>
                            <textarea
                              value={row.notes}
                              onChange={(event) =>
                                updateImportRow(row.id, (current) => ({
                                  ...current,
                                  notes: event.target.value,
                                }))
                              }
                              rows={2}
                              placeholder="Notas"
                              className="w-full rounded-lg border border-[var(--app-border)] bg-[var(--app-panel)] px-2 py-2 text-xs outline-none transition-all focus:border-[var(--app-accent)]"
                            />
                          </div>
                        </TableCell>
                        <TableCell>
                          <input
                            value={row.description}
                            onChange={(event) =>
                              updateImportRow(row.id, (current) => ({
                                ...current,
                                description: event.target.value,
                              }))
                            }
                            className="h-9 w-full rounded-lg border border-[var(--app-border)] bg-[var(--app-panel)] px-2 text-sm outline-none transition-all focus:border-[var(--app-accent)]"
                          />
                        </TableCell>
                        <TableCell>
                          <div className="space-y-1">
                            <select
                              value={row.categoryId}
                              onChange={(event) =>
                                updateImportRow(row.id, (current) => ({
                                  ...current,
                                  categoryId: event.target.value,
                                }))
                              }
                              className="h-9 w-full rounded-lg border border-[var(--app-border)] bg-[var(--app-panel)] px-2 text-sm outline-none transition-all focus:border-[var(--app-accent)]"
                            >
                              <option value="">Sin categoría</option>
                              {categories.map((category) => (
                                <option key={category.id} value={category.id}>
                                  {category.name}
                                </option>
                              ))}
                            </select>
                            <ImportCategoryHint row={row} />
                          </div>
                        </TableCell>
                        <TableCell>
                          <ImportStatusCell row={row} />
                        </TableCell>
                        <TableCell className="text-right">
                          <button
                            type="button"
                            onClick={() => discardImportRow(row.id)}
                            className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-[var(--app-danger)] transition-all hover:bg-[var(--app-danger-soft)]"
                            aria-label={`Descartar fila ${row.sourceRowNumber}`}
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        ) : null}

        <div className="animate-fadeIn overflow-hidden rounded-2xl border border-[color-mix(in_srgb,var(--app-accent)_15%,var(--app-border))] bg-[color-mix(in_srgb,var(--app-panel-strong)_70%,var(--app-muted-surface))] shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]">
          <div className="flex items-stretch">
            <div className="flex shrink-0 items-center border-r border-[color-mix(in_srgb,var(--app-accent)_20%,var(--app-border))] bg-[color-mix(in_srgb,var(--app-accent)_8%,var(--app-muted-surface))] px-4 text-xs font-bold tracking-wider text-[var(--app-accent)] uppercase">
              Filtros
            </div>
            <div className="min-w-0 flex-1 p-2">
              <div className="flex flex-nowrap items-center gap-1 overflow-x-auto pb-1">
                <FilterSelect
                  value={filters.account_id}
                  onChange={(v) => updateFilter("account_id", v)}
                  placeholder="Cuenta"
                  options={accounts.map((a) => ({ value: a.id, label: a.name }))}
                />
                <FilterSelect
                  value={filters.category_id}
                  onChange={(v) => updateFilter("category_id", v)}
                  placeholder="Categoría"
                  options={categories.map((c) => ({ value: c.id, label: c.name }))}
                />
                <FilterSelect
                  value={filters.category_type}
                  onChange={(v) => updateFilter("category_type", v)}
                  placeholder="Tipo"
                  options={[
                    { value: "expense", label: "Gasto" },
                    { value: "income", label: "Ingreso" },
                    { value: "transfer", label: "Transferencia" },
                  ]}
                  minWidth="92px"
                />
                <FilterSelect
                  value={filters.year}
                  onChange={(v) => updateFilter("year", v)}
                  placeholder="Año"
                  options={yearOptions.map((y) => ({ value: y, label: y }))}
                  minWidth="86px"
                />
                <FilterSelect
                  value={filters.month}
                  onChange={(v) => updateFilter("month", v)}
                  placeholder="Mes"
                  options={monthOptions.map((m) => ({ value: m.value, label: m.label }))}
                  minWidth="86px"
                />
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

        {loadError ? (
          <ErrorScreen
            title="No se han podido cargar las transacciones"
            description={
              loadError instanceof Error
                ? loadError.message
                : "No hemos podido cargar las transacciones y datos auxiliares."
            }
          />
        ) : isLoading ? (
          <ListSkeleton rows={6} />
        ) : (
          <Card className="animate-slideUp">
            <CardHeader>
              <CardTitle>Últimas transacciones</CardTitle>
            </CardHeader>
            <CardContent>
              {transactions.length ? (
                <>
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
                                {
                                  label: "Editar",
                                  icon: <Pencil className="h-4 w-4" />,
                                  onClick: () => handleOpenEdit(transaction),
                                },
                                {
                                  label: "Duplicar",
                                  icon: <Copy className="h-4 w-4" />,
                                  onClick: () => handleOpenDuplicate(transaction),
                                },
                                {
                                  label: "Eliminar",
                                  icon: <Trash2 className="h-4 w-4" />,
                                  onClick: () =>
                                    setConfirmDelete({ open: true, ids: [transaction.id] }),
                                  danger: true,
                                },
                              ]}
                            />
                          </div>
                        </div>
                        <div className="mt-3 flex flex-wrap items-center gap-2">
                          <span className="text-xs text-[var(--app-muted)]">
                            {formatDate(transaction.date)}
                          </span>
                        </div>
                        {transaction.notes ? (
                          <p className="mt-3 text-xs text-[var(--app-muted)]">{transaction.notes}</p>
                        ) : null}
                      </article>
                    ))}
                  </div>

                  <div className="hidden md:block">
                    <Table className="table-fixed">
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-12">
                            <input
                              type="checkbox"
                              checked={allVisibleSelected}
                              onChange={toggleSelectAll}
                              aria-label="Seleccionar todas"
                            />
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
                              <input
                                type="checkbox"
                                checked={selectedIds.includes(transaction.id)}
                                onChange={() => toggleSelection(transaction.id)}
                                aria-label={`Seleccionar ${transaction.description}`}
                              />
                            </TableCell>
                            <TableCell>
                              <div className="space-y-1 overflow-hidden">
                                <p className="truncate font-medium">{transaction.description}</p>
                                {transaction.notes ? (
                                  <p className="truncate text-xs text-[var(--app-muted)]">
                                    {transaction.notes}
                                  </p>
                                ) : null}
                              </div>
                            </TableCell>
                            <TableCell className="truncate">
                              {accountMap.get(transaction.account_id)?.name ?? "Cuenta desconocida"}
                            </TableCell>
                            <TableCell>
                              <CategoryBadge category={categoryMap.get(transaction.category_id ?? "")} />
                            </TableCell>
                            <TableCell className="whitespace-nowrap">
                              {formatDate(transaction.date)}
                            </TableCell>
                            <TableCell className="text-right">
                              <div className="flex items-center justify-end gap-2">
                                <AmountValue amount={transaction.amount} currency={transaction.currency} />
                                <ActionMenu
                                  label={transaction.description}
                                  ariaLabel={`Acciones de transacción ${transaction.description}`}
                                  actions={[
                                    {
                                      label: "Editar",
                                      icon: <Pencil className="h-4 w-4" />,
                                      onClick: () => handleOpenEdit(transaction),
                                    },
                                    {
                                      label: "Duplicar",
                                      icon: <Copy className="h-4 w-4" />,
                                      onClick: () => handleOpenDuplicate(transaction),
                                    },
                                    {
                                      label: "Eliminar",
                                      icon: <Trash2 className="h-4 w-4" />,
                                      onClick: () =>
                                        setConfirmDelete({ open: true, ids: [transaction.id] }),
                                      danger: true,
                                    },
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
                    <PaginationControls
                      page={page}
                      pageSize={pageSize}
                      total={totalTransactions}
                      onPageChange={handlePageChange}
                    />
                  </div>
                </>
              ) : (
                <EmptyState
                  title="Aún no hay transacciones"
                  description="Crea la primera para empezar a poblar el dashboard."
                  icon={CreditCard}
                  actionLabel="Nueva transacción"
                  onAction={() => handleOpenCreate("expense")}
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

function ImportMappingSelect({
  label,
  value,
  options,
  disabled = false,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  disabled?: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <label className="space-y-2">
      <span className="text-sm font-medium text-[var(--app-foreground)]">{label}</span>
      <select
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-4 py-2.5 text-sm outline-none transition-all focus:border-[var(--app-accent)] disabled:cursor-not-allowed disabled:opacity-70"
      >
        <option value="">No mapear</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function ImportReviewCard({
  row,
  categories,
  onChange,
  onDiscard,
}: {
  row: TransactionImportPreviewRow;
  categories: Category[];
  onChange: (
    rowId: string,
    updater: (row: TransactionImportPreviewRow) => TransactionImportPreviewRow,
  ) => void;
  onDiscard: (rowId: string) => void;
}) {
  return (
    <article className="rounded-2xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="text-xs text-[var(--app-muted)]">Fila #{row.sourceRowNumber}</p>
          <ImportStatusCell row={row} />
        </div>
        <button
          type="button"
          onClick={() => onDiscard(row.id)}
          className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-[var(--app-danger)] transition-all hover:bg-[var(--app-danger-soft)]"
          aria-label={`Descartar fila ${row.sourceRowNumber}`}
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-3 grid gap-3">
        <input
          type="date"
          value={row.date}
          onChange={(event) =>
            onChange(row.id, (current) => ({ ...current, date: event.target.value }))
          }
          className="h-10 w-full rounded-lg border border-[var(--app-border)] bg-[var(--app-panel)] px-3 text-sm outline-none transition-all focus:border-[var(--app-accent)]"
        />
        <div className="flex items-center gap-2 rounded-lg border border-[var(--app-border)] bg-[var(--app-panel)] px-3">
          <input
            value={row.amount}
            onChange={(event) =>
              onChange(row.id, (current) => ({ ...current, amount: event.target.value }))
            }
            className="h-10 w-full bg-transparent text-sm outline-none"
          />
          <span className="text-xs text-[var(--app-muted)]">{row.currency}</span>
        </div>
        <input
          value={row.description}
          onChange={(event) =>
            onChange(row.id, (current) => ({ ...current, description: event.target.value }))
          }
          placeholder="Descripción"
          className="h-10 w-full rounded-lg border border-[var(--app-border)] bg-[var(--app-panel)] px-3 text-sm outline-none transition-all focus:border-[var(--app-accent)]"
        />
        <select
          value={row.categoryId}
          onChange={(event) =>
            onChange(row.id, (current) => ({ ...current, categoryId: event.target.value }))
          }
          className="h-10 w-full rounded-lg border border-[var(--app-border)] bg-[var(--app-panel)] px-3 text-sm outline-none transition-all focus:border-[var(--app-accent)]"
        >
          <option value="">Sin categoría</option>
          {categories.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name}
            </option>
          ))}
        </select>
        <ImportCategoryHint row={row} />
        <textarea
          value={row.notes}
          onChange={(event) =>
            onChange(row.id, (current) => ({ ...current, notes: event.target.value }))
          }
          rows={2}
          placeholder="Notas"
          className="w-full rounded-lg border border-[var(--app-border)] bg-[var(--app-panel)] px-3 py-2 text-sm outline-none transition-all focus:border-[var(--app-accent)]"
        />
      </div>
    </article>
  );
}

function ImportCategoryHint({ row }: { row: TransactionImportPreviewRow }) {
  const sourceLabel = formatCategorySuggestionSource(row.categorySuggestionSource);

  if (row.categoryIsSuggested && row.categorySuggestionLabel) {
    return (
      <p className="text-xs text-[var(--app-muted)]">
        Categoría sugerida por {sourceLabel}: {row.categorySuggestionLabel}. Puedes cambiarla o
        dejarla vacía.
      </p>
    );
  }

  if (!row.categoryId && row.categoryLabel) {
    return (
      <p className="text-xs text-[var(--app-muted)]">
        Categoría original del archivo: {row.categoryLabel}. Puedes asignarla o dejarla vacía.
      </p>
    );
  }

  return null;
}

function ImportStatusCell({ row }: { row: TransactionImportPreviewRow }) {
  if (row.validationErrors.length === 0) {
    return (
      <div className="inline-flex items-center gap-2 rounded-full bg-[var(--app-success-soft)] px-3 py-1 text-xs font-medium text-[var(--app-success)]">
        <Check className="h-3.5 w-3.5" />
        Lista para importar
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="inline-flex items-center gap-2 rounded-full bg-[var(--app-danger-soft)] px-3 py-1 text-xs font-medium text-[var(--app-danger)]">
        <AlertCircle className="h-3.5 w-3.5" />
        Revisar
      </div>
      <ul className="space-y-1 text-xs text-[var(--app-danger)]">
        {row.validationErrors.map((error) => (
          <li key={error}>{error}</li>
        ))}
      </ul>
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
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
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

function defaultImportMapping(): TransactionImportMapping {
  return {
    date: "",
    amount: "",
    description: "",
    category: "",
    notes: "",
  };
}

function inferTransactionKind(
  transaction: Transaction,
  categoryById: Map<string, Category>,
): TransactionKind {
  const categoryType = transaction.category_id
    ? categoryById.get(transaction.category_id)?.type
    : null;

  if (categoryType === "income" || categoryType === "expense" || categoryType === "transfer") {
    return categoryType;
  }

  const numericAmount = typeof transaction.amount === "number"
    ? transaction.amount
    : Number(transaction.amount);
  return numericAmount < 0 ? "expense" : "income";
}

function normalizeImportPreviewRow(row: TransactionImportPreviewRow): TransactionImportPreviewRow {
  return {
    ...row,
    date: row.date.trim(),
    amount: row.amount.trim(),
    description: row.description.trim(),
    notes: row.notes.trim(),
    validationErrors: getImportRowValidationErrors(row),
  };
}

function formatCategorySuggestionSource(source: string) {
  switch (source) {
    case "history":
      return "historial";
    case "pattern":
      return "patrones repetidos";
    case "assisted":
      return "IA";
    default:
      return "el sistema";
  }
}

function getImportRowValidationErrors(row: TransactionImportPreviewRow): string[] {
  const errors: string[] = [];
  if (!row.date || Number.isNaN(Date.parse(row.date))) {
    errors.push("Revisa la fecha");
  }
  if (!row.amount || Number.isNaN(Number(row.amount.replace(",", ".")))) {
    errors.push("Revisa el importe");
  }
  if (!row.description.trim()) {
    errors.push("Revisa la descripción");
  }
  return errors;
}

const monthOptions = [
  { value: "1", label: "Enero" },
  { value: "2", label: "Febrero" },
  { value: "3", label: "Marzo" },
  { value: "4", label: "Abril" },
  { value: "5", label: "Mayo" },
  { value: "6", label: "Junio" },
  { value: "7", label: "Julio" },
  { value: "8", label: "Agosto" },
  { value: "9", label: "Septiembre" },
  { value: "10", label: "Octubre" },
  { value: "11", label: "Noviembre" },
  { value: "12", label: "Diciembre" },
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
