"""Build the same public snapshot as a standalone web page and GitHub Markdown."""
from __future__ import annotations
import csv,html,io,json,re
from datetime import datetime,timedelta
from pathlib import Path
from .core import status_of,canonical,DETAIL_FIELDS,clean_title,preferred_title
from .daily import compare_day, comparison_lines
from .quality import visible_state

LABEL={'active':'기한 남음/접수 표시','upcoming':'접수 예정','closed':'마감/종료','unknown':'마감 미확인'}

def embedded_json(data:dict)->str:
    return json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e').replace('\u2028','\\u2028').replace('\u2029','\\u2029')

def public_data(state:dict,now:datetime,demo:bool=False)->dict:
    state=visible_state(state)
    threshold=(now-timedelta(hours=24)).isoformat()
    comparison=compare_day(state, now)
    daily_new=set(comparison['new_ids'])
    recent={c['id'] for c in state['changes'] if c['kind']=='new' and c['at']>threshold}
    items=[]
    for original in state['items'].values():
        item={k:v for k,v in original.items() if k in ('id','title','url','source_id','source_name','group','posted_at','deadline','registration_start','platform_status','first_seen','last_seen','last_changed') + DETAIL_FIELDS}
        item['title']=preferred_title(item) or '제목 확인 필요'
        item['status']=status_of(item,now.date());item['recent_new']=item['id'] in recent
        item['daily_new']=item['id'] in daily_new
        items.append(item)
    items.sort(key=lambda x:deadline_sort_key(x,now.date()))
    return {'version':5,'daily_comparison':comparison,'updated_at':state.get('updated_at'),'demo':demo,'items':items,'sources':list(state['sources'].values())}

def deadline_sort_key(item, today):
    """Known remaining time descending, unknown after it, closed last."""
    from datetime import date
    end=item.get('deadline')
    closed=status_of(item,today)=='closed'
    if closed:return (2,0,clean_title(item.get('title','')))
    if not end:return (1,0,clean_title(item.get('title','')))
    try:remaining=(date.fromisoformat(end)-today).days
    except ValueError:return (1,0,clean_title(item.get('title','')))
    return (0,-remaining,clean_title(item.get('title','')))

def md_text(text:str)->str:
    return html.escape(str(text)).replace('|','\\|').replace('\n',' ').replace('[','\\[').replace(']','\\]').replace('`','\\`')

def markdown_table(data:dict)->str:
    lines=['### 어제 대비 확인 결과', '', *[md_text(x) + '  ' for x in comparison_lines(data['daily_comparison'])], '', '공고 주소 기준 · 다른 출처의 같은 대회는 중복될 수 있습니다.', '', '| 출처 | 공고 / 사이트 | 접수기간 | 대회·행사기간 | 주최 / 참가 대상 | 상태 |','|---|---|---|---|---|---|']
    rows=[i for i in data['items'] if i['status']!='closed'][:100]
    for i in rows:
        url=canonical(i['url'])
        title=md_text(i['title'])
        cell=f'[{title}](<{url}>)' if url else title
        for field,label in [('website_url','안내 사이트'),('application_url','신청')]:
            link=canonical(i.get(field) or '')
            if link:cell+=f' · [{label}](<{link}>)'
        reg=f"{i.get('registration_start') or '시작 미확인'} ~ {i.get('deadline') or '마감 미확인'}"
        if i.get('deadline') and i.get('deadline_time'):reg+=' '+i['deadline_time']
        event=f"{i.get('event_start') or '미확인'} ~ {i.get('event_end') or '미확인'}" if i.get('event_end') else (i.get('schedule_text') or '미확인')
        info=(i.get('organizer') or '주최 미확인')+' / '+(i.get('eligibility') or '대상 미확인')
        lines.append(f"| {md_text(i['source_name'])} | {cell} | {md_text(reg)} | {md_text(event)} | {md_text(info)} | {LABEL[i['status']]} |")
    if not rows:lines.append('| — | 아직 표시할 공고가 없습니다. 아래 수집 상태를 확인하세요. | — | — | — | — |')
    lines+=['','### 출처별 수집 상태','', '| 출처 | 상태 | 설명 |','|---|---|---|']
    names={'ok':'정상','error':'실패','partial':'부분 실패','disabled':'직접 확인','pending':'대기'}
    for s in data['sources']:lines.append(f"| {md_text(s['name'])} | {names.get(s['status'],s['status'])} | {md_text(s.get('message',''))} |")
    return '\n'.join(lines)

def csv_cell(value)->str:
    text='' if value is None else str(value)
    return "'"+text if text.lstrip().startswith(('=','+','-','@','\t','\r')) else text

def build(root:Path,state:dict,now:datetime,repo_url:str='',page_url:str='',demo:bool=False)->None:
    public=public_data(state,now,demo);public.update(repo_url=canonical(repo_url),page_url=canonical(page_url))
    site=root/'site';site.mkdir(exist_ok=True)
    template=(root/'web/index.template.html').read_text(encoding='utf-8')
    page=template.replace('/*__STYLE__*/',(root/'web/style.css').read_text(encoding='utf-8')).replace('/*__APP__*/',(root/'web/app.js').read_text(encoding='utf-8')).replace('/*__DATA__*/',embedded_json(public))
    (site/'index.html').write_text(page,encoding='utf-8')
    (site/'data.json').write_text(json.dumps(public,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (site/'.nojekyll').touch()
    buf=io.StringIO();writer=csv.writer(buf)
    writer.writerow(['대회명','출처','접수시작일','접수마감일','접수기간 원문','대회시작일','대회종료일','일정안내','주최기관','참가대상','혜택','주제','안내사이트','신청링크','상태','공고원문','상세확인일','접수시작시각','접수마감시각'])
    for i in public['items']:
        writer.writerow([csv_cell(v) for v in (i['title'],i['source_name'],i.get('registration_start'),i.get('deadline'),i.get('registration_text'),i.get('event_start'),i.get('event_end'),i.get('schedule_text'),i.get('organizer'),i.get('eligibility'),i.get('benefits'),i.get('summary'),i.get('website_url'),i.get('application_url'),LABEL[i['status']],i['url'],i.get('detail_checked_at'),i.get('registration_start_time'),i.get('deadline_time'))])
    (site/'contests.csv').write_text('\ufeff'+buf.getvalue(),encoding='utf-8')
    readme=root/'README.md'
    if readme.exists():
        text=readme.read_text(encoding='utf-8')
        status=f"마지막 수집 시도: **{state.get('updated_at') or '아직 수집 전'}**\n\n"
        if page_url:status+=f'[전체 웹페이지 열기]({page_url}) · [설정 안내](SETUP.md)\n\n'
        replacement='<!-- CONTESTS:START -->\n'+status+markdown_table(public)+'\n<!-- CONTESTS:END -->'
        text=re.sub(r'<!-- CONTESTS:START -->.*?<!-- CONTESTS:END -->',lambda _:replacement,text,flags=re.S)
        readme.write_text(text,encoding='utf-8')
