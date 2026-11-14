"""Edge cases for scripts/risk_baseline.py (review of pull request #3)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import risk_baseline as rb  # noqa: E402


def dates(year: int) -> pd.Series:
    return pd.Series(pd.date_range(f"{year}-01-01", f"{year}-12-31"))


def cells_of(*pairs) -> pd.DataFrame:
    cells = pd.DataFrame(pairs, columns=["cell_lat", "cell_lon"])
    cells.index.name = "cell_id"
    return cells


def rows_at(*items) -> pd.DataFrame:
    """items: (cell_lat, cell_lon, 'YYYY-MM-DD', satellite)."""
    df = pd.DataFrame(items, columns=["cell_lat", "cell_lon", "burn_date", "satellite"])
    df["burn_date"] = pd.to_datetime(df["burn_date"])
    return df


# ---------------------------------------------------------------- weeks

@pytest.mark.parametrize("year", [2023, 2024, 2000, 2100])
def test_every_day_falls_inside_its_week(year):
    d = dates(year)
    w = rb.week_index(d)
    assert w.min() == 0 and w.max() == rb.N_WEEKS - 1
    for day, week in zip(d, w):
        assert rb.week_start(year, week) <= day <= rb.week_end(year, week)


def test_29_february_shares_the_week_of_28_february():
    w = rb.week_index(pd.Series(pd.to_datetime(["2024-02-28", "2024-02-29", "2024-03-01"])))
    assert w[0] == w[1]  # 29 February counts as 28 February
    assert w[2] in (w[1], w[1] + 1)


@pytest.mark.parametrize("year,days", [(2023, 365), (2024, 366)])
def test_weeks_cover_the_year_without_gaps(year, days):
    sizes = pd.Series(rb.week_index(dates(year))).value_counts()
    assert sizes.sum() == days
    assert sizes.min() == 7 and sizes.max() == 8


# ---------------------------------------------------------------- panel

def test_rows_outside_the_cell_universe_are_ignored():
    # Point 1 of the review: a satellite with a cell the universe does not have must not crash.
    cells = cells_of((-33.0, -71.5))
    rows = rows_at((-33.0, -71.5, "2020-02-03", "Suomi-NPP"), (-40.0, -72.0, "2020-02-03", "NOAA-20"))
    fire = rb.build_panel(rows, np.arange(2020, 2021), cells)
    assert fire.shape == (1, 1, rb.N_WEEKS)
    assert fire.sum() == 1


def test_reference_series_switches_satellite_and_last_day_follows_it():
    df = rows_at(
        (-33.0, -71.5, "2012-01-25", "Suomi-NPP"),  # before VIIRS_START: dropped
        (-33.0, -71.5, "2026-10-30", "Suomi-NPP"),
        (-33.0, -71.5, "2026-10-30", "NOAA-20"),   # before the switch: not in the target
        (-33.0, -71.5, "2026-11-10", "NOAA-20"),
        (-33.0, -71.5, "2026-11-13", "NOAA-21"),   # newer than NOAA-20, must not move last_day
    )
    rows, first_day, switch, last_day = rb.select_target_rows(df, "reference")
    assert first_day == rb.VIIRS_START
    assert rows["burn_date"].min() >= rb.VIIRS_START
    assert set(rows.loc[rows["burn_date"] < switch, "satellite"]) == {"Suomi-NPP"}
    assert set(rows.loc[rows["burn_date"] >= switch, "satellite"]) == {"NOAA-20"}
    assert last_day == pd.Timestamp("2026-11-09")


# ---------------------------------------------------------------- baseline

def panel(n_cells=2, n_years=6):
    fire = np.zeros((n_cells, n_years, rb.N_WEEKS), dtype=bool)
    avail = np.ones((n_years, rb.N_WEEKS), dtype=bool)
    return fire, avail


def test_baseline_never_reads_the_year_it_predicts():
    fire, avail = panel()
    fire[0, :4, 10] = True
    before = rb.baseline_for_year(fire, avail, 4, window=1, shrink=3.0)
    fire[:, 4:, :] = True  # change the scored year and later
    after = rb.baseline_for_year(fire, avail, 4, window=1, shrink=3.0)
    np.testing.assert_allclose(before, after)


def test_baseline_is_the_mean_weekly_rate_of_the_window():
    # Point 5: a cell that burns in one of the three weeks every year gets about 1/3.
    fire, avail = panel(n_cells=1, n_years=11)
    fire[0, :10, 20] = True
    p = rb.baseline_for_year(fire, avail, 10, window=1, shrink=0.0)
    assert p[0, 20] == pytest.approx(1 / 3)
    assert p[0, 19] == pytest.approx(1 / 3) and p[0, 21] == pytest.approx(1 / 3)
    assert p[0, 30] == 0


def test_window_crosses_into_the_adjacent_year():
    # Point 6: week 0 borrows week 51 of the year before, not of the same year.
    fire, avail = panel(n_cells=1, n_years=5)
    fire[0, 1, 51] = True  # last week of year 1
    p = rb.baseline_for_year(fire, avail, 4, window=1, shrink=0.0)
    # Week 0 of year 2 sees it (adjacent year). A same-year wrap would let week 0 of year 1 see it instead.
    n_windows = 4 * 3 - 1  # 4 past years x 3 weeks, minus week -1 of year 0 (before the record)
    assert p[0, 0] == pytest.approx(1 / n_windows)
    assert p[0, 51] == pytest.approx(1 / (4 * 3 - 1))


def test_last_week_of_the_last_past_year_does_not_read_the_scored_year():
    fire, avail = panel(n_cells=1, n_years=5)
    fire[0, 4, 0] = True  # week 0 of the scored year
    p = rb.baseline_for_year(fire, avail, 4, window=1, shrink=0.0)
    assert p[0, 51] == 0


def test_eligible_cells_only_look_at_earlier_years():
    # Point 2: a cell that burns for the first time in the scored year is not in its universe.
    fire, avail = panel(n_cells=3, n_years=5)
    fire[0, 1, 5] = True   # history
    fire[1, 4, 5] = True   # first fire in the scored year
    keep = rb.eligible_cells(fire, avail, 4)
    assert keep.tolist() == [True, False, False]
