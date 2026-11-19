"""Build the bundled two-week demo sample from a completed Penmanshiel 2022 validation run.

The sample lets the API, the CLI, the dashboard's Controller Lab and CI run a real closed loop
without the private research data folders. It contains one turbine's interval-mean power and two
forecasts (persistence and the neighbour-turbine LightGBM) for 14 days of February 2022.

2022 is the Stage 5 pre-freeze validation year, not the sealed test. Penmanshiel SCADA data is
CC-BY-4.0 (Zenodo DOI 10.5281/zenodo.16807304); see ATTRIBUTION.md in this folder.

Usage (only needed to regenerate; the output is committed):
    python -m windgrid.data.make_sample <run_dir_with_series.npz> [--start 4752]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / 'penmanshiel_2022_sample.npz'
ROWS = 14 * 144  # 14 days of 10-minute intervals
FORECASTS = ('persistence', 'lightgbm_spatial')


def build(run_dir: Path, start: int):
    source = run_dir / 'series.npz'
    data = np.load(source)
    window = slice(start, start + ROWS)
    arrays = {'times': data['times'][window], 'realised': data['realised'][window]}
    arrays.update({f'pred_{name}': data[f'pred_{name}'][window] for name in FORECASTS})
    if np.isnan(arrays['realised']).any() or any(np.isnan(arrays[f'pred_{n}']).any() for n in FORECASTS):
        raise ValueError('the selected window has missing values; choose another start')
    np.savez_compressed(OUT, **arrays)
    meta = {
        'source_file': 'publication_v2/stage5/runs/pen_validation_2022/series.npz',
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'start_row': start,
        'rows': ROWS,
        'turbine': 'Penmanshiel WT11',
        'forecasts': list(FORECASTS),
        'sample_sha256': hashlib.sha256(OUT.read_bytes()).hexdigest(),
    }
    (HERE / 'sample_provenance.json').write_bytes((json.dumps(meta, indent=1) + chr(10)).encode())
    return meta


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--start', type=int, default=4752)
    print(build(**vars(parser.parse_args(argv))))


if __name__ == '__main__':
    main()
