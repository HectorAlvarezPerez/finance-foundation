"use client";

import { formatCurrency } from "@/lib/format";
import { cn } from "@/lib/utils";

type CategoryData = {
  name: string;
  value: number;
  fill: string;
};

type CategoryTreemapProps = {
  data: CategoryData[];
  className?: string;
};

export function CategoryTreemap({ data, className }: CategoryTreemapProps) {
  if (!data || data.length === 0) return null;

  const sorted = [...data].sort((left, right) => right.value - left.value);
  const topCategories = sorted.slice(0, 6);
  const remainingTotal = sorted.slice(6).reduce((sum, item) => sum + item.value, 0);

  const distribution =
    remainingTotal > 0
      ? [...topCategories, { name: "Otras", value: remainingTotal, fill: "var(--app-muted)" }]
      : topCategories;

  const total = distribution.reduce((sum, item) => sum + item.value, 0);

  return (
    <div
      className={cn(
        "relative flex flex-col rounded-[2rem] border p-6 shadow-[var(--app-shadow-elevated)] backdrop-blur-xl overflow-hidden h-full",
        className
      )}
      style={{
        borderColor: "var(--app-border)",
        background: "color-mix(in srgb, var(--app-panel) 82%, transparent)",
      }}
    >
      <div className="mb-6 flex flex-col gap-1 relative z-10">
        <h3 className="text-lg font-bold text-[var(--app-ink)]">Distribución de Gasto</h3>
        <p className="text-sm text-[var(--app-muted)]">Ranking de categorías por peso relativo</p>
      </div>

      <div className="relative flex-1 w-full min-h-[300px] space-y-3">
        {distribution.map((category) => {
          const share = total > 0 ? (category.value / total) * 100 : 0;

          return (
            <div key={category.name} className="space-y-1.5">
              <div className="flex items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-2">
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{
                      backgroundColor: category.fill,
                    }}
                  />
                  <span className="truncate text-sm font-medium text-[var(--app-ink)]">{category.name}</span>
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-xs font-semibold text-[var(--app-muted)]">{share.toFixed(1)}%</p>
                  <p className="text-xs text-[var(--app-muted)]">{formatCurrency(category.value, "EUR")}</p>
                </div>
              </div>

              <div
                className="h-2.5 w-full overflow-hidden rounded-full"
                style={{
                  background: "color-mix(in srgb, var(--app-muted-surface) 88%, transparent)",
                }}
              >
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{
                    width: `${Math.max(share, 2)}%`,
                    background: buildPastelBarFill(category.fill),
                    border: `1px solid ${category.fill}`,
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

function buildPastelBarFill(color: string) {
  if (color.startsWith("var(")) {
    return `color-mix(in srgb, ${color} 26%, white)`;
  }

  if (color.startsWith("rgb") || color.startsWith("hsl")) {
    return `color-mix(in srgb, ${color} 26%, white)`;
  }

  const normalized = color.replace("#", "");
  if (normalized.length === 6) {
    const value = Number.parseInt(normalized, 16);
    const red = (value >> 16) & 255;
    const green = (value >> 8) & 255;
    const blue = value & 255;
    return `rgba(${red}, ${green}, ${blue}, 0.24)`;
  }

  return color;
}
