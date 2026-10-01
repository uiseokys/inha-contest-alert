"""Validated non-secret server preferences. Safe to import before dependencies."""
from __future__ import annotations
import copy,json,re
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
KST=ZoneInfo('Asia/Seoul')
FIELDS={'data_analysis','model_development','service_development','creative_ai','general_ai'}
ID=re.compile(r'[A-Za-z0-9:_-]{1,120}')
def validate(value:dict)->dict:
    if not isinstance(value,dict) or set(value)-{'version','notification','watchlist','fields','revision','updated_at','applied_requests'}:raise ValueError('서버 설정에 허용되지 않은 항목이 있습니다. 토픽·개인 메모는 넣지 마세요.')
    if value.get('version',1)!=1:raise ValueError('지원하지 않는 서버 설정 버전입니다.')
    n=value.get('notification',{})
    if not isinstance(n,dict) or set(n)-{'time','timezone','enabled'}:raise ValueError('알림 설정 형식 오류')
    clock=n.get('time','12:00');enabled=n.get('enabled',True)
    if not isinstance(clock,str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',clock):raise ValueError('알림 시각은 00:00~23:59의 HH:MM이어야 합니다.')
    if not isinstance(enabled,bool) or n.get('timezone','Asia/Seoul')!='Asia/Seoul':raise ValueError('한국시간과 명시적인 알림 켜기/끄기만 지원합니다.')
    result={'version':1,'notification':{'time':clock,'enabled':enabled,'timezone':'Asia/Seoul'},'watchlist':[],'fields':[]}
    for key,allowed,limit in [('watchlist',None,100),('fields',FIELDS,5)]:
        seq=value.get(key,[])
        if not isinstance(seq,list) or len(seq)>limit or any(not isinstance(x,str) or (x not in allowed if allowed else not ID.fullmatch(x)) for x in seq):raise ValueError(f'{key} 설정에 허용되지 않은 값이 있습니다.')
        result[key]=list(dict.fromkeys(seq))
    for key in ('revision','updated_at'):
        if key in value:
            if not isinstance(value[key],str) or len(value[key])>100:raise ValueError('설정 기록 형식 오류')
            result[key]=value[key]
    requests=value.get('applied_requests',[])
    if not isinstance(requests,list) or len(requests)>200 or any(type(x) is not int or x<=0 for x in requests):raise ValueError('요청 기록 형식 오류')
    result['applied_requests']=requests
    return result

def load(root:Path)->dict:
    p=root/'server_settings.json'
    return validate(json.loads(p.read_text(encoding='utf-8')) if p.exists() else {})

def target(settings:dict,now:datetime)->datetime:
    clock=validate(settings)['notification']['time'];h,m=map(int,clock.split(':'))
    return now.astimezone(KST).replace(hour=h,minute=m,second=0,microsecond=0)

def due(settings:dict,state:dict,now:datetime)->dict:
    s=validate(settings);now=now.astimezone(KST);day=now.date().isoformat()
    # Disabled pushes still allow one daily noon data refresh.
    t=target(s if s['notification']['enabled'] else {},now)
    if day in state.get('claims',{}) or day in state.get('scheduler_attempts',{}):return {'run':False,'day':day,'reason':'already_attempted'}
    return {'run':now>=t-timedelta(minutes=25),'day':day,'target_at':t.isoformat(),'reason':'due' if now>=t-timedelta(minutes=25) else 'before_window'}

def public(settings:dict)->dict:
    s=validate(settings)
    return {k:copy.deepcopy(s[k]) for k in ('notification','watchlist','fields','revision','updated_at') if k in s}
