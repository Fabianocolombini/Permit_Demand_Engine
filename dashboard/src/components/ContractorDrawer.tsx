"use client";

import { categoryLabel, num, usd } from "@/lib/format";

export type ContractorProject = {
  permit_id: string;
  issued_date: string | null;
  valuation: number;
  material_usd: number;
  som_material_usd: number;
  city?: string | null;
  zip?: string | null;
  address?: string | null;
  category?: string;
  description?: string | null;
  county?: string | null;
  mesoregion?: string | null;
  license?: string | null;
};

export type ContractorDetail = {
  contractor_name: string;
  license?: string | null;
  website?: string | null;
  phone?: string | null;
  mesoregions?: string[];
  counties?: string[];
  permits: number;
  valuation: number;
  material_usd: number;
  som_material_usd: number;
  projects: ContractorProject[];
  search_query?: string;
};

type Props = {
  open: boolean;
  detail: ContractorDetail | null;
  windowLabel: string;
  shareScale: number;
  onClose: () => void;
};

export default function ContractorDrawer({
  open,
  detail,
  windowLabel,
  shareScale,
  onClose,
}: Props) {
  if (!open || !detail) return null;

  const search = encodeURIComponent(
    detail.search_query ||
      `${detail.contractor_name} ${detail.license || ""} Florida contractor`
  );
  const projects = [...(detail.projects || [])].sort((a, b) => {
    const da = a.issued_date || "";
    const db = b.issued_date || "";
    if (da === db) return (b.valuation || 0) - (a.valuation || 0);
    return db.localeCompare(da); // newest → oldest
  });
  const projectSum = projects.reduce((s, p) => s + (p.valuation || 0), 0);
  const website = detail.website?.trim() || null;
  const phone = detail.phone?.trim() || null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center md:items-center">
      <button
        type="button"
        aria-label="Close contractor detail"
        className="absolute inset-0 bg-black/60"
        onClick={onClose}
      />
      <div className="relative z-10 max-h-[88vh] w-full max-w-3xl overflow-y-auto rounded-t-md border border-[var(--line)] bg-[var(--ink)] p-5 shadow-xl md:rounded-md md:p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
              Contractor · {windowLabel}
            </p>
            <h3 className="brand-display mt-1 text-2xl text-[var(--foam)]">
              {detail.contractor_name}
            </h3>
            <p className="mt-1 text-sm text-[var(--muted)]">
              License {detail.license || "not on permit feed"}
              {detail.mesoregions && detail.mesoregions.length
                ? ` · ${detail.mesoregions.join(", ")}`
                : ""}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-[var(--line)] px-2 py-1 text-xs uppercase tracking-[0.12em] text-[var(--sand)]"
          >
            Close
          </button>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
          <div>
            <p className="text-[var(--muted)]">Permits</p>
            <p className="stat-value text-xl">{num(detail.permits)}</p>
          </div>
          <div>
            <p className="text-[var(--muted)]">Project $</p>
            <p className="stat-value text-xl">{usd(detail.valuation)}</p>
          </div>
          <div>
            <p className="text-[var(--muted)]">Materials pot.</p>
            <p className="stat-value text-xl text-[var(--sun)]">
              {usd(detail.som_material_usd * shareScale)}
            </p>
          </div>
          <div>
            <p className="text-[var(--muted)]">Listed projects $</p>
            <p className="stat-value text-xl">{usd(projectSum)}</p>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2 text-xs">
          {website ? (
            <a
              href={website}
              target="_blank"
              rel="noreferrer"
              className="rounded-full bg-[var(--sun)] px-3 py-1 text-[#071a1f] hover:opacity-90"
            >
              Website
            </a>
          ) : null}
          {phone ? (
            <a
              href={`tel:${phone.replace(/[^\d+]/g, "")}`}
              className="rounded-full border border-[var(--line)] px-3 py-1 text-[var(--sand)] hover:bg-white/5"
            >
              {phone}
            </a>
          ) : null}
          <a
            href={`https://www.google.com/search?q=${search}`}
            target="_blank"
            rel="noreferrer"
            className="rounded-full border border-[var(--line)] px-3 py-1 text-[var(--sand)] hover:bg-white/5"
          >
            Search name + license
          </a>
          <a
            href={`https://www.sunbiz.org/search.html`}
            target="_blank"
            rel="noreferrer"
            className="rounded-full border border-[var(--line)] px-3 py-1 text-[var(--sand)] hover:bg-white/5"
          >
            Florida Sunbiz
          </a>
          {!website ? (
            <span className="rounded-full border border-[var(--line)] px-3 py-1 text-[var(--muted)]">
              Website not in permit feed — enriched when found
            </span>
          ) : null}
        </div>

        <p className="mt-6 text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
          Projects in window ({projects.length})
        </p>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead>
              <tr className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">
                <th className="pb-2">Issued ↓</th>
                <th className="pb-2">Permit</th>
                <th className="pb-2">Address</th>
                <th className="pb-2">Category</th>
                <th className="pb-2">Project $</th>
                <th className="pb-2">Mat. pot.</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr key={`${p.permit_id}-${p.issued_date}`} className="table-row align-top">
                  <td className="py-2 text-[var(--muted)]">{p.issued_date || "—"}</td>
                  <td className="py-2 font-mono text-xs text-[var(--sand)]">
                    {p.permit_id}
                  </td>
                  <td className="max-w-[220px] py-2 text-[var(--sand)]">
                    <div>{p.address || "—"}</div>
                    <div className="text-[11px] text-[var(--muted)]">
                      {[p.city, p.mesoregion || p.county].filter(Boolean).join(" · ")}
                    </div>
                    {p.description ? (
                      <div className="mt-0.5 text-[11px] text-[var(--muted)]">
                        {p.description}
                      </div>
                    ) : null}
                  </td>
                  <td className="py-2 text-[var(--muted)]">
                    {categoryLabel(p.category || "")}
                  </td>
                  <td className="py-2">{usd(p.valuation)}</td>
                  <td className="py-2 text-[var(--sun)]">
                    {usd((p.som_material_usd || 0) * shareScale)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
