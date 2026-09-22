"""One daily attempt, persisted BEFORE publish. Never persist an ntfy topic.

An HTTP success means ntfy accepted the message, NOT that a phone displayed it.
There is deliberately no automatic POST retry: an ambiguous timeout may already
have delivered the request, so retrying would risk a duplicate notification.
"""
from __future__ import annotations
import copy,json,re
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import requests
from .core import status_of
from .quality import visible_state
from .daily import compare_day, comparison_lines

KST=ZoneInfo('Asia/Seoul')

def noon_target(now:datetime)->datetime:
    return now.astimezone(KST).replace(hour=12,minute=0,second=0,microsecond=0)

def validate_topic(topic:str)->str:
    if not re.fullmatch(r'[A-Za-z0-9_-]{32,64}',topic or ''):
        raise ValueError('NTFY_TOPIC에는 영문/숫자/_/-로 만든 32~64자 무작위 토픽을 설정하세요. 값은 로그에 표시하지 않습니다.')
    return topic

def utf8_clip(text:str,limit:int)->str:
    return text.encode('utf-8')[:limit].decode('utf-8',errors='ignore')

def digest(state:dict,now:datetime,page_url:str)->str:
    state=visible_state(state)
    today=now.astimezone(KST).date();cursor=state.get('digest_cursor','')
    changes=[x for x in state['changes'] if x['at']>cursor and x['id'] in state['items']]
    new=list(dict.fromkeys(c['id'] for c in changes if c['kind']=='new'))
    initial=list(dict.fromkeys(c['id'] for c in changes if c['kind']=='initial'))
    updated=list(dict.fromkeys(c['id'] for c in changes if c['kind']=='updated' and c['id'] not in new))
    enabled=[s for s in state['sources'].values() if s['status']!='disabled']
    good=sum(s['status']=='ok' for s in enabled)
    failed=sum(s['status'] in ('error','partial') for s in enabled)
    comparison = compare_day(state, now)
    lines=[f'{today.isoformat()} 공모전·경진대회', *comparison_lines(comparison),
           f'지난 알림 이후 미전달 신규 {len(new)}건 · 변경 {len(updated)}건',
           f'출처 수집 정상 {good}/{len(enabled)}곳']
    if failed:lines.append(f'주의: {failed}곳 수집 실패/부분 실패. 신규 0건이어도 전체에 없다는 뜻은 아닙니다.')
    if initial:lines.append(f'최초 수집 {len(initial)}건은 기존 목록에 추가했습니다.')
    visible=sum(status_of(x,today)!='closed' for x in state['items'].values())
    lines.append(f'목록 {visible}건 (마감 미확인 포함)')
    picks=new[:4] or updated[:3]
    for rid in picks:
        item=state['items'][rid]
        lines.append('• '+utf8_clip(item['title'],180))
    due=sorted((x for x in state['items'].values() if x.get('deadline') and today.isoformat()<=x['deadline']<=(today+timedelta(days=7)).isoformat()),key=lambda x:x['deadline'])
    if due:
        lines.append('7일 이내 마감일 확인:')
        for x in due[:2]:lines.append(f"• {x['deadline']} {utf8_clip(x['title'],140)}")
    if not new and not updated and not initial:lines.append('이번 확인 범위에서 새로 발견한 공고 0건입니다.')
    tail=f'\n전체 목록: {page_url}\n신규는 새로 확인한 공고 주소 기준이며 실제 게시일·대회 수와 다를 수 있습니다.\n신청 가능 여부와 마감 시각은 원문을 확인하세요.'
    return utf8_clip('\n'.join(lines),2600)+tail

def reserve(state:dict,now:datetime,page_url:str,mode:str,run_id:str)->dict|None:
    day=now.astimezone(KST).date().isoformat()
    if day in state['claims']:return None
    draft={'day':day,'mode':mode,'run_id':run_id,'cutoff_at':state.get('updated_at') or now.isoformat(),
           'payload':{'title':'공모전 모아보기 · 점심 브리핑','message':digest(state,now,page_url),
                      'click':page_url,'tags':['calendar'],'priority':3}}
    state['claims'][day]={'status':'reserved','at':now.isoformat(),'run_id':run_id}
    return draft

def publish(draft:dict,topic:str,now:datetime,sender=None)->str:
    topic=validate_topic(topic)
    payload=copy.deepcopy(draft['payload']);payload['topic']=topic
    if draft['mode']=='scheduled':
        target=datetime.fromisoformat(draft['day']+'T12:00:00+09:00')
        seconds=(target-now.astimezone(KST)).total_seconds()
        if seconds>=15:payload['delay']=str(int(target.timestamp()))
        elif seconds>0:
            # ntfy minimum delay is 10s; avoid delivering a few seconds before noon.
            payload['delay']='15s'
        else:payload['message']='[정오 작업 지연: 완료 후 발송]\n'+payload['message']
    encoded=json.dumps(payload,ensure_ascii=False).encode('utf-8')
    if len(encoded)>4096:raise ValueError('메시지가 ntfy 4096바이트 한도를 초과해 전송을 중단했습니다.')
    try:
        response=(sender or requests).post('https://ntfy.sh/',data=encoded,
                    headers={'Content-Type':'application/json; charset=utf-8'},timeout=20)
    except Exception:
        raise RuntimeError('ntfy 연결 실패. 전송 여부가 불명확할 수 있어 중복 방지상 자동 재시도하지 않습니다.') from None
    if response.status_code!=200:
        raise RuntimeError(f'ntfy가 요청을 수락하지 않음 (HTTP {response.status_code}); 응답 본문은 비공개 처리했습니다.')
    return 'accepted'
