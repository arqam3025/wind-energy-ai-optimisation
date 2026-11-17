"""Fresh first-block replay; redirect output only, preserve all research files."""
from pathlib import Path
import json
import subprocess
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
report={}
for kind in ['fixed','adaptive_one_sided']:
    # No solver/parameter/data patch: replace only the output-directory helper.
    code=("import sys,runpy; from pathlib import Path; sys.path.insert(0,'scripts'); "
          "import heldout_support; "
          "heldout_support.output_directory=lambda kind:Path('audits/publication_readiness_20261029/solver_replay')/kind; "
          f"sys.argv=['scripts/frozen_{kind}_heldout.py','1']; "
          f"runpy.run_path('scripts/frozen_{kind}_heldout.py',run_name='__main__')")
    with (OUT/f'replay_{kind}.log').open('x',encoding='utf-8') as log:
        subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    filename=f'adaptive_charging_mpc_block_1_weight_0p500.csv'
    replay=pd.read_csv(OUT/'solver_replay'/kind/filename)
    original=pd.read_csv(ROOT/'results/frozen_heldout/final_20261029'/kind/filename)
    assert replay.columns.equals(original.columns)
    columns=original.select_dtypes('number').columns
    diff=float(np.abs(original[columns].to_numpy()-replay[columns].to_numpy()).max())
    assert diff<=1e-5
    for col in original.select_dtypes(exclude='number'):
        assert original[col].equals(replay[col])
    report[kind]={'rows':len(original),'max_numeric_difference':diff,'non_numeric_columns_match':True}
with (OUT/'fresh_solver_replay.json').open('x') as handle:json.dump(report,handle,indent=2)
print(json.dumps(report,indent=2))
