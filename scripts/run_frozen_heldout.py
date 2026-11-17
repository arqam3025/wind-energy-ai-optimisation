"""Sequential, resumable frozen evaluation. Completed CSVs are never overwritten."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
from heldout_support import ROOT, VALID_BLOCKS, preflight

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', default=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    parser.add_argument('--blocks', nargs='+', type=int, default=list(VALID_BLOCKS))
    args = parser.parse_args()
    assert set(args.blocks) <= set(VALID_BLOCKS)
    preflight()
    run = ROOT / 'results/frozen_heldout' / args.run
    run.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, WIND_HELDOUT_RUN=args.run)
    provenance = run / 'provenance.json'
    if not provenance.exists():
        paths = list((ROOT/'scripts').glob('*heldout*.py')) + [ROOT/'scripts/heldout_support.py']
        paths += list((ROOT/'data/processed').glob('evaluation_block_*.csv'))
        paths += list((ROOT/'data/processed/controller_development_blocks').glob('*.csv'))
        paths += [ROOT/'results/multistep_calibration_split.csv', ROOT/'results/multistep_uncertainty_calibration_split.csv', ROOT/'results/evaluation_schedule.csv']
        with provenance.open('x') as handle:
            json.dump({'created_utc': datetime.now(timezone.utc).isoformat(), 'python':sys.version,
                       'packages': {p:importlib.metadata.version(p) for p in ['numpy','pandas','cvxpy','highspy','scipy','matplotlib']},
                       'eligible_blocks':list(VALID_BLOCKS), 'excluded_blocks':{'6':'explicit development role and preparation script'},
                       'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}, handle, indent=2)
    else:
        for name, expected in json.loads(provenance.read_text())['sha256'].items():
            assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == expected, name
    for block in args.blocks:
        for kind in ['fixed','adaptive_one_sided']:
            output = run/kind/f'adaptive_charging_mpc_block_{block}_weight_0p500.csv'
            if output.exists():
                print(f'Existing (not overwritten): {output}', flush=True)
                continue
            log = run/f'{kind}_block_{block}_{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")}.log'
            print(f'Running {kind} block {block}', flush=True)
            with log.open('x') as handle:
                subprocess.run([sys.executable, f'scripts/frozen_{kind}_heldout.py', str(block)], cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT, check=True)
            print(f'Completed {kind} block {block}', flush=True)
    print(f'COMPLETE: {run}', flush=True)

if __name__ == '__main__':
    main()
