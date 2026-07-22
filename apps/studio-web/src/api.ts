function resolveApiBase(): string {
  const fromEnv = import.meta.env.VITE_SPWS_API as string | undefined;
  if (fromEnv && fromEnv.trim()) return fromEnv.trim().replace(/\/$/, "");
  try {
    const stored = localStorage.getItem("SPWS_API");
    if (stored && stored.trim()) return stored.trim().replace(/\/$/, "");
  } catch {
    /* ignore */
  }
  return "http://127.0.0.1:8000";
}

export function getApiBase(): string {
  return resolveApiBase();
}

export async function apiPost<T = unknown>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${getApiBase()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || res.statusText);
  }
  return res.json() as Promise<T>;
}

export async function apiGet<T = unknown>(path: string): Promise<T> {
  const res = await fetch(`${getApiBase()}${path}`);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || res.statusText);
  }
  return res.json() as Promise<T>;
}
