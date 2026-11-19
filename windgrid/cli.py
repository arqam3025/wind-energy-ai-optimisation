"""``windgrid`` command-line interface.

windgrid serve      start the dispatch API (http://127.0.0.1:8000/docs)
windgrid dashboard  start the Streamlit dashboard (http://127.0.0.1:8501)
windgrid simulate   compare controllers on the bundled sample, closed loop
windgrid dispatch   one decision from a JSON request file (or the bundled sample)
windgrid check      run the same lint and test steps as CI
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Test suites that need no private data; the same list runs in CI.
SUITES = (
    'windgrid/tests',
    'publication_v2/tests',
    'publication_v2/stage31/tests',
    'publication_v2/stage32/tests',
    'publication_v2/stage33/tests',
    'publication_v2/stage4/tests',
    'publication_v2/stage5/tests',
)
# Dashboard page tests that run on committed files only (no private data).
DASHBOARD_TESTS = ('tests.test_controller_lab_page', 'tests.test_real_data_page')


def _serve(args):
    import uvicorn

    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {'console': {'class': 'logging.StreamHandler', 'stream': 'ext://sys.stdout'}},
        'loggers': {'windgrid': {'handlers': ['console'], 'level': 'INFO'}},
    }
    uvicorn.run('windgrid.api:app', host=args.host, port=args.port, log_config=None if args.quiet else logging_config)


def _dashboard(args):
    app = ROOT / 'app' / 'dashboard.py'
    if not app.exists():
        sys.exit('The dashboard needs a source checkout of the repository (app/dashboard.py not found).')
    sys.exit(
        subprocess.call(
            [
                sys.executable,
                '-m',
                'streamlit',
                'run',
                str(app),
                '--server.port',
                str(args.port),
                '--server.address',
                args.host,
                '--browser.gatherUsageStats',
                'false',
            ]
        )
    )


def _simulate(args):
    from . import simulate

    table = simulate.compare(forecast=args.forecast, limit=args.episodes)
    print(
        f'Closed-loop replay on the bundled Penmanshiel sample ({simulate.FORECAST_LABELS[args.forecast]}), '
        f'{int(table["episodes"].iloc[0])} episodes of 8 hours\n'
    )
    print(table.drop(columns='episodes').round(2).sort_values('change_vs_uncontrolled_pct').to_string())


def _dispatch(args):
    from fastapi.testclient import TestClient

    from .api import app

    client = TestClient(app)
    body = (
        json.loads(Path(args.request).read_text(encoding='utf-8'))
        if args.request
        else client.get('/v1/sample', params={'controller': args.controller}).json()
    )
    response = client.post('/v1/dispatch', json=body)
    print(json.dumps(response.json(), indent=2))
    sys.exit(0 if response.status_code == 200 else 1)


def _check(args):
    steps = [[sys.executable, '-m', 'ruff', 'check', '.'], [sys.executable, '-m', 'ruff', 'format', '--check', '.']]
    steps += [[sys.executable, '-B', '-m', 'unittest', 'discover', '-s', suite] for suite in SUITES]
    steps += [[sys.executable, '-B', '-m', 'unittest', *DASHBOARD_TESTS]]
    failed = []
    for step in steps:
        print('$', ' '.join(step[1:]), flush=True)
        if subprocess.call(step, cwd=ROOT) != 0:
            failed.append(' '.join(step[1:]))
    print('\nAll checks passed.' if not failed else '\nFAILED:\n  ' + '\n  '.join(failed))
    sys.exit(1 if failed else 0)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='windgrid', description='Forecast-aware battery dispatch for wind ramps.')
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('serve', help='start the dispatch API')
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--port', type=int, default=8000)
    p.add_argument('--quiet', action='store_true', help='use uvicorn default logging')
    p.set_defaults(run=_serve)
    p = commands.add_parser('dashboard', help='start the Streamlit dashboard')
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--port', type=int, default=8501)
    p.set_defaults(run=_dashboard)
    p = commands.add_parser('simulate', help='compare controllers on the bundled sample')
    p.add_argument('--forecast', default='lightgbm_spatial', choices=('lightgbm_spatial', 'persistence'))
    p.add_argument('--episodes', type=int, default=None, help='limit the number of episodes')
    p.set_defaults(run=_simulate)
    p = commands.add_parser('dispatch', help='one decision from a JSON request (default: bundled sample)')
    p.add_argument('request', nargs='?', help='path to a DispatchRequest JSON file')
    p.add_argument('--controller', default='graded_mpc')
    p.set_defaults(run=_dispatch)
    p = commands.add_parser('check', help='run lint and the data-free test suites (same as CI)')
    p.set_defaults(run=_check)
    args = parser.parse_args(argv)
    args.run(args)


if __name__ == '__main__':
    main()
