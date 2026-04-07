"use client";

import { RefreshCw, Sparkles, Play } from "lucide-react";

import { formatMonthLabel } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { InsightsMonthlyRecap, InsightsRecapMonth } from "@/lib/types";

export function MonthlyRecapLauncher({
  compact = false,
  months,
  selectedMonthKey,
  onSelectedMonthKeyChange,
  onPlay,
  onRegenerate,
  isLoading,
  recap,
  error,
}: {
  compact?: boolean;
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
  const compactStatusText = recap ? getStatusLabel(recap.is_stale) : "Sin recap";

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
          compact ? "gap-3 p-3 sm:p-4" : "gap-4 p-4 sm:p-5 lg:grid-cols-[1.1fr_0.9fr] lg:gap-5",
        )}
      >
        <div className={cn("flex min-h-0 flex-col justify-between", compact ? "gap-3" : "gap-4")}>
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 rounded-full border border-[var(--app-border)] bg-[var(--app-muted-surface)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--app-muted)] backdrop-blur">
              <Sparkles className="h-3.5 w-3.5" />
              Recap mensual
            </div>
            <div className="space-y-1.5">
              <h2
                className={cn(
                  "font-semibold tracking-tight text-[var(--app-ink)]",
                  compact ? "max-w-xl text-xl sm:text-2xl" : "max-w-2xl text-2xl sm:text-[2rem]",
                )}
              >
                Tu mes, contado en historias.
              </h2>
              <p className={cn("text-[var(--app-muted)]", compact ? "max-w-xl text-xs leading-5 sm:text-sm" : "max-w-xl text-sm leading-5")}>
                Elige un mes y recorre 2-3 stories creadas con señales reales de gasto.
              </p>
            </div>
          </div>

          <div className={cn("flex flex-wrap text-xs text-[var(--app-muted)]", compact ? "gap-1.5" : "gap-2")}>
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
          className={cn(
            "relative border backdrop-blur-xl",
            compact ? "rounded-[1.2rem] p-3" : "rounded-[1.35rem] p-3.5",
          )}
          style={{
            borderColor: "var(--app-border)",
            background: "color-mix(in srgb, var(--app-panel) 82%, transparent)",
          }}
        >
          <div className={cn(compact ? "space-y-2" : "space-y-2.5")}>
            <label className="block text-xs font-semibold uppercase tracking-[0.18em] text-[var(--app-muted)]" htmlFor="recap-month-select">
              Mes
            </label>
            <select
              id="recap-month-select"
              value={selectedMonthKey}
              onChange={(event) => onSelectedMonthKeyChange(event.target.value)}
              className={cn(
                "w-full rounded-2xl border px-4 text-sm shadow-inner outline-none transition-all",
                compact ? "py-2" : "py-2.5",
              )}
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

            <div
              className={cn(
                compact
                  ? "grid gap-2 sm:grid-cols-[1fr_1fr_auto] sm:items-stretch"
                  : "space-y-2.5",
              )}
            >
              <button
                type="button"
                onClick={onPlay}
                disabled={isLoading || !selectedMonthKey || normalizedMonths.length === 0}
                className={cn(
                  "inline-flex w-full items-center justify-center gap-2 rounded-2xl px-4 text-sm font-semibold transition-all",
                  compact ? "py-2" : "py-2.5",
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
                disabled={isLoading || !selectedMonthKey || normalizedMonths.length === 0}
                className={cn(
                  "inline-flex w-full items-center justify-center gap-2 rounded-2xl border px-4 text-sm font-semibold transition-all",
                  compact ? "py-2" : "py-2.5",
                  isLoading || !selectedMonthKey || normalizedMonths.length === 0
                    ? "cursor-not-allowed"
                    : "",
                )}
                style={{
                  borderColor: "var(--app-border)",
                  background:
                    isLoading || !selectedMonthKey || normalizedMonths.length === 0
                      ? "color-mix(in srgb, var(--app-muted-surface) 70%, transparent)"
                      : "color-mix(in srgb, var(--app-panel) 92%, transparent)",
                  color:
                    isLoading || !selectedMonthKey || normalizedMonths.length === 0
                      ? "color-mix(in srgb, var(--app-ink) 38%, transparent)"
                      : "var(--app-ink)",
                }}
              >
                <RefreshCw className="h-4 w-4" />
                Regenerar
              </button>

              {compact ? (
                <div
                  className="rounded-2xl border px-3 py-2 text-left"
                  style={{
                    borderColor: "var(--app-border)",
                    background: "color-mix(in srgb, var(--app-muted-surface) 80%, transparent)",
                  }}
                >
                  <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--app-muted)]">
                    Estado
                  </p>
                  <p className="mt-0.5 text-sm font-medium text-[var(--app-text)]">{compactStatusText}</p>
                </div>
              ) : null}
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

  const monthKey = month.monthKey ?? month.month_key ?? "";
  const rawLabel = month.label ?? month.month_label ?? "";

  return {
    monthKey,
    label: formatMonthSelectionLabel(rawLabel, monthKey),
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

function formatMonthSelectionLabel(label: string, monthKey: string) {
  const normalizedLabel = label.trim();

  if (normalizedLabel) {
    const shortMonthPattern = /^(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)\s+(\d{2}|\d{4})$/i;
    const shortMatch = normalizedLabel.toLowerCase().replace(".", "").match(shortMonthPattern);

    if (shortMatch) {
      const monthByShortName: Record<string, number> = {
        ene: 1,
        feb: 2,
        mar: 3,
        abr: 4,
        may: 5,
        jun: 6,
        jul: 7,
        ago: 8,
        sep: 9,
        oct: 10,
        nov: 11,
        dic: 12,
      };

      const month = monthByShortName[shortMatch[1]];
      const parsedYear = Number(shortMatch[2]);
      const year = shortMatch[2].length === 2 ? 2000 + parsedYear : parsedYear;

      if (month && Number.isFinite(year)) {
        return formatMonthLabel(year, month);
      }
    }

    const labelAsIso = normalizedLabel.match(/^(\d{4})-(\d{2})$/);
    if (labelAsIso) {
      return formatMonthKeyLabel(normalizedLabel);
    }

    const longMonthPattern = /^(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+\d{4}$/i;
    if (longMonthPattern.test(normalizedLabel)) {
      return normalizedLabel;
    }
  }

  if (monthKey) {
    return formatMonthKeyLabel(monthKey);
  }

  return normalizedLabel || label;
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
