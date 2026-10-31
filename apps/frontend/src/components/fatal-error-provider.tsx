"use client";

import { PropsWithChildren, useEffect, useState } from "react";

import { ErrorScreen } from "@/components/error-screen";
import { FATAL_APP_ERROR_EVENT, type FatalAppErrorDetail } from "@/lib/fatal-error";

export function FatalErrorProvider({ children }: PropsWithChildren) {
  const [fatalError, setFatalError] = useState<FatalAppErrorDetail | null>(null);

  useEffect(() => {
    function handleFatalError(event: Event) {
      const customEvent = event as CustomEvent<FatalAppErrorDetail>;
      setFatalError(customEvent.detail ?? {});
    }

    window.addEventListener(FATAL_APP_ERROR_EVENT, handleFatalError as EventListener);
    return () => {
      window.removeEventListener(FATAL_APP_ERROR_EVENT, handleFatalError as EventListener);
    };
  }, []);

  if (fatalError) {
    return <ErrorScreen />;
  }

  return <>{children}</>;
}
