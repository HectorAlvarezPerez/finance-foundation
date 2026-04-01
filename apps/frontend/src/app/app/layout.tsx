import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";

export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth>
      <AppShell>{children}</AppShell>
    </RequireAuth>
  );
}
