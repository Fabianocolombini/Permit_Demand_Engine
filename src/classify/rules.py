"""Deterministic classification rules stub (V1.1 §1.8). Full apply deferred; used lightly in 04_classify."""

from __future__ import annotations

import re
from typing import Any

RULES: list[tuple[str, str, float]] = [
    (r"\bre-?pipe\b|repipe|water\s+line\s+replacement|repipe\s+entire", "res_repipe", 0.95),
    (r"\blead\s+service\s+line\b|water\s+main|sewer\s+lateral|force\s+main", "site_utility", 0.92),
    (r"\bfire\s+sprinkler\b|fire\s+protection|nfpa", "fire_protection", 0.95),
    (r"\bpool\b|\bspa\b|swimming|jacuzzi", "pool_spa", 0.90),
    (
        r"\birrigation\b|lawn\s+sprinkler|landscape\s+irrig|(?<!fire\s)\bsprinkler\s+system\b",
        "irrigation",
        0.88,
    ),
    (r"water\s+heater|\bwh\s+replace", "res_water_heater", 0.93),
    (
        r"(new|nueva).{0,30}(single\s+family|sfr|residence|dwelling).{0,40}plumb|"
        r"rough[-\s]?in\s+plumb|plumbing\s+rough",
        "res_new_plumbing",
        0.85,
    ),
    (r"(bath|kitchen|bathroom).{0,25}remodel|remodel.{0,25}plumb", "res_remodel_plumbing", 0.80),
    (r"commercial.{0,20}plumb|tenant\s+(improvement|build).{0,30}plumb", "comm_plumbing", 0.82),
]


def classify_text(*parts: str | None) -> tuple[str, str, float]:
    blob = " ".join(p for p in parts if p).lower()
    if not blob.strip():
        return "other", "unclassified", 0.0
    for pattern, category, conf in RULES:
        if re.search(pattern, blob, flags=re.IGNORECASE):
            return category, "regex", conf
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
    return out
