"""Persist explicit new chronology diagnostics and a non-applied purge projection."""
from pathlib import Path
import hashlib,json,sys
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from windresearch.protocol import (target_purged_calibration,role_target_overlap,
    require_new_output_directory,require_cohort_interpretation,ProtocolError)

if __name__=='__main__':
    output=require_new_output_directory(ROOT/'results/research_grade_v1_20261029/protocol_corrections')
    calibration_path=ROOT/'results/multistep_calibration_split.csv'
    calibration=pd.read_csv(calibration_path,parse_dates=['timestamp'])
    development_path=ROOT/'data/processed/controller_development_blocks/development_block_1.csv'
    development=pd.read_csv(development_path,parse_dates=['timestamp'])
    retained,excluded=target_purged_calibration(calibration,development.timestamp.iloc[0])
    retained.to_csv(output/'calibration_target_purged_projection.csv',index=False,mode='x')
    excluded.to_csv(output/'excluded_calibration_origins.csv',index=False,mode='x')
    schedule_path=ROOT/'results/evaluation_schedule.csv'
    schedule=pd.read_csv(schedule_path)
    blocks={int(b):pd.read_csv(ROOT/f'data/processed/evaluation_block_{b}.csv',parse_dates=['timestamp']) for b in schedule.block_id}
    overlap=role_target_overlap(schedule,blocks)
    overlap.to_csv(output/'legacy_role_target_overlap.csv',index=False,mode='x')
    try:
        require_cohort_interpretation(overlap,retrospective=False)
    except ProtocolError:
        clean_claim_rejected=True
    else:clean_claim_rejected=False
    metadata={'scope':'Protocol correction demonstration only; original quantiles/models/inputs/49 scores unchanged',
        'new_projection_used_for_frozen_or_new_benchmark':False,
        'retained_origins':len(retained),'excluded_origins':len(excluded),
        'first_development_decision':str(development.timestamp.iloc[0]),
        'latest_retained_60min_target':str(retained.timestamp.max()+pd.Timedelta(minutes=60)),
        'legacy_overlap_pairs':len(overlap),'legacy_overlap_h1_targets':int(overlap.horizon_minutes.eq(10).sum()),
        'clean_holdout_claim_rejected':clean_claim_rejected,
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [calibration_path,development_path,schedule_path]}}
    with (output/'protocol_correction_record.json').open('x') as handle:json.dump(metadata,handle,indent=2)
    print(json.dumps(metadata,indent=2))
