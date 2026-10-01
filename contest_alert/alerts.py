"""Daily quality regression checks, conservative about new/unrequested records."""
from __future__ import annotations
from collections import defaultdict

def sample(state:dict)->dict:
    groups=defaultdict(list)
    for i in state.get('items',{}).values():
        if i.get('relevance_status')=='included' and not i.get('duplicate_of'):groups[i['source_id']].append(i)
    return {sid:{'items':len(rows),'known':sum(bool(x.get('deadline')) for x in rows),'ids':[x['id'] for x in rows],'known_ids':[x['id'] for x in rows if x.get('deadline')],'status':state.get('sources',{}).get(sid,{}).get('status')} for sid,rows in groups.items()}

def compare(before:dict,after:dict)->list[dict]:
    results=[]
    for sid,a in before.items():
        b=after.get(sid)
        if not b or a.get('items',0)<5 or b.get('items',0)<5:continue
        common=set(a.get('ids',[]))&set(b.get('ids',[]))
        if len(common)<5:continue
        if 'known_ids' in a and 'known_ids' in b:
            old=len(set(a['known_ids'])&common);new=len(set(b['known_ids'])&common)
        elif set(a.get('ids',[]))==set(b.get('ids',[])):old=a['known'];new=b['known']
        else:continue
        if old-new>=3 and (old-new)/len(common)>=0.3:results.append({'source_id':sid,'kind':'date_regression','previous_known':old,'current_known':new,'comparable':len(common),'message':'같은 공고 기준 마감 확인 수가 급감했습니다. 추출 결과를 확인하세요.'})
        if a.get('status')=='ok' and b.get('status')=='error':results.append({'source_id':sid,'kind':'source_failure','message':'지난 정상 출처의 목록 접근이 실패했습니다.'})
    return results

def record(state:dict,now)->None:
    day=now.date().isoformat();history=state.setdefault('quality_history',{});previous=sorted(k for k in history if k<day)
    current=sample(state);state['quality_alerts']=compare(history[previous[-1]],current) if previous else []
    history[day]=current
    for old in sorted(history)[:-14]:history.pop(old)
