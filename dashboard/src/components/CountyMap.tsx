"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { Metrics } from "@/lib/types";
import { usd, num } from "@/lib/format";
import {
  getBasemapAttribution,
  getBasemapTileUrl,
  isCartoBasemapKeyed,
} from "@/lib/basemap";
import {
  CARTO_API_BASE_DEFAULT,
  type CartoFloridaPlace,
  type CartoStatus,
} from "@/lib/carto";
import { MIAMI_DADE_MESO_CENTERS, type MesoRegion } from "@/lib/meso";

type Props = {
  counties: Metrics["regions"]["counties"];
  selected: string | null;
  onSelect: (county: string | null) => void;
  mode: "sam_valuation" | "sam_count" | "som_usd" | "som_material_usd";
  mesoregions?: MesoRegion[];
  selectedMeso?: string | null;
  onSelectMeso?: (area: string | null) => void;
};

function colorScale(t: number): string {
  const clamps = Math.max(0, Math.min(1, t));
  const r = Math.round(6 + clamps * (226 - 6));
  const g = Math.round(84 + clamps * (177 - 84));
  const b = Math.round(92 + clamps * (74 - 92));
  return `rgb(${r},${g},${b})`;
}

function featureBounds(
  L: typeof import("leaflet"),
  feat: GeoJSON.Feature
): import("leaflet").LatLngBounds | null {
  try {
    return L.geoJSON(feat).getBounds();
  } catch {
    return null;
  }
}

export default function CountyMap({
  counties,
  selected,
  onSelect,
  mode,
  mesoregions = [],
  selectedMeso = null,
  onSelectMeso,
}: Props) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapObj = useRef<import("leaflet").Map | null>(null);
  const geoByFips = useRef<Map<string, GeoJSON.Feature>>(new Map());
  const [carto, setCarto] = useState<CartoStatus | null>(null);
  const [places, setPlaces] = useState<CartoFloridaPlace[]>([]);

  const byFips = useMemo(() => {
    const m = new Map<string, (typeof counties)[0]>();
    for (const c of counties) {
      if (c.fips) m.set(c.fips, c);
    }
    return m;
  }, [counties]);

  const maxVal = useMemo(() => {
    const vals = counties.map((c) => Number(c[mode as keyof typeof c] || 0));
    return Math.max(...vals, 1);
  }, [counties, mode]);

  const drillMiami = selected === "Miami-Dade" && mesoregions.length > 0;

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/carto/status", { cache: "no-store" });
        if (!res.ok || cancelled) return;
        const body = (await res.json()) as CartoStatus;
        if (!cancelled) setCarto(body);
        if (body.auth === "ok" && !selected) {
          const placesRes = await fetch("/api/carto/florida-places", {
            cache: "no-store",
          });
          if (!placesRes.ok || cancelled) return;
          const placesBody = (await placesRes.json()) as {
            ok?: boolean;
            places?: CartoFloridaPlace[];
          };
          if (!cancelled && placesBody.ok && placesBody.places) {
            setPlaces(placesBody.places);
          }
        } else if (!cancelled) {
          setPlaces([]);
        }
      } catch {
        if (!cancelled) {
          setCarto({
            ok: false,
            apiBaseUrl: CARTO_API_BASE_DEFAULT,
            configured: false,
            connectionName: "carto_dw",
            regionLabel: "gcp-us-east1",
            auth: "error",
            detail: "status unreachable",
          });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selected]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const L = await import("leaflet");
      if (cancelled || !mapRef.current) return;
      if (mapObj.current) {
        mapObj.current.remove();
        mapObj.current = null;
      }

      const keyed = isCartoBasemapKeyed();
      const map = L.map(mapRef.current, {
        zoomControl: true,
        attributionControl: true,
        scrollWheelZoom: true,
      }).setView([27.8, -83.5], 6);
      mapObj.current = map;

      L.tileLayer(getBasemapTileUrl(), {
        maxZoom: 16,
        attribution: getBasemapAttribution(keyed),
      }).addTo(map);

      const geo = await fetch("/data/fl-counties.geojson").then((r) => r.json());
      const fipsMap = new Map<string, GeoJSON.Feature>();
      for (const feat of geo.features as GeoJSON.Feature[]) {
        const id = String(feat.id || "");
        if (id) fipsMap.set(id, feat);
      }
      geoByFips.current = fipsMap;

      const layer = L.geoJSON(geo as GeoJSON.GeoJsonObject, {
        style: (feat) => {
          const id = String((feat as GeoJSON.Feature).id || "");
          const row = byFips.get(id);
          const v = row ? Number(row[mode as keyof typeof row] || 0) : 0;
          const t = Math.sqrt(v / maxVal);
          const isSel = row && selected === row.county;
          const dimOthers = Boolean(selected) && !isSel;
          return {
            fillColor: row ? colorScale(t) : "#1a2e33",
            weight: isSel ? 2.5 : 0.8,
            color: isSel ? "#e8dcc8" : "#0a1619",
            fillOpacity: dimOthers ? 0.15 : row ? 0.82 : 0.25,
          };
        },
        onEachFeature: (feat, lyr) => {
          const id = String(feat.id || "");
          const row = byFips.get(id);
          const name =
            row?.county ||
            (feat.properties as { NAME?: string })?.NAME ||
            id;
          lyr.on({
            click: () => {
              onSelect(row ? row.county : name);
              onSelectMeso?.(null);
            },
            mouseover: (e) => {
              const t = e.target;
              t.setStyle({ weight: 2, color: "#e8dcc8" });
            },
            mouseout: (e) => {
              layer.resetStyle(e.target);
            },
          });
          if (row) {
            lyr.bindTooltip(
              `<strong>${row.county}</strong><br/>Total Market ${num(row.sam_count)} · ${usd(row.sam_valuation)}<br/>Addressable Market ${usd(row.som_usd)}<br/>Tigre × Dura Potential ${usd(row.som_material_usd || 0)}<br/><em>click to enter</em>`,
              { sticky: true }
            );
          } else {
            lyr.bindTooltip(`${name}<br/><em>no bronze coverage here</em>`, {
              sticky: true,
            });
          }
        },
      }).addTo(map);

      // State overview places only when no county selected
      if (!selected && places.length) {
        const maxPop = Math.max(...places.map((p) => p.pop_max), 1);
        for (const p of places) {
          const r = 4 + 10 * Math.sqrt(p.pop_max / maxPop);
          L.circleMarker([p.lat, p.lng], {
            radius: r,
            color: "#e8dcc8",
            weight: 1,
            fillColor: "#e2b14a",
            fillOpacity: 0.7,
          })
            .bindTooltip(
              `<strong>${p.name}</strong><br/>pop ${num(p.pop_max)}`,
              { direction: "top" }
            )
            .addTo(map);
        }
      }

      // Meso drill-down for Miami-Dade
      if (drillMiami) {
        const maxMeso = Math.max(
          ...mesoregions.map((m) => Number(m.som_material_usd || 0)),
          1
        );
        for (const m of mesoregions) {
          const center = MIAMI_DADE_MESO_CENTERS[m.area];
          if (!center) continue;
          const val = Number(m.som_material_usd || 0);
          const isSel = selectedMeso === m.area;
          const r = 6 + 16 * Math.sqrt(val / maxMeso);
          L.circleMarker(center, {
            radius: Math.max(r, 5),
            color: isSel ? "#fff6e8" : "#0a1619",
            weight: isSel ? 2.5 : 1,
            fillColor: isSel ? "#e2b14a" : "#c4a574",
            fillOpacity: isSel ? 0.95 : 0.8,
          })
            .on("click", () => onSelectMeso?.(m.area))
            .bindTooltip(
              `<strong>${m.area}</strong><br/>Total Market ${num(m.sam_count)} · ${usd(m.sam_valuation)}<br/>Tigre × Dura Potential ${usd(m.som_material_usd || 0)}`,
              { direction: "top" }
            )
            .addTo(map);
        }
      }

      // Zoom into selected county
      if (selected) {
        const row = counties.find((c) => c.county === selected);
        const feat = row?.fips ? fipsMap.get(row.fips) : undefined;
        if (feat) {
          const b = featureBounds(L, feat);
          if (b && b.isValid()) {
            map.fitBounds(b.pad(0.08), { maxZoom: drillMiami ? 10 : 9 });
          }
        } else if (selected === "Miami-Dade") {
          map.setView([25.6, -80.4], 9);
        }
      } else {
        map.setView([27.8, -83.5], 6);
      }
    })();
    return () => {
      cancelled = true;
      if (mapObj.current) {
        mapObj.current.remove();
        mapObj.current = null;
      }
    };
  }, [
    byFips,
    counties,
    drillMiami,
    maxVal,
    mesoregions,
    mode,
    onSelect,
    onSelectMeso,
    places,
    selected,
    selectedMeso,
  ]);

  const badge = (() => {
    const base = isCartoBasemapKeyed() ? "CARTO tiles" : "Esri dark";
    if (drillMiami) {
      return selectedMeso
        ? `Meso · ${selectedMeso}`
        : `Miami-Dade · ${mesoregions.length} mesos · ${base}`;
    }
    if (selected) return `${selected} · ${base}`;
    if (!carto) return `Florida · ${base}`;
    if (carto.auth === "ok") return `CARTO SQL live · ${base}`;
    return `Florida · ${base}`;
  })();

  return (
    <div className="relative">
      <div
        ref={mapRef}
        className="h-[420px] w-full overflow-hidden rounded-sm border border-[var(--line)]"
      />
      <div className="pointer-events-none absolute bottom-3 left-3 flex flex-col gap-1">
        <div
          className="rounded-sm border border-[var(--line)] bg-[rgba(8,18,22,0.88)] px-2.5 py-1 text-[10px] uppercase tracking-[0.14em] text-[var(--sand)]"
          title={carto?.apiBaseUrl || CARTO_API_BASE_DEFAULT}
        >
          {badge}
        </div>
      </div>
      {selected ? (
        <button
          type="button"
          className="absolute right-3 top-3 rounded-sm border border-[var(--line)] bg-[rgba(8,18,22,0.92)] px-2.5 py-1 text-[11px] uppercase tracking-[0.12em] text-[var(--sand)] hover:bg-[rgba(20,36,42,0.95)]"
          onClick={() => {
            onSelectMeso?.(null);
            onSelect(null);
          }}
        >
          ← Florida
        </button>
      ) : null}
    </div>
  );
}
