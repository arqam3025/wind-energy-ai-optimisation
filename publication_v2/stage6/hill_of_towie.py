"""Hill of Towie SCADA access (Stage 6 third site), following the admission record.

Rules (docs/DATA_ADMISSION_HILL_OF_TOWIE.md):
- roles: development 2016–2023, validation 2024, sealed_test 2025; 2026 is excluded;
- MD5 verification against the published Zenodo checksums before any read;
- timestamps are UTC interval ENDS already (no shift). As in Stages 4–5, an interval belongs to
  the year in which it STARTS: year Y is the interval-end grid Y-01-01 00:10 … Y+1-01-01 00:00.
  Each monthly file repeats its boundary timestamps (it runs from the 1st 00:00 to the next 1st
  00:00), so the year's own file contains all of year Y plus one extra row at Y-01-01 00:00
  (the previous year's last interval), which is dropped; no year reads another role's file;
- y = max(0, P); rows absent from a file are missing (NaN), never imputed;
- duplicate (timestamp, turbine) rows are resolved only by the most-complete-version rule, with
  refusal on any conflicting values.

Per-year wide tables (one column per turbine) are cached as Parquet under the data root, in a
folder named after the role, so a sealed cache can exist only after the sealed year was opened.
"""

from __future__ import annotations

import hashlib
import math
import zipfile
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from publication_v2.stage4.kelmarsh import DataAccessError

ROOT = Path('C:/ResearchData/hill_of_towie_zenodo_20204946')
ARCHIVES = {
    2016: ('development', '74c6807483a6e8c767b9082afff6558d'),
    2017: ('development', 'c7cbe0b4d99c69994b95b1c1557ce0a4'),
    2018: ('development', '5d3a77aa05c75ea8476cc279a24d48ac'),
    2019: ('development', 'ca240b179200f5db25a273a1291eb597'),
    2020: ('development', '51b9cd3a98469373302722d1ab8094b7'),
    2021: ('development', '86d59d93afab4916bf06949a8986e644'),
    2022: ('development', '3861de12eb3ba588f48259c918ade242'),
    2023: ('development', '45eceb1855af89cf4dc215f2ab97eda1'),
    2024: ('validation', '89783562792fd71fc7a8543faf93ab18'),
    2025: ('sealed_test', 'd3cd7edb535a45ffca1c7028b397f035'),
}
TURBINES = tuple(f'T{i:02d}' for i in range(1, 22))
STATION_OFFSET = 2304509  # StationId = turbine number + offset (README)
TARGET = 'T10'
RATED_KW = 2300.0
STEP = pd.Timedelta(minutes=10)
# signal name -> (table, column)
SIGNALS = {
    'power_kw': ('tblSCTurGrid', 'wtc_ActPower_mean'),
    'wind_ms': ('tblSCTurbine', 'wtc_AcWindSp_mean'),
    'nacelle_deg': ('tblSCTurbine', 'wtc_NacelPos_mean'),
}
CACHE_VERSION = 2


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1 << 22), b''):
            digest.update(block)
    return digest.hexdigest()


@lru_cache(maxsize=None)
def _verified(path: str, md5: str) -> bool:
    if _md5(Path(path)) != md5:
        raise DataAccessError(f'MD5 mismatch for {path}')
    return True


def archive(year: int, allow=('development',)) -> Path:
    if year not in ARCHIVES:
        raise DataAccessError(f'Hill of Towie {year} is not admitted (2026 is excluded)')
    role, md5 = ARCHIVES[year]
    if role not in allow:
        raise DataAccessError(f'Hill of Towie {year} is {role.upper()}; opening it requires a protocol-backed opt-in')
    path = ROOT / role / f'{year}.zip'
    if not path.exists():
        raise DataAccessError(f'{path} is missing (download it and verify the MD5 first)')
    _verified(str(path), md5)
    return path


def year_grid(year: int) -> pd.DatetimeIndex:
    return pd.date_range(f'{year}-01-01 00:10', f'{year + 1}-01-01 00:00', freq=STEP, tz='UTC', name='interval_end')


def _deduplicate(frame: pd.DataFrame, columns, source: str) -> pd.DataFrame:
    """One row per (TimeStamp, StationId): keep the most complete version; refuse on conflict."""
    keys = ['TimeStamp', 'StationId']
    dup = frame.duplicated(keys, keep=False)
    if not dup.any():
        return frame
    clean, rows = frame[~dup], []
    for _, group in frame[dup].groupby(keys, sort=False):
        values = group[list(columns)]
        best = values.notna().sum(axis=1).idxmax()
        reference = values.loc[best]
        for _, other in values.iterrows():
            both = reference.notna() & other.notna()
            if not np.allclose(reference[both].to_numpy(float), other[both].to_numpy(float), rtol=0, atol=1e-9):
                raise DataAccessError(f'{source}: conflicting duplicate rows for {tuple(group.iloc[0][keys])}')
        rows.append(group.loc[[best]])
    return pd.concat([clean, *rows]).sort_values(keys, kind='stable')


def _read_table(zf: zipfile.ZipFile, table: str, columns, year: int, source: str) -> pd.DataFrame:
    members = sorted(n for n in zf.namelist() if n.startswith(f'{table}_{year}_') and n.endswith('.csv'))
    if len(members) != 12:
        raise DataAccessError(f'{source}: expected 12 monthly {table} files, found {len(members)}')
    parts = []
    for member in members:
        with zf.open(member) as handle:
            parts.append(pd.read_csv(handle, usecols=['TimeStamp', 'StationId', *columns], encoding='utf-8-sig'))
    frame = pd.concat(parts, ignore_index=True)
    return _deduplicate(frame, columns, f'{source}:{table}')


def _build_year(year: int, path: Path) -> dict:
    source = path.name
    grid = year_grid(year)
    by_table = {}
    for name, (table, column) in SIGNALS.items():
        by_table.setdefault(table, []).append((name, column))
    out = {}
    with zipfile.ZipFile(path) as zf:
        for table, pairs in by_table.items():
            frame = _read_table(zf, table, [c for _, c in pairs], year, source)
            times = pd.to_datetime(frame['TimeStamp'], format='%Y-%m-%d %H:%M:%S', utc=True)
            previous_year_end = times == pd.Timestamp(f'{year}-01-01 00:00', tz='UTC')
            frame, times = frame[~previous_year_end], times[~previous_year_end]
            if not times.isin(grid).all():
                bad = int((~times.isin(grid)).sum())
                raise DataAccessError(f'{source}:{table}: {bad} timestamps off the year/10-minute grid')
            turbine = frame['StationId'] - STATION_OFFSET
            if not turbine.between(1, 21).all():
                raise DataAccessError(f'{source}:{table}: unknown StationId values')
            frame = frame.assign(interval_end=times, turbine=turbine.map(lambda t: f'T{t:02d}'))
            for name, column in pairs:
                wide = frame.pivot(index='interval_end', columns='turbine', values=column)
                out[name] = wide.reindex(index=grid, columns=list(TURBINES)).astype('float64')
    return out


def load_year(year: int, *, allow=('development',)) -> dict:
    """Wide per-signal tables (index: interval end UTC; columns: T01..T21) for one admitted year."""
    path = archive(year, allow)
    role = ARCHIVES[year][0]
    cache = ROOT / 'cache' / role / f'{year}_v{CACHE_VERSION}.parquet'
    if cache.exists():
        table = pd.read_parquet(cache)
        signals = {name: table.xs(name, axis=1, level=0) for name in SIGNALS}
    else:
        signals = _build_year(year, path)
        cache.parent.mkdir(parents=True, exist_ok=True)
        pd.concat(signals, axis=1).to_parquet(cache)
    for name, frame in signals.items():
        frame.index = pd.DatetimeIndex(frame.index, name='interval_end').tz_convert('UTC')
        frame.attrs.update(source=path.name, role=role, year=year, signal=name)
    return signals


def load_years(years, *, allow=('development',)) -> dict:
    parts = [load_year(y, allow=allow) for y in years]
    return {name: pd.concat([p[name] for p in parts]) for name in SIGNALS}


def turbine_frame(signals: dict, turbine: str = TARGET) -> pd.DataFrame:
    """One turbine in the Stage 2/4 feature-contract layout (realised_kw, wind_ms, wind_dir_deg)."""
    frame = pd.DataFrame({'power_kw': signals['power_kw'][turbine], 'wind_ms': signals['wind_ms'][turbine],
                          'wind_dir_deg': farm_direction(signals)})
    frame['realised_kw'] = frame['power_kw'].clip(lower=0.0)
    return frame


def farm_frame(signals: dict) -> pd.DataFrame:
    """Farm-level unit: the sum of the 21 turbines (missing if any turbine is missing)."""
    power = signals['power_kw'].clip(lower=0.0)
    total = power.sum(axis=1, min_count=len(TURBINES))
    frame = pd.DataFrame({'power_kw': total, 'wind_ms': signals['wind_ms'].median(axis=1, skipna=False),
                          'wind_dir_deg': farm_direction(signals)})
    frame['realised_kw'] = frame['power_kw']
    return frame


def farm_direction(signals: dict) -> pd.Series:
    """Farm wind direction: circular mean of the nacelle positions (degrees from north), if >= 11 turbines report."""
    radians = np.deg2rad(signals['nacelle_deg'])
    s, c = np.sin(radians).mean(axis=1, skipna=True), np.cos(radians).mean(axis=1, skipna=True)
    direction = (np.rad2deg(np.arctan2(s, c)) + 360.) % 360.
    count = signals['nacelle_deg'].notna().sum(axis=1)
    return direction.where(count >= 11)  # majority of turbines reporting


@lru_cache(maxsize=1)
def geometry() -> pd.DataFrame:
    """Turbine positions (metres east/north of the target) from the published metadata."""
    meta = pd.read_csv(ROOT / 'metadata' / 'Hill_of_Towie_turbine_metadata.csv', encoding='utf-8-sig')
    meta = meta.set_index('Turbine Name').loc[list(TURBINES)]
    lat0, lon0 = meta.loc[TARGET, ['Latitude', 'Longitude']]
    north = (meta['Latitude'] - lat0) * 111_320.0
    east = (meta['Longitude'] - lon0) * 111_320.0 * math.cos(math.radians(lat0))
    bearing = (np.rad2deg(np.arctan2(east, north)) + 360.) % 360.
    return pd.DataFrame({'east_m': east, 'north_m': north, 'distance_m': np.hypot(east, north),
                         'bearing_deg': bearing})
