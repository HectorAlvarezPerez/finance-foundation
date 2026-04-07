"use client";

import { RefreshCw, Sparkles, Play } from "lucide-react";

import { formatMonthLabel } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { InsightsMonthlyRecap, InsightsRecapMonth } from "@/lib/types";

export function MonthlyRecapLauncher({
  months,
  selectedMonthKey,
  onSelectedMonthKeyChange,
  onPlay,
  onRegenerate,
  isLoading,
  recap,
  error,
}: {
  months: Array<InsightsRecapMonth | string>;
  selectedMonthKey: string;
  onSelectedMonthKeyChange: (monthKey: string) => void;
  onPlay: () => void;
  onRegenerate: () => void;
  isLoading: boolean;
  recap: InsightsMonthlyRecap | null;
  error: string | null;
}) {
  const normalizedMonths = months.map((month) => normalizeMonth(month));
  const selectedMonth = normalizedMonths.find((month) => month.monthKey === selectedMonthKey);
  const activeRecapStatus = recap ? getStatusLabel(recap.is_stale) : "Sin recap";

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
      <div className="relative grid gap-5 p-5 sm:p-6 lg:grid-cols-[1.2fr_0.8fr] lg:gap-6">
        <div className="flex min-h-0 flex-col justify-between gap-5">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 rounded-full border border-[var(--app-border)] bg-[var(--app-muted-surface)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--app-muted)] backdrop-blur">
              <Sparkles className="h-3.5 w-3.5" />
              Recap mensual
            </div>
            <div className="space-y-2">
              <h2 className="max-w-3xl text-3xl font-semibold tracking-tight text-[var(--app-ink)] sm:text-4xl">
                Vive el mes como una historia, no como una hoja de cálculo.
              </h2>
              <p className="max-w-2xl text-sm leading-6 text-[var(--app-muted)] sm:text-base">
                Elige un mes, lanza el recap y recorre 2-3 stories editoriales construidas con señales reales
                de gasto.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 text-xs text-[var(--app-muted)]">
            <StatusPill label={activeRecapStatus} active />
            {selectedMonth ? (
              <StatusPill label={selectedMonth.label} />
            ) : (
              <StatusPill label="Elige un mes" />
            )}
            {recap?.generated_at ? <StatusPill label={`Actualizado ${formatDateLabel(recap.generated_at)}`} /> : null}
          </div>
        </div>

        <div
          className="relative rounded-[1.5rem] border p-4 backdrop-blur-xl"
          style={{
            borderColor: "var(--app-border)",
            background: "color-mix(in srgb, var(--app-panel) 82%, transparent)",
          }}
        >
          <div className="space-y-3">
            <label className="block text-xs font-semibold uppercase tracking-[0.18em] text-[var(--app-muted)]" htmlFor="recap-month-select">
              Mes
            </label>
            <select
              id="recap-month-select"
              value={selectedMonthKey}
              onChange={(event) => onSelectedMonthKeyChange(event.target.value)}
              className="w-full rounded-2xl border px-4 py-3 text-sm shadow-inner outline-none transition-all"
              style={{
                borderColor: "var(--app-border)",
                background: "var(--app-panel)",
                color: "var(--app-ink)",
              }}
            >
              {normalizedMonths.map((month) => (
                <option key={month.monthKey} value={month.monthKey}>
                  {month.label}
                </option>
              ))}
            </select>

            <button
              type="button"
              onClick={onPlay}
              disabled={isLoading || !selectedMonthKey || normalizedMonths.length === 0}
              className={cn(
                "inline-flex w-full items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-semibold transition-all",
                isLoading || !selectedMonthKey || normalizedMonths.length === 0
                  ? "cursor-not-allowed"
                  : "hover:-translate-y-0.5",
              )}
              style={{
                background:
                  isLoading || !selectedMonthKey || normalizedMonths.length === 0
                    ? "color-mix(in srgb, var(--app-muted-surface) 88%, transparent)"
                    : "var(--app-ink)",
                color:
                  isLoading || !selectedMonthKey || normalizedMonths.length === 0
                    ? "color-mix(in srgb, var(--app-ink) 32%, transparent)"
                    : "var(--app-surface)",
              }}
            >
              {isLoading ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Generando recap...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Ver recap mensual
                </>
              )}
            </button>

            <button
              type="button"
              onClick={onRegenerate}
              disabled={isLoading || !recap}
              className={cn(
                "inline-flex w-full items-center justify-center gap-2 rounded-2xl border px-4 py-3 text-sm font-semibold transition-all",
                isLoading || !recap
                  ? "cursor-not-allowed"
                  : "",
              )}
              style={{
                borderColor: "var(--app-border)",
                background:
                  isLoading || !recap
                    ? "color-mix(in srgb, var(--app-muted-surface) 70%, transparent)"
                    : "color-mix(in srgb, var(--app-panel) 92%, transparent)",
                color:
                  isLoading || !recap
                    ? "color-mix(in srgb, var(--app-ink) 38%, transparent)"
                    : "var(--app-ink)",
              }}
            >
              <RefreshCw className="h-4 w-4" />
              Regenerar
            </button>
          </div>

          <div className="mt-4 space-y-3">
          <div
            className="rounded-2xl border p-4"
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
            {error ? (
              <div className="rounded-2xl border border-[rgba(255,59,48,0.24)] bg-[rgba(255,59,48,0.08)] px-4 py-3 text-sm text-[var(--app-danger)]">
                {error}
              </div>
            ) : null}
            {normalizedMonths.length === 0 ? (
              <p className="text-sm text-[var(--app-muted)]">Todavía no hay meses disponibles. Añade actividad primero.</p>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  );
}

function normalizeMonth(month: InsightsRecapMonth | string) {
  if (typeof month === "string") {
    return { monthKey: month, label: formatMonthKeyLabel(month) };
  }

  return {
    monthKey: month.monthKey ?? month.month_key ?? "",
    label: month.label ?? month.month_label ?? formatMonthKeyLabel(month.monthKey ?? month.month_key ?? ""),
  };
}

function formatMonthKeyLabel(monthKey: string) {
  const match = monthKey.match(/^(\d{4})-(\d{2})$/);
  if (!match) {
    return monthKey;
  }

  const year = Number(match[1]);
  const month = Number(match[2]);
  return formatMonthLabel(year, month);
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
