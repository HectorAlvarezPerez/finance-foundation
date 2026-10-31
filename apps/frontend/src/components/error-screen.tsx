"use client";

type ErrorScreenProps = {
  title?: string;
  description?: string;
};

const defaultTitle = "Se ha producido un error";
const defaultDescription =
  "No hemos podido cargar la aplicación en este momento. Inténtalo de nuevo más tarde.";

export function ErrorScreen({
  title = defaultTitle,
  description = defaultDescription,
}: ErrorScreenProps) {
  return (
    <div className="flex min-h-screen items-center justify-center px-6 py-10">
      <div className="w-full max-w-lg rounded-3xl border border-[var(--app-border)] bg-[var(--app-panel)] px-8 py-10 text-center shadow-[var(--app-shadow-elevated)]">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--app-muted)]">
          Finance Foundation
        </p>
        <h1 className="mt-4 text-3xl font-semibold tracking-tight text-[var(--app-ink)]">{title}</h1>
        <p className="mt-3 text-sm leading-6 text-[var(--app-muted)]">{description}</p>
      </div>
    </div>
  );
}
