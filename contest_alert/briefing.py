"""Priority public watchlist briefing. No browser-local notes or profile are read."""
from datetime import timedelta
from .timing import as_local,valid_day,status_at,exact_instant
from .taxonomy import technical_fields

def priority_lines(events,state,now,settings,comparison)->list[str]:
    watch=set(settings.get('watchlist',[]));wanted=set(settings.get('fields',[]))
    selected=[e for e in events if watch & set([e['id'],*e.get('member_ids',[]),*e.get('favorite_ids',[])])]
    lines=[]
    if watch:
        lines.append(f'관심 공고 {len(selected)}개 · 서버에 동기화한 목록 기준')
        today=as_local(now).date();end=today+timedelta(days=7);due=[]
        for e in selected:
            dates=[]
            if status_at(e,now)!='closed':
                dates.append({'label':'신청 마감','date':e.get('deadline'),'time':e.get('deadline_time'),'timezone':e.get('registration_timezone','Asia/Seoul')})
            dates+=e.get('milestones',[])
            for d in dates:
                day=valid_day(d.get('date'))
                instant=exact_instant({'deadline':d.get('date'),'deadline_time':d.get('time'),'registration_timezone':d.get('timezone','Asia/Seoul')},'deadline')
                if instant is not None and as_local(now)>=instant:continue
                if day and today<=day<=end:due.append((d['date'],e,d))
        for _,e,d in sorted(due,key=lambda x:x[0])[:3]:
            lines.append(f"• {d['label']} {d['date']}"+(' '+d['time'] if d.get('time') else ' (시각 미확인)')+' · '+e['title'][:65])
        watched_ids=set().union(*(set(e.get('member_ids',[]))|{e['id']} for e in selected)) if selected else set()
        changes=[x for x in state.get('changes',[]) if x.get('kind')=='updated' and x.get('id') in watched_ids and x.get('at','')>state.get('digest_cursor','')]
        if changes:lines.append('관심 공고 내용 변경 '+str(len({x['id'] for x in changes}))+'건 · 원문 재확인')
        if not due:lines.append('관심 목록에서 7일 이내 확인된 신청·제출 일정 없음')
        if len(selected)<len(watch):lines.append('일부 관심 항목은 통합·제외·미수집 상태일 수 있습니다.')
    if wanted:
        new=set(comparison.get('new_event_ids',[]))
        count=sum(e['id'] in new and bool(wanted&set(technical_fields(e))) for e in events)
        lines.append(f'선택 분야와 일치하는 신규 기회 {count}개')
    for a in state.get('quality_alerts',[])[:2]:lines.append('수집 점검: '+a.get('source_id','')+' · '+a.get('message',''))
    return lines
