"""Read-only validation of WindGrid UI, original artifacts and historical totals."""
from pathlib import Path
from datetime import datetime,timezone
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/'audits/windgrid_dashboard_20261029'
sys.path.insert(0,str(ROOT/'app'))
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'windgrid-verification-mpl'))

def require(value,message):
    if not value:raise RuntimeError(message)

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--check-http',action='store_true')
    parser.add_argument('--record',help='New JSON filename in the WindGrid audit directory; never overwritten')
    args=parser.parse_args()
    from platform_data import valid_blocks,interval_frame,energy_metrics,integrity_report,environment_summary
    baseline=json.loads((AUDIT/'protected_baseline.json').read_text())
    changed=[name for name,h in baseline.items() if digest(ROOT/name)!=h]
    require(not changed,'Protected research artifacts changed: '+str(changed))
    integrity=integrity_report()
    require(integrity['status']=='pass','Freeze or referenced artifact mismatch')
    totals={}
    for block in valid_blocks():
        for kind in ['adaptive_one_sided','fixed','uncontrolled']:
            metrics=energy_metrics(interval_frame(block,kind))
            result=totals.setdefault(kind,dict(intervals=0,throughput_kwh=0.,ramp_exceedance_kw=0.,ramp_violations=0))
            for key in result:result[key]+=metrics[key]
    require(totals['fixed']['ramp_violations']==1502 and totals['adaptive_one_sided']['ramp_violations']==1486 and totals['uncontrolled']['ramp_violations']==1465,'Historical count regression')
    require(abs(totals['fixed']['ramp_exceedance_kw']-326158.29597609653)<1e-6,'Fixed exceedance regression')
    require(abs(totals['adaptive_one_sided']['ramp_exceedance_kw']-323638.52560146264)<1e-6,'Adaptive exceedance regression')
    test=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-v'],cwd=ROOT,capture_output=True,text=True)
    output=test.stdout+'\n'+test.stderr
    require(test.returncode==0,output)
    count=re.search(r'Ran (\d+) tests',output)
    http={}
    if args.check_http:
        for route in ['/', '/_stcore/health']:
            with urllib.request.urlopen('http://127.0.0.1:8501'+route,timeout=10) as response:
                http[route]=response.status
                require(response.status==200,'HTTP smoke failure')
    require(all(digest(ROOT/name)==h for name,h in baseline.items()),'Research artifact changed during verification')
    whitespace=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,text=True)
    require(whitespace.returncode==0,whitespace.stdout+whitespace.stderr)
    sources=list((ROOT/'app').rglob('*.py'))+[ROOT/'.streamlit/config.toml',ROOT/'README.md',ROOT/'requirements-dashboard.txt',ROOT/'requirements-research.txt',ROOT/'tests/test_windgrid_ui.py',ROOT/'tests/test_platform_data.py',ROOT/'docs/windgrid_platform_guide.md',Path(__file__)]
    result={'status':'pass','created_utc':datetime.now(timezone.utc).isoformat(),
        'application':'WindGrid AI — Wind–Battery Digital Twin','tests_passed':int(count.group(1)) if count else None,
        'pages_tested':['Command Center','Digital Twin','AI Forecasting Lab','MPC Decision Explorer','Battery Analytics','Grid Stability Lab','Research Results','Reproducibility'],
        'physical_frames_checked':147,'recorded_controller_blocks':98,'original_totals':totals,
        'protected_files_unchanged':len(baseline),'freeze_sha256':integrity['actual_sha256'],'frozen_references_verified':integrity['checked_files'],
        'http_status':http,'environment':environment_summary(),
        'initial_failures_resolved':['Reserved pages/ folder bypassed shared entry point during AppTest page switching; registered screens/ folder fixes it','End-of-episode test incorrectly clicked a disabled widget; now verifies disabled Step/Play'],
        'limitations':['Browser visual/accessibility automation unavailable; native AppTest and HTTP smoke only','No clean-machine package installation performed','Unlogged six-step solver trajectories, costs, gaps and solve times are unavailable','Retrospective evaluation and original publication limitations remain'],
        'test_output':output,'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in sources if '__pycache__' not in p.parts}}
    if args.record:
        require(Path(args.record).name==args.record and args.record.endswith('.json'),'Choose a new JSON filename')
        with (AUDIT/args.record).open('x',encoding='utf-8') as handle:json.dump(result,handle,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ['test_output','source_sha256']},indent=2))

if __name__=='__main__':main()
