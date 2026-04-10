export const FATAL_APP_ERROR_EVENT = "finance-foundation:fatal-app-error";

export type FatalAppErrorDetail = {
  requestId?: string | null;
};

export function notifyFatalAppError(detail: FatalAppErrorDetail = {}): void {
  if (typeof window === "undefined") {
    return;
  }

  window.dispatchEvent(new CustomEvent<FatalAppErrorDetail>(FATAL_APP_ERROR_EVENT, { detail }));
}
