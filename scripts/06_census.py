#!/usr/bin/env python3
"""Download Census BPS + HUD county permits for all 67 FL counties; coverage vs bronze."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ingest.census_bps import (  # noqa: E402
    fetch_bps_fl_years,
    fetch_hud_fl_permits,
    write_csv,
)
from src.registry import load_jurisdictions_raw as load_jurisdictions  # noqa: E402


def bronze_row_counts() -> dict[str, dict]:
    """Count rows in full bronze CSVs (skip sample_preview)."""
    bronze = ROOT / "data" / "bronze"
    out: dict[str, dict] = {}
    if not bronze.exists():
        return out
    for d in sorted(bronze.iterdir()):
        if not d.is_dir():
            continue
        total = 0
        files = []
        for p in d.glob("*.csv"):
            if p.name == "sample_preview.csv":
                continue
            # fast line count
            with p.open("rb") as fh:
                n = sum(1 for _ in fh) - 1
            if n > 0:
                total += n
                files.append({"path": str(p), "rows": n})
        if total:
            out[d.name] = {"rows": total, "files": files}
    return out


def coverage_table(
    bps_rows: list[dict],
    hud_rows: list[dict],
    bronze: dict[str, dict],
    registry: list[dict],
) -> list[dict]:
    # Aggregate BPS 2021–latest by county
    bps_by: dict[str, dict] = defaultdict(lambda: {"units": 0, "valuation_usd": 0.0, "years": set()})
    for r in bps_rows:
        fips = r["county_fips"]
        bps_by[fips]["units"] += int(r.get("units_total") or 0)
        bps_by[fips]["valuation_usd"] += float(r.get("valuation_usd") or 0)
        bps_by[fips]["years"].add(int(r["year"]))
        bps_by[fips]["name"] = r.get("county_name") or bps_by[fips].get("name")

    hud_by: dict[str, dict] = defaultdict(lambda: {"all_permits": 0, "sf": 0, "mf": 0, "years": set()})
    for r in hud_rows:
        fips = r["county_fips"]
        try:
            hud_by[fips]["all_permits"] += int(float(r.get("all_permits") or 0))
        except (TypeError, ValueError):
            pass
        try:
            hud_by[fips]["sf"] += int(float(r.get("single_family_permits") or 0))
        except (TypeError, ValueError):
            pass
        try:
            hud_by[fips]["mf"] += int(float(r.get("multifamily_permits") or 0))
        except (TypeError, ValueError):
            pass
        hud_by[fips]["years"].add(int(r["year"]))
        hud_by[fips]["name"] = r.get("county_name") or hud_by[fips].get("name")

    # Map registry jurisdictions → county_fips and bronze rows
    jur_by_fips: dict[str, list[dict]] = defaultdict(list)
    for j in registry:
        fips = str(j.get("county_fips") or "")
        if not fips:
            continue
        jid = j["id"]
        br = bronze.get(jid, {})
        jur_by_fips[fips].append(
            {
                "id": jid,
                "tier": j.get("tier"),
                "covers": j.get("covers"),
                "bronze_rows": br.get("rows", 0),
                "name": j.get("name"),
            }
        )

    all_fips = sorted(set(bps_by) | set(hud_by) | set(jur_by_fips))
    rows = []
    for fips in all_fips:
        if not fips.startswith("12"):
            continue
        jurs = jur_by_fips.get(fips, [])
        bronze_rows = sum(j["bronze_rows"] for j in jurs)
        bps = bps_by.get(fips, {})
        hud = hud_by.get(fips, {})
        bps_units = int(bps.get("units") or 0)
        # Coverage ratio: bronze permit rows / BPS units (directional; different universes)
        cov = round(bronze_rows / bps_units, 4) if bps_units else None
        rows.append(
            {
                "county_fips": fips,
                "county_name": (bps.get("name") or hud.get("name") or "").replace(" County", ""),
                "bps_units_2021_plus": bps_units,
                "bps_valuation_usd_2021_plus": round(float(bps.get("valuation_usd") or 0), 2),
                "bps_years": ",".join(str(y) for y in sorted(bps.get("years") or [])),
                "hud_all_permits_2021_plus": int(hud.get("all_permits") or 0),
                "hud_sf_permits_2021_plus": int(hud.get("sf") or 0),
                "hud_mf_permits_2021_plus": int(hud.get("mf") or 0),
                "hud_years": ",".join(str(y) for y in sorted(hud.get("years") or [])),
                "bronze_permit_rows": bronze_rows,
                "bronze_vs_bps_units_ratio": cov,
                "jurisdiction_ids": ";".join(j["id"] for j in jurs) if jurs else "",
                "tiers": ";".join(sorted({str(j["tier"]) for j in jurs})) if jurs else "C",
                "n_jurisdictions_with_bronze": sum(1 for j in jurs if j["bronze_rows"] > 0),
            }
        )
    return rows


def write_coverage_md(path: Path, cov_rows: list[dict], bps_years: list[int], hud_years: list[int]) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    n67 = len([r for r in cov_rows if r["county_fips"].startswith("12")])
    with_bronze = sum(1 for r in cov_rows if r["bronze_permit_rows"] > 0)
    lines = [
        "# Census BPS + HUD coverage — Florida (67 counties)",
        "",
        f"Generated: {stamp}",
        "",
        f"- **Census BPS** annual county files: years **{min(bps_years)}–{max(bps_years)}** → `data/reference/census_bps_fl.csv`",
        f"- **HUD** Residential Construction Permits by County (ArcGIS): years **{', '.join(map(str, hud_years)) or 'none in layer'}** → `data/reference/hud_permits_fl.csv`",
        f"- Counties in table: **{n67}** · with any bronze rows: **{with_bronze}**",
        "",
        "## Method notes",
        "",
        "- BPS `units_total` / `valuation_usd` = new privately-owned residential units authorized (USD as filed in coYYYYa.txt).",
        "- HUD `all_permits` = final residential permit counts (SOCDS; may lag BPS annual).",
        "- Bronze rows are **all permit types** (plumbing, roof, etc.), not BPS-equivalent new residential units — ratio is a **directional coverage signal**, not a true capture rate.",
        "",
        "## County coverage (sorted by BPS units desc)",
        "",
        "| FIPS | County | BPS units ≥2021 | BPS $ ≥2021 | HUD permits ≥2021 | Bronze rows | Bronze/BPS units | Tiers |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in sorted(cov_rows, key=lambda x: -int(x["bps_units_2021_plus"] or 0)):
        ratio = r["bronze_vs_bps_units_ratio"]
        ratio_s = f"{ratio:.2f}" if ratio is not None else "—"
        bps_val = r["bps_valuation_usd_2021_plus"]
        bps_val_s = f"${bps_val/1e9:.2f}B" if bps_val >= 1e9 else f"${bps_val/1e6:.1f}M"
        lines.append(
            f"| {r['county_fips']} | {r['county_name']} | {r['bps_units_2021_plus']:,} | "
            f"{bps_val_s} | {r['hud_all_permits_2021_plus']:,} | {r['bronze_permit_rows']:,} | "
            f"{ratio_s} | {r['tiers']} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--years", default="2021,2022,2023,2024,2025")
    p.add_argument("--ref-dir", type=Path, default=ROOT / "data" / "reference")
    args = p.parse_args()
    years = [int(x) for x in args.years.split(",") if x.strip()]

    print(f"Fetching Census BPS FL for {years}…", flush=True)
    bps_rows = fetch_bps_fl_years(years)
    print(f"  BPS rows: {len(bps_rows)} (expect ~67×{len(years)})", flush=True)
    bps_path = args.ref_dir / "census_bps_fl.csv"
    bps_cols = [
        "year",
        "county_fips",
        "county_name",
        "state_fips",
        "county_fips3",
        "units_total",
        "bldgs_total",
        "valuation_usd",
        "units_1",
        "value_1_thousands",
        "units_2",
        "value_2_thousands",
        "units_3_4",
        "value_3_4_thousands",
        "units_5plus",
        "value_5plus_thousands",
        "source_url",
    ]
    write_csv(bps_path, bps_rows, bps_cols)
    print(f"  → {bps_path}", flush=True)

    print("Fetching HUD FL residential permits…", flush=True)
    hud_rows = fetch_hud_fl_permits(years=years)
    hud_years = sorted({int(r["year"]) for r in hud_rows})
    print(f"  HUD long rows: {len(hud_rows)} years={hud_years}", flush=True)
    hud_path = args.ref_dir / "hud_permits_fl.csv"
    write_csv(
        hud_path,
        hud_rows,
        [
            "year",
            "county_fips",
            "county_name",
            "state_fips",
            "stusab",
            "all_permits",
            "single_family_permits",
            "multifamily_permits",
            "source",
            "source_url",
            "retrieved_at",
        ],
    )
    print(f"  → {hud_path}", flush=True)

    bronze = bronze_row_counts()
    registry = load_jurisdictions()
    cov = coverage_table(bps_rows, hud_rows, bronze, registry)
    cov_csv = args.ref_dir / "bps_bronze_coverage_fl.csv"
    if cov:
        with cov_csv.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(cov[0].keys()))
            w.writeheader()
            w.writerows(cov)
    cov_md = args.ref_dir / "bps_bronze_coverage_fl.md"
    write_coverage_md(cov_md, cov, years, hud_years)
    print(f"  coverage → {cov_csv} · {cov_md}", flush=True)

    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bps_years": years,
        "bps_rows": len(bps_rows),
        "bps_counties": len({r["county_fips"] for r in bps_rows}),
        "hud_years": hud_years,
        "hud_rows": len(hud_rows),
        "hud_counties": len({r["county_fips"] for r in hud_rows}),
        "bronze_jurisdictions": len(bronze),
        "bronze_total_rows": sum(v["rows"] for v in bronze.values()),
        "paths": {
            "census_bps_fl": str(bps_path),
            "hud_permits_fl": str(hud_path),
            "coverage_csv": str(cov_csv),
            "coverage_md": str(cov_md),
        },
    }
    (args.ref_dir / "census_hud_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
