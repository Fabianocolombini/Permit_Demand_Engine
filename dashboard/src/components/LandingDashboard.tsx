"use client";

import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { MetricMode, Metrics } from "@/lib/types";
import {
  categoryLabel,
  MONTHS,
  num,
  pct,
  pctPlain,
  usd,
  ymLabel,
} from "@/lib/format";

const CountyMap = dynamic(() => import("./CountyMap"), { ssr: false });

const GULF = "#0e7c86";
const CORAL = "#c45c3e";
const SUN = "#e2b14a";
const SAND = "#e8dcc8";

const L = {
  tcm: "Total Construction Market",
  market: "Plumbing · Irrigation · Pool",
  marketShort: "Total Market",
  addressable: "Addressable Market",
  tigreDura: "Tigre × Dura Potential",
} as const;

function yearFromClick(
  raw: unknown,
  index?: number,
  rows?: Array<{ year: number | string }>
): number | null {
  if (typeof index === "number" && rows?.[index]) {
    const y = Number(rows[index].year);
    if (Number.isFinite(y) && y >= 2000) return y;
  }
  if (raw == null || typeof raw !== "object") return null;
  const d = raw as Record<string, unknown>;
  for (const c of [
    d.year,
    (d.payload as Record<string, unknown> | undefined)?.year,
    d.label,
  ]) {
    const y = Number(c);
    if (Number.isFinite(y) && y >= 2000) return y;
  }
  return null;
}

export default function LandingDashboard({ data }: { data: Metrics }) {
  const yearOptions = useMemo(
    () =>
      [...new Set(data.sam_som.share_by_year.map((r) => r.year))]
        .filter((y) => y >= 2023)
        .sort(),
    [data.sam_som.share_by_year]
  );
  const [selectedYears, setSelectedYears] = useState<number[]>([
    yearOptions[yearOptions.length - 1] ?? 2026,
  ]);
  const [mode, setMode] = useState<MetricMode>("valuation");
  const [grain, setGrain] = useState<"month" | "quarter">("month");
  const [sharePct, setSharePct] = useState<0.025 | 0.05>(0.05);
  const [pipelineScope, setPipelineScope] = useState<"ytd" | 30 | 60>("ytd");
  const [selectedCounty, setSelectedCounty] = useState<string | null>("Miami-Dade");
  const [selectedMeso, setSelectedMeso] = useState<string | null>(null);

  const ytdM = data.ytd_through_month;
  const onlyYear = (y: number) => setSelectedYears([y]);
  const toggleYear = (y: number) => {
    setSelectedYears((prev) => {
      if (prev.includes(y)) {
        const next = prev.filter((x) => x !== y);
        return next.length ? next : [y];
      }
      return [...prev, y].sort();
    });
  };

  const scopeLabel = useMemo(() => {
    if (selectedYears.length === 1) return String(selectedYears[0]);
    if (selectedYears.length === yearOptions.length) return "2023–2026";
    return selectedYears.join(" + ");
  }, [selectedYears, yearOptions.length]);

  const filteredShare = useMemo(() => {
    const rows = data.sam_som.share_by_year.filter((r) =>
      selectedYears.includes(r.year)
    );
    const tom_count = rows.reduce((s, r) => s + r.tom_count, 0);
    const sam_count = rows.reduce((s, r) => s + r.sam_count, 0);
    const tom_valuation = rows.reduce((s, r) => s + r.tom_valuation, 0);
    const sam_valuation = rows.reduce((s, r) => s + r.sam_valuation, 0);
    return {
      tom_count,
      sam_count,
      tom_valuation,
      sam_valuation,
      sam_share_count_pct: tom_count ? (100 * sam_count) / tom_count : null,
      sam_share_valuation_pct: tom_valuation
        ? (100 * sam_valuation) / tom_valuation
        : null,
    };
  }, [data.sam_som.share_by_year, selectedYears]);

  const filteredCategories = useMemo(() => {
    const map = new Map<
      string,
      {
        category: string;
        count: number;
        valuation: number;
        material_usd: number;
        labor_usd: number;
      }
    >();
    for (const r of data.sam_som.by_category_year) {
      if (!selectedYears.includes(r.year)) continue;
      const cur = map.get(r.category) ?? {
        category: r.category,
        count: 0,
        valuation: 0,
        material_usd: 0,
        labor_usd: 0,
      };
      cur.count += r.count;
      cur.valuation += r.valuation;
      cur.material_usd += r.material_usd;
      cur.labor_usd += r.labor_usd;
      map.set(r.category, cur);
    }
    return [...map.values()].sort((a, b) => b.valuation - a.valuation);
  }, [data.sam_som.by_category_year, selectedYears]);

  const materialsTotal = useMemo(
    () => filteredCategories.reduce((s, r) => s + r.material_usd, 0),
    [filteredCategories]
  );
  const laborTotal = useMemo(
    () => filteredCategories.reduce((s, r) => s + r.labor_usd, 0),
    [filteredCategories]
  );
  const tigrePotential = materialsTotal * sharePct;
  const addressableAtShare = filteredShare.sam_valuation * sharePct;

  const ytdYoY = useMemo(() => {
    if (selectedYears.length !== 1) return null;
    const y = selectedYears[0];
    const sam = data.sam_som.ytd_comparison.find((r) => r.year === y);
    const tom = data.tom.ytd_comparison.find((r) => r.year === y);
    return { y, sam, tom };
  }, [selectedYears, data.sam_som.ytd_comparison, data.tom.ytd_comparison]);

  const monthlySeries = useMemo(() => {
    const rows = data.tom.monthly.filter(
      (p) => p.year >= 2023 && selectedYears.includes(p.year)
    );
    return rows.map((p) => ({
      label: ymLabel(p.year!, p.month!),
      year: p.year!,
      month: p.month!,
      count: p.count ?? 0,
      valuation: p.valuation ?? 0,
      quarter: `Q${Math.ceil((p.month ?? 1) / 3)} ${p.year}`,
    }));
  }, [data.tom.monthly, selectedYears]);

  const grainSeries = useMemo(() => {
    if (grain === "month") {
      return monthlySeries.map((r) => ({
        label: r.label,
        value: mode === "count" ? r.count : r.valuation,
      }));
    }
    const map = new Map<string, { label: string; value: number; order: number }>();
    for (const r of monthlySeries) {
      const q = Math.ceil(r.month / 3);
      const key = `${r.year}-Q${q}`;
      const cur = map.get(key) ?? {
        label: `Q${q} ${r.year}`,
        value: 0,
        order: r.year * 10 + q,
      };
      cur.value += mode === "count" ? r.count : r.valuation;
      map.set(key, cur);
    }
    return [...map.values()]
      .sort((a, b) => a.order - b.order)
      .map(({ label, value }) => ({ label, value }));
  }, [monthlySeries, grain, mode]);

  const quarterGrowth = useMemo(() => {
    if (grain !== "quarter" || selectedYears.length !== 1) return [];
    const y = selectedYears[0];
    const cur = grainSeries.filter((r) => r.label.endsWith(String(y)));
    const prevYear = y - 1;
    const prevRows = data.tom.monthly.filter((p) => p.year === prevYear);
    return cur.map((r) => {
      const q = Number(r.label[1]);
      const prevVal = prevRows
        .filter((p) => Math.ceil((p.month ?? 1) / 3) === q)
        .reduce(
          (s, p) => s + (mode === "count" ? p.count ?? 0 : p.valuation ?? 0),
          0
        );
      const yoy = prevVal > 0 ? (100 * (r.value - prevVal)) / prevVal : null;
      return { label: r.label, value: r.value, yoy };
    });
  }, [grain, grainSeries, selectedYears, data.tom.monthly, mode]);

  const pipe =
    pipelineScope === "ytd"
      ? data.pipeline.ytd ?? data.pipeline.d60
      : pipelineScope === 30
        ? data.pipeline.d30
        : data.pipeline.d60;

  /** Near-term materials @ selected share (pipe stores @ 5%). */
  const pipeMaterialsAtShare = pipe.som_material_usd * (sharePct / 0.05);
  const shareScale = sharePct / 0.05;

  /** Map + county panel share the same near-term county slice as the KPI. */
  const pipelineCounties = useMemo(() => {
    const byName = new Map(pipe.by_county.map((c) => [c.county, c]));
    return data.regions.counties.map((c) => {
      const hit = byName.get(c.county);
      if (!hit) {
        return {
          ...c,
          sam_count: 0,
          sam_valuation: 0,
          som_usd: 0,
          material_usd: 0,
          som_material_usd: 0,
        };
      }
      return {
        ...c,
        sam_count: hit.sam_count,
        sam_valuation: hit.sam_valuation,
        som_usd: hit.som_usd,
        material_usd: hit.material_usd,
        som_material_usd: hit.som_material_usd,
      };
    });
  }, [data.regions.counties, pipe.by_county]);

  const selectedCountyRow = pipelineCounties.find(
    (c) => c.county === selectedCounty
  );

  const regionCountyCats = useMemo(() => {
    const rows = pipe.by_county_category ?? [];
    if (!selectedCounty) return [];
    return rows
      .filter((r) => r.county === selectedCounty)
      .sort((a, b) => b.som_material_usd - a.som_material_usd);
  }, [pipe.by_county_category, selectedCounty]);

  /** Scale all-time Miami meso mix into the selected near-term Miami-Dade pot. */
  const scaledMesoregions = useMemo(() => {
    const mdPipe = pipe.by_county.find((c) => c.county === "Miami-Dade");
    const mdAll = data.regions.counties.find((c) => c.county === "Miami-Dade");
    const base = mdAll?.som_material_usd || 0;
    const target = mdPipe?.som_material_usd || 0;
    const factor = base > 0 ? target / base : 0;
    const valFactor =
      (mdAll?.sam_valuation || 0) > 0
        ? (mdPipe?.sam_valuation || 0) / (mdAll?.sam_valuation || 1)
        : 0;
    const countFactor =
      (mdAll?.sam_count || 0) > 0
        ? (mdPipe?.sam_count || 0) / (mdAll?.sam_count || 1)
        : 0;
    return data.regions.miami_dade.mesoregions.map((m) => ({
      ...m,
      sam_count: Math.round((m.sam_count || 0) * countFactor),
      sam_valuation: (m.sam_valuation || 0) * valFactor,
      som_usd: (m.som_usd || 0) * valFactor,
      material_usd: (m.material_usd || 0) * factor,
      som_material_usd: (m.som_material_usd || 0) * factor,
      note: `${m.note ?? ""} Scaled to near-term window ${pipe.label ?? ""}.`.trim(),
    }));
  }, [
    data.regions.counties,
    data.regions.miami_dade.mesoregions,
    pipe.by_county,
    pipe.label,
  ]);

  const contractors = useMemo(() => {
    const rows = pipe.by_contractor ?? [];
    if (!selectedCounty) return rows;
    return rows.filter((c) =>
      (c.counties || "")
        .split(",")
        .map((s) => s.trim())
        .includes(selectedCounty)
    );
  }, [pipe.by_contractor, selectedCounty]);

  const contractorsMaterialsSum = useMemo(
    () => contractors.reduce((s, c) => s + (c.som_material_usd || 0), 0),
    [contractors]
  );

  const countiesMaterialsSum = useMemo(
    () => pipe.by_county.reduce((s, c) => s + (c.som_material_usd || 0), 0),
    [pipe.by_county]
  );

  const yearBars = data.sam_som.ytd_comparison.filter((r) => r.year >= 2023);

  return (
    <main className="min-h-screen">
      {/* HERO */}
      <section className="hero-shell">
        <div className="hero-media" aria-hidden />
        <header className="relative z-10 flex items-center justify-between px-5 py-5 md:px-10">
          <p className="brand-display text-lg text-[var(--sand)] md:text-xl">
            Tigre <span className="text-[var(--gulf)]">×</span> Dura
          </p>
          <p className="text-[10px] uppercase tracking-[0.18em] text-[var(--muted)]">
            Florida · permits ≥ 2021
          </p>
        </header>
        <div className="relative z-10 flex flex-1 flex-col justify-center px-5 pb-16 pt-8 md:px-10 md:pb-24">
          <p className="rise text-[11px] uppercase tracking-[0.2em] text-[var(--sun)]">
            Permit Demand Engine
          </p>
          <h1 className="rise rise-delay-1 brand-display mt-4 max-w-3xl text-4xl leading-[1.08] text-[var(--foam)] md:text-6xl">
            Florida demand, read from permits.
          </h1>
          <p className="rise rise-delay-2 mt-5 max-w-xl text-base text-[var(--sand)]/90 md:text-lg">
            {L.tcm}, {L.marketShort} ({L.market}), and {L.tigreDura} — same open
            Florida feeds, clearer landing story for S&OP.
          </p>
          <div className="rise rise-delay-3 mt-8 flex flex-wrap gap-3">
            <a href="#markets" className="pill-cta">
              View markets
            </a>
            <a href="#tigre" className="ghost-cta">
              {L.tigreDura}
            </a>
          </div>
          <div className="rise rise-delay-3 mt-12 grid max-w-4xl grid-cols-2 gap-6 md:grid-cols-4">
            <div>
              <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
                {L.tcm}
              </p>
              <p className="stat-value mt-1 text-2xl text-[var(--foam)] md:text-3xl">
                {usd(filteredShare.tom_valuation)}
              </p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
                {L.marketShort}
              </p>
              <p className="stat-value mt-1 text-2xl text-[var(--foam)] md:text-3xl">
                {usd(filteredShare.sam_valuation)}
              </p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
                Segment share
              </p>
              <p className="stat-value mt-1 text-2xl text-[var(--foam)] md:text-3xl">
                {pctPlain(filteredShare.sam_share_valuation_pct)}
              </p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
                {L.tigreDura}
              </p>
              <p className="stat-value mt-1 text-2xl text-[var(--sun)] md:text-3xl">
                {usd(tigrePotential)}
              </p>
            </div>
          </div>
        </div>
        <div className="wave-divider relative z-10" />
      </section>

      {/* STICKY FILTERS */}
      <div className="sticky top-0 z-30 border-b border-[var(--line)] bg-[#071a1f]/95 backdrop-blur">
        <div className="flex flex-wrap items-center gap-3 px-5 py-3 md:px-10">
          <span className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
            Years
          </span>
          {yearOptions.map((y) => (
            <button
              key={y}
              type="button"
              onClick={(e) =>
                e.metaKey || e.ctrlKey || e.shiftKey ? toggleYear(y) : onlyYear(y)
              }
              className={`rounded-full px-3 py-1 text-xs font-medium ${
                selectedYears.includes(y)
                  ? "bg-[var(--gulf)] text-white"
                  : "border border-[var(--line)] text-[var(--muted)]"
              }`}
            >
              {y}
            </button>
          ))}
          <span className="mx-1 h-4 w-px bg-[var(--line)]" />
          <div className="inline-flex rounded-full border border-[var(--line)] p-0.5 text-xs">
            {(
              [
                ["count", "Permits"],
                ["valuation", "Value $"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setMode(id)}
                className={`rounded-full px-3 py-1 ${
                  mode === id ? "bg-[var(--gulf)] text-white" : "text-[var(--muted)]"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="inline-flex rounded-full border border-[var(--line)] p-0.5 text-xs">
            {(
              [
                ["month", "Month"],
                ["quarter", "Quarter"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setGrain(id)}
                className={`rounded-full px-3 py-1 ${
                  grain === id ? "bg-[var(--mangrove)] text-white" : "text-[var(--muted)]"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <p className="ml-auto text-xs text-[var(--muted)]">
            Scope {scopeLabel} · as of {data.as_of}
          </p>
        </div>
      </div>

      {/* MARKETS */}
      <section id="markets" className="section-band px-5 py-14 md:px-10">
        <p className="text-[11px] uppercase tracking-[0.18em] text-[var(--sun)]">
          Markets
        </p>
        <h2 className="brand-display mt-2 max-w-2xl text-3xl text-[var(--foam)] md:text-4xl">
          {L.tcm} and {L.marketShort}
        </h2>
        <p className="mt-3 max-w-2xl text-sm text-[var(--muted)]">
          Click a year above (or a bar below) — every figure on this page recalculates.
          YoY uses YTD Jan–{MONTHS[ytdM - 1]} vs the same months last year.
        </p>

        <div className="mt-10 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <div className="chart-panel p-5">
            <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
              {L.tcm}
            </p>
            <p className="stat-value mt-2 text-3xl text-[var(--foam)]">
              {usd(filteredShare.tom_valuation)}
            </p>
            <p className="mt-2 text-sm text-[var(--muted)]">
              {num(filteredShare.tom_count)} permits
            </p>
          </div>
          <div className="chart-panel p-5">
            <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
              {L.marketShort}
            </p>
            <p className="stat-value mt-2 text-3xl text-[var(--foam)]">
              {usd(filteredShare.sam_valuation)}
            </p>
            <p className="mt-2 text-sm text-[var(--muted)]">
              {L.market} · {num(filteredShare.sam_count)} permits
            </p>
          </div>
          <div className="chart-panel p-5">
            <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
              Segment of construction
            </p>
            <p className="stat-value mt-2 text-3xl text-[var(--sun)]">
              {pctPlain(filteredShare.sam_share_valuation_pct)}
            </p>
            <p className="mt-2 text-sm text-[var(--muted)]">
              {pctPlain(filteredShare.sam_share_count_pct)} of permits
            </p>
          </div>
          <div className="chart-panel p-5">
            <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
              YTD YoY · {L.marketShort}
            </p>
            <p className="stat-value mt-2 text-3xl text-[var(--foam)]">
              {pct(ytdYoY?.sam?.valuation_yoy_pct)}
            </p>
            <p className="mt-2 text-sm text-[var(--muted)]">
              Permits {pct(ytdYoY?.sam?.count_yoy_pct)} · TCM ${" "}
              {pct(ytdYoY?.tom?.valuation_yoy_pct)}
            </p>
          </div>
        </div>

        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          <div className="chart-panel p-5">
            <p className="mb-4 text-sm text-[var(--muted)]">
              YTD {L.marketShort} by year · click to filter
            </p>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={yearBars.map((r) => ({
                    year: r.year,
                    label: String(r.year),
                    count: r.count,
                    valuationB: r.valuation / 1e9,
                  }))}
                >
                  <CartesianGrid stroke="rgba(232,220,200,0.08)" vertical={false} />
                  <XAxis dataKey="label" stroke={SAND} tick={{ fill: SAND, fontSize: 12 }} />
                  <YAxis stroke={SAND} tick={{ fill: SAND, fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      background: "#0c2a32",
                      border: "1px solid rgba(232,220,200,0.2)",
                    }}
                    formatter={(v, name) =>
                      String(name).includes("valuation")
                        ? usd(Number(v) * 1e9)
                        : num(Number(v))
                    }
                  />
                  <Bar
                    dataKey={mode === "count" ? "count" : "valuationB"}
                    radius={[2, 2, 0, 0]}
                    cursor="pointer"
                    onClick={(d, index) => {
                      const y = yearFromClick(d, index, yearBars);
                      if (y) onlyYear(y);
                    }}
                  >
                    {yearBars.map((r) => (
                      <Cell
                        key={r.year}
                        cursor="pointer"
                        fill={selectedYears.includes(r.year) ? GULF : "#35555a"}
                        onClick={() => onlyYear(r.year)}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="chart-panel p-5">
            <p className="mb-4 text-sm text-[var(--muted)]">
              {L.tcm} · {grain === "month" ? "monthly" : "quarterly"} trajectory
            </p>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={grain === "quarter" && quarterGrowth.length ? quarterGrowth : grainSeries}>
                  <CartesianGrid stroke="rgba(232,220,200,0.08)" vertical={false} />
                  <XAxis
                    dataKey="label"
                    stroke={SAND}
                    tick={{ fill: SAND, fontSize: 10 }}
                    minTickGap={24}
                  />
                  <YAxis stroke={SAND} tick={{ fill: SAND, fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      background: "#0c2a32",
                      border: "1px solid rgba(232,220,200,0.2)",
                    }}
                    formatter={(v, name) =>
                      name === "yoy"
                        ? `${Number(v).toFixed(1)}%`
                        : mode === "count"
                          ? num(Number(v))
                          : usd(Number(v))
                    }
                  />
                  <Bar dataKey="value" fill={GULF} radius={[2, 2, 0, 0]} name={mode === "count" ? "Permits" : "Value $"} />
                  {grain === "quarter" && (
                    <Line
                      type="monotone"
                      dataKey="yoy"
                      stroke={SUN}
                      strokeWidth={2}
                      dot={false}
                      name="YoY %"
                    />
                  )}
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <p className="mt-2 text-xs text-[var(--muted)]">
              Toggle Month / Quarter in the sticky bar. Quarterly shows YoY vs same
              quarter prior year when one year is selected.
            </p>
          </div>
        </div>
      </section>

      {/* SEGMENT */}
      <section id="segment" className="section-band px-5 py-14 md:px-10">
        <p className="text-[11px] uppercase tracking-[0.18em] text-[var(--sun)]">
          Segment
        </p>
        <h2 className="brand-display mt-2 max-w-2xl text-3xl text-[var(--foam)] md:text-4xl">
          {L.market}
        </h2>
        <p className="mt-3 max-w-2xl text-sm text-[var(--muted)]">
          Named segment for the addressable Total Market — how it splits across
          categories, and how much of that is materials vs labor.
        </p>

        <div className="mt-10 grid gap-6 lg:grid-cols-5">
          <div className="chart-panel p-5 lg:col-span-2">
            <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
              Segment vs {L.tcm}
            </p>
            <p className="stat-value mt-3 text-5xl text-[var(--foam)]">
              {pctPlain(filteredShare.sam_share_valuation_pct)}
            </p>
            <p className="mt-2 text-sm text-[var(--muted)]">
              of construction $ · {pctPlain(filteredShare.sam_share_count_pct)} of
              permits
            </p>
            <div className="mt-8 grid grid-cols-2 gap-4 border-t border-[var(--line)] pt-6">
              <div>
                <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
                  Materials
                </p>
                <p className="stat-value mt-1 text-2xl text-[var(--gulf)]">
                  {usd(materialsTotal)}
                </p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
                  Labor / other
                </p>
                <p className="stat-value mt-1 text-2xl text-[#c45c3e]">
                  {usd(laborTotal)}
                </p>
              </div>
            </div>
            <p className="mt-3 text-xs text-[var(--muted)]">
              Materials{" "}
              {pctPlain(
                materialsTotal + laborTotal
                  ? (100 * materialsTotal) / (materialsTotal + laborTotal)
                  : null
              )}{" "}
              of estimated plumbing/pool/irrigation content.
            </p>
          </div>

          <div className="chart-panel p-5 lg:col-span-3">
            <p className="mb-4 text-sm text-[var(--muted)]">
              Category mix · {scopeLabel}
            </p>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={filteredCategories.map((r) => ({
                    name: categoryLabel(r.category).replace(
                      "New residential plumbing",
                      "New resid. plumbing"
                    ),
                    valuation: r.valuation,
                    material: r.material_usd,
                    labor: r.labor_usd,
                  }))}
                  layout="vertical"
                  margin={{ left: 8 }}
                >
                  <CartesianGrid stroke="rgba(232,220,200,0.08)" horizontal={false} />
                  <XAxis type="number" stroke={SAND} tick={{ fill: SAND, fontSize: 11 }} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={118}
                    stroke={SAND}
                    tick={{ fill: SAND, fontSize: 10 }}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#0c2a32",
                      border: "1px solid rgba(232,220,200,0.2)",
                    }}
                    formatter={(v) => usd(Number(v))}
                  />
                  <Legend />
                  <Bar dataKey="material" stackId="a" fill={GULF} name="Materials" />
                  <Bar dataKey="labor" stackId="a" fill={CORAL} name="Labor / other" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div className="mt-6 overflow-x-auto chart-panel p-5">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead>
              <tr className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
                <th className="pb-2">Category</th>
                <th className="pb-2">Permits</th>
                <th className="pb-2">{L.marketShort} $</th>
                <th className="pb-2">Materials</th>
                <th className="pb-2">Labor / other</th>
                <th className="pb-2">{L.tigreDura}</th>
              </tr>
            </thead>
            <tbody>
              {filteredCategories.map((r) => (
                <tr key={r.category} className="table-row">
                  <td className="py-2.5 text-[var(--sand)]">
                    {categoryLabel(r.category)}
                  </td>
                  <td className="py-2.5">{num(r.count)}</td>
                  <td className="py-2.5">{usd(r.valuation)}</td>
                  <td className="py-2.5">{usd(r.material_usd)}</td>
                  <td className="py-2.5">{usd(r.labor_usd)}</td>
                  <td className="py-2.5 text-[var(--sun)]">
                    {usd(r.material_usd * sharePct)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* TIGRE POTENTIAL */}
      <section id="tigre" className="section-band px-5 py-14 md:px-10">
        <p className="text-[11px] uppercase tracking-[0.18em] text-[var(--sun)]">
          Obtainable share
        </p>
        <h2 className="brand-display mt-2 max-w-2xl text-3xl text-[var(--foam)] md:text-4xl">
          {L.tigreDura}
        </h2>
        <p className="mt-3 max-w-2xl text-sm text-[var(--muted)]">
          Materials-only slice. Choose 2.5% or 5% market share — construction
          addressable stays visible for context.
        </p>

        <div className="mt-6 inline-flex rounded-full border border-[var(--line)] p-0.5 text-xs">
          {(
            [
              [0.025, "2.5% share"],
              [0.05, "5% share"],
            ] as const
          ).map(([v, label]) => (
            <button
              key={v}
              type="button"
              onClick={() => setSharePct(v)}
              className={`rounded-full px-4 py-1.5 ${
                sharePct === v ? "bg-[var(--sun)] text-[#071a1f]" : "text-[var(--muted)]"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="mt-8 grid gap-6 md:grid-cols-3">
          <div className="chart-panel p-6">
            <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
              {L.addressable} · construction
            </p>
            <p className="stat-value mt-2 text-4xl text-[var(--foam)]">
              {usd(addressableAtShare)}
            </p>
            <p className="mt-2 text-sm text-[var(--muted)]">
              {pctPlain(sharePct * 100)} of {L.marketShort} construction $
            </p>
          </div>
          <div className="chart-panel p-6">
            <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
              {L.tigreDura} · materials
            </p>
            <p className="stat-value mt-2 text-4xl text-[var(--sun)]">
              {usd(pipeMaterialsAtShare)}
            </p>
            <p className="mt-2 text-sm text-[var(--muted)]">
              {pctPlain(sharePct * 100)} of estimated materials · same window as
              county map ({pipe.label ?? "near-term"})
            </p>
          </div>
          <div className="chart-panel p-6">
            <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
              Near-term materials · {pipe.label ?? `last ${pipelineScope}d`}
            </p>
            <p className="stat-value mt-2 text-4xl text-[var(--foam)]">
              {usd(pipeMaterialsAtShare)}
            </p>
            <p className="mt-2 text-sm text-[var(--muted)]">
              Growth vs prior window{" "}
              {pct(pipe.growth?.som_material_pct)} · Σ counties{" "}
              {usd(countiesMaterialsSum * shareScale)}
            </p>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-2">
          <span className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
            Near-term window
          </span>
          {(
            [
              ["ytd", `YTD Jan–${MONTHS[ytdM - 1]}`],
              [30, "Last 30 days"],
              [60, "Last 60 days"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={String(id)}
              type="button"
              onClick={() => setPipelineScope(id)}
              className={`rounded-full px-3 py-1 text-xs ${
                pipelineScope === id
                  ? "bg-[var(--gulf)] text-white"
                  : "border border-[var(--line)] text-[var(--muted)]"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </section>

      {/* COUNTIES */}
      <section id="counties" className="section-band px-5 py-14 md:px-10">
        <p className="text-[11px] uppercase tracking-[0.18em] text-[var(--sun)]">
          Geography
        </p>
        <h2 className="brand-display mt-2 text-3xl text-[var(--foam)] md:text-4xl">
          County analysis
        </h2>
        <p className="mt-3 max-w-2xl text-sm text-[var(--muted)]">
          Same near-term window as above ({pipe.label ?? "pipeline"}) — county{" "}
          {L.tigreDura} sums to {usd(pipeMaterialsAtShare)}. Click any county to
          zoom; Miami-Dade opens mesoregions.
        </p>

        <div className="mt-10 grid gap-6 lg:grid-cols-5">
          <div className="chart-panel p-4 lg:col-span-3">
            <CountyMap
              counties={pipelineCounties}
              selected={selectedCounty}
              onSelect={(c) => {
                setSelectedCounty(c);
                setSelectedMeso(null);
              }}
              mode="som_material_usd"
              mesoregions={scaledMesoregions}
              selectedMeso={selectedMeso}
              onSelectMeso={setSelectedMeso}
            />
          </div>
          <div className="space-y-4 lg:col-span-2">
            <div className="chart-panel p-5">
              <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
                {pipe.label ?? "Near-term"} · {pctPlain(sharePct * 100)} materials
              </p>
              <p className="mt-1 text-sm text-[var(--sand)]">
                {selectedMeso
                  ? `Miami-Dade · ${selectedMeso}`
                  : selectedCounty ?? "Select a county"}
              </p>
              {selectedCountyRow && !selectedMeso ? (
                <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-[var(--muted)]">{L.marketShort} $</p>
                    <p className="stat-value text-xl">
                      {usd(selectedCountyRow.sam_valuation)}
                    </p>
                  </div>
                  <div>
                    <p className="text-[var(--muted)]">{L.tigreDura}</p>
                    <p className="stat-value text-xl text-[var(--sun)]">
                      {usd((selectedCountyRow.som_material_usd || 0) * shareScale)}
                    </p>
                  </div>
                </div>
              ) : null}
              {selectedMeso
                ? (() => {
                    const meso = scaledMesoregions.find(
                      (a) => a.area === selectedMeso
                    );
                    if (!meso) return null;
                    return (
                      <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                        <div>
                          <p className="text-[var(--muted)]">{L.marketShort} $</p>
                          <p className="stat-value text-xl">
                            {usd(meso.sam_valuation)}
                          </p>
                        </div>
                        <div>
                          <p className="text-[var(--muted)]">{L.tigreDura}</p>
                          <p className="stat-value text-xl text-[var(--sun)]">
                            {usd((meso.som_material_usd || 0) * shareScale)}
                          </p>
                        </div>
                        <div className="col-span-2">
                          <p className="text-[var(--muted)]">Permits</p>
                          <p className="stat-value text-lg">{num(meso.sam_count)}</p>
                        </div>
                      </div>
                    );
                  })()
                : null}
              {regionCountyCats.length > 0 && !selectedMeso && (
                <table className="mt-4 w-full text-left text-sm">
                  <thead>
                    <tr className="text-[10px] uppercase text-[var(--muted)]">
                      <th className="pb-1">Category</th>
                      <th>Permits</th>
                      <th>{L.tigreDura}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {regionCountyCats.map((r) => (
                      <tr key={r.category} className="table-row">
                        <td className="py-1.5 text-[var(--sand)]">
                          {categoryLabel(r.category)}
                        </td>
                        <td>{num(r.sam_count)}</td>
                        <td className="text-[var(--sun)]">
                          {usd(r.som_material_usd * shareScale)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              {!selectedCountyRow && selectedCounty ? (
                <p className="mt-3 text-sm text-[var(--muted)]">
                  No SAM activity for {selectedCounty} in this near-term window.
                </p>
              ) : null}
            </div>
            {selectedCounty === "Miami-Dade" ? (
              <div className="chart-panel max-h-72 overflow-y-auto p-4">
                <p className="mb-2 text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
                  Mesoregions · {pipe.label}
                </p>
                <p className="mb-3 text-[11px] text-[var(--muted)]">
                  {data.regions.miami_dade.coverage_note}
                </p>
                {[...scaledMesoregions]
                  .sort(
                    (a, b) => (b.som_material_usd || 0) - (a.som_material_usd || 0)
                  )
                  .map((a) => (
                    <button
                      key={a.area}
                      type="button"
                      onClick={() => setSelectedMeso(a.area)}
                      className={`flex w-full items-center justify-between rounded px-2 py-1.5 text-left text-sm hover:bg-white/5 ${
                        selectedMeso === a.area ? "bg-white/10" : ""
                      }`}
                    >
                      <span className="text-[var(--sand)]">{a.area}</span>
                      <span className="text-[var(--muted)]">
                        {usd((a.som_material_usd || 0) * shareScale)}
                      </span>
                    </button>
                  ))}
              </div>
            ) : (
              <div className="chart-panel max-h-64 overflow-y-auto p-4">
                <p className="mb-2 text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
                  All counties · {pipe.label}
                </p>
                {[...pipelineCounties]
                  .filter((c) => (c.som_material_usd || 0) > 0)
                  .sort(
                    (a, b) => (b.som_material_usd || 0) - (a.som_material_usd || 0)
                  )
                  .map((c) => (
                    <button
                      key={c.county}
                      type="button"
                      onClick={() => {
                        setSelectedCounty(c.county);
                        setSelectedMeso(null);
                      }}
                      className={`flex w-full items-center justify-between rounded px-2 py-1.5 text-left text-sm hover:bg-white/5 ${
                        selectedCounty === c.county ? "bg-white/10" : ""
                      }`}
                    >
                      <span className="text-[var(--sand)]">{c.county}</span>
                      <span className="text-[var(--muted)]">
                        {usd((c.som_material_usd || 0) * shareScale)}
                      </span>
                    </button>
                  ))}
                <p className="mt-3 border-t border-[var(--line)] pt-2 text-[11px] text-[var(--muted)]">
                  Σ counties {usd(countiesMaterialsSum * shareScale)} = near-term{" "}
                  {usd(pipeMaterialsAtShare)}
                </p>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* CONTRACTORS */}
      <section id="contractors" className="section-band px-5 py-14 md:px-10">
        <p className="text-[11px] uppercase tracking-[0.18em] text-[var(--sun)]">
          Outreach
        </p>
        <h2 className="brand-display mt-2 text-3xl text-[var(--foam)] md:text-4xl">
          Contractor analysis
        </h2>
        <p className="mt-3 max-w-2xl text-sm text-[var(--muted)]">
          Same window · {pipe.label}
          {selectedCounty ? ` · filtered to ${selectedCounty}` : ""}. Top named
          contractors by materials potential (owner-builder / blank excluded). Listed
          sum {usd(contractorsMaterialsSum * shareScale)} of near-term{" "}
          {usd(pipeMaterialsAtShare)}.
        </p>

        <div className="mt-8 overflow-x-auto chart-panel p-5">
          <table className="w-full min-w-[860px] text-left text-sm">
            <thead>
              <tr className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
                <th className="pb-2">#</th>
                <th className="pb-2">Contractor</th>
                <th className="pb-2">Permits</th>
                <th className="pb-2">Value $</th>
                <th className="pb-2">{L.tigreDura}</th>
                <th className="pb-2">Counties</th>
                <th className="pb-2">Categories</th>
              </tr>
            </thead>
            <tbody>
              {contractors.slice(0, 40).map((c, i) => (
                <tr key={c.contractor_name} className="table-row">
                  <td className="py-2 text-[var(--muted)]">{i + 1}</td>
                  <td className="py-2 text-[var(--sand)]">{c.contractor_name}</td>
                  <td className="py-2">{num(c.permits)}</td>
                  <td className="py-2">{usd(c.valuation)}</td>
                  <td className="py-2 text-[var(--sun)]">
                    {usd((c.som_material_usd || 0) * shareScale)}
                  </td>
                  <td className="max-w-[160px] truncate py-2 text-[var(--muted)]">
                    {c.counties}
                  </td>
                  <td className="max-w-[180px] truncate py-2 text-[var(--muted)]">
                    {c.categories}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <footer className="border-t border-[var(--line)] px-5 py-8 text-xs text-[var(--muted)] md:px-10">
        Tigre × Dura · {L.tcm} → {L.marketShort} ({L.market}) → {L.addressable} →{" "}
        {L.tigreDura} · as of {data.as_of} · open Florida feeds
      </footer>
    </main>
  );
}
