"use client";

import { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { cn } from "@/lib/utils";

/**
 * Ensures we map the type correctly regardless if it comes via "InsightsDailyPacingRead"
 * or another shared structure.
 */
type DailyPacingData = {
  day: number;
  current_month_cumulative: number | null;
  previous_month_cumulative: number | null;
};

type CumulativePacingChartProps = {
  data: DailyPacingData[];
  className?: string;
};

type ChartTooltipEntry = {
  dataKey?: string;
  color?: string;
  value?: number | string;
};

type ChartTooltipContent = {
  active?: boolean;
  payload?: ChartTooltipEntry[];
  label?: string | number;
};

export function CumulativePacingChart({ data, className }: CumulativePacingChartProps) {
  const formattedData = useMemo(() => {
    return data.map((item) => ({
      ...item,
      // Recharts handles nulls if we set connectNulls or if we want the line to stop
      // it stops automatically when it hits a null (which is perfect for current month).
      current_month_cumulative: item.current_month_cumulative,
      previous_month_cumulative: item.previous_month_cumulative,
    }));
  }, [data]);

  if (!data || data.length === 0) {
    return null;
  }

  // Calculate if pacing is better (less cumulative spend) or worse (more) than previous month.
  const currentTotal =
    data.filter((d) => d.current_month_cumulative !== null).slice(-1)[0]?.current_month_cumulative || 0;
  const prevTotal =
    data.filter((d) => d.previous_month_cumulative !== null).slice(-1)[0]?.previous_month_cumulative || 0;

  const isWorse = currentTotal > prevTotal;

  return (
    <div
      className={cn(
        "relative flex flex-col rounded-[2rem] border p-6 shadow-[var(--app-shadow-elevated)] backdrop-blur-xl overflow-hidden",
        className
      )}
      style={{
        borderColor: "var(--app-border)",
        background: "color-mix(in srgb, var(--app-panel) 82%, transparent)",
      }}
    >
      <div className="mb-6 flex flex-col gap-2 relative z-10">
        <div>
          <h3 className="text-lg font-bold text-[var(--app-ink)]">Ritmo de Gasto Mensual</h3>
          <p className="text-sm text-[var(--app-muted)]">Gasto acumulado día a día</p>
        </div>
        <div className="flex items-center gap-4 text-xs font-medium">
          <div className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-[var(--app-accent)]" />
            <span className="text-[var(--app-text)]">Mes actual</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-[var(--app-border)] border border-[var(--app-muted)] border-dashed" />
            <span className="text-[var(--app-muted)]">Mes anterior</span>
          </div>
        </div>
      </div>

      <div className="relative h-[250px] w-full mt-auto">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={formattedData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid
              strokeDasharray="4 4"
              vertical={false}
              stroke="color-mix(in srgb, var(--app-border) 60%, transparent)"
            />
            <XAxis
              dataKey="day"
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11, fill: "var(--app-muted)" }}
              dy={10}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tickFormatter={(val) => `€${val}`}
              tick={{ fontSize: 11, fill: "var(--app-muted)" }}
            />
            <Tooltip
              content={({ active, payload, label }: ChartTooltipContent) => {
                if (!active || !payload?.length) return null;
                return (
                  <div
                    className="rounded-xl border p-3 py-2 shadow-sm backdrop-blur-md"
                    style={{
                      borderColor: "var(--app-border)",
                      background: "color-mix(in srgb, var(--app-surface) 90%, transparent)",
                    }}
                  >
                    <p className="mb-1 text-[11px] font-bold uppercase tracking-wider text-[var(--app-muted)]">
                      Día {String(label ?? "")}
                    </p>
                    {payload.map((entry, idx) => (
                      <div key={idx} className="flex items-center justify-between gap-4 py-0.5">
                        <span className="text-sm text-[var(--app-text)]">
                          {entry.dataKey === "current_month_cumulative" ? "Actual" : "Anterior"}
                        </span>
                        <span className="text-sm font-semibold" style={{ color: entry.color }}>
                          €{Number(entry.value).toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                );
              }}
            />
            {/* Previous month baseline */}
            <Line
              type="monotone"
              dataKey="previous_month_cumulative"
              stroke="var(--app-muted)"
              strokeWidth={2}
              strokeDasharray="4 4"
              dot={false}
              activeDot={{ r: 4, fill: "var(--app-muted)" }}
              isAnimationActive={false}
            />
            {/* Current month pacing */}
            <Line
              type="monotone"
              dataKey="current_month_cumulative"
              stroke={isWorse ? "var(--app-danger)" : "var(--app-accent)"}
              strokeWidth={3}
              dot={false}
              activeDot={{ r: 6, fill: "var(--app-surface)", strokeWidth: 2 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Absolute positioning background glow based on pacing */}
      <div
        className={cn(
          "pointer-events-none absolute inset-0 -z-0 opacity-10 transition-colors duration-1000",
          isWorse ? "bg-gradient-to-t from-[var(--app-danger)] to-transparent" : "bg-gradient-to-t from-[var(--app-accent)] to-transparent"
        )}
      />
    </div>
  );
}
