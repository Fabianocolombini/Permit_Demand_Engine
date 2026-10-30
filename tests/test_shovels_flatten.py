"""Unit tests for Shovels flatten / key helpers (no network)."""

from __future__ import annotations

import pytest

from src.ingest.shovels import (
    ENV_API_KEY,
    ShovelsAuthError,
    api_key_length,
    flatten_permit,
    require_api_key,
)


def test_api_key_length_empty():
    assert api_key_length({}) == 0
    assert api_key_length({ENV_API_KEY: ""}) == 0
    assert api_key_length({ENV_API_KEY: "abc123"}) == 6


def test_require_api_key_raises():
    with pytest.raises(ShovelsAuthError):
        require_api_key({})


def test_flatten_permit_address_and_cents():
    row = flatten_permit(
        {
            "id": "p1",
            "number": "BP-9",
            "issue_date": "2022-03-01",
            "job_value": 1_500_000,
            "tags": ["plumbing", "pool"],
            "address": {
                "name": "100 Ocean Ave",
                "city": "Sarasota",
                "zip_code": "34236",
                "latlng": [27.33, -82.53],
            },
            "geo_ids": {"county": "geoCounty"},
        }
    )
    assert row["permit_id"] == "BP-9"
    assert row["issued_date"] == "2022-03-01"
    assert row["job_value_usd"] == 15000.0
    assert row["address_city"] == "Sarasota"
    assert row["address_zip_code"] == "34236"
    assert row["address_lat"] == 27.33
    assert row["address_lon"] == -82.53
    assert row["tags"] == "plumbing|pool"
    assert row["geo_county"] == "geoCounty"
