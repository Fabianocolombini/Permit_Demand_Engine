"""Site geography helpers.

Miami-Dade Hub layer has City/State but NO site ZIP and NO geometry.
ContractorZip is contractor HQ — NEVER use it as site ZIP.

This module:
  1. Reports ZIP / city coverage stats
  2. Optionally geocodes a small address sample via Census Bureau batch API
     to fill missing ZIP / lat / lon (best-effort; offline-safe if skipped)
"""

from __future__ import annotations

import csv
import io
import time
from pathlib import Path
from typing import Any

import httpx

CENSUS_GEOCODER = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"
CENSUS_BENCHMARK = "Public_AR_Current"


def coverage_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {
            "n": 0,
            "pct_city": 0.0,
            "pct_zip": 0.0,
            "pct_valuation": 0.0,
            "pct_latlon": 0.0,
        }

    def _ok(v: Any) -> bool:
        return v is not None and str(v).strip() not in {"", "None", "null"}

    n_city = sum(1 for r in rows if _ok(r.get("city")))
    n_zip = sum(1 for r in rows if _ok(r.get("zip")))
    n_val = sum(1 for r in rows if r.get("declared_valuation") is not None)
    n_geo = sum(1 for r in rows if r.get("lat") is not None and r.get("lon") is not None)
    return {
        "n": n,
        "n_city": n_city,
        "n_zip": n_zip,
        "n_valuation": n_val,
        "n_latlon": n_geo,
        "pct_city": 100.0 * n_city / n,
        "pct_zip": 100.0 * n_zip / n,
        "pct_valuation": 100.0 * n_val / n,
        "pct_latlon": 100.0 * n_geo / n,
    }


def _parse_census_batch_line(line: str) -> dict[str, Any] | None:
    # Census returns CSV: id, input address, match flag, match type, matched address, lon/lat, tiger…, …
    reader = csv.reader([line])
    parts = next(reader)
    if len(parts) < 6:
        return None
    match_flag = parts[2].strip().upper() if len(parts) > 2 else ""
    if match_flag != "MATCH":
        return None
    matched = parts[4] if len(parts) > 4 else ""
    coords = parts[5] if len(parts) > 5 else ""
    lon = lat = None
    if coords and "," in coords:
        try:
            lon_s, lat_s = coords.split(",", 1)
            lon, lat = float(lon_s), float(lat_s)
        except ValueError:
            pass
    zip_code = None
    # Matched address often ends with ", FL, 33101" or similar
    if matched:
        bits = [b.strip() for b in matched.split(",")]
        for b in reversed(bits):
            tok = b.split()[-1] if b.split() else ""
            if tok.isdigit() and len(tok) == 5:
                zip_code = tok
                break
    return {"lat": lat, "lon": lon, "zip": zip_code, "matched_address": matched}


def census_batch_geocode(
    addresses: list[tuple[str, str, str, str]],
    *,
    batch_size: int = 1000,
    timeout: float = 120.0,
    sleep_s: float = 0.5,
) -> dict[str, dict[str, Any]]:
    """Geocode (id, street, city, state) tuples via Census addressbatch.

    Returns map id → {lat, lon, zip, matched_address}.
    On network failure returns {} (caller should treat as TODO / skip).
    """
    results: dict[str, dict[str, Any]] = {}
    if not addresses:
        return results

    try:
        client = httpx.Client(timeout=timeout)
    except Exception:
        return results

    with client:
        for i in range(0, len(addresses), batch_size):
            chunk = addresses[i : i + batch_size]
            buf = io.StringIO()
            w = csv.writer(buf)
            for aid, street, city, state in chunk:
                # Census batch format: Unique ID, Street address, City, State, ZIP
                w.writerow([aid, street, city, state, ""])
            payload = buf.getvalue().encode("utf-8")
            try:
                resp = client.post(
                    CENSUS_GEOCODER,
                    data={"benchmark": CENSUS_BENCHMARK},
                    files={"addressFile": ("addresses.csv", payload, "text/csv")},
                )
                resp.raise_for_status()
            except Exception as exc:  # noqa: BLE001 — soft-fail geocode
                print(f"[geocode] Census batch failed (skipping): {exc}")
                return results

            for line in resp.text.splitlines():
                line = line.strip()
                if not line:
                    continue
                reader = csv.reader([line])
                parts = next(reader)
                if not parts:
                    continue
                aid = parts[0].strip().strip('"')
                parsed = _parse_census_batch_line(line)
                if parsed:
                    results[aid] = parsed
            time.sleep(sleep_s)
    return results


def enrich_missing_zip(
    permits: list[dict[str, Any]],
    *,
    max_sample: int = 200,
    enabled: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fill zip/lat/lon for a small sample missing ZIP via Census batch.

    Does NOT use ContractorZip. Returns (updated_rows, geocode_meta).
    """
    meta: dict[str, Any] = {
        "enabled": enabled,
        "requested": 0,
        "matched": 0,
        "note": (
            "Site ZIP absent on Miami-Dade Hub table; ContractorZip intentionally unused. "
            "Census batch used only for a small sample when enabled."
        ),
    }
    if not enabled or max_sample <= 0:
        meta["note"] += " Geocode skipped."
        return permits, meta

    need: list[tuple[str, str, str, str]] = []
    index_by_id: dict[str, int] = {}
    for idx, p in enumerate(permits):
        if p.get("zip"):
            continue
        addr = (p.get("address_raw") or "").strip()
        if not addr:
            continue
        city = (p.get("city") or "").strip() or "Miami"
        state = (p.get("state") or "FL").strip()
        aid = f"{idx}"
        need.append((aid, addr, city, state))
        index_by_id[aid] = idx
        if len(need) >= max_sample:
            break

    meta["requested"] = len(need)
    if not need:
        return permits, meta

    geo = census_batch_geocode(need)
    meta["matched"] = len(geo)
    for aid, g in geo.items():
        i = index_by_id.get(aid)
        if i is None:
            continue
        if g.get("zip") and not permits[i].get("zip"):
            permits[i]["zip"] = g["zip"]
            permits[i]["geocode_source"] = "census_batch"
            permits[i]["geocode_confidence"] = 0.7
        if g.get("lat") is not None and permits[i].get("lat") is None:
            permits[i]["lat"] = g["lat"]
            permits[i]["lon"] = g["lon"]
            permits[i]["geocode_source"] = permits[i].get("geocode_source") or "census_batch"
            permits[i]["geocode_confidence"] = permits[i].get("geocode_confidence") or 0.7

    return permits, meta


def write_coverage_report(stats: dict[str, Any], meta: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Geography coverage — silver.permits sample",
        "",
        f"- Rows: **{stats.get('n', 0)}**",
        f"- City present: **{stats.get('pct_city', 0):.1f}%** ({stats.get('n_city', 0)})",
        f"- Site ZIP present: **{stats.get('pct_zip', 0):.1f}%** ({stats.get('n_zip', 0)})",
        f"- Valuation parsed: **{stats.get('pct_valuation', 0):.1f}%** ({stats.get('n_valuation', 0)})",
        f"- Lat/lon present: **{stats.get('pct_latlon', 0):.1f}%** ({stats.get('n_latlon', 0)})",
        "",
        "## Notes",
        "",
        f"- Geocode enabled: `{meta.get('enabled')}` — requested={meta.get('requested')}, matched={meta.get('matched')}",
        f"- {meta.get('note', '')}",
        "- **Never** use `ContractorZip` as site ZIP.",
        "",
    ]
    path.write_text("\n".join(lines))
