import { API_BASE_URL } from "@/lib/config";

type RequestOptions = RequestInit & {
  skipJson?: boolean;
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { headers, skipJson, ...rest } = options;
  const requestHeaders = new Headers(headers);
  if (!(rest.body instanceof FormData) && !requestHeaders.has("Content-Type")) {
    requestHeaders.set("Content-Type", "application/json");
  }
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...rest,
      cache: rest.cache ?? "no-store",
      credentials: "include",
      headers: requestHeaders,
    });
  } catch (error) {
    throw new ApiError(getNetworkErrorMessage(error), 0);
  }

  if (!response.ok) {
    const payload = (await tryReadJson(response)) as { detail?: unknown } | null;
    throw new ApiError(getErrorMessage(payload?.detail, response.status), response.status);
  }

  if (skipJson || response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

async function tryReadJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function getErrorMessage(detail: unknown, status: number): string {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const firstItem = detail[0];
    if (
      firstItem &&
      typeof firstItem === "object" &&
      "msg" in firstItem &&
      typeof firstItem.msg === "string"
    ) {
      return firstItem.msg;
    }
  }

  return `Request failed with status ${status}`;
}

function getNetworkErrorMessage(error: unknown): string {
  if (error instanceof DOMException && error.name === "AbortError") {
    return "La petición tardó demasiado y fue cancelada.";
  }

  return `No se pudo conectar con la API en ${API_BASE_URL}. Comprueba que el backend esté levantado y accesible desde el navegador.`;
}
