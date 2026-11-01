"""Map raw jurisdiction rows → Permit using field_map from the registry."""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any

from src.normalize.schema import Permit
from src.registry import Jurisdiction

# Never treat these as site ZIP
_CONTRACTOR_ZIP_FIELDS = {"contractorzip", "contractor_zip", "contrzip"}


def parse_date(value: Any, fmt_hint: str = "mixed") -> date | None:
    """Normalize epoch-ms and ISO/text dates (Miami-Dade mixed trap)."""
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, (int, float)):
        # St. Pete PermitsExternal stores PERMITISSUEDATE as YYMMDD int (e.g. 210413).
        # Must run before epoch heuristics (210413 as seconds → 1970-01-03).
        if float(value).is_integer():
            s = str(int(value))
            if len(s) == 6:
                try:
                    return datetime.strptime(s, "%y%m%d").date()
                except ValueError:
                    pass
        # Heuristic: epoch ns / µs / ms / seconds (2021 ms ≈ 1.6e12)
        ts = float(value)
        if ts > 1e17:  # nanoseconds
            ts /= 1e9
        elif ts > 1e14:  # microseconds
            ts /= 1e6
        elif ts > 1e11:  # milliseconds
            ts /= 1e3
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc).date()
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # Numeric string that looks like epoch
        if s.isdigit() and len(s) >= 10:
            return parse_date(int(s), fmt_hint)
        # Hillsborough period key YYYY_MM
        if len(s) == 7 and s[4] == "_" and s[:4].isdigit() and s[5:].isdigit():
            try:
                return date(int(s[:4]), int(s[5:]), 1)
            except ValueError:
                return None
        # St. Pete PermitsExternal: YYMMDD text (e.g. 210413 → 2021-04-13)
        if len(s) == 6 and s.isdigit():
            try:
                return datetime.strptime(s, "%y%m%d").date()
            except ValueError:
                pass
        for f in (
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y_%m",
            "%d-%b-%y",  # Auburn Sarasota In_Date e.g. 4-Jan-21
            "%d-%b-%Y",
        ):
            try:
                return datetime.strptime(s[:26], f).date()
            except ValueError:
                continue
        # Lee Auburn Record_Num embeds year: RES2022-09504 → 2022-01-01
        m = re.search(r"(20\d{2})", s)
        if m and ("RES" in s.upper() or "COM" in s.upper() or "-" in s):
            try:
                return date(int(m.group(1)), 1, 1)
            except ValueError:
                pass
    return None


def parse_valuation_usd(value: Any) -> float | None:
    """Parse EstimatedValue-style strings as USD dollars (not cents)."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        return v if v >= 0 else None
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "").replace("$", "")
        if not cleaned:
            return None
        try:
            v = float(cleaned)
        except ValueError:
            return None
        return v if v >= 0 else None
    return None


def parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "")
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def parse_int(value: Any) -> int | None:
    f = parse_float(value)
    if f is None:
        return None
    try:
        return int(f)
    except (ValueError, OverflowError):
        return None


def _get(row: dict[str, Any], field: str | None) -> Any:
    if not field:
        return None
    if field in row:
        return row[field]
    # case-insensitive fallback
    lower = {k.lower(): k for k in row}
    key = lower.get(field.lower())
    return row[key] if key else None


_ZIP_RE = re.compile(r"\b(\d{5})(?:-\d{4})?\b")
# Trailing / state-qualified ZIP only — do NOT treat leading house numbers as ZIP
# e.g. "18964 BOBOLINK DR" must not yield 18964; "… FL 33101" / "…, 33101" is OK.
_ADDR_ZIP_RE = re.compile(
    r"(?:"
    r"(?:,\s*|\s+)(?:[A-Za-z]{2}\s+)?(\d{5})(?:-\d{4})?\s*$"  # end of address
    r"|"
    r"\b(?:FL|Florida)\s+(\d{5})(?:-\d{4})?\b"  # explicit FL + ZIP
    r")",
    re.IGNORECASE,
)


def extract_site_zip_from_address(address: str | None) -> str | None:
    """Best-effort site ZIP from PropertyAddress — never from contractor fields.

    Miami-Dade Hub rows usually have street + city only (no ZIP in address).
    Leading 5-digit house numbers are ignored.
    """
    if not address:
        return None
    m = _ADDR_ZIP_RE.search(address.strip())
    if not m:
        return None
    return m.group(1) or m.group(2)


def is_owner_builder(name: Any) -> bool:
    if name is None:
        return False
    s = str(name).strip().upper()
    return s in {"OWNER", "OWNER BUILDER", "OWNER/BUILDER", "N/A", "NA", ""}


def map_row(
    row: dict[str, Any],
    jurisdiction: Jurisdiction,
    *,
    ingested_at: datetime | None = None,
    issued_date_min: date | None = None,
) -> Permit | None:
    """Map one raw dict to Permit. Returns None if required fields missing / filtered."""
    fm = jurisdiction.field_map
    # Guard: never pull site ZIP from contractor columns even if misconfigured
    zip_field = fm.get("zip")
    if zip_field and zip_field.lower().replace("_", "") in {
        "contractorzip",
        "contrzip",
    }:
        zip_field = None

    permit_id = _get(row, fm.get("permit_id", "PermitNumber"))
    if permit_id is None or str(permit_id).strip() == "":
        return None
    permit_id = str(permit_id).strip()

    issued = parse_date(_get(row, fm.get("issued_date")), jurisdiction.date_format)
    if issued is None:
        return None
    if issued_date_min and issued < issued_date_min:
        return None

    address = _get(row, fm.get("address_raw"))
    address_raw = "" if address is None else str(address).strip()
    # Manatee PermitData (and similar) split house/street across columns
    if not address_raw:
        parts: list[str] = []
        for key in ("HOUSE", "STREETDIR", "STREETNAME", "STREETSUFFIX", "UNITNUM"):
            val = row.get(key)
            if val is None:
                continue
            s = str(val).strip()
            if not s or s.upper() in {"NA", "N/A", "NONE", "NULL"}:
                continue
            parts.append(s)
        address_raw = " ".join(parts)

    city_val = _get(row, fm.get("city"))
    city = None if city_val is None or str(city_val).strip() == "" else str(city_val).strip()

    state_val = _get(row, fm.get("state"))
    state = (
        jurisdiction.state
        if state_val is None or str(state_val).strip() == ""
        else str(state_val).strip()
    )

    # Site ZIP: mapped field (if not contractor) → address parse → else None
    site_zip = None
    zip_source = None
    if zip_field:
        raw_zip = _get(row, zip_field)
        if raw_zip is not None and str(raw_zip).strip():
            m = _ZIP_RE.search(str(raw_zip))
            if m:
                site_zip = m.group(1)
                zip_source = "field_map"
    if site_zip is None:
        site_zip = extract_site_zip_from_address(address_raw)
        if site_zip:
            zip_source = "address_parse"

    # Explicitly ignore ContractorZip even if present on the row
    for k in row:
        if k.lower().replace("_", "") in _CONTRACTOR_ZIP_FIELDS:
            break  # acknowledged and unused

    res_flag = _get(row, fm.get("is_residential"))
    is_residential = True
    if res_flag is not None:
        s = str(res_flag).strip().upper()
        if s in {"C", "COMMERCIAL", "COMM", "N", "NO", "0", "FALSE"}:
            is_residential = False
        elif s in {"R", "RESIDENTIAL", "RES", "Y", "YES", "1", "TRUE"}:
            is_residential = True

    contractor = _get(row, fm.get("contractor_name"))
    contractor_name = None if contractor is None else str(contractor).strip() or None

    valuation = parse_valuation_usd(_get(row, fm.get("declared_valuation")))

    work_class = _get(row, fm.get("work_class_raw"))
    # Enrich work_class for classify: Miami-Dade ApplicationType* carries NEW vs
    # RE-ROOF; ProposedUse* carries SFR/townhouse; CategoryDescription slots too.
    cat_bits: list[str] = []
    for key in (
        "ApplicationTypeDescription",
        "ApplicationTypeCode",
        "ProposedUseDescription",
        "ProposedUseCode",
        "TYPEOFPROJECT",
        "BUILDINGTYPE",
        "CATEGORY",
        "SUBTYPE",
    ):
        # Skip if this key is already the mapped work_class / permit_type / desc
        mapped = {
            (fm.get("work_class_raw") or "").lower(),
            (fm.get("permit_type_raw") or "").lower(),
            (fm.get("description_raw") or "").lower(),
        }
        if key.lower() in mapped:
            continue
        cd = row.get(key)
        if cd is not None and str(cd).strip() and str(cd).strip().upper() not in {"NA", "N/A"}:
            cat_bits.append(str(cd).strip())
    for i in range(1, 11):
        cd = row.get(f"CategoryDescription{i}")
        if cd is not None and str(cd).strip():
            cat_bits.append(str(cd).strip())
    work_class_raw = None
    if work_class is not None and str(work_class).strip():
        work_class_raw = str(work_class).strip()
    if cat_bits:
        # de-dupe preserving order
        seen: set[str] = set()
        uniq: list[str] = []
        for b in cat_bits:
            if b not in seen:
                seen.add(b)
                uniq.append(b)
        extra = " | ".join(uniq)
        if work_class_raw and work_class_raw in seen:
            work_class_raw = extra
        else:
            work_class_raw = f"{work_class_raw} | {extra}" if work_class_raw else extra

    desc = _get(row, fm.get("description_raw"))
    ptype = _get(row, fm.get("permit_type_raw"))

    now = ingested_at or datetime.now(timezone.utc).replace(tzinfo=None)

    permit = Permit(
        permit_id=permit_id,
        jurisdiction_id=jurisdiction.id,
        source_tier=jurisdiction.tier if jurisdiction.tier in {"A", "B", "C"} else "A",  # type: ignore[arg-type]
        ingested_at=now,
        applied_date=parse_date(_get(row, fm.get("applied_date")), jurisdiction.date_format),
        issued_date=issued,
        address_raw=address_raw,
        city=city,
        county=jurisdiction.county or jurisdiction.name,
        county_fips=jurisdiction.county_fips,
        state=state,
        zip=site_zip,
        permit_type_raw=None if ptype is None else str(ptype).strip() or None,
        work_class_raw=work_class_raw,
        description_raw=None if desc is None else str(desc).strip() or None,
        is_residential=is_residential,
        declared_valuation=valuation,
        square_feet=parse_float(_get(row, fm.get("square_feet"))),
        units=parse_int(_get(row, fm.get("units"))),
        contractor_name=contractor_name,
        contractor_license=(
            None
            if _get(row, fm.get("contractor_license")) is None
            else str(_get(row, fm.get("contractor_license"))).strip() or None
        ),
        is_owner_builder=is_owner_builder(contractor_name),
        project_key=f"{jurisdiction.id}|{address_raw.upper()}|{issued.isoformat()}",
    )
    # zip_source kept local for future diagnostics (address_parse | field_map | None)
    _ = zip_source
    return permit
