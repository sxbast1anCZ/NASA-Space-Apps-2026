"""Edge cases for scripts/timefields.py (list in docs/eda-plan.md)."""

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_hotspots  # noqa: E402
import timefields  # noqa: E402

SANTIAGO = ("Chile", "Región Metropolitana de Santiago", -70.6)
VALPARAISO = ("Chile", "Región de Valparaíso", -71.6)
MAGALLANES = ("Chile", "Región de Magallanes y Antártica Chilena", -70.9)
AYSEN = ("Chile", "Región de Aysén del Gral.Ibañez del Campo", -72.1)
BUENOS_AIRES = ("Argentina", "Buenos Aires", -60.0)
MENDOZA = ("Argentina", "Mendoza", -68.8)
SAN_LUIS = ("Argentina", "San Luis", -66.3)


def one(utc: str, place, strict=True) -> pd.Series:
    country, region, lon = place
    df = pd.DataFrame({
        "acq_datetime": pd.to_datetime([utc], utc=True),
        "longitude": [lon], "country": [country], "admin1": [region],
    })
    df = timefields.add_solar_fields(df, strict=strict)
    return timefields.add_civil_fields(df).iloc[0]


def wall(row) -> str:
    return row["local_wall_time"].strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------- burn_date and passes

def test_viirs_night_pass_belongs_to_previous_burn_date():
    r = one("2024-02-03 05:30", VALPARAISO)
    assert r["burn_date"] == date(2024, 2, 2)
    assert r["pass_slot"] == "night_pass"
    assert wall(r) == "2024-02-03 02:30"  # civil date is the 3rd, burn date the 2nd


@pytest.mark.parametrize("utc, expected", [
    ("2020-01-15 02:30", date(2020, 1, 14)),  # summer
    ("2020-07-15 02:30", date(2020, 7, 14)),  # winter
])
def test_terra_night_pass_stays_with_its_afternoon(utc, expected):
    r = one(utc, BUENOS_AIRES)
    assert r["burn_date"] == expected
    assert r["pass_slot"] == "night_pass"
    assert 22 < r["solar_time_h"] < 23


def test_new_year_night_stays_in_old_year():
    r = one("2021-01-01 02:30", BUENOS_AIRES)
    assert (r["burn_date"], r["burn_year"], r["burn_month"]) == (date(2020, 12, 31), 2020, 12)
    assert r["season_year"] == 2020


def test_season_changes_on_1_july():
    assert one("2021-07-01 02:30", BUENOS_AIRES)["season_year"] == 2020  # night of 30 June
    assert one("2021-07-01 18:00", BUENOS_AIRES)["season_year"] == 2021  # afternoon of 1 July


def test_29_february():
    assert one("2024-02-29 18:00", SANTIAGO)["burn_date"] == date(2024, 2, 29)


@pytest.mark.parametrize("utc", ["2026-06-15 13:15", "2026-06-15 20:30"])  # Terra 8.6 h, Aqua 15.8 h
def test_drifted_2026_passes_are_day_passes(utc):
    r = one(utc, SANTIAGO)
    assert r["pass_slot"] == "day_pass"
    assert r["burn_date"] == date(2026, 6, 15)


def test_guard_fails_near_the_day_cut():
    with pytest.raises(ValueError, match="day cut"):
        one("2024-02-03 10:50", SANTIAGO)  # about 06:08 local solar time
    assert one("2024-02-03 10:50", SANTIAGO, strict=False)["burn_date"] == date(2024, 2, 3)


# ---------------------------------------------------------------- civil time

def test_chile_spring_forward_skips_midnight_hour():
    before, after = one("2023-09-03 03:59", SANTIAGO), one("2023-09-03 04:00", SANTIAGO)
    assert (wall(before), before["utc_offset_min"]) == ("2023-09-02 23:59", -240)
    assert (wall(after), after["utc_offset_min"]) == ("2023-09-03 01:00", -180)


def test_chile_fall_back_repeats_the_hour():
    before, after = one("2024-04-07 02:30", SANTIAGO), one("2024-04-07 03:30", SANTIAGO)
    assert (wall(before), before["utc_offset_min"]) == ("2024-04-06 23:30", -180)
    assert (wall(after), after["utc_offset_min"]) == ("2024-04-06 23:30", -240)
    assert before["burn_date"] == after["burn_date"] == date(2024, 4, 6)


def test_magallanes_and_aysen_against_santiago_in_winter():
    assert one("2020-07-15 18:00", SANTIAGO)["utc_offset_min"] == -240
    assert one("2020-07-15 18:00", MAGALLANES)["utc_offset_min"] == -180
    assert one("2024-07-15 18:00", AYSEN)["utc_offset_min"] == -240  # still changing clocks
    assert one("2025-07-15 18:00", AYSEN)["utc_offset_min"] == -180  # stayed on UTC-3
    assert one("2025-07-15 18:00", AYSEN)["tz_name"] == "America/Coyhaique"


def test_argentina_summer_2008_09_differs_by_province():
    assert one("2009-01-15 18:00", BUENOS_AIRES)["utc_offset_min"] == -120
    assert one("2009-01-15 18:00", MENDOZA)["utc_offset_min"] == -180


def test_san_luis_on_utc_minus_4():
    assert one("2009-06-15 18:00", SAN_LUIS)["utc_offset_min"] == -240


def test_easter_island_is_set_by_longitude():
    r = one("2024-01-15 20:00", ("Chile", "Región de Valparaíso", -109.4))
    assert r["tz_name"] == "Pacific/Easter"
    assert wall(r) == "2024-01-15 15:00"


def test_unknown_region_fails():
    with pytest.raises(ValueError, match="No time zone"):
        timefields.zone_for("Argentina", "Atlantis")


# ---------------------------------------------------------------- acq_time padding in the build

@pytest.mark.parametrize("raw, hhmm", [("0", "0000"), ("48", "0048"), ("2359", "2359")])
def test_acq_time_without_leading_zeros(raw, hhmm):
    df = pd.DataFrame({
        "acq_date": ["2024-02-02"], "acq_time": [raw], "satellite": ["N20"], "version": ["2.0NRT"],
        "longitude": [-60.0], "scan": [0.4], "track": [0.4], "confidence": ["n"], "frp": [1.0],
        "type": [pd.NA], "instrument": ["VIIRS"], "daynight": ["D"], "source": ["api_bbox"],
        "country": [pd.NA], "confidence_level": ["nominal"],
    }).astype({"acq_date": "string", "acq_time": "string", "version": "string"})
    out = build_hotspots.normalise(df, strict=False).iloc[0]
    assert out["acq_time"] == hhmm
    assert out["acq_datetime"] == pd.Timestamp(f"2024-02-02 {hhmm[:2]}:{hhmm[2:]}", tz="UTC")
