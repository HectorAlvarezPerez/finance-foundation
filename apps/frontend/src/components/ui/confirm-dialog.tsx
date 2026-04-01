"use client";

import { AlertTriangle } from "lucide-react";

import { Modal } from "@/components/ui/modal";

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Eliminar",
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) {
    return null;
  }

  return (
    <Modal open={open} onClose={onCancel} title={title} description={description}>
      <div className="space-y-5">
        <div className="flex items-center gap-3 rounded-2xl bg-[var(--app-danger-soft)] px-4 py-3">
          <AlertTriangle className="h-5 w-5 shrink-0 text-[var(--app-danger)]" />
          <p className="text-sm text-[var(--app-ink)]">{description}</p>
        </div>
        <div className="flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-xl border border-[var(--app-border)] bg-[var(--app-panel)] px-4 py-2.5 text-sm font-medium text-[var(--app-ink)] transition-all hover:bg-[var(--app-muted-surface)]"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-xl bg-[var(--app-danger)] px-4 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </Modal>
  );
}
