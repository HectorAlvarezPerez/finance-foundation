export function formatCurrency(
  amount: number | string,
  currency: string,
  locale = "es-ES",
): string {
  const numericAmount = typeof amount === "number" ? amount : Number(amount);

  if (!Number.isFinite(numericAmount)) {
    return `${amount} ${currency}`;
  }

  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(numericAmount);
}

export function formatDate(value: string, locale = "es-ES"): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(locale, {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function formatMonthLabel(year: number, month: number, locale = "es-ES"): string {
  const date = new Date(year, month - 1, 1);

  return new Intl.DateTimeFormat(locale, {
    month: "long",
    year: "numeric",
  }).format(date);
}
