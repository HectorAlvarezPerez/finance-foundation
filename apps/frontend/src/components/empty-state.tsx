import { type LucideIcon, Inbox } from "lucide-react";
import Link from "next/link";

export function EmptyState({
  title,
  description,
  icon: Icon = Inbox,
  actionLabel,
  actionHref,
  onAction,
  variant = "surface",
}: {
  title: string;
  description: string;
  icon?: LucideIcon;
  actionLabel?: string;
  actionHref?: string;
  onAction?: () => void;
  variant?: "surface" | "plain";
}) {
  const containerClass =
    variant === "plain"
      ? "animate-fadeIn flex flex-col items-center px-6 py-12 text-center"
      : "animate-fadeIn flex flex-col items-center rounded-2xl border border-dashed border-[var(--app-border)] bg-[var(--app-muted-surface)] px-6 py-12 text-center";

  return (
    <div className={containerClass}>
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--app-accent-soft)]">
        <Icon className="h-6 w-6 text-[var(--app-accent)]" />
      </div>
      <p className="text-base font-semibold text-[var(--app-ink)]">{title}</p>
      <p className="mt-1.5 max-w-sm text-sm text-[var(--app-muted)]">{description}</p>
      {actionLabel && actionHref ? (
        <Link
          href={actionHref}
          className="mt-4 inline-flex items-center rounded-xl bg-[var(--app-accent)] px-4 py-2 text-sm font-semibold text-white transition-all hover:brightness-110"
        >
          {actionLabel}
        </Link>
      ) : actionLabel && onAction ? (
        <button
          type="button"
          onClick={onAction}
          className="mt-4 inline-flex items-center rounded-xl bg-[var(--app-accent)] px-4 py-2 text-sm font-semibold text-white transition-all hover:brightness-110"
        >
          {actionLabel}
        </button>
      ) : null}
    </div>
  );
}
