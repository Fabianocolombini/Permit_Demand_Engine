export function usd(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  const a = Math.abs(n);
  if (a >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (a >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  if (a >= 1e3) return `$${(n / 1e3).toFixed(1)}K`;
  return `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

export function num(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  return Math.round(n).toLocaleString();
}

export function pct(n: number | null | undefined, digits = 1): string {
  if (n == null || Number.isNaN(n)) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(digits)}%`;
}

export function pctPlain(n: number | null | undefined, digits = 1): string {
  if (n == null || Number.isNaN(n)) return "—";
  return `${n.toFixed(digits)}%`;
}

export const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

export function ymLabel(year: number, month: number): string {
  return `${MONTHS[month - 1]} ${year}`;
}

export function segmentLabel(s: string): string {
  const map: Record<string, string> = {
    new_residential_plumbing: "New residential plumbing",
    plumbing_repipe_remodel: "Repipe / remodel plumbing",
    pool_spa: "Pool / spa",
    irrigation: "Irrigation",
    other: "Other",
  };
  return map[s] ?? s;
}

export function categoryLabel(s: string): string {
  const map: Record<string, string> = {
    res_new_plumbing: "New residential plumbing",
    res_repipe: "Repipe",
    res_remodel_plumbing: "Remodel plumbing",
    pool_spa: "Pool / spa",
    irrigation: "Irrigation",
  };
  return map[s] ?? s;
}
