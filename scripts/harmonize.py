"""Build the harmonized dataset (contract C2 in docs/work-split.md) from the hotspot table.

Output: NASA_Data_Sources/processed/harmonized/
    cells_daily.parquet   one row per 0.25° cell, burn_date, region and sensor with fire
    factors.csv           the MODIS -> VIIRS-equivalent factors that were applied

One sensor per period, so nothing is counted twice:
    burn_date <  2012-02-01   MODIS (Terra + Aqua), scaled to VIIRS-equivalent counts
    2012-02-01 .. 2026-10-31  VIIRS Suomi-NPP, unchanged
    burn_date >= 2026-11-01   VIIRS NOAA-20, unchanged (Suomi-NPP stopped on 2026-11-02)

Method v0: factor = Suomi-NPP count / MODIS count over the calibration years, per country and
calendar month. A second set of factors uses Terra rows only, for the period before Aqua.
shortcut: country x month factors with no regional detail and NOAA-20 taken as equal to
Suomi-NPP; replace with the method chosen in block 3 of docs/eda-plan.md.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "NASA_Data_Sources" / "processed" / "hotspots"
OUT = ROOT / "NASA_Data_Sources" / "processed" / "harmonized"

CALIBRATION_YEARS = (2012, 2021)   # stable MODIS orbits; Suomi-NPP complete from February 2012
VIIRS_START = "2012-02-01"
NOAA20_START = "2026-11-01"
AQUA_START = "2002-07-04"
CELL = 4                           # cells per degree: 0.25°
# Vegetation fires only. NRT rows have no fire_type yet, so they are kept.
FILTER = "(fire_type = 0 OR fire_type IS NULL)"


def main() -> None:
    con = duckdb.connect()
    con.execute("SET TimeZone='UTC'")
    con.execute(f"""
        CREATE VIEW h AS SELECT * FROM read_parquet('{TABLE}/*/*.parquet', hive_partitioning=true)
        WHERE {FILTER}
    """)

    # Factors on the months where both sensors observed, per country and calendar month.
    y0, y1 = CALIBRATION_YEARS
    con.execute(f"""
        CREATE TABLE factors AS
        WITH overlap AS (
            SELECT country, burn_month,
                   count(*) FILTER (WHERE satellite = 'Suomi-NPP') AS viirs,
                   count(*) FILTER (WHERE instrument = 'MODIS') AS modis,
                   count(*) FILTER (WHERE satellite = 'Terra') AS terra
            FROM h
            WHERE burn_year BETWEEN {y0} AND {y1} AND burn_date >= DATE '{VIIRS_START}'
            GROUP BY ALL
        )
        SELECT country, burn_month, viirs, modis, terra,
               viirs / modis AS factor_terra_aqua, viirs / terra AS factor_terra_only
        FROM overlap ORDER BY ALL
    """)

    con.execute(f"""
        CREATE TABLE cells AS
        WITH series AS (
            SELECT *, CASE
                WHEN burn_date < DATE '{VIIRS_START}' THEN instrument = 'MODIS'
                WHEN burn_date < DATE '{NOAA20_START}' THEN satellite = 'Suomi-NPP'
                ELSE satellite = 'NOAA-20' END AS in_series
            FROM h
        )
        SELECT s.burn_date,
               floor(s.latitude * {CELL}) / {CELL} AS cell_lat,
               floor(s.longitude * {CELL}) / {CELL} AS cell_lon,
               s.country, s.admin1,
               s.instrument AS sensor,
               count(*) AS hotspots_raw,
               sum(CASE WHEN s.instrument = 'VIIRS' THEN 1.0
                        WHEN s.burn_date < DATE '{AQUA_START}' THEN f.factor_terra_only
                        ELSE f.factor_terra_aqua END) AS hotspots_harmonized,
               bool_or(s.processing = 'NRT') AS provisional
        FROM series s JOIN factors f USING (country, burn_month)
        WHERE s.in_series
        GROUP BY ALL
    """)

    OUT.mkdir(parents=True, exist_ok=True)
    con.execute(f"COPY factors TO '{OUT}/factors.csv' (HEADER)")
    con.execute(f"COPY (SELECT * FROM cells ORDER BY burn_date, cell_lat, cell_lon) "
                f"TO '{OUT}/cells_daily.parquet' (FORMAT parquet, COMPRESSION zstd)")

    # Self-check: VIIRS rows are untouched, and every in-series hotspot got a factor.
    raw, harm, viirs_raw, viirs_harm = con.execute("""
        SELECT sum(hotspots_raw), sum(hotspots_harmonized),
               sum(hotspots_raw) FILTER (WHERE sensor = 'VIIRS'),
               sum(hotspots_harmonized) FILTER (WHERE sensor = 'VIIRS')
        FROM cells
    """).fetchone()
    assert viirs_raw == viirs_harm, "VIIRS counts must not change"
    assert con.execute("SELECT count(*) FROM cells WHERE hotspots_harmonized IS NULL").fetchone()[0] == 0

    print(con.execute("SELECT * FROM factors").df().round(2).to_string(index=False))
    print(f"\n{con.execute('SELECT count(*) FROM cells').fetchone()[0]:,} cell-day rows "
          f"| raw {raw:,.0f} -> harmonized {harm:,.0f} hotspots")
    validate(con)


def validate(con: duckdb.DuckDBPyConnection) -> None:
    """Scale MODIS in the overlap years and compare it with what VIIRS really saw."""
    y0, y1 = CALIBRATION_YEARS
    monthly = con.execute(f"""
        SELECT country, burn_year AS year, burn_month AS month,
               count(*) FILTER (WHERE satellite = 'Suomi-NPP') AS viirs,
               count(*) FILTER (WHERE instrument = 'MODIS') AS modis_raw,
               sum(f.factor_terra_aqua) FILTER (WHERE instrument = 'MODIS') AS modis_scaled
        FROM h JOIN factors f USING (country, burn_month)
        WHERE burn_date >= DATE '{VIIRS_START}' AND burn_year <= 2025
        GROUP BY ALL ORDER BY ALL
    """).df()
    monthly["period"] = monthly.year.map(lambda y: f"fit {y0}-{y1}" if y <= y1 else f"test {y1 + 1}-2025")
    monthly["abs_error_pct"] = 100 * (monthly.modis_scaled / monthly.viirs - 1).abs()
    yearly = monthly.groupby("year")[["viirs", "modis_raw", "modis_scaled"]].sum()
    yearly["error_pct"] = 100 * (yearly.modis_scaled / yearly.viirs - 1)
    yearly.to_csv(OUT / "validation_yearly.csv")
    print("\nMODIS scaled to VIIRS-equivalent against Suomi-NPP, per year:")
    print(yearly.round(1).to_string())
    print("\nMedian absolute error of the monthly count, per country (months with 500+ VIIRS hotspots):")
    print(monthly[monthly.viirs >= 500].groupby(["country", "period"]).abs_error_pct.median().round(1).to_string())

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    raw = con.execute("""
        SELECT burn_year AS year, count(*) FILTER (WHERE instrument = 'MODIS') AS "MODIS (raw)",
               count(*) FILTER (WHERE satellite = 'Suomi-NPP') AS "VIIRS Suomi-NPP (raw)"
        FROM h WHERE burn_year BETWEEN 2001 AND 2025 GROUP BY 1 ORDER BY 1
    """).df().set_index("year")
    raw.loc[raw.index < 2013, "VIIRS Suomi-NPP (raw)"] = None  # 2012 is not a full VIIRS year
    series = con.execute("""
        SELECT year(burn_date) AS year, sum(hotspots_harmonized) AS harmonized
        FROM cells WHERE year(burn_date) BETWEEN 2001 AND 2025 GROUP BY 1 ORDER BY 1
    """).df().set_index("year")
    fig, ax = plt.subplots(figsize=(10, 4.5))
    raw.plot(ax=ax, style=["--", "--"], color=["#888888", "#0072B2"], marker="o", ms=3)
    series.harmonized.plot(ax=ax, color="#D55E00", lw=2.5, label="Harmonized series (VIIRS-equivalent)")
    ax.axvline(2012, color="k", lw=0.8, ls=":")
    ax.text(2012.1, ax.get_ylim()[1] * 0.95, "VIIRS starts", fontsize=9, va="top")
    ax.set(title="Hotspots per year, Chile and Argentina: before and after harmonization (v0)",
           xlabel="burn year", ylabel="hotspots")
    ax.legend()
    fig.tight_layout()
    fig.savefig(ROOT / "docs" / "findings" / "03-harmonization-v0.png", dpi=130)


if __name__ == "__main__":
    main()
