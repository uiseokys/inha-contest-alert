"""Small helpers for authored HTML dates and explicit public JSON fields.
No remote API discovery, JavaScript evaluation, OCR or guessed current year.
"""
from __future__ import annotations
import json,re
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import parse_qs,urlsplit
from .core import DATE

FIELD_WORDS=('접수기간','신청기간','모집기간','응모기간','공모기간','접수마감','신청마감','마감일시',
             '대회기간','행사기간','참가기간','주최','주관','주제','대상','문의','접수처','일정')

def normalize_text(text:str)->str:
    text=text.replace('\u00a0',' ').replace('\u200b','')
    # Korean authored headings are sometimes spaced letter by letter.
    for word in FIELD_WORDS:
        pattern=r'(?<![가-힣])'+r'[ \t]*'.join(map(re.escape,word))+r'(?![가-힣])'
        text=re.sub(pattern,word,text)
    text=re.sub(r'오\s+전','오전',text);text=re.sub(r'오\s+후','오후',text)
    text=re.sub(r"[’‘'`]\s*(\d{2})(?=\s*[.년/-]\s*\d)",lambda m:'20'+m[1],text)
    return text


def reorder_timeline(soup,content)->None:
    if content is None:return
    for row in list(content.select('tr,li')):
        cells=row.find_all(['th','td','span'],recursive=False)
        if len(cells)!=2:continue
        a=normalize_text(cells[0].get_text(' ',strip=True));b=normalize_text(cells[1].get_text(' ',strip=True))
        if DATE.search(a) and not DATE.search(b) and len(b)<40 and re.search(r'접수|신청|마감|결과|발표|시작|종료|심사',b):
            tag=soup.new_tag('p');tag.string=b+': '+a;row.replace_with(tag)


def _iso_local(value)->str:
    text=str(value)
    try:
        dt=datetime.fromisoformat(text.replace('Z','+00:00'))
        if dt.tzinfo: return dt.astimezone(ZoneInfo('Asia/Seoul')).isoformat()
    except ValueError:pass
    return text


def structured_registration(soup,page_url:str)->list[str]:
    """Use only explicitly registration-labeled fields bound to this notice.

    Event endDate, datePublished and arbitrary first objects are NOT deadlines.
    Recommendation arrays and dictionaries for different notice IDs are ignored.
    """
    aliases={}
    for prefix in ('registration','application','apply','receipt','recruit','recruitment','entry','submission'):
        for suffix in ('start','startdate','startat','begindate','openat','startdatetime'):
            aliases[prefix+suffix]='접수 시작일'
        for suffix in ('end','enddate','endat','deadline','closedate','closeat','enddatetime'):
            aliases[prefix+suffix]='접수 마감일'
    parts=urlsplit(page_url);q=parse_qs(parts.query)
    expected=next((q[k][0] for k in ('id','vid','board_pid') if q.get(k)),None)
    m=re.search(r'/competitions/(?:official/|open/)?(\d+)',parts.path)
    if m:expected=m[1]
    candidates=[]
    def walk(obj,depth=0):
        if depth>12:return
        if isinstance(obj,list):
            for child in obj[:100]:walk(child,depth+1)
        if not isinstance(obj,dict):return
        identity=next((str(obj[k]) for k in ('id','contestId','competitionId','vid','board_pid') if isinstance(obj.get(k),(str,int))),None)
        if expected and identity and identity!=expected:return
        fields=[]
        for key,val in obj.items():
            norm=re.sub(r'[^a-z]','',key.lower())
            if norm in aliases and isinstance(val,str) and DATE.search(val):
                fields.append(aliases[norm]+': '+_iso_local(val))
        if fields:candidates.append(tuple(sorted(fields)))
        for key,val in obj.items():
            if re.search(r'recommend|related|suggest|other|similar',key,re.I):continue
            if isinstance(val,(dict,list)):walk(val,depth+1)
    for script in soup.select('script[type="application/json"],script[type="application/ld+json"]'):
        if len(script.get_text())>2_000_000:continue
        try:walk(json.loads(script.string or script.get_text()))
        except (TypeError,ValueError,RecursionError):continue
    attr_fields=[]
    for attr,label in [('data-registration-start','접수 시작일'),('data-registration-end','접수 마감일'),('data-registration-deadline','접수 마감일')]:
        for node in soup.select('['+attr+']'):
            if node.find_parent(class_=re.compile(r'recommend|related',re.I)):continue
            if expected and node.get('data-contest-id') and node['data-contest-id']!=expected:continue
            value=node.get(attr,'')
            if DATE.search(value):attr_fields.append(label+': '+_iso_local(value))
    if attr_fields:candidates.append(tuple(sorted(attr_fields)))
    unique=list(dict.fromkeys(candidates))
    # Multiple disagreeing metadata objects do not describe one confident window.
    return list(unique[0]) if len(unique)==1 else []


def time_value(text:str)->str|None:
    m=re.search(r'(?:(오전|오후|AM|PM)\s*)?(?<!\d)(\d{1,2})\s*(?::\s*(\d{2})|시\s*(?:(\d{1,2})\s*분)?)(?!\d)',text,re.I)
    if not m:return None
    hour=int(m[2]);minute=int(m[3] or m[4] or 0);period=(m[1] or '').lower()
    if minute>59 or hour>24:return None
    if period:
        if not 1<=hour<=12:return None
        hour=hour%12+(12 if period in ('오후','pm') else 0)
    if hour==24 and minute!=0:return None
    return f'{hour:02d}:{minute:02d}'
