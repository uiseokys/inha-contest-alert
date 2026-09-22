"""Non-destructive cleanup of observed v5 records and URL aliases.

Never delete item IDs, notification claims or stored observation history.
"""
from __future__ import annotations
import re
from collections import defaultdict
from .core import canonical,preferred_title
from .details import title_registration


def sanitize_fields(item:dict)->None:
    organizer=item.get('organizer') or ''
    if re.match(r'^(?:측|자는|자의)\b',organizer) or re.search(r'책임을?\s*부담|제3자에게|리더보드|디버그|제출물|손해(?:에\s*대해|를|배상)',organizer):
        item.pop('organizer',None)
    benefits=item.get('benefits') or ''
    if re.match(r'^(?:지급과|지급을|환수|반환|취소)',benefits) or ('라이선스' in benefits and not re.search(r'\d[\d,]*\s*(?:만\s*)?원',benefits)):
        item.pop('benefits',None)
    if item.get('schedule_text') and re.search(r'Public\s*점수|Private\s*점수|리더보드에\s*실시간',item['schedule_text']):
        item.pop('schedule_text',None)
    if not item.get('deadline') and not item.get('registration_ambiguous'):
        item.update(title_registration(preferred_title(item),item.get('url','')))


def reconcile_identities(state:dict)->None:
    grouped=defaultdict(list)
    for rid,item in state.get('items',{}).items():
        key=canonical(item.get('url',''))
        if key:grouped[key].append((rid,item))
    aliases={}
    for key,rows in grouped.items():
        # Prefer the existing canonical URL row, otherwise reuse the oldest ID.
        rows.sort(key=lambda pair:(pair[1].get('url')!=key,pair[1].get('first_seen',''),pair[0]))
        primary,record=rows[0]
        record['url']=key;record.pop('duplicate_of',None)
        for rid,other in rows[1:]:
            other['duplicate_of']=primary;aliases[rid]=primary
    state['identity_aliases']=aliases


def reuse_existing_ids(records:list[dict],state:dict)->None:
    identities={canonical(x.get('url','')):rid for rid,x in state.get('items',{}).items() if not x.get('duplicate_of')}
    for record in records:
        if rid:=identities.get(canonical(record.get('url',''))):record['id']=rid
