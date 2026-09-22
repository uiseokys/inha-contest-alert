"""Clearly fictional v7 scenarios. This never modifies production state."""
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import argparse,copy,shutil,sys,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from contest_alert.core import empty_state
from contest_alert.render import build
from contest_alert.daily import capture_snapshot
from contest_alert.operations import finish_collection

def demo_state():
    now=datetime(2026,9,23,12,0,tzinfo=ZoneInfo('Asia/Seoul'));yesterday=now-timedelta(days=1);s=empty_state()
    source_names={'ds':'데이터사이언스학과','campus':'캠퍼스픽 · AI/데이터','dacon':'DACON','aix':'인공지능융합연구센터','af':'인공지능팩토리'}
    specs=[
     ('urban','ds','[가상] 2026 도시 수요 예측 AI 모델 경진대회','2026-11-20','18:00','2026-09-01','공공데이터 분석으로 교통 수요를 예측하는 모델 개발'),
     ('urban-repost','campus','[가상] 2026 도시 수요 예측 AI 모델 경진대회','2026-11-20','18:00','2026-09-01','공공데이터 분석으로 교통 수요를 예측하는 모델 개발'),
     ('factory','dacon','[가상] 2026 제조 현장의 다양한 센서 시계열 데이터를 활용한 설비 이상 탐지 및 유지보수 시점 예측 AI 모델 개발 경진대회','2026-10-31','17:00','2026-09-20','센서 데이터 분석 및 이상 탐지 모델 개발'),
     ('creative','campus','[가상] 생성형 AI 영상 제작 공모전','2026-10-12','18:00','2026-09-01','AI로 지속가능한 도시의 모습을 그리는 영상 창작'),
     ('service','af','[가상] 2026 LLM RAG 기반 AI 서비스 해커톤','2026-09-28','18:00','2026-09-10','지역 행정 정보를 제공하는 챗봇 서비스 개발'),
     ('program','aix','[가상] 데이터 시각화 교육 프로그램','2026-09-23','18:00','2026-09-01','공공데이터 시각화와 통계 분석 교육'),
     ('dayonly','ds','[가상] 2026 AI 아이디어 공모전','2026-09-23',None,'2026-09-01','지역 문제를 해결하는 AI 활용 아이디어'),
     ('upcoming','af','[가상] 2026 컴퓨터비전 모델 개발 부트캠프','2026-10-20','18:00','2026-09-23','컴퓨터비전과 딥러닝 모델 실습'),
     ('closed','ds','[가상] 2026 오늘 오전 접수 종료 AI 경진대회','2026-09-23','10:00','2026-09-01','AI 모델 개발'),
     ('unknown','aix','[가상] AI 연구 협력 프로그램',None,None,None,'인공지능 연구 프로젝트'),
     ('pending','campus','[가상] 지역 문제 해결 아이디어 공모전',None,None,None,'상세 원문 관련성 확인 대기')]
    new={'factory','urban-repost'}
    for rid,sid,title,end,clock,start,summary in specs:
        group='inha' if sid in ('ds','aix') else 'external';stamp=now.isoformat() if rid in new else yesterday.isoformat()
        row={'id':rid,'source_id':sid,'source_name':source_names[sid],'group':group,'title':title,'url':'https://example.org/notices/'+rid,'registration_start':start,'deadline':end,'deadline_time':clock,
             'summary':summary,'organizer':'가상데이터연구원','eligibility':'대학생·대학원생 / 1~4인 팀 (가상 예시)','benefits':'가상 예시 · 실제 모집 아님','first_seen':stamp,'last_changed':stamp,'last_seen':now.isoformat(),
             'relevance_status':'pending' if rid=='pending' else 'included','relevance_reason':'원문 분야 확인 대기' if rid=='pending' else 'AI·데이터 주제 확인',
             'relevance_evidence':summary,'detail_status':'ok' if end else 'unconfirmed','date_parser_version':7,'detail_parser_version':7,'detail_attempted_at':now.isoformat(),'date_evidence':('접수기간 '+str(start)+' ~ '+str(end)+' '+str(clock or '')+' (가상)') if end else None,
             'date_source_url':'https://example.org/notices/'+rid,'opportunity_kind':'program' if rid in ('program','upcoming','unknown') else 'contest'}
        if rid.startswith('urban'):row['website_url']='https://example.org/contest/2026-urban'
        if rid=='upcoming':row['registration_start_time']='14:00'
        if rid=='service':row['manual_correction']={'checked_at':'2026-09-23','evidence_url':row['url'],'reason':'가상 마감 연장 사례','needs_review':False}
        row['date_failure_code']='confirmed' if end else 'no_explicit_date'
        row['detail_trace']=[{'stage':'detail_http','outcome':'ok','text_length':1200},{'stage':'date_parse','outcome':'ok' if end else 'unconfirmed'}]
        s['items'][rid]=row;s['changes'].append({'id':rid,'kind':'new' if rid in new else 'initial','at':stamp})
    for sid,name in source_names.items():s['sources'][sid]={'name':name,'group':'inha' if sid in ('ds','aix') else 'external','url':'https://example.org/source/'+sid,'status':'ok','retained':sum(x['source_id']==sid for x in s['items'].values()),'checked_at':now.isoformat(),'message':'가상 사례 · 실제 수집 결과가 아닙니다.'}
    s['initialized_sources']=list(source_names);s['quality_policy_version']=6
    old=copy.deepcopy(s);old['items']={k:v for k,v in old['items'].items() if k not in new};old['updated_at']=yesterday.isoformat();capture_snapshot(old,yesterday);s['daily_snapshots']=old['daily_snapshots']
    s['updated_at']=now.isoformat();capture_snapshot(s,now);finish_collection(s,now-timedelta(minutes=20),now)
    s['claims'][now.date().isoformat()]={'status':'accepted','at':now.isoformat(),'accepted_at':now.isoformat()}
    return s,now

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path('preview-v7.html'));a=p.parse_args();root=Path(__file__).resolve().parents[1];s,now=demo_state()
    with tempfile.TemporaryDirectory() as td:
        temp=Path(td);shutil.copytree(root/'web',temp/'web');build(temp,s,now,repo_url='https://github.com/example/contest-demo',demo=True);a.output.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(temp/'site/index.html',a.output)
    print('Fictional v7 preview:',a.output)
if __name__=='__main__':main()
