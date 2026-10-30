"""Load and validate config/jurisdictions.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "config" / "jurisdictions.yaml"
DEFAULT_ASSUMPTIONS = ROOT / "config" / "assumptions.yaml"


class Jurisdiction(BaseModel):
    id: str
    name: str
    state: str = "FL"
    county: str | None = None
    county_fips: str
    level: str  # county | city
    covers: str  # unincorporated_only | full_county | city | critical
    tier: str  # A | B | C
    connector: str | None = None
    endpoint: str | None = None
    layer: int | None = 0
    bronze_glob: str | None = None
    raw_glob: str | None = None
    field_map: dict[str, str] = Field(default_factory=dict)
    date_format: str = "mixed"
    issued_date_min: str | None = None
    notes: str | None = None
    # Export / live-pull helpers
    export_date_field: str | None = None
    arcgis_date_format: str | None = None  # date_only | epoch_ms | sql_date | iso_text | year_int
    page_size: int | None = None
    order_by_fields: str | None = None
    return_geometry: bool | None = None
    export_monthly: bool | None = None
    export_where: str | None = None  # optional full WHERE override (skips date clauses)


def load_jurisdictions(path: Path | str = DEFAULT_REGISTRY) -> list[Jurisdiction]:
    raw = yaml.safe_load(Path(path).read_text()) or []
    if not isinstance(raw, list):
        raise ValueError(f"jurisdictions.yaml must be a list, got {type(raw)}")
    return [Jurisdiction.model_validate(item) for item in raw]


def load_jurisdictions_raw(path: Path | str = DEFAULT_REGISTRY) -> list[dict[str, Any]]:
    """Dicts with YAML extras preserved (export tooling)."""
    raw = yaml.safe_load(Path(path).read_text()) or []
    if not isinstance(raw, list):
        raise ValueError(f"jurisdictions.yaml must be a list, got {type(raw)}")
    out: list[dict[str, Any]] = []
    for item in raw:
        model = Jurisdiction.model_validate(item)
        out.append({**item, **model.model_dump()})
    return out


def get_jurisdiction(jurisdiction_id: str, path: Path | str = DEFAULT_REGISTRY) -> Jurisdiction:
    for j in load_jurisdictions(path):
        if j.id == jurisdiction_id:
            return j
    raise KeyError(f"Unknown jurisdiction_id: {jurisdiction_id}")


def load_assumptions(path: Path | str = DEFAULT_ASSUMPTIONS) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text()) or {}
