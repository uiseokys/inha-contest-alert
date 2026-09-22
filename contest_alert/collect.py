"""Small, polite, source-isolated public-page collector.

Live access varies by website and GitHub runner IP. An access or parsing failure
is ALWAYS reported; it is never silently interpreted as zero competitions.
"""
from __future__ import annotations
import re
import time
from collections import deque
from datetime import datetime,timedelta
from urllib.parse import urlsplit,urljoin
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
from .core import canonical,parse_listing,detail_fields,merge_items

AGENT='ContestNoticeMonitor/0.2'
class FetchError(RuntimeError):
    def __init__(self,code:str,message:str):super().__init__(message);self.code=code


def robots_allowed(text:str,url:str)->bool:
    rp=RobotFileParser();rp.parse(text.splitlines())
    return rp.can_fetch(AGENT,url)


class Client:
    def __init__(self,browser_fallback:bool=False):
        self.session=requests.Session();self.session.headers['User-Agent']=AGENT
        self.robots={};self.last_request={};self.browser_fallback=browser_fallback
        self._pw=None;self._browser=None
    def _raw(self,url:str)->tuple[int,str]:
        host=urlsplit(url).netloc
        pause=1-(time.monotonic()-self.last_request.get(host,0))
        if pause>0:time.sleep(pause)
        self.last_request[host]=time.monotonic()
        try:
            with self.session.get(url,timeout=(8,15),stream=True) as r:
                if r.status_code>=400:return r.status_code,''
                chunks=[];size=0
                for chunk in r.iter_content(65536):
                    size+=len(chunk)
                    if size>3_000_000:raise FetchError('too_large','HTML 응답이 3 MB 한도를 초과함')
                    chunks.append(chunk)
                data=b''.join(chunks)
                enc=r.encoding
                if not enc or enc.lower()=='iso-8859-1':enc='utf-8'
                return r.status_code,data.decode(enc,errors='replace')
        except requests.RequestException as e:
            # Do not include request URLs or response bodies in public error output.
            raise FetchError('network_error',f'네트워크 요청 실패 ({type(e).__name__})') from None
    def _check_robots(self,url:str):
        p=urlsplit(url);origin=f'{p.scheme}://{p.netloc}'
        if origin not in self.robots:
            status,text=self._raw(origin+'/robots.txt')
            if status in (404,410):text='User-agent: *\nDisallow:'
            elif status!=200:raise FetchError('robots_unavailable',f'robots.txt 확인 실패 (HTTP {status}); 수집 보류')
            self.robots[origin]=text
        if not robots_allowed(self.robots[origin],url):raise FetchError('robots_disallowed','robots.txt에 따라 자동 수집하지 않음')
    def get_text(self,url:str)->str:
        self._check_robots(url)
        status,text=self._raw(url)
        if status!=200:raise FetchError(f'http_{status}',f'HTTP {status}; 로그인/차단을 우회하지 않음')
        if re.search(r'access denied|verify you are human|captcha|just a moment\.\.\.',text[:12000],re.I):
            raise FetchError('access_blocked','접근 제한 화면 감지; 인증/차단을 우회하지 않음')
        return text
    def browser_html(self,url:str)->str:
        self._check_robots(url)
        if not self.browser_fallback:raise FetchError('no_links','게시글 링크를 찾지 못함')
        try:
            if self._browser is None:
                from playwright.sync_api import sync_playwright
                self._pw=sync_playwright().start()
                self._browser=self._pw.chromium.launch(headless=True)
            page=self._browser.new_page()
            try:
                page.route('**/*',lambda route:route.abort() if route.request.resource_type in ('image','media','font') else route.continue_())
                response=page.goto(url,wait_until='domcontentloaded',timeout=25000)
                if response and response.status in (401,403,429):raise FetchError('browser_denied',f'HTTP {response.status}; 우회하지 않음')
                if '/contest' in urlsplit(url).path and 'campuspick.com' in urlsplit(url).netloc:
                    page.wait_for_timeout(5000)
                else:page.wait_for_timeout(2500)
                return page.content()
            finally:page.close()
        except FetchError:raise
        except Exception as e:raise FetchError('browser_failed',f'공개 페이지 렌더링 실패 ({type(e).__name__})') from None
    def close(self):
        if self._browser:self._browser.close()
        if self._pw:self._pw.stop()
        self.session.close()


def discover_pages(html:str,base:str)->list[str]:
    """Follow only links already present: notice subpages or link-based pagination."""
    soup=BeautifulSoup(html,'html.parser');host=urlsplit(base).hostname;result=[]
    for a in soup.select('a[href]'):
        url=canonical(urljoin(base,a['href']));label=a.get_text(' ',strip=True)
        if not url or urlsplit(url).hostname!=host:continue
        board=bool(re.search(r'공지|공모|경진|이벤트|외부.*홍보|학사.*안내',label) and 'subview.do' in url and 'enc=' not in url)
        pagination=bool(re.search(r'[?&](?:pageIndex|board_page|page)=\d+',url) and len(label)<12)
        if (board or pagination) and url!=canonical(base) and url not in result:result.append(url)
    return result


def collect_all(config:dict,state:dict,now:datetime,client:Client|None=None)->dict:
    own=client is None;client=client or Client(config.get('browser_fallback',False))
    all_records=[];successful=[];stamp=now.isoformat()
    try:
        for source in config['sources']:
            report={'name':source['name'],'url':source['url'],'group':source.get('group','external'),
                    'status':'pending','message':'','checked_at':stamp,'recognized':0,'retained':0,'pages':0}
            if not source.get('enabled',True):
                report.update(status='disabled',message='설정에서 자동 수집 제외; 원문 바로가기로 확인')
                state['sources'][source['id']]=report;continue
            queue=deque([source['url']]);visited=set();records={};errors=[];empty_valid=False
            while queue and len(visited)<config.get('max_pages_per_source',2):
                url=queue.popleft()
                if url in visited:continue
                visited.add(url)
                try:
                    html=client.get_text(url)
                    selected,count=parse_listing(html,source,url)
                    extra=discover_pages(html,url)
                    if count==0 and not extra and config.get('browser_fallback',False):
                        html=client.browser_html(url);selected,count=parse_listing(html,source,url);extra=discover_pages(html,url)
                    report['recognized']+=count;report['pages']+=1
                    empty_valid=empty_valid or bool(re.search(r'등록된\s*게시물이\s*없|검색된\s*결과가\s*없',BeautifulSoup(html,'html.parser').get_text(' ',strip=True)))
                    for item in selected:
                        old=state['items'].get(item['id'])
                        cutoff=(now.date()-timedelta(days=config.get('lookback_days',120))).isoformat()
                        if not old and item.get('posted_at') and item['posted_at']<cutoff:continue
                        if not old and not item.get('posted_at') and item.get('platform_status')=='closed':continue
                        records[item['id']]=item
                    for link in extra:
                        if link not in visited:queue.append(link)
                except FetchError as e:errors.append(str(e))
                except Exception as e:errors.append(f'파서 오류 ({type(e).__name__}); 기존 기록 유지')
            report['retained']=len(records)
            if report['recognized'] or empty_valid:
                successful.append(source['id'])
                report.update(status='partial' if errors else 'ok',message='; '.join(errors) if errors else '설정된 범위 수집 완료 · 전체 게시판 전수 수집 아님')
            else:report.update(status='error',message='; '.join(errors) or '게시글 링크 0개: 구조 변경/렌더링/접근 제한 확인 필요')
            state['sources'][source['id']]=report
            all_records.extend(records.values())
        # Revisit recent notices even if they moved off the list, especially a
        # just-expired deadline which may have been extended. Never re-fetch an
        # unbounded archive; the same global detail budget applies.
        source_map={src['id']:src for src in config['sources'] if src.get('enabled',True)}
        ids={i['id'] for i in all_records}
        for old in state['items'].values():
            if old['id'] in ids or old['source_id'] not in successful:continue
            end=old.get('deadline')
            recent_seen=old.get('last_seen','')[:10]>=(now.date()-timedelta(days=14)).isoformat()
            recently_ended=bool(end and end>=(now.date()-timedelta(days=7)).isoformat())
            if recently_ended or (not end and recent_seen):
                copy=dict(old);copy['_preserve_last_seen']=True;all_records.append(copy)
        # Fair round-robin: a large first board must not consume the entire
        # budget and permanently starve CampusPick or other later sources.
        grouped={sid:[] for sid in source_map}
        for item in all_records:
            old=state['items'].get(item['id'],{})
            attempted=old.get('detail_attempted_at') or old.get('detail_checked_at','')
            if not attempted or attempted[:10]<(now.date()-timedelta(days=2)).isoformat():
                grouped[item['source_id']].append((attempted,item))
        queues=[deque(x[1] for x in sorted(rows,key=lambda row:row[0])) for rows in grouped.values() if rows]
        due=[];budget=config.get('max_detail_requests',30)
        while queues and len(due)<budget:
            for queue in queues:
                if queue and len(due)<budget:due.append(queue.popleft())
            queues=[q for q in queues if q]
        for item in due:
            report=state['sources'][item['source_id']]
            item['detail_attempted_at']=stamp
            source=source_map[item['source_id']]
            try:
                html=client.get_text(item['url'])
                fields=detail_fields(html,item['url'],source.get('kind',''))
                if not fields and config.get('browser_fallback',False):
                    html=client.browser_html(item['url'])
                    fields=detail_fields(html,item['url'],source.get('kind',''))
                if fields:
                    item.update(fields);item['detail_checked_at']=stamp;item['detail_status']='ok'
                else:
                    item['detail_status']='unconfirmed'
                    report['detail_unconfirmed']=report.get('detail_unconfirmed',0)+1
            except (FetchError,ValueError,TypeError,AttributeError):
                item['detail_status']='error'
                report['detail_errors']=report.get('detail_errors',0)+1
        merge_items(state,all_records,now)
        state['initialized_sources']=sorted(set(state['initialized_sources'])|set(successful))
        from .daily import capture_snapshot
        capture_snapshot(state, now)
        return state
    finally:
        if own:client.close()
