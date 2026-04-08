import { cn } from "@/lib/utils";

type BrandLogoProps = {
  className?: string;
  compact?: boolean;
  showText?: boolean;
};

export function BrandLogo({ className, compact = false, showText = true }: BrandLogoProps) {
  return (
    <div className={cn("inline-flex items-center gap-3 text-[var(--app-ink)]", className)}>
      <svg
        viewBox="0 0 58 58"
        aria-hidden="true"
        className={cn(compact ? "h-8 w-8" : "h-10 w-10")}
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M17 10.5h19"
          stroke="currentColor"
          strokeWidth="2.8"
          strokeLinecap="round"
          fill="none"
        />
        <path
          d="M17 10.5a6 6 0 0 0-6 6V42a6 6 0 0 0 9.93 4.53l9.57-8.2A17 17 0 0 1 41.56 34H49"
          stroke="currentColor"
          strokeWidth="2.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
        <path
          d="M24 24h19"
          stroke="currentColor"
          strokeWidth="2.8"
          strokeLinecap="round"
          fill="none"
        />
        <path
          d="M30 45.5h19"
          stroke="var(--app-accent)"
          strokeWidth="3.4"
          strokeLinecap="round"
          fill="none"
        />
      </svg>

      {showText ? (
        <span className="leading-none">
          <span className={cn("block font-bold tracking-[-0.02em]", compact ? "text-base" : "text-2xl")}>
            Finance
          </span>
          <span className={cn("block font-medium text-[var(--app-muted)]", compact ? "text-xs" : "text-lg")}>
            Foundation
          </span>
        </span>
      ) : null}
    </div>
  );
}
