"use client";

import { RefreshCw, Sparkles, Play } from "lucide-react";

import { cn } from "@/lib/utils";
import type { InsightsMonthlyRecap } from "@/lib/types";

export function MonthlyRecapLauncher({
  compact = false,
  hasSelectedMonth,
  onPlay,
  onRegenerate,
  isLoading,
  recap,
  error,
}: {
  compact?: boolean;
  hasSelectedMonth: boolean;
  onPlay: () => void;
  onRegenerate: () => void;
  isLoading: boolean;
  recap: InsightsMonthlyRecap | null;
  error: string | null;
}) {
  return (
    <section
      className="relative overflow-hidden rounded-[2rem] border shadow-[var(--app-shadow-elevated)]"
      style={{
        borderColor: "color-mix(in srgb, var(--app-accent) 16%, var(--app-border))",
        background:
          "linear-gradient(135deg, color-mix(in srgb, var(--app-panel) 92%, var(--app-accent-soft) 8%), color-mix(in srgb, var(--app-panel-strong) 96%, transparent) 48%, color-mix(in srgb, var(--app-panel) 88%, var(--app-success-soft) 12%))",
        color: "var(--app-ink)",
      }}
    >
      <div className="absolute inset-0 opacity-80" style={launcherGlowStyle} />
      <div className="absolute inset-y-0 right-0 w-44 blur-3xl" style={launcherEdgeGlowStyle} />
      <div
        className={cn(
          "relative grid",
          compact ? "gap-2.5 p-2.5 sm:p-3" : "gap-4 p-4 sm:p-5 lg:grid-cols-[1.1fr_0.9fr] lg:gap-5",
        )}
      >
        <div className={cn("flex min-h-0 flex-col justify-between", compact ? "gap-2" : "gap-4")}>
          <div className={cn(compact ? "space-y-2" : "space-y-3")}>
            <div className={cn("inline-flex items-center rounded-full border border-[var(--app-border)] bg-[var(--app-muted-surface)] font-semibold uppercase text-[var(--app-muted)] backdrop-blur", compact ? "gap-1.5 px-2.5 py-0.5 text-[10px] tracking-[0.16em]" : "gap-2 px-3 py-1 text-xs tracking-[0.18em]")}>
              <Sparkles className={cn(compact ? "h-3 w-3" : "h-3.5 w-3.5")} />
              Recap mensual
            </div>
            <div className={cn(compact ? "space-y-1" : "space-y-1.5")}>
              <h2
                className={cn(
                  "font-semibold tracking-tight text-[var(--app-ink)]",
                  compact ? "max-w-xl text-lg sm:text-xl" : "max-w-2xl text-2xl sm:text-[2rem]",
                )}
              >
                Tu mes, contado en historias.
              </h2>
              <p className={cn("text-[var(--app-muted)]", compact ? "max-w-xl text-[11px] leading-4 sm:text-xs" : "max-w-xl text-sm leading-5")}>
                Recorre 2-3 stories creadas con señales reales del mes analizado.
              </p>
            </div>
          </div>

          <div className={cn("flex flex-wrap text-xs text-[var(--app-muted)]", compact ? "gap-1.5" : "gap-2")}>
            {recap?.generated_at ? <StatusPill label={`Actualizado ${formatDateLabel(recap.generated_at)}`} /> : null}
          </div>
        </div>

        <div
          className={cn(
            "relative border backdrop-blur-xl",
            compact ? "rounded-[1rem] p-2.5" : "rounded-[1.35rem] p-3.5",
          )}
          style={{
            borderColor: "var(--app-border)",
            background: "color-mix(in srgb, var(--app-panel) 82%, transparent)",
          }}
        >
          <div className={cn(compact ? "space-y-1.5" : "space-y-2.5")}>
            <div
              className={cn(
                compact ? "space-y-1.5" : "space-y-2.5",
              )}
            >
              <button
                type="button"
                onClick={onPlay}
                disabled={isLoading || !hasSelectedMonth}
                className={cn(
                  "inline-flex w-full items-center justify-center gap-2 rounded-2xl px-4 text-sm font-semibold transition-all",
                  compact ? "py-1.5" : "py-2.5",
                  isLoading || !hasSelectedMonth
                    ? "cursor-not-allowed"
                    : "hover:-translate-y-0.5",
                )}
                style={{
                  background:
                    isLoading || !hasSelectedMonth
                      ? "color-mix(in srgb, var(--app-muted-surface) 88%, transparent)"
                      : "var(--app-ink)",
                  color:
                    isLoading || !hasSelectedMonth
                      ? "color-mix(in srgb, var(--app-ink) 32%, transparent)"
                      : "var(--app-surface)",
                }}
              >
                {isLoading ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    Generando...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4" />
                    {compact ? "Ver recap" : "Ver recap mensual"}
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={onRegenerate}
                disabled={isLoading || !hasSelectedMonth}
                className={cn(
                  "inline-flex w-full items-center justify-center gap-2 rounded-2xl border px-4 text-sm font-semibold transition-all",
                  compact ? "py-1.5" : "py-2.5",
                  isLoading || !hasSelectedMonth
                    ? "cursor-not-allowed"
                    : "hover:-translate-y-0.5 hover:bg-[var(--app-muted-surface)]",
                )}
                style={{
                  borderColor: "var(--app-border)",
                  background:
                    isLoading || !hasSelectedMonth
                      ? "color-mix(in srgb, var(--app-muted-surface) 70%, transparent)"
                      : "color-mix(in srgb, var(--app-panel) 92%, transparent)",
                  color:
                    isLoading || !hasSelectedMonth
                      ? "color-mix(in srgb, var(--app-ink) 38%, transparent)"
                      : "var(--app-ink)",
                }}
              >
                <RefreshCw className="h-4 w-4" />
                Regenerar
              </button>
            </div>
          </div>

          <div className={cn(compact ? "mt-2.5 space-y-2" : "mt-3 space-y-2.5")}>
          {!compact ? (
            <div
              className={cn("rounded-2xl border", compact ? "p-2.5" : "p-3")}
              style={{
                borderColor: "var(--app-border)",
                background: "color-mix(in srgb, var(--app-muted-surface) 80%, transparent)",
              }}
            >
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--app-muted)]">
                Estado del recap
              </p>
                <p className="mt-1 text-sm font-medium text-[var(--app-text)]">
                  {recap ? getStatusDescription(recap.is_stale) : "Todavía no se ha generado ningún recap."}
                </p>
              </div>
            ) : null}
            {error ? (
              <div className="rounded-2xl border border-[rgba(255,59,48,0.24)] bg-[rgba(255,59,48,0.08)] px-4 py-3 text-sm text-[var(--app-danger)]">
                {error}
              </div>
            ) : null}
            {!hasSelectedMonth ? (
              <p className="text-sm text-[var(--app-muted)]">No hay recap disponible para este mes. Cambia el mes del análisis.</p>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  );
}

function formatDateLabel(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("es-ES", {
    day: "2-digit",
    month: "short",
  }).format(date);
}

function StatusPill({ label, active = false }: { label: string; active?: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-3 py-1",
        active
          ? "border-[color:color-mix(in_srgb,var(--app-accent)_18%,var(--app-border))] bg-[var(--app-accent-soft)] text-[var(--app-accent)]"
          : "border-[var(--app-border)] bg-[var(--app-muted-surface)] text-[var(--app-muted)]",
      )}
    >
      {label}
    </span>
  );
}

const launcherGlowStyle = {
  background:
    "radial-gradient(circle at top left, color-mix(in srgb, var(--app-accent) 18%, transparent), transparent 30%), radial-gradient(circle at bottom right, color-mix(in srgb, var(--app-success) 12%, transparent), transparent 26%)",
} as const;

const launcherEdgeGlowStyle = {
  background:
    "linear-gradient(180deg, color-mix(in srgb, var(--app-accent-soft) 55%, transparent), transparent)",
} as const;

function getStatusLabel(isStale?: boolean) {
  if (isStale) {
    return "Desactualizado";
  }
  return "Disponible";
}

function getStatusDescription(isStale?: boolean) {
  if (isStale) {
    return "Existe un recap en caché, pero hay datos nuevos disponibles. Regénéralo cuando quieras la versión más reciente.";
  }
  return "El recap está disponible para este mes y puede reabrirse cuando quieras.";
}
