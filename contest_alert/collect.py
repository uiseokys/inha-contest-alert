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
from .core import canonical,parse_listing,detail_fields,merge_items,preferred_title
from .details import PARSER_VERSION,schedule_links
from .quality import effective_config,apply_policy,classify
from .repair import reuse_existing_ids

AGENT='ContestNoticeMonitor/0.2'
class FetchError(RuntimeError):
    def __init__(self,code:str,message:str):super().__init__(message);self.code=code


def robots_allowed(text:str,url:str)->bool:
    rp=RobotFileParser();rp.parse(text.splitlines())
    return rp.can_fetch(AGENT,url)


def wait_for_public_content(page,url:str)->None:
    """Wait for rendered notice text or public listing links, at most eight seconds."""
    is_detail=bool(re.search(r'/contest/view|/competitions/(?:official/|open/)?\d+|artclView|[?&]vid=',url))
    page.wait_for_function(r'''detail => {
        const text=document.body?.innerText||'';
        if(detail)return /(?:접수|참가\s*(?:기간|접수)|신청|모집)[\s\S]{0,180}?20\d{2}\s*[.년\/-]\s*\d{1,2}/.test(text);
        return [...document.querySelectorAll('a[href]')].some(a=>/artclView|[?&]vid=|\/contest\/view|\/competitions\/(?:official\/|open\/)?\d+/.test(a.getAttribute('href')));
    }''',arg=is_detail,timeout=8000)


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
                try:
                    wait_for_public_content(page,url)
                except Exception as exc:
                    from playwright.sync_api import TimeoutError as PlaywrightTimeout
                    if not isinstance(exc,PlaywrightTimeout):raise
                    # Returning the available HTML does not claim dates exist.
                    # The parser reports missing fields separately.

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
    config=effective_config(config)
    apply_policy(state,config)
    own=client is None;client=client or Client(config.get('browser_fallback',False))
    all_records=[];successful=[];stamp=now.isoformat()
    try:
        for source in config['sources']:
            report={'name':source['name'],'url':source['url'],'group':source.get('group','external'),
                    'status':'pending','message':'','checked_at':stamp,'recognized':0,'retained':0,'pages':0}
            if not source.get('enabled',True):
                report.update(status='disabled',message=source.get('disabled_reason','설정에서 자동 수집 제외; 원문 바로가기로 확인'))
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
                    reuse_existing_ids(selected,state)
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
            if old.get('duplicate_of') or old['id'] in ids or old['source_id'] not in successful:continue
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
            if classify(dict(old,**item))['relevance_status']=='excluded':continue
            attempted=old.get('detail_attempted_at') or old.get('detail_checked_at','')
            missing=not (old.get('registration_start') and old.get('deadline'))
            upgraded=old.get('date_parser_version')!=PARSER_VERSION
            due_day=now.date().isoformat() if missing else (now.date()-timedelta(days=2)).isoformat()
            if upgraded or not attempted or attempted[:10]<due_day:
                topic_known=classify(dict(state['items'].get(item['id'],{}),**item))['relevance_status']=='included'
                # Unchecked generic candidates must eventually be examined too.
                priority=0 if topic_known and not old.get('deadline') else (1 if not attempted else 2)
                grouped[item['source_id']].append((priority,attempted,item))
        queues=[deque(x[2] for x in sorted(rows,key=lambda row:(row[0],row[1]))) for rows in grouped.values() if rows]
        due=[];budget=config.get('max_detail_requests',30)
        while queues and len(due)<budget:
            for queue in queues:
                if queue and len(due)<budget:due.append(queue.popleft())
            queues=[q for q in queues if q]
        for queue in queues:
            for pending in queue:
                report=state['sources'][pending['source_id']]
                report['detail_deferred']=report.get('detail_deferred',0)+1
                pending['date_failure_code']='budget_deferred'
        # Extra requests are bounded independently of the number of notices.
        # This keeps the existing 18-minute workflow and free-host usage modest.
        extra_left=config.get('max_extra_detail_requests',18)
        browser_left=config.get('max_browser_detail_requests',16)
        stop_at=time.monotonic()+config.get('detail_time_budget_seconds',360)
        for item in due:
            report=state['sources'][item['source_id']]
            if time.monotonic()>=stop_at:
                report['detail_deferred']=report.get('detail_deferred',0)+1;item['date_failure_code']='budget_deferred';continue
            item['detail_trace']=[]
            item['date_failure_code']=''
            def trace(stage,outcome,code='',text_length=None):
                entry={'stage':stage,'outcome':outcome}
                if code:entry['code']=code
                if text_length is not None:entry['text_length']=text_length
                item['detail_trace'].append(entry)
            item['detail_attempted_at']=stamp
            item['date_parser_version']=PARSER_VERSION
            source=source_map[item['source_id']]
            def needs_dates(fields):
                return not (fields.get('registration_start') and fields.get('deadline'))
            def blend(previous,extra):
                # Keep information already established; report mutually
                # inconsistent overview/schedule dates rather than choosing one.
                mismatch=any(previous.get(k) and extra.get(k) and previous[k]!=extra[k]
                             for k in ('registration_start','deadline'))
                result=dict(previous)
                for k,v in extra.items():
                    if v is not None and (v!='' or k=='date_note'):result[k]=v
                if mismatch:
                    result.update(registration_start=None,deadline=None,registration_ambiguous=True,
                                  date_status='conflict',date_note='개요와 일정의 접수 날짜가 서로 다릅니다. 원문을 확인하세요.',
                                  date_evidence=(str(previous.get('date_evidence',''))+' / '+str(extra.get('date_evidence','')))[:400])
                return result
            try:
                html=client.get_text(item['url'])
                trace('detail_http','ok',text_length=len(html))
                fields=detail_fields(html,item['url'],source.get('kind',''),preferred_title(item))
                links=schedule_links(html,item['url'])
                # Rendering is needed for absent dates, not merely absent ALL fields.
                if needs_dates(fields) and not links and config.get('browser_fallback',False) and browser_left>0 and time.monotonic()<stop_at:
                    browser_left-=1
                    try:
                        html=client.browser_html(item['url'])
                        trace('detail_render','ok',text_length=len(html))
                        fields=blend(fields,detail_fields(html,item['url'],source.get('kind',''),preferred_title(item)))
                        links=schedule_links(html,item['url'])
                    except FetchError as exc:
                        trace('detail_render','error',exc.code);item['date_failure_code']=exc.code
                        report['detail_render_errors']=report.get('detail_render_errors',0)+1
                for link in links[:1]:
                    if (not needs_dates(fields) and fields.get('deadline_time')) or extra_left<=0 or time.monotonic()>=stop_at:break
                    extra_left-=1
                    try:
                        more=client.get_text(link)
                        trace('schedule_http','ok',text_length=len(more))
                        kind='dacon' if urlsplit(link).hostname in ('dacon.io','www.dacon.io') else source.get('kind','')
                        extra=detail_fields(more,link,kind,preferred_title(item))
                        if needs_dates(extra) and config.get('browser_fallback',False) and browser_left>0 and time.monotonic()<stop_at:
                            browser_left-=1
                            try:extra=blend(extra,detail_fields(client.browser_html(link),link,kind,preferred_title(item)))
                            except FetchError as exc:
                                trace('schedule_render','error',exc.code);item['date_failure_code']=exc.code
                                report['detail_render_errors']=report.get('detail_render_errors',0)+1
                        # Preserve the source article title; the linked platform
                        # is date evidence, not a replacement for its identity.
                        if fields.get('detail_title'):extra.pop('detail_title',None)
                        fields=blend(fields,extra)
                    except FetchError as exc:
                        trace('schedule_http','error',exc.code);item['date_failure_code']='schedule_error'
                        report['schedule_errors']=report.get('schedule_errors',0)+1
                fields['date_status']=fields.get('date_status') or ('complete' if not needs_dates(fields) else 'partial' if fields.get('deadline') or fields.get('registration_start') else 'missing')
                item.update(fields)
                trace('date_parse','ok' if fields.get('deadline') else 'unconfirmed',text_length=fields.get('detail_text_length'))
                if fields.get('registration_ambiguous'):item['date_failure_code']='date_conflict'
                elif fields.get('deadline'):item['date_failure_code']='confirmed'
                elif not item.get('date_failure_code'):item['date_failure_code']='no_explicit_date'
                substantive={k for k,v in fields.items() if v and k not in {'detail_title','detail_source_url','date_status','date_note','_topic_text','detail_parser_version','detail_text_length','detail_content_hash'}}
                if substantive:
                    item['detail_checked_at']=stamp;item['detail_status']='ok'
                else:
                    item['detail_status']='unconfirmed'
                    report['detail_unconfirmed']=report.get('detail_unconfirmed',0)+1
            except (FetchError,ValueError,TypeError,AttributeError) as exc:
                item['date_failure_code']=exc.code if isinstance(exc,FetchError) else 'parser_error'
                trace('detail_http' if isinstance(exc,FetchError) else 'date_parse','error',item['date_failure_code'])
                item['detail_status']='error'
                report['detail_errors']=report.get('detail_errors',0)+1
        for item in all_records:
            if config.get('strict_ai_data',True):
                item.update(classify(dict(state['items'].get(item['id'],{}),**item)))
        merge_items(state,all_records,now)
        apply_policy(state,config)
        for sid,report in state['sources'].items():
            all_source=[i for i in state['items'].values() if i['source_id']==sid]
            current=[i for i in all_source if i.get('relevance_status')=='included' and not i.get('duplicate_of') and i.get('last_seen','')[:10]==now.date().isoformat()]
            report['retained']=len(current)
            report['duplicates_hidden']=sum(bool(i.get('duplicate_of')) for i in all_source)
            report['excluded']=sum(i.get('relevance_status')=='excluded' for i in all_source)
            report['topic_pending']=sum(i.get('relevance_status')=='pending' for i in all_source)
            report['dates_complete']=sum(bool(i.get('registration_start') and i.get('deadline')) for i in current)
            report['dates_partial']=sum(bool(i.get('registration_start') or i.get('deadline')) and not bool(i.get('registration_start') and i.get('deadline')) for i in current)
            report['dates_missing']=len(current)-report['dates_complete']-report['dates_partial']
        state['initialized_sources']=sorted(set(state['initialized_sources'])|set(successful))
        from .daily import capture_snapshot
        capture_snapshot(state, now)
        return state
    finally:
        if own:client.close()
