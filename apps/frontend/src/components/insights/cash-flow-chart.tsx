"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";
import { cn } from "@/lib/utils";

type MonthlyData = {
  month: string;
  income: number;
  expenses: number;
  net: number;
};

type CashFlowChartProps = {
  data: MonthlyData[];
  className?: string;
};

export function CashFlowChart({ data, className }: CashFlowChartProps) {
  if (!data || data.length === 0) return null;

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
        <h3 className="text-lg font-bold text-[var(--app-ink)]">Flujo de Caja</h3>
        <p className="text-sm text-[var(--app-muted)]">Comparativa de ingresos vs gastos por mes</p>
      </div>

      <div className="relative flex-1 w-full min-h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="colorIncome" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--app-success)" stopOpacity={0.3} />
                <stop offset="95%" stopColor="var(--app-success)" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorExpenses" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--app-danger)" stopOpacity={0.3} />
                <stop offset="95%" stopColor="var(--app-danger)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="4 4"
              vertical={false}
              stroke="color-mix(in srgb, var(--app-border) 60%, transparent)"
            />
            <XAxis
              dataKey="month"
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
              content={({ active, payload, label }: any) => {
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
                      {label}
                    </p>
                    {payload.map((entry: any, idx: number) => (
                      <div key={idx} className="flex items-center justify-between gap-4 py-0.5">
                        <span className="text-sm text-[var(--app-text)]">
                          {entry.name === "income" ? "Ingresos" : "Gastos"}
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
            <Legend
               formatter={(value: string) => (value === "income" ? "Ingresos" : "Gastos")}
               wrapperStyle={{ fontSize: 11, paddingTop: 20 }}
            />
            <Area
              type="monotone"
              dataKey="income"
              name="income"
              stroke="var(--app-success)"
              strokeWidth={3}
              fillOpacity={1}
              fill="url(#colorIncome)"
            />
            <Area
              type="monotone"
              dataKey="expenses"
              name="expenses"
              stroke="var(--app-danger)"
              strokeWidth={3}
              fillOpacity={1}
              fill="url(#colorExpenses)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
