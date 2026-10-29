"""Run predeclared paired block uncertainty; never overwrite original statistics."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from windresearch.dependent_statistics import run_original_statistics
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'results/research_grade_v1_20261029/statistics_original')
    parser.add_argument('--figures',type=Path,default=ROOT/'figures/research_grade_v1_20261029/statistics_original')
    args=parser.parse_args()
    print(json.dumps(run_original_statistics(ROOT,args.output,args.figures),indent=2))
