"use client";

import { useEffect, useMemo, useRef } from "react";
import type { Metrics } from "@/lib/types";
import { usd, num } from "@/lib/format";

type Props = {
  counties: Metrics["regions"]["counties"];
  selected: string | null;
  onSelect: (county: string | null) => void;
  mode: "sam_valuation" | "sam_count" | "som_usd" | "som_material_usd";
};

function colorScale(t: number): string {
  // gulf deep → sun
  const clamps = Math.max(0, Math.min(1, t));
  const r = Math.round(6 + clamps * (226 - 6));
  const g = Math.round(84 + clamps * (177 - 84));
  const b = Math.round(92 + clamps * (74 - 92));
  return `rgb(${r},${g},${b})`;
}

export default function CountyMap({ counties, selected, onSelect, mode }: Props) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapObj = useRef<import("leaflet").Map | null>(null);
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

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const L = await import("leaflet");
      if (cancelled || !mapRef.current) return;
      if (mapObj.current) {
        mapObj.current.remove();
        mapObj.current = null;
      }
      const map = L.map(mapRef.current, {
        zoomControl: true,
        attributionControl: false,
        scrollWheelZoom: false,
      }).setView([27.8, -83.5], 6);
      mapObj.current = map;

      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        maxZoom: 12,
      }).addTo(map);

      const geo = await fetch("/data/fl-counties.geojson").then((r) => r.json());
      const layer = L.geoJSON(geo as GeoJSON.GeoJsonObject, {
        style: (feat) => {
          const id = String((feat as GeoJSON.Feature).id || "");
          const row = byFips.get(id);
          const v = row ? Number(row[mode as keyof typeof row] || 0) : 0;
          const t = Math.sqrt(v / maxVal);
          const isSel = row && selected === row.county;
          return {
            fillColor: row ? colorScale(t) : "#1a2e33",
            weight: isSel ? 2.5 : 0.8,
            color: isSel ? "#e8dcc8" : "#0a1619",
            fillOpacity: row ? 0.82 : 0.25,
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
            click: () => onSelect(row ? row.county : name),
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
              `<strong>${row.county}</strong><br/>Total Market ${num(row.sam_count)} · ${usd(row.sam_valuation)}<br/>Potential · Tigre 5% ${usd(row.som_usd)}<br/>Materials Potential ${usd(row.som_material_usd || 0)}`,
              { sticky: true }
            );
          } else {
            lyr.bindTooltip(`${name}<br/><em>no bronze coverage here</em>`, {
              sticky: true,
            });
          }
        },
      }).addTo(map);

      if (selected === "Miami-Dade") {
        map.setView([25.6, -80.4], 8);
      }
    })();
    return () => {
      cancelled = true;
      if (mapObj.current) {
        mapObj.current.remove();
        mapObj.current = null;
      }
    };
  }, [byFips, maxVal, mode, onSelect, selected]);

  return (
    <div
      ref={mapRef}
      className="h-[420px] w-full overflow-hidden rounded-sm border border-[var(--line)]"
    />
  );
}
