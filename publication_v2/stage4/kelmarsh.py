"""Kelmarsh SCADA loader (Stage 4, real data). Development years only unless a frozen protocol opts in.

Timing convention (see docs/STAGE4_DEVELOPMENT_NOTES.md): a row labelled t holds the mean over
[t, t+10 min) in UTC. Its value is first available at t + 10 min, so the series is re-indexed to
the interval END: ``end = label + 10 min``. A decision at time d may use every value whose end is
<= d; the next six targets end at d + 10, ..., d + 60 min.

Realised power is y = max(0, P). Nothing is imputed: missing values stay NaN, and callers skip
any decision or episode that needs them.
"""
from __future__ import annotations

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
        text = archive.read(members[0]).decode('utf-8')
    lines = text.splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.startswith('# Date and time'))
    if 'Time zone: UTC' not in text[:2000]:
        raise DataAccessError('File header does not declare UTC')
    body = '\n'.join([lines[header_index][2:]] + lines[header_index + 1:])
    frame = pd.read_csv(io.StringIO(body), usecols=lambda c: c in COLUMNS or c == 'Date and time'
                        or c.startswith('Wind direction (') and c.endswith(')') and ',' not in c)
    direction = [c for c in frame.columns if c.startswith('Wind direction (')]
    if len(direction) != 1 or len(frame.columns) != len(COLUMNS) + 2:
        raise DataAccessError(f'Unexpected column set: {list(frame.columns)}')
    frame = frame.rename(columns={direction[0]: 'wind_dir_deg'})
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
