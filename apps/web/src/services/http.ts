const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");

export class ApiError extends Error {
  readonly status: number;
  readonly path: string;
  readonly detail: string;

  constructor(status: number, path: string, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.path = path;
    this.detail = detail;
  }
}

async function readErrorDetail(response: Response): Promise<string> {
  const contentType = response.headers.get("Content-Type") ?? "";
  if (contentType.includes("application/json")) {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    if (payload.detail !== undefined) {
      return JSON.stringify(payload.detail);
    }
    return JSON.stringify(payload);
  }
  const text = await response.text();
  return text || response.statusText || "API request failed";
}

function buildHeaders(input?: HeadersInit): Record<string, string> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (!input) {
    return headers;
  }
  new Headers(input).forEach((value, key) => {
    if (key.toLowerCase() === "accept") {
      headers.Accept = value;
    } else {
      headers[key] = value;
    }
  });
  return headers;
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: buildHeaders(init.headers),
  });

  if (!response.ok) {
    throw new ApiError(response.status, path, await readErrorDetail(response));
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
