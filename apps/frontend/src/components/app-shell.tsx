"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  CreditCard,
  LayoutDashboard,
  LineChart,
  LogOut,
  Menu,
  MoonStar,
  Sun,
  PiggyBank,
  Settings,
  Tag,
  Wallet,
} from "lucide-react";

import { BrandLogo } from "@/components/brand-logo";
import { useTheme } from "@/components/theme-provider";

import { useAuth } from "@/components/auth-provider";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/app", label: "Resumen", icon: LayoutDashboard },
  { href: "/app/transactions", label: "Transacciones", icon: CreditCard },
  { href: "/app/accounts", label: "Cuentas", icon: Wallet },
  { href: "/app/categories", label: "Categorías", icon: Tag },
  { href: "/app/insights", label: "Análisis", icon: LineChart },
  { href: "/app/budgets", label: "Presupuestos", icon: PiggyBank },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { logout, user } = useAuth();
  const [isMoreOpen, setIsMoreOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);
  const { theme, setTheme } = useTheme();

  function toggleTheme() {
    setTheme(theme === "dark" ? "light" : "dark");
  }

  async function handleLogout() {
    setIsMoreOpen(false);
    await logout();
    router.replace("/login");
  }

  // Close "More" menu on outside click
  useEffect(() => {
    if (!isMoreOpen) return;

    function handleClick(event: MouseEvent) {
      if (moreRef.current && !moreRef.current.contains(event.target as Node)) {
        setIsMoreOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsMoreOpen(false);
      }
    }

    document.addEventListener("click", handleClick);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("click", handleClick);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isMoreOpen]);

  const mobilePrimaryItems = [
    navItems[0],
    navItems[1],
    navItems[4],
    navItems[2],
  ];

  const mobileMoreItems = [navItems[3], navItems[5]];
  const isMoreActive = mobileMoreItems.some((item) => pathname.startsWith(item.href)) || pathname.startsWith("/app/settings");

  return (
    <div className="app-shell-grid bg-[var(--background)]">
      {/* ─── Top navigation bar ─── */}
      <header className="sticky top-0 z-40 border-b border-[var(--app-border)] bg-[var(--app-glass)] backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-[var(--app-content-max-width)] flex-col gap-4 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex w-full items-center justify-between gap-4 sm:w-auto sm:justify-start sm:gap-6">
            <Link href="/app" className="flex min-w-0 items-center">
              <BrandLogo compact className="min-w-0" />
            </Link>

            <nav className="hidden items-center gap-0.5 md:flex">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive =
                  item.href === "/app" ? pathname === item.href : pathname.startsWith(item.href);

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-all",
                      isActive
                        ? "bg-[var(--app-accent)] text-white shadow-sm"
                        : "text-[var(--app-muted)] hover:bg-[var(--app-muted-surface)] hover:text-[var(--app-ink)]",
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>
          </div>

          <div className="hidden w-full items-center justify-between gap-3 sm:flex sm:w-auto sm:justify-end">
            <div className="min-w-0 text-left sm:text-right">
              <p className="text-sm font-medium">{user?.name}</p>
              <p className="truncate text-xs text-[var(--app-muted)]">{user?.email}</p>
            </div>
            <div className="flex shrink-0 items-center gap-1.5">
              <Link
                href="/app/settings"
                className={cn(
                  "inline-flex h-9 w-9 items-center justify-center rounded-xl transition-all hover:bg-[var(--app-muted-surface)]",
                  pathname.startsWith("/app/settings") && "bg-[var(--app-accent-soft)] text-[var(--app-accent)]",
                )}
                title="Preferencias"
              >
                <Settings className="h-[18px] w-[18px]" />
              </Link>
              <button
                type="button"
                onClick={toggleTheme}
                className="inline-flex h-9 w-9 items-center justify-center rounded-xl text-[var(--app-muted)] transition-all hover:bg-[var(--app-muted-surface)] hover:text-[var(--app-ink)]"
                title="Cambiar tema"
                aria-label="Cambiar tema"
              >
                {theme === "dark" ? <Sun className="h-[18px] w-[18px]" /> : <MoonStar className="h-[18px] w-[18px]" />}
              </button>
              <button
                type="button"
                onClick={handleLogout}
                className="inline-flex h-9 w-9 items-center justify-center rounded-xl text-[var(--app-muted)] transition-all hover:bg-[var(--app-danger-soft)] hover:text-[var(--app-danger)]"
                title="Cerrar sesión"
                aria-label="Cerrar sesión"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* ─── Main content ─── */}
      <main className="page-container">{children}</main>

      {/* ─── Mobile bottom navigation ─── */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-[var(--app-border)] bg-[var(--app-glass)] shadow-[0_-4px_20px_-12px_rgba(0,0,0,0.15)] backdrop-blur-xl md:hidden [padding-bottom:env(safe-area-inset-bottom)]">
        <div className="mx-auto grid w-full max-w-[var(--app-content-max-width)] grid-cols-5 items-center gap-1 px-2 py-1.5">
          {mobilePrimaryItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.href === "/app" ? pathname === item.href : pathname.startsWith(item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setIsMoreOpen(false)}
                className={cn(
                  "flex flex-col items-center justify-center gap-0.5 rounded-xl px-1 py-2 text-[10px] font-medium transition-all",
                  isActive
                    ? "text-[var(--app-accent)]"
                    : "text-[var(--app-muted)] hover:text-[var(--app-ink)]",
                )}
              >
                <Icon className={cn("h-5 w-5", isActive && "scale-110")} />
                <span>{item.label}</span>
              </Link>
            );
          })}

          <div className="relative" ref={moreRef}>
            <button
              type="button"
              onClick={() => setIsMoreOpen((current) => !current)}
              className={cn(
                "flex w-full flex-col items-center justify-center gap-0.5 rounded-xl px-1 py-2 text-[10px] font-medium transition-all",
                isMoreActive || isMoreOpen
                  ? "text-[var(--app-accent)]"
                  : "text-[var(--app-muted)] hover:text-[var(--app-ink)]",
              )}
              aria-expanded={isMoreOpen}
              aria-label="Más opciones"
            >
              <Menu className="h-5 w-5" />
              <span>Más</span>
            </button>

            {isMoreOpen ? (
              <div className="animate-slideUp absolute bottom-14 right-0 w-52 rounded-2xl border border-[var(--app-border)] bg-[var(--app-glass)] p-2 shadow-[var(--app-shadow-elevated)] backdrop-blur-xl">
                {mobileMoreItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname.startsWith(item.href);

                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setIsMoreOpen(false)}
                      className={cn(
                        "flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm transition-all",
                        isActive
                          ? "bg-[var(--app-accent-soft)] text-[var(--app-accent)]"
                          : "text-[var(--app-ink)] hover:bg-[var(--app-muted-surface)]",
                      )}
                    >
                      <Icon className="h-4 w-4" />
                      <span>{item.label}</span>
                    </Link>
                  );
                })}

                <Link
                  href="/app/settings"
                  onClick={() => setIsMoreOpen(false)}
                  className={cn(
                    "mt-1 flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm transition-all",
                    pathname.startsWith("/app/settings")
                      ? "bg-[var(--app-accent-soft)] text-[var(--app-accent)]"
                      : "text-[var(--app-ink)] hover:bg-[var(--app-muted-surface)]",
                  )}
                >
                  <Settings className="h-4 w-4" />
                  <span>Preferencias</span>
                </Link>

                <div className="mx-2 my-1.5 border-t border-[var(--app-border)]" />

                <button
                  type="button"
                  onClick={toggleTheme}
                  className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm transition-all text-[var(--app-ink)] hover:bg-[var(--app-muted-surface)]"
                >
                  {theme === "dark" ? <Sun className="h-4 w-4" /> : <MoonStar className="h-4 w-4" />}
                  <span>{theme === "dark" ? "Modo claro" : "Modo oscuro"}</span>
                </button>

                <div className="mx-2 my-1.5 border-t border-[var(--app-border)]" />

                <button
                  type="button"
                  onClick={handleLogout}
                  className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm text-[var(--app-danger)] transition-all hover:bg-[var(--app-danger-soft)]"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Cerrar sesión</span>
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </nav>
    </div>
  );
}
