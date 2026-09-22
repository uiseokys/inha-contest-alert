"""Evidence-required date corrections. Original automatic values remain recoverable."""
from __future__ import annotations
import copy,hashlib,json,re
from datetime import datetime
from .core import canonical
from .timing import valid_day,exact_instant,as_local
FIELDS=('registration_start','deadline','registration_start_time','deadline_time')
BACKUP=FIELDS+('registration_ambiguous','registration_time_ambiguous','date_status','date_note','date_evidence','date_source_url')

def _hash(value)->str:return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:20]

def validate_config(config:dict,now:datetime)->dict:
    if not isinstance(config,dict) or config.get('version',1)!=1 or not isinstance(config.get('entries',{}),dict):
        raise ValueError('overrides.json은 version:1, entries 객체 형식이어야 합니다.')
    entries=config.get('entries',{})
    if len(entries)>500:raise ValueError('수동 보정은 500개까지 허용합니다.')
    cleaned={}
    for url,entry in entries.items():
        target=canonical(url)
        if not target or not isinstance(entry,dict):raise ValueError('수동 보정의 공고 주소 또는 항목 형식이 잘못되었습니다.')
        evidence=canonical(entry.get('evidence_url',''));checked=entry.get('checked_at','');reason=entry.get('reason','')
        if not evidence or not valid_day(str(checked)[:10]) or str(checked)[:10]>as_local(now).date().isoformat() or not isinstance(reason,str) or not reason.strip():
            raise ValueError('수동 보정에는 유효한 evidence_url, 미래가 아닌 checked_at 날짜, reason이 필요합니다.')
        fields={k:entry[k] for k in FIELDS if k in entry}
        if not fields:raise ValueError('수동 보정에 날짜 또는 시각 필드가 필요합니다.')
        for k in ('registration_start','deadline'):
            if k in fields and fields[k] is not None and not valid_day(fields[k]):raise ValueError('수동 보정 날짜는 YYYY-MM-DD 형식이어야 합니다.')
        for k in ('registration_start_time','deadline_time'):
            v=fields.get(k)
            if v is not None and (not isinstance(v,str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d|24:00',v)):
                raise ValueError('수동 보정 시각은 유효한 HH:MM 형식이어야 합니다.')
        cleaned[target]={**fields,'evidence_url':evidence,'checked_at':str(checked)[:10],'reason':reason.strip()[:300]}
    return cleaned

def restore_automatic_dates(state:dict)->None:
    for item in state.get('items',{}).values():
        old=item.pop('_automatic_dates',None)
        if isinstance(old,dict):
            for key in BACKUP:
                if key in old:item[key]=old[key]
                else:item.pop(key,None)
        item.pop('manual_correction',None)

def apply_corrections(state:dict,config:dict,now:datetime)->None:
    entries=validate_config(config,now);restore_automatic_dates(state)
    tracking=state.setdefault('correction_tracking',{})
    for rid,item in state.get('items',{}).items():
        entry=entries.get(canonical(item.get('url','')))
        if not entry:continue
        before={k:copy.deepcopy(item[k]) for k in BACKUP if k in item}
        combined=dict(item,**{k:entry[k] for k in FIELDS if k in entry})
        # A corrected date must not inherit the previous date's time by accident.
        for day,clock in [('deadline','deadline_time'),('registration_start','registration_start_time')]:
            if day in entry and entry[day]!=item.get(day) and clock not in entry:combined[clock]=None
            if combined.get(clock) and not combined.get(day):raise ValueError('보정 시각에는 해당 날짜도 필요합니다.')
        st,en=combined.get('registration_start'),combined.get('deadline')
        if st and en and st>en:raise ValueError('접수 시작일이 마감일보다 늦은 보정은 적용할 수 없습니다.')
        combined['registration_ambiguous']=combined['registration_time_ambiguous']=False
        a,b=exact_instant(combined,'registration_start'),exact_instant(combined,'deadline')
        if a and b and a>b:raise ValueError('접수 시작 시각이 마감 시각보다 늦습니다.')
        key=rid+':'+_hash(entry);signature=_hash({k:before.get(k) for k in FIELDS})
        tracking.setdefault(key,{'automatic_signature':signature,'first_applied_at':as_local(now).isoformat()})
        changed=tracking[key]['automatic_signature']!=signature and str(item.get('detail_checked_at',''))[:10]>=entry['checked_at']
        item.update({k:combined.get(k) for k in FIELDS})
        item.update(_automatic_dates=before,registration_ambiguous=False,registration_time_ambiguous=False,
            manual_correction={'evidence_url':entry['evidence_url'],'checked_at':entry['checked_at'],'reason':entry['reason'],'needs_review':bool(changed)},
            date_source_url=entry['evidence_url'],date_evidence=entry['reason'],
            date_note='관리자 근거 확인 보정'+(' · 자동 수집 내용이 달라져 재검토 필요' if changed else ''),
            date_status='manual')
