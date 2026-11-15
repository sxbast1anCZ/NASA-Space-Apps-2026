"""scripts/daily_wind.py: reading the Open-Meteo answer (no network in the tests)."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import daily_wind as dw  # noqa: E402


def place(direction, speed=20.0):
    return {"daily": {"time": ["2026-11-13"], "wind_direction_10m_dominant": [direction], "wind_speed_10m_max": [speed],
                      "wind_gusts_10m_max": [45.0], "relative_humidity_2m_min": [18], "temperature_2m_max": [34.0]}}


def test_downwind_is_opposite_to_where_the_wind_comes_from():
    cells = pd.DataFrame({"burn_date": ["2026-11-13"] * 3, "cell_lat": [-33.25, -27.0, -40.0], "cell_lon": [-71.5, -62.0, -71.0]})
    out = dw.parse([place(180), place(350), place(0)], cells)
    assert out["wind_from_deg"].tolist() == [180, 350, 0]
    assert out["downwind_deg"].tolist() == [0, 170, 180]          # a south wind blows towards the north
    assert out["gust_max_kmh"].tolist() == [45.0] * 3 and out["rh_min_pct"].tolist() == [18] * 3


def test_one_location_comes_back_as_one_object():
    cells = pd.DataFrame({"burn_date": ["2026-11-13"], "cell_lat": [-33.25], "cell_lon": [-71.5]})
    assert dw.parse(place(90), cells)["downwind_deg"].tolist() == [270]


def test_a_missing_value_stays_missing_and_a_short_answer_is_an_error():
    cells = pd.DataFrame({"burn_date": ["2026-11-13"] * 2, "cell_lat": [-33.25, -27.0], "cell_lon": [-71.5, -62.0]})
    out = dw.parse([place(None), place(90)], cells)
    assert out["wind_from_deg"].isna().tolist() == [True, False] and out["downwind_deg"].isna().tolist() == [True, False]
    with pytest.raises(ValueError):
        dw.parse([place(90)], cells)
