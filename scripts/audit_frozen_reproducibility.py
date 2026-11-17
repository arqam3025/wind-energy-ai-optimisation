"""Verify repeated solver outputs and reconstruct frozen development accounting."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from heldout_support import ROOT
from prepare_frozen_heldout import verify

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--main-run',default='final_20261029')
    parser.add_argument('--replay-run',default='replay_20261029')
    parser.add_argument('--output',default='reproducibility_audit_v1.json')
    args=parser.parse_args()
    manifest=verify()
    report={'freeze':'pass','replay':{},'development_reconstruction':{}}
    for kind in ['fixed','adaptive_one_sided']:
        name=f'{kind}/adaptive_charging_mpc_block_1_weight_0p500.csv'
        first=pd.read_csv(ROOT/'results/frozen_heldout'/args.main_run/name)
        second=pd.read_csv(ROOT/'results/frozen_heldout'/args.replay_run/name)
        assert first.columns.equals(second.columns)
        for column in first.select_dtypes(exclude='number'):
            assert first[column].equals(second[column]),column
        numeric=first.select_dtypes('number').columns
        difference=np.abs(first[numeric].to_numpy()-second[numeric].to_numpy())
        assert difference.max()<=1e-5
        report['replay'][kind]={'block':1,'max_absolute_numeric_difference':float(difference.max()),'columns':len(first.columns),'rows':len(first),'status':'pass'}
    for kind,entries in manifest['development_result_files'].items():
        totals={key:0. for key in ['throughput_kwh','conversion_losses_kwh','actual_export_mwh','terminal_adjusted_export_mwh']}
        for entry in entries.values():
            d=pd.read_csv(ROOT/entry['path'])
            charge=d.charge_kw.sum()/6
            discharge=d.discharge_kw.sum()/6
            export=d.grid_export_kw.sum()/6
            delta=d.soc_percent.iloc[-1]*20-1000
            totals['throughput_kwh']+=charge+discharge
            totals['conversion_losses_kwh']+=.05*charge+(1/.95-1)*discharge
            totals['actual_export_mwh']+=export/1000
            totals['terminal_adjusted_export_mwh']+=(export+(.95*delta if delta>=0 else delta/.95))/1000
        for key,value in totals.items():
            assert abs(value-manifest['development_results'][kind][key])<.001,(kind,key)
        report['development_reconstruction'][kind]=totals
    path=ROOT/'results/frozen_heldout'/args.main_run/args.output
    with path.open('x') as handle:json.dump(report,handle,indent=2)
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
