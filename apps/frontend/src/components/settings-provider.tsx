"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type PropsWithChildren,
  useCallback,
} from "react";
import { apiRequest } from "@/lib/api";
import type { Settings } from "@/lib/types";
import { useAuth } from "./auth-provider";

type SettingsContextValue = {
  settings: Settings | null;
  refreshSettings: () => Promise<void>;
};

const SettingsContext = createContext<SettingsContextValue | null>(null);

export function SettingsProvider({ children }: PropsWithChildren) {
  const { status } = useAuth();
  const [settings, setSettings] = useState<Settings | null>(null);

  const refreshSettings = useCallback(async () => {
    if (status === "authenticated") {
      try {
        const data = await apiRequest<Settings>("/settings");
        setSettings(data);
      } catch (err) {
        setSettings(null);
      }
    } else {
      setSettings(null);
    }
  }, [status]);

  useEffect(() => {
    void refreshSettings();
  }, [refreshSettings]);

  return (
    <SettingsContext.Provider value={{ settings, refreshSettings }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error("useSettings must be used within a SettingsProvider");
  }
  return context;
}
