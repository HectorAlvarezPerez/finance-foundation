"use client";

import { Badge } from "@/components/ui/badge";
import type { Category } from "@/lib/types";

export function CategoryBadge({
  category,
  fallback = "Sin categoría",
  variant = "pill",
}: {
  category?: Category | null;
  fallback?: string;
  variant?: "pill" | "inline";
}) {
  const color = category?.color ?? "#94a3b8";
  const label = category?.name ?? fallback;

  if (variant === "inline") {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-[var(--app-muted)]">
        <span
          className="h-1.5 w-1.5 rounded-full"
          style={{ backgroundColor: color }}
          aria-hidden="true"
        />
        <span>{label}</span>
      </span>
    );
  }

  return (
    <Badge
      className="gap-1.5 border-transparent"
      style={{
        color,
        backgroundColor: hexToRgba(color, 0.12),
      }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: color }}
        aria-hidden="true"
      />
      {label}
    </Badge>
  );
}

function hexToRgba(hex: string, alpha: number) {
  const normalized = hex.replace("#", "");

  if (normalized.length !== 6) {
    return `rgba(148, 163, 184, ${alpha})`;
  }

  const value = Number.parseInt(normalized, 16);
  const red = (value >> 16) & 255;
  const green = (value >> 8) & 255;
  const blue = value & 255;

  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}
