"""Evidence-based public notice extraction; no guessed clock year or private API."""
from __future__ import annotations
import json,re
from datetime import date
from urllib.parse import urljoin,urlsplit,urlunsplit
from bs4 import BeautifulSoup
from .core import DATE,dates,canonical,clean_title,generic_title

from .extraction import normalize_text,reorder_timeline,structured_registration,time_value

PARSER_VERSION=6
LABELS={
 'registration':r'참가\s*접수(?=\s*(?:[:：]|\n|20\d{2}|$))|(?:(?:접수|신청|모집|응모)\s*)?마감\s*일\s*시|(?:접수|신청|모집)\s*(?:시작|종료)\s*일\s*시|(?:(?:참가|참여|작품|참가자)\s*)?(?:접수|신청|모집|응모|공모|지원)\s*(?:기간|일정|기한|시작(?:일)?|개시(?:일)?|종료(?:일)?|마감(?:일)?)|(?:참가|참여)\s*기간|(?:접수|응모|공모|신청)(?=\s*[:：])|(?:registration|application|submission)\s*(?:period|deadline|opens?|closes?|start(?:s| date)?|end(?:s| date)?)',
 'event':r'(?:대회|행사|본선|해커톤|활동|개최)\s*(?:기간|일시|일정|일자)|event\s*(?:dates?|period)',
 'organizer':r'주최\s*[/·ㆍ및]+\s*주관|주최(?:\s*기관)?|주관(?:\s*기관)?',
 'eligibility':r'대상(?=\s*[:：])|참가\s*(?:대상|자격)|참여\s*(?:대상|자격)|지원\s*(?:대상|자격)|신청\s*자격|응모\s*(?:대상|자격)|모집\s*대상',
 'benefits':r'상금\s*(?:및|/|·)\s*혜택|시상\s*(?:내역|내용|규모)|총\s*상금|상금|혜택',
 'summary':r'참여\s*주제|프로그램\s*(?:주제|내용)|공모\s*주제|대회\s*주제|공모\s*내용|주제|주요\s*내용',
 'schedule':r'상세\s*일정|진행\s*일정|주요\s*일정|추진\s*일정|세부\s*일정',
 'stop':r'참가자\s*수|조회\s*수|소개(?=\s*(?:\n|$))|(?:팀\s*병합|팀명\s*변경)\s*기간|평가\s*방법|평가\s*기준|동의사항|참가\s*방법|대회명|신청\s*안내|담당자|선발\s*결과|결과\s*발표|학습\s*데이터셋\s*공개|코드\s*제출|순위\s*발표|접수처|(?:공식\s*)?홈페이지|참가\s*신청(?=\s*[:：])|공식\s*사이트|신청\s*방법|접수\s*방법|문의(?:처)?|유의\s*사항|첨부\s*파일|발표\s*일시|심사\s*(?:기간|일정)|팀\s*병합\s*마감|(?:소스\s*코드|리더보드|결과물|보고서|작품|2차\s*평가\s*자료)\s*제출(?:\s*마감)?|최종\s*(?:순위|결과)\s*발표|시상식|대회\s*(?:종료|시작)|운영|설명|대회\s*설명',
}
LABEL_RE=re.compile(r'(?<![가-힣A-Za-z0-9])(?:'+'|'.join('(?P<'+k+'>'+v+')' for k,v in LABELS.items())+r')(?=\s|[:：]|$)[ \t]*[:：]?[ \t]*',re.I)
SHORT=re.compile(r'(?<![\d./-])(\d{1,2})\s*[./월-]\s*(\d{1,2})\s*(?:일)?(?!\d)')
RANGE=re.compile(r'[~～∼–—]|\s-\s|\bto\b|부터',re.I)


def compact(text: str,limit: int=240)->str:
    text=re.sub(r'\s+',' ',text).strip(' \t\n:：•·○■□●-')
    return text[:limit]+('…' if len(text)>limit else '')


def entries(text:str)->list[tuple[str,str,str]]:
    text=normalize_text(text)
    text=re.sub(r'[\[【]([^\]\n】]{1,40})[\]】]',r' \1 ',text)
    matches=[];out=[]
    for m in LABEL_RE.finditer(text):
        label=m.group(m.lastgroup)
        before=text[text.rfind('\n',0,m.start())+1:m.start()].strip(' \t•·○■□●*-0123456789.)')
        after=text[m.end():]
        if m.lastgroup in ('organizer','benefits','summary','event','eligibility'):
            # A field is a heading or a colon-labelled value, not prose such as
            # '주최 측', '상금 지급', or '대회 기간 중에는'.
            if before and not re.search(r'[:：]',m.group()):continue
            if re.match(r'(?:측|자(?:는|의|에게)|중(?:에|에는)?|동안|지급(?:과|을)?|환수|취소|관련|안내)(?:\s|$)',after):continue
        if m.lastgroup=='registration' and re.fullmatch(r'접수|신청|응모|공모',label):
            first=after.split('\n',1)[0]
            if not DATE.search(first) and not SHORT.search(first) and not re.match(r'^[~～∼]',first):continue
        matches.append(m)
    for idx,m in enumerate(matches):
        if m.lastgroup=='stop':continue
        end=matches[idx+1].start() if idx+1<len(matches) else len(text)
        raw=text[m.end():end].strip()
        raw=re.split(r'\n\s*\n',raw,maxsplit=1)[0]
        # Drop prose after a line break, but retain split dates and range tokens.
        raw=re.split(r'\n\s*(?:※|\*|•|○|■|□|-(?=\s*[가-힣A-Za-z])|\d+[.)](?=\s*[가-힣A-Za-z]))\s*(?!\d)',raw,maxsplit=1)[0]
        if m.lastgroup in ('organizer','benefits','eligibility','summary'):
            raw=re.split(r'\n(?:평가|동의|규칙|참가 방법|제출|문의|주의|유의|개요|일정|진행 방식|첨부)(?:[^\n]{0,35})(?:\n|$)',raw,maxsplit=1)[0]
        value=compact(raw,400)
        if not re.search(r'[가-힣A-Za-z0-9]',value):continue
        if m.lastgroup=='benefits' and re.fullmatch(r'총\s*상금',m.group('benefits')) and value:value='총상금 '+value
        if value:out.append((m.lastgroup,m.group(m.lastgroup),value))
    return out


def fields_from_text(text:str)->dict[str,list[str]]:
    out={}
    for kind,label,value in entries(text):
        if value not in out.setdefault(kind,[]):out[kind].append(value)
    return out


def date_tokens(text:str,reference_year:int|None=None)->list[str|None]:
    """Only complete dates or short dates tied to an explicit same-page year."""
    text=normalize_text(text)
    full=list(DATE.finditer(text));tokens=[]
    year=reference_year
    years={int(m[1]) for m in full}
    if len(years)==1:year=next(iter(years))
    for m in full:
        try:value=date(*map(int,m.groups())).isoformat()
        except ValueError:value=None
        tokens.append((m.start(),value))
    for m in SHORT.finditer(text):
        if any(m.start()<f.end() and m.end()>f.start() for f in full):continue
        # Do not interpret numerical sizes or times; short forms require year.
        if year is None:continue
        try:value=date(year,int(m[1]),int(m[2])).isoformat()
        except ValueError:value=None
        tokens.append((m.start(),value))
    return [x[1] for x in sorted(tokens)]


def date_range(text:str,allow_single:bool=False,reference_year:int|None=None)->tuple[str|None,str|None]:
    ds=date_tokens(text,reference_year)
    if len(ds)==2 and all(ds) and ds[0]<=ds[1]:return ds[0],ds[1]
    if len(ds)==1 and ds[0] and allow_single and not RANGE.search(text):return ds[0],ds[0]
    return None,None


def registration_from_text(text:str,reference_year:int|None=None)->tuple[str|None,str|None]:
    found=[(label,v) for k,label,v in entries(text) if k=='registration']
    periods=set();starts=set();ends=set();unresolved=False
    for label,value in dict.fromkeys(found):
        pair=date_range(value,reference_year=reference_year)
        if pair!=(None,None):periods.add(pair);continue
        ds=date_tokens(value,reference_year)
        if len(ds)==1 and ds[0]:
            if re.search(r'시작|개시|open|start',label,re.I) and not RANGE.search(value):starts.add(ds[0])
            elif re.search(r'마감|종료|기한|deadline|clos|end',label,re.I) and not RANGE.search(value):ends.add(ds[0])
            elif ('까지' in value and not RANGE.search(value)) or re.match(r'^[~～∼]',value):ends.add(ds[0])
            else:unresolved=True
        else:unresolved=True
    if len(periods)>1 or len(starts)>1 or len(ends)>1:return None,None
    if periods:
        start,end=next(iter(periods))
        if (starts and starts!={start}) or (ends and ends!={end}):return None,None
        # Unresolved yearless duplicates are harmless only when identical to the
        # resolved explicit period. Otherwise never choose an arbitrary track.
        if unresolved:return None,None
        return start,end
    start=next(iter(starts),None);end=next(iter(ends),None)
    if unresolved or (start and end and start>end):return None,None
    return start,end


def registration_times(text:str,reference_year:int|None=None)->dict:
    candidates={'registration_start_time':set(),'deadline_time':set()}
    for kind,label,value in entries(text):
        if kind!='registration':continue
        value=normalize_text(value)
        full=list(DATE.finditer(value))
        short=[m for m in SHORT.finditer(value) if not any(m.start()<f.end() and m.end()>f.start() for f in full)]
        spans=sorted(full+short,key=lambda m:m.start())
        ds=date_tokens(value,reference_year)
        if len(ds)==2 and len(spans)==2 and all(ds):
            st=time_value(value[spans[0].end():spans[1].start()])
            en=time_value(value[spans[1].end():])
            if st:candidates['registration_start_time'].add(st)
            if en:candidates['deadline_time'].add(en)
        elif len(ds)==1 and len(spans)==1:
            t=time_value(value[spans[0].end():])
            if t and re.search(r'마감|종료|기한|deadline|clos|end',label,re.I):candidates['deadline_time'].add(t)
            elif t and re.search(r'시작|개시|open|start',label,re.I):candidates['registration_start_time'].add(t)
    if any(len(values)>1 for values in candidates.values()):
        return {'registration_time_ambiguous':True,'deadline_time':None,'registration_start_time':None}
    return dict({key:next(iter(values)) for key,values in candidates.items() if values},registration_time_ambiguous=False)


def _content(soup:BeautifulSoup,kind:str):
    if kind in ('dacon','aifactory','campuspick'):
        return soup.body or soup.select_one('#__nuxt,#__next,#app') or soup
    for selector in ('.contest-detail','.contest-view','.contest_view','.competition-content','.mb-view-content','.mb-board-view-content','#mb_content','.mb-content', '[id$=\"_content\"].content', '.artclViewBody','.view-content','.view-content-box','.mb-content','.artclView','article','main','#container','.contest-view','.contest_view','.competition-content','.contest-detail'):
        node=soup.select_one(selector)
        if node is not None:return node
    if kind in ('dacon','aifactory','campuspick'):
        return soup.select_one('#__nuxt,#__next,#app') or soup.body
    return None


def _title(soup:BeautifulSoup,content)->str:
    def usable(value):
        value=clean_title(value)
        return value if len(value)>=4 and not generic_title(value) else ''
    # Actual bulletin subject before generic WordPress page headings and OG tags.
    for selector in ('.artclViewTitle','.view-title','.mb-view-title','.mb-board-view-title','.mb-subject','#mb_subject','[itemprop="headline"]','.contest-title'):
        for node in soup.select(selector):
            if value:=usable(node.get_text(' ',strip=True)):return value
    for row in soup.select('tr'):
        cells=row.find_all(['th','td'],recursive=False)
        if len(cells)>=2 and cells[0].get_text(strip=True)=='제목':
            if value:=usable(cells[1].get_text(' ',strip=True)):return value
    # MangBoard often exposes the subject as h3 inside the board form.
    for node in soup.select('h1,h2,h3'):
        if node.find_parent(['nav','header','footer','aside']):continue
        if node.find_parent(class_=re.compile(r'related|recommend|comment',re.I)):continue
        value=usable(node.get_text(' ',strip=True))
        if value and (node.name=='h1' or re.search(r'공모|대회|경진|챌린지|해커톤|프로그램|교육|세미나|AI|데이터',value,re.I)):return value
    node=soup.select_one('meta[property="og:title"]')
    if node:
        if value:=usable(node.get('content','')):return value
    if soup.title:
        value=usable(soup.title.get_text(' ',strip=True))
        if value and re.search(r'공모|경진|챌린지|해커톤|competition|challenge',value,re.I):return value
    return ''


def resource_url(url:str)->str:
    """Validate a public URL without collapsing DACON schedule tabs to identity."""
    if not canonical(url):return ''
    p=urlsplit(url)
    return urlunsplit((p.scheme,p.netloc,p.path,p.query,''))


def schedule_links(html:str,page_url:str)->list[str]:
    """Follow same-event tabs and explicitly linked official platform schedules."""
    soup=BeautifulSoup(html,'html.parser');out=[];host=urlsplit(page_url).hostname
    base=canonical(page_url)
    content=_content(soup,'') or soup
    for a in content.select('a[href]'):
        if a.find_parent(['nav','aside','header','footer']):continue
        if a.find_parent(class_=re.compile(r'recommend|related|prev|next',re.I)):continue
        label=a.get_text(' ',strip=True);url=resource_url(urljoin(page_url,a['href']))
        if not url:continue
        target=urlsplit(url).hostname
        if target!=host:
            # Only directly authored, application-labeled links to known public
            # platforms; never generic websites/search/recommendation links.
            nearby=a.parent.get_text(' ',strip=True)[:600] if a.parent else label
            if not re.search(r'접수처|공식|신청|접수|참가|홈페이지',nearby):continue
            if target in ('dacon.io','www.dacon.io') and re.search(r'/competitions/(?:official|open)/\d+',url):
                m=re.search(r'(/competitions/(?:official|open)/\d+)',urlsplit(url).path)
                url='https://'+target+m[1]+'/overview/schedule'
            elif target in ('aifactory.space','www.aifactory.space') and re.search(r'/competitions/\d+',url):pass
            else:continue
        else:
            if not re.search(r'일정|접수\s*기간|schedule|timeline',label,re.I):continue
            if '/competitions/' in page_url and canonical(url)!=base:continue
            if 'campuspick.com' in (host or '') and canonical(url)!=base:continue
            if re.search(r'calendar|login|member|download',urlsplit(url).path,re.I):continue
        if url!=page_url and url not in out:out.append(url)
    if host in ('dacon.io','www.dacon.io'):
        match=re.match(r'(/competitions/(?:official|open)/\d+)',urlsplit(page_url).path)
        if match:
            known='https://'+host+match[1]+'/overview/schedule'
            if resource_url(page_url).rstrip('/')!=known and known not in out:out.insert(0,known)
    return out[:2]


def _json_events(soup:BeautifulSoup,page_url:str)->list[dict]:
    candidates=[]
    for script in soup.select('script[type="application/ld+json"]'):
        try:data=json.loads(script.string or script.get_text())
        except (TypeError,ValueError):continue
        roots=data if isinstance(data,list) else [data]
        for obj in roots:
            if not isinstance(obj,dict):continue
            nodes=obj.get('@graph',[obj])
            if not isinstance(nodes,list):continue
            for node in nodes:
                if not isinstance(node,dict):continue
                if isinstance(node.get('mainEntity'),dict):node=node['mainEntity']
                typ=node.get('@type','');types=typ if isinstance(typ,list) else [typ]
                if not any(str(t).endswith(('Event','Hackathon')) for t in types):continue
                target=node.get('url') or node.get('mainEntityOfPage')
                if isinstance(target,dict):target=target.get('@id')
                if isinstance(target,str) and canonical(urljoin(page_url,target))!=canonical(page_url):continue
                candidates.append(node)
    # A page containing several event entities is a list, not one detail record.
    return candidates if len(candidates)==1 else []


def title_registration(title:str,page_url:str='')->dict:
    """Parse only a recruitment-labelled title window with its own explicit year."""
    text=normalize_text(title)
    years=set(re.findall(r'(?<!\d)(20\d{2})(?!\d)',text))
    if len(years)!=1:return {}
    year=int(next(iter(years)))
    marker=list(re.finditer(r'참여\s*신청|참가\s*신청|접수|모집|응모|지원',text))
    if not marker:return {}
    tail=text[marker[-1].end():]
    if re.search(r'대회\s*기간|행사\s*기간|교육\s*기간|시험\s*일',tail):return {}
    datepart=r'\d{1,2}\s*[./월]\s*\d{1,2}\s*(?:일|\.)?(?:\s*\([월화수목금토일]\))?'
    found=re.search(r'('+datepart+r')?\s*[~～∼]\s*('+datepart+r')',tail)
    if not found:return {}
    evidence=found.group().strip()
    start,end=registration_from_text('접수기간: '+evidence,year)
    if not end:return {}
    return dict(registration_start=start,deadline=end,registration_text=evidence,
                registration_ambiguous=False,date_status='complete' if start else 'partial',
                date_source_url=resource_url(page_url),date_evidence=title,
                date_note='공고 제목에 명시된 연도와 신청·모집 기간을 확인했습니다.')


def parse_details(html:str,page_url:str='',source_kind:str='',context_title:str='')->dict:
    soup=BeautifulSoup(html,'html.parser');content=_content(soup,source_kind)
    title=_title(soup,content);years=set(re.findall(r'(?<!\d)(20\d{2})(?!\d)',title or context_title))
    reference_year=int(next(iter(years))) if len(years)==1 else None
    out={};texts=[];raw_evidence=[]
    structured=structured_registration(soup,page_url)
    if content is not None:
        for node in content.select('script,style,nav,header,footer,aside,input,button,select,textarea,del,s,.comments,.comment-list,.related,.recommend,.recommendations,.mb-prev-next,.mb-neighbor,.sidebar,.breadcrumbs,.breadcrumb,.post-navigation,.pagination,[role=\"navigation\"],[hidden],[aria-hidden=\"true\"]'):
            node.decompose()
        for node in list(content.find_all(class_=re.compile(r'(?:related|recommend|suggest|breadcrumb|pagination|login-modal)',re.I))):
            if node.parent is not None:node.decompose()
        for block in content.select('p,tr,li,dd'):
            raw=block.get_text(' ',strip=True)
            if len(raw)<700 and any(k=='registration' for k,_,_ in entries(raw)):
                raw_evidence.append(raw)
        reorder_timeline(soup,content)
        # Visible text + authored alternative text; never OCR or read pixels.
        for img in content.select('img[alt]'):
            alt=img.get('alt','')
            if re.search(r'접수|신청|모집|응모',alt) and DATE.search(alt):img.replace_with(alt)
        visible=normalize_text(content.get_text('\n',strip=True))
        if source_kind=='dacon':
            # The summary timeline is date-before-label and often omits years.
            # Its next milestone must not overwrite the explicit period above.
            visible=re.split(r'(?:^|\n)\s*대회\s*주요\s*일정\s*(?:\n|$)',visible,maxsplit=1)[0]
        texts.append(visible)
    for selector in ('meta[property="og:description"]','meta[name="description"]'):
        node=soup.select_one(selector)
        if node and node.get('content'):texts.append(node['content'])
    # Keep text blocks separated, rather than turning metadata into a second track.
    text=texts[0] if texts else ''
    values=fields_from_text(text)
    if not values.get('registration'):
        for extra in texts[1:]:
            if fields_from_text(extra).get('registration'):
                text+='\n'+extra;values=fields_from_text(text);break
    if structured:
        # Explicit registration metadata is parsed together with visible fields.
        # Conflicts stay ambiguous rather than silently overwriting a date.
        text+='\n'+'\n'.join(structured);values=fields_from_text(text)
    if values.get('registration'):
        raw=' / '.join(values['registration']);start,end=registration_from_text(text,reference_year)
        out.update(registration_text=compact(raw,400),registration_start=start,deadline=end,
                   registration_ambiguous=start is None and end is None,
                   date_evidence=compact(raw,400),date_source_url=resource_url(page_url),
                   date_status='complete' if start and end else 'partial' if start or end else 'unconfirmed',date_note='')
        if reference_year and not dates(raw):out['date_note']=f'원문 제목의 {reference_year}년을 기준으로 월·일을 해석했습니다.'
        if start is None and end is None:out['date_note']='날짜 형식·연도·부문별 기간을 확정하지 못했습니다. 원문 확인이 필요합니다.'
    if not values.get('registration'):
        out.update(title_registration(context_title or title,page_url))
    if values.get('event'):
        pairs=list(dict.fromkeys(date_range(v,allow_single=True,reference_year=reference_year) for v in values['event']))
        if len(pairs)==1 and pairs[0]!=(None,None):out['event_start'],out['event_end']=pairs[0]
        out['event_ambiguous']=not bool(out.get('event_end'))
        out['schedule_text']=compact(' / '.join(values['event']),400)
    if values.get('schedule'):out['schedule_text']=compact(' / '.join(values.get('event',[])+values['schedule']),400)
    for name in ('organizer','eligibility','benefits','summary'):
        if values.get(name):out[name]=compact(' / '.join(values[name]),220)
    # JSON-LD Event dates describe the event, NOT the registration window.
    for event in _json_events(BeautifulSoup(html,'html.parser'),page_url):
        for key,target in [('startDate','event_start'),('endDate','event_end')]:
            ds=dates(str(event.get(key,'')))
            if len(ds)==1 and not out.get('event_ambiguous'):out.setdefault(target,ds[0])
        if not title:title=clean_title(event.get('name',''))
        if not out.get('registration_text') and isinstance(event.get('description'),str):
            desc=BeautifulSoup(event['description'],'html.parser').get_text('\n')
            a,b=registration_from_text(desc,reference_year)
            if a or b:out.update(registration_start=a,deadline=b,registration_ambiguous=False,registration_text=compact(desc,400),date_evidence=compact(desc,400),date_source_url=resource_url(page_url),date_status='complete' if a and b else 'partial')
    if out.get('event_start') and out.get('event_end') and out['event_start']>out['event_end']:
        out.update(event_start=None,event_end=None,event_ambiguous=True)
    if content is not None:
        for a in content.select('a[href]'):
            label=a.get_text(' ',strip=True);url=canonical(urljoin(page_url,a.get('href','')))
            if not url or re.match(r'/(?:login|download|linkclick|member)(?:/|$)',urlsplit(url).path):continue
            if re.search(r'(?:참가\s*)?(?:신청|접수|지원)\s*(?:하기|바로가기|사이트|링크|페이지)?$',label):out.setdefault('application_url',url)
            elif re.search(r'공식\s*(?:홈페이지|사이트)|홈페이지|대회\s*(?:사이트|안내)|관련\s*사이트',label):out.setdefault('website_url',url)
    if out.get('date_evidence') and raw_evidence:
        out['date_evidence']=compact(' / '.join(dict.fromkeys(raw_evidence)),400)
        if re.search(r"[’‘'`]\s*\d{2}(?=\s*[.년/-])",out['date_evidence']):
            out['date_note']=(out.get('date_note','')+' 원문의 두 자리 연도 표기를 20YY년으로 정규화했습니다.').strip()
    if structured and out.get('deadline'):
        out['date_note']=(out.get('date_note','')+' 해당 공고의 공개 구조화 접수 필드도 확인했습니다. 시간대가 명시된 값은 한국시간으로 변환했습니다.').strip()
    if title:out['detail_title']=title
    if title or re.search(r'AI|데이터|인공지능|통계|머신러닝|딥러닝',text,re.I):out['_topic_text']=text[:12000]
    if out.get('deadline') or out.get('registration_start'):
        out.update(registration_times(text,reference_year))
    if out.get('registration_time_ambiguous'):
        out['date_note']=(out.get('date_note','')+' 접수 시각 표기가 서로 달라 시간을 확정하지 않았습니다.').strip()
    if out and content is not None:out['detail_parser_version']=PARSER_VERSION
    if out and page_url:out['detail_source_url']=canonical(page_url)
    return out
