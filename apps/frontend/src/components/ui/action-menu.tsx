import { useEffect, useRef, useState } from "react";
import { MoreVertical } from "lucide-react";

export type ActionMenuItem = {
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
  danger?: boolean;
};

export function ActionMenu({
  label,
  actions,
  ariaLabel,
}: {
  label: string;
  actions: ActionMenuItem[];
  ariaLabel?: string;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    function handleClick(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }

    document.addEventListener("click", handleClick);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("click", handleClick);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  function runAndClose(action: () => void) {
    action();
    setIsOpen(false);
  }

  return (
    <div ref={menuRef} className="relative z-30">
      <button
        type="button"
        onClick={() => setIsOpen((current) => !current)}
        className="rounded-lg p-1.5 text-[var(--app-muted)] transition-all hover:bg-[var(--app-muted-surface)]"
        aria-label={ariaLabel || `Acciones de ${label}`}
      >
        <MoreVertical className="h-4 w-4" />
      </button>

      {isOpen ? (
        <div className="animate-slideDown absolute right-0 z-[80] mt-1 min-w-40 rounded-xl border border-[var(--app-border)] bg-[var(--app-glass)] p-1 shadow-[var(--app-shadow-elevated)] backdrop-blur-xl">
          {actions.map((action, index) => (
            <button
              key={index}
              type="button"
              onClick={() => runAndClose(action.onClick)}
              className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-all ${
                action.danger
                  ? "text-[var(--app-danger)] hover:bg-[var(--app-danger-soft)]"
                  : "hover:bg-[var(--app-muted-surface)]"
              }`}
            >
              {action.icon} {action.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
