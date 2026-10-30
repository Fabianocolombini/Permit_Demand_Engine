"""Deterministic classification — TOM universe → SAM (Tigre/Dura) subset.

**TOM** = total permits ingested (raw universe; every silver row).
**SAM** = subset that affects Tigre USA / Dura:
  - plumbing (new / repipe / remodel), including **new residential construction**
    (ApplicationType NEW, new SFR/townhouse/etc.) — plumbing rough-in is implied
    for the whole job, not only PLUM-typed permits
  - pool / spa
  - irrigation
  Explicitly not SAM: roof, windows, AC-only, fence-only, demolition,
  electrical-only, fire protection, site utility, water-heater-only.

Keep signals: PLUM/MPLU + pool / irrigation / repipe / remodel plumbing +
new residential building.
Exclude noise: roof / windows / AC-only / demo / fence / electrical-only
when those trades dominate (even on an SFR parcel).
"""

from __future__ import annotations

import re
from typing import Any

# SAM = Tigre/Dura commercial scope (Fabiano naming)
SAM_CATEGORIES = frozenset(
    {
        "res_new_plumbing",  # includes new residential construction (implied rough-in)
        "res_repipe",
        "res_remodel_plumbing",
        "irrigation",
        "pool_spa",
    }
)

TIGRE_DURA_CATEGORIES = SAM_CATEGORIES  # back-compat

_RES_USE = (
    r"single\s+fam|sfr|town\s*house|townhouse|duplex|tri-?plex|quad(?:plex)?|"
    r"multi[\s-]?fam|condo(?:minium)?|apartment|residence|residential|dwelling|"
    r"zero\s+lot|cluster\s+home|mobile\s+home|modular"
)

# Ordered: first regex match wins
RULES: list[tuple[str, str, float]] = [
    (
        r"\bre-?pipe\b|repipe|water\s+line\s+replacement|repipe\s+entire|whole[\s-]?house\s+re-?pipe",
        "res_repipe",
        0.95,
    ),
    (r"\bfire\s+sprinkler\b|fire\s+protection|nfpa|\bfire\s+backflow\b", "fire_protection", 0.95),
    (r"\bpool[_\s-]?spa\b|\bpool\b|\bspa\b|swimming|jacuzzi|hot\s+tub", "pool_spa", 0.90),
    (
        r"\birrigation\b|lawn\s+sprinkler|landscape\s+irrig|(?<!fire\s)\bsprinkler\s+system\b|\birri\b",
        "irrigation",
        0.88,
    ),
    (r"water\s+heater|\bwh\s+replace|\btankless\b", "res_water_heater", 0.93),
    (r"(bath|kitchen|bathroom).{0,25}remodel|remodel.{0,25}plumb", "res_remodel_plumbing", 0.80),
    # PLUM/MPLU / Plumbing* before site_utility so typed plumbing stays in SAM
    (
        r"(^|[^A-Z])PLUM([^A-Z]|$)|(^|[^A-Z])MPLU([^A-Z]|$)|plumbing\s+express|\bplumbing\b",
        "res_new_plumbing",
        0.78,
    ),
    (r"commercial.{0,20}plumb|tenant\s+(improvement|build).{0,30}plumb", "comm_plumbing", 0.82),
    # --- New residential construction → SAM as res_new_plumbing ---
    # Miami-Dade ApplicationTypeDescription "NEW" ↔ residential use (either order)
    (
        rf"(?:^|[\s|,;])NEW(?:[\s|,;]|$).{{0,200}}(?:{_RES_USE})|"
        rf"(?:{_RES_USE}).{{0,200}}(?:^|[\s|,;])NEW(?:[\s|,;]|$)",
        "res_new_plumbing",
        0.88,
    ),
    # Orlando Socrata: "Building Permit | New" (worktype New on building apps)
    (
        r"building\s+permit\s*[|\s/-]+new\b|"
        r"(?:^|[\s|,;])new(?:[\s|,;]|$).{0,40}building\s+permit",
        "res_new_plumbing",
        0.80,
    ),
    # Explicit new-house / new-construction language
    (
        rf"\bnew\s+(?:single\s+family|sfr|residence|dwelling|home|house|town\s*house|"
        rf"townhouse|duplex|multi[\s-]?fam|construction)\b|"
        rf"\bnew\s+construction\b.{{0,80}}(?:{_RES_USE})|"
        rf"rough[-\s]?in\s+plumb|plumbing\s+rough|"
        rf"(new|nueva).{{0,30}}(single\s+family|sfr|residence|dwelling).{{0,40}}plumb",
        "res_new_plumbing",
        0.85,
    ),
    # BLDG/MBLD + NEW application + residential (order-flexible within window)
    (
        rf"(?:^|[^A-Z])(?:BLDG|MBLD)(?:[^A-Z]|$).{{0,40}}\bNEW\b.{{0,120}}(?:{_RES_USE})|"
        rf"\bNEW\b.{{0,40}}(?:^|[^A-Z])(?:BLDG|MBLD)(?:[^A-Z]|$).{{0,120}}(?:{_RES_USE})",
        "res_new_plumbing",
        0.84,
    ),
    # Non-PLUM infrastructure (not SAM)
    (
        r"\blead\s+service\s+line\b|water\s+main|sewer\s+lateral|force\s+main|"
        r"sewer\s+replacement|water\s+service\s+replace",
        "site_utility",
        0.92,
    ),
]

# Noise outside SAM — applied when trade noise dominates (see classify_text)
EXCLUDE_NOISE: list[tuple[str, str]] = [
    (r"\bre-?roof\b|\broof\b|roofing|shingle|tile\s+roof|roof\s+express|roof\s+standard", "roof"),
    (r"\bwindows?\b|\bdoors?\b|impact\s+window|door\s+and\s+window|ent\s+replacement", "windows_doors"),
    (
        r"\b(a/?c|hvac|air\s+condition|mechanical\s+express|mech\s+change|like\s+for\s+like|"
        r"same\s+for\s+same|equipment\s+equivalent\s+changeout|ton\s+system)\b|"
        r"(^|[^A-Z])MECH([^A-Z]|$)|(^|[^A-Z])MMEC([^A-Z]|$)",
        "ac_mechanical",
    ),
    (r"\bdemolition\b|\bdemo\b|tear[\s-]?down", "demolition"),
    (r"\bfence\b|\bsolar\b|\bgenerator\b|\bdriveway\b|\bsiding\b|\bsign\b|\bantenna\b", "misc_non_plumbing"),
    (r"(^|[^A-Z])ELEC([^A-Z]|$)|(^|[^A-Z])MELE([^A-Z]|$)|electrical\s+express|\belectrical\b", "electrical"),
]

_PLUMB_KEEP = re.compile(
    r"\bplumb|\bplum\b|\bmplu\b|\bre-?pipe\b|\brepipe\b|\bpool\b|\bspa\b|"
    r"\birrigation\b|\bsprinkler\b|\bwater\s+heater\b|\bwater\s+line\b|"
    r"\bsewer\b|\bbackflow\b|\birri\b|"
    r"\bnew\s+(?:single|sfr|residence|dwelling|home|house|construction|town)|"
    r"(?:^|[\s|,;])NEW(?:[\s|,;]|$)",
    re.IGNORECASE,
)


def _blob(*parts: str | None) -> str:
    return " ".join(p for p in parts if p)


def is_sam(category: str | None) -> bool:
    return bool(category) and category in SAM_CATEGORIES


def _is_noise_dominant(blob: str) -> tuple[bool, str]:
    """Roof/windows/AC/fence/etc. without plumbing/pool/irrig/new-build keep."""
    if re.search(
        r"\bplumb|\bpool\b|\bspa\b|\birrigation\b|\bre-?pipe\b|\brepipe\b|"
        r"\bnew\s+(?:single|sfr|residence|dwelling|home|house|construction|town)|"
        r"building\s+permit\s*[|\s/-]+new\b|"
        r"(?:^|[\s|,;])NEW(?:[\s|,;]|$).{0,200}(?:" + _RES_USE + r")|"
        r"(?:" + _RES_USE + r").{0,200}(?:^|[\s|,;])NEW(?:[\s|,;]|$)",
        blob,
        flags=re.IGNORECASE,
    ):
        return False, ""
    for pattern, reason in EXCLUDE_NOISE:
        if re.search(pattern, blob, flags=re.IGNORECASE):
            return True, reason
    return False, ""


def classify_text(*parts: str | None) -> tuple[str, str, float]:
    blob = _blob(*parts)
    if not blob.strip():
        return "other", "unclassified", 0.0

    # Noise trades win over bare BLDG+SFR (e.g. RE-ROOF on single-family)
    noisy, reason = _is_noise_dominant(blob)
    if noisy:
        return "other", f"excluded_{reason}", 0.0

    for pattern, category, conf in RULES:
        if re.search(pattern, blob, flags=re.IGNORECASE):
            return category, "regex", conf

    if not _PLUMB_KEEP.search(blob):
        for pattern, reason in EXCLUDE_NOISE:
            if re.search(pattern, blob, flags=re.IGNORECASE):
                return "other", f"excluded_{reason}", 0.0

    return "other", "unclassified", 0.0


def classify_permit_dict(row: dict[str, Any]) -> dict[str, Any]:
    cat, method, conf = classify_text(
        row.get("permit_type_raw"),
        row.get("work_class_raw"),
        row.get("description_raw"),
    )
    out = dict(row)
    out["category"] = cat
    out["classification_method"] = method
    out["classification_confidence"] = conf
    out["in_sam"] = is_sam(cat)
    return out
