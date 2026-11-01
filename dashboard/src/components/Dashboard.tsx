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

const TABS: { id: TabId; label: string }[] = [
  { id: "tom", label: "TOM" },
  { id: "sam", label: "SAM + SOM" },
  { id: "pipeline", label: "Pipeline 30/60d" },
  { id: "regions", label: "Regiões / Mapa" },
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
        Anos
      </span>
      {years.map((y) => {
        const on = selected.includes(y);
        return (
          <button
            key={y}
            type="button"
            title="Clique = só este ano · Shift/Ctrl+clique via botão para multi"
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
        Todos
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
          ["count", "Counts"],
          ["valuation", "Valor $"],
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

  const u = data.universe;
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
    return [...map.values()].sort((a, b) => b.valuation - a.valuation);
  }, [data.sam_som.by_category_year, selectedYears]);

  const filteredMatLab = useMemo(
    () =>
      data.sam_som.material_labor_annual.filter((r) =>
        selectedYears.includes(r.year)
      ),
    [data.sam_som.material_labor_annual, selectedYears]
  );

  const pipe = pipelineDays === 30 ? data.pipeline.d30 : data.pipeline.d60;

  const tomMonthlyChart = useMemo(() => {
    const series =
      mode === "count"
        ? data.tom.monthly_count_with_projection
        : data.tom.monthly_valuation_with_projection;
    // last 36 months for readability
    const recent = series.filter((p) => p.year >= 2023);
    return recent.map((p) => ({
      label: ymLabel(p.year, p.month),
      observed: p.kind === "observed" ? p.value : null,
      projected: p.kind === "projected" ? p.value : null,
      // connect: last observed also as projected start for visual continuity
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
      {/* Compact brand bar + KPIs — not a long marketing scroll */}
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
                Florida Permit Demand · as of {data.as_of} · YTD Jan–{MONTHS[ytdM - 1]}
              </p>
            </div>
            <ModeToggle mode={mode} setMode={setMode} />
          </div>
          <div className="mt-6 grid grid-cols-2 gap-6 lg:grid-cols-5">
            <Kpi label="TOM" value={num(u.tom)} sub={usd(u.tom_valuation)} />
            <Kpi
              label="SAM / TOM"
              value={pctPlain(u.sam_share_count_pct)}
              sub={`${pctPlain(u.sam_share_valuation_pct)} do $`}
            />
            <Kpi label="SAM $" value={usd(u.sam_valuation)} sub={`${num(u.sam)} permits`} />
            <Kpi label="SOM 5%" value={usd(u.som_usd)} sub="do SAM addressable" />
            <Kpi
              label={`TOM YTD ${latestTomYtd?.year} vs LY`}
              value={pct(latestTomYtd?.count_yoy_pct)}
              sub={`$ ${pct(latestTomYtd?.valuation_yoy_pct)}`}
            />
          </div>
        </div>
      </header>

      {/* Tab nav */}
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
              title={`YTD Jan–${MONTHS[ytdM - 1]} · mesmo período 2023–2026 (${mode === "count" ? "counts" : "valor"})`}
            >
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={ytdCompareChart}>
                    <CartesianGrid stroke="rgba(232,220,200,0.08)" vertical={false} />
                    <XAxis dataKey="year" stroke={SAND} tick={{ fill: SAND, fontSize: 12 }} />
                    <YAxis stroke={SAND} tick={{ fill: SAND, fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{ background: "#0c2a32", border: "1px solid rgba(232,220,200,0.2)" }}
                      formatter={(v, name) =>
                        name === "valuationB"
                          ? [`$${Number(v).toFixed(2)}B`, "Valor"]
                          : [num(Number(v)), "Counts"]
                      }
                    />
                    <Bar
                      dataKey={mode === "count" ? "count" : "valuationB"}
                      fill={GULF}
                      radius={[2, 2, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
                {tomYtd
                  .filter((r) => r.year >= 2023)
                  .map((r) => (
                    <div key={r.year} className="border-t border-[var(--line)] pt-2">
                      <p className="text-[var(--muted)]">{r.year}</p>
                      <p className="text-[var(--sand)]">
                        {mode === "count" ? num(r.count) : usd(r.valuation)}
                      </p>
                      <p className="text-xs text-[var(--muted)]">
                        YoY {mode === "count" ? pct(r.count_yoy_pct) : pct(r.valuation_yoy_pct)}
                      </p>
                    </div>
                  ))}
              </div>
            </Panel>

            <Panel title="Mensal TOM → Dez (linha pontilhada = projeção)">
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
                      contentStyle={{ background: "#0c2a32", border: "1px solid rgba(232,220,200,0.2)" }}
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
                      name="Observado"
                    />
                    <Line
                      type="monotone"
                      dataKey="bridge"
                      stroke={SUN}
                      strokeWidth={2}
                      strokeDasharray="5 5"
                      dot={false}
                      connectNulls
                      name="Projetado"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
              <p className="mt-2 text-xs text-[var(--muted)]">
                YE 2026 esperado:{" "}
                {mode === "count"
                  ? num(Number(data.tom.projection_count.full_year))
                  : usd(Number(data.tom.projection_valuation.full_year))}{" "}
                (YTD + YTG). Método: mesmo mês do ano anterior × crescimento trailing 3m.
              </p>
            </Panel>

            <Panel title="Crescimento YTD vs ano anterior (counts e $)">
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={tomYtd
                      .filter((r) => r.year >= 2024)
                      .map((r) => ({
                        year: String(r.year),
                        counts: r.count_yoy_pct,
                        valor: r.valuation_yoy_pct,
                      }))}
                  >
                    <CartesianGrid stroke="rgba(232,220,200,0.08)" vertical={false} />
                    <XAxis dataKey="year" stroke={SAND} tick={{ fill: SAND, fontSize: 12 }} />
                    <YAxis stroke={SAND} tick={{ fill: SAND, fontSize: 11 }} unit="%" />
                    <Tooltip
                      contentStyle={{ background: "#0c2a32", border: "1px solid rgba(232,220,200,0.2)" }}
                      formatter={(v) => `${Number(v).toFixed(1)}%`}
                    />
                    <Legend />
                    <Bar dataKey="counts" fill={GULF} name="YoY counts" />
                    <Bar dataKey="valor" fill={CORAL} name="YoY $" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>

            <Panel title="Leitura">
              <ul className="space-y-3 text-sm text-[var(--muted)]">
                <li>
                  Compare sempre <span className="text-[var(--sand)]">YTD vs mesmo período</span>{" "}
                  (Jan–{MONTHS[ytdM - 1]}), não ano cheio incompleto.
                </li>
                <li>
                  2026 counts YTD {pct(latestTomYtd?.count_yoy_pct)} vs 2025; valor{" "}
                  {pct(latestTomYtd?.valuation_yoy_pct)} — $ sensível a outliers Miami-Dade.
                </li>
                <li>
                  Projeção Nov–Dez em pontilhado no gráfico mensal; ajuste o toggle Counts / Valor $.
                </li>
              </ul>
            </Panel>
          </div>
        )}

        {tab === "sam" && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <YearChips
                years={yearOptions}
                selected={selectedYears}
                onToggle={toggleYear}
                onOnly={onlyYear}
              />
              <p className="text-xs text-[var(--muted)]">
                Clique num ano = só ele · Ctrl/Cmd+clique = soma anos · filtrando % e categorias
              </p>
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <Panel
                title={`SAM vs TOM · ${selectedYears.join(" + ")}`}
              >
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.14em] text-[var(--muted)]">
                      Counts
                    </p>
                    <p className="stat-value text-4xl text-[var(--sand)]">
                      {pctPlain(filteredShare.sam_share_count_pct)}
                    </p>
                    <p className="text-sm text-[var(--muted)]">
                      {num(filteredShare.sam_count)} de {num(filteredShare.tom_count)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.14em] text-[var(--muted)]">
                      Valor $
                    </p>
                    <p className="stat-value text-4xl text-[var(--sun)]">
                      {pctPlain(filteredShare.sam_share_valuation_pct)}
                    </p>
                    <p className="text-sm text-[var(--muted)]">
                      SAM $ {usd(filteredShare.sam_valuation)}
                    </p>
                  </div>
                </div>
                <div className="mt-6 border-t border-[var(--line)] pt-4">
                  <p className="text-xs uppercase tracking-[0.14em] text-[var(--muted)]">
                    SOM @ 5% (anos selecionados)
                  </p>
                  <p className="stat-value mt-1 text-3xl text-[var(--foam)]">
                    {usd(filteredShare.som_usd)}
                  </p>
                  <p className="mt-1 text-sm text-[var(--muted)]">
                    SOM material (soma categorias):{" "}
                    {usd(
                      filteredCategories.reduce((s, r) => s + r.som_material_usd, 0)
                    )}
                  </p>
                </div>
              </Panel>

              <Panel
                title="Clique nas barras de ano para filtrar"
                action={<ModeToggle mode={mode} setMode={setMode} />}
              >
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={data.sam_som.share_by_year
                        .filter((r) => r.year >= 2023)
                        .map((r) => ({
                          year: r.year,
                          label: String(r.year),
                          count: r.sam_count,
                          valuationB: r.sam_valuation / 1e9,
                          active: selectedYears.includes(r.year),
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
                        {data.sam_som.share_by_year
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
                  YTD ref {latestSamYtd?.year}: YoY counts {pct(latestSamYtd?.count_yoy_pct)} · $
                  {pct(latestSamYtd?.valuation_yoy_pct)}
                </p>
              </Panel>

              <Panel
                title={`Categorias · ${selectedYears.join(" + ")} (permits, $, SOM, material)`}
              >
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[720px] text-left text-sm">
                    <thead>
                      <tr className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
                        <th className="pb-2 font-medium">Categoria</th>
                        <th className="pb-2 font-medium">Permits</th>
                        <th className="pb-2 font-medium">Valor obra</th>
                        <th className="pb-2 font-medium">SOM 5%</th>
                        <th className="pb-2 font-medium">Material</th>
                        <th className="pb-2 font-medium">SOM material</th>
                        <th className="pb-2 font-medium">Mão de obra</th>
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
                          <td className="py-2.5 text-[var(--sun)]">{usd(r.som_usd)}</td>
                          <td className="py-2.5">{usd(r.material_usd)}</td>
                          <td className="py-2.5 text-[var(--sun)]">
                            {usd(r.som_material_usd)}
                          </td>
                          <td className="py-2.5">{usd(r.labor_usd)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>

              <Panel title="Material vs mão de obra · anos selecionados">
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
                      <Bar dataKey="material_usd" stackId="a" fill={GULF} name="Material" />
                      <Bar dataKey="labor_usd" stackId="a" fill={CORAL} name="Mão de obra" />
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
                    onClick={() => setPipelineDays(d)}
                    className={`rounded-full px-3 py-1.5 ${
                      pipelineDays === d
                        ? "bg-[var(--gulf)] text-white"
                        : "text-[var(--muted)]"
                    }`}
                  >
                    Últimos {d} dias
                  </button>
                ))}
              </div>
              <p className="text-xs text-[var(--muted)]">
                {pipe.start} → {pipe.end} · para a equipe comercial correr atrás agora
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Kpi label="SAM permits" value={num(pipe.sam_count)} />
              <Kpi label="SAM $" value={usd(pipe.sam_valuation)} />
              <Kpi label="SOM 5%" value={usd(pipe.som_usd)} />
              <Kpi
                label="SOM material 5%"
                value={usd(pipe.som_material_usd)}
                sub="potencial materiais"
              />
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <Panel title={`Onde correr · top condados (SOM material ${pipelineDays}d)`}>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="text-[10px] uppercase text-[var(--muted)]">
                        <th className="pb-2">#</th>
                        <th className="pb-2">Condado</th>
                        <th className="pb-2">Permits</th>
                        <th className="pb-2">SAM $</th>
                        <th className="pb-2">SOM material</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pipe.by_county.slice(0, 12).map((c, i) => (
                        <tr key={c.county} className="table-row">
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
              <Panel title="Categorias no pipeline">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="text-[10px] uppercase text-[var(--muted)]">
                        <th className="pb-2">Categoria</th>
                        <th className="pb-2">Permits</th>
                        <th className="pb-2">SOM material</th>
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
              </Panel>
              <Panel title="Quem puxar · contractors no pipeline (SOM material)">
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[640px] text-left text-sm">
                    <thead>
                      <tr className="text-[10px] uppercase text-[var(--muted)]">
                        <th className="pb-2">#</th>
                        <th className="pb-2">Contractor</th>
                        <th className="pb-2">Permits</th>
                        <th className="pb-2">SOM material</th>
                        <th className="pb-2">Condados</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pipe.by_contractor.slice(0, 20).map((c, i) => (
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
              <Panel title="Mapa FL · potencial SOM material (5% do material estimado)">
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
                  Cor = SOM material. Clique Miami-Dade para abrir mesorregiões. Cobertura:{" "}
                  {data.regions.counties.length} condados.
                </p>
              </Panel>
            </div>
            <div className="space-y-4 lg:col-span-2">
              <Panel title={selectedCounty ? selectedCounty : "Selecione um condado"}>
                {selectedCountyRow ? (
                  <div className="space-y-3 text-sm">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <p className="text-[var(--muted)]">SAM permits</p>
                        <p className="stat-value text-2xl text-[var(--sand)]">
                          {num(selectedCountyRow.sam_count)}
                        </p>
                      </div>
                      <div>
                        <p className="text-[var(--muted)]">SAM $</p>
                        <p className="stat-value text-2xl text-[var(--sand)]">
                          {usd(selectedCountyRow.sam_valuation)}
                        </p>
                      </div>
                      <div>
                        <p className="text-[var(--muted)]">SOM 5% obra</p>
                        <p className="stat-value text-2xl text-[var(--sun)]">
                          {usd(selectedCountyRow.som_usd)}
                        </p>
                      </div>
                      <div>
                        <p className="text-[var(--muted)]">SOM material 5%</p>
                        <p className="stat-value text-2xl text-[var(--sun)]">
                          {usd(selectedCountyRow.som_material_usd || 0)}
                        </p>
                      </div>
                    </div>
                    {selectedCounty === "Miami-Dade" && (
                      <button
                        type="button"
                        className="pill-cta mt-2 text-sm"
                        onClick={() => setMiamiOpen((v) => !v)}
                      >
                        {miamiOpen ? "Fechar" : "Abrir"} mesorregiões Miami-Dade
                      </button>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-[var(--muted)]">
                    Clique no mapa para ver SAM / SOM material do condado.
                  </p>
                )}
              </Panel>

              <Panel title="Top condados · SOM material">
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
                <Panel title="Miami-Dade · drill mesorregião / jurisdição">
                  <p className="mb-3 text-xs text-[var(--muted)]">
                    {data.regions.miami_dade.coverage_note}
                  </p>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <p className="mb-2 text-sm text-[var(--sand)]">Camadas (jurisdição)</p>
                      <table className="w-full text-left text-sm">
                        <thead>
                          <tr className="text-[10px] uppercase text-[var(--muted)]">
                            <th className="pb-1">Camada</th>
                            <th>SAM</th>
                            <th>SAM $</th>
                            <th>SOM mat.</th>
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
                        Mesorregiões (parse de endereço)
                      </p>
                      <div className="max-h-72 overflow-y-auto">
                        <table className="w-full text-left text-sm">
                          <thead>
                            <tr className="text-[10px] uppercase text-[var(--muted)]">
                              <th className="pb-1">Área</th>
                              <th>SAM</th>
                              <th>SAM $</th>
                              <th>SOM mat.</th>
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
                        ? "bg-[var(--coral,#c45c3e)] bg-[var(--gulf)] text-white"
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
                    ["permits", "Rank por # permits"],
                    ["valuation", "Rank por $"],
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
                Cobertura SAM com nome: {pctPlain(data.contractors.coverage.sam_coverage_pct)}
              </p>
            </div>

            <Panel
              title={
                contractorScope === "near"
                  ? `Quem gerar demanda agora · ${data.contractors.near_term_label}`
                  : `YTD · quem mais colocou projetos SAM`
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
                      <th className="pb-2">Valor</th>
                      <th className="pb-2">Condados</th>
                      <th className="pb-2">Categorias</th>
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
        Tigre × Dura · Permit Demand Engine · {data.definitions.YTD} · Material/labor = premissa
        calibrável
      </footer>
    </main>
  );
}
