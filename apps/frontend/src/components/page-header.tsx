export function PageHeader({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <header className="animate-slideUp mb-5 sm:mb-8">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--app-accent)] sm:text-xs sm:tracking-[0.2em]">
        {eyebrow}
      </p>
      <h2 className="mt-1.5 text-2xl font-bold leading-tight tracking-normal sm:mt-2 sm:text-4xl">{title}</h2>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--app-muted)]">{description}</p>
    </header>
  );
}
