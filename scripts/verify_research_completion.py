"""Verify the completed package without editing research artifacts."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/'audits/research_completion_20261029'
EXPECTED='b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a'
os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'wind-final-verification-mpl'))
os.environ['PYTHONDONTWRITEBYTECODE']='1'

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def require(condition,message):
    if not condition:raise RuntimeError(message)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--record',help='New JSON filename in the completion audit directory; exclusive create')
    parser.add_argument('--check-http',action='store_true')
    args=parser.parse_args()
    require(__debug__,'Run without -O: legacy research checks require assertions')
    immutable=json.loads((AUDIT/'immutable_baseline.json').read_text())
    changed=[name for name,h in immutable.items() if digest(ROOT/name)!=h]
    require(not changed,f'Immutable artifact changes: {changed}')
    freeze=ROOT/'results/development_controller_freeze_manifest.json'
    require(digest(freeze)==EXPECTED,'Freeze mismatch')
    m=json.loads(freeze.read_text())
    refs=list(m['source_files'].values())+[v for group in m['development_result_files'].values() for v in group.values()]
    require(all(digest(ROOT/v['path'])==v['sha256'] for v in refs),'Frozen reference mismatch')
    from analyse_frozen_heldout import validate_and_measure
    schedule=pd.read_csv(ROOT/'results/evaluation_schedule.csv')
    valid=schedule.loc[schedule.evaluation_role.eq('evaluation'),'block_id'].astype(int).tolist()
    require(len(valid)==49 and 6 not in valid,'Unexpected scoring set')
    rows=[]
    run=ROOT/'results/frozen_heldout/final_20261029'
    for block_id in valid:
        source=pd.read_csv(ROOT/f'data/processed/evaluation_block_{block_id}.csv',parse_dates=['timestamp'])
        for kind in ['fixed','adaptive_one_sided']:
            trace=pd.read_csv(run/kind/f'adaptive_charging_mpc_block_{block_id}_weight_0p500.csv')
            rows.append(dict(controller=kind,**validate_and_measure(trace,source,kind)))
    aggregate=pd.DataFrame(rows).groupby('controller').sum(numeric_only=True)
    f=aggregate.loc['fixed'];a=aggregate.loc['adaptive_one_sided']
    require(int(f.ramp_violations)==1502 and int(a.ramp_violations)==1486,'Violation total mismatch')
    require(abs(100*(1-a.throughput_kwh/f.throughput_kwh)-27.864427505619094)<1e-9,'Throughput change mismatch')
    require(abs(100*(1-a.ramp_exceedance_kw/f.ramp_exceedance_kw)-.7725605651369261)<1e-9,'Exceedance change mismatch')
    provenance=json.loads((ROOT/'docs/completion_tables/diagnostic_provenance.json').read_text())
    require(all(digest(ROOT/name)==h for name,h in provenance['source_sha256'].items()),'Diagnostic input changed')
    required=['docs/grid_ramp_diagnostic.md','docs/literature_review.md','docs/literature_verified.json','docs/paper_submission_draft.md','docs/mathematical_formulation.md','docs/unresolved_scientific_issues.md','app/dashboard.py','app/research_data.py','requirements-research.txt']
    require(all((ROOT/name).is_file() for name in required),'Missing deliverable')
    literature=json.loads((ROOT/'docs/literature_verified.json').read_text(encoding='utf-8'))['references']
    require(len(literature)==15 and len({r['id'] for r in literature})==15,'Reference register incomplete')
    manuscript=(ROOT/'docs/paper_submission_draft.md').read_text(encoding='utf-8')
    require(not re.search(r'@@[A-Z_]+@@',manuscript),'Unfilled manuscript token')
    broken=[]
    documents=[ROOT/'README.md',*[ROOT/f'docs/{n}' for n in ['paper_submission_draft.md','grid_ramp_diagnostic.md','literature_review.md','mathematical_formulation.md','methodology.md','reproducibility.md','unresolved_scientific_issues.md']]]
    for document in documents:
        for target in re.findall(r'\]\(([^)]+)\)',document.read_text(encoding='utf-8')):
            if not target.startswith(('http:','https:','#')):
                local=target.split('#')[0]
                if local and not (document.parent/local).exists():broken.append([str(document.relative_to(ROOT)),target])
    require(not broken,f'Broken local links: {broken}')
    test=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-v'],cwd=ROOT,capture_output=True,text=True)
    require(test.returncode==0,test.stdout+'\n'+test.stderr)
    test_text=test.stdout+'\n'+test.stderr
    count=re.search(r'Ran (\d+) tests',test_text)
    gitcheck=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,text=True)
    require(gitcheck.returncode==0,gitcheck.stdout+gitcheck.stderr)
    candidates=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
    patterns={'AWS access ID':r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b','GitHub token':r'\bgh[pousr]_[A-Za-z0-9]{30,}\b','private key':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----','OpenAI token':r'\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b'}
    secret_matches=[]
    for name in candidates:
        path=ROOT/name
        if path.is_file() and path.suffix.lower() in ['.py','.json','.txt','.md','.yaml','.yml','.env','.toml']:
            content=path.read_text(encoding='utf-8',errors='replace')
            for label,pattern in patterns.items():
                if re.search(pattern,content):secret_matches.append({'file':name,'pattern':label})
    require(not secret_matches,'Possible credential patterns; review filenames only: '+str(secret_matches))
    http={}
    if args.check_http:
        for route in ['/', '/_stcore/health']:
            with urllib.request.urlopen('http://127.0.0.1:8501'+route,timeout=10) as response:
                http[route]=response.status
                require(response.status==200,'HTTP smoke failure')
    # The documented four authorised files were archived before any changes.
    older=json.loads((ROOT/'audits/publication_readiness_20261029/protected_sha256_before_after.json').read_text())
    archive={}
    for name in ['README.md','.gitignore','docs/methodology.md','docs/reproducibility.md']:
        expected=next(h for p,h in older.items() if p.replace('\\','/')==name)
        saved=AUDIT/'prior_documentation'/Path(name).name
        require(digest(saved)==expected,'Documentation archive mismatch')
        archive[name]={'archived_sha256':expected,'current_sha256':digest(ROOT/name)}
    require(all(digest(ROOT/name)==h for name,h in immutable.items()),'Artifact changed during checks')
    report={'status':'pass','immutable_files_unchanged':len(immutable),'freeze_sha256':EXPECTED,'frozen_references':len(refs),'physical_controller_blocks':len(rows),'tests_passed':int(count.group(1)) if count else None,
        'diagnostic_sources_verified':len(provenance['source_sha256']),'references':len(literature),'headline_throughput_reduction_percent':float(100*(1-a.throughput_kwh/f.throughput_kwh)),
        'headline_exceedance_reduction_percent':float(100*(1-a.ramp_exceedance_kw/f.ramp_exceedance_kw)),'fewer_violations':16,'http_status':http,'broken_local_links':broken,'secret_pattern_matches':secret_matches,
        'authorised_documentation_changes':archive,'limits':['Retrospective, not untouched confirmatory evaluation','No clean-machine dependency installation tested','No browser visual automation; Streamlit AppTest and HTTP smoke only','Full solver replay not repeated; prior independent first-block replay retained','No external publication or rights clearance'],
        'test_output':test_text}
    if args.record:
        require(Path(args.record).name==args.record and args.record.endswith('.json'),'Record must be a new JSON filename')
        with (AUDIT/args.record).open('x',encoding='utf-8') as handle:json.dump(report,handle,indent=2)
    print(json.dumps({k:v for k,v in report.items() if k!='test_output'},indent=2))

if __name__=='__main__':main()
