"""Fittings demand estimates from config/assumptions.yaml (V1.1 §2.2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MaterialEstimate:
    low: float
    base: float
    high: float


def estimate_fittings_value(
    category: str,
    valuation: float | None,
    assumptions: dict[str, Any],
) -> MaterialEstimate:
    cfg = (assumptions.get("material_content") or {}).get(category)
    if cfg is None:
        return MaterialEstimate(0.0, 0.0, 0.0)

    if cfg.get("method") == "fixed_per_project":
        v = cfg["fittings_value_usd"]
        return MaterialEstimate(float(v["low"]), float(v["base"]), float(v["high"]))

    if not valuation or valuation <= 0:
        return MaterialEstimate(0.0, 0.0, 0.0)

    out: dict[str, float] = {}
    for s in ("low", "base", "high"):
        factor = 1.0
        for key in (
            "plumbing_share_of_project_value",
            "material_share_of_plumbing",
            "fittings_share_of_material",
            "fittings_share_of_project",
        ):
            if key in cfg:
                factor *= float(cfg[key][s])
        out[s] = float(valuation) * factor
    return MaterialEstimate(out["low"], out["base"], out["high"])
