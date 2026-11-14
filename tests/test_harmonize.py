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
