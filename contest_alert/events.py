"""Conservative cross-source opportunity identity without deleting notice history.

Exact official event URLs dominate. Similarity alone never merges two notices.
Years, rounds and tracks are guards; ambiguous groups expose conflicting dates.
"""
from __future__ import annotations
import copy,hashlib,re
from urllib.parse import urlsplit
from .core import canonical,preferred_title
from .quality import visible_state
from .timing import valid_day

def _platform(url:str)->str:
    p=urlsplit(canonical(url));host=p.hostname or ''
    if host in ('dacon.io','www.dacon.io'):
        m=re.match(r'/competitions/(official|open)/(\d+)',p.path)
        if m:return 'dacon:'+m[1]+':'+m[2]
    if host in ('aifactory.space','www.aifactory.space'):
        m=re.match(r'/(?:ko/)?competitions/(\d+)',p.path)
        if m:return 'aifactory:'+m[1]
    return ''

def official_key(item:dict)->str:
    if own:=_platform(item.get('url','')):return own
    values=[canonical(item.get(k,'')) for k in ('application_url','website_url','date_source_url')]
    known={_platform(v) for v in values if _platform(v)}
    if len(known)==1:return next(iter(known))
    if len(known)>1:return ''  # A multi-track landing page is not one event.
    for v in values[:2]:
        if not v:continue
        p=urlsplit(v)
        if any(x in (p.hostname or '') for x in ('campuspick.com','inha.ac.kr')):continue
        if re.search(r'/(?:contest|competition|hackathon|challenge|event)s?/[^/]{3,}',p.path,re.I):
            return 'linked:'+v
    return ''

def _scope(item:dict)->tuple[set,tuple]:
    title=preferred_title(item)
    years=set(re.findall(r'(?<!\d)(20\d{2})(?!\d)',title))
    if not years:
        years={str(item[k])[:4] for k in ('registration_start','deadline') if valid_day(item.get(k))}
    rounds=tuple(sorted((a or b or c) for a,b,c in re.findall(r'(\d+\s*차)|((?:시즌|season)\s*\d+)|((?:주제|트랙|부문|track)\s*[:：]?\s*[0-9A-Z]+)',title,re.I)))
    audience=tuple(sorted(re.findall(r'(?:학부생|대학원생|학생|일반|청소년|초급|고급)\s*(?:부문|트랙|부|팀)',title)))
    named=tuple(sorted(re.findall(r'[가-힣A-Za-z]+\s*(?:부문|트랙)',title)))
    return years,rounds+audience+named

def _compatible(a:dict,b:dict)->bool:
    ya,sa=_scope(a);yb,sb=_scope(b)
    if ya and yb and not (ya&yb):return False
    if sa!=sb and (sa or sb):return False
    ka,kb=official_key(a),official_key(b)
    if ka and kb and not ka.startswith('linked:') and not kb.startswith('linked:') and ka!=kb:return False
    return True

def _title_fallback(item:dict)->str:
    title=preferred_title(item)
    title=re.sub(r'^\s*\[(?:행사|홍보|공모|모집|공지|안내)\]\s*','',title)
    title=re.sub(r'\s*(?:개최\s*안내|참가자?\s*모집\s*안내|개최)$','',title)
    title=re.sub(r'[\s\W_]+','',title).casefold()
    org=re.sub(r'[\s\W_]+','',str(item.get('organizer',''))).casefold()
    start,end=item.get('registration_start'),item.get('deadline')
    years,_=_scope(item)
    if len(title)<12 or len(org)<2 or not years or not valid_day(start) or not valid_day(end):return ''
    return '|'.join([title,org,str(start),str(end)])

def _birth(item):return (str(item.get('first_seen') or '9999'),str(item.get('id','')))

def _rank(item):
    return (0 if item.get('manual_correction') else 1,
            0 if _platform(item.get('url','')) else 1,
            0 if item.get('deadline') and not item.get('registration_ambiguous') else 1,
            0 if item.get('deadline_time') else 1,_birth(item))

def group_events(state:dict)->list[dict]:
    rows=list(visible_state(state).get('items',{}).values())
    parent=list(range(len(rows)));members={n:{n} for n in parent}
    def find(n):
        while parent[n]!=n:parent[n]=parent[parent[n]];n=parent[n]
        return n
    buckets={}
    for n,row in enumerate(rows):
        key=official_key(row);title=_title_fallback(row)
        for token in ([key] if key else [])+(['title:'+title] if title else []):buckets.setdefault(token,[]).append(n)
    for candidates in buckets.values():
        for i in range(len(candidates)):
            for j in range(i):
                a,b=find(candidates[i]),find(candidates[j])
                if a==b:continue
                if all(_compatible(rows[x],rows[y]) for x in members[a] for y in members[b]):
                    parent[b]=a;members[a]|=members.pop(b)
    registry=state.setdefault('event_registry',{})
    aliases=state.setdefault('event_aliases',{})
    identities=state.get('identity_aliases',{})
    output=[]
    for bucket in members.values():
        entries=sorted((rows[i] for i in bucket),key=_birth)
        first=entries[0]
        prior=[registry[x['id']] for x in entries if x['id'] in registry]
        eid=prior[0] if prior else 'evt_'+first['id']
        # Collapse earlier event IDs without invalidating downloaded favorites.
        for old in set(prior):
            if old!=eid:aliases[old]=eid
        ids={x['id'] for x in entries}
        ids|={old for old,new in identities.items() if new in ids}
        for rid in ids:registry[rid]=eid
        winner=sorted(entries,key=_rank)[0];event=copy.deepcopy(winner)
        event['id']=eid;event['notice_id']=winner['id'];event['member_ids']=sorted(ids)
        previous_ids={old for old,target in aliases.items() if target==eid}
        event['favorite_ids']=sorted(ids|previous_ids|{eid}|{'evt_'+rid for rid in ids})
        event['first_seen']=min(str(x.get('first_seen') or '9999') for x in entries)
        event['last_changed']=max(str(x.get('last_changed') or '') for x in entries)
        event['last_seen']=max(str(x.get('last_seen') or '') for x in entries)
        event['source_names']=list(dict.fromkeys(x.get('source_name','') for x in entries))
        event['groups']=sorted(set(x.get('group','external') for x in entries))
        event['source_count']=len(entries)
        event['grouping_basis']='공식 대회 주소' if any(official_key(x) for x in entries) else '동일 제목·연도·주최·접수기간' if len(entries)>1 else '단일 공고'
        event['sources']=[{k: x.get(k) for k in ('id','title','url','source_id','source_name','group','deadline','deadline_time','registration_start','date_source_url')} for x in entries]
        event['source_name']=' · '.join(event['source_names'][:2])+(' 외 '+str(len(event['source_names'])-2)+'곳' if len(event['source_names'])>2 else '')
        for field in ('organizer','summary','eligibility','benefits','application_url','website_url'):
            if not event.get(field):event[field]=next((x[field] for x in sorted(entries,key=_rank) if x.get(field)),None)
        ends={x['deadline'] for x in entries if valid_day(x.get('deadline')) and not x.get('registration_ambiguous')}
        times={x['deadline_time'] for x in entries if x.get('deadline')==event.get('deadline') and x.get('deadline_time') and not x.get('registration_time_ambiguous')}
        conflict=len(ends)>1 or len(times)>1
        event['cross_source_conflict']=conflict
        if conflict:
            event['conflicting_deadlines']=sorted(ends)
            # Known direct platform or an explicit manual correction has a clear
            # preferred provenance. Others remain uncertain instead of guessing.
            if not (_platform(winner.get('url','')) or winner.get('manual_correction')):
                event.update(deadline=None,registration_start=None,deadline_time=None,registration_start_time=None,registration_ambiguous=True,date_status='conflict')
            event['date_note']=(event.get('date_note','')+' 출처 간 일정이 다릅니다. 상세의 각 원문을 확인하세요.').strip()
        output.append(event)
    return sorted(output,key=_birth)

def event_comparison(state:dict,comparison:dict,events:list[dict])->dict:
    result=copy.deepcopy(comparison)
    ready=result.get('status') in ('comparable','gap')
    baseline=set(state.get('daily_snapshots',{}).get(result.get('base_date'),{}).get('ids',[]))
    raw_new=set(result.get('new_ids',[]));raw_updated=set(result.get('updated_ids',[]))
    new=[e['id'] for e in events if raw_new.intersection(e['member_ids']) and not baseline.intersection(e['member_ids'])] if ready else []
    updated=[e['id'] for e in events if raw_updated.intersection(e['member_ids']) and e['id'] not in new] if ready else []
    result.update(new_notice_count=result.get('new_count'),new_event_count=len(new) if ready else None,
        new_event_ids=new,updated_event_count=len(updated),updated_event_ids=updated,
        repost_count=max(0,len(raw_new)-sum(len(raw_new.intersection(e['member_ids'])) for e in events if e['id'] in new)) if ready else 0)
    result['deadline_extensions']=[];result['date_correction_count']=0
    if ready:
        cutoff=result.get('base_at') or '';upper=result.get('as_of') or ''
        idmap={rid:e for e in events for rid in e['member_ids']}
        latest={}
        for c in state.get('changes',[]):
            if c.get('kind')!='updated' or not cutoff<c.get('at','')<=upper:continue
            if c.get('date_change_reason')=='reparsed':
                result['date_correction_count']+=1;continue
            old,newd=c.get('old_deadline'),c.get('new_deadline')
            if not valid_day(old) or not valid_day(newd):continue
            extension=newd>old
            if old==newd and c.get('old_deadline_time') and c.get('new_deadline_time'):
                extension=c['new_deadline_time']>c['old_deadline_time']
            event=idmap.get(c.get('id'))
            if extension and event and event.get('deadline')==newd:
                latest[event['id']]={'id':event['id'],'title':event['title'],'from':old,'to':newd,'from_time':c.get('old_deadline_time'),'to_time':c.get('new_deadline_time')}
        result['deadline_extensions']=list(latest.values())
    return result
