/**
 * Raster basemap for Leaflet.
 * CARTO dark_all tiles require a free Basemaps API key (?key=…) since Sep 2026;
 * without it they render the "API KEY REQUIRED" watermark.
 * Prefer that key when present; otherwise use Esri dark canvas (no watermark).
 */
export const CARTO_DARK_BASEMAP_TEMPLATE =
  "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";

export const ESRI_DARK_BASEMAP =
  "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}";

export function getBasemapTileUrl(): string {
  const key =
    (typeof process !== "undefined" &&
      (process.env.NEXT_PUBLIC_CARTO_BASEMAP_KEY ||
        process.env.CARTO_BASEMAP_KEY)) ||
    "";
  const trimmed = String(key).trim();
  if (trimmed) {
    return `${CARTO_DARK_BASEMAP_TEMPLATE}?key=${encodeURIComponent(trimmed)}`;
  }
  return ESRI_DARK_BASEMAP;
}

export function getBasemapAttribution(usingCartoKey: boolean): string {
  if (usingCartoKey) {
    return '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';
  }
  return "Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ";
}

export function isCartoBasemapKeyed(): boolean {
  const key =
    (typeof process !== "undefined" &&
      (process.env.NEXT_PUBLIC_CARTO_BASEMAP_KEY ||
        process.env.CARTO_BASEMAP_KEY)) ||
    "";
  return Boolean(String(key).trim());
}
