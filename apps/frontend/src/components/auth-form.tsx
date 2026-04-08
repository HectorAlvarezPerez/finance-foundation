"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Eye, EyeOff, LockKeyhole, Sparkles } from "lucide-react";

import { useAuth } from "@/components/auth-provider";
import { BrandLogo } from "@/components/brand-logo";
import { apiRequest } from "@/lib/api";
import { API_BASE_URL } from "@/lib/config";
import type { AuthProvidersRead } from "@/lib/types";

type Mode = "login" | "register";

export function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = useMemo(() => searchParams.get("next") ?? "/app", [searchParams]);
  const { clearError, error, login, register, status } = useAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [providers, setProviders] = useState<AuthProvidersRead>({
    local_password_enabled: true,
    entra_external_id_enabled: false,
    google_enabled: false,
  });

  const isLogin = mode === "login";

  useEffect(() => {
    let isMounted = true;

    void (async () => {
      try {
        const response = await apiRequest<AuthProvidersRead>("/auth/providers");
        if (isMounted) {
          setProviders(response);
        }
      } catch {
        if (isMounted) {
          setProviders({
            local_password_enabled: true,
            entra_external_id_enabled: false,
            google_enabled: false,
          });
        }
      }
    })();

    return () => {
      isMounted = false;
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    clearError();

    try {
      if (mode === "login") {
        await login({ email, password });
      } else {
        await register({ email, name, password });
      }
      router.replace(next);
    } catch {
      // Error state is handled in the provider.
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDemoLogin() {
    setIsSubmitting(true);
    clearError();

    try {
      await login({
        email: "demo@finance-foundation.app",
        password: "Demo12345",
      });
      router.replace("/app");
    } catch {
      // Error state is handled in the provider.
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleExternalLogin(path: "/auth/entra/start" | "/auth/google/start") {
    clearError();
    const search = new URLSearchParams({ next });
    window.location.assign(`${API_BASE_URL}${path}?${search.toString()}`);
  }

  return (
    <div className="flex min-h-[100svh] items-center justify-center bg-[var(--background)] px-4 py-6 sm:p-4">
      <div className="w-full max-w-md animate-scaleIn">
        <div className="rounded-2xl border border-[var(--app-border)] bg-[var(--app-panel)] shadow-[var(--app-shadow-elevated)]">
          <div className="space-y-1.5 px-6 pt-8 text-center">
            <div className="mb-5 flex justify-center">
              <BrandLogo />
            </div>
            <h1 className="text-2xl font-bold tracking-tight">{isLogin ? "Bienvenido de nuevo" : "Crea tu cuenta"}</h1>
            <p className="text-sm text-[var(--app-muted)]">
              {isLogin
                ? "Inicia sesión para continuar en tu espacio financiero."
                : "Registra tu usuario para empezar a gestionar tus finanzas."}
            </p>
          </div>

          <form className="space-y-4 px-6 py-6" onSubmit={handleSubmit}>
            {isLogin && (providers.entra_external_id_enabled || providers.google_enabled) ? (
              <div className="grid gap-2">
                {providers.entra_external_id_enabled ? (
                  <button
                    type="button"
                    onClick={() => handleExternalLogin("/auth/entra/start")}
                    disabled={isSubmitting || status === "loading"}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-[var(--app-border)] bg-[var(--app-panel)] px-4 py-2.5 text-sm font-medium transition-all hover:bg-[var(--app-muted-surface)] disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <LockKeyhole className="h-4 w-4 text-[var(--app-accent)]" />
                    Continuar con Microsoft
                  </button>
                ) : null}

                {providers.google_enabled ? (
                  <button
                    type="button"
                    onClick={() => handleExternalLogin("/auth/google/start")}
                    disabled={isSubmitting || status === "loading"}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-[var(--app-border)] bg-[var(--app-panel)] px-4 py-2.5 text-sm font-medium transition-all hover:bg-[var(--app-muted-surface)] disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <GoogleIcon className="h-4 w-4" />
                    Continuar con Google
                  </button>
                ) : null}

                <div className="relative py-1">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t border-[var(--app-border)]" />
                  </div>
                  <div className="relative flex justify-center text-[11px] uppercase tracking-[0.18em]">
                    <span className="bg-[var(--app-panel)] px-2 text-[var(--app-muted)]">o con email</span>
                  </div>
                </div>
              </div>
            ) : null}

            {mode === "register" ? (
              <label className="block space-y-2">
                <span className="block text-sm font-medium">Nombre</span>
                <input
                  required
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  className="w-full rounded-xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-4 py-2.5 outline-none transition-all focus:border-[var(--app-accent)] focus:shadow-[0_0_0_3px_var(--app-accent-soft)]"
                  placeholder="Tu nombre"
                />
              </label>
            ) : null}

            <label className="block space-y-2">
              <span className="block text-sm font-medium">Email</span>
              <input
                required
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="w-full rounded-xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-4 py-2.5 outline-none transition-all focus:border-[var(--app-accent)] focus:shadow-[0_0_0_3px_var(--app-accent-soft)]"
                placeholder="you@example.com"
              />
            </label>

            <label className="block space-y-2">
              <div className="flex items-center justify-between">
                <span className="block text-sm font-medium">Contraseña</span>
                {isLogin ? (
                  <span className="text-xs text-[var(--app-muted)]">Sesión por cookie</span>
                ) : null}
              </div>
              <div className="relative">
                <input
                  required
                  type={showPassword ? "text" : "password"}
                  minLength={8}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="w-full rounded-xl border border-[var(--app-border)] bg-[var(--app-panel-strong)] px-4 py-2.5 pr-10 outline-none transition-all focus:border-[var(--app-accent)] focus:shadow-[0_0_0_3px_var(--app-accent-soft)]"
                  placeholder={isLogin ? "••••••••" : "Mínimo 8 caracteres"}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((current) => !current)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-0.5 text-[var(--app-muted)] transition-colors hover:text-[var(--app-ink)]"
                  aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </label>

            {searchParams.get("error") ? (
              <div className="rounded-xl bg-[var(--app-danger-soft)] px-4 py-3 text-sm text-[var(--app-danger)]">
                {searchParams.get("error")}
              </div>
            ) : null}

            {error ? (
              <div className="rounded-xl bg-[var(--app-danger-soft)] px-4 py-3 text-sm text-[var(--app-danger)]">
                {error}
              </div>
            ) : null}

            <button
              type="submit"
              disabled={isSubmitting || status === "loading"}
              className="inline-flex w-full items-center justify-center rounded-xl bg-[var(--app-accent)] px-4 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? "Enviando..." : isLogin ? "Entrar" : "Crear cuenta"}
            </button>

            <p className="text-center text-sm text-[var(--app-muted)]">
              {isLogin ? "¿No tienes cuenta?" : "¿Ya tienes cuenta?"}{" "}
              <Link
                href={isLogin ? "/register" : "/login"}
                className="font-semibold text-[var(--app-accent)] hover:underline"
              >
                {isLogin ? "Crea una ahora" : "Inicia sesión"}
              </Link>
            </p>
          </form>

          {isLogin ? (
            <div className="px-6 pb-6">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t border-[var(--app-border)]" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-[var(--app-panel)] px-2 text-[var(--app-muted)]">O pruébala</span>
                </div>
              </div>

              <button
                type="button"
                onClick={handleDemoLogin}
                disabled={isSubmitting || status === "loading"}
                className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-[var(--app-border)] bg-[var(--app-panel)] px-4 py-2.5 text-sm font-medium transition-all hover:bg-[var(--app-muted-surface)] disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Sparkles className={`h-4 w-4 ${isSubmitting ? "animate-spin" : "text-amber-500"}`} />
                {isSubmitting ? "Entrando..." : "Probar modo demo"}
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function GoogleIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 18 18"
      aria-hidden="true"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M17.64 9.2045c0-.6382-.0573-1.2518-.1636-1.8409H9v3.4818h4.8436c-.2086 1.125-.8427 2.0782-1.7959 2.7164v2.2582h2.9091c1.7023-1.5673 2.6832-3.8773 2.6832-6.6155Z"
        fill="#4285F4"
      />
      <path
        d="M9 18c2.43 0 4.4673-.8059 5.9568-2.1791l-2.9091-2.2582c-.8059.54-1.8368.8591-3.0477.8591-2.3441 0-4.3282-1.5823-5.0364-3.7091H.9568v2.3328A9 9 0 0 0 9 18Z"
        fill="#34A853"
      />
      <path
        d="M3.9636 10.7127A5.4094 5.4094 0 0 1 3.6818 9c0-.5959.1036-1.1727.2818-1.7127V4.9545H.9568A9 9 0 0 0 0 9c0 1.4523.3482 2.8277.9568 4.0455l3.0068-2.3328Z"
        fill="#FBBC05"
      />
      <path
        d="M9 3.5795c1.3214 0 2.5077.4541 3.4418 1.345L15.0218 2.344C13.5273.9527 11.43 0 9 0A9 9 0 0 0 .9568 4.9545l3.0068 2.3328C4.6718 5.1609 6.6559 3.5795 9 3.5795Z"
        fill="#EA4335"
      />
    </svg>
  );
}
