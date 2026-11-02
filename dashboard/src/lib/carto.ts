/**
 * CARTO platform config for the Florida demand map.
 * API base locked from Workspace → Developers (user-provided).
 */
export const CARTO_API_BASE_DEFAULT = "https://gcp-us-east1.api.carto.com";

export const CARTO_BASEMAP =
  "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";

/** Demo table granted on the Maps/SQL token — used for live overlay. */
export const CARTO_FL_PLACES_SOURCE =
  "`carto-demo-data.demo_tables.populated_places`";

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

async function cartoSqlQuery<T = Record<string, unknown>>(
  q: string
): Promise<{ ok: true; rows: T[] } | { ok: false; status: number; error: string }> {
  const cfg = getCartoRuntimeConfig();
  const token = getCartoAccessToken();
  if (!token) {
    return { ok: false, status: 401, error: "missing_token" };
  }
  const url = new URL(
    `${cfg.apiBaseUrl}/v3/sql/${encodeURIComponent(cfg.connectionName)}/query`
  );
  url.searchParams.set("q", q);
  try {
    const res = await fetch(url.toString(), {
      method: "GET",
      headers: { Authorization: `Bearer ${token}`, Accept: "application/json" },
      cache: "no-store",
      signal: AbortSignal.timeout(20_000),
    });
    const body = (await res.json().catch(() => ({}))) as {
      error?: string;
      rows?: T[];
    };
    if (!res.ok) {
      return {
        ok: false,
        status: res.status,
        error: body.error || `SQL HTTP ${res.status}`,
      };
    }
    return { ok: true, rows: body.rows || [] };
  } catch (err) {
    return {
      ok: false,
      status: 500,
      error: err instanceof Error ? err.message : "sql failed",
    };
  }
}

/** Probe platform root + Maps/SQL auth (SELECT 1). */
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
    status.ok = true;
    status.detail = "API host running; set CARTO_ACCESS_TOKEN for Maps/SQL";
    return status;
  }

  const probe = await cartoSqlQuery<{ ok: number }>("SELECT 1 AS ok");
  if (!probe.ok) {
    if (probe.status === 401 || probe.status === 403) {
      status.auth = "unauthorized";
      status.detail = probe.error;
      return status;
    }
    status.auth = "error";
    status.detail = probe.error;
    return status;
  }

  status.auth = "ok";
  status.ok = true;
  status.detail = `Maps/SQL live · ${cfg.connectionName}`;
  return status;
}

export type CartoFloridaPlace = {
  name: string;
  pop_max: number;
  lat: number;
  lng: number;
};

/** Top Florida populated places from CARTO demo warehouse (token-scoped). */
export async function fetchFloridaPlaces(): Promise<
  | { ok: true; places: CartoFloridaPlace[] }
  | { ok: false; status: number; error: string }
> {
  const q = `
SELECT name, pop_max,
  ST_Y(geom) AS lat, ST_X(geom) AS lng
FROM ${CARTO_FL_PLACES_SOURCE}
WHERE adm0name = 'United States of America'
  AND adm1name = 'Florida'
ORDER BY pop_max DESC
LIMIT 40
`.trim();
  const res = await cartoSqlQuery<CartoFloridaPlace>(q);
  if (!res.ok) return res;
  const places = res.rows
    .filter(
      (r) =>
        typeof r.lat === "number" &&
        typeof r.lng === "number" &&
        typeof r.name === "string"
    )
    .map((r) => ({
      name: r.name,
      pop_max: Number(r.pop_max) || 0,
      lat: r.lat,
      lng: r.lng,
    }));
  return { ok: true, places };
}
