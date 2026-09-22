"""Whitelisted public runtime metadata, never raw claims or environment dumps."""
from __future__ import annotations
import os,re,hashlib,subprocess
from pathlib import Path
from datetime import datetime
from .timing import as_local
VERSION='7.0.0'

def code_fingerprint(root:Path|None=None) -> str:
    root=root or Path(__file__).resolve().parents[1]
    digest=hashlib.sha256()
    paths=[]
    for sub,pattern in [('contest_alert','*.py'),('web','*'),('.github/workflows','*.yml')]:
        paths.extend(p for p in (root/sub).glob(pattern) if p.is_file())
    for path in sorted(paths):
        digest.update(str(path.relative_to(root)).encode());digest.update(path.read_bytes())
    return digest.hexdigest()[:12]

def execution_identity()->dict:
    repo=os.getenv('GITHUB_REPOSITORY','')
    run=os.getenv('GITHUB_RUN_ID','')
    sha=os.getenv('GITHUB_SHA','')
    try:
        resolved=subprocess.run(['git','rev-parse','HEAD'],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,timeout=2)
        if resolved.returncode==0:sha=resolved.stdout.strip()
    except (OSError,subprocess.TimeoutExpired):pass
    result={'version':VERSION,'fingerprint':code_fingerprint(),'commit':sha if re.fullmatch(r'[0-9a-f]{7,64}',sha) else None}
    if re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo) and run.isdigit():
        result['run_url']=f'https://github.com/{repo}/actions/runs/{run}'
        result['run_id']=run
    return result

def finish_collection(state:dict,started:datetime,finished:datetime)->None:
    ops=state.setdefault('operations',{})
    enabled=[s for s in state.get('sources',{}).values() if s.get('status')!='disabled']
    good=sum(s.get('status')=='ok' for s in enabled)
    usable=sum(s.get('status') in ('ok','partial') for s in enabled)
    status='complete' if enabled and good==len(enabled) else 'partial' if usable else 'failed'
    ops['collection']={**execution_identity(),'status':status,'attempted_at':as_local(started).isoformat(),
        'finished_at':as_local(finished).isoformat(),'enabled_sources':len(enabled),'ok_sources':good}
    if usable:ops['last_usable_at']=as_local(finished).isoformat()
    if status=='complete':ops['last_complete_at']=as_local(finished).isoformat()

def runtime_metadata(state:dict,now:datetime)->dict:
    ops=state.get('operations',{})
    collection={k:v for k,v in ops.get('collection',{}).items() if k in ('version','fingerprint','commit','run_url','run_id','status','attempted_at','finished_at','enabled_sources','ok_sources')}
    # Old snapshots have only the attempt timestamp, not a proven finish.
    collection.setdefault('attempted_at',state.get('updated_at'))
    collection.setdefault('status','legacy' if state.get('updated_at') else 'not_started')
    days=sorted(d for d in state.get('claims',{}) if re.fullmatch(r'\d{4}-\d{2}-\d{2}',str(d)))
    notification={'status':'not_attempted'}
    if days:
        claim=state['claims'][days[-1]]
        status=claim.get('status','unknown')
        if status not in ('reserved','accepted','scheduled','failed'):status='unknown'
        notification={'status':status,'day':days[-1]}
        for key in ('at','accepted_at','failed_at'):
            value=claim.get(key)
            if isinstance(value,str):
                try:
                    parsed=datetime.fromisoformat(value)
                    if parsed.tzinfo:notification[key]=parsed.isoformat()
                except ValueError:pass
    from .details import PARSER_VERSION
    return {'version':VERSION,'parser_version':PARSER_VERSION,'build':execution_identity(),
        'generated_at':as_local(now).isoformat(),'collection':collection,
        'last_usable_at':ops.get('last_usable_at'),'last_complete_at':ops.get('last_complete_at'),
        'notification':notification,'notification_note':'ntfy 수락은 휴대폰 표시 성공이 아닙니다.'}
