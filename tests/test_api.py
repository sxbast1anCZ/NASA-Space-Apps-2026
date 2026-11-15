"""API tests on a tiny synthetic dataset with the real schemas (outputs of scripts/harmonize.py)."""

import math
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
UNION ALL
-- Salta, one day every July: 2 in 2011-2012, 8 in 2013-2017, 12 in 2018-2022, 100 in 2023.
SELECT make_date(y, 7, 15), -25.0, -65.0, 'Argentina', 'Salta', 'VIIRS', v, v, false
FROM (SELECT y, CASE WHEN y < 2013 THEN 2 WHEN y < 2018 THEN 8 WHEN y < 2023 THEN 12 ELSE 100 END AS v
      FROM range(2011, 2024) t(y))
"""
SALTA = {"country": "Argentina", "admin1": "Salta"}

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

# Risk layer (contract C3): one week in progress and one old week the API must ignore.
RISK = """
SELECT * FROM (VALUES
    (DATE '2024-03-11', -33.25::DOUBLE, -71.75::DOUBLE, 0.6::FLOAT, 0.4::FLOAT),
    (DATE '2024-03-11', -27.00::DOUBLE, -60.00::DOUBLE, 0.2::FLOAT, 0.2::FLOAT),
    (DATE '2024-01-01', -33.25::DOUBLE, -71.75::DOUBLE, 0.9::FLOAT, 0.9::FLOAT)
) t(week_start, cell_lat, cell_lon, probability, baseline_probability)
"""


@pytest.fixture
def client(tmp_path, monkeypatch):
    (tmp_path / "harmonized").mkdir()
    duckdb.sql(f"COPY ({CELLS}) TO '{tmp_path}/harmonized/cells_daily.parquet'")
    duckdb.sql(f"COPY ({HOTSPOTS}) TO '{tmp_path}/harmonized/hotspots_kept.parquet'")
    (tmp_path / "risk").mkdir()
    duckdb.sql(f"COPY ({RISK}) TO '{tmp_path}/risk/cells_weekly.parquet'")
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
                                    "estimated": True, "provisional": False, "partial": False,
                                    "median": 0.0, "ratio": 8.0, "reliable": False}
    assert month(body, 2015, 6)["hotspots"] == 0.0            # months without detections are present
    assert body["cells"] == 1 and body["bounds"] == [-71.75, -33.25, -71.5, -33.0]
    assert body["median_by_month"][1] == 0.0                  # February: 1 reference year with fire out of 11


def test_partial_month_is_compared_on_the_same_days(client):
    body = client.get("/api/calendar", params=CHILE_BOX).json()
    assert body["to"] == "2024-03-15"
    assert month(body, 2024, 3)["partial"] is True and month(body, 2024, 3)["provisional"] is True
    # 1-15 March: 2024 has 1 + 3. March 2023 had 52 in total but only 2 in days 1-15.
    assert body["current"]["hotspots"] == 4.0 and body["current"]["days"] == 15
    assert body["current"]["rank"] == 1 and body["current"]["years_compared"] == 11   # 2013 to 2023
    assert body["current"]["median"] == 0.0 and body["current"]["ratio"] == 5.0       # (4 + 1) / (0 + 1)
    assert body["current"]["reliable"] is False
    # The partial month itself gets no ratio: it is not compared with complete months.
    assert month(body, 2024, 3)["ratio"] is None and month(body, 2024, 3)["reliable"] is False
    assert body["years"][-1] == {"year": 2024, "hotspots": 14.0, "partial": True}


def test_box_smaller_than_a_cell_still_selects_it(client):
    tiny = {"west": -71.6, "south": -33.1, "east": -71.59, "north": -33.09}
    assert month(client.get("/api/calendar", params=tiny).json(), 2024, 2)["hotspots"] == 10.0


def test_region_filter_and_date_range(client):
    body = client.get("/api/calendar", params={"country": "Argentina", "from": "2024-01-15", "to": "2024-02-29"}).json()
    assert [(x["year"], x["month"], x["hotspots"]) for x in body["months"]] == [(2024, 1, 0.0), (2024, 2, 5.0)]
    assert month(body, 2024, 2)["partial"] is False


def test_ratio_with_a_zero_median(client):
    feb = month(client.get("/api/calendar", params=CHILE_BOX).json(), 2024, 2)
    # February 2013-2023: only 2023 has fire, so the median is 0. (10 + 1) / (0 + 1).
    assert (feb["median"], feb["ratio"], feb["reliable"]) == (0.0, 11.0, False)


def test_reference_leaves_out_the_year_being_judged(client):
    body = client.get("/api/calendar", params=SALTA).json()
    assert body["reference"] == {"mode": "recent", "from_year": 2013, "to_year": 2023}
    # July 2023 (100) against 2013-2022: five 8s and five 12s. With 2023 inside, the median would be 12.
    assert (month(body, 2023, 7)["median"], month(body, 2023, 7)["ratio"]) == (10.0, round(101 / 11, 3))
    assert body["median_by_month"][6] == 12.0                 # the typical year leaves nothing out
    # A year outside the reference is judged against all of it.
    assert (month(body, 2012, 7)["median"], month(body, 2012, 7)["ratio"]) == (12.0, round(3 / 13, 3))
    # The reference does not depend on the period shown.
    one_year = client.get("/api/calendar", params={**SALTA, "from": "2023-01-01", "to": "2023-12-31"}).json()
    assert month(one_year, 2023, 7) == month(body, 2023, 7)


def test_default_reference_against_all_years(client):
    recent = client.get("/api/calendar", params=SALTA).json()
    full = client.get("/api/calendar", params={**SALTA, "reference": "all"}).json()
    # The record starts in February 2010 and ends in March 2024: complete years are 2011 to 2023.
    assert full["reference"] == {"mode": "all", "from_year": 2011, "to_year": 2023}
    # July 2023 with 2011 and 2012 (2 each) in the reference: 2, 2, five 8s, five 12s.
    assert (month(recent, 2023, 7)["median"], month(full, 2023, 7)["median"]) == (10.0, 8.0)
    assert month(full, 2023, 7)["ratio"] == round(101 / 9, 3)
    assert full["current"]["years_compared"] == 13 and recent["current"]["years_compared"] == 11


def test_reliable_needs_a_reference_median_of_at_least_10(client):
    recent = client.get("/api/calendar", params=SALTA).json()
    full = client.get("/api/calendar", params={**SALTA, "reference": "all"}).json()
    assert month(recent, 2023, 7)["reliable"] is True         # median exactly 10
    assert month(full, 2023, 7)["reliable"] is False          # median 8
    assert month(recent, 2023, 1)["reliable"] is False        # median 0


@pytest.mark.parametrize("params", [
    {"west": -72, "south": -33.5, "east": -71.5},                    # incomplete box
    {"west": -71, "south": -33.5, "east": -72, "north": -33},        # west > east
    {"west": -720, "south": -33.5, "east": -71.5, "north": -33},     # out of range
    {"from": "2030-01-01"},                                          # after the data
    {"from": "not-a-date"},
    {"reference": "2013"},                                           # only 'recent' and 'all' exist
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



def test_risk_lists_only_the_week_in_progress_and_later(client):
    assert client.get("/api/meta").json()["risk_weeks"] == ["2024-03-11"]


def test_risk_returns_the_cells_of_the_area(client):
    chile = client.get("/api/risk", params={"week": "2024-03-11", **CHILE_BOX}).json()
    assert chile == {"week_start": "2024-03-11", "cells": [[-33.25, -71.75, 0.6, 0.4]]}
    argentina = client.get("/api/risk", params={"week": "2024-03-11", "country": "Argentina"}).json()
    assert argentina["cells"] == [[-27.0, -60.0, 0.2, 0.2]]
    assert client.get("/api/risk", params={"week": "2024-01-01"}).json()["cells"] == []  # old week


def test_app_works_without_a_risk_file(client, tmp_path, monkeypatch):
    (tmp_path / "risk" / "cells_weekly.parquet").unlink()
    monkeypatch.setattr(main, "_con", None)
    assert client.get("/api/meta").json()["risk_weeks"] == []
    assert client.get("/api/risk", params={"week": "2024-03-11"}).json()["cells"] == []


# ---------------------------------------------------------------- next-day outlook

DAILY = """
SELECT * FROM (VALUES
    (DATE '2024-02-03', -33.25::DOUBLE, -71.75::DOUBLE, 0.93::FLOAT, 0.09::FLOAT, 1::TINYINT),
    (DATE '2024-02-03', -27.00::DOUBLE, -60.00::DOUBLE, 0.01::FLOAT, 0.02::FLOAT, 0::TINYINT),
    (DATE '2023-07-16', -25.00::DOUBLE, -65.00::DOUBLE, 0.30::FLOAT, 0.20::FLOAT, 1::TINYINT)
) t(burn_date, cell_lat, cell_lon, probability, baseline_probability, alert)
"""
REASONS = """
SELECT DATE '2024-02-03' AS burn_date, -33.25::DOUBLE AS cell_lat, -71.75::DOUBLE AS cell_lon,
       'Today''s fire here had 128 hotspots' AS reason_1, 'Fire was detected in this cell today' AS reason_2,
       '' AS reason_3, 0.6::FLOAT AS share_1, 0.4::FLOAT AS share_2, 0.0::FLOAT AS share_3
"""
WIND = """
SELECT DATE '2024-02-03' AS burn_date, -33.25::DOUBLE AS cell_lat, -71.75::DOUBLE AS cell_lon,
       186::BIGINT AS wind_from_deg, 6::BIGINT AS downwind_deg, 21.0 AS wind_max_kmh, 58.3 AS gust_max_kmh,
       18::BIGINT AS rh_min_pct, 34.0 AS tmax_c
"""
VALPARAISO = {"date": "2024-02-03", "cell_lat": -33.25, "cell_lon": -71.75}


@pytest.fixture
def daily(client, tmp_path):
    for name, query in (("cells_daily", DAILY), ("cells_daily_reasons", REASONS), ("wind_live", WIND)):
        duckdb.sql(f"COPY ({query}) TO '{tmp_path}/risk/{name}.parquet'")
    return client


def test_daily_days_are_listed_newest_first(daily):
    assert daily.get("/api/meta").json()["risk_days"] == ["2024-02-03", "2023-07-16"]


def test_daily_returns_the_cells_of_the_day_and_area_with_alert_and_wind(daily):
    body = daily.get("/api/risk/daily", params={"date": "2024-02-03"}).json()
    assert body["cells"] == [[-33.25, -71.75, 0.93, 0.09, 1], [-27.0, -60.0, 0.01, 0.02, 0]]
    assert body["wind"] == [[-33.25, -71.75, 6.0, 21.0]]                       # blows to the north
    argentina = daily.get("/api/risk/daily", params={"date": "2024-02-03", "country": "Argentina"}).json()
    assert argentina["cells"] == [[-27.0, -60.0, 0.01, 0.02, 0]] and argentina["wind"] == []
    assert daily.get("/api/risk/daily", params={"date": "2024-02-04"}).json()["cells"] == []


def test_daily_cell_gives_reasons_and_wind(daily):
    body = daily.get("/api/risk/daily/cell", params=VALPARAISO).json()
    assert body["probability"] == 0.93 and body["baseline_probability"] == 0.09 and body["alert"] is True
    assert body["reasons"] == [{"text": "Today's fire here had 128 hotspots", "share": 0.6},
                               {"text": "Fire was detected in this cell today", "share": 0.4}]   # no empty third
    assert body["wind"]["wind_from_deg"] == 186 and body["wind"]["downwind_deg"] == 6
    quiet = daily.get("/api/risk/daily/cell", params={**VALPARAISO, "cell_lat": -27.0, "cell_lon": -60.0}).json()
    assert quiet["alert"] is False and quiet["reasons"] == [] and quiet["wind"] is None
    assert daily.get("/api/risk/daily/cell", params={**VALPARAISO, "cell_lat": 0}).status_code == 404


def test_daily_hotspots_are_the_day_before_from_the_satellite_of_the_outlook(daily, tmp_path):
    duckdb.sql(f"""COPY (SELECT * REPLACE (CASE WHEN latitude = -33.12 THEN 'Suomi-NPP' ELSE satellite END AS satellite)
                         FROM ({HOTSPOTS})) TO '{tmp_path}/harmonized/hotspots_kept.parquet'""")
    body = daily.get("/api/risk/daily/hotspots", params={"date": "2024-02-03"}).json()
    assert body["date"] == "2024-02-02" and body["satellite"] == "Suomi-NPP"
    assert body["points"] == [[-33.12, -71.62]] and body["truncated"] is False   # thinned to 0.02 degrees
    assert [r["km"] for r in body["rings"]] == [5, 10, 25]
    assert daily.get("/api/risk/daily/hotspots", params={"date": "2024-02-03", "country": "Argentina"}).json()["points"] == []
    assert daily.get("/api/risk/daily/hotspots", params={"date": "2026-11-13"}).json()["satellite"] == "NOAA-20"


def test_app_works_without_the_daily_files(client):
    assert client.get("/api/meta").json()["risk_days"] == []
    body = client.get("/api/risk/daily", params={"date": "2024-02-03"}).json()
    assert (body["date"], body["cells"], body["wind"]) == ("2024-02-03", [], [])
    assert body["area"] == {"cells": 0, "alert_cells": 0, "cells_km2": 0, "alert_km2": 0, "expected_km2": 0,
                            "regions": []}
    assert client.get("/api/risk/daily/cell", params=VALPARAISO).status_code == 404
    zones = client.get("/api/risk/daily/zones", params={"date": "2024-02-03"}).json()
    assert zones["fires"] == [] and zones["points"] == [] and zones["summary"]["fires"] == 0
    assert zones["available"] is False and zones["seen_date"] is None     # no file: no data, not "no fires"


def cell_km2(lat: float) -> float:
    """Area of a 0.25 degree cell from its south-west corner, on a sphere of radius 6371.0088 km."""
    return 6371.0088 ** 2 * math.radians(0.25) * (math.sin(math.radians(lat + 0.25)) - math.sin(math.radians(lat)))


def test_daily_area_adds_cells_in_alert_and_expected_area_by_region(daily):
    area = daily.get("/api/risk/daily", params={"date": "2024-02-03"}).json()["area"]
    valpo, chaco = cell_km2(-33.25), cell_km2(-27.0)
    assert 600 < valpo < 700 and chaco > valpo                     # cells shrink towards the pole
    assert (area["cells"], area["alert_cells"]) == (2, 1)
    assert area["cells_km2"] == round(valpo + chaco)
    assert area["alert_km2"] == round(valpo)
    assert area["expected_km2"] == round(0.93 * valpo + 0.01 * chaco)
    assert area["regions"][0] == {"country": "Chile", "admin1": "Región de Valparaíso", "cells": 1, "alert_cells": 1,
                                  "alert_km2": round(valpo), "expected_km2": round(0.93 * valpo)}
    assert [r["admin1"] for r in area["regions"]] == ["Región de Valparaíso", "Chaco"]   # Chaco: 8 km2 expected
    salta = daily.get("/api/risk/daily", params={"date": "2023-07-16", **SALTA}).json()["area"]
    assert salta["alert_km2"] == round(cell_km2(-25.0)) and salta["regions"][0]["admin1"] == "Salta"


ZONES = """
SELECT DATE '2024-02-03' AS burn_date, DATE '2024-02-02' AS seen_date, fire_id, lat, lon, country, admin1,
       hotspots, 50.0 AS frp_sum_mw, size_class, active, p_continue, 0.6 AS r50_km, 1.9 AS r80_km, 2.7 AS r90_km,
       a50 AS area50_km2, a80 AS area80_km2, a90 AS area90_km2, continued, nxt AS next_hotspots, inside AS next_in_r80
FROM (VALUES
    (0, -33.11, -71.61, 'Chile', 'Región de Valparaíso', 3, '2-4', true, 0.21, 2.0, 15.0, 30.0, true, 4, 3),
    (1, -27.00, -60.00, 'Argentina', 'Chaco', 1, '1', false, 0.06, 1.1, 11.3, 22.9, false, 0, 0)
) t(fire_id, lat, lon, country, admin1, hotspots, size_class, active, p_continue, a50, a80, a90, continued, nxt, inside)
"""
ZONE_POINTS = """
SELECT DATE '2024-02-03' AS burn_date, fire_id, lat, lon FROM (VALUES
    (0, -33.110, -71.610), (0, -33.112, -71.612), (0, -33.114, -71.610), (1, -27.0, -60.0)) t(fire_id, lat, lon)
"""


def test_zones_give_each_fire_its_chance_radii_area_and_points(daily, tmp_path):
    duckdb.sql(f"COPY ({ZONES}) TO '{tmp_path}/risk/fire_zones.parquet'")
    duckdb.sql(f"COPY ({ZONE_POINTS}) TO '{tmp_path}/risk/fire_zone_points.parquet'")
    main._con = None
    body = daily.get("/api/risk/daily/zones", params={"date": "2024-02-03"}).json()
    assert body["seen_date"] == "2024-02-02" and body["available"] is True
    assert [f[0] for f in body["fires"]] == [0, 1]                              # largest first
    assert body["fires"][0][3:8] == [3, 0.21, 0.6, 1.9, 2.7]
    assert body["fires"][0][11:] == [True, 4, 3, "Región de Valparaíso"]
    assert len(body["points"]) == 4 and body["truncated"] is False
    assert body["summary"] == {"fires": 2, "likely": 0, "expected_continuing": 0.3, "area80_km2": 26}
    chile = daily.get("/api/risk/daily/zones", params={"date": "2024-02-03", "country": "Chile"}).json()
    assert [f[0] for f in chile["fires"]] == [0] and {p[0] for p in chile["points"]} == {0}
    salta = daily.get("/api/risk/daily/zones", params={"date": "2024-02-03", **SALTA}).json()
    assert salta["fires"] == [] and salta["available"] is True and salta["seen_date"] == "2024-02-02"   # no fires there
    other = daily.get("/api/risk/daily/zones", params={"date": "2024-02-04"}).json()
    assert other["fires"] == [] and other["available"] is False                # a day the file does not cover


def test_zone_points_stop_at_the_budget_but_the_largest_fire_keeps_its_own(daily, tmp_path, monkeypatch):
    duckdb.sql(f"COPY ({ZONES}) TO '{tmp_path}/risk/fire_zones.parquet'")
    duckdb.sql(f"COPY ({ZONE_POINTS}) TO '{tmp_path}/risk/fire_zone_points.parquet'")
    main._con = None
    monkeypatch.setattr(main, "ZONE_POINTS", 2)                                # fewer than the 3 of fire 0
    body = daily.get("/api/risk/daily/zones", params={"date": "2024-02-03"}).json()
    assert {p[0] for p in body["points"]} == {0} and body["truncated"] is True
