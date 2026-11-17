"""Stage 2 development command line. Synthetic mode exists only in test APIs."""
import argparse
import json
from pathlib import Path
from .workflow import preflight,run_development,verify_run


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('preflight');p.add_argument('--run-id',required=True)
    p=sub.add_parser('run');p.add_argument('--run-id',required=True);p.add_argument('--dataset',type=Path,required=True)
    p=sub.add_parser('verify');p.add_argument('--run',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='preflight':
            directory,manifest=preflight(args.run_id)
        elif args.command=='run':
            directory,manifest=run_development(args.dataset,args.run_id)
        else:
            directory=args.run;manifest=verify_run(directory)
        print(json.dumps({'run':str(directory),'status':manifest['status'],
                          'confirmatory_status':manifest['confirmatory_status'],
                          'research_metrics_available':manifest['research_metrics_available']}))
        return 2 if manifest['status']=='BLOCKED_DEVELOPMENT_EXPERIMENT' else 0
    except Exception as error:
        print(json.dumps({'status':'FAILED_CLOSED','error_type':type(error).__name__,'error':str(error)}))
        return 1


if __name__=='__main__': raise SystemExit(main())
