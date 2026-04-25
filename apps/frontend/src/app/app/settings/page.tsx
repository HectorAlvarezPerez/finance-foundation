"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, CheckCircle2, Clock3, Globe2, MoonStar, Wallet } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { PageHeader } from "@/components/page-header";
import { useAuth } from "@/components/auth-provider";
import { useTheme } from "@/components/theme-provider";
import { apiRequest } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import type { Settings } from "@/lib/types";

type SettingsForm = {
  default_currency: string;
  locale: string;
  theme: "light" | "dark" | "system";
  auto_categorization_enabled: boolean;
};

type SettingsResponse = Settings & {
  auto_categorization_enabled?: boolean;
};

type SaveState = "idle" | "saving" | "saved" | "error";

const DEFAULT_FORM: SettingsForm = {
  default_currency: "EUR",
  locale: "es-ES",
  theme: "system",
  auto_categorization_enabled: true,
};

const LOCALE_OPTIONS = [
  { value: "es-ES", label: "Español (España)" },
  { value: "en-US", label: "English (US)" },
];

export default function SettingsPage() {
  const router = useRouter();
  const { deleteAccount, user } = useAuth();
  const { setTheme } = useTheme();
  const [error, setError] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [form, setForm] = useState<SettingsForm>(DEFAULT_FORM);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const hasLoadedRef = useRef(false);
  const lastSavedSnapshotRef = useRef(JSON.stringify(DEFAULT_FORM));

  useEffect(() => {
    async function load() {
      try {
        const response = await apiRequest<SettingsResponse>("/settings");
        const nextForm: SettingsForm = {
          default_currency: response.default_currency,
          locale: response.locale,
          theme: response.theme as SettingsForm["theme"],
          auto_categorization_enabled: response.auto_categorization_enabled ?? true,
        };

        setForm(nextForm);
        setTheme(nextForm.theme);
        lastSavedSnapshotRef.current = JSON.stringify(nextForm);
        setSaveState("idle");
      } catch (requestError) {
        if (requestError instanceof Error && requestError.message === "Settings not found") {
          return;
        }

        setError(requestError instanceof Error ? requestError.message : "No se pudo cargar la configuración");
      } finally {
        hasLoadedRef.current = true;
      }
    }

    void load();
  }, [setTheme]);

  useEffect(() => {
    if (!hasLoadedRef.current) return;

    const snapshot = JSON.stringify(form);
    if (snapshot === lastSavedSnapshotRef.current) return;

    if (form.default_currency.trim().length !== 3) {
      setSaveState("idle");
      return;
    }

    const localeLength = form.locale.trim().length;
    if (localeLength < 2 || localeLength > 16) {
      setSaveState("idle");
      return;
    }

    setSaveState("saving");
    setError(null);

    const timeoutId = window.setTimeout(async () => {
      try {
        const response = await apiRequest<SettingsResponse>("/settings", {
          method: "PUT",
          body: JSON.stringify(form),
        });
        const savedForm: SettingsForm = {
          default_currency: response.default_currency,
          locale: response.locale,
          theme: response.theme as SettingsForm["theme"],
          auto_categorization_enabled: response.auto_categorization_enabled ?? form.auto_categorization_enabled,
        };

        lastSavedSnapshotRef.current = JSON.stringify(savedForm);
        setTheme(savedForm.theme);
        setSaveState("saved");
      } catch (requestError) {
        setSaveState("error");
        setError(requestError instanceof Error ? requestError.message : "No se pudo guardar la configuración");
      }
    }, 350);

    return () => window.clearTimeout(timeoutId);
  }, [form, setTheme]);

  const saveLabel = useMemo(() => {
    if (saveState === "saving") return "Guardando...";
    if (saveState === "saved") return "Guardado";
    if (saveState === "error") return "Error al guardar";
    return "Guardado automático";
  }, [saveState]);

  const localeExampleDate = useMemo(() => {
    try {
      return new Intl.DateTimeFormat(form.locale, { dateStyle: "medium" }).format(new Date("2026-03-31"));
    } catch {
      return "Formato no válido";
    }
  }, [form.locale]);

  const localeExampleAmount = useMemo(() => {
    try {
      return new Intl.NumberFormat(form.locale, {
        style: "currency",
        currency: form.default_currency || "EUR",
      }).format(1520.4);
    } catch {
      return formatCurrency(1520.4, form.default_currency || "EUR");
    }
  }, [form.default_currency, form.locale]);

  async function handleDeleteAccount() {
    try {
      await deleteAccount();
      router.replace("/login");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No se pudo eliminar la cuenta");
    } finally {
      setConfirmDelete(false);
    }
  }

  const inputClasses = "w-full rounded-xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-4 py-3 outline-none transition-all focus:border-[var(--app-accent)] focus:shadow-[0_0_0_3px_var(--app-accent-soft)]";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Configuración"
        title="Preferencias"
        description="Ajusta el formato, la apariencia y la cuenta. Los cambios se guardan automáticamente."
      />

      <ConfirmDialog
        open={confirmDelete}
        title="Eliminar cuenta"
        description="Se eliminarán tu usuario, cuentas, categorías, transacciones, presupuestos y configuración. Esta acción no se puede deshacer."
        confirmLabel="Eliminar cuenta"
        onConfirm={() => void handleDeleteAccount()}
        onCancel={() => setConfirmDelete(false)}
      />

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-6">
          <Card className="animate-slideUp">
            <CardHeader className="flex flex-row items-start justify-between gap-4 border-b border-[var(--app-border)]">
              <div>
                <CardTitle>General</CardTitle>
                <CardDescription>Moneda por defecto, formato regional y estado de guardado.</CardDescription>
              </div>
              <SaveIndicator label={saveLabel} state={saveState} />
            </CardHeader>
            <CardContent className="space-y-6 pt-6">
              <label className="grid gap-2">
                <span className="text-sm font-medium">Moneda principal (Global)</span>
                <select
                  required
                  value={form.default_currency}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      default_currency: event.target.value.toUpperCase(),
                    }))
                  }
                  className={inputClasses}
                >
                  <option value="EUR">Euros (EUR)</option>
                  <option value="USD">Dólares Estadounidenses (USD)</option>
                </select>
                <span className="text-xs text-[var(--app-muted)]">
                  Esta será la única moneda utilizada en todas las cuentas y transacciones.
                </span>
              </label>

              <label className="grid gap-2">
                <span className="text-sm font-medium">Locale</span>
                <select
                  value={form.locale}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      locale: event.target.value,
                    }))
                  }
                  className={inputClasses}
                >
                  {LOCALE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <span className="text-xs text-[var(--app-muted)]">
                  El locale define cómo se muestran fechas y números. Ejemplo: {localeExampleDate} y {localeExampleAmount}.
                </span>
              </label>

              <label className="flex items-start gap-3 rounded-2xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-4 py-4">
                <input
                  type="checkbox"
                  checked={form.auto_categorization_enabled}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      auto_categorization_enabled: event.target.checked,
                    }))
                  }
                  className="mt-1 h-4 w-4 rounded border border-[var(--app-border)] text-[var(--app-accent)]"
                />
                <span className="grid gap-1">
                  <span className="text-sm font-medium">Autocategorización</span>
                  <span className="text-sm text-[var(--app-muted)]">
                    Permite que la app sugiera categorías automáticamente durante la importación de transacciones.
                  </span>
                </span>
              </label>
            </CardContent>
          </Card>

          <Card className="animate-slideUp stagger-2">
            <CardHeader>
              <CardTitle>Apariencia</CardTitle>
              <CardDescription>Elige cómo quieres ver la app en este dispositivo.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-3">
                {(["system", "light", "dark"] as const).map((themeOption) => {
                  const isSelected = form.theme === themeOption;
                  const labels = { system: "Sistema", light: "Claro", dark: "Oscuro" };
                  return (
                    <button
                      key={themeOption}
                      type="button"
                      onClick={() => {
                        setForm((current) => ({ ...current, theme: themeOption }));
                        setTheme(themeOption);
                      }}
                      className={`rounded-2xl border px-4 py-4 text-sm font-medium transition-all ${
                        isSelected
                          ? "border-[var(--app-accent)] bg-[var(--app-accent-soft)] text-[var(--app-accent)] shadow-[var(--app-shadow)]"
                          : "border-[var(--app-border)] bg-[var(--app-panel-strong)] text-[var(--app-muted)] hover:border-[var(--app-muted)]"
                      }`}
                    >
                      <span className="block">{labels[themeOption]}</span>
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {error ? (
            <div className="animate-fadeIn rounded-xl bg-[var(--app-danger-soft)] px-4 py-3 text-sm text-[var(--app-danger)]">
              {error}
            </div>
          ) : null}
        </div>

        <div className="space-y-6">
          <Card className="animate-slideUp stagger-3">
            <CardHeader>
              <CardTitle>Vista previa</CardTitle>
              <CardDescription>Así se aplican tus preferencias al formato diario.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <PreviewRow icon={<Wallet className="h-4 w-4" />} label="Importe" value={localeExampleAmount} />
              <PreviewRow icon={<Globe2 className="h-4 w-4" />} label="Fecha" value={localeExampleDate} />
              <PreviewRow icon={<CheckCircle2 className="h-4 w-4" />} label="Autocategorización" value={form.auto_categorization_enabled ? "Activada" : "Desactivada"} />
              <PreviewRow icon={<MoonStar className="h-4 w-4" />} label="Tema" value={form.theme === "system" ? "Seguir sistema" : form.theme === "light" ? "Modo claro" : "Modo oscuro"} />
            </CardContent>
          </Card>

          <Card className="animate-slideUp stagger-4">
            <CardHeader>
              <CardTitle>Cuenta</CardTitle>
              <CardDescription>Información básica del usuario actual.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <InfoRow label="Nombre" value={user?.name ?? "Sin nombre"} />
              <InfoRow label="Email" value={user?.email ?? "Sin email"} />
            </CardContent>
          </Card>

          <Card className="animate-slideUp stagger-5 border-[color-mix(in_srgb,var(--app-danger)_18%,var(--app-border))]">
            <CardHeader>
              <CardTitle>Zona de peligro</CardTitle>
              <CardDescription>Acciones permanentes que afectan a todos tus datos.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-2xl border border-[color-mix(in_srgb,var(--app-danger)_18%,transparent)] bg-[color-mix(in_srgb,var(--app-danger-soft)_70%,transparent)] px-4 py-3">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-[var(--app-danger)]" />
                  <div className="space-y-1">
                    <p className="text-sm font-medium">Eliminar cuenta y datos</p>
                    <p className="text-sm text-[var(--app-muted)]">
                      Borra usuario, cuentas, categorías, transacciones, presupuestos y configuración.
                    </p>
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setConfirmDelete(true)}
                className="inline-flex items-center justify-center rounded-xl bg-[var(--app-danger)] px-4 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110"
              >
                Eliminar cuenta
              </button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function PreviewRow({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-2xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-4 py-3">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--app-muted-surface)] text-[var(--app-muted)]">
          {icon}
        </div>
        <span className="text-sm font-medium">{label}</span>
      </div>
      <span className="text-sm text-[var(--app-muted)]">{value}</span>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-2xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-4 py-3">
      <span className="text-sm text-[var(--app-muted)]">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  );
}

function SaveIndicator({
  label,
  state,
}: {
  label: string;
  state: SaveState;
}) {
  const className =
    state === "error"
      ? "text-[var(--app-danger)]"
      : state === "saved"
        ? "text-[var(--app-success)]"
        : "text-[var(--app-muted)]";

  return (
    <div className={`inline-flex items-center gap-2 text-sm transition-colors ${className}`}>
      {state === "saved" ? <CheckCircle2 className="h-4 w-4" /> : <Clock3 className="h-4 w-4" />}
      <span>{label}</span>
    </div>
  );
}
