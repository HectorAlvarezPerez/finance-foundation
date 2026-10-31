import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";
import { SettingsProvider } from "@/components/settings-provider";

export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth>
      <SettingsProvider>
        <AppShell>{children}</AppShell>
      </SettingsProvider>
    </RequireAuth>
  );
}
