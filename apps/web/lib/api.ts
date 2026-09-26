const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function apiRequest<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const isMultipart =
    typeof FormData !== "undefined" && options?.body instanceof FormData;
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: isMultipart
      ? options?.headers
      : { "Content-Type": "application/json", ...options?.headers },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Request failed");
  }

  return response.json() as Promise<T>;
}
