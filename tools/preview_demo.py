"""Generate a clearly labeled synthetic UI preview; never touch live state."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse,shutil,tempfile,sys,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from contest_alert.core import empty_state
from contest_alert.render import build
from contest_alert.daily import capture_snapshot


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path('preview.html'));args=p.parse_args()
    root=Path(__file__).resolve().parents[1];now=datetime(2026,9,22,11,43,tzinfo=ZoneInfo('Asia/Seoul'))
    state=empty_state();state['updated_at']=now.isoformat()
    rows=[
      ('데이터사이언스학과 · 대회','inha','인하 데이터 분석 경진대회','2026-09-30',None,True),
      ('인공지능공학과 · 공지','inha','대학생 AI 아이디어 공모전','2026-09-25',None,False),
      ('인공지능융합연구센터','inha','생성형 AI 서비스 해커톤',None,None,False),
      ('SW중심대학사업단','inha','교내 캡스톤 디자인 경진대회 — 인공지능과 공공데이터를 활용한 지속가능한 도시·산업 현장 문제 해결 및 실증 서비스 개발 프로젝트','2026-10-08','2026-10-01',False),
      ('DACON','external','제조 데이터 예측 챌린지','2026-09-24',None,True),
      ('인하대학교 · 교내 공지','inha','공공데이터 활용 아이디어톤',None,None,False),
      ('인공지능팩토리','external','컴퓨터비전 모델 경진대회','2026-10-06',None,False),
      ('데이터사이언스학과 · 대회','inha','지난 학기 데이터톤','2026-09-10',None,False),
      ('캠퍼스픽 · AI/데이터','external','도시 수요예측 AI 경진대회','2026-09-30','2026-09-01',True)]
    for idx,(source,group,title,deadline,start,new) in enumerate(rows):
        if deadline and not start:start='2026-09-01'  # Synthetic date, not a scraped fact.
        sid='s'+str(idx if idx!=7 else 0);rid=str(idx)
        stamp=now.isoformat() if new else '2026-09-20T11:40:00+09:00'
        state['items'][rid]={'id':rid,'title':'[예시] '+title,'source_name':source,'source_id':sid,'group':group,
          'url':f'https://example.com/demo-contest/{idx}','deadline':deadline,'registration_start':start,'platform_status':None,
          'posted_at':'2026-09-21' if new else '2026-09-18','first_seen':stamp,'last_seen':now.isoformat(),'last_changed':stamp}
        if deadline:
            state['items'][rid].update(date_source_url=state['items'][rid]['url'],date_evidence=f'접수기간: {start} ~ {deadline} (가상 예시)',date_status='complete',detail_status='ok',detail_checked_at=now.isoformat())
        if idx in (0,8):
            state['items'][rid].update(registration_start='2026-09-01',
                registration_text='2026.09.01 ~ 2026.09.30 18:00',event_start='2026-10-10',event_end='2026-10-12',
                organizer='예시데이터연구원',eligibility='대학생 및 대학원생 · 개인 또는 2~4인 팀',
                benefits='총상금 300만원 (가상 예시)',summary='공공데이터를 이용한 도시 수요 예측',
                schedule_text='본선 2026.10.10 ~ 2026.10.12',
                website_url='https://example.com/demo-official',application_url='https://example.com/demo-apply',
                date_source_url=state['items'][rid]['url'],date_evidence='접수기간: 2026.09.01 ~ 2026.09.30 18:00 (가상 예시)',date_status='complete',detail_source_url=state['items'][rid]['url'],detail_checked_at=now.isoformat(),detail_status='ok')
        elif idx==2:state['items'][rid].update(detail_status='unconfirmed')
        state['changes'].append({'id':rid,'kind':'new' if new else 'initial','at':stamp})
        if sid not in state['sources']:
            state['sources'][sid]={'name':source,'url':'https://example.com/','group':group,'status':'error' if idx==1 else 'ok',
             'message':'[예시] 접속 실패 · 원문 직접 확인 필요' if idx==1 else '[예시] 설정된 목록 범위 수집 완료',
             'checked_at':now.isoformat(),'retained':1,'recognized':20,'pages':1}
    for sid,report in state['sources'].items():
        own=[x for x in state['items'].values() if x['source_id']==sid]
        report['dates_complete']=sum(bool(x.get('registration_start') and x.get('deadline')) for x in own)
        report['dates_partial']=0;report['dates_missing']=len(own)-report['dates_complete']
    state['initialized_sources']=sorted(state['sources'])
    previous=copy.deepcopy(state)
    new_ids={x['id'] for x in state['changes'] if x['kind']=='new'}
    previous['items']={k:v for k,v in previous['items'].items() if k not in new_ids}
    capture_snapshot(previous,datetime(2026,9,21,11,43,tzinfo=ZoneInfo('Asia/Seoul')))
    state['daily_snapshots']=previous['daily_snapshots']
    capture_snapshot(state,now)
    with tempfile.TemporaryDirectory() as td:
        temp=Path(td);shutil.copytree(root/'web',temp/'web')
        build(temp,state,now,repo_url='https://github.com/',demo=True)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(temp/'site/index.html',args.output)
    print('Synthetic preview:',args.output)
if __name__=='__main__':main()
