"""Time fields for the hotspot table. Rules and measurements: docs/eda-plan.md ("Time rules").

Three clocks, one per kind of question:
    UTC               storage, time differences, reconciliation with FIRMS (`acq_datetime`).
    Local solar time  everything about the sensor: UTC hour + longitude / 15.
    Civil time        everything about people: IANA zone of the region.

The day key is `burn_date`: the day from 06:00 to 06:00 local solar time. It is the only cut that
splits no satellite pass, so an afternoon and the night that follows stay in the same day.
"""

from __future__ import annotations

import unicodedata
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

DAY_CUT_H = 6.0     # local solar hour where a burn day starts
CUT_GUARD_H = 0.5   # no detection may be closer than this to the cut
EASTER_LON = -100.0  # Easter Island sits inside the Valparaíso polygon; split it by longitude

# (keyword in the accent-free, lower-case region name, IANA zone). First match wins.
_ZONES = {
    "Chile": (
        ("magallanes", "America/Punta_Arenas"),
        ("aysen", "America/Coyhaique"),
        ("aisen", "America/Coyhaique"),
        ("", "America/Santiago"),
    ),
    "Argentina": (
        ("buenos aires", "America/Argentina/Buenos_Aires"),  # province and CABA
        ("cordoba", "America/Argentina/Cordoba"),
        ("chaco", "America/Argentina/Cordoba"),
        ("corrientes", "America/Argentina/Cordoba"),
        ("entre rios", "America/Argentina/Cordoba"),
        ("formosa", "America/Argentina/Cordoba"),
        ("misiones", "America/Argentina/Cordoba"),
        ("santiago del estero", "America/Argentina/Cordoba"),
        ("santa fe", "America/Argentina/Cordoba"),
        ("salta", "America/Argentina/Salta"),
        ("la pampa", "America/Argentina/Salta"),
        ("neuquen", "America/Argentina/Salta"),
        ("rio negro", "America/Argentina/Salta"),
        ("jujuy", "America/Argentina/Jujuy"),
        ("tucuman", "America/Argentina/Tucuman"),
        ("catamarca", "America/Argentina/Catamarca"),
        ("chubut", "America/Argentina/Catamarca"),
        ("la rioja", "America/Argentina/La_Rioja"),
        ("san juan", "America/Argentina/San_Juan"),
        ("mendoza", "America/Argentina/Mendoza"),
        ("san luis", "America/Argentina/San_Luis"),
        ("santa cruz", "America/Argentina/Rio_Gallegos"),
        ("tierra del fuego", "America/Argentina/Ushuaia"),
    ),
}


def _plain(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def zone_for(country: str, region: str) -> str:
    """IANA zone of a first-level region. Fails on a region it does not know."""
    name = _plain(region)
    for keyword, zone in _ZONES.get(country, ()):
        if keyword in name:
            return zone
    raise ValueError(f"No time zone known for {country!r} / {region!r}")


def add_solar_fields(df: pd.DataFrame, strict: bool = True) -> pd.DataFrame:
    """Add solar_time_h, pass_slot, burn_date, burn_year, burn_month, season_year.

    Needs `acq_datetime` (UTC, zone-aware) and `longitude`.
    """
    utc = df["acq_datetime"]
    if utc.dt.tz is None or utc.isna().any():
        raise ValueError("acq_datetime must be zone-aware UTC with no missing values")
    lon_h = df["longitude"].to_numpy() / 15.0
    solar_h = (utc.dt.hour.to_numpy() + utc.dt.minute.to_numpy() / 60.0 + lon_h) % 24.0
    if strict:
        near = np.abs(solar_h - DAY_CUT_H) < CUT_GUARD_H
        if near.any():
            raise ValueError(
                f"{int(near.sum())} detections within {CUT_GUARD_H} h of the {DAY_CUT_H:.0f}:00 "
                "local solar day cut: the cut would split a satellite pass"
            )
    shifted = utc.dt.tz_localize(None) + pd.to_timedelta((lon_h - DAY_CUT_H) * 3600, unit="s")
    burn_year = shifted.dt.year.to_numpy()
    burn_month = shifted.dt.month.to_numpy()

    df["solar_time_h"] = solar_h.astype("float32")
    df["pass_slot"] = pd.Categorical(
        np.where((solar_h >= 6.0) & (solar_h < 18.0), "day_pass", "night_pass"),
        categories=["day_pass", "night_pass"],
    )
    df["burn_date"] = shifted.dt.date
    df["burn_year"] = burn_year.astype("int16")
    df["burn_month"] = burn_month.astype("int8")
    # Fire season, July to June (CONAF), named by the year it starts: 2016 is July 2016 - June 2017.
    df["season_year"] = np.where(burn_month >= 7, burn_year, burn_year - 1).astype("int16")
    return df


def add_civil_fields(df: pd.DataFrame, region_col: str = "admin1") -> pd.DataFrame:
    """Add tz_name, utc_offset_min, local_wall_time, local_date.

    Needs `acq_datetime` (UTC), `longitude`, `country` and a region column with no missing values.
    Conversion always goes from UTC to local, so clock changes cannot produce invalid times.
    """
    region = df[region_col].astype("object")
    if region.isna().any():
        raise ValueError(f"{int(region.isna().sum())} rows have no region to take a time zone from")
    key = df["country"].astype("object") + "|" + region
    lookup = {k: zone_for(*k.split("|", 1)) for k in key.unique()}
    tz_name = key.map(lookup).to_numpy(dtype=object)
    tz_name[df["longitude"].to_numpy() < EASTER_LON] = "Pacific/Easter"

    utc = df["acq_datetime"]
    naive_utc = utc.dt.tz_localize(None)
    walls, offsets = [], []
    for name in pd.unique(tz_name):
        rows = tz_name == name
        wall = utc[rows].dt.tz_convert(ZoneInfo(name)).dt.tz_localize(None)  # fails if zone missing
        walls.append(wall)
        offsets.append((wall - naive_utc[rows]).dt.total_seconds() // 60)
    wall = pd.concat(walls).reindex(df.index)

    df["tz_name"] = pd.Categorical(tz_name)
    df["utc_offset_min"] = pd.concat(offsets).reindex(df.index).astype("int16")
    df["local_wall_time"] = wall
    df["local_date"] = wall.dt.date
    return df
