"""Stage 5 frozen-protocol runner for the SEALED second-site test (Penmanshiel 2023–2024).

The 2022 validation check runs before the freeze through ``site_experiment.py --stage validation``.
This runner refuses unless:
- the protocol file's SHA-256 equals ``PROTOCOL_SHA256``;
- the git tree is clean;
- no completed run already exists in the output directory.

It records the commit, environment and SHA-256 of every output. It is run once; a resume is
allowed only from the same commit and protocol, and must be reported as a deviation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / 'docs' / 'STAGE5_CONFIRMATORY_PROTOCOL.md'
PROTOCOL_SHA256 = '509885b8e3bb7bbb6fe2add6ffed344ba0ecba7feee73ae13cdf10b6730e4aab'  # frozen 2026-11-17


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args) -> str:
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def preflight(out: Path) -> dict:
    if PROTOCOL_SHA256 is None:
        raise SystemExit('Protocol not frozen: PROTOCOL_SHA256 is unset')
    if _sha(PROTOCOL) != PROTOCOL_SHA256:
        raise SystemExit('Protocol file does not match the frozen SHA-256')
    if _git('status', '--porcelain', '--untracked-files=no'):
        raise SystemExit('Tracked files are modified; run from a clean checkout of the frozen commit')
    if (out / 'COMPLETED.json').exists():
        raise SystemExit(f'{out} already holds a completed run; it is never overwritten')
    head = _git('rev-parse', 'HEAD')
    started = out / 'STARTED.json'
    if started.exists():
        previous = json.loads(started.read_text(encoding='utf-8'))
        if previous['git_head'] != head or previous['protocol_sha256'] != PROTOCOL_SHA256:
            raise SystemExit('A resume must use the same commit and protocol')
    import lightgbm, numpy, pandas, scipy  # noqa: E401
    return {'stage': 'sealed', 'site': 'penmanshiel', 'protocol_sha256': PROTOCOL_SHA256, 'git_head': head,
            'started_utc': datetime.now(timezone.utc).isoformat(),
            'environment': {'python': platform.python_version(), 'numpy': numpy.__version__,
                            'pandas': pandas.__version__, 'scipy': scipy.__version__,
                            'lightgbm': lightgbm.__version__, 'platform': platform.platform()}}


def run(out: Path, workers: int):
    from . import analysis, site_experiment
    from publication_v2.stage4.analysis import descriptive, forecast_skill, render_skill
    record = preflight(out)
    out.mkdir(parents=True, exist_ok=True)
    if not (out / 'STARTED.json').exists():
        (out / 'STARTED.json').write_bytes((json.dumps(record, indent=1) + chr(10)).encode())
    if not (out / 'series.npz').exists():
        site_experiment.prepare(out, 'penmanshiel', 'sealed', sealed_opt_in=True)
    results = site_experiment.run(out, workers=workers)
    tests, rows = analysis.primary_tests(results['results']), descriptive(results['results'])
    skill = forecast_skill(out)
    (out / 'tests.json').write_bytes((json.dumps({'tests': tests, 'descriptive': rows}, indent=1) + chr(10)).encode())
    (out / 'forecast_skill.json').write_bytes((json.dumps(skill, indent=1) + chr(10)).encode())
    text = analysis.render(tests, rows, results, 'Stage 5 sealed second-site test: Penmanshiel 2023–2024') + render_skill(skill)
    (out / 'REPORT.md').write_bytes(text.encode())
    files = sorted(p.name for p in out.iterdir() if p.is_file() and p.name != 'COMPLETED.json')
    completed = {**record, 'completed_utc': datetime.now(timezone.utc).isoformat(),
                 'file_sha256': {name: _sha(out / name) for name in files}}
    (out / 'COMPLETED.json').write_bytes((json.dumps(completed, indent=1) + chr(10)).encode())
    print(text)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = parser.parse_args(argv)
    run(args.out, args.workers)


if __name__ == '__main__':
    sys.exit(main())
