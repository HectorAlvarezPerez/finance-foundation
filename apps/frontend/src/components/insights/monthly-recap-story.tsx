"use client";

import { ArrowRight, ArrowUpRight, Sparkles } from "lucide-react";

import { AmountValue } from "@/components/amount-value";
import { cn } from "@/lib/utils";
import type {
  InsightsMonthlyRecapFact,
  InsightsMonthlyRecapStory,
  InsightsMonthlyRecapVisual,
} from "@/lib/types";

export function MonthlyRecapStoryCard({
  story,
  index,
  total,
}: {
  story: InsightsMonthlyRecapStory;
  index: number;
  total: number;
}) {
  return (
    <section
      className="relative mx-auto flex h-[calc(100dvh-8rem)] max-h-[640px] min-h-[420px] w-full flex-col overflow-hidden rounded-[2.25rem] border sm:h-[calc(100dvh-8.5rem)]"
      style={{
        borderColor: "var(--app-border)",
        background:
          "linear-gradient(180deg, color-mix(in srgb, var(--app-panel) 94%, var(--app-accent-soft) 6%), var(--app-panel-strong))",
        boxShadow: "var(--app-shadow-elevated)",
      }}
    >
      <div className="absolute inset-0 opacity-70" style={storyGlowStyle} />
      <div className="absolute inset-x-0 top-0 h-24" style={storyTopGlowStyle} />
      <div className="relative grid min-h-0 flex-1 grid-rows-[auto_auto_minmax(0,1fr)_auto] gap-2.5 p-4 sm:gap-3 sm:p-5">
        <div className="flex items-start justify-between gap-4">
          <RecapKindChip kind={story.kind} />
          <div
            className="rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em]"
            style={{
              borderColor: "var(--app-border)",
              background: "color-mix(in srgb, var(--app-panel) 84%, transparent)",
              color: "var(--app-muted)",
            }}
          >
            {index + 1}/{total}
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--app-muted)]">
            Recap mensual
          </p>
          <h2 className="text-[1.65rem] font-semibold leading-[1.06] tracking-tight text-[var(--app-ink)] sm:text-[1.9rem]">
            {story.headline}
          </h2>
          {story.subheadline ? (
            <p className="text-sm leading-6 text-[var(--app-muted)] sm:text-[15px]">
              {story.subheadline}
            </p>
          ) : null}
          {story.body ? (
            <p className="text-sm leading-6 text-[var(--app-text)] sm:text-[15px]">
              {story.body}
            </p>
          ) : null}
        </div>

        <div className="min-h-0 overflow-y-auto overflow-x-hidden">
          <RecapVisual visual={story.visual} />
        </div>

        <div className="space-y-2">
          {story.facts?.length ? (
            <div className="grid grid-cols-3 gap-2">
              {story.facts.slice(0, 3).map((fact) => (
                <FactChip key={`${fact.label}-${fact.value}`} fact={fact} />
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function RecapVisual({ visual }: { visual: InsightsMonthlyRecapVisual }) {
  switch (visual.kind) {
    case "top_category":
      return <TopCategoryVisual visual={visual as Extract<InsightsMonthlyRecapVisual, { kind: "top_category" }>} />;
    case "biggest_moment":
      return (
        <BiggestMomentVisual
          visual={visual as Extract<InsightsMonthlyRecapVisual, { kind: "biggest_moment" }>}
        />
      );
    case "month_comparison":
      return (
        <MonthComparisonVisual
          visual={visual as Extract<InsightsMonthlyRecapVisual, { kind: "month_comparison" }>}
        />
      );
    default:
      return <GenericVisual />;
  }
}

function TopCategoryVisual({
  visual,
}: {
  visual: Extract<InsightsMonthlyRecapVisual, { kind: "top_category" }>;
}) {
  const categoryColor = visual.category_color ?? "#0071e3";
  const series = visual.series?.length
    ? visual.series
    : [
        {
          label: visual.category_name ?? "Categoría principal",
          value: typeof visual.amount === "number" ? visual.amount : Number(visual.amount ?? 0),
          color: categoryColor,
        },
      ];
  const visibleSeries = series.slice(0, 3);
  const maxSeriesValue = Math.max(...visibleSeries.map((item) => Number(item.value ?? 0)), 1);

  return (
    <div
      className="mx-auto flex w-full max-w-[96%] flex-col rounded-[1.65rem] border p-3.5 sm:p-4"
      style={buildVisualCardStyle("top")}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--app-muted)]">
            Categoría principal
          </p>
          <h3 className="text-[1.45rem] font-semibold tracking-tight text-[var(--app-ink)] sm:text-[1.6rem]">
            {visual.category_name ?? "Categoría principal"}
          </h3>
        </div>
        {visual.share != null ? (
          <div
            className="rounded-full border px-3 py-1 text-xs font-semibold"
            style={{
              borderColor: "var(--app-border)",
              background: "color-mix(in srgb, var(--app-panel) 76%, transparent)",
              color: "var(--app-ink)",
            }}
          >
            {Math.round(visual.share)}% del mes
          </div>
        ) : null}
      </div>

      <div className="mt-3 grid grid-cols-[minmax(0,1fr)_84px] items-center gap-3 sm:grid-cols-[minmax(0,1fr)_96px] sm:gap-4">
        <div className="min-w-0">
          <p className="text-sm text-[var(--app-muted)]">Gasto destacado</p>
          <div className="mt-1 text-[1.95rem] font-semibold tracking-tight">
            <AmountValue
              amount={visual.amount ?? 0}
              currency="EUR"
              className="text-[1.95rem] font-semibold text-[var(--app-ink)]"
            />
          </div>
          <p className="mt-1 text-sm text-[var(--app-muted)]">
            {visibleSeries.length} señales comparadas
          </p>
        </div>
        <div
          className="mx-auto h-20 w-20 rounded-full border p-2 sm:h-24 sm:w-24"
          style={{
            borderColor: "var(--app-border)",
            background:
              "radial-gradient(circle, color-mix(in srgb, var(--app-panel) 50%, white 50%), transparent 72%)",
          }}
        >
          <div
            className="h-full w-full rounded-full"
            style={{
              background: `conic-gradient(${categoryColor} 0deg, ${categoryColor} 250deg, color-mix(in srgb, var(--app-muted-surface) 80%, transparent) 250deg)`,
            }}
          />
        </div>
      </div>

      <div className="mt-4 grid content-start gap-2.5">
        {visibleSeries.map((item, index) => {
          const value = Number(item.value ?? 0);
          const width = Math.max(14, Math.min(100, (value / maxSeriesValue) * 100));
          return (
            <div key={`${item.label}-${index}`} className="space-y-1.5">
              <div className="flex items-center justify-between text-sm text-[var(--app-muted)]">
                <span>{item.label}</span>
                <span>{compactNumber(value)}</span>
              </div>
              <div className="h-2.5 rounded-full bg-[var(--app-muted-surface)]">
                <div
                  className="h-2.5 rounded-full transition-all duration-700"
                  style={{
                    width: `${width}%`,
                    background: item.color ?? categoryColor,
                    boxShadow: `0 0 18px ${colorWithAlpha(item.color ?? categoryColor, 0.35)}`,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function BiggestMomentVisual({
  visual,
}: {
  visual: Extract<InsightsMonthlyRecapVisual, { kind: "biggest_moment" }>;
}) {
  return (
    <div
      className="mx-auto flex w-full max-w-[96%] flex-col rounded-[1.65rem] border p-3.5 sm:p-4"
      style={buildVisualCardStyle("neutral")}
    >
      <div className="flex items-center justify-between gap-3">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--app-muted)]">
            Momento clave
          </p>
        <div className="rounded-full bg-[var(--app-accent-soft)] px-3 py-1 text-xs font-semibold text-[var(--app-accent)]">
          Mayor gasto
        </div>
      </div>

      <div className="mt-3 flex flex-col justify-between gap-3">
        <div className="space-y-2.5">
          <div className="flex items-end gap-4">
            <div className="text-[1.95rem] font-semibold tracking-tight text-[var(--app-ink)] sm:text-[2.05rem]">
              <AmountValue amount={visual.amount ?? 0} currency="EUR" className="text-[1.95rem] font-semibold sm:text-[2.05rem]" />
            </div>
            <ArrowUpRight className="mb-1 h-6 w-6 text-[var(--app-danger)]" />
          </div>
          {visual.date_label ? (
            <p className="text-sm font-medium text-[var(--app-muted)]">{visual.date_label}</p>
          ) : null}
          {visual.merchant ? (
            <h3 className="text-[1.45rem] font-semibold tracking-tight text-[var(--app-ink)] sm:text-[1.55rem]">
              {visual.merchant}
            </h3>
          ) : null}
          {visual.description ? (
            <p className="text-sm leading-6 text-[var(--app-muted)]">{visual.description}</p>
          ) : null}
        </div>

        <div className="relative shrink-0 overflow-hidden rounded-[1.35rem] border border-[var(--app-border)] bg-[linear-gradient(180deg,color-mix(in_srgb,var(--app-danger-soft)_65%,transparent),color-mix(in_srgb,var(--app-panel)_94%,transparent))] p-3.5">
          <div className="absolute inset-x-0 top-0 h-1 bg-[linear-gradient(90deg,var(--app-danger),transparent)]" />
          <div className="grid grid-cols-2 gap-3">
            <MetricTile label="Impacto" value="Pico" tone="danger" />
            <MetricTile label="Señal" value="Dato real" tone="accent" />
          </div>
        </div>
      </div>
    </div>
  );
}

function MonthComparisonVisual({
  visual,
}: {
  visual: Extract<InsightsMonthlyRecapVisual, { kind: "month_comparison" }>;
}) {
  const previousLabel = formatMonthDisplayLabel(visual.previous_label ?? "Mes anterior");
  const currentLabel = formatMonthDisplayLabel(visual.current_label ?? "Este mes");
  const current = parseNumericAmount(visual.current_amount) ?? 0;
  const previous = parseNumericAmount(visual.previous_amount) ?? 0;
  const previousColor = normalizeVisualColor(
    visual.previous_color,
    "color-mix(in srgb, var(--app-ink) 24%, transparent)",
  );
  const currentColor = normalizeVisualColor(visual.current_color, "var(--app-accent)");
  const max = Math.max(Math.abs(current), Math.abs(previous), 1);
  const delta = parseNumericAmount(visual.delta) ?? current - previous;
  const isPositive = delta >= 0;

  return (
    <div
      className="mx-auto flex w-full max-w-[96%] flex-col rounded-[1.65rem] border p-3.5 sm:p-4"
      style={buildVisualCardStyle("comparison")}
    >
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--app-muted)]">
          Comparativa mensual
        </p>
        <div
          className={cn(
            "rounded-full px-3 py-1 text-xs font-semibold",
            isPositive ? "bg-[rgba(52,199,89,0.18)] text-[var(--app-success)]" : "bg-[rgba(255,59,48,0.18)] text-[var(--app-danger)]",
          )}
        >
          {isPositive ? "Sube" : "Baja"} {compactNumber(Math.abs(delta))}
        </div>
      </div>

      <div className="mt-3 grid grid-cols-[1fr_1fr] items-end gap-2.5 sm:gap-3">
        <ComparisonColumn
          label={previousLabel}
          amount={previous}
          max={max}
          color={previousColor}
          tone="muted"
        />
        <ComparisonColumn
          label={currentLabel}
          amount={current}
          max={max}
          color={currentColor}
          tone="active"
        />
      </div>

      <div className="mt-3 shrink-0 rounded-[1.35rem] border p-3.5" style={buildSubPanelStyle()}>
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--app-muted)]">
              Diferencia
            </p>
            <div className="mt-1 flex items-center gap-2 text-[1.6rem] font-semibold tracking-tight text-[var(--app-ink)]">
              <ArrowRight className={cn("h-5 w-5", isPositive ? "rotate-[-30deg] text-[var(--app-success)]" : "rotate-[30deg] text-[var(--app-danger)]")} />
              <span className="whitespace-nowrap tabular-nums text-[1.6rem] font-semibold text-[var(--app-ink)]">
                {formatStrictCurrency(delta, "EUR")}
              </span>
            </div>
          </div>
          <div className="text-right text-sm text-[var(--app-muted)]">
            <p>{previousLabel} vs {currentLabel}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function ComparisonColumn({
  label,
  amount,
  max,
  color,
  tone,
}: {
  label: string;
  amount: number;
  max: number;
  color: string;
  tone: "active" | "muted";
}) {
  const safeAmount = Number.isFinite(amount) ? amount : 0;
  const safeMax = Number.isFinite(max) && max > 0 ? max : 1;
  const height = Math.max(18, Math.min(100, (Math.abs(safeAmount) / safeMax) * 100));
  const fillColor = tone === "muted" ? "var(--app-muted)" : color;
  const fillOpacity = tone === "muted" ? 0.7 : 1;
  const shadowAlpha = tone === "muted" ? 0.14 : 0.2;

  return (
    <div className="flex min-h-0 flex-col items-center justify-end gap-2.5">
      <div className="text-center">
        <p className={cn("text-sm font-medium", tone === "active" ? "text-[var(--app-ink)]" : "text-[var(--app-muted)]")}>
          {label}
        </p>
        <p className="mt-1 text-base font-semibold">
          <AmountValue amount={amount} currency="EUR" className="text-base font-semibold text-[var(--app-ink)]" />
        </p>
      </div>
      <div
        className="flex h-24 w-full items-end justify-center rounded-[1.15rem] border p-2.5 sm:h-28"
        style={buildSubPanelStyle()}
      >
          <div
            data-testid={`comparison-bar-${tone}`}
            className="w-full rounded-[1rem] transition-all duration-700"
            style={{
              height: `${height}%`,
              background: buildColumnFill(fillColor),
              boxShadow: `0 0 28px ${colorWithAlpha(fillColor, shadowAlpha)}`,
              opacity: fillOpacity,
            }}
        />
      </div>
    </div>
  );
}

function GenericVisual() {
  return (
    <div
      className="flex items-center justify-center rounded-[1.9rem] border p-6"
      style={buildVisualCardStyle("neutral")}
    >
      <div className="max-w-sm text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--app-muted)]">
          Visual
        </p>
        <h3 className="mt-3 text-2xl font-semibold tracking-tight text-[var(--app-ink)]">
          Una story construida con tu actividad reciente
        </h3>
        <p className="mt-3 text-sm leading-6 text-[var(--app-muted)]">
          El backend puede sustituir este visual por otro más rico sin cambiar el contenedor del frontend.
        </p>
      </div>
    </div>
  );
}

function RecapKindChip({ kind }: { kind: string }) {
  const label = getKindLabel(kind);
  const toneClass =
    kind === "top_category"
      ? "border-[rgba(111,66,193,0.28)] bg-[rgba(111,66,193,0.12)] text-[color:color-mix(in_srgb,var(--app-accent)_86%,#6f42c1)]"
      : kind === "biggest_moment"
        ? "border-[rgba(255,59,48,0.24)] bg-[rgba(255,59,48,0.1)] text-[var(--app-danger)]"
        : kind === "month_comparison"
          ? "border-[rgba(52,199,89,0.24)] bg-[rgba(52,199,89,0.1)] text-[var(--app-success)]"
          : "border-[var(--app-border)] bg-[var(--app-muted-surface)] text-[var(--app-muted)]";

  return (
    <div className={cn("inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em]", toneClass)}>
      <Sparkles className="h-3.5 w-3.5" />
      {label}
    </div>
  );
}

const storyGlowStyle = {
  background:
    "radial-gradient(circle at top left, color-mix(in srgb, var(--app-accent) 18%, transparent), transparent 32%), radial-gradient(circle at bottom right, color-mix(in srgb, var(--app-success) 14%, transparent), transparent 28%), linear-gradient(180deg, color-mix(in srgb, var(--app-panel) 12%, transparent), transparent)",
} as const;

const storyTopGlowStyle = {
  background:
    "linear-gradient(180deg, color-mix(in srgb, var(--app-panel) 8%, white), transparent)",
} as const;

function buildVisualCardStyle(kind: "top" | "neutral" | "comparison") {
  if (kind === "top") {
    return {
      borderColor: "var(--app-border)",
      background:
        "linear-gradient(180deg, color-mix(in srgb, var(--app-panel) 91%, var(--app-accent-soft) 9%), color-mix(in srgb, var(--app-panel-strong) 95%, transparent))",
      boxShadow: "var(--app-shadow)",
    } as const;
  }

  if (kind === "comparison") {
    return {
      borderColor: "var(--app-border)",
      background:
        "linear-gradient(180deg, color-mix(in srgb, var(--app-panel) 90%, var(--app-success-soft) 10%), color-mix(in srgb, var(--app-panel-strong) 95%, transparent))",
      boxShadow: "var(--app-shadow)",
    } as const;
  }

  return {
    borderColor: "var(--app-border)",
    background:
      "linear-gradient(180deg, var(--app-panel), color-mix(in srgb, var(--app-panel-strong) 94%, transparent))",
    boxShadow: "var(--app-shadow)",
  } as const;
}

function buildSubPanelStyle() {
  return {
    borderColor: "var(--app-border)",
    background: "color-mix(in srgb, var(--app-muted-surface) 80%, transparent)",
  } as const;
}

function FactChip({ fact }: { fact: InsightsMonthlyRecapFact }) {
  const toneClass =
    fact.tone === "positive"
      ? "border-[rgba(52,199,89,0.24)] bg-[rgba(52,199,89,0.08)] text-[var(--app-success)]"
      : fact.tone === "negative"
        ? "border-[rgba(255,59,48,0.24)] bg-[rgba(255,59,48,0.08)] text-[var(--app-danger)]"
        : fact.tone === "accent"
          ? "border-[rgba(0,113,227,0.24)] bg-[rgba(0,113,227,0.08)] text-[var(--app-accent)]"
          : "border-[var(--app-border)] bg-[var(--app-muted-surface)] text-[var(--app-ink)]";

  return (
    <div className={cn("min-w-0 rounded-2xl border px-2.5 py-2 text-sm", toneClass)}>
      <p className="text-[10px] font-semibold uppercase leading-[1.2] tracking-[0.08em] opacity-70 whitespace-normal break-words">
        {fact.label}
      </p>
      <p className="mt-0.5 text-sm font-medium leading-tight text-inherit">{fact.value}</p>
    </div>
  );
}

function MetricTile({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "danger" | "accent" | "success";
}) {
  const toneClass =
    tone === "danger"
      ? "bg-[rgba(255,59,48,0.12)] text-[var(--app-danger)]"
      : tone === "success"
        ? "bg-[rgba(52,199,89,0.12)] text-[var(--app-success)]"
        : "bg-[rgba(0,113,227,0.12)] text-[var(--app-accent)]";

  return (
    <div className={cn("rounded-2xl border border-white/10 px-3 py-3 text-center", toneClass)}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] opacity-70">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}

function getKindLabel(kind: string) {
      switch (kind) {
    case "top_category":
      return "Categoría principal";
    case "biggest_moment":
      return "Momento clave";
    case "month_comparison":
      return "Comparativa mensual";
    default:
      return kind.replaceAll("_", " ");
  }
}

function compactNumber(value: number) {
  if (!Number.isFinite(value)) {
    return "0";
  }

  if (Math.abs(value) >= 1000) {
    return `${Math.round(value / 1000)}k`;
  }

  return `${Math.round(value)}`;
}

function formatMonthDisplayLabel(label: string) {
  const rawLabel = label.trim();
  if (!rawLabel) {
    return label;
  }

  const normalized = rawLabel.toLowerCase().replace(".", "");
  const shortPattern = /^(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)\s+(\d{2}|\d{4})$/i;
  const isoPattern = /^(\d{4})-(\d{2})$/;

  const shortMatch = normalized.match(shortPattern);
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
      const date = new Date(year, month - 1, 1);
      const monthName = new Intl.DateTimeFormat("es-ES", { month: "long" }).format(date);
      return `${monthName} ${year}`;
    }
  }

  const isoMatch = normalized.match(isoPattern);
  if (isoMatch) {
    const year = Number(isoMatch[1]);
    const month = Number(isoMatch[2]);
    if (Number.isFinite(year) && month >= 1 && month <= 12) {
      const date = new Date(year, month - 1, 1);
      const monthName = new Intl.DateTimeFormat("es-ES", { month: "long" }).format(date);
      return `${monthName} ${year}`;
    }
  }

  return rawLabel;
}

function parseNumericAmount(value: unknown) {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }

  if (typeof value !== "string") {
    return null;
  }

  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }

  let normalized = trimmed.replace(/\s+/g, "").replace(/[^\d,.-]/g, "");
  if (!normalized) {
    return null;
  }

  const hasComma = normalized.includes(",");
  const hasDot = normalized.includes(".");

  if (hasComma && hasDot) {
    const lastComma = normalized.lastIndexOf(",");
    const lastDot = normalized.lastIndexOf(".");

    if (lastComma > lastDot) {
      normalized = normalized.replace(/\./g, "").replace(",", ".");
    } else {
      normalized = normalized.replace(/,/g, "");
    }
  } else if (hasComma) {
    const parts = normalized.split(",");
    const decimalPart = parts[parts.length - 1] ?? "";
    if (parts.length > 1 && decimalPart.length <= 2) {
      normalized = `${parts.slice(0, -1).join("")}.${decimalPart}`;
    } else {
      normalized = parts.join("");
    }
  } else if (hasDot) {
    const parts = normalized.split(".");
    const decimalPart = parts[parts.length - 1] ?? "";
    if (parts.length > 1 && decimalPart.length <= 2) {
      normalized = `${parts.slice(0, -1).join("")}.${decimalPart}`;
    } else {
      normalized = parts.join("");
    }
  }

  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatStrictCurrency(amount: number, currency: string, locale = "es-ES") {
  const safeAmount = Number.isFinite(amount) ? amount : 0;
  const normalizedAmount = Math.abs(safeAmount) < 0.005 ? 0 : safeAmount;

  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(normalizedAmount);
}

function normalizeVisualColor(value: unknown, fallback: string) {
  if (typeof value !== "string") {
    return fallback;
  }

  const color = value.trim();
  if (!color) {
    return fallback;
  }

  if (
    color.startsWith("var(") ||
    color.startsWith("rgb(") ||
    color.startsWith("rgba(") ||
    color.startsWith("hsl(") ||
    color.startsWith("hsla(")
  ) {
    return color;
  }

  if (/^#([\da-fA-F]{3}|[\da-fA-F]{4}|[\da-fA-F]{6}|[\da-fA-F]{8})$/.test(color)) {
    return color;
  }

  if (/^[a-zA-Z]+$/.test(color)) {
    return color;
  }

  return fallback;
}

function colorWithAlpha(color: string, alpha: number) {
  if (color.startsWith("var(")) {
    return `color-mix(in srgb, ${color} ${Math.round(alpha * 100)}%, transparent)`;
  }

  if (color.startsWith("rgb") || color.startsWith("hsl")) {
    return color;
  }

  const normalized = color.replace("#", "");
  if (normalized.length === 6) {
    const value = Number.parseInt(normalized, 16);
    const red = (value >> 16) & 255;
    const green = (value >> 8) & 255;
    const blue = value & 255;
    return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
  }

  return color;
}

function buildColumnFill(color: string) {
  if (color.startsWith("var(")) {
    return `linear-gradient(180deg, ${color}, color-mix(in srgb, ${color} 70%, transparent))`;
  }

  if (color.startsWith("rgb") || color.startsWith("hsl")) {
    return `linear-gradient(180deg, ${color}, ${color})`;
  }

  const normalized = color.replace("#", "");
  if (normalized.length === 6) {
    const value = Number.parseInt(normalized, 16);
    const red = (value >> 16) & 255;
    const green = (value >> 8) & 255;
    const blue = value & 255;
    return `linear-gradient(180deg, rgba(${red}, ${green}, ${blue}, 1), rgba(${red}, ${green}, ${blue}, 0.65))`;
  }

  return color;
}
