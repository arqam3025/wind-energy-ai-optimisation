"""Site-generic SCADA access and features (Stage 5): Kelmarsh and Penmanshiel, one code path.

- Loading reuses the Stage 4 rules unchanged: MD5 verification, a UTC interval-END index
  (label + 10 min), y = max(0, P), de-duplication of cumulative exports, no imputation, and
  role-based access refusal.
- Features reuse the Stage 2 contract plus the Stage 4 neighbour features, generalised to any
  target turbine and neighbour set. For Kelmarsh (target 1, neighbours 2–6), ``build_spatial``
  reproduces ``stage4.features.build_spatial`` exactly; a test checks this.
"""
from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from publication_v2.stage4 import kelmarsh
from publication_v2.stage4.features import FEATURES, LABELS, build


@dataclass(frozen=True)
class Site:
    name: str
    root: Path
    archives: dict          # year -> (role, file, md5)
    member_pattern: str     # regex with {t} for the turbine number, matched against archive member names
    target: int
    neighbours: tuple


SITES = {
    'kelmarsh': Site('kelmarsh', kelmarsh.ROOT, kelmarsh.ARCHIVES, r'Turbine_Data_Kelmarsh_{t}_', 1, (2, 3, 4, 5, 6)),
    'penmanshiel': Site('penmanshiel', Path('C:/ResearchData/penmanshiel_zenodo_16807304'), {
        2018: ('development', 'Penmanshiel_SCADA_2018_WT11-15_3116.zip', '7c40dc00df6d6301427213e15170b927'),
        2019: ('development', 'Penmanshiel_SCADA_2019_WT11-15_3117.zip', '92747a976716c5f35d9ee6462958fd7a'),
        2020: ('development', 'Penmanshiel_SCADA_2020_WT11-15_3118.zip', 'c73323f21451c08247dbdb5d1a1434a9'),
        2021: ('development', 'Penmanshiel_SCADA_2021_WT11-15_4461.zip', 'f5804b90089ce4d50dc5117fda6f675c'),
        2022: ('validation', 'Penmanshiel_SCADA_2022_WT11-15_4463.zip', '5f4743133a9cf65ad33de139b43f96b4'),
        2023: ('sealed_test', 'Penmanshiel_SCADA_2023_WT_11-15_5964.zip', '813ad4635cf50b9d96b253ee53175086'),
        2024: ('sealed_test', 'Penmanshiel_SCADA_2024_WT_11-15_5966.zip', 'e0a700cad1d45f4130272feaef244b12'),
    }, r'Turbine_Data_Penmanshiel_0?{t}_', 11, (12, 13, 14, 15)),
}
STEP = pd.Timedelta(minutes=10)


def load_turbine(site: Site, year: int, turbine: int, *, allow=('development',)):
    """One turbine-year on the complete interval-END grid. Refuses roles that are not allowed."""
    if year not in site.archives:
        raise kelmarsh.DataAccessError(f'{site.name}: unknown year {year}')
    role, name, md5 = site.archives[year]
    if role not in allow:
        raise kelmarsh.DataAccessError(f'{site.name} {year} is {role.upper()}; opening it requires a protocol-backed opt-in')
    path = site.root / role / name
    if kelmarsh._md5(path) != md5:
        raise kelmarsh.DataAccessError(f'MD5 mismatch for {name}')
    pattern = re.compile(site.member_pattern.format(t=turbine))
    with zipfile.ZipFile(path) as archive:
        members = [m for m in archive.namelist() if pattern.match(Path(m).name)]
        if len(members) != 1:
            raise kelmarsh.DataAccessError(f'Expected one file for turbine {turbine} in {name}, found {members}')
        with archive.open(members[0]) as raw:
            frame = kelmarsh._read_deduplicated(io.TextIOWrapper(raw, encoding='utf-8', newline=''), name)
    label = pd.to_datetime(frame.pop('Date and time'), format='%Y-%m-%d %H:%M:%S', utc=True)
    frame = frame.rename(columns=kelmarsh.COLUMNS)
    frame.index = pd.DatetimeIndex(label + STEP, name='interval_end')
    expected = pd.date_range(f'{year}-01-01 00:10', f'{year + 1}-01-01 00:00', freq=STEP, tz='UTC')
    if not frame.index.is_unique or not frame.index.isin(expected).all():
        raise kelmarsh.DataAccessError(f'{site.name} {year}: timestamps off the 10-minute grid or duplicated')
    missing_rows = int(len(expected) - len(frame))
    frame = frame.reindex(expected)          # absent rows become NaN (missing), never imputed
    frame.index.name = 'interval_end'
    frame['realised_kw'] = frame['power_kw'].clip(lower=0.0)
    frame.attrs.update(source=name, md5=md5, role=role, turbine=turbine, absent_rows=missing_rows)
    return frame


def load_frames(site: Site, years, *, allow=('development',)):
    turbines = (site.target, *site.neighbours)
    return {t: pd.concat([load_turbine(site, y, t, allow=allow) for y in years]) for t in turbines}


def spatial_features(site: Site):
    return FEATURES + [f'n{i}_{k}' for i in range(len(site.neighbours)) for k in ('p', 'dp', 'dp3', 'w', 'dw')] + [
        'farm_dp', 'farm_dp3', 'dir_sin', 'dir_cos', 'p_std_60']


def build_spatial(frames: dict, site: Site) -> pd.DataFrame:
    """Stage 2 features of the target turbine plus causal neighbour features (Stage 4 definitions)."""
    target = frames[site.target]
    out = build(target)
    labels = out[LABELS]
    out = out.drop(columns=LABELS)
    for i, t in enumerate(site.neighbours):
        f = frames[t]
        if not f.index.equals(target.index):
            raise ValueError('turbine frames must share one grid')
        p, w = f['realised_kw'], f['wind_ms']
        out[f'n{i}_p'], out[f'n{i}_dp'], out[f'n{i}_dp3'] = p, p - p.shift(1), p - p.shift(3)
        out[f'n{i}_w'], out[f'n{i}_dw'] = w, w - w.shift(1)
    farm = sum(frames[t]['realised_kw'] for t in (site.target, *site.neighbours))
    out['farm_dp'], out['farm_dp3'] = farm - farm.shift(1), farm - farm.shift(3)
    direction = np.deg2rad(target['wind_dir_deg'])
    out['dir_sin'], out['dir_cos'] = np.sin(direction), np.cos(direction)
    out['p_std_60'] = target['realised_kw'].rolling(6, min_periods=6).std()
    if list(out.columns) != spatial_features(site):
        raise AssertionError('spatial feature order changed')
    return pd.concat([out, labels], axis=1)
