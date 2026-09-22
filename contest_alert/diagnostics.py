"""Small, public-safe date quality reports measured from saved collection results."""
from __future__ import annotations
from collections import Counter
from datetime import datetime
from .core import canonical
from .timing import valid_day,exact_instant,as_local
REASONS={
 'manual_date':'관리자 근거 보정','manual_review':'관리자 보정 · 원문 변경 재확인 필요',
 'not_requested':'상세 조회 전','budget_deferred':'상세 요청 예산으로 대기',
 'network_error':'네트워크 요청 실패','robots_disallowed':'robots 정책으로 보류',
 'robots_unavailable':'robots 확인 실패','http_401':'인증 필요','http_403':'접근 거부',
 'http_404':'상세 페이지 없음','http_429':'요청 제한','access_blocked':'접근 제한 화면',
 'browser_failed':'동적 화면 읽기 실패','browser_denied':'동적 화면 접근 제한',
 'render_unconfirmed':'화면에서 접수 날짜 미확인','no_explicit_date':'명시적인 접수 날짜 미확인',
 'date_conflict':'접수 기간 충돌·형식 미확정','schedule_error':'추가 일정 페이지 확인 실패',
 'parser_error':'본문 해석 오류','confirmed':'날짜 확인','partial_date':'시작 또는 마감 일부만 확인',
 'stale_evidence':'이전 확인 날짜 유지 · 이번 상세에서 재확인 못함','cached_date':'이전 확인 날짜 · 재조회 대기',
}
def reason_for(item:dict)->str:
    if item.get('manual_correction'):return 'manual_review' if item['manual_correction'].get('needs_review') else 'manual_date'
    known=bool(valid_day(item.get('deadline'))) and not item.get('registration_ambiguous')
    if known and item.get('date_failure_code')=='budget_deferred':return 'cached_date'
    if known and (item.get('detail_status')=='error' or item.get('date_failure_code') not in (None,'','confirmed')):return 'stale_evidence'
    if item.get('registration_ambiguous') or item.get('date_status')=='conflict':return 'date_conflict'
    if known:return 'confirmed' if valid_day(item.get('registration_start')) else 'partial_date'
    code=item.get('date_failure_code')
    if code:return code if code in REASONS or str(code).startswith('http_') else 'parser_error'
    if not item.get('detail_attempted_at'):return 'not_requested'
    if item.get('detail_status')=='error':return 'network_error'
    if valid_day(item.get('registration_start')):return 'partial_date'
    return 'no_explicit_date'

def diagnostic_report(state:dict,now:datetime)->dict:
    """Denominator includes saved relevant notices, including expired ones, not all web contests."""
    visible=[i for i in state.get('items',{}).values() if not i.get('duplicate_of') and
             (not state.get('quality_policy_version') or i.get('relevance_status')=='included')]
    source_ids=list(dict.fromkeys([*state.get('sources',{}),*(i.get('source_id','') for i in visible)]))
    sources=[]
    for sid in source_ids:
        src=state.get('sources',{}).get(sid,{})
        rows=[i for i in visible if i.get('source_id','')==sid]
        end=[i for i in rows if valid_day(i.get('deadline')) and not i.get('registration_ambiguous')]
        exact=[i for i in end if exact_instant(i,'deadline')]
        confirmed_both=sum(bool(valid_day(i.get('registration_start'))) for i in end)
        reasons=Counter(reason_for(i) for i in rows)
        samples=[]
        for i in sorted(rows,key=lambda i:(reason_for(i) in ('confirmed','partial_date'),str(i.get('last_changed',''))),reverse=False)[:8]:
            samples.append({'id':i.get('id'),'title':str(i.get('title',''))[:220],'url':canonical(i.get('url','')),
                'reason':reason_for(i),'label':REASONS.get(reason_for(i),'접근 상태 확인'),
                'last_attempted_at':i.get('detail_attempted_at'),'parser_version':i.get('date_parser_version'),
                'text_length':i.get('detail_text_length'),'evidence_hash':i.get('detail_content_hash'),
                'trace':[{k:step[k] for k in ('stage','outcome','code','text_length','elapsed_ms') if k in step}
                         for step in i.get('detail_trace',[])[:8] if isinstance(step,dict)]})
        sources.append({'id':sid,'name':src.get('name',sid),'status':src.get('status','unknown'),
            'checked_at':src.get('checked_at'),'denominator':len(rows),'deadline_known':len(end),
            'start_and_end_known':confirmed_both,'deadline_time_known':len(exact),
            'attempted_this_run':sum(bool(state.get('updated_at')) and i.get('detail_attempted_at')==state.get('updated_at') for i in rows),
            'deadline_confirmed_this_run':sum(bool(state.get('updated_at')) and i.get('detail_attempted_at')==state.get('updated_at') and any(t.get('stage')=='date_parse' and t.get('outcome')=='ok' for t in i.get('detail_trace',[])) for i in rows),
            'manual_count':sum(bool(i.get('manual_correction')) for i in rows),
            'automatic_deadline_known':sum(bool(valid_day((i.get('_automatic_dates',{}) if i.get('manual_correction') else i).get('deadline'))) and not (i.get('_automatic_dates',{}) if i.get('manual_correction') else i).get('registration_ambiguous') for i in rows),
            'deadline_coverage':round(100*len(end)/len(rows),1) if rows else None,
            'reasons':dict(reasons),'samples':samples})
    total=len(visible);known=sum(s['deadline_known'] for s in sources)
    return {'version':1,'generated_at':as_local(now).isoformat(),'observation_at':state.get('updated_at'),
        'basis':'저장된 AI·데이터 관련 공고 주소 기준(마감 포함). 관리자 보정 포함 여부를 구분하며, 목록 접근 성공과 날짜 추출 성공은 별개입니다.',
        'manual_count':sum(s['manual_count'] for s in sources),'automatic_deadline_known':sum(s['automatic_deadline_known'] for s in sources),
        'total':total,'deadline_known':known,'deadline_time_known':sum(s['deadline_time_known'] for s in sources),
        'coverage':round(100*known/total,1) if total else None,'sources':sources}

def report_markdown(report:dict)->str:
    lines=['## 날짜 확인 진단',report['basis'],'', '| 출처 | 목록 상태 | 마감 확인 / 대상 | 시각 확인 | 확인율 |','|---|---|---|---|---|']
    for s in report['sources']:
        name=str(s['name']).replace('|','/').replace('\n',' ')
        pct='해당 없음' if s['deadline_coverage'] is None else str(s['deadline_coverage'])+'%'
        lines.append(f"| {name} | {s['status']} | {s['deadline_known']} / {s['denominator']} | {s['deadline_time_known']} | {pct} |")
    lines+=['','접근 실패·동적 화면 미확인·기간 충돌·요청 예산 대기는 site/quality.json에서 구분합니다.','실행한 범위의 진단이며 모든 공고의 완전성을 보증하지 않습니다.']
    return '\n'.join(lines)+'\n'
