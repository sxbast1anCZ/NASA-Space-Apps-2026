"""The quality filter and the region correction of scripts/harmonize.py, on synthetic rows."""

import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import harmonize  # noqa: E402

# id, country, admin1 from the polygons, admin1_fixed from block 1, keep
ROWS = [
    (1, "Chile", "Región de Ñuble", None, True),
    (2, "Argentina", "Neuquén", None, True),
    (3, "Chile", None, "RegiÃ³n de Ã\x91uble", True),   # encoding as in the raw boundary file
    (4, "Chile", None, "Neuquén", True),                  # nearest polygon is across the border
    (5, "Argentina", None, "Neuquén", True),
    (6, "Chile", "Región de Ñuble", None, False),         # dropped by the filter
    (7, "Chile", None, None, True),
]


@pytest.fixture
def data(tmp_path):
    con = duckdb.connect()
    con.execute("CREATE TABLE rows (id INT, country VARCHAR, admin1 VARCHAR, admin1_fixed VARCHAR, keep BOOLEAN)")
    con.executemany("INSERT INTO rows VALUES (?, ?, ?, ?, ?)", ROWS)
    key = """'NOAA-20' AS satellite, TIMESTAMPTZ '2024-02-02 18:30:00+00' AS acq_datetime,
             -33.0 - id / 100.0 AS latitude, -71.0 AS longitude"""
    con.execute(f"COPY (SELECT id, {key}, country, admin1 FROM rows) TO '{tmp_path}/table.parquet'")
    con.execute(f"COPY (SELECT {key}, keep, admin1_fixed FROM rows) TO '{tmp_path}/flags.parquet'")
    return con, f"read_parquet('{tmp_path}/table.parquet')", tmp_path


def kept(data):
    con, table, tmp = data
    n = harmonize.build_kept(con, table, tmp / "flags.parquet", tmp / "out" / "kept.parquet")
    regions = dict(con.execute(f"SELECT id, admin1 FROM read_parquet('{tmp}/out/kept.parquet')").fetchall())
    return n, regions


def test_only_kept_rows_are_written(data):
    n, regions = kept(data)
    assert n == 6 and 6 not in regions


def test_fixed_region_gets_the_canonical_name(data):
    assert kept(data)[1][3] == "Región de Ñuble"  # same name as row 1, not a second spelling


def test_fixed_region_of_another_country_is_rejected(data):
    _, regions = kept(data)
    assert regions[4] is None            # Chile / Neuquén is not a valid pair
    assert regions[5] == "Neuquén"       # Argentina / Neuquén is


def test_rows_with_a_region_keep_it(data):
    _, regions = kept(data)
    assert (regions[1], regions[2], regions[7]) == ("Región de Ñuble", "Neuquén", None)


def test_missing_flag_stops_the_build(data):
    con, table, tmp = data
    con.execute(f"COPY (SELECT * FROM read_parquet('{tmp}/flags.parquet') WHERE latitude <> -33.03) TO '{tmp}/short.parquet'")
    with pytest.raises(SystemExit, match="no quality flag"):
        harmonize.build_kept(con, table, tmp / "short.parquet", tmp / "out" / "kept.parquet")


def test_missing_flags_file_stops_the_build(data):
    con, table, tmp = data
    with pytest.raises(SystemExit, match="not found"):
        harmonize.build_kept(con, table, tmp / "nope.parquet", tmp / "out" / "kept.parquet")


# Which satellite enters the series, with and without a Suomi-NPP outage.
OUTAGES = """satellite,start,end,days
Suomi-NPP,2022-07-26,2022-07-27,2
Suomi-NPP,2015-03-01,2015-03-01,1
Terra,2003-12-16,2003-12-17,2
Terra,2016-02-19,2016-02-19,1
"""
# burn_date, instrument, satellite
HOTSPOTS = [
    ("2022-07-25", "VIIRS", "Suomi-NPP"),   # normal day: both VIIRS satellites and MODIS report
    ("2022-07-25", "VIIRS", "NOAA-20"),
    ("2022-07-25", "MODIS", "Aqua"),
    ("2022-07-26", "VIIRS", "NOAA-20"),     # Suomi-NPP outage
    ("2022-07-26", "VIIRS", "NOAA-20"),
    ("2022-07-26", "MODIS", "Aqua"),
]


def series(tmp_path, outages):
    con = duckdb.connect()
    con.execute("CREATE TABLE hf (burn_date DATE, instrument VARCHAR, satellite VARCHAR)")
    con.executemany("INSERT INTO hf VALUES (?, ?, ?)", HOTSPOTS)
    if outages:
        (tmp_path / "outage_days.csv").write_text(outages)
    harmonize.load_outages(con, tmp_path / "outage_days.csv")
    picked = con.execute(f"""
        SELECT burn_date::VARCHAR, satellite, count(*) FROM hf WHERE {harmonize.IN_SERIES}
        GROUP BY ALL ORDER BY ALL
    """).fetchall()
    return con, picked


def test_outage_day_takes_noaa20_and_a_normal_day_only_suomi_npp(tmp_path):
    _, picked = series(tmp_path, OUTAGES)
    assert picked == [("2022-07-25", "Suomi-NPP", 1), ("2022-07-26", "NOAA-20", 2)]


def test_without_the_outage_file_the_series_has_no_fill(tmp_path, capsys):
    con, picked = series(tmp_path, None)
    assert picked == [("2022-07-25", "Suomi-NPP", 1)]
    assert con.execute("SELECT count(*) FROM series_outages").fetchone()[0] == 0
    assert "not found" in capsys.readouterr().out


def test_outage_days_of_the_series_and_their_substitute(tmp_path):
    con, _ = series(tmp_path, OUTAGES)
    listed = con.execute("SELECT burn_date::VARCHAR, satellite, substitute FROM series_outages").fetchall()
    assert listed == [
        ("2003-12-16", "Terra", None),          # MODIS era: listed, nothing can replace it
        ("2003-12-17", "Terra", None),
        ("2015-03-01", "Suomi-NPP", None),      # before NOAA-20 had data
        ("2022-07-26", "Suomi-NPP", "NOAA-20"),
        ("2022-07-27", "Suomi-NPP", "NOAA-20"),
    ]                                           # Terra in 2016 is not a satellite of the series
