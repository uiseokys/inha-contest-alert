"""Structured issue requests: data only, repository-owner approval only, no fetch."""
from __future__ import annotations
import copy,hashlib,ipaddress,json,re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
from .settings import validate as validate_settings
MARKER='<!-- CONTEST_REQUEST_V8 -->'

def authorized(actor:str,owner:str)->bool:
    return bool(actor and owner and actor.casefold()==owner.casefold())

def public_url(value:str)->str:
    if not isinstance(value,str) or len(value)>1800 or re.search(r'[\s\\<>"\x00-\x1f]',value):raise ValueError('공개 HTTPS 주소를 입력하세요.')
    p=urlsplit(value)
    if p.scheme!='https' or not p.hostname or p.username or p.password or p.port not in (None,443):raise ValueError('공개 HTTPS 주소만 사용할 수 있습니다.')
    host=p.hostname.lower()
    if '.' not in host or host.endswith(('.local','.localhost','.internal','.lan')):raise ValueError('내부 주소를 등록할 수 없습니다.')
    try:
        ip=ipaddress.ip_address(host)
        if not ip.is_global:raise ValueError('내부 IP는 등록할 수 없습니다.')
    except ValueError as e:
        if re.fullmatch(r'[\d.]+',host) or ':' in host:raise ValueError('IP 주소 대신 공식 호스트 이름을 사용하세요.') from e
    return urlunsplit((p.scheme,p.netloc,p.path or '/',p.query,''))

def _text(x,maxlen,required=False):
    if not isinstance(x,str) or len(x)>maxlen or re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]',x) or (required and not x.strip()):raise ValueError('입력 텍스트 길이/형식 오류')
    return x.strip()

def validate_payload(kind:str,payload:dict)->dict:
    from .timing import valid_day
    if not isinstance(payload,dict):raise ValueError('요청 payload는 객체여야 합니다.')
    if kind=='settings':
        if set(payload)-{'notification','watchlist','fields'}:raise ValueError('설정 요청 항목 오류')
        normalized=validate_settings(payload)
        result={key:normalized[key] for key in payload}
        if 'notification' in payload:result['notification']={k:normalized['notification'][k] for k in payload['notification']}
        return result
    allowed={'add_notice':{'url','title','summary','organizer','eligibility','deadline','registration_start','deadline_time','evidence_url','checked_at'},
             'correct_notice':{'url','title','exclude','deadline','registration_start','deadline_time','evidence_url','checked_at','reason'},
             'report':{'url','id','category','description'}}
    if kind not in allowed or set(payload)-allowed[kind]:raise ValueError('지원하지 않는 요청 종류/항목')
    out=copy.deepcopy(payload);out['url']=public_url(out.get('url',''))
    if kind=='report':
        if out.get('category') not in ['date','title','irrelevant','duplicate','broken_link','other']:raise ValueError('오류 유형을 선택하세요.')
        out['description']=_text(out.get('description',''),800,True)
        if 'id' in out:out['id']=_text(out['id'],120)
        return out
    out['evidence_url']=public_url(out.get('evidence_url',''))
    if not valid_day(out.get('checked_at','')):raise ValueError('근거 확인일 YYYY-MM-DD가 필요합니다.')
    if kind=='add_notice':
        out['title']=_text(out.get('title',''),240,True);out['summary']=_text(out.get('summary',''),500,True)
    for key,limit in [('organizer',200),('eligibility',350),('title',240),('reason',300)]:
        if key in out:out[key]=_text(out[key],limit,True)
    if kind=='correct_notice' and not out.get('reason'):raise ValueError('수정 사유가 필요합니다.')
    if 'exclude' in out and not isinstance(out['exclude'],bool):raise ValueError('제외 여부는 boolean이어야 합니다.')
    for key in ('registration_start','deadline'):
        if key in out and out[key] is not None and not valid_day(out[key]):raise ValueError('날짜는 YYYY-MM-DD 형식이어야 합니다.')
    if out.get('registration_start') and out.get('deadline') and out['registration_start']>out['deadline']:raise ValueError('시작일이 마감일보다 늦습니다.')
    if out.get('deadline_time'):
        if not out.get('deadline') or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',out['deadline_time']):raise ValueError('마감 시각에는 올바른 마감 날짜도 필요합니다.')
    if kind=='correct_notice' and not any(k in out for k in ('title','exclude','deadline','registration_start','deadline_time')):raise ValueError('수정할 항목이 없습니다.')
    return out

def parse_request(body:str)->dict|None:
    if not isinstance(body,str) or not body.lstrip().startswith(MARKER):return None
    if len(body)>16000:raise ValueError('요청 크기가 너무 큽니다.')
    blocks=re.findall(r'```json\s*\n([\s\S]*?)\n```',body)
    if len(blocks)!=1:raise ValueError('JSON 요청 블록은 하나여야 합니다.')
    data=json.loads(blocks[0])
    if not isinstance(data,dict) or set(data)!={'version','kind','payload'} or data['version']!=1:raise ValueError('v8 요청 형식 오류')
    return {'version':1,'kind':data['kind'],'payload':validate_payload(data['kind'],data['payload'])}

def apply_request(root:Path,request:dict,number:int,now:datetime)->dict:
    """Caller must authenticate GitHub actor first. Commit is caller's responsibility."""
    from .__main__ import read_json,write_json
    from .settings import load
    if type(number) is not int or number<=0:raise ValueError('유효한 이슈 번호 필요')
    req={'kind':request['kind'],'payload':validate_payload(request['kind'],request['payload'])};p=req['payload'];kind=req['kind']
    if p.get('checked_at','')>now.date().isoformat():raise ValueError('미래 확인일을 사용할 수 없습니다.')
    s=load(root)
    if number in s.get('applied_requests',[]):return {'status':'already_applied','changed':False}
    if kind=='report':return {'status':'review_required','changed':False}
    if kind=='settings':
        for k,v in p.items():
            if k=='notification':s[k].update(v)
            else:s[k]=v
    else:
        store=read_json(root/'intake.json',{'version':1,'entries':{},'corrections':{}})
        if len(store.get('entries',{}))>=300 and kind=='add_notice' and p['url'] not in store['entries']:raise ValueError('직접 추가 공고는 300개까지입니다.')
        if kind=='add_notice':store.setdefault('entries',{})[p['url']]=p
        else:
            store.setdefault('corrections',{})[p['url']]={**store.get('corrections',{}).get(p['url'],{}),**p}
            dates={k:p[k] for k in ('deadline','registration_start','deadline_time') if k in p}
            if dates:
                overrides=read_json(root/'overrides.json',{'version':1,'entries':{}})
                overrides.setdefault('entries',{})[p['url']]={**dates,'evidence_url':p['evidence_url'],'checked_at':p['checked_at'],'reason':p['reason']}
                # Validate against the existing records before any file is written.
                from .core import empty_state
                from .corrections import apply_corrections
                probe=read_json(root/'data/state.json',empty_state());apply_corrections(probe,overrides,now)
                write_json(root/'overrides.json',overrides)
        write_json(root/'intake.json',store)
    s['updated_at']=now.isoformat();s['revision']='issue-'+str(number);s['applied_requests']=(s.get('applied_requests',[])+[number])[-200:]
    write_json(root/'server_settings.json',validate_settings(s))
    return {'status':'applied','changed':True,'kind':kind,'revision':s['revision']}

def apply_intake(root:Path,state:dict,now:datetime)->None:
    from .__main__ import read_json
    from .core import merge_items,canonical
    from .quality import classify
    content=read_json(root/'intake.json',{'version':1,'entries':{},'corrections':{}});records=[]
    for url,entry in content.get('entries',{}).items():
        p=validate_payload('add_notice',entry);old=next((i for i in state['items'].values() if canonical(i.get('url',''))==canonical(url)),None)
        if old:continue
        rid=hashlib.sha256(canonical(url).encode()).hexdigest()[:20]
        record={'id':rid,'url':url,'source_id':'manual','source_name':'직접 추가 · 관리자 확인','group':'external',**{k:v for k,v in p.items() if k in ('title','summary','organizer','eligibility','deadline','registration_start','deadline_time')}}
        record.update(detail_status='ok',detail_checked_at=now.isoformat(),date_source_url=p['evidence_url'],date_evidence='관리자 직접 입력 · '+p['checked_at']+' 원문 확인',date_failure_code='confirmed' if p.get('deadline') else 'no_explicit_date')
        record.update(classify(record));records.append(record)
    if records:
        # Rendering an owner-added record is not a successful live crawl.
        import copy
        stamp=state.get('updated_at');claims=copy.deepcopy(state.get('claims',{}))
        merge_items(state,records,now)
        state['updated_at']=stamp;state['claims']=claims
        state['sources']['manual']={'name':'직접 추가 · 관리자 확인','url':'','group':'external','status':'ok','retained':len(records),'message':'자동 수집이 아닌 근거 링크를 확인한 직접 추가 공고','checked_at':now.isoformat()}
        state['initialized_sources']=sorted(set(state.get('initialized_sources',[]))|{'manual'})
    for item in state['items'].values():
        entry=next((v for u,v in content.get('corrections',{}).items() if canonical(u)==canonical(item.get('url',''))),None)
        if not entry:continue
        if entry.get('title'):item['title']=item['detail_title']=entry['title']
        if entry.get('exclude') is True:item.update(relevance_status='excluded',relevance_reason='관리자 원문 확인 후 제외',relevance_evidence='')
        elif entry.get('exclude') is False:item.update(classify(item))
