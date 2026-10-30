"""Guard: never treat house numbers or ContractorZip as site ZIP."""

from datetime import datetime

from src.normalize.mapper import extract_site_zip_from_address, map_row
from src.registry import Jurisdiction


def test_house_number_not_zip():
    assert extract_site_zip_from_address("18964 BOBOLINK DR") is None
    assert extract_site_zip_from_address("10343 SW 126 ST") is None


def test_trailing_fl_zip():
    assert extract_site_zip_from_address("123 MAIN ST, MIAMI, FL 33101") == "33101"
    assert extract_site_zip_from_address("123 MAIN ST FL 33176-0001") == "33176"


def test_contractor_zip_ignored():
    j = Jurisdiction(
        id="fl_miami_dade_county",
        name="test",
        county="Miami-Dade",
        county_fips="12086",
        level="county",
        covers="unincorporated_only",
        tier="A",
        connector="file",
        field_map={
            "permit_id": "PermitNumber",
            "issued_date": "PermitIssuedDate",
            "address_raw": "PropertyAddress",
            "city": "City",
            "declared_valuation": "EstimatedValue",
            "zip": "ContractorZip",  # misconfiguration must be ignored
        },
        date_format="mixed",
    )
    row = {
        "PermitNumber": "X1",
        "PermitIssuedDate": "2024-06-01",
        "PropertyAddress": "100 SW 1 ST",
        "City": "MIAMI",
        "EstimatedValue": "25000",
        "ContractorZip": "33196",
    }
    p = map_row(row, j, ingested_at=datetime(2024, 1, 1))
    assert p is not None
    assert p.zip is None
    assert p.declared_valuation == 25000.0
