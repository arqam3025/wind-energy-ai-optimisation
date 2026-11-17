"""Preflight guards for frozen evaluation; no fitting or parameter selection."""
from pathlib import Path
import os
import numpy as np
import pandas as pd
from prepare_frozen_heldout import ROOT, verify

SCHEDULE = pd.read_csv(ROOT / 'results/evaluation_schedule.csv')
VALID_BLOCKS = tuple(SCHEDULE.loc[SCHEDULE.evaluation_role.eq('evaluation'), 'block_id'].astype(int))

def output_directory(kind):
    run = os.environ.get('WIND_HELDOUT_RUN')
    if not run or Path(run).name != run:
        raise ValueError('Set WIND_HELDOUT_RUN to a unique run directory name')
    return ROOT / 'results/frozen_heldout' / run / kind

def heldout_history():
    # Full precomputed history is filtered by STRICT target time in frozen module.
    # Include excluded block 6 as observable past history, never as a scored test block.
    return [pd.read_csv(ROOT / f'data/processed/evaluation_block_{int(b)}.csv', parse_dates=['timestamp'])
            for b in SCHEDULE.block_id]

def preflight():
    verify()
    assert 6 not in VALID_BLOCKS
    development = pd.concat([pd.read_csv(p, parse_dates=['timestamp']) for p in
        sorted((ROOT / 'data/processed/controller_development_blocks').glob('*.csv'))])
    for entry in SCHEDULE.itertuples():
        block = pd.read_csv(ROOT / f'data/processed/evaluation_block_{entry.block_id}.csv', parse_dates=['timestamp'])
        assert len(block) == entry.forecast_origins == 144
        assert block.timestamp.iloc[0] == pd.Timestamp(entry.start_timestamp)
        assert block.timestamp.iloc[-1] == pd.Timestamp(entry.end_timestamp)
        assert block.timestamp.diff().iloc[1:].eq(pd.Timedelta(minutes=10)).all()
        assert np.isfinite(block.select_dtypes('number')).all().all()
        assert np.allclose(block.actual_h1_kw.iloc[:-1], block.current_power_kw.iloc[1:], atol=.001)
        if entry.block_id in VALID_BLOCKS:
            # Protect target intervals as well as forecast origins.
            assert not development.timestamp.between(block.timestamp.min()-pd.Timedelta(minutes=60), block.timestamp.max()+pd.Timedelta(minutes=60)).any(), 'Development overlap'

if __name__ == '__main__':
    preflight()
    print(f'PASS: freeze, physical input alignment, {len(VALID_BLOCKS)} eligible blocks; block 6 excluded')
