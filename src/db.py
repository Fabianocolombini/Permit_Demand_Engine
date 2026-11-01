"""DuckDB helpers — schemas and silver.permits DDL per V1.1."""

from __future__ import annotations

from pathlib import Path

import duckdb

DEFAULT_DB_PATH = Path("permits.duckdb")

PERMITS_DDL = """
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS bronze;

CREATE TABLE IF NOT EXISTS silver.jurisdictions (
    jurisdiction_id   VARCHAR PRIMARY KEY,
    name              VARCHAR,
    county_fips       VARCHAR,
    level             VARCHAR,
    covers            VARCHAR,
    tier              VARCHAR,
    connector         VARCHAR,
    last_pull_at      TIMESTAMP,
    last_pull_status  VARCHAR,
    records_total     BIGINT,
    earliest_permit   DATE,
    latest_permit     DATE,
    notes             VARCHAR
);

CREATE TABLE IF NOT EXISTS silver.permits (
    permit_id                 VARCHAR NOT NULL,
    jurisdiction_id           VARCHAR NOT NULL,
    source_tier               VARCHAR,
    ingested_at               TIMESTAMP,
    applied_date              DATE,
    issued_date               DATE NOT NULL,
    final_date                DATE,
    address_raw               VARCHAR,
    city                      VARCHAR,
    county                    VARCHAR,
    county_fips               VARCHAR,
    state                     VARCHAR,
    zip                       VARCHAR,
    lat                       DOUBLE,
    lon                       DOUBLE,
    geocode_confidence        DOUBLE,
    geocode_source            VARCHAR,
    permit_type_raw           VARCHAR,
    work_class_raw            VARCHAR,
    description_raw           VARCHAR,
    category                  VARCHAR,
    classification_method     VARCHAR,
    classification_confidence DOUBLE,
    is_new_construction       BOOLEAN,
    is_residential            BOOLEAN,
    declared_valuation        DOUBLE,
    square_feet               DOUBLE,
    units                     INTEGER,
    contractor_name           VARCHAR,
    contractor_license        VARCHAR,
    is_owner_builder          BOOLEAN,
    project_key               VARCHAR,
    PRIMARY KEY (jurisdiction_id, permit_id)
);

CREATE INDEX IF NOT EXISTS idx_permits_issued ON silver.permits(issued_date);
CREATE INDEX IF NOT EXISTS idx_permits_cat    ON silver.permits(category);
CREATE INDEX IF NOT EXISTS idx_permits_fips   ON silver.permits(county_fips);
CREATE INDEX IF NOT EXISTS idx_permits_zip    ON silver.permits(zip);
"""


def connect(db_path: Path | str = DEFAULT_DB_PATH) -> duckdb.DuckDBPyConnection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    con.execute(PERMITS_DDL)
    return con
