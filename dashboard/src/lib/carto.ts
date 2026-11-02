/**
 * CARTO platform config for the Florida demand map.
 * API base locked from Workspace → Developers (user-provided).
 */
export const CARTO_API_BASE_DEFAULT = "https://gcp-us-east1.api.carto.com";

export const CARTO_BASEMAP =
  "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";

export type CartoRuntimeConfig = {
  apiBaseUrl: string;
  connectionName: string;
  /** True when a server-side access token is present. */
  configured: boolean;
  regionLabel: string;
};

export function getCartoApiBase(): string {
  const raw =
    process.env.CARTO_API_BASE ||
    process.env.NEXT_PUBLIC_CARTO_API_BASE ||
    CARTO_API_BASE_DEFAULT;
  return raw.replace(/\/$/, "");
}

export function getCartoAccessToken(): string | undefined {
  const t =
    process.env.CARTO_ACCESS_TOKEN ||
    process.env.NEXT_PUBLIC_CARTO_ACCESS_TOKEN ||
    process.env.CARTO_API_KEY;
  return t?.trim() || undefined;
}

export function getCartoConnectionName(): string {
  return (
    process.env.CARTO_CONNECTION_NAME ||
    process.env.NEXT_PUBLIC_CARTO_CONNECTION_NAME ||
    "carto_dw"
  );
}

export function getCartoRuntimeConfig(): CartoRuntimeConfig {
  const apiBaseUrl = getCartoApiBase();
  let regionLabel = "carto";
  try {
    regionLabel = new URL(apiBaseUrl).hostname.split(".")[0] || "carto";
  } catch {
    /* keep default */
  }
  return {
    apiBaseUrl,
    connectionName: getCartoConnectionName(),
    configured: Boolean(getCartoAccessToken()),
    regionLabel,
  };
}

export type CartoStatus = {
  ok: boolean;
  apiBaseUrl: string;
  configured: boolean;
  connectionName: string;
  regionLabel: string;
  platform?: { status?: string };
  auth?: "ok" | "unauthorized" | "missing_token" | "error";
  detail?: string;
};

/** Probe platform root + optional authenticated connections list. */
export async function probeCartoStatus(): Promise<CartoStatus> {
  const cfg = getCartoRuntimeConfig();
  const status: CartoStatus = {
    ok: false,
    apiBaseUrl: cfg.apiBaseUrl,
    configured: cfg.configured,
    connectionName: cfg.connectionName,
    regionLabel: cfg.regionLabel,
  };

  try {
    const root = await fetch(`${cfg.apiBaseUrl}/`, {
      method: "GET",
      cache: "no-store",
      signal: AbortSignal.timeout(8_000),
    });
    const body = (await root.json().catch(() => ({}))) as { status?: string };
    status.platform = body;
    if (!root.ok) {
      status.detail = `platform HTTP ${root.status}`;
      return status;
    }
  } catch (err) {
    status.auth = "error";
    status.detail = err instanceof Error ? err.message : "platform unreachable";
    return status;
  }

  const token = getCartoAccessToken();
  if (!token) {
    status.auth = "missing_token";
    status.ok = true; // host is up; token still needed for Maps/SQL
    status.detail = "API host running; set CARTO_ACCESS_TOKEN for Maps/SQL";
    return status;
  }

  try {
    const res = await fetch(`${cfg.apiBaseUrl}/v3/connections`, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
    if (res.status === 401 || res.status === 403) {
      status.auth = "unauthorized";
      status.detail = `auth HTTP ${res.status}`;
      return status;
    }
    if (!res.ok) {
      status.auth = "error";
      status.detail = `connections HTTP ${res.status}`;
      return status;
    }
    status.auth = "ok";
    status.ok = true;
    return status;
  } catch (err) {
    status.auth = "error";
    status.detail = err instanceof Error ? err.message : "auth probe failed";
    return status;
  }
}
