"use client";

import {
  createContext,
  PropsWithChildren,
  useContext,
  useEffect,
  useEffectEvent,
  useState,
  useCallback,
} from "react";

import { apiRequest, ApiError } from "@/lib/api";
import type { AuthLoginRequest, AuthRegisterRequest, AuthStatus, User } from "@/lib/types";

type AuthContextValue = {
  status: AuthStatus;
  user: User | null;
  error: string | null;
  login: (payload: AuthLoginRequest) => Promise<void>;
  register: (payload: AuthRegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  deleteAccount: () => Promise<void>;
  refreshSession: () => Promise<void>;
  clearError: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshSession = useCallback(async () => {
    try {
      setError(null);
      const sessionUser = await apiRequest<User>("/auth/me");
      setUser(sessionUser);
      setStatus("authenticated");
    } catch (requestError) {
      if (
        requestError instanceof ApiError &&
        (requestError.status === 401 || requestError.status === 404)
      ) {
        setUser(null);
        setError(null);
        setStatus("unauthenticated");
        return;
      }

      setError(requestError instanceof ApiError && requestError.isFatal ? null : requestError instanceof Error ? requestError.message : "Session check failed");
      setStatus("unauthenticated");
    }
  }, []);

  const loadInitialSession = useEffectEvent(async () => {
    await refreshSession();
  });

  useEffect(() => {
    void loadInitialSession();
  }, []);

  async function login(payload: AuthLoginRequest) {
    try {
      setError(null);
      await apiRequest<User>("/auth/login", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      await refreshSession();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Usuario o contraseña incorrecto.");
      } else if (err instanceof ApiError && err.status === 404) {
        setError("Usuario o contraseña incorrecto.");
      } else {
        setError(err instanceof Error ? err.message : "Error al iniciar sesión");
      }
      throw err;
    }
  }

  async function register(payload: AuthRegisterRequest) {
    try {
      setError(null);
      await apiRequest<User>("/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      await refreshSession();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al registrarse");
      throw err;
    }
  }

  async function logout() {
    setError(null);
    await apiRequest<void>("/auth/logout", {
      method: "POST",
      skipJson: true,
    });
    setUser(null);
    setStatus("unauthenticated");
  }

  async function deleteAccount() {
    setError(null);
    await apiRequest<void>("/auth/me", {
      method: "DELETE",
      skipJson: true,
    });
    setUser(null);
    setStatus("unauthenticated");
  }

  function clearError() {
    setError(null);
  }

  const value: AuthContextValue = {
    status,
    user,
    error,
    login,
    register,
    logout,
    deleteAccount,
    refreshSession,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (context === null) {
    throw new Error("useAuth must be used within an AuthProvider");
  }

  return context;
}
