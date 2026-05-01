"use client";

import { useEffect, useRef } from "react";
import { X } from "lucide-react";

export function Modal({
  open,
  title,
  description,
  onClose,
  children,
  dialogClassName,
}: {
  open: boolean;
  title: React.ReactNode;
  description?: React.ReactNode;
  onClose: () => void;
  children: React.ReactNode;
  dialogClassName?: string;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!open) {
      return;
    }

    previousFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onCloseRef.current();
        return;
      }

      if (event.key !== "Tab" || !dialogRef.current) {
        return;
      }

      const focusableElements = dialogRef.current.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );

      if (focusableElements.length === 0) {
        event.preventDefault();
        dialogRef.current.focus();
        return;
      }

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];
      const activeElement = document.activeElement;

      if (event.shiftKey && activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      } else if (!event.shiftKey && activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";

    const firstFocusableElement = dialogRef.current?.querySelector<HTMLElement>(
      'input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
    );

    if (firstFocusableElement) {
      firstFocusableElement.focus();
    } else {
      dialogRef.current?.focus();
    }

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
      previousFocusRef.current?.focus();
    };
  }, [open]);

  if (!open) {
    return null;
  }

  return (
    <div
      className="animate-fadeIn fixed inset-0 z-[60] flex items-start justify-center overflow-y-auto bg-black/40 px-[max(0.75rem,env(safe-area-inset-left))] py-[max(0.75rem,env(safe-area-inset-top))] pb-[max(0.75rem,env(safe-area-inset-bottom))] backdrop-blur-sm sm:items-center sm:px-4 sm:py-6"
      onClick={() => onCloseRef.current()}
      role="presentation"
    >
      <div
        ref={dialogRef}
        className={`animate-scaleIn flex max-h-[calc(100dvh-max(1.5rem,env(safe-area-inset-top)+env(safe-area-inset-bottom)))] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-[var(--app-border)] bg-[var(--app-panel)] shadow-[var(--app-shadow-elevated)] ${dialogClassName ?? ""}`}
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === "string" ? title : "Modal"}
        tabIndex={-1}
      >
        <div className="flex items-start justify-between gap-3 border-b border-[var(--app-border)] px-4 py-4 sm:gap-4 sm:px-6 sm:py-5">
          <div className="min-w-0">
            <h2 className="text-base font-semibold leading-snug sm:text-lg">{title}</h2>
            {description ? (
              <p className="mt-1 text-sm text-[var(--app-muted)]">{description}</p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={() => onCloseRef.current()}
            className="rounded-full p-1.5 text-[var(--app-muted)] transition-all hover:bg-[var(--app-muted-surface)] hover:text-[var(--app-ink)]"
            aria-label="Cerrar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4 sm:px-6 sm:py-5">{children}</div>
      </div>
    </div>
  );
}
