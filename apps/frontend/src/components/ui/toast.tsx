"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { CheckCircle2, AlertTriangle, Info, X } from "lucide-react";

type ToastType = "success" | "error" | "info";

type Toast = {
  id: number;
  message: string;
  type: ToastType;
};

type ToastContextValue = {
  toast: (message: string, type?: ToastType) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

let nextId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback((message: string, type: ToastType = "success") => {
    const id = nextId++;
    setToasts((current) => [...current, { id, message, type }]);

    setTimeout(() => {
      setToasts((current) => current.filter((t) => t.id !== id));
    }, 3500);
  }, []);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((t) => t.id !== id));
  }, []);

  const value = useMemo(() => ({ toast }), [toast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed bottom-20 md:bottom-6 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} onDismiss={() => dismiss(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: () => void }) {
  const Icon = toast.type === "success" ? CheckCircle2 : toast.type === "error" ? AlertTriangle : Info;
  const iconColor =
    toast.type === "success"
      ? "text-[var(--app-success)]"
      : toast.type === "error"
        ? "text-[var(--app-danger)]"
        : "text-[var(--app-accent)]";

  return (
    <div className="animate-slideUp pointer-events-auto flex items-center gap-3 rounded-2xl border border-[var(--app-border)] bg-[var(--app-glass)] px-4 py-3 shadow-[var(--app-shadow-elevated)] backdrop-blur-xl">
      <Icon className={`h-5 w-5 shrink-0 ${iconColor}`} />
      <p className="text-sm font-medium text-[var(--app-ink)] flex-1">{toast.message}</p>
      <button
        type="button"
        onClick={onDismiss}
        className="shrink-0 rounded-lg p-1 text-[var(--app-muted)] transition-colors hover:text-[var(--app-ink)]"
        aria-label="Cerrar notificación"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

export function useToast() {
  const context = useContext(ToastContext);

  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }

  return context;
}
