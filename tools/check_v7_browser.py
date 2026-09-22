"""Offline DOM checks. Navigation is blocked by the harness, so an injected
Storage-compatible adapter tests UI persistence across fresh documents. Native
origin-backed localStorage and the deployed GitHub origin remain unverified.
"""
from pathlib import Path
import argparse,contextlib,http.server,json,shutil,tempfile,threading,time
from playwright.sync_api import sync_playwright,expect
p=argparse.ArgumentParser();p.add_argument('page',type=Path);p.add_argument('--screenshots',type=Path);a=p.parse_args();results=[]
class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
with tempfile.TemporaryDirectory() as td:
    root=Path(td);shutil.copyfile(a.page,root/'index.html')
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),lambda *args,**kw:Handler(*args,directory=str(root),**kw));threading.Thread(target=server.serve_forever,daemon=True).start();url='http://127.0.0.1:'+str(server.server_port)+'/'
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
            for width,height in [(320,900),(390,844),(768,1024),(1440,1050)]:
                context=browser.new_context(viewport={'width':width,'height':height});context.route('**/*',lambda r:r.abort());errors=[]
                def load(saved=None):
                    page=context.new_page();page.set_default_timeout(4000);page.on('pageerror',lambda e:errors.append(str(e)))
                    page.evaluate("""seed=>{let values={...seed};window.testStorage=values;Object.defineProperty(window,'localStorage',{value:{getItem:k=>values[k]??null,setItem:(k,v)=>{values[k]=String(v);},removeItem:k=>{delete values[k];}}});}""",saved or {})
                    page.set_content(a.page.read_text());return page
                def reload(page):
                    saved=page.evaluate('window.testStorage');page.close();return load(saved)
                page=load()
                assert page.locator('.contest').count()==8
                assert page.locator('.contest').first.get_attribute('id')=='contest-evt_urban'
                assert page.locator('#newCount').inner_text()=='1'
                assert '새 공고 2건' in page.locator('#comparisonTitle').inner_text()
                assert page.locator('#fieldFilter').count()==1,'missing independent technical field filter'
                assert page.locator('#favoriteOnly').count()==1,'missing favorites'
                assert '7.0.0' in page.locator('#runtimeSummary').inner_text()
                first=page.locator('.contest').first;first.locator('summary').click();assert '같은 대회의 공고 2건' in first.inner_text();first.locator('summary').click()
                first.locator('.favorite-button').click();assert first.locator('.favorite-button').get_attribute('aria-pressed')=='true'
                page.locator('#favoriteOnly').check();assert page.locator('.contest').count()==1
                page=reload(page);assert page.locator('#favoriteOnly').is_checked();assert page.locator('.contest').count()==1
                with page.expect_download() as download:page.locator('#exportPersonal').click()
                text=Path(download.value.path()).read_text();backup=json.loads(text);assert backup['favorites']==['evt_urban']
                page.locator('#favoriteOnly').uncheck();page.locator('#fieldFilter').select_option('creative_ai');assert page.locator('.contest').count()==1;assert 'AI 영상' in page.locator('.contest').inner_text()
                page=reload(page);assert page.locator('#fieldFilter').input_value()=='creative_ai'
                page.locator('#fieldFilter').select_option('all');page.locator('#kindFilter').select_option('program');assert page.locator('.contest').count()==3
                page.locator('#kindFilter').select_option('all');page.locator('#sourceFilter').select_option('캠퍼스픽 · AI/데이터');assert page.locator('.contest').count()==2
                page.locator('#sourceFilter').select_option('all');page.locator('#searchInput').fill('없는검색결과');page.locator('#resetFilters').click();assert page.locator('.contest').count()==8
                page.locator('#showNew').click();assert page.locator('.contest').count()==1;assert '제조 현장' in page.locator('.contest').inner_text();page.locator('#newOnly').uncheck();page.locator('#statusFilter').select_option('review')
                page.locator('#searchInput').fill('시각화');page.locator('.favorite-button').click();assert '데이터 시각화' in page.locator('#urgentFavorites').inner_text();page.locator('#searchInput').fill('')
                page.locator('#importPersonalFile').set_input_files({'name':'prefs.json','mimeType':'application/json','buffer':text.encode()});expect(page.locator('#favoriteOnly')).to_be_checked()
                page.locator('#importPersonalFile').set_input_files({'name':'bad.json','mimeType':'application/json','buffer':b'{'});expect(page.locator('#personalNotice')).to_contain_text('올바른')
                page.locator('#favoriteOnly').uncheck();page.locator('#fieldFilter').select_option('all');page.locator('#statusFilter').select_option('review')
                page.locator('#reviewSection summary').click();assert page.locator('#reviewItems .review-item').count()==1
                assert page.locator('#qualitySummary').inner_text()
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
                page.locator('.contest').first.locator('summary').focus();assert page.locator('.contest').first.locator('summary').evaluate('el=>el===document.activeElement');page.keyboard.press('Enter');assert page.locator('.contest').first.locator('details').get_attribute('open') is not None
                # A fresh document avoids depending on the earlier preference choices.
                clock=load();clock.locator('#searchInput').fill('시각화');clock.locator('.contest summary').focus()
                clock.evaluate("DATA.updated_at='2026-09-23T18:01:00+09:00';refreshClock()")
                assert '마감 / 종료' in clock.locator('.contest .pill').inner_text()
                assert clock.locator('.contest summary').evaluate('e=>e===document.activeElement')
                clock.locator('#searchInput').focus();expect(clock.locator('.contest')).to_have_count(0)
                clock.locator('#searchInput').fill('');clock.locator('#statusFilter').select_option('all')
                clock.evaluate("DATA.updated_at='2026-09-24T00:01:00+09:00';refreshClock()")
                assert clock.locator('#newCount').inner_text()=='—';assert clock.locator('#newOnly').is_disabled();assert clock.locator('.new-badge').count()==0
                clock.close()
                if a.screenshots:
                    a.screenshots.mkdir(exist_ok=True,parents=True);page.emulate_media(reduced_motion='reduce');page.evaluate('window.scrollTo({top:0,behavior:"instant"})');page.screenshot(path=str(a.screenshots/f'v7-{width}.png'),full_page=True)
                assert not errors,errors;results.append({'width':width,'passed':True,'page_errors':errors});context.close()
            browser.close()
    finally:server.shutdown();server.server_close()
print(json.dumps(results,ensure_ascii=False,indent=2))
