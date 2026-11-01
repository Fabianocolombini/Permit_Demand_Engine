#!/usr/bin/env python3
"""Build Cape Coral post-2021 history from official All Issued Permits Excels.

Downloads (or reuses) City Document Center annual workbooks and normalizes them
into one bronze CSV. Optionally merges the live OpenData MapServer table for
rows not present in the Excel dumps.

  python3 scripts/export_cape_coral_history.py --since 2021-01-01
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import httpx
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORTS_PAGE = (
    "https://www.capecoral.gov/departments/development_services/"
    "building_permit_reports/index.php"
)
OPENDATA_LAYER = (
    "https://capeims.capecoral.gov/arcgis/rest/services/OpenData/OpenData/MapServer/1"
)
UA = "PermitDemandEngine/1.0 (+https://github.com/Fabianocolombini/Permit_Demand_Engine)"

# Canonical bronze columns
CANON = [
    "permit_number",
    "issued_date",
    "applied_date",
    "finalized_date",
    "permit_type",
    "work_class",
    "description",
    "status",
    "valuation",
    "address",
    "zip",
    "parcel",
    "owner_name",
    "contractor_name",
    "source_file",
    "source_year",
]


def _as_date(v: Any) -> date | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, pd.Timestamp):
        if pd.isna(v):
            return None
        return v.date()
    s = str(v).strip()
    if not s or s.lower() in {"nan", "nat", "none", "null"}:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s[:19], fmt).date()
        except ValueError:
            continue
    # Excel serial?
    try:
        n = float(s)
        if 30000 < n < 60000:
            return (datetime(1899, 12, 30) + pd.Timedelta(days=n)).date()
    except Exception:
        return None
    return None


def _cell(v: Any) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    if isinstance(v, pd.Timestamp):
        if pd.isna(v):
            return ""
        return v.date().isoformat()
    if isinstance(v, (datetime, date)):
        return v.isoformat() if isinstance(v, date) and not isinstance(v, datetime) else v.date().isoformat()
    s = str(v).replace("_x000D_", " ").replace("\r", " ").replace("\n", " ").strip()
    if s.lower() in {"nan", "nat", "none", "null"}:
        return ""
    return s


def _find_header_row(df: pd.DataFrame) -> int | None:
    for i in range(min(25, len(df))):
        vals = [str(x).strip().lower() for x in list(df.iloc[i].values)]
        joined = " | ".join(vals)
        has_permit = any(
            t in joined
            for t in ("permit no", "permit number", "permit_no", "permitnumber", "permit_number")
        )
        has_issued = any(
            t in joined
            for t in ("issued", "issue date", "permit issue date", "issuedate", "issue_date")
        )
        if has_permit and has_issued:
            return i
    return None


def _normalize_columns(cols: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for c in cols:
        key = re.sub(r"[^a-z0-9]+", "_", str(c).strip().lower()).strip("_")
        aliases = {
            "permit_no": "permit_number",
            "permit_number": "permit_number",
            "permitnumber": "permit_number",
            "permitnum": "permit_number",
            "permit_type": "permit_type",
            "permittype": "permit_type",
            "type": "permit_type",
            "work_class": "work_class",
            "permit_work_class": "work_class",
            "permitsubtype": "work_class",
            "description": "description",
            "value": "valuation",
            "valuation": "valuation",
            "permit_valuation": "valuation",
            "status": "status",
            "permit_status": "status",
            "applied": "applied_date",
            "applydate": "applied_date",
            "permit_application_date": "applied_date",
            "issued": "issued_date",
            "issuedate": "issued_date",
            "permit_issue_date": "issued_date",
            "issue_date": "issued_date",
            "finalized": "finalized_date",
            "finalizedate": "finalized_date",
            "finaled": "finalized_date",
            "strap": "parcel",
            "parcel": "parcel",
            "site_addr": "address",
            "address": "address",
            "site_zip": "zip",
            "zip": "zip",
            "owner_name": "owner_name",
            "ownername": "owner_name",
            "contractor_name": "contractor_name",
            "cont_company": "contractor_name",
            "builder": "contractor_name",
        }
        if key in aliases:
            mapping[c] = aliases[key]
    return mapping


def load_workbook(path: Path) -> pd.DataFrame:
    # Try clean header first
    df0 = pd.read_excel(path, dtype=object)
    if any(
        str(c).strip().lower() in {"permit number", "permit_no", "permit no"}
        for c in df0.columns
    ):
        return df0

    # Titled EnerGov exports: detect header row
    hdr = _find_header_row(df0)
    if hdr is None:
        # retry without assuming first sheet defaults
        df_raw = pd.read_excel(path, header=None, dtype=object)
        hdr = _find_header_row(df_raw)
        if hdr is None:
            raise RuntimeError(f"Could not find header row in {path.name}")
        headers = [str(x).strip() for x in list(df_raw.iloc[hdr].values)]
        body = df_raw.iloc[hdr + 1 :].copy()
        body.columns = headers
        return body.reset_index(drop=True)

    headers = [str(x).strip() for x in list(df0.iloc[hdr].values)]
    body = df0.iloc[hdr + 1 :].copy()
    body.columns = headers
    return body.reset_index(drop=True)


def rows_from_excel(path: Path, since: date) -> list[dict[str, str]]:
    df = load_workbook(path)
    mapping = _normalize_columns([str(c) for c in df.columns])
    year_guess = next((y for y in range(2021, 2027) if str(y) in path.name), None)
    out: list[dict[str, str]] = []
    for _, series in df.iterrows():
        raw = {mapping[c]: series[c] for c in df.columns if c in mapping}
        pid = _cell(raw.get("permit_number"))
        if not pid or set(pid) <= {"*"}:
            continue
        issued = _as_date(raw.get("issued_date"))
        if issued is None:
            continue
        if issued < since:
            continue
        row = {k: "" for k in CANON}
        row["permit_number"] = pid
        row["issued_date"] = issued.isoformat()
        ad = _as_date(raw.get("applied_date"))
        row["applied_date"] = ad.isoformat() if ad else ""
        fd = _as_date(raw.get("finalized_date"))
        row["finalized_date"] = fd.isoformat() if fd else ""
        for k in ("permit_type", "work_class", "description", "status", "valuation", "address", "zip", "parcel", "owner_name", "contractor_name"):
            row[k] = _cell(raw.get(k))
        row["address"] = re.sub(r"\s+", " ", row["address"]).strip()
        row["source_file"] = path.name
        row["source_year"] = str(year_guess or issued.year)
        out.append(row)
    return out


def fetch_opendata(since: date, sleep_s: float = 0.15) -> list[dict[str, str]]:
    """Paginate Cape Coral OpenData Building Permits table (issuedate)."""
    rows: list[dict[str, str]] = []
    offset = 0
    page = 2000
    where = f"issuedate >= DATE '{since.isoformat()}'"
    with httpx.Client(timeout=120.0, follow_redirects=True, headers={"User-Agent": UA}) as client:
        while True:
            payload = client.get(
                f"{OPENDATA_LAYER}/query",
                params={
                    "where": where,
                    "outFields": "*",
                    "returnGeometry": "false",
                    "resultOffset": offset,
                    "resultRecordCount": page,
                    "orderByFields": "objectid",
                    "f": "json",
                },
            ).json()
            if payload.get("error"):
                raise RuntimeError(payload["error"])
            feats = payload.get("features") or []
            if not feats:
                break
            for feat in feats:
                a = feat.get("attributes") or {}
                issued_ms = a.get("issuedate")
                if issued_ms is None:
                    continue
                issued = datetime.fromtimestamp(issued_ms / 1000, tz=timezone.utc).date()
                # OpenData has a handful of absurd future epochs (e.g. year 2610)
                if issued < since or issued.year > date.today().year + 1:
                    continue
                addr_parts = [
                    _cell(a.get("Addr1")),
                    _cell(a.get("Predir")),
                    _cell(a.get("Addr2")),
                    _cell(a.get("Street_Type")),
                    _cell(a.get("Post_Dir")),
                    _cell(a.get("Unit")),
                ]
                address = re.sub(r"\s+", " ", " ".join(p for p in addr_parts if p)).strip()
                city = _cell(a.get("City"))
                state = _cell(a.get("State"))
                if city or state:
                    address = ", ".join(p for p in [address, city, state] if p)
                apply_ms = a.get("applydate")
                final_ms = a.get("finalizedate")
                row = {k: "" for k in CANON}
                row["permit_number"] = _cell(a.get("Permit_Number"))
                row["issued_date"] = issued.isoformat()
                row["applied_date"] = (
                    datetime.fromtimestamp(apply_ms / 1000, tz=timezone.utc).date().isoformat()
                    if apply_ms
                    else ""
                )
                row["finalized_date"] = (
                    datetime.fromtimestamp(final_ms / 1000, tz=timezone.utc).date().isoformat()
                    if final_ms
                    else ""
                )
                row["permit_type"] = _cell(a.get("Permit_Type") or a.get("Friendly_Name"))
                row["work_class"] = _cell(a.get("Work_Class"))
                row["description"] = _cell(a.get("permit_desc"))
                row["status"] = _cell(a.get("permit_status"))
                row["valuation"] = _cell(a.get("permitvalue"))
                row["address"] = address
                row["zip"] = _cell(a.get("Zip"))
                row["parcel"] = _cell(a.get("Parcel"))
                row["owner_name"] = ""
                row["contractor_name"] = _cell(a.get("Company_Name") or a.get("Contractor"))
                row["source_file"] = "OpenData/MapServer/1"
                row["source_year"] = str(issued.year)
                if row["permit_number"]:
                    rows.append(row)
            offset += len(feats)
            print(f"  OpenData … {offset}", flush=True)
            if not payload.get("exceededTransferLimit", False) and len(feats) < page:
                break
            time.sleep(sleep_s)
    return rows


def discover_and_download(raw_dir: Path) -> list[Path]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=180.0, follow_redirects=True, headers={"User-Agent": UA}) as client:
        html = client.get(REPORTS_PAGE).text
        urls = sorted(
            {
                m.split("?")[0]
                for m in re.findall(r"https://www\.capecoral\.gov/Documents/[^\"']+", html)
                if any(f"202{y}" in m for y in "12345")
                and ("Issued" in m or "ISSUED" in m or "issued" in m)
                and "2019" not in m
                and "2020" not in m
            }
        )
        paths: list[Path] = []
        for url in urls:
            name = unquote(url.rsplit("/", 1)[-1])
            dest = raw_dir / name
            if not dest.exists() or dest.stat().st_size < 1000:
                print(f"GET {name}", flush=True)
                resp = client.get(url)
                resp.raise_for_status()
                dest.write_bytes(resp.content)
                time.sleep(0.5)
            paths.append(dest)
        return paths


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--since", default="2021-01-01")
    ap.add_argument("--preview-rows", type=int, default=100)
    ap.add_argument("--skip-opendata", action="store_true")
    args = ap.parse_args()
    since = date.fromisoformat(args.since)

    raw_dir = ROOT / "data" / "raw" / "fl_cape_coral_history"
    bronze = ROOT / "data" / "bronze" / "fl_cape_coral_history"
    bronze.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_csv = bronze / f"fl_cape_coral_history_permits_{since.isoformat()}_{stamp}.csv"
    preview_csv = bronze / "sample_preview.csv"
    meta_path = bronze / "fl_cape_coral_history_extract_meta.json"

    files = discover_and_download(raw_dir)
    by_permit: dict[str, dict[str, str]] = {}
    per_file: dict[str, int] = {}
    for path in files:
        print(f"parse {path.name}", flush=True)
        rows = rows_from_excel(path, since)
        per_file[path.name] = len(rows)
        for row in rows:
            # prefer later issued_date / richer valuation when dupes
            prev = by_permit.get(row["permit_number"])
            if prev is None or row["issued_date"] >= prev["issued_date"]:
                by_permit[row["permit_number"]] = row
        print(f"  kept {len(rows)}", flush=True)

    if not args.skip_opendata:
        print("fetch OpenData Feature table …", flush=True)
        od = fetch_opendata(since)
        per_file["opendata_mapserver_1"] = len(od)
        for row in od:
            prev = by_permit.get(row["permit_number"])
            if prev is None or row["issued_date"] >= prev.get("issued_date", ""):
                by_permit[row["permit_number"]] = row
        print(f"  OpenData rows {len(od)}", flush=True)

    merged = sorted(by_permit.values(), key=lambda r: (r["issued_date"], r["permit_number"]))
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CANON)
        w.writeheader()
        w.writerows(merged)

    with preview_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CANON)
        w.writeheader()
        w.writerows(merged[: args.preview_rows])

    dates = [r["issued_date"] for r in merged if r["issued_date"]]
    meta = {
        "jurisdiction_id": "fl_cape_coral_history",
        "rows": len(merged),
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
        "per_file": per_file,
        "csv": str(out_csv),
        "bytes": out_csv.stat().st_size,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "since": since.isoformat(),
        "notes": "Official Cape Coral All Issued Permits Excels + OpenData MapServer/1 merge; deduped by permit_number.",
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
