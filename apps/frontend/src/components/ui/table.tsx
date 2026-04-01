import { cn } from "@/lib/utils";

export function Table({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className="relative w-full overflow-auto">
      <table className={cn("w-full caption-bottom text-sm", className)}>{children}</table>
    </div>
  );
}

export function TableHeader({ children }: { children: React.ReactNode }) {
  return <thead className="[&_tr]:border-b">{children}</thead>;
}

export function TableBody({ children }: { children: React.ReactNode }) {
  return <tbody className="[&_tr:last-child]:border-0">{children}</tbody>;
}

export function TableRow({ children, className }: { children: React.ReactNode; className?: string }) {
  return <tr className={cn("border-b transition-colors hover:bg-[var(--app-muted-surface)]", className)}>{children}</tr>;
}

export function TableHead({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <th
      className={cn(
        "h-10 px-4 text-left align-middle text-xs font-medium uppercase tracking-[0.16em] text-[var(--app-muted)]",
        className,
      )}
    >
      {children}
    </th>
  );
}

export function TableCell({ children, className }: { children: React.ReactNode; className?: string }) {
  return <td className={cn("p-4 align-middle", className)}>{children}</td>;
}
