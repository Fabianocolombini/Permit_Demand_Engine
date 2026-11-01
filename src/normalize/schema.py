"""Pydantic Permit schema — V1.1 §1.6."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel

Category = Literal[
    "res_new_plumbing",
    "res_repipe",
    "res_remodel_plumbing",
    "res_water_heater",
    "irrigation",
    "pool_spa",
    "comm_plumbing",
    "institutional",
    "fire_protection",
    "site_utility",
    "other",
]


class Permit(BaseModel):
    permit_id: str
    jurisdiction_id: str
    source_tier: Literal["A", "B", "C"]
    ingested_at: datetime

    applied_date: Optional[date] = None
    issued_date: date
    final_date: Optional[date] = None

    address_raw: str = ""
    city: Optional[str] = None
    county: str
    county_fips: str
    state: str = "FL"
    zip: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    geocode_confidence: Optional[float] = None
    geocode_source: Optional[str] = None

    permit_type_raw: Optional[str] = None
    work_class_raw: Optional[str] = None
    description_raw: Optional[str] = None
    category: Category = "other"
    classification_method: str = "unclassified"
    classification_confidence: float = 0.0
    is_new_construction: bool = False
    is_residential: bool = True

    declared_valuation: Optional[float] = None
    square_feet: Optional[float] = None
    units: Optional[int] = None

    contractor_name: Optional[str] = None
    contractor_license: Optional[str] = None
    is_owner_builder: bool = False

    project_key: Optional[str] = None
