"""Pure parsing and state logic. No network access, no secrets."""
from __future__ import annotations
import base64
import hashlib
import re
from datetime import date, datetime, timedelta
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit, unquote
from bs4 import BeautifulSoup

DATE = re.compile(r'(?<!\d)(20\d{2})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})\s*(?:일)?(?!\d)')
CONTEST = re.compile(r'공모|경진|해커톤|데이터톤|아이디어톤|챌린지|콘테스트|캡스톤|competition|hackathon|challenge|contest|awards',re.I)
AI = re.compile(r'인공\s*지능|데이터|빅데이터|통계|머신\s*러닝|딥\s*러닝|컴퓨터\s*비전|자연어|(?<![A-Za-z0-9])(?:ai|aiot|ml|llm|rag|data|machine learning|deep learning)(?![A-Za-z0-9])',re.I)
EXCLUDE = re.compile(r'수상\s*(?:소식|결과|실적)|입상\s*소식|수상자\s*발표|수상팀\s*발표|수강신청|정규\s*수업',re.I)
PATTERNS = {
    'k2web': r'/bbs/[^/]+/\d+/\d+/artclView\.do',
    'mangboard': r'[?&](?:vid|board_pid)=\d+',
    'dacon': r'/competitions/(?:official|open)/\d+',
    'campuspick': r'/contest/view\?(?:[^#]*&)?id=\d+(?:&|$)',
    'aifactory': r'/(?:ko/)?competitions/\d+',
}
DETAIL_FIELDS = ('detail_title','title_raw','date_source_url','date_evidence','date_note','date_parser_version','date_status','deadline','registration_start','registration_text','registration_ambiguous',
                 'event_start','event_end','event_ambiguous','schedule_text','organizer','eligibility',
                 'benefits','summary','website_url','application_url','detail_source_url',
                 'detail_checked_at','detail_attempted_at','detail_status')
PERSIST = ('id','title','url','source_id','source_name','group','posted_at','platform_status') + DETAIL_FIELDS
CHANGE_FIELDS = ('title','deadline','registration_start','platform_status','registration_text',
                 'event_start','event_end','schedule_text','organizer','eligibility','benefits',
                 'summary','website_url','application_url','registration_ambiguous','event_ambiguous')


def canonical(url: str) -> str:
    """Keep identity query params, remove session/tracking/presentation params."""
    try:
        if not isinstance(url,str) or re.search(r'[\x00-\x20<>"\\]',url.strip()):return ''
        p=urlsplit(url.strip())
        if p.scheme not in ('http','https') or not p.hostname or p.username or p.password:
            return ''
        pairs=parse_qsl(p.query,keep_blank_values=True)
        # K2web may wrap an article URL in a base64 `enc` value.
        for k,v in pairs:
            if k=='enc':
                try:
                    decoded=base64.b64decode(v+'='*(-len(v)%4)).decode()
                    inner=unquote(decoded.split('|@@|')[-1])
                    if '/bbs/' in inner and 'artclView.do' in inner:
                        return canonical(urljoin(url,inner))
                except (ValueError,UnicodeError):
                    pass
        drop={'jsessionid','utm_source','utm_medium','utm_campaign','utm_term','utm_content','fbclid','gclid','mode'}
        kept=sorted((k,v) for k,v in pairs if k.lower() not in drop and not k.lower().startswith('utm_'))
        path=re.sub(r';jsessionid=[^/?;]*','',p.path,flags=re.I) or '/'
        # Different navigation tabs of the same DACON event share one identity.
        m=re.match(r'(/competitions/(?:official|open)/\d+)',path)
        if m:path=m.group(1)+'/overview/'
        return urlunsplit((p.scheme.lower(),p.netloc.lower(),path,urlencode(kept),''))
    except ValueError:
        return ''


def dates(text: str) -> list[str]:
    result=[]
    for m in DATE.finditer(text):
        try:result.append(date(*map(int,m.groups())).isoformat())
        except ValueError:pass
    return result


def registration_dates(text: str) -> tuple[str|None,str|None]:
    """Only explicitly labeled dates; never infer a year from the current clock."""
    from .details import registration_from_text
    return registration_from_text(text)


def relevant(title: str, mode: str) -> bool:
    if EXCLUDE.search(title):return False
    if mode=='platform':return True
    if mode=='ai_platform':return bool(AI.search(title))
    return bool(CONTEST.search(title) and (mode!='ai_contest' or AI.search(title)))


def clean_title(text: str) -> str:
    """Remove UI decorations, never summarize or arbitrarily truncate a title."""
    text=re.sub(r'[\u200b-\u200d\ufeff]','',str(text))
    text=re.sub(r'\s+',' ',text).strip()
    text=re.sub(r'^(?:(?:경진대회\s+)?(?:진행중|종료|참가\s*접수중)\s+|\[(?:공지|홍보|모집|NEW)\]\s*)','',text,flags=re.I)
    text=re.sub(r'\s*(?:[|｜]\s*|\s[-–—]\s*)(?:DACON|데이콘|캠퍼스픽|에브리커리어|인공지능팩토리|AI\s*Factory)\s*$','',text,flags=re.I)
    text=re.sub(r'\s+(?:새글|NEW)\s*$','',text,flags=re.I)
    # Counters, dates and tag rows must not become part of the contest name.
    text=re.split(r'\s+(?:알고리즘\s*[|｜]|(?:채용|LG Aimers|SCPC)\s*[|｜]|참가\s*신청중|참가\s*접수중|(?:관심|조회|조회수|스크랩)\s*[:：]?\s*\d|D\s*[-−]\s*\d+(?:\s|$))',text,maxsplit=1,flags=re.I)[0]
    return text.strip()


def listing_title(a) -> str:
    for selector in ('[class~="title"], [class~="subject"], [class*="card-title"], [class*="contest-title"]', 'h1,h2,h3,h4', '[class*="title"],[class*="subject"]', 'strong'):
        node=a.select_one(selector)
        if node and len(node.get_text(' ',strip=True))>=4:
            return clean_title(node.get_text(' ',strip=True))
    lines=[x.strip() for x in a.get_text('\n',strip=True).splitlines() if len(x.strip())>=4]
    # An unstructured card's first non-status text is normally the title.
    lines=[x for x in lines if not re.fullmatch(r'(?:접수중|진행중|종료|마감|D[-−]\d+|관심\s*\d+)',x)]
    return clean_title(lines[0] if lines else a.get_text(' ',strip=True))


def parse_listing(html: str, source: dict, page_url: str|None=None) -> tuple[list[dict],int]:
    soup=BeautifulSoup(html,'html.parser')
    base=page_url or source['url']; host=urlsplit(source['url']).hostname
    pattern=re.compile(source.get('link_pattern') or PATTERNS.get(source['kind'],r'/bbs/[^/]+/\d+/\d+/artclView\.do'))
    found={}
    relevance_text={}
    for a in soup.select(source.get('link_selector','a[href]')):
        href=a.get('href','')
        url=canonical(urljoin(base,href))
        if not url or urlsplit(url).hostname!=host or not pattern.search(url):continue
        title=listing_title(a)
        if source['kind'] in ('dacon','aifactory'):
            # A card without a dedicated title node can include changing counters.
            title=re.split(r'\s+(?:알고리즘\s*\||참가신청중|참가\s*접수중|마감\s+\d|연습\s+\d)',title,maxsplit=1)[0]
            title=re.split(r'\s+20\d{2}[./-]\d{1,2}[./-]\d{1,2}\s*[-~]',title,maxsplit=1)[0]
            title=re.sub(r'\s+\d[\d,]*\s*명\s*$','',title).strip()
        if len(title)<4:continue
        # Rows provide bulletin dates without reading unrelated headers/footers.
        row=a.find_parent('tr') or a.find_parent('li') or a
        rowtext=row.get_text(' ',strip=True)
        ds=dates(rowtext)
        posted=ds[-1] if ds and source['kind'] in ('k2web','mangboard') else None
        status=None
        if source['kind'] in ('dacon','aifactory'):
            if re.search(r'참가\s*(?:신청|접수)\s*중|접수중|모집중',rowtext):status='open'
            elif re.search(r'접수\s*마감|경진대회\s*종료|\s마감\s|\s연습\s',rowtext):status='closed'
        start,deadline=registration_dates(rowtext)
        item={'id':hashlib.sha256(url.encode()).hexdigest()[:20], 'url':url,'title':title,
              'title_raw':title, 'source_id':source['id'],'source_name':source['name'],'group':source.get('group','external'),
              'posted_at':posted,'deadline':deadline,'registration_start':start,'platform_status':status}
        found[url]=item
        relevance_text[url]=(title+' '+rowtext) if source['kind']=='campuspick' else title
    selected=[i for i in found.values() if relevant(relevance_text[i['url']],source.get('mode','contest'))]
    return selected,len(found)


def detail_fields(html: str, page_url: str = '', source_kind: str = '') -> dict:
    from .details import parse_details
    return parse_details(html,page_url,source_kind)


def empty_state() -> dict:
    return {'version':1,'updated_at':None,'items':{},'sources':{},'claims':{},'changes':[],'initialized_sources':[]}


def merge_items(state: dict, records: list[dict], now: datetime) -> None:
    stamp=now.isoformat(); initialized=set(state.get('initialized_sources',[]))
    for record in records:
        rid=record['id']; old=state['items'].get(rid)
        item={k:record[k] for k in PERSIST if k in record}
        if old:
            for k in DETAIL_FIELDS + ('posted_at',):
                if k=='date_note' and k in record:continue
                if k not in item or item[k] is None or item[k]=='':
                    if k in old:item[k]=old[k]
            if record.get('registration_ambiguous'):
                item['deadline']=item['registration_start']=None
            if record.get('event_ambiguous'):
                item['event_start']=item['event_end']=None
            item['title']=clean_title(item.get('detail_title') or item.get('title',''))
            changed=any(item.get(k)!=old.get(k) for k in CHANGE_FIELDS)
            item['first_seen']=old['first_seen']
            item['last_changed']=stamp if changed else old['last_changed']
            if changed:state['changes'].append({'id':rid,'kind':'updated','at':stamp})
        else:
            item['first_seen']=item['last_changed']=stamp
            kind='new' if record['source_id'] in initialized else 'initial'
            state['changes'].append({'id':rid,'kind':kind,'at':stamp})
        item['title']=clean_title(item.get('detail_title') or item.get('title',''))
        item['last_seen']=old['last_seen'] if old and record.get('_preserve_last_seen') else stamp
        state['items'][rid]=item
    state['initialized_sources']=sorted(initialized|{r['source_id'] for r in records})
    state['updated_at']=stamp
    cutoff=(now-timedelta(days=90)).isoformat()
    state['changes']=[x for x in state['changes'] if x['at']>=cutoff]
    # Keep all item identities; retain a year of daily attempts only.
    state['claims']={d:c for d,c in state.get('claims',{}).items() if d>=(now.date()-timedelta(days=370)).isoformat()}


def status_of(item: dict, today: date) -> str:
    deadline=item.get('deadline'); start=item.get('registration_start')
    if deadline and deadline<today.isoformat():return 'closed'
    if start and start>today.isoformat():return 'upcoming'
    if item.get('platform_status')=='closed':return 'closed'
    if deadline:return 'active'  # label is '기한 남음', NOT guaranteed eligibility/open registration.
    seen=item.get('last_seen','')[:10]
    if item.get('platform_status')=='open' and seen and seen>=(today-timedelta(days=3)).isoformat():return 'active'
    return 'unknown'
