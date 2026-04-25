"use client";

import { useSettings } from "@/components/settings-provider";
import { formatCurrency } from "@/lib/format";
import { cn } from "@/lib/utils";

export function AmountValue({
  amount,
  currency,
  className,
}: {
  amount: number | string;
  currency: string;
  className?: string;
}) {
  const numericAmount = typeof amount === "number" ? amount : Number(amount);
  const { settings } = useSettings();
  const locale = settings?.locale ?? "es-ES";

  return (
    <span
      className={cn(
        "font-semibold",
        numericAmount > 0 && "text-green-600",
        numericAmount < 0 && "text-red-600",
        numericAmount === 0 && "text-[var(--app-ink)]",
        className,
      )}
    >
      {formatCurrency(amount, currency, locale)}
    </span>
  );
}
