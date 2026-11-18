"""Kelmarsh SCADA loader (Stage 4, real data). Development years only unless a frozen protocol opts in.

Timing convention (see docs/STAGE4_DEVELOPMENT_NOTES.md): a row labelled t holds the mean over
[t, t+10 min) in UTC. Its value is first available at t + 10 min, so the series is re-indexed to
the interval END: ``end = label + 10 min``. A decision at time d may use every value whose end is
<= d; the next six targets end at d + 10, ..., d + 60 min.

Realised power is y = max(0, P). Nothing is imputed: missing values stay NaN, and callers skip
any decision or episode that needs them.
"""
from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path('C:/ResearchData/kelmarsh_zenodo_16807551')
ARCHIVES = {
    2018: ('development', 'Kelmarsh_SCADA_2018_3084.zip', '972e5280172216a5fe76dcab19c741b0'),
    2019: ('development', 'Kelmarsh_SCADA_2019_3085.zip', '14348a1572b722e1be10e53cd145c39a'),
    2020: ('development', 'Kelmarsh_SCADA_2020_3086.zip', 'e189e02da98f32e74acc72e8559ef0db'),
    2021: ('development', 'Kelmarsh_SCADA_2021_4456.zip', '4e0ef3d65f067fd3d8f3d30e79ab01ae'),
    2022: ('validation', 'Kelmarsh_SCADA_2022_4457.zip', 'b695d2b21cd5a236b2e690e0a43df5ab'),
    2023: ('sealed_test', 'Kelmarsh_SCADA_2023_5961.zip', '685d9589347d1866f6f2cfe45b9af4f4'),
    2024: ('sealed_test', 'Kelmarsh_SCADA_2024_5962.zip', 'e9e3318f5b393d8596ff1801f8da0414'),
}
DEVELOPMENT_YEARS = (2018, 2019, 2020, 2021)
STEP = pd.Timedelta(minutes=10)
EOL = chr(13) + chr(10)  # characters stripped from line ends
COLUMNS = {
    'Power (kW)': 'power_kw',
    'Wind speed (m/s)': 'wind_ms',
    'Wind speed, Standard deviation (m/s)': 'wind_sd_ms',
    'Lost Production to Downtime and Curtailment Total (kWh)': 'lost_kwh',
}


class DataAccessError(RuntimeError):
    pass


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def _read_deduplicated(handle, name):
    """Stream one turbine file and resolve the cumulative-export duplicates of the 2023-2024 files.

    Rule (fixed after the structural check recorded in runs/sealed_v1/DEVIATIONS.md, D1, and
    before any outcome was computed): rows are grouped by timestamp. Versions of a row may differ
    only by values being replaced with "NaN" (as observed). The most complete version is kept;
    if two versions disagree on any non-missing value, or each has a value the other lacks, the
    loader refuses. Missing values stay NaN and are never imputed. Files with one row per
    timestamp (2018-2022) are unaffected.
    """
    header, preamble = None, []
    for line in handle:
        if line.startswith('# Date and time'):
            raw_header = line[2:].rstrip(EOL)
            header = next(csv.reader([raw_header]))
            break
        preamble.append(line)
    if header is None or not any('Time zone: UTC' in line for line in preamble):
        raise DataAccessError('Missing header or UTC declaration')
    wanted = ['Date and time', *COLUMNS]
    direction = [c for c in header if c.startswith('Wind direction (') and c.endswith(')') and ',' not in c]
    if len(direction) != 1 or any(c not in header for c in wanted):
        raise DataAccessError(f'Unexpected column set in {name}')
    kept, duplicates = {}, 0
    for line in handle:
        line = line.rstrip(EOL)
        if not line:
            continue
        stamp = line.split(',', 1)[0]
        previous = kept.get(stamp)
        if previous is None:
            kept[stamp] = line
            continue
        duplicates += 1
        if previous == line:
            continue
        old, new = previous.split(','), line.split(',')
        if len(old) != len(new):
            raise DataAccessError(f'{name}: rows of different width for {stamp}')
        missing = ('NaN', '')
        conflict = any(a != b and a not in missing and b not in missing for a, b in zip(old, new))
        new_adds = any(a in missing and b not in missing for a, b in zip(old, new))
        old_adds = any(b in missing and a not in missing for a, b in zip(old, new))
        if conflict or (new_adds and old_adds):
            raise DataAccessError(f'{name}: incompatible rows for {stamp}')
        if new_adds:
            kept[stamp] = line   # the more complete version; the other differs only value -> NaN
    # Parse the resolved rows with the same pandas CSV parser used for 2018-2022, so files that
    # had no duplicates are reproduced bit for bit (floating-point parsing differs between parsers).
    body = chr(10).join([raw_header] + list(kept.values()))
    frame = pd.read_csv(io.StringIO(body), usecols=lambda c: c in COLUMNS or c == 'Date and time' or c == direction[0])
    frame = frame.rename(columns={direction[0]: 'wind_dir_deg'})
    frame.attrs['resolved_duplicate_rows'] = duplicates
    return frame


def load_turbine(year: int, turbine: int = 1, *, root: Path = ROOT, allow: tuple[str, ...] = ('development',)):
    """One turbine-year, indexed by interval END (UTC). Refuses years whose role is not allowed."""
    if year not in ARCHIVES:
        raise DataAccessError(f'Unknown year {year}')
    role, name, md5 = ARCHIVES[year]
    if role not in allow:
        raise DataAccessError(f'{year} is {role.upper()}; opening it requires an explicit, protocol-backed opt-in')
    path = root / role / name
    if _md5(path) != md5:
        raise DataAccessError(f'MD5 mismatch for {name}')
    with zipfile.ZipFile(path) as archive:
        members = [m for m in archive.namelist() if m.startswith(f'Turbine_Data_Kelmarsh_{turbine}_')]
        if len(members) != 1:
            raise DataAccessError(f'Expected one file for turbine {turbine} in {name}, found {members}')
        with archive.open(members[0]) as raw:
            frame = _read_deduplicated(io.TextIOWrapper(raw, encoding='utf-8', newline=''), name)
    label = pd.to_datetime(frame.pop('Date and time'), format='%Y-%m-%d %H:%M:%S', utc=True)
    frame = frame.rename(columns=COLUMNS)
    frame.index = pd.DatetimeIndex(label + STEP, name='interval_end')
    expected = pd.date_range(f'{year}-01-01 00:10', f'{year + 1}-01-01 00:00', freq=STEP, tz='UTC')
    if not frame.index.is_unique or not frame.index.equals(expected):
        raise DataAccessError(f'{year}: timestamps are not the complete, unique 10-minute grid')
    frame['realised_kw'] = frame['power_kw'].clip(lower=0.0)
    frame.attrs.update(source=name, md5=md5, role=role, turbine=turbine)
    return frame


def load_development(turbine: int = 1, *, root: Path = ROOT):
    frames = [load_turbine(year, turbine, root=root) for year in DEVELOPMENT_YEARS]
    return pd.concat(frames)


def load_development_farm(*, root: Path = ROOT):
    """All six turbines for the development years, keyed by turbine number."""
    return {t: load_development(t, root=root) for t in range(1, 7)}


def summary(frame: pd.DataFrame) -> dict:
    y = frame['realised_kw']
    ramp = y.diff().abs()
    return {'rows': int(len(frame)), 'missing_power': float(y.isna().mean()),
            'mean_kw': float(y.mean()), 'downtime_or_curtailment_rows': float((frame['lost_kwh'] > 0).mean()),
            'ramps_over_200kw': float((ramp > 200).sum() / ramp.notna().sum()),
            'p95_ramp_kw': float(np.nanquantile(ramp, .95))}
