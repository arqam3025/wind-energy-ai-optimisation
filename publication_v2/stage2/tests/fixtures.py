"""Fully invented, explicitly synthetic time-ledger for software integration only."""
import csv
from datetime import datetime,timedelta,timezone
import json
import math
from pathlib import Path

from publication_v2.integrity import digest
from publication_v2.protocol import FEATURE_SUPPORT,HORIZONS
from publication_v2.stage2.data import REQUIRED_PROVENANCE


def dataset(root: Path) -> Path:
    base=datetime(2030,1,1,tzinfo=timezone.utc)
    measurements={base+timedelta(minutes=10*i):{'power_kw':(-3. if i%37==0 else 500+90*math.sin(i/7)+(250 if i%19==0 else 0)),
        'wind_speed':8+math.cos(i/13),'wind_direction':float((17*i)%360)} for i in range(165)}
    source=root/'fixture_measurements.csv'
    with source.open('x',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['event_time','available_at','source_observation_id','power_kw','wind_speed','wind_direction']);writer.writeheader()
        writer.writerows({'event_time':t.isoformat(),'available_at':t.isoformat(),'source_observation_id':f'fixture-{i}',**row} for i,(t,row) in enumerate(measurements.items()))
    upstream=root/'fixture_upstream.csv';upstream.write_bytes(source.read_bytes())
    evidence=root/'synthetic_attestation.txt';evidence.write_text('SYNTHETIC TEST DATA. No measurements, license or operational availability is claimed. Fictional zero receipt latency.',encoding='utf-8')
    proof={'path':evidence.name,'sha256':digest(evidence)}
    provenance={name:{'status':'SYNTHETIC_FIXTURE','value':'SYNTHETIC_TEST_ONLY','evidence':proof} for name in REQUIRED_PROVENANCE}
    provenance['timezone']['value']='UTC'
    provenance['units']['value']={'power':'kW','wind_speed':'m/s','wind_direction':'degrees'}
    partitions={}
    for role,indices in [('train',range(6,86)),('calibration',range(93,133)),('development',range(139,151))]:
        records=[]
        for index in indices:
            origin=base+timedelta(minutes=10*index)
            features=[]
            for name,offsets in FEATURE_SUPPORT.items():
                support=[origin-timedelta(minutes=k) for k in offsets]
                if name in ('power_kw','wind_speed','wind_direction'):value=measurements[origin][name]
                elif '_lag_' in name:value=measurements[support[0]]['power_kw' if name.startswith('power') else 'wind_speed']
                elif name.endswith('_change_10min'):
                    key='power_kw' if name.startswith('power') else 'wind_speed'
                    value=measurements[origin][key]-measurements[origin-timedelta(minutes=10)][key]
                else:value=sum(measurements[origin-timedelta(minutes=k)]['power_kw'] for k in (0,10,20,30))/4
                features.append({'name':name,'value':value,'source_times':[t.isoformat() for t in support],
                    'available_at':origin.isoformat(),'source_available_ats':[t.isoformat() for t in support]})
            targets=[]
            for h in HORIZONS:
                target=origin+timedelta(minutes=h);previous=target-timedelta(minutes=10)
                targets.append({'horizon_minutes':h,'target_time':target.isoformat(),'value_kw':max(0,measurements[target]['power_kw']),
                    'available_at':target.isoformat(),'residual_available_at':(target+timedelta(seconds=1)).isoformat(),
                    'previous_target_time':previous.isoformat(),'previous_value_kw':max(0,measurements[previous]['power_kw']),
                    'previous_available_at':previous.isoformat()})
            records.append({'origin_time':origin.isoformat(),'issued_at':origin.isoformat(),'decision_time':origin.isoformat(),
                            'features':features,'targets':targets})
        partitions[role]=records
    doc={'schema_version':'publication_v2.stage2.dataset.v1','scope':'DEVELOPMENT_ONLY','dataset_kind':'SYNTHETIC_FIXTURE',
         'contains_confirmation_data':False,'provenance':provenance,'grid_anchor':base.isoformat(),
         'fit_time':(base+timedelta(minutes=920)).isoformat(),'target_transform':'max(0,raw_power_kw)',
         'source_artifact':{'schema_version':'publication_v2.stage2.measurements.csv.v1','path':source.name,'sha256':digest(source),
                            'upstream':{'path':upstream.name,'sha256':digest(upstream)}},'partitions':partitions}
    windows={role:{'start':rows[0]['origin_time'],'end':rows[-1]['origin_time']} for role,rows in partitions.items()}
    authorization={role:{'start':base.isoformat(),'end':(base+timedelta(minutes=1640)).isoformat()} for role in partitions}
    policy={'schema_version':'publication_v2.stage21.cohort-policy.v1','policy_id':'SYNTHETIC_TEST_ONLY',
        'declared_at':(base-timedelta(days=1)).isoformat(),'missing_cells':'reject','duplicates':'reject','imputation':'forbidden',
        'gaps':'reject','declared_missing_measurements':[],'role_origin_windows':windows,'excluded_origins':[],
        'authorized_periods':authorization,'measurement_window':{'start':base.isoformat(),'end':(base+timedelta(minutes=1640)).isoformat()}}
    policy_path=root/'fixture_cohort_policy.json';policy_path.write_text(json.dumps(policy),encoding='utf-8')
    doc['cohort_policy']={'path':policy_path.name,'sha256':digest(policy_path)}
    refresh_lineage(root,doc)
    path=root/'fixture_dataset.json';path.write_text(json.dumps(doc,indent=2),encoding='utf-8');return path


def refresh_lineage(root,doc):
    """Fixture-only content-addressed manifest; never represents real review."""
    from publication_v2.stage2.lineage import FIELDS,TRANSFORM_ID,IMPLEMENTATION,_read_measurements,semantic_sha256
    source=doc['source_artifact']
    source['sha256']=digest(root/source['path']);source['upstream']['sha256']=digest(root/source['upstream']['path'])
    manifest={'schema_version':'publication_v2.stage21.lineage.v1','scope':'DEVELOPMENT_ONLY','confirmatory_status':'BLOCKED_CONFIRMATORY_TEST',
        'source_identity':{'provider':'SYNTHETIC_TEST_ONLY','dataset':'invented-fixture','release':'fixture-v1','observation_namespace':'synthetic-fixture'},
        'canonical':source,'upstream':source['upstream'],
        'transformation':{'id':TRANSFORM_ID,'implementation_sha256':digest(IMPLEMENTATION),'column_map':{k:k for k in FIELDS}},
        'canonical_semantic_sha256':semantic_sha256(_read_measurements(root/source['path'],{k:k for k in FIELDS})),
        'independent_review_id':'SYNTHETIC_TEST_ONLY'}
    path=root/'fixture_lineage.json';path.write_text(json.dumps(manifest),encoding='utf-8')
    doc['lineage_manifest']={'path':path.name,'sha256':digest(path)}
