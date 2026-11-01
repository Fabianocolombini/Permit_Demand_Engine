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
import type { MetricMode, Metrics, TabId } from "@/lib/types";
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
const MANGROVE = "#1f6b4f";
const CORAL = "#c45c3e";
const SUN = "#e2b14a";
const SAND = "#e8dcc8";

/** Product naming (executive English) — aligned with Tigre × Dura */
const L = {
  tcm: "Total Construction Market",
  market: "Plumbing · Irrigation · Pool",
  marketShort: "Total Market",
  addressable: "Addressable Market",
  tigreDura: "Tigre × Dura Potential",
} as const;

const TABS: { id: TabId; label: string }[] = [
  { id: "tom", label: "Construction Market" },
  { id: "sam", label: "Total Market" },
  { id: "pipeline", label: "Pipeline 30/60d" },
  { id: "regions", label: "Regions / Map" },
  { id: "contractors", label: "Contractors" },
];

function YearChips({
  years,
  selected,
  onToggle,
  onOnly,
}: {
  years: number[];
  selected: number[];
  onToggle: (y: number) => void;
  onOnly: (y: number) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="mr-1 text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
        Years
      </span>
      {years.map((y) => {
        const on = selected.includes(y);
        return (
          <button
            key={y}
            type="button"
            title="Click = this year only · Ctrl/Cmd/Shift+click to multi-select"
            onClick={(e) => {
              if (e.metaKey || e.ctrlKey || e.shiftKey) onToggle(y);
              else onOnly(y);
            }}
            className={`rounded-full px-2.5 py-1 text-xs font-medium transition ${
              on
                ? "bg-[var(--gulf)] text-white"
                : "border border-[var(--line)] text-[var(--muted)] hover:text-[var(--sand)]"
            }`}
          >
            {y}
          </button>
        );
      })}
      <button
        type="button"
        onClick={() => {
          years.forEach((y) => {
            if (!selected.includes(y)) onToggle(y);
          });
        }}
        className="ml-1 text-[10px] uppercase tracking-[0.12em] text-[var(--muted)] hover:text-[var(--sand)]"
      >
        All
      </button>
    </div>
  );
}

function Kpi({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="border-l border-[var(--line)] pl-4 first:border-l-0 first:pl-0">
      <p className="text-[10px] uppercase tracking-[0.16em] text-[var(--muted)]">
        {label}
      </p>
      <p className="stat-value mt-1 text-2xl text-[var(--sand)] md:text-3xl">
        {value}
      </p>
      {sub && <p className="mt-1 text-xs text-[var(--muted)]">{sub}</p>}
    </div>
  );
}

function Panel({
  title,
  children,
  action,
}: {
  title: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="chart-panel flex flex-col p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <p className="text-sm text-[var(--muted)]">{title}</p>
        {action}
      </div>
      <div className="min-h-0 flex-1">{children}</div>
    </div>
  );
}

function ModeToggle({
  mode,
  setMode,
}: {
  mode: MetricMode;
  setMode: (m: MetricMode) => void;
}) {
  return (
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
          className={`rounded-full px-3 py-1 transition ${
            mode === id
              ? "bg-[var(--gulf)] text-[var(--foam)]"
              : "text-[var(--muted)] hover:text-[var(--sand)]"
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

export default function Dashboard({ data }: { data: Metrics }) {
  const yearOptions = useMemo(
    () =>
      [...new Set(data.sam_som.by_category_year.map((r) => r.year))]
        .filter((y) => y >= 2023)
        .sort(),
    [data.sam_som.by_category_year]
  );
  const [tab, setTab] = useState<TabId>("tom");
  const [mode, setMode] = useState<MetricMode>("count");
  const [selectedYears, setSelectedYears] = useState<number[]>(() => [
    yearOptions[yearOptions.length - 1] ?? 2026,
  ]);
  const [selectedCounty, setSelectedCounty] = useState<string | null>(null);
  const [miamiOpen, setMiamiOpen] = useState(false);
  const [pipelineDays, setPipelineDays] = useState<30 | 60>(30);
  const [pipelineCounty, setPipelineCounty] = useState<string | null>(null);
  const [contractorRank, setContractorRank] = useState<"permits" | "valuation">(
    "permits"
  );
  const [contractorScope, setContractorScope] = useState<"near" | "ytd">("near");

  const toggleYear = (y: number) => {
    setSelectedYears((prev) => {
      if (prev.includes(y)) {
        const next = prev.filter((x) => x !== y);
        return next.length ? next : [y];
      }
      return [...prev, y].sort();
    });
  };
  const onlyYear = (y: number) => setSelectedYears([y]);

  const ytdM = data.ytd_through_month;
  const tomYtd = data.tom.ytd_comparison;
  const samYtd = data.sam_som.ytd_comparison;
  const latestTomYtd = tomYtd[tomYtd.length - 1];
  const latestSamYtd = samYtd[samYtd.length - 1];

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
      sam_share_count_pct:
        tom_count > 0 ? (100 * sam_count) / tom_count : null,
      sam_share_valuation_pct:
        tom_valuation > 0 ? (100 * sam_valuation) / tom_valuation : null,
      som_usd: sam_valuation * 0.05,
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
        som_usd: number;
        som_material_usd: number;
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
        som_usd: 0,
        som_material_usd: 0,
      };
      cur.count += r.count;
      cur.valuation += r.valuation;
      cur.material_usd += r.material_usd;
      cur.labor_usd += r.labor_usd;
      cur.som_usd += r.som_usd;
      cur.som_material_usd += r.som_material_usd;
      map.set(r.category, cur);
    }
    return [...map.values()].sort((a, b) => b.som_material_usd - a.som_material_usd);
  }, [data.sam_som.by_category_year, selectedYears]);

  const filteredMatLab = useMemo(
    () =>
      data.sam_som.material_labor_annual.filter((r) =>
        selectedYears.includes(r.year)
      ),
    [data.sam_som.material_labor_annual, selectedYears]
  );

  const materialsPotentialSelected = useMemo(
    () => filteredCategories.reduce((s, r) => s + r.som_material_usd, 0),
    [filteredCategories]
  );

  /** Category rows for Total Market tab — YTD + YoY when a single year is selected. */
  const categoryGrowthRows = useMemo(() => {
    if (selectedYears.length === 1) {
      const y = selectedYears[0];
      const cur = data.sam_som.by_category_ytd.filter((r) => r.year === y);
      const prev = data.sam_som.by_category_ytd.filter((r) => r.year === y - 1);
      const prevByCat = new Map(prev.map((r) => [r.category, r]));
      return cur
        .map((r) => {
          const p = prevByCat.get(r.category);
          const tigre = r.material_usd * 0.05;
          const tigrePrev = p ? p.material_usd * 0.05 : null;
          const tigreYoy =
            tigrePrev != null && tigrePrev > 0
              ? (100 * (tigre - tigrePrev)) / tigrePrev
              : null;
          return {
            category: r.category,
            count: r.count,
            valuation: r.valuation,
            addressable: r.som_usd,
            material_usd: r.material_usd,
            tigreDura: tigre,
            count_yoy_pct: r.count_yoy_pct,
            valuation_yoy_pct: r.valuation_yoy_pct,
            tigre_yoy_pct: tigreYoy,
            ytd: true as const,
          };
        })
        .sort((a, b) => b.tigreDura - a.tigreDura);
    }
    return filteredCategories.map((r) => ({
      category: r.category,
      count: r.count,
      valuation: r.valuation,
      addressable: r.som_usd,
      material_usd: r.material_usd,
      tigreDura: r.som_material_usd,
      count_yoy_pct: null as number | null,
      valuation_yoy_pct: null as number | null,
      tigre_yoy_pct: null as number | null,
      ytd: false as const,
    }));
  }, [selectedYears, data.sam_som.by_category_ytd, filteredCategories]);

  const marketTabYtd = useMemo(() => {
    if (selectedYears.length !== 1) return null;
    return samYtd.find((r) => r.year === selectedYears[0]) ?? null;
  }, [selectedYears, samYtd]);

  const headerScopeLabel = useMemo(() => {
    if (selectedYears.length === 1) return String(selectedYears[0]);
    if (selectedYears.length === yearOptions.length) return "2023–2026";
    return selectedYears.join(" + ");
  }, [selectedYears, yearOptions.length]);

  /** YoY always uses same-period YTD (Jan–ytdM), never full-year vs partial. */
  const headerYoY = useMemo(() => {
    if (selectedYears.length !== 1) return null;
    const y = selectedYears[0];
    const tom = tomYtd.find((r) => r.year === y);
    const sam = samYtd.find((r) => r.year === y);
    if (!tom && !sam) return null;
    return {
      y,
      throughMonth: ytdM,
      marketValPct: sam?.valuation_yoy_pct ?? null,
      marketCountPct: sam?.count_yoy_pct ?? null,
      tcmValPct: tom?.valuation_yoy_pct ?? null,
      tcmCountPct: tom?.count_yoy_pct ?? null,
    };
  }, [selectedYears, tomYtd, samYtd, ytdM]);

  const pipe = pipelineDays === 30 ? data.pipeline.d30 : data.pipeline.d60;

  const pipelineCountyCats = useMemo(() => {
    const rows = pipe.by_county_category ?? [];
    if (!pipelineCounty) return [];
    return rows
      .filter((r) => r.county === pipelineCounty)
      .sort((a, b) => b.som_material_usd - a.som_material_usd);
  }, [pipe, pipelineCounty]);

  const regionCountyCats = useMemo(() => {
    const rows = data.regions.county_by_category ?? [];
    if (!selectedCounty) return [];
    return rows
      .filter((r) => r.county === selectedCounty)
      .sort((a, b) => b.som_material_usd - a.som_material_usd);
  }, [data.regions.county_by_category, selectedCounty]);

  const mat2026 = data.sam_som.material_labor_annual.find((r) => r.year === 2026);

  const tomMonthlyChart = useMemo(() => {
    const series =
      mode === "count"
        ? data.tom.monthly_count_with_projection
        : data.tom.monthly_valuation_with_projection;
    const recent = series.filter((p) => p.year >= 2023);
    return recent.map((p) => ({
      label: ymLabel(p.year, p.month),
      observed: p.kind === "observed" ? p.value : null,
      projected: p.kind === "projected" ? p.value : null,
      bridge:
        p.kind === "observed" &&
        recent.some(
          (q) =>
            q.kind === "projected" &&
            q.year === p.year &&
            q.month === p.month + 1
        )
          ? p.value
          : p.kind === "projected"
            ? p.value
            : null,
    }));
  }, [data.tom, mode]);

  const ytdCompareChart = useMemo(() => {
    const src = tab === "sam" ? samYtd : tomYtd;
    return src
      .filter((r) => r.year >= 2023)
      .map((r) => ({
        year: String(r.year),
        count: r.count,
        valuationB: r.valuation / 1e9,
        countYoY: r.count_yoy_pct,
        valYoY: r.valuation_yoy_pct,
      }));
  }, [tab, tomYtd, samYtd]);

  const selectedCountyRow = data.regions.counties.find(
    (c) => c.county === selectedCounty
  );

  const contractorList =
    contractorScope === "near"
      ? contractorRank === "permits"
        ? data.contractors.near_term_by_permits
        : data.contractors.near_term_by_valuation
      : contractorRank === "permits"
        ? data.contractors.ytd_by_permits
        : data.contractors.ytd_by_valuation;

  return (
    <main className="min-h-screen">
      <header className="relative overflow-hidden border-b border-[var(--line)]">
        <div
          className="absolute inset-0 opacity-40"
          style={{
            backgroundImage: "url(/images/florida-keys.jpg)",
            backgroundSize: "cover",
            backgroundPosition: "center 45%",
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-r from-[#071a1f] via-[#071a1f]/90 to-[#071a1f]/55" />
        <div className="relative z-10 px-5 py-6 md:px-8">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="brand-display text-xl text-[var(--sand)] md:text-2xl">
                Tigre <span className="text-[var(--gulf)]">×</span> Dura
              </p>
              <p className="mt-1 text-sm text-[var(--muted)]">
                Florida Permit Demand · {L.market} · as of {data.as_of} · YoY always
                YTD Jan–{MONTHS[ytdM - 1]}
              </p>
            </div>
            <div className="flex flex-col items-end gap-2">
              <YearChips
                years={yearOptions}
                selected={selectedYears}
                onToggle={toggleYear}
                onOnly={onlyYear}
              />
              <ModeToggle mode={mode} setMode={setMode} />
            </div>
          </div>
          <div className="mt-6 grid grid-cols-2 gap-6 lg:grid-cols-5">
            <Kpi
              label={`${L.tcm} · ${headerScopeLabel}`}
              value={usd(filteredShare.tom_valuation)}
              sub={`${num(filteredShare.tom_count)} permits`}
            />
            <Kpi
              label={`${L.marketShort} · ${headerScopeLabel}`}
              value={usd(filteredShare.sam_valuation)}
              sub={`${L.market} · ${num(filteredShare.sam_count)} permits · ${pctPlain(filteredShare.sam_share_valuation_pct)} of TCM $`}
            />
            <Kpi
              label={`${L.addressable} · ${headerScopeLabel}`}
              value={usd(filteredShare.som_usd)}
              sub="5% of Total Market construction $"
            />
            <Kpi
              label={`${L.tigreDura} · ${headerScopeLabel}`}
              value={usd(materialsPotentialSelected)}
              sub="5% market share · materials only"
            />
            <Kpi
              label={
                headerYoY
                  ? `YTD YoY vs ${headerYoY.y - 1}`
                  : `YTD YoY ${latestSamYtd?.year} vs LY`
              }
              value={
                headerYoY
                  ? pct(headerYoY.marketValPct)
                  : pct(latestSamYtd?.valuation_yoy_pct)
              }
              sub={
                headerYoY
                  ? `Jan–${MONTHS[ytdM - 1]} same period · Total Market $ · permits ${pct(headerYoY.marketCountPct)} · TCM $ ${pct(headerYoY.tcmValPct)}`
                  : `Jan–${MONTHS[ytdM - 1]} · Total Market $ · permits ${pct(latestSamYtd?.count_yoy_pct)}`
              }
            />
          </div>
          <p className="mt-4 max-w-4xl text-xs text-[var(--muted)]">
            <span className="text-[var(--sand)]">Naming:</span> {L.tcm} → {L.marketShort}{" "}
            ({L.market}) → {L.addressable} (5% construction) → {L.tigreDura} (5%
            materials). Click a year to refresh KPIs. YoY always compares YTD Jan–
            {MONTHS[ytdM - 1]} vs the same months last year
            {selectedYears.length === 1 && selectedYears[0] === 2026 && mat2026
              ? ` · 2026 ${L.tigreDura} ≈ ${usd(mat2026.som_material_usd)}.`
              : "."}
          </p>
        </div>
      </header>

      <nav className="sticky top-0 z-20 border-b border-[var(--line)] bg-[#071a1f]/95 backdrop-blur">
        <div className="flex gap-1 overflow-x-auto px-3 py-2 md:px-8">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`whitespace-nowrap rounded-full px-4 py-2 text-sm font-medium transition ${
                tab === t.id
                  ? "bg-[var(--gulf)] text-white"
                  : "text-[var(--muted)] hover:bg-white/5 hover:text-[var(--sand)]"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </nav>

      <div className="px-4 py-6 md:px-8">
        {tab === "tom" && (
          <div className="grid gap-4 lg:grid-cols-2">
            <Panel
              title={`YTD Jan–${MONTHS[ytdM - 1]} · same period 2023–2026 · click a year to refresh header KPIs`}
              action={<ModeToggle mode={mode} setMode={setMode} />}
            >
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={ytdCompareChart}>
                    <CartesianGrid stroke="rgba(232,220,200,0.08)" vertical={false} />
                    <XAxis dataKey="year" stroke={SAND} tick={{ fill: SAND, fontSize: 12 }} />
                    <YAxis stroke={SAND} tick={{ fill: SAND, fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        background: "#0c2a32",
                        border: "1px solid rgba(232,220,200,0.2)",
                      }}
                      formatter={(v, name) =>
                        name === "valuationB"
                          ? [`$${Number(v).toFixed(2)}B`, "Value $"]
                          : [num(Number(v)), "Permits"]
                      }
                    />
                    <Bar
                      dataKey={mode === "count" ? "count" : "valuationB"}
                      radius={[2, 2, 0, 0]}
                      cursor="pointer"
                      onClick={(d) => {
                        const y = Number(
                          (d as { payload?: { year?: string | number } })?.payload
                            ?.year ?? (d as { year?: string | number })?.year
                        );
                        if (y) onlyYear(y);
                      }}
                    >
                      {ytdCompareChart.map((r) => (
                        <Cell
                          key={r.year}
                          fill={
                            selectedYears.includes(Number(r.year)) ? GULF : "#35555a"
                          }
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
                {tomYtd
                  .filter((r) => r.year >= 2023)
                  .map((r) => (
                    <button
                      key={r.year}
                      type="button"
                      onClick={() => onlyYear(r.year)}
                      className={`border-t border-[var(--line)] pt-2 text-left hover:bg-white/5 ${
                        selectedYears.includes(r.year) ? "bg-white/10" : ""
                      }`}
                    >
                      <p className="text-[var(--muted)]">{r.year}</p>
                      <p className="text-[var(--sand)]">
                        Permits {num(r.count)}
                      </p>
                      <p className="text-[var(--sand)]">Value {usd(r.valuation)}</p>
                      <p className="text-xs text-[var(--muted)]">
                        YoY permits {pct(r.count_yoy_pct)} · $ {pct(r.valuation_yoy_pct)}
                      </p>
                    </button>
                  ))}
              </div>
            </Panel>

            <Panel
              title={`Monthly ${L.tcm} → Dec (dotted = projection)`}
              action={<ModeToggle mode={mode} setMode={setMode} />}
            >
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={tomMonthlyChart}>
                    <CartesianGrid stroke="rgba(232,220,200,0.08)" vertical={false} />
                    <XAxis
                      dataKey="label"
                      stroke={SAND}
                      tick={{ fill: SAND, fontSize: 10 }}
                      minTickGap={28}
                    />
                    <YAxis stroke={SAND} tick={{ fill: SAND, fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        background: "#0c2a32",
                        border: "1px solid rgba(232,220,200,0.2)",
                      }}
                      formatter={(v) =>
                        mode === "count" ? num(Number(v)) : usd(Number(v))
                      }
                    />
                    <Line
                      type="monotone"
                      dataKey="observed"
                      stroke={GULF}
                      strokeWidth={2}
                      dot={false}
                      connectNulls={false}
                      name="Observed"
                    />
                    <Line
                      type="monotone"
                      dataKey="bridge"
                      stroke={SUN}
                      strokeWidth={2}
                      strokeDasharray="5 5"
                      dot={false}
                      connectNulls
                      name="Projected"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
              <p className="mt-2 text-xs text-[var(--muted)]">
                YE 2026 expected — permits{" "}
                {num(Number(data.tom.projection_count.full_year))} · value{" "}
                {usd(Number(data.tom.projection_valuation.full_year))} (YTD + YTG).
                Chart toggles Permits / Value $; method = same month prior year × trailing
                3m growth.
              </p>
            </Panel>

            <Panel title="YTD growth vs prior year (permits and $)">
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={tomYtd
                      .filter((r) => r.year >= 2024)
                      .map((r) => ({
                        year: String(r.year),
                        permits: r.count_yoy_pct,
                        value: r.valuation_yoy_pct,
                      }))}
                  >
                    <CartesianGrid stroke="rgba(232,220,200,0.08)" vertical={false} />
                    <XAxis dataKey="year" stroke={SAND} tick={{ fill: SAND, fontSize: 12 }} />
                    <YAxis stroke={SAND} tick={{ fill: SAND, fontSize: 11 }} unit="%" />
                    <Tooltip
                      contentStyle={{
                        background: "#0c2a32",
                        border: "1px solid rgba(232,220,200,0.2)",
                      }}
                      formatter={(v) => `${Number(v).toFixed(1)}%`}
                    />
                    <Legend />
                    <Bar dataKey="permits" fill={GULF} name="YoY permits" />
                    <Bar dataKey="value" fill={CORAL} name="YoY value $" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>

            <Panel title="How to read">
              <ul className="space-y-3 text-sm text-[var(--muted)]">
                <li>
                  Always compare{" "}
                  <span className="text-[var(--sand)]">YTD vs same period</span> (Jan–
                  {MONTHS[ytdM - 1]}), not incomplete full years.
                </li>
                <li>
                  2026 YTD permits {pct(latestTomYtd?.count_yoy_pct)} vs 2025; value{" "}
                  {pct(latestTomYtd?.valuation_yoy_pct)}. Declared $ ≥$1B are capped
                  (Miami-Dade glitches).
                </li>
                <li>
                  Use Permits / Value $ on both the YTD bars and the monthly projection
                  line.
                </li>
              </ul>
            </Panel>
          </div>
        )}

        {tab === "sam" && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm text-[var(--sand)]">
                  {L.marketShort} · {L.market}
                </p>
                <p className="text-xs text-[var(--muted)]">
                  Scope {headerScopeLabel}
                  {marketTabYtd
                    ? ` · YTD Jan–${MONTHS[ytdM - 1]} growth vs prior year`
                    : " · select one year to see YTD YoY by category"}
                </p>
              </div>
              <YearChips
                years={yearOptions}
                selected={selectedYears}
                onToggle={toggleYear}
                onOnly={onlyYear}
              />
            </div>

            <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
              <Kpi
                label="Permits"
                value={num(
                  marketTabYtd ? marketTabYtd.count : filteredShare.sam_count
                )}
                sub={
                  marketTabYtd
                    ? `YTD YoY ${pct(marketTabYtd.count_yoy_pct)}`
                    : `${pctPlain(filteredShare.sam_share_count_pct)} of TCM permits`
                }
              />
              <Kpi
                label={`${L.marketShort} $`}
                value={usd(
                  marketTabYtd ? marketTabYtd.valuation : filteredShare.sam_valuation
                )}
                sub={
                  marketTabYtd
                    ? `YTD YoY ${pct(marketTabYtd.valuation_yoy_pct)}`
                    : `${pctPlain(filteredShare.sam_share_valuation_pct)} of TCM $`
                }
              />
              <Kpi
                label={L.addressable}
                value={usd(
                  marketTabYtd
                    ? marketTabYtd.valuation * 0.05
                    : filteredShare.som_usd
                )}
                sub="5% of Total Market construction $"
              />
              <Kpi
                label={L.tigreDura}
                value={usd(
                  marketTabYtd
                    ? categoryGrowthRows.reduce((s, r) => s + r.tigreDura, 0)
                    : materialsPotentialSelected
                )}
                sub="5% market share · materials only"
              />
              <Kpi
                label={
                  marketTabYtd
                    ? `YTD YoY vs ${marketTabYtd.year - 1}`
                    : "YTD YoY"
                }
                value={
                  marketTabYtd
                    ? pct(marketTabYtd.valuation_yoy_pct)
                    : pct(latestSamYtd?.valuation_yoy_pct)
                }
                sub={`Jan–${MONTHS[ytdM - 1]} Total Market $ · permits ${pct(
                  marketTabYtd?.count_yoy_pct ?? latestSamYtd?.count_yoy_pct
                )}`}
              />
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <Panel
                title={`${L.marketShort} by year · click to filter`}
                action={<ModeToggle mode={mode} setMode={setMode} />}
              >
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={samYtd
                        .filter((r) => r.year >= 2023)
                        .map((r) => ({
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
                        onClick={(d) => {
                          const y = Number(
                            (d as { payload?: { year?: number } })?.payload?.year ??
                              (d as { year?: number })?.year
                          );
                          if (y) onlyYear(y);
                        }}
                      >
                        {samYtd
                          .filter((r) => r.year >= 2023)
                          .map((r) => (
                            <Cell
                              key={r.year}
                              fill={
                                selectedYears.includes(r.year) ? MANGROVE : "#35555a"
                              }
                            />
                          ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <p className="mt-2 text-xs text-[var(--muted)]">
                  Bars are YTD Jan–{MONTHS[ytdM - 1]} (same period every year).
                </p>
              </Panel>

              <Panel title={`YTD growth by category · ${headerScopeLabel}`}>
                {!marketTabYtd ? (
                  <p className="text-sm text-[var(--muted)]">
                    Select a single year to see category YoY (permits, value,{" "}
                    {L.tigreDura}).
                  </p>
                ) : (
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={categoryGrowthRows.map((r) => ({
                          name: categoryLabel(r.category).replace(
                            "New residential plumbing",
                            "New resid. plumbing"
                          ),
                          permits: r.count_yoy_pct,
                          value: r.valuation_yoy_pct,
                          tigre: r.tigre_yoy_pct,
                        }))}
                        layout="vertical"
                        margin={{ left: 8, right: 8 }}
                      >
                        <CartesianGrid stroke="rgba(232,220,200,0.08)" horizontal={false} />
                        <XAxis
                          type="number"
                          stroke={SAND}
                          tick={{ fill: SAND, fontSize: 11 }}
                          unit="%"
                        />
                        <YAxis
                          type="category"
                          dataKey="name"
                          width={120}
                          stroke={SAND}
                          tick={{ fill: SAND, fontSize: 10 }}
                        />
                        <Tooltip
                          contentStyle={{
                            background: "#0c2a32",
                            border: "1px solid rgba(232,220,200,0.2)",
                          }}
                          formatter={(v) => `${Number(v).toFixed(1)}%`}
                        />
                        <Legend />
                        <Bar dataKey="permits" fill={GULF} name="Permits YoY" />
                        <Bar dataKey="value" fill={CORAL} name="Value $ YoY" />
                        <Bar dataKey="tigre" fill={SUN} name="Tigre × Dura YoY" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </Panel>

              <Panel
                title={`Categories · ${headerScopeLabel}${
                  marketTabYtd ? ` · YTD Jan–${MONTHS[ytdM - 1]}` : ""
                }`}
              >
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[880px] text-left text-sm">
                    <thead>
                      <tr className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
                        <th className="pb-2 font-medium">Category</th>
                        <th className="pb-2 font-medium">Permits</th>
                        <th className="pb-2 font-medium">YTD YoY #</th>
                        <th className="pb-2 font-medium">{L.marketShort} $</th>
                        <th className="pb-2 font-medium">YTD YoY $</th>
                        <th className="pb-2 font-medium">{L.addressable}</th>
                        <th className="pb-2 font-medium">{L.tigreDura}</th>
                        <th className="pb-2 font-medium">YTD YoY mat.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {categoryGrowthRows.map((r) => (
                        <tr key={r.category} className="table-row">
                          <td className="py-2.5 text-[var(--sand)]">
                            {categoryLabel(r.category)}
                          </td>
                          <td className="py-2.5">{num(r.count)}</td>
                          <td className="py-2.5">{pct(r.count_yoy_pct)}</td>
                          <td className="py-2.5">{usd(r.valuation)}</td>
                          <td className="py-2.5">{pct(r.valuation_yoy_pct)}</td>
                          <td className="py-2.5">{usd(r.addressable)}</td>
                          <td className="py-2.5 text-[var(--sun)]">{usd(r.tigreDura)}</td>
                          <td className="py-2.5 text-[var(--sun)]">
                            {pct(r.tigre_yoy_pct)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="mt-2 text-xs text-[var(--muted)]">
                  Growth columns use same-period YTD only. Multi-year scope aggregates
                  levels without YoY.
                </p>
              </Panel>

              <Panel title={`Materials vs labor · ${L.marketShort}`}>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={filteredMatLab}>
                      <CartesianGrid stroke="rgba(232,220,200,0.08)" vertical={false} />
                      <XAxis dataKey="year" stroke={SAND} tick={{ fill: SAND, fontSize: 12 }} />
                      <YAxis stroke={SAND} tick={{ fill: SAND, fontSize: 11 }} />
                      <Tooltip
                        contentStyle={{
                          background: "#0c2a32",
                          border: "1px solid rgba(232,220,200,0.2)",
                        }}
                        formatter={(v) => usd(Number(v))}
                      />
                      <Legend />
                      <Bar dataKey="material_usd" stackId="a" fill={GULF} name="Materials" />
                      <Bar dataKey="labor_usd" stackId="a" fill={CORAL} name="Labor / other" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Panel>
            </div>
          </div>
        )}

        {tab === "pipeline" && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="inline-flex rounded-full border border-[var(--line)] p-0.5 text-xs">
                {([30, 60] as const).map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => {
                      setPipelineDays(d);
                      setPipelineCounty(null);
                    }}
                    className={`rounded-full px-3 py-1.5 ${
                      pipelineDays === d
                        ? "bg-[var(--gulf)] text-white"
                        : "text-[var(--muted)]"
                    }`}
                  >
                    Last {d} days
                  </button>
                ))}
              </div>
              <p className="text-xs text-[var(--muted)]">
                {pipe.start} → {pipe.end} · chase window for sales · focus on materials
                potential
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Kpi label="Total Market permits" value={num(pipe.sam_count)} />
              <Kpi label="Total Market $" value={usd(pipe.sam_valuation)} />
              <Kpi label={L.addressable} value={usd(pipe.som_usd)} />
              <Kpi
                label={L.tigreDura}
                value={usd(pipe.som_material_usd)}
                sub={`${pipelineDays}d materials @ 5%`}
              />
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <Panel title={`Click a county · Tigre × Dura Potential (${pipelineDays}d)`}>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="text-[10px] uppercase text-[var(--muted)]">
                        <th className="pb-2">#</th>
                        <th className="pb-2">County</th>
                        <th className="pb-2">Permits</th>
                        <th className="pb-2">Total Market $</th>
                        <th className="pb-2">Tigre × Dura Potential</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pipe.by_county.slice(0, 12).map((c, i) => (
                        <tr
                          key={c.county}
                          className={`table-row cursor-pointer ${
                            pipelineCounty === c.county ? "bg-white/10" : ""
                          }`}
                          onClick={() =>
                            setPipelineCounty((prev) =>
                              prev === c.county ? null : c.county
                            )
                          }
                        >
                          <td className="py-2 text-[var(--muted)]">{i + 1}</td>
                          <td className="py-2 text-[var(--sand)]">{c.county}</td>
                          <td className="py-2">{num(c.sam_count)}</td>
                          <td className="py-2">{usd(c.sam_valuation)}</td>
                          <td className="py-2 text-[var(--sun)]">
                            {usd(c.som_material_usd)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>

              <Panel
                title={
                  pipelineCounty
                    ? `${pipelineCounty} · categories by Tigre × Dura Potential`
                    : "Select a county to see categories"
                }
              >
                {pipelineCounty && pipelineCountyCats.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead>
                        <tr className="text-[10px] uppercase text-[var(--muted)]">
                          <th className="pb-2">Category</th>
                          <th className="pb-2">Permits</th>
                          <th className="pb-2">Total Market $</th>
                          <th className="pb-2">Tigre × Dura Potential</th>
                        </tr>
                      </thead>
                      <tbody>
                        {pipelineCountyCats.map((c) => (
                          <tr key={c.category} className="table-row">
                            <td className="py-2 text-[var(--sand)]">
                              {categoryLabel(c.category)}
                            </td>
                            <td className="py-2">{num(c.sam_count)}</td>
                            <td className="py-2">{usd(c.sam_valuation)}</td>
                            <td className="py-2 text-[var(--sun)]">
                              {usd(c.som_material_usd)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="space-y-2 text-sm text-[var(--muted)]">
                    <p>Click Miami-Dade (or any county) on the left to drill categories.</p>
                    <p className="text-[var(--sand)]">Statewide categories ({pipelineDays}d):</p>
                    <table className="w-full text-left text-sm">
                      <thead>
                        <tr className="text-[10px] uppercase text-[var(--muted)]">
                          <th className="pb-2">Category</th>
                          <th className="pb-2">Permits</th>
                          <th className="pb-2">Tigre × Dura Potential</th>
                        </tr>
                      </thead>
                      <tbody>
                        {pipe.by_category.map((c) => (
                          <tr key={c.category} className="table-row">
                            <td className="py-2 text-[var(--sand)]">
                              {categoryLabel(c.category)}
                            </td>
                            <td className="py-2">{num(c.sam_count)}</td>
                            <td className="py-2 text-[var(--sun)]">
                              {usd(c.som_material_usd)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Panel>

              <Panel title="Who to call · contractors (Tigre × Dura Potential)">
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[640px] text-left text-sm">
                    <thead>
                      <tr className="text-[10px] uppercase text-[var(--muted)]">
                        <th className="pb-2">#</th>
                        <th className="pb-2">Contractor</th>
                        <th className="pb-2">Permits</th>
                        <th className="pb-2">Tigre × Dura Potential</th>
                        <th className="pb-2">Counties</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pipe.by_contractor
                        .filter((c) =>
                          pipelineCounty
                            ? c.counties.split(", ").includes(pipelineCounty)
                            : true
                        )
                        .slice(0, 20)
                        .map((c, i) => (
                          <tr key={c.contractor_name} className="table-row">
                            <td className="py-2 text-[var(--muted)]">{i + 1}</td>
                            <td className="py-2 text-[var(--sand)]">{c.contractor_name}</td>
                            <td className="py-2">{num(c.permits)}</td>
                            <td className="py-2 text-[var(--sun)]">
                              {usd(c.som_material_usd)}
                            </td>
                            <td className="max-w-[140px] truncate py-2 text-[var(--muted)]">
                              {c.counties}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
                <p className="mt-2 text-xs text-[var(--muted)]">{data.pipeline.note}</p>
              </Panel>
            </div>
          </div>
        )}

        {tab === "regions" && (
          <div className="grid gap-4 lg:grid-cols-5">
            <div className="lg:col-span-3">
              <Panel title={`Map · ${L.tigreDura} (5% materials only)`}>
                <CountyMap
                  counties={data.regions.counties}
                  selected={selectedCounty}
                  onSelect={(c) => {
                    setSelectedCounty(c);
                    setMiamiOpen(c === "Miami-Dade");
                  }}
                  mode="som_material_usd"
                />
                <p className="mt-2 text-xs text-[var(--muted)]">
                  Color = Tigre × Dura Potential. Click a county (try Miami-Dade) for category
                  drill. Coverage: {data.regions.counties.length} counties.
                </p>
              </Panel>
            </div>
            <div className="space-y-4 lg:col-span-2">
              <Panel title={selectedCounty ? selectedCounty : "Select a county"}>
                {selectedCountyRow ? (
                  <div className="space-y-3 text-sm">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <p className="text-[var(--muted)]">Total Market permits</p>
                        <p className="stat-value text-2xl text-[var(--sand)]">
                          {num(selectedCountyRow.sam_count)}
                        </p>
                      </div>
                      <div>
                        <p className="text-[var(--muted)]">Total Market $</p>
                        <p className="stat-value text-2xl text-[var(--sand)]">
                          {usd(selectedCountyRow.sam_valuation)}
                        </p>
                      </div>
                      <div>
                        <p className="text-[var(--muted)]">{L.addressable}</p>
                        <p className="stat-value text-2xl text-[var(--foam)]">
                          {usd(selectedCountyRow.som_usd)}
                        </p>
                      </div>
                      <div>
                        <p className="text-[var(--muted)]">{L.tigreDura}</p>
                        <p className="stat-value text-2xl text-[var(--sun)]">
                          {usd(selectedCountyRow.som_material_usd || 0)}
                        </p>
                      </div>
                    </div>
                    {regionCountyCats.length > 0 && (
                      <div className="border-t border-[var(--line)] pt-3">
                        <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--muted)]">
                          Categories · Tigre × Dura Potential
                        </p>
                        <table className="w-full text-left text-sm">
                          <thead>
                            <tr className="text-[10px] uppercase text-[var(--muted)]">
                              <th className="pb-1">Category</th>
                              <th>Permits</th>
                              <th>Mat. pot.</th>
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
                                  {usd(r.som_material_usd)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                    {selectedCounty === "Miami-Dade" && (
                      <button
                        type="button"
                        className="pill-cta mt-2 text-sm"
                        onClick={() => setMiamiOpen((v) => !v)}
                      >
                        {miamiOpen ? "Hide" : "Open"} Miami-Dade mesoregions
                      </button>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-[var(--muted)]">
                    Click the map to see Total Market and Tigre × Dura Potential by county.
                  </p>
                )}
              </Panel>

              <Panel title={`Top counties · ${L.tigreDura}`}>
                <div className="max-h-64 space-y-1 overflow-y-auto text-sm">
                  {[...data.regions.counties]
                    .sort(
                      (a, b) =>
                        (b.som_material_usd || 0) - (a.som_material_usd || 0)
                    )
                    .slice(0, 12)
                    .map((c) => (
                      <button
                        key={c.county}
                        type="button"
                        onClick={() => {
                          setSelectedCounty(c.county);
                          setMiamiOpen(c.county === "Miami-Dade");
                        }}
                        className={`flex w-full items-center justify-between rounded px-2 py-1.5 text-left hover:bg-white/5 ${
                          selectedCounty === c.county ? "bg-white/10" : ""
                        }`}
                      >
                        <span className="text-[var(--sand)]">{c.county}</span>
                        <span className="text-[var(--muted)]">
                          {usd(c.som_material_usd || 0)}
                        </span>
                      </button>
                    ))}
                </div>
              </Panel>
            </div>

            {miamiOpen && (
              <div className="lg:col-span-5">
                <Panel title="Miami-Dade · mesoregion / jurisdiction drill">
                  <p className="mb-3 text-xs text-[var(--muted)]">
                    {data.regions.miami_dade.coverage_note}
                  </p>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <p className="mb-2 text-sm text-[var(--sand)]">Layers (jurisdiction)</p>
                      <table className="w-full text-left text-sm">
                        <thead>
                          <tr className="text-[10px] uppercase text-[var(--muted)]">
                            <th className="pb-1">Layer</th>
                            <th>Market</th>
                            <th>Market $</th>
                            <th>Mat. pot.</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.regions.miami_dade.jurisdictions.map((j) => (
                            <tr key={j.jurisdiction_id} className="table-row">
                              <td className="py-2 text-[var(--sand)]">
                                {j.jurisdiction_id === "fl_miami_city"
                                  ? "City of Miami"
                                  : "County Hub (unincorp.)"}
                              </td>
                              <td>{num(j.sam_count)}</td>
                              <td>{usd(j.sam_valuation)}</td>
                              <td className="text-[var(--sun)]">
                                {usd(j.som_material_usd || 0)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div>
                      <p className="mb-2 text-sm text-[var(--sand)]">
                        Mesoregions (address parse)
                      </p>
                      <div className="max-h-72 overflow-y-auto">
                        <table className="w-full text-left text-sm">
                          <thead>
                            <tr className="text-[10px] uppercase text-[var(--muted)]">
                              <th className="pb-1">Area</th>
                              <th>Market</th>
                              <th>Market $</th>
                              <th>Mat. pot.</th>
                            </tr>
                          </thead>
                          <tbody>
                            {data.regions.miami_dade.mesoregions.map((a) => (
                              <tr key={a.area} className="table-row">
                                <td className="py-2 text-[var(--sand)]">{a.area}</td>
                                <td>{num(a.sam_count)}</td>
                                <td>{usd(a.sam_valuation)}</td>
                                <td className="text-[var(--sun)]">
                                  {usd(a.som_material_usd || 0)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                </Panel>
              </div>
            )}
          </div>
        )}

        {tab === "contractors" && (
          <div className="grid gap-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="inline-flex rounded-full border border-[var(--line)] p-0.5 text-xs">
                {(
                  [
                    ["near", data.contractors.near_term_label],
                    ["ytd", `YTD Jan–${MONTHS[ytdM - 1]}`],
                  ] as const
                ).map(([id, label]) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setContractorScope(id)}
                    className={`rounded-full px-3 py-1.5 ${
                      contractorScope === id
                        ? "bg-[var(--gulf)] text-white"
                        : "text-[var(--muted)]"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <div className="inline-flex rounded-full border border-[var(--line)] p-0.5 text-xs">
                {(
                  [
                    ["permits", "Rank by # permits"],
                    ["valuation", "Rank by $"],
                  ] as const
                ).map(([id, label]) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setContractorRank(id)}
                    className={`rounded-full px-3 py-1.5 ${
                      contractorRank === id
                        ? "bg-[var(--gulf)] text-white"
                        : "text-[var(--muted)]"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <p className="text-xs text-[var(--muted)]">
                Named coverage: {pctPlain(data.contractors.coverage.sam_coverage_pct)}
                {data.valuation_quality
                  ? ` · ${data.valuation_quality.rows_ge_1b} permits ≥$1B imputed`
                  : ""}
              </p>
            </div>

            <Panel
              title={
                contractorScope === "near"
                  ? `Who drives demand now · ${data.contractors.near_term_label}`
                  : `YTD · who placed the most ${L.marketShort} projects`
              }
            >
              <p className="mb-3 text-xs text-[var(--muted)]">{data.contractors.notes}</p>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead>
                    <tr className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
                      <th className="pb-2">#</th>
                      <th className="pb-2">Contractor</th>
                      <th className="pb-2">Permits</th>
                      <th className="pb-2">Value $</th>
                      <th className="pb-2">Counties</th>
                      <th className="pb-2">Categories</th>
                    </tr>
                  </thead>
                  <tbody>
                    {contractorList.slice(0, 30).map((c, i) => (
                      <tr key={c.contractor_name} className="table-row">
                        <td className="py-2 text-[var(--muted)]">{i + 1}</td>
                        <td className="py-2 text-[var(--sand)]">{c.contractor_name}</td>
                        <td className="py-2">{num(c.permits)}</td>
                        <td className="py-2">{usd(c.valuation)}</td>
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
            </Panel>
          </div>
        )}
      </div>

      <footer className="border-t border-[var(--line)] px-5 py-6 text-xs text-[var(--muted)] md:px-8">
        Tigre × Dura · Permit Demand Engine · {L.tcm} / {L.marketShort} /{" "}
        {L.addressable} / {L.tigreDura} · YoY = YTD Jan–{MONTHS[ytdM - 1]} · Materials
        model is calibratable
      </footer>
    </main>
  );
}
