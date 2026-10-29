"""Analyse completed studies; outputs must be new directories."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from windresearch.result_analysis import run_analysis

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--studies', type=Path, default=ROOT / 'results/research_grade_v1_20261029')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--figures', type=Path, required=True)
    args = parser.parse_args()
    print(run_analysis(ROOT, args.studies, args.output, args.figures))
