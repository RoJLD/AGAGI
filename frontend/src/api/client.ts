export const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8001";

/** Token API optionnel (opt-in) : si défini, envoyé en `Authorization: Bearer` sur chaque appel.
 *  Absent → aucun header (le backend n'exige rien tant que AGAGI_API_TOKEN n'est pas posé côté serveur). */
const API_TOKEN = import.meta.env.VITE_API_TOKEN;

/** Erreur réseau/HTTP typée (status, endpoint, message) — remplace les `string` ad hoc. */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly endpoint: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type FetchInit = RequestInit & { timeoutMs?: number };

/** Wrapper unique des appels REST : URL, timeout, vérification ok, ApiError typée, parsing JSON. */
export async function apiFetch<T>(path: string, init: FetchInit = {}): Promise<T> {
  const { timeoutMs = 10_000, signal, ...rest } = init;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const headers = new Headers(rest.headers);
  if (API_TOKEN) headers.set("Authorization", `Bearer ${API_TOKEN}`);
  try {
    const response = await fetch(`${BASE_URL}${path}`, { ...rest, headers, signal: signal ?? controller.signal });
    if (!response.ok) {
      const detail = await response.text().catch(() => "");
      throw new ApiError(response.status, path, detail || response.statusText);
    }
    return (await response.json()) as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(0, path, `Timeout après ${timeoutMs} ms`);
    }
    throw new ApiError(0, path, err instanceof Error ? err.message : String(err));
  } finally {
    clearTimeout(timer);
  }
}

/** Construit l'URL WebSocket (ws/wss) à partir de la base HTTP. */
export function wsUrl(path: string): string {
  const proto = typeof window !== "undefined" && window.location.protocol === "https:" ? "wss" : "ws";
  return `${BASE_URL.replace(/^https?/, proto)}${path}`;
}
