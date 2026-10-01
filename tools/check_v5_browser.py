"""Offline Chromium acceptance test with explicitly synthetic v5 records."""
from pathlib import Path
import argparse,copy,json,shutil,sys,tempfile
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from contest_alert import core,quality,render,daily

def demo_state(now):
    sources=[{'id':'aix','name':'인공지능융합연구센터','kind':'mangboard','group':'inha','url':'https://example.com/center/'},
             {'id':'campuspick','name':'캠퍼스픽 · AI/데이터','kind':'campuspick','group':'external','url':'https://example.com/contests/'},
             {'id':'inha','name':'인하대학교 · 교내 공지','kind':'k2web','group':'inha','url':'https://www.inha.ac.kr/'}]
    state=core.empty_state();cfg=quality.effective_config({'sources':sources})
    values=[('a','aix','[예시] 도시 데이터 예측 경진대회','2026-11-30','18:00'),
            ('b','campuspick','[예시] 생성형 AI로 만드는 지속가능한 도시·환경·교육 서비스 및 공공데이터 분석과 실증 프로젝트 아이디어 경진대회','2026-10-31','23:59'),
            ('c','aix','[예시] AI 연구 프로그램',None,None),
            ('x','campuspick','[예시] 풍경 사진 공모전','2026-12-31',None),
            ('y','inha','[예시] 데이터 교내 공고','2026-12-31',None)]
    for rid,sid,title,end,clock in values:
        src=next(s for s in sources if s['id']==sid)
        core.merge_items(state,[dict(id=rid,source_id=sid,source_name=src['name'],group=src['group'],title=title,listing_title=title,
            url='https://example.com/contest/'+rid,registration_start='2026-09-01' if end else None,deadline=end,
            deadline_time=clock,detail_checked_at=now.isoformat(),detail_status='ok',organizer='가상 주최기관',
            eligibility='가상 참가 대상',date_evidence=('접수마감: '+end+' '+(clock or '')) if end else '',
            date_source_url='https://example.com/contest/'+rid)],now)
    state['items']['a'].update(title='공지사항',detail_title='공지사항')
    state['sources']={s['id']:dict(name=s['name'],url=s['url'],group=s['group'],status='disabled' if s['id']=='inha' else 'ok',
        message='[가상 예시] 자동 수집 제외 · 직접 확인' if s['id']=='inha' else '[가상 예시] 필터 결과',
        checked_at=now.isoformat(),retained=2,excluded=1,topic_pending=1) for s in sources}
    state['claims']['secret-test']={'token':'not-public-test-marker'}
    quality.apply_policy(state,cfg)
    for change in state['changes']:
        if change['id']=='b':change['kind']='new'
    prev=copy.deepcopy(state);prev['items'].pop('b');daily.capture_snapshot(prev,now-timedelta(days=1))
    state['daily_snapshots']=prev['daily_snapshots'];daily.capture_snapshot(state,now)
    return state

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);p.add_argument('--screenshots',type=Path);a=p.parse_args()
    now=datetime(2026,9,22,11,43,tzinfo=ZoneInfo('Asia/Seoul'));state=demo_state(now)
    root=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as td:
        tmp=Path(td);shutil.copytree(root/'web',tmp/'web');render.build(tmp,state,now,repo_url='https://github.com/',demo=True)
        text=(tmp/'site/index.html').read_text()
        assert '풍경 사진 공모전' not in text and 'not-public-test-marker' not in text
        if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text)
    results=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
        for width,height in [(320,900),(390,844),(768,1024),(1440,1100)]:
            page=browser.new_page(viewport={'width':width,'height':height});page.set_default_timeout(3000)
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.route('**/*',lambda route:route.abort())
            page.set_content(text,wait_until='load')
            ids=[c.get_attribute('id') for c in page.locator('.contest').all()]
            assert ids==['contest-a','contest-b','contest-c'],ids
            assert '공지사항' not in page.locator('.contest h3').all_text_contents()
            first=page.locator('#contest-a');assert '2026-11-30 18:00' in first.inner_text()
            first.locator('summary').click()
            assert '접수 마감 시각' in first.inner_text() and 'AI·데이터 관련 근거' in first.inner_text()
            assert '관련성 검사: 제외' in page.locator('#sourceHealth').inner_text()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            if a.screenshots:
                a.screenshots.mkdir(parents=True,exist_ok=True)
                page.screenshot(path=str(a.screenshots/f'v5-{width}.png'),full_page=True)
            page.locator('#showNew').click();assert page.locator('.contest').count()==1
            assert page.locator('.contest').first.get_attribute('id')=='contest-b'
            assert not errors,errors
            results.append({'width':width,'result':'PASS','page_errors':errors});page.close()
        browser.close()
    print(json.dumps(results,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
