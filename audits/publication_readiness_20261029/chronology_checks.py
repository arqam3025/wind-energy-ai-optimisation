"""Document development-target overlap and segment heterogeneity without edits."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
s=pd.read_csv(ROOT/'results/evaluation_schedule.csv')
development=pd.read_csv(ROOT/'data/processed/evaluation_block_6.csv',parse_dates=['timestamp'])
targets=set(t for h in range(1,7) for t in development.timestamp+pd.Timedelta(minutes=10*h))
overlap=[]
for b in s.loc[s.evaluation_role.eq('evaluation'),'block_id']:
    d=pd.read_csv(ROOT/f'data/processed/evaluation_block_{b}.csv',parse_dates=['timestamp'])
    pairs=[(t,h) for h in range(1,7) for t in d.timestamp+pd.Timedelta(minutes=10*h) if t in targets]
    if pairs:
        overlap.append({'block':int(b),'forecast_target_pairs':len(pairs),'unique_targets':sorted(set(str(t) for t,h in pairs)),
                        'scored_h1_targets':[str(t) for t,h in pairs if h==1]})
paired=pd.read_csv(ROOT/'results/frozen_heldout/final_20261029/analysis_v2/paired_differences.csv').merge(s,on='block_id')
segments=paired.groupby('segment_id')[['throughput_kwh','ramp_exceedance_kw','ramp_violations']].sum()
rng=np.random.default_rng(20261029)
draws=rng.integers(0,len(paired),size=(10000,len(paired)))
boot={key:np.quantile(paired[key].to_numpy()[draws].mean(axis=1),[.025,.975]).tolist() for key in ['throughput_kwh','conversion_losses_kwh','ramp_exceedance_kw','ramp_violations','terminal_adjusted_export_kwh']}
report={'block6_target_overlap':overlap,'segment_paired_sums':segments.to_dict('index'),
        'recomputed_iid_day_bootstrap_bounds':boot,'bootstrap_warning':'IID day resampling; not dependence-corrected inference'}
with (OUT/'chronology_and_statistics.json').open('x') as handle:json.dump(report,handle,indent=2)
print(json.dumps(report,indent=2))
