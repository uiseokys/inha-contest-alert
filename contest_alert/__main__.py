"""CLI used by GitHub Actions. All writes are inside the chosen project root."""
from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
from datetime import datetime
from .core import empty_state,canonical
from .collect import collect_all
from .notify import KST,validate_topic,reserve,publish
from .render import build


def read_json(path:Path,default=None):
    if not path.exists():
        if default is not None:return default
        raise ValueError(f'필수 파일이 없습니다: {path.name}')
    try:return json.loads(path.read_text(encoding='utf-8'))
    except (ValueError,OSError):raise ValueError(f'{path.name}을 읽을 수 없습니다. 중복 방지를 위해 기존 상태를 초기화하지 않고 중단합니다.') from None

def write_json(path:Path,data:dict):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(path)

def urls()->tuple[str,str]:
    repo=os.getenv('GITHUB_REPOSITORY','')
    repo_url='https://github.com/'+repo if repo else ''
    # Pages URL may be changed to a custom domain; set public PAGE_URL variable.
    page=os.getenv('PAGE_URL','').strip()
    if not page and os.getenv('ENABLE_PAGES','').lower()=='false':page=repo_url
    if not page and '/' in repo:
        owner,name=repo.split('/',1)
        page=f'https://{owner.lower()}.github.io/'+('' if name.lower()==owner.lower()+'.github.io' else name+'/')
    return canonical(repo_url),canonical(page)

def main()->int:
    p=argparse.ArgumentParser(description='공모전 목록과 정오 ntfy 브리핑')
    p.add_argument('command',choices=['collect','render','prepare','send'])
    p.add_argument('--root',type=Path,default=Path.cwd())
    p.add_argument('--mode',choices=['scheduled','manual'],default='manual')
    args=p.parse_args();root=args.root.resolve();now=datetime.now(KST)
    config=read_json(root/'config.json');state_path=root/'data/state.json'
    state=read_json(state_path,empty_state());repo_url,page_url=urls()
    runtime=root/'.runtime';runtime.mkdir(exist_ok=True)
    if args.command=='collect':
        state=collect_all(config,state,now);write_json(state_path,state)
        build(root,state,now,repo_url,page_url)
        for src in state['sources'].values():print(f"{src['name']}: {src['status']} ({src['retained']}건)")
        return 0
    if args.command=='render':build(root,state,now,repo_url,page_url);return 0
    if args.command=='prepare':
        validate_topic(os.getenv('NTFY_TOPIC',''))
        if not page_url:raise ValueError('알림에서 열 PAGE_URL 또는 GITHUB_REPOSITORY 설정이 필요합니다.')
        draft=reserve(state,now,page_url,args.mode,os.getenv('GITHUB_RUN_ID','local'))
        output=os.getenv('GITHUB_OUTPUT')
        if output:
            with open(output,'a',encoding='utf-8') as f:f.write('send='+('true' if draft else 'false')+'\n')
        if draft:
            write_json(runtime/'notification.json',draft);write_json(state_path,state)
            print('오늘 전송 시도 선점 기록을 생성했습니다. GitHub에 먼저 저장한 뒤 send를 실행해야 합니다.')
        else:print('오늘 전송 시도 기록이 있어 중복 발송을 생략합니다.')
        return 0
    if args.command=='send':
        draft=read_json(runtime/'notification.json')
        claim=state['claims'].get(draft['day'],{})
        if claim.get('status')!='reserved' or claim.get('run_id')!=draft['run_id']:
            raise ValueError('현재 실행의 전송 선점 기록이 일치하지 않습니다. 전송하지 않습니다.')
        if draft['day']!=now.date().isoformat():raise ValueError('이전 날짜의 전송 파일입니다. 오래된 알림을 발송하지 않습니다.')
        try:
            result=publish(draft,os.getenv('NTFY_TOPIC',''),now)
            claim.update(status=result,accepted_at=now.isoformat())
            state['digest_cursor']=draft['cutoff_at']
            print('ntfy가 메시지를 수락했습니다. 휴대폰 수신 성공까지 검증한 것은 아닙니다.')
            return 0
        except (RuntimeError,ValueError) as e:
            claim.update(status='failed',failed_at=now.isoformat())
            print(str(e),file=sys.stderr);return 1
        finally:write_json(state_path,state)
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,OSError) as e:
        print(f'작업 중단: {e}',file=sys.stderr);sys.exit(2)
