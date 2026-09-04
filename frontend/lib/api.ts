export type ApiError = { status: number; detail: string };

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.split("; ").find((row) => row.startsWith(name + "="));
  return match ? decodeURIComponent(match.split("=").slice(1).join("=")) : null;
}

export async function api<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const csrf = getCookie("mailgate_csrf");
  if (csrf) headers.set("X-CSRF-Token", csrf);
  const response = await fetch(path, {
    ...options,
    headers,
    credentials: "include",
  });
  const text = await response.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text };
  }
  if (!response.ok) {
    const detail =
      typeof data === "object" && data && "detail" in data
        ? String((data as { detail: unknown }).detail)
        : response.statusText;
    if (response.status === 401 && typeof window !== "undefined" && !path.startsWith("/api/auth")) {
      window.location.href = "/login/";
    }
    const error: ApiError = { status: response.status, detail };
    throw error;
  }
  return data as T;
}

export function isApiError(value: unknown): value is ApiError {
  return Boolean(value && typeof value === "object" && "status" in value && "detail" in value);
}
