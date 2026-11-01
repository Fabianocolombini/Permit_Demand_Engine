"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Metrics } from "@/lib/types";
import {
  categoryLabel,
  num,
  pct,
  pctPlain,
  segmentLabel,
  usd,
  ymLabel,
} from "@/lib/format";

const GULF = "#0e7c86";
const MANGROVE = "#1f6b4f";
const CORAL = "#c45c3e";
const SUN = "#e2b14a";
const SAND = "#e8dcc8";
const SEG_COLORS: Record<string, string> = {
  new_residential_plumbing: GULF,
  plumbing_repipe_remodel: "#3aa6b0",
  pool_spa: CORAL,
  irrigation: MANGROVE,
  other: "#5a7076",
};

function Section({
  id,
  eyebrow,
  title,
  lead,
  children,
}: {
  id: string;
  eyebrow: string;
  title: string;
  lead: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="section-band px-5 py-16 md:px-10 lg:px-16">
      <div className="mx-auto max-w-6xl">
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.22em] text-[var(--gulf)]">
          {eyebrow}
        </p>
        <h2 className="brand-display max-w-3xl text-3xl text-[var(--foam)] md:text-4xl">
          {title}
        </h2>
        <p className="mt-3 max-w-2xl text-[var(--muted)]">{lead}</p>
        <div className="mt-10">{children}</div>
      </div>
    </section>
  );
}

export default function Dashboard({ data }: { data: Metrics }) {
  const h = data.q1_tom_yoy.headline;
  const sam = data.q3_sam;
  const som = data.q4_som;

  const tomAnnualChart = data.q1_tom_yoy.annual.map((r) => ({
    year: String(r.year),
    count: r.count,
    valuation: r.valuation / 1e9,
    yoy: r.count_yoy_pct,
  }));

  const monthlyTom = data.q1_tom_yoy.monthly.map((r) => ({
    label: ymLabel(r.year, r.month),
    count: r.count,
    valuationM: r.valuation / 1e6,
  }));

  // Latest year segment mix
  const years = [...new Set(data.q2_segment_trends.annual.map((r) => r.year))].sort();
  const latestYear = years[years.length - 1];
  const segLatest = data.q2_segment_trends.annual
    .filter((r) => r.year === latestYear && r.segment !== "other")
    .map((r) => ({
      name: segmentLabel(r.segment),
      key: r.segment,
      count: r.count,
      valuation: r.valuation,
    }));

  // Segment YoY series (count) for SAM-ish segments + other
  const segKeys = [
    "new_residential_plumbing",
    "plumbing_repipe_remodel",
    "pool_spa",
    "irrigation",
    "other",
  ];
  const segByYear: Record<string, Record<string, number>> = {};
  for (const r of data.q2_segment_trends.annual) {
    segByYear[r.year] ??= {};
    segByYear[r.year][r.segment] = r.count;
  }
  const segTrendChart = years.map((y) => {
    const row: Record<string, string | number> = { year: String(y) };
    for (const k of segKeys) row[k] = segByYear[y]?.[k] ?? 0;
    return row;
  });

  const countyBars = sam.top_counties.slice(0, 10).map((c) => ({
    county: c.county.replace(/ County$/i, ""),
    valuation: c.valuation / 1e6,
    count: c.count,
  }));

  const nearTerm = data.q5_near_term.by_county.slice(0, 8).map((c) => ({
    county: c.county.replace(/ County$/i, ""),
    pipeline: c.pipeline_0_3m_valuation / 1e6,
  }));

  const pieSam = sam.by_category.map((c) => ({
    name: categoryLabel(c.category),
    value: c.valuation,
    pct: c.pct_of_sam_valuation,
  }));

  return (
    <main>
      {/* Hero — one composition, brand-forward, full-bleed FL image */}
      <header className="hero-shell">
        <div className="hero-media" aria-hidden />
        <div className="relative z-10 flex flex-1 flex-col">
          <nav className="flex items-center justify-between px-5 py-6 md:px-10 lg:px-16">
            <div className="brand-display text-lg tracking-wide text-[var(--sand)] md:text-xl">
              Tigre <span className="text-[var(--gulf)]">×</span> Dura
            </div>
            <div className="hidden text-xs uppercase tracking-[0.18em] text-[var(--muted)] sm:block">
              Florida · Permits ≥ 2021
            </div>
          </nav>

          <div className="flex flex-1 flex-col justify-center px-5 pb-16 pt-8 md:px-10 lg:px-16">
            <p className="rise text-sm font-medium uppercase tracking-[0.28em] text-[var(--sun)]">
              Permit Demand Engine
            </p>
            <h1 className="brand-display rise rise-delay-1 mt-4 max-w-4xl text-5xl leading-[1.05] text-[var(--foam)] md:text-7xl">
              Florida demand,
              <br />
              <span className="text-[var(--sand)]">read from permits.</span>
            </h1>
            <p className="rise rise-delay-2 mt-6 max-w-xl text-base text-[var(--muted)] md:text-lg">
              TOM, SAM, and 5% SOM for Tigre USA and Dura — statewide MVP from
              open Florida permit feeds, not paid Shovels.
            </p>
            <div className="rise rise-delay-3 mt-10 flex flex-wrap gap-3">
              <a className="pill-cta" href="#tom">
                View growth
              </a>
              <a className="ghost-cta" href="#som">
                SOM at 5%
              </a>
            </div>
          </div>
        </div>
        <div className="wave-divider relative z-10" />
      </header>

      {/* Headline strip — not hero clutter; sits below first viewport */}
      <section className="px-5 py-12 md:px-10 lg:px-16">
        <div className="mx-auto grid max-w-6xl gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { label: "TOM permits", value: num(data.universe.tom) },
            {
              label: "SAM share",
              value: pctPlain(data.universe.sam_share_pct),
            },
            {
              label: "SAM addressable $",
              value: data.formatted_headlines.sam_valuation ?? usd(sam.share.sam_valuation),
            },
            {
              label: "SOM (5%)",
              value: data.formatted_headlines.som ?? usd(som.som_usd),
            },
          ].map((s) => (
            <div key={s.label}>
              <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                {s.label}
              </p>
              <p className="stat-value mt-2 text-3xl text-[var(--sand)] md:text-4xl">
                {s.value}
              </p>
            </div>
          ))}
        </div>
        <p className="mx-auto mt-8 max-w-6xl text-xs text-[var(--muted)]">
          As of {data.as_of} · generated {new Date(data.generated_at).toUTCString()} ·{" "}
          {data.universe.jurisdictions} jurisdictions · {data.universe.counties} counties
        </p>
      </section>

      <Section
        id="tom"
        eyebrow="01 · TOM"
        title="Statewide permit growth and 2026 year-to-go"
        lead="Total market = every permit issued since 2021. YoY on counts and declared project $, with year-end 2026 expectation from prior-year seasonality × trailing growth."
      >
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 chart-panel p-5">
            <p className="mb-4 text-sm text-[var(--muted)]">Annual TOM permits</p>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={tomAnnualChart}>
                  <CartesianGrid stroke="rgba(232,220,200,0.08)" vertical={false} />
                  <XAxis dataKey="year" stroke={SAND} tick={{ fill: SAND, fontSize: 12 }} />
                  <YAxis stroke={SAND} tick={{ fill: SAND, fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      background: "#0c2a32",
                      border: "1px solid rgba(232,220,200,0.2)",
                    }}
                    formatter={(v) => num(Number(v))}
                  />
                  <Bar dataKey="count" fill={GULF} radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="flex flex-col justify-between gap-6">
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                Latest YoY (counts)
              </p>
              <p className="stat-value mt-2 text-4xl text-[var(--sand)]">
                {pct(h.yoy_count_pct)}
              </p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                Latest YoY ($)
              </p>
              <p className="stat-value mt-2 text-4xl text-[var(--sand)]">
                {pct(h.yoy_valuation_pct)}
              </p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                2026 YTD → YE expected
              </p>
              <p className="stat-value mt-2 text-2xl text-[var(--foam)]">
                {num(h.y2026_ytd_count)} → {num(h.y2026_full_year_count)}
              </p>
              <p className="mt-1 text-sm text-[var(--muted)]">
                YTG {num(h.y2026_ytg_count)} · $ YTD {usd(h.y2026_ytd_valuation)} · YE{" "}
                {usd(h.y2026_full_year_valuation)}
              </p>
            </div>
          </div>
        </div>
        <div className="chart-panel mt-6 p-5">
          <p className="mb-4 text-sm text-[var(--muted)]">Monthly TOM trajectory</p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={monthlyTom}>
                <defs>
                  <linearGradient id="tomFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={GULF} stopOpacity={0.45} />
                    <stop offset="100%" stopColor={GULF} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(232,220,200,0.08)" vertical={false} />
                <XAxis
                  dataKey="label"
                  stroke={SAND}
                  tick={{ fill: SAND, fontSize: 10 }}
                  interval="preserveStartEnd"
                  minTickGap={40}
                />
                <YAxis stroke={SAND} tick={{ fill: SAND, fontSize: 12 }} />
                <Tooltip
                  contentStyle={{
                    background: "#0c2a32",
                    border: "1px solid rgba(232,220,200,0.2)",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke={GULF}
                  fill="url(#tomFill)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </Section>

      <Section
        id="segments"
        eyebrow="02 · Segments"
        title="Trend by Tigre–Dura category"
        lead="New residential plumbing, repipe/remodel, pool/spa, irrigation, and residual other — the same classification that defines SAM."
      >
        <div className="chart-panel p-5">
          <p className="mb-4 text-sm text-[var(--muted)]">
            Annual permit counts by segment
          </p>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={segTrendChart}>
                <CartesianGrid stroke="rgba(232,220,200,0.08)" vertical={false} />
                <XAxis dataKey="year" stroke={SAND} tick={{ fill: SAND, fontSize: 12 }} />
                <YAxis stroke={SAND} tick={{ fill: SAND, fontSize: 12 }} />
                <Tooltip
                  contentStyle={{
                    background: "#0c2a32",
                    border: "1px solid rgba(232,220,200,0.2)",
                  }}
                />
                <Legend />
                {segKeys.map((k) => (
                  <Bar
                    key={k}
                    dataKey={k}
                    stackId="a"
                    name={segmentLabel(k)}
                    fill={SEG_COLORS[k]}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {segLatest.map((s) => (
            <div key={s.key} className="border-t border-[var(--line)] pt-4">
              <p className="text-xs uppercase tracking-[0.16em] text-[var(--muted)]">
                {s.name} · {latestYear}
              </p>
              <p className="stat-value mt-2 text-2xl text-[var(--sand)]">{num(s.count)}</p>
              <p className="text-sm text-[var(--muted)]">{usd(s.valuation)}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section
        id="sam"
        eyebrow="03 · SAM"
        title="Tigre–Dura addressable share and county trend"
        lead="SAM is plumbing + pool/spa + irrigation + new residential construction. Projection to year-end 2026 uses the same seasonal method as TOM."
      >
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="chart-panel p-5">
            <p className="mb-4 text-sm text-[var(--muted)]">SAM category mix ($)</p>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieSam}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={55}
                    outerRadius={95}
                    paddingAngle={2}
                  >
                    {pieSam.map((_, i) => (
                      <Cell
                        key={i}
                        fill={[GULF, CORAL, MANGROVE, SUN, "#5a7076"][i % 5]}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(v) => usd(Number(v))}
                    contentStyle={{
                      background: "#0c2a32",
                      border: "1px solid rgba(232,220,200,0.2)",
                    }}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="flex flex-col justify-center gap-8">
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                SAM / TOM (rows)
              </p>
              <p className="stat-value mt-2 text-5xl text-[var(--sand)]">
                {pctPlain(sam.share.sam_share_of_tom_count_pct)}
              </p>
              <p className="mt-2 text-sm text-[var(--muted)]">
                {num(sam.share.sam_count)} of {num(sam.share.tom_count)} permits
              </p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                SAM / TOM ($)
              </p>
              <p className="stat-value mt-2 text-4xl text-[var(--sand)]">
                {pctPlain(sam.share.sam_share_of_tom_valuation_pct)}
              </p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                2026 SAM YE expected
              </p>
              <p className="stat-value mt-2 text-2xl">
                {num(sam.projection_2026_count.full_year_expected)} ·{" "}
                {usd(sam.projection_2026_valuation.full_year_expected)}
              </p>
            </div>
          </div>
        </div>
        <div className="chart-panel mt-6 p-5">
          <p className="mb-4 text-sm text-[var(--muted)]">
            Top counties by SAM valuation ($M)
          </p>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={countyBars} layout="vertical" margin={{ left: 24 }}>
                <CartesianGrid stroke="rgba(232,220,200,0.08)" horizontal={false} />
                <XAxis type="number" stroke={SAND} tick={{ fill: SAND, fontSize: 12 }} />
                <YAxis
                  type="category"
                  dataKey="county"
                  width={100}
                  stroke={SAND}
                  tick={{ fill: SAND, fontSize: 11 }}
                />
                <Tooltip
                  formatter={(v) => `$${Number(v).toFixed(1)}M`}
                  contentStyle={{
                    background: "#0c2a32",
                    border: "1px solid rgba(232,220,200,0.2)",
                  }}
                />
                <Bar dataKey="valuation" fill={MANGROVE} radius={[0, 2, 2, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </Section>

      <Section
        id="som"
        eyebrow="04 · SOM"
        title="Serviceable obtainable market at 5%"
        lead="SOM = 5% of SAM addressable project $. Missing valuations filled with peer medians. Material vs labor uses fittings assumptions from the V1.1 model."
      >
        <div className="grid gap-10 md:grid-cols-3">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
              SAM addressable
            </p>
            <p className="stat-value mt-2 text-4xl text-[var(--sand)]">
              {som.formatted.sam_addressable}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
              SOM @ 5%
            </p>
            <p className="stat-value mt-2 text-4xl text-[var(--sun)]">
              {som.formatted.som}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
              Material / labor (of SOM $)
            </p>
            <p className="stat-value mt-2 text-2xl text-[var(--foam)]">
              {som.formatted.material}{" "}
              <span className="text-[var(--muted)]">/</span> {som.formatted.labor}
            </p>
            <p className="mt-2 text-sm text-[var(--muted)]">
              {pctPlain(som.material_share_of_sam_pct)} material ·{" "}
              {pctPlain(som.labor_share_of_sam_pct)} labor
            </p>
            {som.formatted.fittings_som && (
              <p className="mt-3 text-sm text-[var(--sun)]">
                Fittings SOM (5% of modeled fittings demand): {som.formatted.fittings_som}
              </p>
            )}
          </div>
        </div>
        <div className="mt-10 grid gap-3 text-sm text-[var(--muted)] md:grid-cols-2">
          <p>
            Plumbing material share of plumbing (base):{" "}
            <span className="text-[var(--sand)]">
              {pctPlain(
                Number(som.assumptions_stated.plumbing_material_share_of_plumbing_base) *
                  100,
                0
              )}
            </span>
            ; fittings share of material:{" "}
            <span className="text-[var(--sand)]">
              {pctPlain(
                Number(som.assumptions_stated.fittings_share_of_material_base) * 100,
                0
              )}
            </span>
            .
          </p>
          <p>
            Pool fittings share of project:{" "}
            <span className="text-[var(--sand)]">
              {pctPlain(
                Number(som.assumptions_stated.pool_fittings_share_of_project_base) * 100,
                0
              )}
            </span>
            ; irrigation:{" "}
            <span className="text-[var(--sand)]">
              {pctPlain(
                Number(som.assumptions_stated.irrigation_fittings_share_of_project_base) *
                  100,
                0
              )}
            </span>
            . {som.imputation_method}
          </p>
        </div>
      </Section>

      <Section
        id="near-term"
        eyebrow="05 · Near-term"
        title="County opportunity — now through +3 months"
        lead="Observed current month where available; forward months from prior-year same month × recent growth. Short/medium horizon for rep activation."
      >
        <div className="chart-panel p-5">
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={nearTerm}>
                <CartesianGrid stroke="rgba(232,220,200,0.08)" vertical={false} />
                <XAxis dataKey="county" stroke={SAND} tick={{ fill: SAND, fontSize: 11 }} />
                <YAxis stroke={SAND} tick={{ fill: SAND, fontSize: 12 }} />
                <Tooltip
                  formatter={(v) => `$${Number(v).toFixed(1)}M`}
                  contentStyle={{
                    background: "#0c2a32",
                    border: "1px solid rgba(232,220,200,0.2)",
                  }}
                />
                <Bar dataKey="pipeline" name="0–3m pipeline $M" fill={CORAL} radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="mt-8 overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-[0.14em] text-[var(--muted)]">
                <th className="pb-3 font-medium">County</th>
                <th className="pb-3 font-medium">Current</th>
                <th className="pb-3 font-medium">+1m</th>
                <th className="pb-3 font-medium">+2m</th>
                <th className="pb-3 font-medium">+3m</th>
                <th className="pb-3 font-medium">0–3m $</th>
              </tr>
            </thead>
            <tbody>
              {data.q5_near_term.by_county.slice(0, 10).map((row) => (
                <tr key={row.county} className="table-row">
                  <td className="py-3 text-[var(--sand)]">{row.county}</td>
                  {row.horizon.map((h) => (
                    <td key={h.label} className="py-3 text-[var(--muted)]">
                      {usd(h.valuation)}
                      <span className="ml-1 text-[10px] uppercase opacity-60">
                        {h.kind === "projected" ? "proj" : "obs"}
                      </span>
                    </td>
                  ))}
                  <td className="py-3 text-[var(--foam)]">
                    {usd(row.pipeline_0_3m_valuation)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section
        id="contractors"
        eyebrow="06 · Activation"
        title="Contractor ranking for outreach"
        lead={data.q6_contractors.notes}
      >
        <div className="mb-8 grid gap-6 sm:grid-cols-3">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
              SAM contractor coverage
            </p>
            <p className="stat-value mt-2 text-4xl text-[var(--sand)]">
              {pctPlain(data.q6_contractors.coverage.sam_coverage_pct)}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
              Named SAM permits
            </p>
            <p className="stat-value mt-2 text-4xl text-[var(--sand)]">
              {num(data.q6_contractors.coverage.sam_with_name)}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
              TOM name coverage
            </p>
            <p className="stat-value mt-2 text-4xl text-[var(--sand)]">
              {pctPlain(data.q6_contractors.coverage.tom_coverage_pct)}
            </p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-[0.14em] text-[var(--muted)]">
                <th className="pb-3 font-medium">#</th>
                <th className="pb-3 font-medium">Contractor</th>
                <th className="pb-3 font-medium">SAM permits</th>
                <th className="pb-3 font-medium">Valuation</th>
                <th className="pb-3 font-medium">Counties</th>
              </tr>
            </thead>
            <tbody>
              {data.q6_contractors.top.slice(0, 25).map((c, i) => (
                <tr key={c.contractor_name} className="table-row">
                  <td className="py-3 text-[var(--muted)]">{i + 1}</td>
                  <td className="py-3 text-[var(--sand)]">{c.contractor_name}</td>
                  <td className="py-3">{num(c.permits)}</td>
                  <td className="py-3">{usd(c.valuation)}</td>
                  <td className="max-w-[220px] truncate py-3 text-[var(--muted)]">
                    {c.counties}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <footer className="section-band px-5 py-12 md:px-10 lg:px-16">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="brand-display text-2xl text-[var(--sand)]">Tigre × Dura</p>
            <p className="mt-2 max-w-lg text-sm text-[var(--muted)]">
              Open-data Florida MVP. Valuation USD with peer-median fill. Material
              shares from config/assumptions.yaml (base scenario). Coverage is
              jurisdiction-tiered — not full statewide census of every city.
            </p>
          </div>
          <p className="text-xs text-[var(--muted)]">
            Permit Demand Engine · as of {data.as_of}
          </p>
        </div>
      </footer>
    </main>
  );
}
