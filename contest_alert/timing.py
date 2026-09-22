"""Registration status in Korea time. Unknown clock times are never invented."""
from __future__ import annotations
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
import re
KST = ZoneInfo('Asia/Seoul')

def as_local(value: datetime | date) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError('시간대가 있는 시각을 사용하세요.')
        return value.astimezone(KST)
    return datetime.combine(value, time.min, tzinfo=KST)

def valid_day(value) -> date | None:
    try:
        if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):return None
        return date.fromisoformat(value)
    except ValueError:return None

def exact_instant(item: dict, field: str) -> datetime | None:
    day = valid_day(item.get(field))
    clock = item.get('deadline_time' if field=='deadline' else 'registration_start_time')
    if not day or item.get('registration_time_ambiguous') or not isinstance(clock,str):return None
    if not re.fullmatch(r'\d{2}:\d{2}(?::\d{2})?',clock):return None
    # Existing sources are Korean; an explicitly unknown/non-Korean timezone is
    # not silently treated as Korean. Store an IANA timezone when known.
    zone = item.get('registration_timezone','Asia/Seoul')
    try:
        if clock in ('24:00','24:00:00'):return datetime.combine(day+timedelta(days=1),time.min,tzinfo=ZoneInfo(zone)).astimezone(KST)
        return datetime.combine(day,time.fromisoformat(clock),tzinfo=ZoneInfo(zone)).astimezone(KST)
    except (ValueError,KeyError,TypeError):return None

def status_at(item: dict, now: datetime | date) -> str:
    local=as_local(now);today=local.date()
    end=valid_day(item.get('deadline'));start=valid_day(item.get('registration_start'))
    if item.get('registration_ambiguous'):end=start=None
    ending=exact_instant(item,'deadline') if end else None
    starting=exact_instant(item,'registration_start') if start else None
    if item.get('platform_status')=='closed':return 'closed'
    if end and (local>=ending if ending is not None else end<today):return 'closed'
    if start and (local<starting if starting is not None else start>today):return 'upcoming'
    if end:return 'active'
    seen=valid_day(str(item.get('last_seen',''))[:10])
    if item.get('platform_status')=='open' and seen and today-timedelta(days=3)<=seen<=today:return 'active'
    return 'unknown'

def timing_label(item:dict,now:datetime|date)->str:
    status=status_at(item,now)
    if status=='closed':return '마감 / 종료'
    if status=='upcoming':return '접수 예정'
    if status=='unknown':return '마감 미확인'
    end=valid_day(item.get('deadline'))
    if end==as_local(now).date() and exact_instant(item,'deadline') is None:return '오늘 마감 · 시각 미확인'
    return '기한 남음' if end else '접수중 표시 · 마감 확인 필요'
