"""Conservative, label-based extraction of short public notice information.

No LLM, OCR, login or private API. Missing/ambiguous dates stay unknown.
Text is a short excerpt, not a full mirror of the originating notice.
"""
from __future__ import annotations
import re
from datetime import date
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup
from .core import DATE, dates, canonical

LABELS = {
    'registration': r'(?:참가\s*)?(?:접수|신청|모집)\s*(?:기간|기한|마감(?:일)?)',
    'event': r'(?:대회|행사|본선|해커톤|활동|개최)\s*(?:기간|일시|일정|일자)',
    'organizer': r'주최\s*[/·ㆍ및]+\s*주관|주최(?:\s*기관)?|주관(?:\s*기관)?',
    'eligibility': r'참가\s*(?:대상|자격)|참여\s*(?:대상|자격)|지원\s*(?:대상|자격)|신청\s*자격|응모\s*(?:대상|자격)|모집\s*대상',
    'benefits': r'상금\s*(?:및|/|·)\s*혜택|시상\s*(?:내역|내용|규모)|총\s*상금|상금|혜택',
    'summary': r'공모\s*주제|대회\s*주제|공모\s*내용|주제|주요\s*내용',
    'schedule': r'상세\s*일정|진행\s*일정|주요\s*일정|추진\s*일정',
    # These terminate another field but are not exported as descriptive facts.
    'stop': r'(?:공식\s*)?홈페이지|참가\s*신청|공식\s*사이트|신청\s*방법|접수\s*방법|문의(?:처)?|유의\s*사항|첨부\s*파일|발표\s*일시|심사\s*(?:기간|일정)',
}
LABEL_RE = re.compile(r'(?<![가-힣A-Za-z0-9])(?:' + '|'.join(
    '(?P<'+k+'>'+v+')' for k,v in LABELS.items()) + r')(?=\s|[:：]|$)[ \t]*[:：]?[ \t]*', re.I)


def compact(text: str, limit: int = 240) -> str:
    text = re.sub(r'\s+', ' ', text).strip(' \t\n:：•·○■□●-')
    return text[:limit] + ('…' if len(text)>limit else '')


def fields_from_text(text: str) -> dict[str, list[str]]:
    """Works with labels in adjacent table cells, paragraphs and dt/dd nodes."""
    result: dict[str,list[str]] = {}
    matches = list(LABEL_RE.finditer(text))
    for index, match in enumerate(matches):
        if match.lastgroup == 'stop': continue
        end = matches[index+1].start() if index+1<len(matches) else len(text)
        raw = text[match.end():end].strip()
        # Stop at a blank paragraph. Keep two lines for dt/dd and split dates.
        raw = re.split(r'\n\s*\n',raw,maxsplit=1)[0]
        value = compact(raw, 300)
        if match.lastgroup=='benefits' and re.fullmatch(r'총\s*상금',match.group('benefits')) and value:
            value='총상금 '+value
        if value:
            values=result.setdefault(match.lastgroup,[])
            if value not in values:values.append(value)
    return result


def date_range(text: str, allow_single: bool = False) -> tuple[str|None,str|None]:
    ds=dates(text)
    if len(ds)==2 and ds[0]<=ds[1]:return ds[0],ds[1]
    if len(ds)!=1:return None,None
    first=DATE.search(text)
    tail=text[first.end():] if first else ''
    short=re.search(r'(?:~|～|∼|–|—|\s-\s|부터)\s*(\d{1,2})[./월-]\s*(\d{1,2})(?:일)?(?!\d)',tail)
    if short:
        try:
            end=date(int(ds[0][:4]),int(short[1]),int(short[2])).isoformat()
            # Do not guess the year of a cross-year abbreviated range.
            return (ds[0],end) if end>=ds[0] else (None,None)
        except ValueError:return None,None
    if re.search(r'[~～∼–—]|\s-\s|부터',tail):return None,None
    if allow_single:return ds[0],ds[0]
    return None,None


def registration_from_text(text: str) -> tuple[str|None,str|None]:
    values=fields_from_text(text).get('registration',[])
    candidates=[]
    for value in values:
        pair=date_range(value)
        if pair==(None,None):
            ds=dates(value)
            # A single dated cutoff is allowed only with an explicit cutoff label.
            has_cutoff=bool(re.search(r'(?:접수|신청|모집)\s*(?:마감(?:일)?|기한)',text))
            if len(ds)==1 and (has_cutoff or '까지' in value) and not re.search(r'[~～∼]',value):
                pair=(None,ds[0])
        candidates.append(pair)
    unique=list(dict.fromkeys(candidates))
    return unique[0] if len(unique)==1 else (None,None)


def _content(soup: BeautifulSoup, source_kind: str):
    content=soup.select_one('.artclViewBody, .view-content, .view-content-box, .mb-content, .artclView, article, main')
    if content:return content
    # CampusPick/Everycareer page renders details inside its container.
    if source_kind=='campuspick':return soup.select_one('#container, .contest-view, .contest_view')
    return None


def parse_details(html: str, page_url: str = '', source_kind: str = '') -> dict:
    soup=BeautifulSoup(html,'html.parser');content=_content(soup,source_kind)
    if not content:return {}
    for node in content.select('script,style,nav,header,footer,form,.comments,.comment-list,.related,.recommend'):
        node.decompose()
    text=content.get_text('\n',strip=True)
    values=fields_from_text(text)
    out={}
    if values.get('registration'):
        raw=' / '.join(values['registration'])
        start,end=registration_from_text(text)
        out.update(registration_text=compact(raw,320),registration_start=start,deadline=end,
                   registration_ambiguous=end is None)
    if values.get('event'):
        pairs=[date_range(v,allow_single=True) for v in values['event']]
        unique=list(dict.fromkeys(pairs))
        if len(unique)==1 and unique[0]!=(None,None):
            out['event_start'],out['event_end']=unique[0]
        out['event_ambiguous']=not bool(out.get('event_end'))
        out['schedule_text']=compact(' / '.join(values['event']),320)
    if values.get('schedule'):
        out['schedule_text']=compact(' / '.join(values.get('event',[])+values['schedule']),320)
    for name in ('organizer','eligibility','benefits','summary'):
        if values.get(name):out[name]=compact(' / '.join(values[name]),220)
    for a in content.select('a[href]'):
        label=a.get_text(' ',strip=True)
        href=a.get('href','');url=canonical(urljoin(page_url,href))
        if not url:continue
        path=urlsplit(url).path
        if re.match(r'/(?:login|download|linkclick|member)(?:/|$)',path):continue
        if re.search(r'(?:참가\s*)?(?:신청|접수|지원)\s*(?:하기|바로가기|사이트|링크|페이지)?$',label):
            out.setdefault('application_url',url)
        elif re.search(r'공식\s*(?:홈페이지|사이트)|홈페이지|대회\s*(?:사이트|안내)|관련\s*사이트',label):
            out.setdefault('website_url',url)
    # Metadata-free JS shells must be rendered or reported as unconfirmed.
    if out and page_url:out['detail_source_url']=canonical(page_url)
    return out
