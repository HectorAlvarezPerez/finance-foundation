"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, X, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import type { InsightsMonthlyRecap } from "@/lib/types";
import { MonthlyRecapStoryCard } from "@/components/insights/monthly-recap-story";

export function MonthlyRecapOverlay({
  open,
  recap,
  onClose,
}: {
  open: boolean;
  recap: InsightsMonthlyRecap | null;
  onClose: () => void;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const [activeStoryIndex, setActiveStoryIndex] = useState(0);
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

      if (!recap) {
        return;
      }

      if (event.key === "ArrowRight") {
        setActiveStoryIndex((current) => Math.min(current + 1, recap.stories.length - 1));
        return;
      }

      if (event.key === "ArrowLeft") {
        setActiveStoryIndex((current) => Math.max(current - 1, 0));
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
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
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
  }, [open, recap]);

  if (!open || !recap) {
    return null;
  }

  if (recap.stories.length === 0) {
    return (
      <div className="animate-fadeIn fixed inset-0 z-[90] flex items-center justify-center bg-[rgba(5,8,20,0.82)] px-3 py-3 backdrop-blur-2xl">
        <div className="w-full max-w-[420px] rounded-[2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(7,10,20,0.98),rgba(17,24,39,0.92))] p-6 text-center text-white shadow-[0_32px_120px_rgba(0,0,0,0.45)]">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-white/52">
            Monthly recap
          </p>
          <h2 className="mt-3 text-2xl font-semibold tracking-tight">{recap.month_label}</h2>
          <p className="mt-3 text-sm text-white/68">
            No stories are available for this recap yet.
          </p>
          <button
            type="button"
            onClick={() => onCloseRef.current()}
            className="mt-5 inline-flex items-center justify-center rounded-2xl bg-white px-4 py-3 text-sm font-semibold text-[var(--app-ink)] transition-all hover:bg-white/95"
          >
            Close recap
          </button>
        </div>
      </div>
    );
  }

  const activeStory = recap.stories[activeStoryIndex] ?? recap.stories[0];
  const isFirstStory = activeStoryIndex === 0;
  const isLastStory = activeStoryIndex >= recap.stories.length - 1;

  return (
    <div
      className="animate-fadeIn fixed inset-0 z-[90] flex items-center justify-center px-3 py-3 backdrop-blur-2xl sm:px-4 sm:py-4"
      style={{
        background:
          "color-mix(in srgb, var(--background) 68%, rgba(7, 12, 24, 0.42))",
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          onCloseRef.current();
        }
      }}
      role="presentation"
    >
      <div
        ref={dialogRef}
        className="mx-auto flex min-h-[calc(100dvh-1.5rem)] w-full items-center justify-center"
        role="dialog"
        aria-modal="true"
        aria-label={`Monthly recap ${recap.month_label}`}
        tabIndex={-1}
      >
        <div className="flex w-full max-w-[540px] flex-col items-center gap-3 sm:gap-4">
          <div className="flex w-full items-center justify-center gap-3 sm:gap-5">
            <NavButton
              label="Previous story"
              icon={ChevronLeft}
              disabled={isFirstStory}
              onClick={() => setActiveStoryIndex((current) => Math.max(current - 1, 0))}
            />

            <div className="relative min-h-0 w-full max-w-[410px]">
              <button
                type="button"
                onClick={() => onCloseRef.current()}
                aria-label="Close recap"
                className="absolute right-3 top-3 z-10 inline-flex h-9 w-9 items-center justify-center rounded-full border transition-all hover:scale-[1.02] sm:right-4 sm:top-4"
                style={{
                  borderColor: "var(--app-border)",
                  background: "color-mix(in srgb, var(--app-panel) 92%, transparent)",
                  color: "var(--app-ink)",
                  boxShadow: "var(--app-shadow)",
                }}
              >
                <X className="h-4 w-4" />
              </button>

              <MonthlyRecapStoryCard story={activeStory} index={activeStoryIndex} total={recap.stories.length} />
            </div>

            <NavButton
              label="Next story"
              icon={ChevronRight}
              disabled={isLastStory}
              onClick={() => setActiveStoryIndex((current) => Math.min(current + 1, recap.stories.length - 1))}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function NavButton({
  label,
  icon: Icon,
  onClick,
  disabled,
}: {
  label: string;
  icon: LucideIcon;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      className={cn(
        "inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-full border text-sm font-semibold transition-all sm:h-14 sm:w-14",
        disabled
          ? "cursor-not-allowed text-[color:color-mix(in_srgb,var(--app-ink)_22%,transparent)]"
          : "text-[var(--app-ink)] hover:scale-[1.02]",
      )}
      style={{
        borderColor: disabled ? "color-mix(in srgb, var(--app-border) 80%, transparent)" : "var(--app-border)",
        background: disabled
          ? "color-mix(in srgb, var(--app-panel) 72%, transparent)"
          : "color-mix(in srgb, var(--app-panel) 88%, transparent)",
        boxShadow: "var(--app-shadow)",
      }}
    >
      <Icon className="h-4 w-4" />
    </button>
  );
}
