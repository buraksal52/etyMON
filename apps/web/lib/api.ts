const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function readDetail(body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) =>
        typeof (item as { msg?: unknown })?.msg === "string"
          ? (item as { msg: string }).msg
          : "",
      )
      .filter(Boolean)
      .join(", ");
  }
  return "";
}

export async function apiRequest<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const isMultipart =
    typeof FormData !== "undefined" && options?.body instanceof FormData;
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      credentials: "include",
      headers: isMultipart
        ? options?.headers
        : { "Content-Type": "application/json", ...options?.headers },
    });
  } catch {
    throw new ApiError("Network error", 0);
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(readDetail(body) || "Request failed", response.status);
  }

  return response.json() as Promise<T>;
}
