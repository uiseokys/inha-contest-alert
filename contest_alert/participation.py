"""Explicit participation evidence; not an automated legal eligibility decision."""
from __future__ import annotations
import re
from .timing import valid_day

def conditions(text:str)->dict:
    lines=[re.sub(r'\s+',' ',x).strip() for x in str(text).splitlines() if x.strip()]
    def evidence(pattern):
        for i,line in enumerate(lines):
            if re.match(pattern,line):
                return (line+(' '+lines[i+1] if (len(line.split(':')[-1])<2 or re.fullmatch(r'(?:참가|참여|응모|지원|모집)\s*(?:대상|자격)|팀\s*(?:구성|규모|인원)|진행\s*(?:방식|형태)|참가비|교육비|수강료',line)) and i+1<len(lines) else ''))[:280]
        return ''
    audience=evidence(r'(?:참가|참여|응모|지원|모집)\s*(?:대상|자격)\s*[:：]?|대상\s*[:：]')
    team=evidence(r'(?:팀\s*(?:구성|규모|인원)|참가\s*(?:단위|인원|형태))\s*[:：]?') or audience
    mode=evidence(r'(?:진행\s*(?:방식|형태)|참가\s*방식|개최\s*방식)\s*[:：]?')
    cost=evidence(r'(?:참가비|참가\s*비용|접수비|교육비|수강료)\s*[:：]?')
    out={k:{'value':'unknown','evidence':v} for k,v in [('audience',audience),('affiliation',audience),('team',team),('mode',mode),('cost',cost)]}
    if audience and not re.search(r'제외|불가|제한|아닌|외에는',audience):
        levels=[]
        if re.search(r'대학생|학부생',audience):levels.append('undergraduate')
        if '대학원생' in audience:levels.append('graduate')
        if re.search(r'일반인|누구나|전\s*국민|제한\s*없',audience):levels.append('general')
        if re.search(r'누구나|전\s*국민|제한\s*없',audience):levels=['undergraduate','graduate','general']
        if levels:out['audience']['value']=levels
        if re.search(r'인하대(?:학교)?\s*(?:재학생|학생|구성원|학부|대학원)',audience):out['affiliation']['value']='inha'
        elif re.search(r'누구나|전국|전\s*국민|제한\s*없',audience):out['affiliation']['value']='unrestricted'
    if team and not re.search(r'제외|불가|금지',team):
        individual=bool(re.search(r'개인|1\s*인|1\s*[~∼-]',team));group=bool(re.search(r'팀|[2-9]\s*인',team))
        if individual:out['team']['value']='individual_or_team' if group else 'individual'
        elif group and re.search(r'필수|[2-9]\s*[~∼-]\s*\d+\s*인|[2-9]\s*인\s*(?:이상|팀)',team):out['team']['value']='team_required'
    if mode:
        online='온라인' in mode or '비대면' in mode;offline='오프라인' in mode or '현장' in mode or bool(re.search(r'(?<!비)대면',mode))
        if online or offline:out['mode']['value']='hybrid' if online and offline else 'online' if online else 'onsite'
    if cost:
        if re.search(r'무료|없음|\b0\s*원',cost) and not re.search(r'유료|\d+[1-9]\d*\s*원|[1-9]\d*\s*만원',cost):out['cost']['value']='free'
        elif re.search(r'유료|[1-9][\d,]*\s*(?:만\s*)?원',cost) and '무료' not in cost:out['cost']['value']='paid'
    return out

def milestones(text:str,title:str='',url:str='')->list[dict]:
    from .details import date_tokens
    from .extraction import time_value
    years=set(re.findall(r'\b(20\d{2})\b',title));year=int(next(iter(years))) if len(years)==1 else None
    labels=r'(?:결과물|제안서|보고서|작품|코드|소스\s*코드)\s*제출\s*(?:마감|기한|기간)|(?:본선|결과\s*발표|시상식)\s*(?:일시|일정|일자)'
    out=[];lines=str(text).splitlines()
    for idx,line in enumerate(lines):
        m=re.search(labels,line)
        if not m:continue
        body=line[m.end():].strip(' :：')
        if not re.search(r'\d',body) and idx+1<len(lines):body+=' '+lines[idx+1]
        days=[d for d in date_tokens(body,year) if d]
        if len(set(days))!=1:continue
        clock=re.search(r'(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)',body)
        item={'kind':'submission' if '제출' in m.group() else 'event','label':m.group(),'date':days[0],'time':f'{int(clock[1]):02d}:{clock[2]}' if clock else None,'evidence':line[:350],'source_url':url}
        if item not in out:out.append(item)
    return out[:12]
