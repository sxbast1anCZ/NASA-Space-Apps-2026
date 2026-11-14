"""API tests on a tiny synthetic dataset with the real schemas (outputs of scripts/harmonize.py)."""

import sys
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import main  # noqa: E402

CHILE_BOX = {"west": -72, "south": -33.5, "east": -71.5, "north": -33}

CELLS = """
SELECT burn_date, cell_lat::DOUBLE AS cell_lat, cell_lon::DOUBLE AS cell_lon, country, admin1, sensor,
       hotspots_raw::BIGINT AS hotspots_raw, hotspots_harmonized::DOUBLE AS hotspots_harmonized, provisional
FROM (VALUES
    (DATE '2010-02-05', -33.25, -71.75, 'Chile', 'Región de Valparaíso', 'MODIS', 2, 7.0, false),
    (DATE '2023-02-10', -33.25, -71.75, 'Chile', 'Región de Valparaíso', 'VIIRS', 4, 4.0, false),
    (DATE '2024-02-02', -33.25, -71.75, 'Chile', 'Región de Valparaíso', 'VIIRS', 10, 10.0, false),
    (DATE '2024-02-02', -27.00, -60.00, 'Argentina', 'Chaco', 'VIIRS', 5, 5.0, false),
    (DATE '2023-03-10', -33.25, -71.75, 'Chile', 'Región de Valparaíso', 'VIIRS', 2, 2.0, false),
    (DATE '2023-03-20', -33.25, -71.75, 'Chile', 'Región de Valparaíso', 'VIIRS', 50, 50.0, false),
    (DATE '2024-03-01', -33.25, -71.75, 'Chile', 'Región de Valparaíso', 'VIIRS', 1, 1.0, true),
    (DATE '2024-03-15', -33.25, -71.75, 'Chile', 'Región de Valparaíso', 'VIIRS', 3, 3.0, true),
    (DATE '2024-03-16', -33.25, -71.75, 'Chile', 'Región de Valparaíso', 'VIIRS', 1, 1.0, true)
) t(burn_date, cell_lat, cell_lon, country, admin1, sensor, hotspots_raw, hotspots_harmonized, provisional)
"""

HOTSPOTS = """
SELECT latitude::DOUBLE AS latitude, longitude::DOUBLE AS longitude, DATE '2024-02-02' AS acq_date, '1830' AS acq_time,
       TIMESTAMPTZ '2024-02-02 18:30:00+00' AS acq_datetime, 'NOAA-20' AS satellite, 'VIIRS' AS instrument,
       'n' AS confidence_raw, '2' AS version, 330.0 AS bright_mir_k, 290.0 AS bright_tir_k, 5.0 AS frp_mw,
       'D' AS daynight, fire_type, 'SP' AS processing, DATE '2024-02-02' AS burn_date,
       TIMESTAMP '2024-02-02 15:30:00' AS local_wall_time, 'America/Santiago' AS tz_name,
       country, 'Region' AS admin1
FROM (VALUES (-33.10, -71.60, 0, 'Chile'), (-33.12, -71.61, NULL, 'Chile'),
             (-27.00, -60.00, 0, 'Argentina'))
     t(latitude, longitude, fire_type, country)
"""

@pytest.fixture
def client(tmp_path, monkeypatch):
    (tmp_path / "harmonized").mkdir()
    duckdb.sql(f"COPY ({CELLS}) TO '{tmp_path}/harmonized/cells_daily.parquet'")
    duckdb.sql(f"COPY ({HOTSPOTS}) TO '{tmp_path}/harmonized/hotspots_kept.parquet'")
    monkeypatch.setattr(main, "DATA", tmp_path)
    monkeypatch.setattr(main, "_con", None)
    return TestClient(main.app)


def month(body, year, m):
    return next(x for x in body["months"] if (x["year"], x["month"]) == (year, m))


def test_meta_reports_last_complete_day_and_regions(client):
    body = client.get("/api/meta").json()
    assert body["data_through"] == "2024-03-15"  # 2024-03-16 is the newest, partial day
    assert {"country": "Argentina", "admin1": "Chaco"} in body["regions"]


def test_calendar_sums_the_box_and_flags_estimated_months(client):
    body = client.get("/api/calendar", params=CHILE_BOX).json()
    assert month(body, 2024, 2)["hotspots"] == 10.0          # the Argentine cell is outside the box
    assert month(body, 2010, 2) == {"year": 2010, "month": 2, "hotspots": 7.0, "raw": 2,
                                    "estimated": True, "provisional": False, "partial": False}
    assert month(body, 2015, 6)["hotspots"] == 0.0            # months without detections are present
    assert body["cells"] == 1 and body["bounds"] == [-71.75, -33.25, -71.5, -33.0]
    assert body["median_by_month"][1] == 0.0                  # February: 3 years with fire out of 15


def test_partial_month_is_compared_on_the_same_days(client):
    body = client.get("/api/calendar", params=CHILE_BOX).json()
    assert body["to"] == "2024-03-15"
    assert month(body, 2024, 3)["partial"] is True and month(body, 2024, 3)["provisional"] is True
    # 1-15 March: 2024 has 1 + 3. March 2023 had 52 in total but only 2 in days 1-15.
    assert body["current"]["hotspots"] == 4.0 and body["current"]["days"] == 15
    assert body["current"]["rank"] == 1
    assert body["years"][-1] == {"year": 2024, "hotspots": 14.0, "partial": True}


def test_box_smaller_than_a_cell_still_selects_it(client):
    tiny = {"west": -71.6, "south": -33.1, "east": -71.59, "north": -33.09}
    assert month(client.get("/api/calendar", params=tiny).json(), 2024, 2)["hotspots"] == 10.0


def test_region_filter_and_date_range(client):
    body = client.get("/api/calendar", params={"country": "Argentina", "from": "2024-01-15", "to": "2024-02-29"}).json()
    assert [(x["year"], x["month"], x["hotspots"]) for x in body["months"]] == [(2024, 1, 0.0), (2024, 2, 5.0)]
    assert month(body, 2024, 2)["partial"] is False


@pytest.mark.parametrize("params", [
    {"west": -72, "south": -33.5, "east": -71.5},                    # incomplete box
    {"west": -71, "south": -33.5, "east": -72, "north": -33},        # west > east
    {"west": -720, "south": -33.5, "east": -71.5, "north": -33},     # out of range
    {"from": "2030-01-01"},                                          # after the data
    {"from": "not-a-date"},
])
def test_bad_input_is_rejected(client, params):
    assert client.get("/api/calendar", params=params).status_code == 422


def test_csv_has_the_hotspots_of_the_search(client):
    r = client.get("/api/hotspots.csv", params={**CHILE_BOX, "from": "2024-02-01", "to": "2024-02-29"})
    lines = r.text.strip().splitlines()
    assert lines[0].split(",")[:4] == ["latitude", "longitude", "acq_date", "acq_time"]
    assert len(lines) == 3                                   # the Argentine point is outside the box
    assert r.headers["x-hotspot-count"] == "2"


def test_csv_needs_the_kept_hotspots_file(client, tmp_path):
    (tmp_path / "harmonized" / "hotspots_kept.parquet").unlink()
    r = client.get("/api/hotspots.csv", params=CHILE_BOX)
    assert r.status_code == 503 and "harmonize.py" in r.json()["detail"]


def test_csv_refuses_searches_that_are_too_large(client, monkeypatch):
    monkeypatch.setattr(main, "CSV_ROW_LIMIT", 1)
    r = client.get("/api/hotspots.csv", params=CHILE_BOX)
    assert r.status_code == 413 and "smaller area" in r.json()["detail"]
