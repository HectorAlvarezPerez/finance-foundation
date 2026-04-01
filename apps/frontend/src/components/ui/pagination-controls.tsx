"use client";

export function PaginationControls({
  page,
  pageSize,
  total,
  onPageChange,
  className = "",
}: {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  className?: string;
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);

  if (totalPages <= 1) {
    return null;
  }

  return (
    <div className={`flex flex-col gap-3 border-t border-[var(--app-border)] pt-4 sm:flex-row sm:items-center sm:justify-between ${className}`}>
      <p className="text-sm text-[var(--app-muted)]">
        Mostrando {start}-{end} de {total}
      </p>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => onPageChange(page - 1)}
          disabled={page === 1}
          className="rounded-xl border border-[var(--app-border)] bg-[var(--app-panel)] px-3 py-2 text-sm font-medium transition-all hover:bg-[var(--app-muted-surface)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          Anterior
        </button>
        <span className="rounded-xl bg-[var(--app-muted-surface)] px-3 py-2 text-sm text-[var(--app-muted)]">
          {page} / {totalPages}
        </span>
        <button
          type="button"
          onClick={() => onPageChange(page + 1)}
          disabled={page === totalPages}
          className="rounded-xl border border-[var(--app-border)] bg-[var(--app-panel)] px-3 py-2 text-sm font-medium transition-all hover:bg-[var(--app-muted-surface)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          Siguiente
        </button>
      </div>
    </div>
  );
}
