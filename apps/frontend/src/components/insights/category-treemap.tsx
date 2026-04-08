"use client";

import { ResponsiveContainer, Treemap, Tooltip } from "recharts";
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

const CustomizedContent = (props: any) => {
  const { x, y, width, height, index, name, fill } = props;

  if (width < 30 || height < 20) return null;

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        style={{
          fill,
          stroke: "var(--app-surface)",
          strokeWidth: 2,
          strokeOpacity: 0.2,
        }}
        rx={8}
        ry={8}
      />
      <text
        x={x + width / 2}
        y={y + height / 2}
        textAnchor="middle"
        dominantBaseline="middle"
        fill="#fff"
        fontSize={Math.min(width / 6, 12)}
        fontWeight="600"
        style={{ pointerEvents: "none", textShadow: "0 1px 2px rgba(0,0,0,0.2)" }}
      >
        {name}
      </text>
    </g>
  );
};

export function CategoryTreemap({ data, className }: CategoryTreemapProps) {
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
        <h3 className="text-lg font-bold text-[var(--app-ink)]">Distribución de Gasto</h3>
        <p className="text-sm text-[var(--app-muted)]">Mapa de calor por volumen de categorías</p>
      </div>

      <div className="relative flex-1 w-full min-h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <Treemap
            data={data}
            dataKey="value"
            aspectRatio={4 / 3}
            stroke="#fff"
            content={<CustomizedContent />}
          >
            <Tooltip
              content={({ active, payload }: any) => {
                if (!active || !payload?.length) return null;
                const data = payload[0].payload;
                return (
                  <div
                    className="rounded-xl border p-3 py-2 shadow-sm backdrop-blur-md"
                    style={{
                      borderColor: "var(--app-border)",
                      background: "color-mix(in srgb, var(--app-surface) 90%, transparent)",
                    }}
                  >
                    <p className="text-sm font-bold text-[var(--app-text)]">{data.name}</p>
                    <p className="text-sm font-semibold text-[var(--app-accent)]">
                      €{Number(data.value).toFixed(2)}
                    </p>
                  </div>
                );
              }}
            />
          </Treemap>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
