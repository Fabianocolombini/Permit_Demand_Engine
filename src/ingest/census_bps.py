"""Census Building Permits Survey (county) + HUD Residential Construction Permits."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

BPS_BASE = "https://www2.census.gov/econ/bps/County"
HUD_LAYER = (
    "https://services.arcgis.com/VTyQ9soqVukalItT/arcgis/rest/services/"
    "Residential_Construction_Permits_by_County/FeatureServer/24"
)

# BPS county annual header (after two preamble rows) — see cntyasc.pdf
BPS_COLUMNS = [
    "survey_date",
    "state_fips",
    "county_fips3",
    "region_code",
    "division_code",
    "county_name",
    "bldgs_1",
    "units_1",
    "value_1_thousands",
    "bldgs_2",
    "units_2",
    "value_2_thousands",
    "bldgs_3_4",
    "units_3_4",
    "value_3_4_thousands",
    "bldgs_5plus",
    "units_5plus",
    "value_5plus_thousands",
    "bldgs_1_rep",
    "units_1_rep",
    "value_1_rep_thousands",
    "bldgs_2_rep",
    "units_2_rep",
    "value_2_rep_thousands",
    "bldgs_3_4_rep",
    "units_3_4_rep",
    "value_3_4_rep_thousands",
    "bldgs_5plus_rep",
    "units_5plus_rep",
    "value_5plus_rep_thousands",
]


def fetch_bps_county_annual(year: int, *, state_fips: str = "12", timeout: float = 120.0) -> list[dict[str, Any]]:
    """Download Census BPS county annual file and filter to one state (default FL=12)."""
    url = f"{BPS_BASE}/co{year}a.txt"
    r = httpx.get(url, timeout=timeout, follow_redirects=True)
    r.raise_for_status()
    # Skip 2 preamble rows; third is header with awkward names — we rename.
    text = r.text
    reader = csv.reader(io.StringIO(text))
    rows_iter = iter(reader)
    next(rows_iter, None)
    next(rows_iter, None)
    header = next(rows_iter, None)
    if not header:
        raise RuntimeError(f"Empty BPS file: {url}")

    out: list[dict[str, Any]] = []
    for raw in rows_iter:
        if not raw or len(raw) < 6:
            continue
        state = str(raw[1]).strip().zfill(2)
        if state != state_fips.zfill(2):
            continue
        county3 = str(raw[2]).strip().zfill(3)
        rec: dict[str, Any] = {"source_url": url, "year": year}
        for i, col in enumerate(BPS_COLUMNS):
            rec[col] = raw[i].strip() if i < len(raw) else ""
        rec["county_fips"] = f"{state}{county3}"
        # Census docs historically say "$000"; recent coYYYYa.txt files ship
        # full dollar amounts (e.g. Miami-Dade SF ~$1B, not $1B×1000). Treat as USD.
        units_total = 0
        value_usd = 0.0
        for u_key, v_key in (
            ("units_1", "value_1_thousands"),
            ("units_2", "value_2_thousands"),
            ("units_3_4", "value_3_4_thousands"),
            ("units_5plus", "value_5plus_thousands"),
        ):
            try:
                units_total += int(float(rec.get(u_key) or 0))
            except ValueError:
                pass
            try:
                value_usd += float(rec.get(v_key) or 0)
            except ValueError:
                pass
        rec["units_total"] = units_total
        rec["valuation_usd"] = value_usd
        rec["valuation_note"] = "usd_as_filed"
        rec["bldgs_total"] = 0
        for b_key in ("bldgs_1", "bldgs_2", "bldgs_3_4", "bldgs_5plus"):
            try:
                rec["bldgs_total"] += int(float(rec.get(b_key) or 0))
            except ValueError:
                pass
        out.append(rec)
    return out


def fetch_bps_fl_years(years: list[int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for y in years:
        rows.extend(fetch_bps_county_annual(y))
    return rows


def fetch_hud_fl_permits(*, years: list[int] | None = None, timeout: float = 120.0) -> list[dict[str, Any]]:
    """Pull HUD Residential Construction Permits by County for Florida (67 counties).

    HUD wide schema: ALL_PERMITS_YYYY, SINGLE_FAMILY_PERMITS_YYYY, …
    """
    years = years or list(range(2021, 2026))
    # Discover available year columns from layer metadata
    meta = httpx.get(HUD_LAYER, params={"f": "json"}, timeout=timeout).json()
    field_names = {f["name"] for f in meta.get("fields", [])}
    keep_years = [y for y in years if f"ALL_PERMITS_{y}" in field_names]
    if not keep_years:
        # Fall back to latest years present in metadata
        avail = sorted(
            int(n.split("_")[-1])
            for n in field_names
            if n.startswith("ALL_PERMITS_") and n.split("_")[-1].isdigit()
        )
        keep_years = [y for y in avail if y >= 2021] or avail[-5:]

    out_fields = ["GEOID", "STATE", "COUNTY", "NAME", "STUSAB", "STATE_NAME"]
    for y in keep_years:
        for prefix in (
            "ALL_PERMITS_",
            "SINGLE_FAMILY_PERMITS_",
            "ALL_MULTIFAMILY_PERMITS_",
        ):
            col = f"{prefix}{y}"
            if col in field_names:
                out_fields.append(col)

    # Paginate FL counties (STATE numeric '12' or STUSAB 'FL')
    where = "STUSAB='FL' OR STATE='12'"
    offset = 0
    page = 1000
    features: list[dict[str, Any]] = []
    while True:
        payload = httpx.get(
            f"{HUD_LAYER}/query",
            params={
                "where": where,
                "outFields": ",".join(out_fields),
                "returnGeometry": "false",
                "resultOffset": offset,
                "resultRecordCount": page,
                "f": "json",
            },
            timeout=timeout,
        ).json()
        if payload.get("error"):
            raise RuntimeError(payload["error"])
        batch = payload.get("features") or []
        if not batch:
            break
        features.extend(batch)
        offset += len(batch)
        if not payload.get("exceededTransferLimit"):
            break

    long_rows: list[dict[str, Any]] = []
    retrieved = datetime.now(timezone.utc).isoformat()
    for feat in features:
        a = feat.get("attributes") or {}
        geoid = str(a.get("GEOID") or "").zfill(5)
        base = {
            "county_fips": geoid,
            "state_fips": str(a.get("STATE") or "12").zfill(2),
            "county_fips3": str(a.get("COUNTY") or geoid[-3:]).zfill(3),
            "county_name": a.get("NAME") or "",
            "stusab": a.get("STUSAB") or "FL",
            "state_name": a.get("STATE_NAME") or "Florida",
            "source": "hud_residential_construction_permits_by_county",
            "source_url": HUD_LAYER,
            "retrieved_at": retrieved,
        }
        for y in keep_years:
            long_rows.append(
                {
                    **base,
                    "year": y,
                    "all_permits": a.get(f"ALL_PERMITS_{y}"),
                    "single_family_permits": a.get(f"SINGLE_FAMILY_PERMITS_{y}"),
                    "multifamily_permits": a.get(f"ALL_MULTIFAMILY_PERMITS_{y}"),
                }
            )
    return long_rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return 0
    cols = fieldnames or list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows)
